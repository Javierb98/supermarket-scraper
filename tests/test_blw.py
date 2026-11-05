"""
The Swiss BLW feeds, offline: currency, units, organic split, variety
averaging, VAT basis and the Liechtenstein copy, on rows shaped like LINDAS's.

    python -m unittest tests.test_blw
"""

import os
import sys
import unittest
from datetime import date
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import blw_consumer as blw
from feeds.common import Figure
from pipeline.catalog import products

P = 'https://agriculture.ld.admin.ch/foag/product/'
CH = 'https://agriculture.ld.admin.ch/foag/sales-region/1'
DCH = 'https://agriculture.ld.admin.ch/foag/sales-region/L4-10005'
M = 'https://ld.admin.ch/time/month/'


def row(pid, price, unit='kg', region=CH, system='Nicht-Bio', currency='CHF', month='2026-09',
        cost=blw.INCL_VAT, origin=None):
    r = {'product': f'{P}{pid}', 'price': str(price), 'unit': unit, 'region': region,
         'system': system, 'currency': currency, 'date': M + month, 'cost': cost}
    if origin:
        r['origin'] = origin
    return r


def run(rows, mapping, also=None, **kw):
    with mock.patch.object(blw, 'sparql', return_value=rows):
        figs = blw.figures('x', mapping, also or {}, '2025-10', blw.REGIONS, **kw)
    return {(f.name, f.region, f.unit): f for f in figs}


class Mapping(unittest.TestCase):
    def test_every_name_is_in_the_catalogue(self):
        from feeds import blw_producer
        cat = products()
        maps = [blw.FRUIT_VEG, blw.DAIRY, blw.EGGS, blw_producer.EGGS, blw_producer.MILK]
        names = {v[0] for m in maps for v in m.values()} | set(blw.ALSO.values()) | set(blw.ALSO_DAIRY.values())
        self.assertEqual([n for n in names if n.lower() not in cat], [])


class Figures(unittest.TestCase):
    def test_varieties_are_averaged_with_spread(self):
        f = run([row(1061, 2.73), row(1070, 2.84), row(1050, 3.50)], blw.FRUIT_VEG)
        apples = f[('Apples', None, 'kg')]
        self.assertAlmostEqual(apples.price, (2.73 + 2.84 + 3.50) / 3)
        self.assertEqual((apples.low, apples.high), (2.73, 3.50))
        self.assertEqual(apples.snapshot, date(2026, 9, 1))

    def test_regions_are_named(self):
        f = run([row(1011, 4.58), row(1011, 4.70, region=DCH)], blw.FRUIT_VEG, blw.ALSO)
        self.assertEqual(f[('Tomato', 'German-speaking Switzerland', 'kg')].price, 4.70)
        self.assertEqual(f[('Vine Tomatoes', None, 'kg')].price, 4.58)

    def test_dairy_organic_row_is_not_conventional(self):
        f = run([row(292, 1.71, unit='Liter', system='Konventionell'),
                 row(292, 1.89, unit='Liter', system='Bio')], blw.DAIRY)
        self.assertEqual(f[('Whole Milk', None, 'l')].price, 1.71)

    def test_pieces_and_packs(self):
        f = run([row(1444, 4.13, unit='Stück'), row(1030, 1.41, unit='Bund')], blw.FRUIT_VEG)
        self.assertAlmostEqual(f[('Mini Romaine', None, 'unit')].price, 4.13 / 3)
        self.assertEqual(f[('Radish', None, 'unit')].price, 1.41)

    def test_eggs_in_rappen_become_francs_a_dozen(self):
        f = run([row(163, 66.57, unit='Stück', currency='Rappen', system='Boden, Freiland & Bio')], blw.EGGS)
        self.assertAlmostEqual(f[('Eggs', None, 'dozen')].price, 7.9884)

    def test_vat_basis_preferred(self):
        from feeds import blw_producer as bp
        swiss = 'https://agriculture.ld.admin.ch/foag/product-origin/1'
        rows = [row(271, 76.15, currency='Rappen', system='NA', cost=blw.INCL_VAT, origin=swiss),
                row(271, 74.22, currency='Rappen', system='NA', cost=blw.EXCL_VAT, origin=swiss),
                row(271, 84.03, currency='Rappen', system='NA', cost=blw.EXCL_VAT,
                    origin='https://agriculture.ld.admin.ch/foag/product-origin/3')]
        f = run(rows, bp.MILK, want_vat=blw.EXCL_VAT, origins=bp.SWISS_ORIGIN)
        self.assertAlmostEqual(f[('Raw Cow Milk', None, 'l')].price, 0.7422 * 1.03)

    def test_euro_cents_are_refused(self):
        self.assertIsNone(blw.to_francs(30.0, 'Eurocent'))


class Liechtenstein(unittest.TestCase):
    def test_takes_german_speaking_then_national(self):
        d = date(2026, 9, 1)
        figs = [Figure('Tomato', 4.58, 'kg', d), Figure('Tomato', 4.70, 'kg', d, 'German-speaking Switzerland'),
                Figure('Tomato', 4.10, 'kg', d, 'French-speaking Switzerland'), Figure('Eggs', 7.99, 'dozen', d)]
        li = {f.name: f for f in blw.for_liechtenstein(figs)}
        self.assertEqual(li['Tomato'].price, 4.70)
        self.assertIsNone(li['Tomato'].region)
        self.assertEqual(li['Eggs'].price, 7.99)

    def test_months_back(self):
        self.assertEqual(blw.months_back(12, date(2026, 11, 4)), '2025-11')
        self.assertEqual(blw.months_back(1, date(2026, 1, 15)), '2025-12')


if __name__ == '__main__':
    unittest.main()
