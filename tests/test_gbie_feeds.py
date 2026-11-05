"""
Offline tests for the United Kingdom and Ireland feeds: parsing and unit
conversion on small copies of the real files' shapes. No network, no DB.

    venv/bin/python -m unittest tests.test_gbie_feeds
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import defra_wholesale, ons_shopping, cso_ie
from pipeline.catalog import products


DEFRA_CSV = """category,item,variety,date,price,unit
fruit,apples,bramleys_seedling,2026-10-26,1.24,kg
fruit,apples,gala,2026-10-26,1.31,kg
fruit,apples,braeburn,2026-10-26,1.53,kg
fruit,apples,other_late_season,2026-07-20,1.79,kg
vegetable,cauliflower,all,2026-10-26,1.18,head
vegetable,coriander,coriander,2026-10-26,2,kg
vegetable,watercress,pillow_packs,2019-08-30,10.14,kg
vegetable,tomatoes,round,2026-10-19,1.42,kg
vegetable,tomatoes,round,2026-10-26,1.35,kg
"""

ONS_AVG = '''"ID_NAME","CONSUMPTION_SEGMENT_CODE","2026-08-01","2026-09-01"
"Butter - dairy (block or tub)","CP0115101",2.3,2.25
"Eggs - free-range","CP0114701",3.92,3.95
"Milk - cow's (whole, fresh)","CP0114101",1.87,1.86
"Peppers","CP0117101",1.6,1.65
"Honey","CP0118301",2.3,
'''
ONS_META = '''ID_START,ID_NAME,CONSUMPTION_SEGMENT_CODE,WEIGHT_SIZE,AVERAGE_PRICE
202502,Butter - dairy (block or tub),CP0115101,250 g,2.25
202502,Eggs - free-range,CP0114701,12 pack,3.95
202502,"Milk - cow's (whole, fresh)",CP0114101,2272 ml,1.86
202502,Peppers,CP0117101,each,1.65
202502,Honey,CP0118301,400 g,2.22
'''


def cso_dataset():
    items = ['10750', '10370', '11090']
    labels = {'10750': 'Butter per lb', '10370': 'Uncooked chicken medium size 1.6kg', '11090': 'Potatoes 2.5 kg'}
    months = ['202608', '202609']
    # value order: STATISTIC(1) x month x item, row-major
    values = [4.304, 6.068, 3.638,
              4.238, None, 3.665]
    return {
        'id': ['STATISTIC', 'TLIST(M1)', 'C02363V03422'],
        'size': [1, 2, 3],
        'dimension': {
            'STATISTIC': {'category': {'index': ['CPM12'], 'label': {'CPM12': 'National Average Price'}}},
            'TLIST(M1)': {'category': {'index': months, 'label': {m: m for m in months}}},
            'C02363V03422': {'category': {'index': items, 'label': labels}},
        },
        'value': values,
    }


class Defra(unittest.TestCase):
    def setUp(self):
        self.figs = {f.name: f for f in defra_wholesale.figures_from(defra_wholesale.read_rows(DEFRA_CSV))}

    def test_apples_mean_of_latest_week_dessert_varieties(self):
        a = self.figs['Apples']
        self.assertAlmostEqual(a.price, (1.31 + 1.53) / 2, places=4)   # no Bramley, no stale late-season
        self.assertEqual((a.low, a.high, a.snapshot), (1.31, 1.53, date(2026, 10, 26)))

    def test_per_head_stays_per_unit(self):
        self.assertEqual(self.figs['Cauliflower'].unit, 'unit')

    def test_latest_week_and_skips(self):
        self.assertEqual(self.figs['Tomato'].price, 1.35)
        self.assertNotIn('Watercress', self.figs)        # stale
        self.assertNotIn('Cilantro', self.figs)          # bunch priced, not mapped


class ONS(unittest.TestCase):
    def test_pack_sizes_convert(self):
        figs, problems = ons_shopping.parse(ONS_AVG, ONS_META)
        f = {x.name: x for x in figs}
        self.assertAlmostEqual(f['Butter'].price, 9.0)                    # 250 g -> kg
        self.assertAlmostEqual(f['Eggs'].price, 3.95)                     # 12 pack -> dozen
        self.assertAlmostEqual(f['Whole Milk'].price, 1.86 / 2.272, 4)    # 4 pints -> l
        self.assertEqual((f['Bell Pepper'].unit, f['Bell Pepper'].price), ('unit', 1.65))
        self.assertEqual(f['Butter'].snapshot, date(2026, 9, 1))
        self.assertEqual(f['Honey'].snapshot, date(2026, 8, 1))           # latest month with a value

    def test_unreadable_size_is_skipped(self):
        self.assertIsNone(ons_shopping.per_unit(2.0, 'each', 'kg'))
        self.assertIsNone(ons_shopping.per_unit(2.0, '6 pack', 'kg'))


class CSO(unittest.TestCase):
    def test_conversions_and_missing_values(self):
        figs, problems = cso_ie.parse(cso_dataset())
        f = {x.name: x for x in figs}
        self.assertAlmostEqual(f['Butter'].price, 4.238 / 0.45359237, 3)  # per lb -> per kg
        self.assertAlmostEqual(f['Whole Chicken'].price, 6.068 / 1.6, 4)  # Sept empty -> August
        self.assertEqual(f['Whole Chicken'].snapshot, date(2026, 8, 1))
        self.assertAlmostEqual(f['Potato'].price, 3.665 / 2.5, 4)

    def test_relabelled_item_is_skipped(self):
        ds = cso_dataset()
        ds['dimension']['C02363V03422']['category']['label']['10750'] = 'Butter per 500g'
        figs, problems = cso_ie.parse(ds)
        self.assertNotIn('Butter', {x.name for x in figs})


class Catalogue(unittest.TestCase):
    def test_every_mapped_name_is_in_the_catalogue(self):
        cat = products()
        names = [m[1] for m in defra_wholesale.MAP] + [v[0] for v in ons_shopping.MAP.values()] \
            + [v[1] for v in cso_ie.ITEMS.values()]
        self.assertEqual([n for n in names if n.lower() not in cat], [])


if __name__ == '__main__':
    unittest.main()
