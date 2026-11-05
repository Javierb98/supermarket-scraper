"""Stats NZ feed: CSV reading, unit conversion, stale series. No network, no DB."""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import statsnz
from pipeline.catalog import products

G = statsnz.GROUP
CSV = '\n'.join([
    '"Series_reference","Period","Data_value","STATUS","UNITS","Subject","Group","Series_title_1","Series_title_2","Series_title_3"',
    f'"CPIM.SAP0111","2026.08",12.65,"FINAL","Dollars","CPI","{G}","Mushrooms, 1kg",NA,NA',
    f'"CPIM.SAP0111","2026.09",12.87,"FINAL","Dollars","CPI","{G}","Mushrooms, 1kg",NA,NA',
    f'"CPIM.SAP0131","2026.09",7.62,"FINAL","Dollars","CPI","{G}","Butter - salted, 500g",NA,NA',
    f'"CPIM.SAP0127","2026.09",5.05,"FINAL","Dollars","CPI","{G}","Milk - standard homogenised, 2 litres",NA,NA',
    f'"CPIM.SAP0162","2024.12",4.69,"FINAL","Dollars","CPI","{G}","Celery, 1kg",NA,NA',
    '"CPIM.SE901","2026.09",1200,"FINAL","Index","CPI","Food Price Index Level 1","Food",NA,NA',
])


class StatsNZ(unittest.TestCase):
    def test_every_mapped_name_is_in_the_catalogue(self):
        for name, unit, _ in statsnz.SERIES.values():
            self.assertIn(name.lower(), products(), name)
            self.assertIn(unit, ('kg', 'l', 'dozen', 'unit'))

    def test_latest_month_converted_and_stale_dropped(self):
        got = {f.name: f for f in statsnz.figures_from_csv(CSV)}
        self.assertEqual(set(got), {'White Mushroom', 'Butter', 'Whole Milk'})   # celery stopped in 2024
        self.assertEqual(got['White Mushroom'].price, 12.87)
        self.assertEqual(got['White Mushroom'].snapshot, date(2026, 9, 1))
        self.assertAlmostEqual(got['Butter'].price, 15.24)      # 500 g -> per kg
        self.assertAlmostEqual(got['Whole Milk'].price, 2.525)  # 2 l -> per litre
        self.assertIsNone(got['Butter'].region)

    def test_months(self):
        got = [f for f in statsnz.figures_from_csv(CSV, months=2) if f.name == 'White Mushroom']
        self.assertEqual(sorted(f.snapshot for f in got), [date(2026, 8, 1), date(2026, 9, 1)])

    def test_period(self):
        self.assertEqual(statsnz.month_start('2026.10'), date(2026, 10, 1))
        self.assertEqual(statsnz.month_start('2026.1'), date(2026, 10, 1))


if __name__ == '__main__':
    unittest.main()
