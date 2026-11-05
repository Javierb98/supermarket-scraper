"""Central and Eastern European official feeds (LV, SI, CZ, HU, LT): parsers fed small
hand-made answers in each office's real format. No network, no DB."""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import cee_pxweb, csb_lv, surs_si, czso_cz, ksh_hu, stat_lt
from pipeline.catalog import products


def jsonstat(dims, values):
    """A JSON-stat 2 dataset: dims = [(id, [(code, label), ...]), ...]."""
    return {
        'id': [d for d, _ in dims],
        'size': [len(c) for _, c in dims],
        'dimension': {d: {'category': {'index': {code: i for i, (code, _) in enumerate(c)},
                                       'label': dict(c)}} for d, c in dims},
        'value': values,
    }


class CatalogueNames(unittest.TestCase):
    def test_every_mapped_name_is_in_the_catalogue(self):
        catalog = products()
        names = [p[1] for p in csb_lv.PRODUCTS + surs_si.RETAIL + surs_si.FARMGATE + czso_cz.PRODUCTS]
        names += [p[2] for p in ksh_hu.PRODUCTS + stat_lt.RETAIL['products'] + stat_lt.MARKETS['products']]
        missing = sorted({n for n in names if n.lower() not in catalog})
        self.assertEqual(missing, [])


class Latvia(unittest.TestCase):
    def test_latest_filled_month_and_eggs_by_the_dozen(self):
        stat = jsonstat(
            [('GOODS_SERVICES', [('01.1.4.8.1.701', 'Eggs, 10 pcs'), ('01.1.4.5.0.504', 'Cream cheese, 200 g'),
                                 ('01.1.7.2.4.104', 'Tomatoes, 1 kg')]),
             ('TIME', [('2026M08', '2026M08'), ('2026M09', '2026M09')])],
            [2.96, 2.87, 2.19, 2.20, 2.42, None])
        figs = {f.name: f for f in csb_lv.figures(cee_pxweb.cells(stat))}
        self.assertAlmostEqual(figs['Eggs'].price, 2.87 * 1.2)
        self.assertEqual(figs['Eggs'].unit, 'dozen')
        self.assertAlmostEqual(figs['Cream Cheese'].price, 11.0)
        self.assertEqual(figs['Tomato'].snapshot, date(2026, 8, 1))     # September blank: August kept
        self.assertAlmostEqual(figs['Tomato'].price, 2.42)


class Slovenia(unittest.TestCase):
    def test_farmgate_uses_the_price_not_the_quantity_and_eggs_per_piece(self):
        stat = jsonstat(
            [('KMETIJSKI PRIDELEK', [('096', 'Eggs'), ('011', 'Main crop potatoes')]),
             ('LETO', [('2025', '2025')]),
             ('MERITVE', [('1', 'Quantity'), ('2', 'Average price (EUR)')])],
            [212398390, 0.16, 8861465, 0.41])
        figs = {f.name: f for f in surs_si.farmgate_figures(cee_pxweb.cells(stat))}
        self.assertAlmostEqual(figs['Eggs'].price, 1.92)
        self.assertAlmostEqual(figs['Potato'].price, 0.41)
        self.assertEqual(figs['Potato'].snapshot, date(2025, 1, 1))


CZ_CSV = '''"Ukazatel","IndicatorType","Území","Uz0","Měsíce","CasM","Druh zboží","CENREP4","Hodnota","MJ_TEXT","MJ_SYMBOL"
"P","6137","Česko","CZ","srpen 2026","2026-08","Vejce slepičí čerstvá [10 ks]","01148001","44.10","koruna česká","Kč"
"P","6137","Česko","CZ","září 2026","2026-09","Vejce slepičí čerstvá [10 ks]","01148001","45.14","koruna česká","Kč"
"P","6137","Česko","CZ","září 2026","2026-09","Jogurt bílý netučný [150 g]","01146001","10.99","koruna česká","Kč"
"P","6137","Česko","CZ","září 2026","2026-09","Květák bílý celý [1 ks]","01171002","35.9","koruna česká","Kč"
"P","6137","Česko","CZ","září 2026","2026-09","Máslo [250 g]","01152001","40.00","koruna česká","Kč"
'''


