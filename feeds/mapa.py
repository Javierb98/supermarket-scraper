"""
Spain: average prices paid by households, by autonomous community, from the
Ministry of Agriculture's household food consumption panel (MAPA, "Panel de
consumo alimentario en hogares").

A panel of households records everything it buys; MAPA publishes, per month
and per community, value and volume per product and their quotient — the
"precio medio kg ó litros". That is what a household paid at the till, so it
is stored as a retail price, beside (not instead of) the shop scrapes.

    python feeds/mapa.py              latest month in the newest file
    python feeds/mapa.py --months 8   every month of that file (one year at most)

The data is one xlsx per year, a sheet per month ("Agosto 2026"), each
community a block of six columns. The file's address carries a content hash,
so it is found by name on the "series anuales" page. The panel is published
with a lag of about two months.

xlsx is read with the standard library (zipfile + ElementTree): the project
has no openpyxl and this does not need one.

Licence: reuse of Spanish public-sector information (Ley 37/2007, Real
Decreto 1495/2011), with attribution to the Ministerio de Agricultura, Pesca
y Alimentación. https://www.mapa.gob.es/es/pie/aviso-legal
"""

import io
import os
import re
import ssl
import sys
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import common, monthly_guard

SOURCE_NAME = 'MAPA household consumption panel'
SITE = 'https://www.mapa.gob.es'
PAGE = SITE + '/es/alimentacion/temas/consumo-tendencias/panel-de-consumo-alimentario/series-anuales/'
FILE = re.compile(r'href="([^"]*?/((\d{4})[a-z]*)-datos-mensuales-panel-consumo-hogares-ccaa[^"]*\.xlsx)"')

NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
RNS = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PKG = '{http://schemas.openxmlformats.org/package/2006/relationships}'

