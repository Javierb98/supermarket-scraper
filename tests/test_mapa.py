"""MAPA feed: a tiny xlsx built here, read with the feed's own reader. No network, no DB."""

import io
import os
import sys
import unittest
import zipfile
from datetime import date
from xml.sax.saxutils import escape

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import mapa
from pipeline.catalog import products


def cell(ref, v):
    if isinstance(v, str):
        return f'<c r="{ref}" t="inlineStr"><is><t>{escape(v)}</t></is></c>'
    return f'<c r="{ref}"><v>{v}</v></c>'


def colname(i):
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def xlsx(rows):
    body = ''.join(
        f'<row r="{n}">' + ''.join(cell(f'{colname(i)}{n}', v) for i, v in enumerate(r) if v is not None) + '</row>'
        for n, r in enumerate(rows, 1))
    ns = 'xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w') as z:
        z.writestr('xl/workbook.xml', f'<workbook {ns} xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
                   '<sheets><sheet name="Agosto 2026" sheetId="1" r:id="rId1"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels',
                   '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                   '<Relationship Id="rId1" Target="worksheets/sheet1.xml"/></Relationships>')
        z.writestr('xl/worksheets/sheet1.xml', f'<worksheet {ns}><sheetData>{body}</sheetData></worksheet>')
    return buf.getvalue()


MEASURES = ['CONSUMO X CAPITA', 'PENETRACION (%)', 'GASTO X CAPITA', 'PRECIO MEDIO kg ó litros',
            'VALOR (Miles Euros)', 'VOLUMEN (Miles kg ó litros)']


def sheet():
    header, measures = ['AGOSTO 26'], [None]
    for label in mapa.REGIONS:
        header += [label] + [None] * 5
        measures += MEASURES

    def line(label, price, pen=50.0):
        r = [label]
        for _ in mapa.REGIONS:
            r += [1.0, pen, 1.0, price, 1.0, 1.0]
        return r

    return [['CONSUMO HOGARES'], header, measures,
            line('.TOTAL ALIMENTACION', 3.0),
            line('TOTAL HUEVOS GALLINA', 0.25),
            line('T.HORTALIZAS FRESCAS', 2.0),
            line('TOMATES', 2.5),
            line('CHAMPIÑONES+O.SETAS', 5.8),
            line('T.FRUTAS FRESCAS', 2.0),
            line('CEREZAS', 6.0, pen=0.5),          # too few households
            line('T.FRUTA&HORTA.TRANSF', 3.0),
            line('TOMATES', 1.1)]                   # tinned: a later section, ignored


class MAPA(unittest.TestCase):
    def test_every_mapped_name_is_in_the_catalogue(self):
        for rows in mapa.SECTIONS.values():
            for name, unit, _ in rows.values():
                self.assertIn(name.lower(), products(), name)

    def test_region_names_are_the_scrapers(self):
        self.assertEqual(sorted(r for r in mapa.REGIONS.values() if r), sorted([
            'Pais Vasco', 'Castilla-La Mancha', 'Comunidad Valenciana', 'Andalucia', 'Castilla y Leon',
            'Extremadura', 'Baleares', 'Cataluna', 'Galicia', 'Aragon', 'La Rioja', 'Madrid', 'Murcia',
            'Navarra', 'Asturias', 'Canarias', 'Cantabria']))

    def test_sheet(self):
        wb = mapa.Workbook(xlsx(sheet()))
        (name, path), = wb.sheets
        month = mapa.sheet_month(name)
        self.assertEqual(month, date(2026, 8, 1))
        got = mapa.figures_from_sheet(wb.rows(path), month)
        names = {f.name for f in got}
        self.assertEqual(names, {'Eggs', 'Tomato', 'White Mushroom'})
        self.assertEqual(len(got), 3 * 18)
        eggs = [f for f in got if f.name == 'Eggs' and f.region is None][0]
        self.assertEqual((eggs.price, eggs.unit), (3.0, 'dozen'))   # 0.25 an egg
        tomato = [f for f in got if f.name == 'Tomato' and f.region == 'Navarra'][0]
        self.assertEqual(tomato.price, 2.5)                         # the fresh row, not the tin

    def test_file_link_pattern(self):
        page = ('<a href="/es/dam/jcr:x/2025dic-datos-mensuales-panel-consumo-hogares-ccaa-base2021-ok2.2026.xlsx">'
                '<a href="/es/dam/jcr:y/2026ago-datos-mensuales-panel-consumo-hogares-ccaa-base2021-ok2.abc.xlsx">'
                '<a href="/dam/x/2026ago-datos-mensuales-panel-consumo-hogares-canales-base2021.xlsx">')
        found = mapa.FILE.findall(page)
        self.assertEqual([f[2] for f in found], ['2025', '2026'])


if __name__ == '__main__':
    unittest.main()