class Czechia(unittest.TestCase):
    def test_quantities_from_the_bracket(self):
        figs = {f.name: f for f in czso_cz.figures(CZ_CSV)}
        self.assertAlmostEqual(figs['Eggs'].price, 45.14 * 1.2)
        self.assertEqual(figs['Eggs'].snapshot, date(2026, 9, 1))
        self.assertAlmostEqual(figs['Yogurt'].price, 10.99 / 0.15, places=3)
        self.assertEqual(figs['Cauliflower'].unit, 'unit')

    def test_a_changed_pack_size_is_skipped_not_misread(self):
        self.assertNotIn('Butter', {f.name for f in czso_cz.figures(CZ_CSV)})


HU_CSV = ('1.2.1.8. Average consumer price of selected products and services (raw data), monthly;;;;\r\n'
          'Code;Denomination;2026 August;2026 September;2026 October\r\n'
          '10001;Pork, short loin, kg;2 010;2 070;\r\n'
          '11001;Eggs, 10 pieces;810;814;\r\n'
          '14002;\'Old\' potatoes, kg;407;393;\r\n'
          '14111;Champignons, kg;1 910;1 900;\r\n')


class Hungary(unittest.TestCase):
    def test_spaced_thousands_blank_future_months_and_relabelled_items(self):
        figs = {f.name: f for f in ksh_hu.figures(HU_CSV)}
        self.assertAlmostEqual(figs['Eggs'].price, 814 * 1.2)
        self.assertEqual(figs['Potato'].snapshot, date(2026, 9, 1))
        self.assertNotIn('White Mushroom', figs)        # label changed: not trusted
        self.assertEqual(ksh_hu.number('2 070'), 2070)


LT_DATA = '''<g:DataSet>
<g:Obs><g:ObsKey><g:Value id="M9100110" value="T28"></g:Value><g:Value id="MATVNT" value="eur"></g:Value><g:Value id="LAIKOTARPIS" value="2026M10"></g:Value></g:ObsKey><g:ObsValue value="NaN"></g:ObsValue></g:Obs>
<g:Obs><g:ObsKey><g:Value id="M9100110" value="T30"></g:Value><g:Value id="MATVNT" value="eur"></g:Value><g:Value id="LAIKOTARPIS" value="2026M10"></g:Value></g:ObsKey><g:ObsValue value="0.80"></g:ObsValue></g:Obs>
<g:Obs><g:ObsKey><g:Value id="M9100110" value="T18"></g:Value><g:Value id="MATVNT" value="eur"></g:Value><g:Value id="LAIKOTARPIS" value="2026M09"></g:Value></g:ObsKey><g:ObsValue value="3.10"></g:ObsValue></g:Obs>
<g:Obs><g:ObsKey><g:Value id="M9100110" value="T18"></g:Value><g:Value id="MATVNT" value="eur"></g:Value><g:Value id="LAIKOTARPIS" value="2026M10"></g:Value></g:ObsKey><g:ObsValue value="3.22"></g:ObsValue></g:Obs>
</g:DataSet>'''


class Lithuania(unittest.TestCase):
    def test_nan_skipped_newest_month_and_eggs_by_the_dozen(self):
        figs = {f.name: f for f in stat_lt.figures(stat_lt.MARKETS, LT_DATA, '')}
        self.assertAlmostEqual(figs['Potato'].price, 0.80)     # old harvest NaN, new harvest used
        self.assertAlmostEqual(figs['Eggs'].price, 3.22 * 1.2)
        self.assertEqual(figs['Eggs'].snapshot, date(2026, 10, 1))


if __name__ == '__main__':
    unittest.main()