MESES = {'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6, 'julio': 7,
         'agosto': 8, 'septiembre': 9, 'setiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12}

# Header in the file -> the community name the scrapers use; None = Spain.
REGIONS = {
    'T.ESPAÑA': None,
    'CATALUÑA': 'Cataluna',
    'ARAGÓN': 'Aragon',
    'ILLES BALEARS': 'Baleares',
    'COMUNITAT VALENCIANA': 'Comunidad Valenciana',
    'REGIÓN DE MURCIA': 'Murcia',
    'ANDALUCÍA': 'Andalucia',
    'COMUNIDAD DE MADRID': 'Madrid',
    'CASTILLA - LA MANCHA': 'Castilla-La Mancha',
    'EXTREMADURA': 'Extremadura',
    'CASTILLA Y LEÓN': 'Castilla y Leon',
    'GALICIA': 'Galicia',
    'PRINCIPADO DE ASTURIAS': 'Asturias',
    'CANTABRIA': 'Cantabria',
    'PAIS VASCO': 'Pais Vasco',
    'LA RIOJA': 'La Rioja',
    'C. FORAL DE NAVARRA': 'Navarra',
    'CANARIAS': 'Canarias',
}

# Rows are read inside a section, because labels repeat: "TOMATES" is fresh
# tomatoes under T.HORTALIZAS FRESCAS and tinned ones further down.
# section header -> {row label: (catalogue name, unit, multiplier)}
# The price is per kg or litre, except eggs, per egg (x12 for a dozen).
# Group rows (COLES, LECHUGA/ESC./ENDIVIA, UVAS, CORDERO...) are left out.
SECTIONS = {
    '.TOTAL ALIMENTACION': {
        'TOTAL HUEVOS GALLINA': ('Eggs', 'dozen', 12.0),       # hen eggs, price per egg
        'MIEL': ('Honey', 'kg', 1.0),
    },
    'TOTAL CARNE': {
        'POLLO ENTERO': ('Whole Chicken', 'kg', 1.0),
        'CARNE CONEJO': ('Rabbit Meat', 'kg', 1.0),
    },
    'TOTAL LECHE LIQUIDA': {
        'LECHE ENTERA': ('Whole Milk', 'l', 1.0),
        'LECHE DESNATADA': ('Skim Milk', 'l', 1.0),
        'LECHE DE CABRA': ('Goat Milk', 'l', 1.0),
    },
    'DERIVADOS LACTEOS': {
        'MANTEQUILLA': ('Butter', 'kg', 1.0),
        'QUESO LECHE CABRA': ('Goat Cheese', 'kg', 1.0),
        'QUESO LECHE OVEJA': ('Sheep Cheese', 'kg', 1.0),
    },
    'TOTAL ACEITE': {
        'A.O VIRGEN EXTRA': ('Olive Oil', 'l', 1.0),
    },
    'TOTAL PATATAS': {
        'PATATAS FRESCAS': ('Potato', 'kg', 1.0),
    },
    'T.HORTALIZAS FRESCAS': {
        'TOMATES': ('Tomato', 'kg', 1.0),
        'CEBOLLAS': ('Onion', 'kg', 1.0),
        'AJOS': ('Garlic', 'kg', 1.0),
        'PEPINOS': ('Cucumber', 'kg', 1.0),
        'JUDIAS VERDES': ('Green Beans', 'kg', 1.0),
        'PIMIENTOS': ('Bell Pepper', 'kg', 1.0),
        'CHAMPIÑONES+O.SETAS': ('White Mushroom', 'kg', 1.0),   # mostly button mushrooms
        'ESPARRAGOS': ('Asparagus', 'kg', 1.0),
        'ACELGA': ('Swiss Chard', 'kg', 1.0),
        'BERENJENAS': ('Eggplant', 'kg', 1.0),
        'ZANAHORIAS': ('Carrot', 'kg', 1.0),
        'CALABACINES': ('Zucchini', 'kg', 1.0),
        'BROCOLI': ('Broccoli', 'kg', 1.0),
        'ALCACHOFAS': ('Artichoke', 'kg', 1.0),
        'APIO': ('Celery', 'kg', 1.0),
        'COLIFLOR': ('Cauliflower', 'kg', 1.0),
        'PUERRO': ('Leek', 'kg', 1.0),
        'CALABAZA': ('Pumpkin', 'kg', 1.0),
        'RABANOS/RABANITOS': ('Radish', 'kg', 1.0),
    },
    'T.FRUTAS FRESCAS': {
        'NARANJAS': ('Oranges', 'kg', 1.0),
        'MANDARINAS': ('Mandarin Oranges Fresh', 'kg', 1.0),
        'LIMONES': ('Lemons', 'kg', 1.0),
        'PLATANOS': ('Banana', 'kg', 1.0),
        'MANZANAS': ('Apples', 'kg', 1.0),
        'MANZANA PINK LADY': ('Pink Lady Apples', 'kg', 1.0),
        'PERAS': ('Pears', 'kg', 1.0),
        'MELOCOTONES': ('Peaches', 'kg', 1.0),
        'FRESAS/FRESON': ('Strawberries', 'kg', 1.0),
        'MELON': ('Melon', 'kg', 1.0),
        'SANDIA': ('Watermelon', 'kg', 1.0),
        'CIRUELAS': ('Plums', 'kg', 1.0),
        'CEREZAS': ('Cherries', 'kg', 1.0),
        'KIWI': ('Kiwi', 'kg', 1.0),
        'AGUACATE': ('Avocado', 'kg', 1.0),
        'PIÑA': ('Pineapple', 'kg', 1.0),
        'CHIRIMOYA': ('Custard Apple', 'kg', 1.0),
        'MANGO': ('Mango', 'kg', 1.0),
        'FRAMBUESAS': ('Raspberry', 'kg', 1.0),
        'ARANDANO': ('Blueberries', 'kg', 1.0),
        'CAQUI': ('Persimmon', 'kg', 1.0),
    },
    'FRUTOS SECOS&SEMILLAS': {
        'NUECES CON CASCARA': ('Walnuts', 'kg', 1.0),
        'CASTAÑAS': ('Chestnuts', 'kg', 1.0),
    },
}

# Where each section ends: the next top-level total.
SECTION_ENDS = {'TOTAL CARNE', 'TOTAL PESCA', 'TOTAL LECHE LIQUIDA', 'DERIVADOS LACTEOS', 'PAN',
                'TOTAL ACEITE', 'TOTAL VINOS', 'TOTAL PATATAS', 'T.HORTALIZAS FRESCAS',
                'T.FRUTAS FRESCAS', 'FRUTOS SECOS&SEMILLAS', 'T.FRUTA&HORTA.TRANSF',
                '.T.ALIMENT.ECOLOGICOS'}

# A community's figure rests on few households when few buy the product
# (penetration, in %); below this it is too noisy to show.
MIN_PENETRATION = 1.0

# mapa.gob.es sends two certificates for FNMT's new root "AC RAIZ FNMT-RCM
# SERVIDORES SEGUROS G2R": a self-signed one no trust store knows yet, and
# this one, the same key cross-signed by "AC RAIZ FNMT-RCM", which Mozilla's
# store (certifi, Debian's ca-certificates) does trust. OpenSSL takes the
# self-signed one and gives up. Adding this cross-signed certificate lets it
# build the chain up to the trusted FNMT root: verification stays on, the
# chain is still checked in full. Valid until 2029-12-16; from FNMT,
# http://www.cert.fnmt.es/certs/ (sha256 32:7E:C9:39:...:B1:07:7A).
FNMT_G2R_CROSS = """-----BEGIN CERTIFICATE-----
MIIGfDCCBGSgAwIBAgIQDRmrUJXP01BpQWO7H0YTQTANBgkqhkiG9w0BAQwFADA7
MQswCQYDVQQGEwJFUzERMA8GA1UECgwIRk5NVC1SQ00xGTAXBgNVBAsMEEFDIFJB
SVogRk5NVC1SQ00wHhcNMjUxMjE2MTM1MDUwWhcNMjkxMjE2MTM1MDUwWjBSMQsw
CQYDVQQGEwJFUzERMA8GA1UECgwIRk5NVC1SQ00xMDAuBgNVBAMMJ0FDIFJBSVog
Rk5NVC1SQ00gU0VSVklET1JFUyBTRUdVUk9TIEcyUjCCAiIwDQYJKoZIhvcNAQEB
BQADggIPADCCAgoCggIBALQ5a+qwhJLRhbQIUIwPLu/7VIlvnpwiQdmDtH+x6dYH
fGFJq53a8p5U6upv8qCFPjKdeIf5FdCGlZb6ZQGn+OG2lG1t2hNUipNIAqfYWdqJ
zDGIkSDnCgubEsR85/CSB10E9bZB3FkQJpYgqEsfIz84C0DQNYToJz7qdObLPUrp
/BUZvFa/L0wnsx2/RirDmau83zlS6MYdQTZQDbmsy/0pi+sV8Cu+GYfYcr2DALC1
11t9RIZoQ59evDzcJsa4S/y5t3qEgMZs9UzNoGiix2fR/N0QP02cuUiW8DVLcNue
qG/ow949OxGwSkJc7dkaZDTeezRByG/02e/MBhrfgUodp9aoGxO/sbtpr6Ptvp+F
C5SwnTJtqAtxZl2LUPhNyN9eCeblrJ12rrLI7mzpwPTM9UiJa9pYOfegeXieDwoH
ufFHR2Hg3RQm/lo75BSvaman89NTva5tS1bx2Rwed2CEKoT8WrWETGBGKupbAp+c
9eE7z39Kx7MkooNqX2TbC5k3OIkcbbeBu7WByP7OSpM1bz4fuj2JgDsmyMtw4J4p
D8+w0k65j+Pmpz82+tbxuoEWw5MPFRQquMjQ+5b63zlguLtdy+2U4uEhGap0v0UO
m9ZIS1tTKGc2vJU4NHBM5nF91AUAwifsxQu2JUBkO9R6FFmL261K+jpLZETs2dpR
AgMBAAGjggFjMIIBXzAOBgNVHQ8BAf8EBAMCAQYwDwYDVR0TAQH/BAUwAwEB/zAd
BgNVHQ4EFgQUI4JUVDBhTKBOgbmDiPLKBfYZuJswHwYDVR0jBBgwFoAU933F/cTo
mht3ZKf1HaDMv4dgmm0wEQYDVR0gBAowCDAGBgRVHSAAMBMGA1UdJQQMMAoGCCsG
AQUFBwMBMIGVBggrBgEFBQcBAQSBiDCBhTBJBggrBgEFBQcwAYY9aHR0cDovL29j
c3Bmbm10cmNtY2EuY2VydC5mbm10LmVzL29jc3Bmbm10cmNtY2EvT2NzcFJlc3Bv
bmRlcjA4BggrBgEFBQcwAoYsaHR0cDovL3d3dy5jZXJ0LmZubXQuZXMvY2VydHMv
QUNSQUlaRk5NVC5jcnQwPAYDVR0fBDUwMzAxoC+gLYYraHR0cDovL3d3dy5jZXJ0
LmZubXQuZXMvY3Jscy9BUkxGTk1UUkNNLmNybDANBgkqhkiG9w0BAQwFAAOCAgEA
HsB/he46/txFsYNJSIxOXPIo4DdNDsPjsm4EqrxSlS6TI0DCzsKAQZHOQhrCp0Bn
9tltUggRnipC4a1sn679PPKj3Ze3/HQ6r3oiZpZlBtRt8rajePtXNxGlvs7RKv1g
Td0/b37Cmd8Ucw7427YdQAbjPXaakeE6Rmy58G51EExfTYR1TMYtqXIVTka/W5x8
zZhgogf4Uf+mu/sYeLbW/XxSKQ1XlPrDJok7WWKdMHFfPcbOH7eANRDXdHBxHbKx
ZZ+BU6RSxJQVRcS5xTc7xe207SrkOKGBT42MQCh+CmN+igROjB3SnG7quX9guwmh
TpGGHqD47M7C5ypu2Eq2M4+ShJb+06/f7veLV4GC5P+qBZHKhyfCUy7ENUjoFW4l
tS/aq3p8MYpNuzgqd0h/ff5qWxHCt4pjwkU2l2YM7rKpfA8TRwynGdOD1j7/ZGOe
ntzc0hnD5EmwbW4vl6C9azUZY84eLF6BQfiOBDeV5UHbwxIA8WVx0rqLAPeY7cFT
WFxYbHUD/L8sMWj/5rKJlexksvUD/qf/AUdM0eukvjA2mOHMBXNf1mdNC00d2pCK
KRXjKXY58+yBIVtCxlYQ/5a1T9pxGjvYVh+Wa/CQ+gzZpZvBw6FCtYFqRWYlyx1O
+aK/hD7Uw8BlmrBq87pNupkoZ1K0gduT3sfuxVpJvMU=
-----END CERTIFICATE-----
"""


def _context():
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        ctx = ssl.create_default_context()
    ctx.load_verify_locations(cadata=FNMT_G2R_CROSS)
    return ctx


def fetch(url, retries=3, timeout=180, pause=1.0):
    """common.get(), with a context that can verify mapa.gob.es."""
    req = urllib.request.Request(url, headers={'User-Agent': common.USER_AGENT, 'Accept': '*/*'})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=_context()) as r:
                body = r.read()
            time.sleep(pause)
            return body
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))


