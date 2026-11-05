"""
The EU agri-food portal feed, offline: stages, units, variety handling,
country codes and recency, on rows shaped like the API's.

    python -m unittest tests.test_eu_agrifood
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import eu_agrifood as eu
from pipeline.catalog import products

TODAY = date(2026, 11, 4)


def fv(ms, variety, stage, price, begin='19/10/2026', period='Week'):
    return {'memberStateCode': ms, 'beginDate': begin, 'price': f'€{price}', 'unit': '€/100Kg',
            'periodType': period, 'variety': variety, 'productStage': stage, 'isCalculated': 'N'}


def figs(points):
    out = eu.latest_figures(points, TODAY)
    return {(c, s, f.name): f for (c, s), fs in out.items() for f in fs}


class Mapping(unittest.TestCase):
    def test_every_name_is_in_the_catalogue(self):
        cat = products()
        names = set(eu.FV_PRODUCTS.values()) | {v for v in eu.FV_VARIETIES.values() if v} | {o[2] for o in eu.OTHER}
        self.assertEqual(sorted(n for n in names if n.lower() not in cat), [])

    def test_varieties(self):
        self.assertEqual(eu.fv_product('Apples - Gala'), ('Apples', False))
        self.assertEqual(eu.fv_product('Apples - National weighted average of all types and varieties'), ('Apples', True))
        self.assertEqual(eu.fv_product('Tomatoes - Cherry/Special'), ('Cherry Tomato', True))
        self.assertIsNone(eu.fv_product('Tomatoes - All types and varieties'))
        self.assertIsNone(eu.fv_product('Organic-Apples - Gala'))
        self.assertIsNone(eu.fv_product('Apples for processing - All types and varieties'))
        self.assertIsNone(eu.fv_product('Nectarines - Flat'))
        self.assertEqual(eu.fv_product('Bananas – EU – All types and varieties'), ('Banana', True))
        self.assertEqual(eu.fv_product('Ware potatoes, size that do not pass ... below 10 kg - All types and varieties'),
                         ('Potato', True))


class Figures(unittest.TestCase):
    def test_stages_units_and_greece(self):
        rows = [fv('DE', 'Apples - Gala', 'Farmgate price', '62.31'),
                fv('DE', 'Apples - Gala', 'Ex-packaging station price', '69.11'),
                fv('EL', 'Tomatoes - Round', 'Retail selling price', '153.30'),
                fv('BG', 'Tomatoes - Round', 'Retail selling price', '99')]
        f = figs(eu.fv_points(rows))
        self.assertAlmostEqual(f[('DE', 'farmgate', 'Apples')].price, 0.6231)
        self.assertAlmostEqual(f[('DE', 'wholesale', 'Apples')].price, 0.6911)
        self.assertAlmostEqual(f[('GR', 'retail', 'Tomato')].price, 1.533)
        self.assertNotIn(('BG', 'retail', 'Tomato'), f)

    def test_whole_product_row_beats_variety_mean(self):
        rows = [fv('DE', 'Apples - Gala', 'Farmgate price', '60'),
                fv('DE', 'Apples - Elstar', 'Farmgate price', '70'),
                fv('DE', 'Apples - National weighted average of all types and varieties', 'Farmgate price', '52')]
        self.assertAlmostEqual(figs(eu.fv_points(rows))[('DE', 'farmgate', 'Apples')].price, 0.52)

    def test_variety_mean_with_spread(self):
        rows = [fv('PL', 'Pears - Conference', 'Ex-packaging station price', '100'),
                fv('PL', 'Pears - Williams', 'Ex-packaging station price', '120')]
        p = figs(eu.fv_points(rows))[('PL', 'wholesale', 'Pears')]
        self.assertAlmostEqual(p.price, 1.10)
        self.assertEqual((p.low, p.high), (1.0, 1.2))

    def test_retail_buying_preferred_and_latest_week(self):
        rows = [fv('DE', 'Apples - Gala', 'Ex-packaging station price', '69', begin='19/10/2026'),
                fv('DE', 'Apples - Gala', 'Retail buying price', '120', begin='21/09/2026'),
                fv('DE', 'Apples - Gala', 'Retail buying price', '128', begin='28/09/2026'),
                fv('DE', 'Apples - Gala', 'Retail buying price', '125', begin='01/09/2026', period='Month')]
        a = figs(eu.fv_points(rows))[('DE', 'wholesale', 'Apples')]
        self.assertAlmostEqual(a.price, 1.28)
        self.assertEqual(a.snapshot, date(2026, 9, 28))

    def test_stale_is_dropped(self):
        rows = [fv('IT', 'Strawberries - All types and varieties', 'Farmgate price', '400', begin='09/06/2026')]
        self.assertEqual(figs(eu.fv_points(rows)), {})

    def test_milk_eggs_poultry(self):
        milk = [{'memberStateCode': 'DE', 'beginDate': '01/10/2026', 'price': '€43.20', 'unit': '100KG', 'product': 'Raw milk'},
                {'memberStateCode': 'DE', 'beginDate': '01/10/2026', 'price': '€60.00', 'unit': '100KG', 'product': 'Organic raw milk'}]
        eggs = [{'memberStateCode': 'DE', 'beginDate': '19/10/2026', 'price': '€378.84', 'farmingMethod': 'Free range'},
                {'memberStateCode': 'DE', 'beginDate': '19/10/2026', 'price': '€227.89', 'farmingMethod': 'Barn'},
                {'memberStateCode': 'IT', 'beginDate': '19/10/2026', 'price': '€340.47', 'farmingMethod': 'Barn'},
                {'memberStateCode': 'IT', 'beginDate': '19/10/2026', 'price': '€302.77', 'farmingMethod': 'Cage'}]
        poultry = [{'memberStateCode': 'HU', 'beginDate': '19/10/2026', 'price': '€1,244.66',
                    'productName': 'Whole broiler (65%)', 'priceType': 'Selling price'}]
        pts = (eu.other_points('rawMilk/prices', milk) + eu.other_points('poultry/egg/prices', eggs)
               + eu.other_points('poultry/prices', poultry))
        f = figs(pts)
        self.assertAlmostEqual(f[('DE', 'farmgate', 'Raw Cow Milk')].price, 0.432 * 1.03)
        self.assertEqual(f[('DE', 'farmgate', 'Raw Cow Milk')].unit, 'l')
        self.assertAlmostEqual(f[('DE', 'wholesale', 'Eggs')].price, 3.7884 * 0.75)   # free range, not barn
        self.assertAlmostEqual(f[('IT', 'wholesale', 'Eggs')].price, 3.4047 * 0.75)   # barn, cage never
        self.assertAlmostEqual(f[('HU', 'wholesale', 'Whole Chicken')].price, 12.4466)

    def test_converted_to_local_currency_at_the_period_mean(self):
        rates = {'HUF': {date(2026, 10, 19): 400.0, date(2026, 10, 20): 410.0, date(2026, 10, 27): 999.0},
                 'PLN': {date(2026, 9, 30): 4.25}}
        pts = [('HU', 'Eggs', 'wholesale', 'dozen', 0, 'week', date(2026, 10, 19), 2.0, True),
               ('PL', 'Raw Cow Milk', 'farmgate', 'l', 0, 'month', date(2026, 10, 1), 0.45, True),
               ('DE', 'Eggs', 'wholesale', 'dozen', 0, 'week', date(2026, 10, 19), 2.8, True),
               ('SE', 'Eggs', 'wholesale', 'dozen', 0, 'week', date(2026, 10, 19), 2.2, True)]
        out = {p[0]: p[7] for p in eu.to_local(pts, rates)}
        self.assertAlmostEqual(out['HU'], 2.0 * 405.0)     # mean of that week's rates only
        self.assertAlmostEqual(out['PL'], 0.45 * 4.25)     # no October rate yet: latest before
        self.assertEqual(out['DE'], 2.8)
        self.assertNotIn('SE', out)                        # no rate, no figure

    def test_national_feeds_keep_their_pairs(self):
        self.assertIn(('SI', 'farmgate'), eu.SKIP)
        self.assertIn(('CZ', 'retail'), eu.SKIP)

    def test_euros(self):
        self.assertEqual(eu.euros('€1,013.83'), 1013.83)
        self.assertIsNone(eu.euros(''))
        self.assertIsNone(eu.euros('€0.00'))


if __name__ == '__main__':
    unittest.main()
