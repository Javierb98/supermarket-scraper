"""
Slovenia: two annual tables from the Statistical Office (SURS), SiStat.

1. 0411005S, average annual retail prices of goods and services -> 'retail'.
   SURS stopped the monthly series (0411001S) in 2017; the annual one is the
   only current retail price list, published each January for the year
   before. National, euros.

2. 1505000S, quantities and average prices of purchased agricultural
   products -> 'farmgate'. What enterprises paid farmers, per kilo for crops
   and honey, per litre for milk, per piece for eggs (so x12 for a dozen),
   per kilo live weight for animals (not used: no farm sells a live bull by
   the kilo on the site). Annual, published in February-October for the year
   before.

Both are annual, so the snapshot is the first day of the year the average is
for (2025 -> 2025-01-01), as for the other annual feeds. The site should read
the date as "the 2025 average", not "a price taken on 1 January".

Items left out: group headings, processed goods, white/sour cabbage (no
catalogue product), "Lettuce" (the catalogue has only specific lettuces),
"Chicory" (radič; cannot tell radicchio from sugar-loaf chicory), industrial
apples, pears and grapes (sold for processing, not the same product), and
"Boned beef"/"Beef with bone" (cut unstated).

    python feeds/surs_si.py

Licence: SURS data may be reused freely with attribution
(https://www.stat.si/StatWeb/en/LegalNotice).
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write
from feeds.cee_pxweb import query, latest

BASE = 'https://pxweb.stat.si/SiStatData/api/v1/en/Data/'
RETAIL_TABLE = '0411005S'
FARMGATE_TABLE = '1505000S'
RETAIL_SOURCE = 'SURS Slovenia, table 0411005S (annual average)'
FARMGATE_SOURCE = 'SURS Slovenia, table 1505000S (annual average)'

# (SURS code, catalogue name, unit, factor)
RETAIL = [
    ('0112402000', 'Chicken Breast',       'kg',    1.0),   # boned chicken meat
    ('0114102000', 'Whole Milk',           'l',     1.0),   # UHT whole milk
    ('0114401000', 'Yogurt',               'kg',    1.0),
    ('0114501000', 'Cheese',               'kg',    1.0),
    ('0114505000', 'Fresh Cottage Cheese', 'kg',    1.0),   # skuta (curd)
    ('0114701000', 'Eggs',                 'dozen', 1.2),   # 10 eggs
    ('0115101000', 'Butter',               'kg',    1.0),
    ('0115301000', 'Olive Oil',            'l',     1.0),
    ('0116101000', 'Lemons',               'kg',    1.0),
    ('0116102000', 'Oranges',              'kg',    1.0),
    ('0116103000', 'Apples',               'kg',    1.0),
    ('0116105000', 'Banana',               'kg',    1.0),
    ('0116106000', 'Peaches',              'kg',    1.0),
    ('0116107000', 'Strawberries',         'kg',    1.0),
    ('0117103000', 'Cauliflower',          'kg',    1.0),
    ('0117110000', 'Tomato',               'kg',    1.0),
    ('0117111000', 'Onion',                'kg',    1.0),
    ('0117113000', 'Carrot',               'kg',    1.0),
    ('0117114000', 'Garlic',               'kg',    1.0),
    ('0117401000', 'Potato',               'kg',    1.0),
    ('0118201000', 'Honey',                'kg',    1.0),   # flower honey
]

FARMGATE = [
    ('011', 'Potato',          'kg',    1.0),   # main crop potatoes
    ('014', 'Green Beans',     'kg',    1.0),
    ('015', 'Onion',           'kg',    1.0),
    ('016', 'Garlic',          'kg',    1.0),
    ('017', 'Leek',            'kg',    1.0),
    ('019', 'Napa Cabbage',    'kg',    1.0),
    ('020', 'Savoy Cabbage',   'kg',    1.0),
    ('021', 'Red Cabbage',     'kg',    1.0),
    ('022', 'Beetroot',        'kg',    1.0),
    ('023', 'Cauliflower',     'kg',    1.0),
    ('024', 'Carrot',          'kg',    1.0),
    ('025', 'Tomato',          'kg',    1.0),
    ('026', 'Bell Pepper',     'kg',    1.0),   # capsicum
    ('028', 'Endive',          'kg',    1.0),
    ('031', 'Cucumber',        'kg',    1.0),   # slicing cucumbers
    ('032', 'Pickling Cucumbers', 'kg', 1.0),
    ('033', 'Zucchini',        'kg',    1.0),
    ('034', 'Spinach',         'kg',    1.0),
    ('035', 'Asparagus',       'kg',    1.0),
    ('036', 'White Mushroom',  'kg',    1.0),   # cultivated mushrooms
    ('042', 'Plums',           'kg',    1.0),
    ('043', 'Apples',          'kg',    1.0),   # dessert apples
    ('045', 'Pears',           'kg',    1.0),   # dessert pears
    ('047', 'Cherries',        'kg',    1.0),   # sweet cherries
    ('049', 'Peaches',         'kg',    1.0),   # dessert peaches and nectarines
    ('051', 'Persimmon',       'kg',    1.0),   # kaki
    ('052', 'Strawberries',    'kg',    1.0),
    ('096', 'Eggs',            'dozen', 12.0),  # per egg
    ('098', 'Raw Cow Milk',    'l',     1.0),   # cows' milk bought by dairies
    ('100', 'Honey',           'kg',    1.0),   # flower honey
]


def year(code):
    return date(int(code), 1, 1)


def retail_figures(rows):
    got = latest(rows, 'IZDELKI IN STORITVE', 'LETO', year)
    return [Figure(n, round(got[c][1] * f, 4), u, got[c][0]) for c, n, u, f in RETAIL if c in got]


def farmgate_figures(rows):
    prices = [r for r in rows if r['MERITVE'][0] == '2']       # 2 = average price; 1 = quantity
    got = latest(prices, 'KMETIJSKI PRIDELEK', 'LETO', year)
    return [Figure(n, round(got[c][1] * f, 4), u, got[c][0]) for c, n, u, f in FARMGATE if c in got]


def fetch_retail():
    return query(BASE + RETAIL_TABLE + '.px', [
        {'code': 'IZDELKI IN STORITVE', 'selection': {'filter': 'item', 'values': [p[0] for p in RETAIL]}},
        {'code': 'LETO', 'selection': {'filter': 'top', 'values': ['2']}},
    ])


def fetch_farmgate():
    return query(BASE + FARMGATE_TABLE + '.px', [
        {'code': 'KMETIJSKI PRIDELEK', 'selection': {'filter': 'item', 'values': [p[0] for p in FARMGATE]}},
        {'code': 'LETO', 'selection': {'filter': 'top', 'values': ['2']}},
        {'code': 'MERITVE', 'selection': {'filter': 'item', 'values': ['2']}},
    ])


def show(figs):
    for f in figs:
        print(f'  {f.name:22} {f.price:>9.2f} EUR/{f.unit:5} {f.snapshot}')


def run():
    retail = retail_figures(fetch_retail())
    farmgate = farmgate_figures(fetch_farmgate())
    if not retail and not farmgate:
        raise RuntimeError('SURS returned no prices — the tables or the API have changed')
    show(retail)
    write('SI', RETAIL_SOURCE, 'retail', retail)
    show(farmgate)
    write('SI', FARMGATE_SOURCE, 'farmgate', farmgate)
    return len(retail) + len(farmgate)


if __name__ == '__main__':
    run()
