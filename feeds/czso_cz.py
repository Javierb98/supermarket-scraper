"""
Czechia: average consumer prices of selected goods, monthly, from the Czech
Statistical Office (CZSO / ČSÚ), open dataset CEN0101N in DataStat.

About 86 food and drink items, national only (the regional series ended with
the old public database in 2018), koruna. The CSV holds the current year's
months; each item's latest month is used.

Each item names its own quantity in brackets — "Rýže [1 kg]",
"Vejce slepičí čerstvá [10 ks]", "Jogurt bílý [150 g]", "Květák [1 ks]" — and
the price is for that quantity. The quantity is read from the bracket and
checked against what this feed expects, so a change of pack size at CZSO
stops the item instead of storing a wrong per-kilo price.

Items left out: processed and cooked goods, beef and pork cuts without a
catalogue twin (kýta, krkovice, pečeně, beef quarters), whole ducks (no
catalogue product), "Kuřecí stehna" (leg quarters), white cabbage and iceberg
lettuce (no catalogue product), table grapes (catalogue splits red/green),
semi-skimmed milk, and "Hermelín" (camembert-type; no catalogue product).

    python feeds/czso_cz.py

Licence: CZSO open data, free reuse with attribution
(https://csu.gov.cz/podminky_pro_vyuzivani_a_dalsi_zverejnovani_statistickych_udaju_csu).
"""

import csv
import io
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get

URL = 'https://data.csu.gov.cz/opendata/sady/CEN0101N/distribuce/csv'
SOURCE_NAME = 'CZSO, dataset CEN0101N'

# (CZSO code, catalogue name, unit, quantity CZSO prices — as written in its bracket)
PRODUCTS = [
    ('01122401', 'Whole Chicken',        'kg',    '1 kg'),    # kuřata kuchaná celá
    ('01122402', 'Chicken Breast',       'kg',    '1 kg'),    # kuřecí prsní řízky
    ('01122405', 'Turkey Breast',        'kg',    '1 kg'),    # krůtí prsní řízky
    ('01122501', 'Rabbit Meat',          'kg',    '1 kg'),    # králík domácí
    ('01122203', 'Pork Shoulder',        'kg',    '1 kg'),    # vepřová plec
    ('01122204', 'Pork Belly',           'kg',    '1 kg'),    # vepřový bůček
    ('01141001', 'Whole Milk',           'l',     '1 l'),     # plnotučné trvanlivé
    ('01143002', 'Cream',                'l',     '1 l'),     # smetana sladká
    ('01145001', 'Edam Cheese',          'kg',    '1 kg'),
    ('01145005', 'Blue Cheese',          'kg',    '1 kg'),    # Niva
    ('01145006', 'Gouda Cheese',         'kg',    '1 kg'),
    ('01145007', 'Fresh Cottage Cheese', 'kg',    '1 kg'),    # tvaroh
    ('01146001', 'Yogurt',               'kg',    '150 g'),   # jogurt bílý
    ('01148001', 'Eggs',                 'dozen', '10 ks'),
    ('01152001', 'Butter',               'kg',    '1 kg'),
    ('01159001', 'Lard',                 'kg',    '1 kg'),    # vepřové sádlo
    ('01161001', 'Banana',               'kg',    '1 kg'),
    ('01162001', 'Oranges',              'kg',    '1 kg'),
    ('01162002', 'Lemons',               'kg',    '1 kg'),
    ('01163001', 'Apples',               'kg',    '1 kg'),
    ('01171002', 'Cauliflower',          'unit',  '1 ks'),
    ('01171003', 'Broccoli',             'unit',  '1 ks'),
    ('01172001', 'Tomato',               'kg',    '1 kg'),
    ('01172002', 'Cucumber',             'kg',    '1 kg'),
    ('01172003', 'Bell Pepper',          'kg',    '1 kg'),
    ('01174001', 'Carrot',               'kg',    '1 kg'),
    ('01174002', 'Celeriac',             'kg',    '1 kg'),    # celer (root)
    ('01174003', 'Onion',                'kg',    '1 kg'),
    ('01174004', 'Garlic',               'kg',    '1 kg'),
    ('01175001', 'Potato',               'kg',    '1 kg'),
    ('01179001', 'Canned Sauerkraut',    'kg',    '1 kg'),    # nakládané zelí
    ('01183001', 'Honey',                'kg',    '1 kg'),
]

QUANTITY = re.compile(r'\[([\d,]+)\s*(kg|g|l|ks)\]\s*$')


def factor(quantity, unit):
    """CZSO's bracketed quantity -> multiplier to the catalogue unit, or None if it does not fit."""
    m = QUANTITY.search('[' + quantity + ']')
    n, u = float(m.group(1).replace(',', '.')), m.group(2)
    if unit == 'kg' and u == 'kg':
        return 1 / n
    if unit == 'kg' and u == 'g':
        return 1000 / n
    if unit == 'l' and u == 'l':
        return 1 / n
    if unit == 'dozen' and u == 'ks':
        return 12 / n
    if unit == 'unit' and u == 'ks':
        return 1 / n
    return None


def figures(text):
    latest = {}
    for r in csv.DictReader(io.StringIO(text)):
        code, period, value = r['CENREP4'], r['CasM'], r['Hodnota']
        if not value:
            continue
        if code not in latest or period > latest[code][0]:
            latest[code] = (period, float(value.replace(',', '.')), r['Druh zboží'])

    out = []
    for code, name, unit, quantity in PRODUCTS:
        if code not in latest:
            continue
        period, value, label = latest[code]
        m = QUANTITY.search(label)
        if not m or f'{m.group(1)} {m.group(2)}' != quantity:
            print(f'  {name}: CZSO now prices "{label}", expected [{quantity}] — skipped', file=sys.stderr)
            continue
        y, mo = period.split('-')
        out.append(Figure(name, round(value * factor(quantity, unit), 4), unit, date(int(y), int(mo), 1)))
    return out


def run():
    figs = figures(get(URL).decode('utf-8-sig'))
    if not figs:
        raise RuntimeError('CZSO CEN0101N returned no prices — the dataset or its address has changed')
    for f in figs:
        print(f'  {f.name:22} {f.price:>9.2f} CZK/{f.unit:5} {f.snapshot}')
    return write('CZ', SOURCE_NAME, 'retail', figs)


if __name__ == '__main__':
    run()