def _col(ref):
    n = 0
    for ch in re.match(r'[A-Z]+', ref).group():
        n = n * 26 + ord(ch) - 64
    return n - 1


class Workbook:
    """Just enough of an xlsx reader: sheet names and rows of cell values."""

    def __init__(self, data):
        self.z = zipfile.ZipFile(io.BytesIO(data))
        root = ET.fromstring(self.z.read('xl/workbook.xml'))
        rels = {r.get('Id'): r.get('Target') for r in ET.fromstring(self.z.read('xl/_rels/workbook.xml.rels')).iter(PKG + 'Relationship')}
        self.sheets = []
        for s in root.iter(NS + 'sheet'):
            target = rels[s.get(RNS + 'id')].lstrip('/')
            self.sheets.append((s.get('name'), target if target.startswith('xl/') else 'xl/' + target))
        try:
            sst = ET.fromstring(self.z.read('xl/sharedStrings.xml'))
            self.strings = [''.join(t.text or '' for t in si.iter(NS + 't')) for si in sst.iter(NS + 'si')]
        except KeyError:
            self.strings = []

    def rows(self, path):
        for _, el in ET.iterparse(self.z.open(path)):
            if el.tag != NS + 'row':
                continue
            row = {}
            for c in el.iter(NS + 'c'):
                v = c.find(NS + 'v')
                if v is not None:
                    val = v.text
                    if c.get('t') == 's':
                        val = self.strings[int(val)]
                else:
                    inline = c.find(NS + 'is')
                    if inline is None:
                        continue
                    val = ''.join(t.text or '' for t in inline.iter(NS + 't'))
                row[_col(c.get('r'))] = val
            yield row
            el.clear()


