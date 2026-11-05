"""BLS feed: flat-file parsing, regions, unit conversion. No network, no DB."""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import bls
from pipeline.catalog import products

FLAT = '\n'.join([
    'series_id        \tyear\tperiod\t       value\tfootnote_codes',
    'APU0000712112    \t2026\tM08\t       0.990\t',
    'APU0000712112    \t2026\tM09\t       0.989\t',
    'APU0100712112    \t2026\tM09\t       1.100\t',
    'APU0300709112    \t2026\tM09\t       4.000\t',
    'APU0000708111    \t2026\tM09\t       2.272\t',
    'APU0400712112    \t2026\tM09\t           -\tX',
    'APU0000711415    \t2026\tM09\t       2.840\t',
    'APU0000704211    \t2026\tM09\t       4.905\t',      # not mapped (bone-in chops)
])


class BLS(unittest.TestCase):
    def test_every_mapped_name_is_in_the_catalogue(self):
        for name, unit, _ in bls.ITEMS.values():
            self.assertIn(name.lower(), products(), name)

    def test_parse_and_convert(self):
        got = {(f.name, f.region): f for f in bls.figures_from(bls.parse_flat(FLAT))}
        self.assertEqual(set(got), {('Potato', None), ('Potato', 'Northeast'), ('Whole Milk', 'South'),
                                    ('Eggs', None), ('Strawberries', None)})
        self.assertAlmostEqual(got[('Potato', None)].price, 0.989 * 2.20462, places=3)   # per lb -> per kg
        self.assertAlmostEqual(got[('Whole Milk', 'South')].price, 4.0 / 3.785411784, places=4)
        self.assertEqual(got[('Eggs', None)].unit, 'dozen')
        self.assertAlmostEqual(got[('Strawberries', None)].price, 2.84 / 0.340194, places=2)  # 12 oz
        self.assertEqual(got[('Potato', None)].snapshot, date(2026, 9, 1))


if __name__ == '__main__':
    unittest.main()
