"""
New Zealand: monthly average retail food prices from Stats NZ.

The "Selected price indexes" release carries, besides the indexes, the
Food Price Index's weighted average prices: about 150 items, national,
monthly, in NZD, from Stats NZ's own shop survey. One CSV per release.

    python feeds/statsnz.py              latest month
    python feeds/statsnz.py --months 6   the last six months

The release comes out in the middle of the following month, so the newest
file is last month's or the month before. Its address is predictable, so the
feed asks for the CSV directly rather than crawling the site, and keeps to
the 10-second crawl delay robots.txt asks for.

Licence: Creative Commons Attribution 4.0 International, attribution
"Stats NZ". https://www.stats.govt.nz/about-us/copyright/
"""

import csv
import io
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import common, monthly_guard

SOURCE_NAME = 'Stats NZ, selected price indexes'
GROUP = 'Food Price Index Selected Monthly Weighted Average Prices for New Zealand'
URL = ('https://www.stats.govt.nz/assets/Uploads/Selected-price-indexes/'
       'Selected-price-indexes-{Month}-{year}/Download-data/selected-price-indexes-{month}-{year}.csv')
CRAWL_DELAY = 10
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']

# Stats NZ series -> (catalogue name, unit, quantity the price is for, in that unit).
# Only items that are the same thing a farm sells; group averages ("Lettuce",
# "Grapes, green or red"), processed and frozen goods are left out.
SERIES = {
    'CPIM.SAP0100': ('Oranges', 'kg', 1.0),                 # Oranges, 1kg
    'CPIM.SAP0101': ('Banana', 'kg', 1.0),                  # Bananas, 1kg
    'CPIM.SAP0102': ('Apples', 'kg', 1.0),                  # Apples, 1kg
    'CPIM.SAP0103': ('Kiwi', 'kg', 1.0),                    # Kiwifruit, 1kg
    'CPIM.SAP0107': ('Broccoli', 'kg', 1.0),
    'CPIM.SAP0109': ('Tomato', 'kg', 1.0),
    'CPIM.SAP0110': ('Carrot', 'kg', 1.0),
    'CPIM.SAP0111': ('White Mushroom', 'kg', 1.0),          # Mushrooms, 1kg (button)
    'CPIM.SAP0112': ('Potato', 'kg', 1.0),
    'CPIM.SAP0115': ('Fresh Sirloin', 'kg', 1.0),           # Beef steak - porterhouse/sirloin
    'CPIM.SAP0116': ('Ground Beef', 'kg', 1.0),             # Beef - mince
    'CPIM.SAP0117': ('Pork Chops', 'kg', 1.0),              # Pork - loin chops
    'CPIM.SAP0118': ('Lamb Chops', 'kg', 1.0),
    'CPIM.SAP0127': ('Whole Milk', 'l', 2.0),               # Milk - standard homogenised, 2 litres
    'CPIM.SAP0129': ('Cheddar Cheese', 'kg', 1.0),          # Cheese - mild cheddar, 1kg
    'CPIM.SAP0130': ('Eggs', 'dozen', 1.0),                 # Eggs, dozen
    'CPIM.SAP0131': ('Butter', 'kg', 0.5),                  # Butter - salted, 500g
    'CPIM.SAP0148': ('Chicken Breast', 'kg', 1.0),
    'CPIM.SAP0152': ('Avocado', 'kg', 1.0),                 # Avocado, 1kg
    'CPIM.SAP0154': ('Green Beans', 'kg', 1.0),             # Beans, 1kg (fresh green)
    'CPIM.SAP0160': ('Bell Pepper', 'kg', 1.0),             # Capsicums, green, else red
    'CPIM.SAP0161': ('Cauliflower', 'kg', 1.0),
    'CPIM.SAP0162': ('Celery', 'kg', 1.0),                  # discontinued 2024-12, dropped as stale
    'CPIM.SAP0168': ('Whole Chicken', 'kg', 1.5),           # Chicken, whole, frozen, No. 15 (1.5 kg)
    'CPIM.SAP0177': ('Corned Beef Fresh', 'kg', 1.0),
    'CPIM.SAP0178': ('Zucchini', 'kg', 1.0),                # Courgettes
    'CPIM.SAP0180': ('Cream', 'l', 0.3),                    # Cream, 300ml
    'CPIM.SAP0181': ('Cucumber', 'kg', 1.0),
    'CPIM.SAP0197': ('Honey', 'kg', 0.5),                   # Honey, clover, creamed, 500g
    'CPIM.SAP0205': ('Sweet Potato', 'kg', 1.0),            # Kumara
    'CPIM.SAP0207': ('Mandarin Oranges Fresh', 'kg', 1.0),
    'CPIM.SAP0216': ('Onion', 'kg', 1.0),
    'CPIM.SAP0220': ('Parsnip', 'kg', 1.0),
    'CPIM.SAP0224': ('Pears', 'kg', 1.0),
    'CPIM.SAP0226': ('Pineapple', 'kg', 1.0),               # Pineapple, 1kg
    'CPIM.SAP0231': ('Pumpkin', 'kg', 1.0),
}