def sheet_month(name):
    """'Agosto 2026' -> date(2026, 8, 1), or None for a sheet that is not a month."""
    m = re.match(r'\s*([A-Za-zé]+)\s+(\d{4})', name or '')
    if not m or m.group(1).lower() not in MESES:
        return None
    return date(int(m.group(2)), MESES[m.group(1).lower()], 1)


def figures_from_sheet(rows, snapshot):
    """One month's sheet -> Figures. Raises if the layout is not what it was."""
    rows = iter(rows)
    next(rows)                                   # CONSUMO HOGARES
    header, measures = next(rows), next(rows)
    blocks = {}                                  # region -> (price col, penetration col)
    starts = sorted(k for k, v in header.items() if k > 0 and v)
    for i, start in enumerate(starts):
        label = header[start].strip()
        if label not in REGIONS:
            raise RuntimeError(f'MAPA: unknown community header {label!r}')
        end = starts[i + 1] if i + 1 < len(starts) else start + 6
        price = pen = None
        for k in range(start, end):
            m = (measures.get(k) or '').upper()
            if m.startswith('PRECIO MEDIO'):
                price = k
            elif m.startswith('PENETRACION'):
                pen = k
        if price is None:
            raise RuntimeError(f'MAPA: no price column for {label}')
        blocks[REGIONS[label]] = (price, pen)
    if len(blocks) != len(REGIONS):
        raise RuntimeError(f'MAPA: {len(blocks)} communities in the sheet, expected {len(REGIONS)}')

    out, section, seen = [], None, set()
    for row in rows:
        label = (row.get(0) or '').strip()
        if not label:
            continue
        if label in SECTIONS:
            section = label
            continue
        if label in SECTION_ENDS:
            section = None
            continue
        if section is None or label not in SECTIONS[section] or (section, label) in seen:
            continue
        seen.add((section, label))
        name, unit, mult = SECTIONS[section][label]
        for region, (pc, pen) in blocks.items():
            try:
                price = float(row.get(pc))
                penetration = float(row.get(pen)) if pen is not None else 100.0
            except (TypeError, ValueError):
                continue
            if price <= 0 or penetration < MIN_PENETRATION:
                continue
            out.append(common.Figure(name, round(price * mult, 4), unit, snapshot, region=region))
    return out


