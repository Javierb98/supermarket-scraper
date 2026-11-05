"""
Latvia: average retail prices of selected goods, monthly, from the Central
Statistical Bureau (CSB), table PCC010m.

About 150 items, national only, euros, published a few weeks after the month.
Prices are per kilo unless the item says otherwise ("Eggs, 10 pcs",
"Cream cheese, 200 g", "Avocados, 1 piece"), and the factor column turns those
into the catalogue's unit.

Items left out on purpose: group averages and processed goods no farm sells
alike (sausages, canned or frozen goods, "Minced meat" of unstated animal),
plain "Cabbage" (the catalogue has only red, savoy and napa), "Grapes"
(the catalogue splits red and green), "Chicken legs" (whole leg quarters; the
catalogue has thighs and drumsticks separately) and "Kefir" (no catalogue
product; "Fermented Milk" is a different thing on a farm's list).

    python feeds/csb_lv.py

Licence: CSB open data, reuse with the source named (CC BY 4.0 per SOURCES.md;
terms page https://stat.gov.lv/en/terms).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write
from feeds.cee_pxweb import query, latest, month

URL = 'https://data.stat.gov.lv/api/v1/en/OSP_PUB/START/VEK/PC/PCC/PCC010m'
SOURCE_NAME = 'CSB Latvia, table PCC010m'
MONTHS = 4          # look back this far for an item missing in the latest month

# (CSB code, catalogue name, unit, factor: CSB price x factor = price per unit)
PRODUCTS = [
    ('01.1.2.2.1.103', 'Ground Beef',          'kg',    1.0),
    ('01.1.2.2.2.206', 'Ground Pork',          'kg',    1.0),
    ('01.1.2.2.4.401', 'Whole Chicken',        'kg',    1.0),
    ('01.1.2.2.4.403', 'Chicken Breast',       'kg',    1.0),   # chicken fillet
    ('01.1.2.3.2.705', 'Smoked Pork',          'kg',    1.0),   # dried or smoked pork
    ('01.1.4.2.0.203', 'Whole Milk',           'l',     1.0),
    ('01.1.4.3.3.602', 'Cream',                'kg',    1.0),   # cream 35%
    ('01.1.4.5.0.501', 'Fresh Cottage Cheese', 'kg',    1.0),   # biezpiens (curd)
    ('01.1.4.5.0.502', 'Cheese',               'kg',    1.0),
    ('01.1.4.5.0.504', 'Cream Cheese',         'kg',    5.0),   # 200 g
    ('01.1.4.6.0.403', 'Yogurt',               'kg',    1.0),   # plain yoghurt
    ('01.1.4.8.1.701', 'Eggs',                 'dozen', 1.2),   # 10 eggs
    ('01.1.5.1.3.301', 'Olive Oil',            'l',     1.0),
    ('01.1.5.2.1.101', 'Butter',               'kg',    1.0),
    ('01.1.6.1.1.109', 'Avocado',              'unit',  1.0),   # per piece
    ('01.1.6.1.2.104', 'Banana',               'kg',    1.0),
    ('01.1.6.2.2.105', 'Lemons',               'kg',    1.0),
    ('01.1.6.2.3.103', 'Oranges',              'kg',    1.0),
    ('01.1.6.3.1.101', 'Apples',               'kg',    1.0),
    ('01.1.6.3.2.102', 'Pears',                'kg',    1.0),
    ('01.1.6.4.5.107', 'Strawberries',         'kg',    1.0),
    ('01.1.6.4.6.115', 'Blueberries',          'kg',    1.0),
    ('01.1.6.5.2.118', 'Kiwi',                 'kg',    1.0),
    ('01.1.6.5.3.116', 'Melon',                'kg',    1.0),
    ('01.1.7.1.2.108', 'Napa Cabbage',         'kg',    1.0),   # Chinese cabbage
    ('01.1.7.2.1.106', 'Bell Pepper',          'kg',    1.0),   # sweet pepper
    ('01.1.7.2.2.105', 'Cucumber',             'kg',    1.0),
    ('01.1.7.2.4.104', 'Tomato',               'kg',    1.0),
    ('01.1.7.2.5.113', 'Zucchini',             'kg',    1.0),   # squash/zucchini
    ('01.1.7.2.5.114', 'Pumpkin',              'kg',    1.0),
    ('01.1.7.4.1.102', 'Carrot',               'kg',    1.0),
    ('01.1.7.4.2.112', 'Garlic',               'kg',    1.0),
    ('01.1.7.4.3.103', 'Onion',                'kg',    1.0),
    ('01.1.7.4.4.107', 'Spring Onions',        'kg',    1.0),
    ('01.1.7.5.1.403', 'Potato',               'kg',    1.0),
    ('01.1.8.3.1.203', 'Honey',                'kg',    1.0),
    ('01.1.9.4.0.109', 'Dill',                 'kg',    1.0),
]


def figures(rows):
    got = latest(rows, 'GOODS_SERVICES', 'TIME', month)
    out = []
    for code, name, unit, factor in PRODUCTS:
        if code in got:
            when, value = got[code]
            out.append(Figure(name, round(value * factor, 4), unit, when))
    return out


def fetch():
    return query(URL, [
        {'code': 'GOODS_SERVICES', 'selection': {'filter': 'item', 'values': [p[0] for p in PRODUCTS]}},
        {'code': 'TIME', 'selection': {'filter': 'top', 'values': [str(MONTHS)]}},
    ])


def run():
    figs = figures(fetch())
    if not figs:
        raise RuntimeError('CSB PCC010m returned no prices — the table or the API has changed')
    for f in figs:
        print(f'  {f.name:22} {f.price:>9.2f} EUR/{f.unit:5} {f.snapshot}')
    return write('LV', SOURCE_NAME, 'retail', figs)


if __name__ == '__main__':
    run()