def month_start(period):
    """'2026.09' -> date(2026, 9, 1). Stats NZ writes October as '2026.1'."""
    year, _, month = period.partition('.')
    m = int(month.ljust(2, '0')) if len(month) == 1 else int(month)
    return date(int(year), m, 1)


def download(today=None):
    """The newest release's CSV text, trying last month then the two before."""
    today = today or date.today()
    y, m = today.year, today.month
    last_error = None
    for back in range(1, 4):
        mm, yy = m - back, y
        while mm < 1:
            mm, yy = mm + 12, yy - 1
        name = MONTHS[mm - 1]
        url = URL.format(Month=name, month=name.lower(), year=yy)
        try:
            body = common.get(url, retries=1, pause=CRAWL_DELAY, timeout=120)
            print(f'Stats NZ: {name} {yy} release')
            return body.decode('utf-8-sig')
        except Exception as e:      # 404 until the release is out
            last_error = e
            time.sleep(CRAWL_DELAY)
    raise RuntimeError(f'no Stats NZ selected price indexes CSV found: {last_error}')


def figures_from_csv(text, months=1):
    """The mapped series' latest `months` months as Figures; stale series dropped."""
    by_series = {}
    for row in csv.DictReader(io.StringIO(text)):
        if row.get('Group') != GROUP or row.get('Series_reference') not in SERIES:
            continue
        try:
            value = float(row['Data_value'])
        except (TypeError, ValueError):
            continue
        by_series.setdefault(row['Series_reference'], {})[month_start(row['Period'])] = value

    if not by_series:
        return []

    newest = max(max(v) for v in by_series.values())
    out = []
    for ref, values in by_series.items():
        name, unit, qty = SERIES[ref]
        periods = sorted(values)[-months:]
        # A series that stopped being collected (celery, after 2024) is not
        # this month's price, however recent it once was.
        if (newest.year - periods[-1].year) * 12 + newest.month - periods[-1].month > 2:
            continue
        for p in periods:
            out.append(common.Figure(name, round(values[p] / qty, 4), unit, p))
    return out


def run(months=1):
    t0 = time.time()
    figures = figures_from_csv(download(), months)
    if not figures:
        raise RuntimeError('Stats NZ CSV had none of the mapped series; the layout may have changed')
    written, refused, collisions = monthly_guard.write('NZ', SOURCE_NAME, 'retail', figures)
    print(f'  {len(figures)} figures, {written} written, {len(collisions)} collisions, {time.time() - t0:.0f}s')
    return written


if __name__ == '__main__':
    n = 1
    if '--months' in sys.argv:
        n = int(sys.argv[sys.argv.index('--months') + 1])
    run(n)