def find_file():
    page = fetch(PAGE).decode('utf-8', errors='replace')
    files = [(int(year), stem, href) for href, stem, year in FILE.findall(page)]
    if not files:
        raise RuntimeError('MAPA: no monthly CCAA file linked from the series page')
    # The newest year; within it, a "base2021" file over an older base.
    files.sort(key=lambda f: (f[0], 'base2021' in f[2]))
    year, _, href = files[-1]
    return year, href if href.startswith('http') else SITE + href


def run(months=1):
    t0 = time.time()
    year, url = find_file()
    print(f'MAPA: {year} file {url.rsplit("/", 1)[-1]}')
    wb = Workbook(fetch(url))
    sheets = [(sheet_month(n), path) for n, path in wb.sheets]
    sheets = sorted((m, p) for m, p in sheets if m is not None)
    if not sheets:
        raise RuntimeError('MAPA: no month sheets in the file')
    figures = []
    for month, path in sheets[-months:]:
        got = figures_from_sheet(wb.rows(path), month)
        print(f'  {month:%Y-%m}: {len(got)} figures')
        figures.extend(got)
    written, refused, collisions = monthly_guard.write('ES', SOURCE_NAME, 'retail', figures)
    print(f'  {len(figures)} figures, {written} written, {len(collisions)} collisions, {time.time() - t0:.0f}s')
    return written


if __name__ == '__main__':
    n = 1
    if '--months' in sys.argv:
        n = int(sys.argv[sys.argv.index('--months') + 1])
    run(n)
