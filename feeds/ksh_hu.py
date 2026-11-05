"""
Hungary: average consumer prices of selected products, monthly, from the
Hungarian Central Statistical Office (KSH), STADAT table ara0044
("1.2.1.8. Average consumer price of selected products and services (raw
data), monthly").

About 175 items, national, forint, from 2017 to the latest month. One CSV
(semicolon-separated, Central European code page, thousands written with a
space: "2 070"). Columns run to the end of the current year and are blank
until published, so each item's latest filled month is used.

Items left out: anything priced per pack of a size KSH gives only as a range
("Butter, 100–125 g", "Pork lard, 400–500 g" — the per-kilo price cannot be
worked out), processed goods, pork and beef cuts without a catalogue twin,
"Chicken leg" (leg quarters), "Cabbage" (no white cabbage in the catalogue),
new potatoes (seasonal duplicate of potatoes) and sour cream.

Three judgment calls, each the product a Hungarian farm sells under that name:
"Red onions" is KSH's translation of vöröshagyma, the ordinary brown onion
-> Onion (not Red Onion); "Green peppers" (the pale sweet pepper) -> Bell
Pepper; pasteurised 2.8% milk (the standard full milk in Hungarian shops)
-> Whole Milk.

    python feeds/ksh_hu.py

Licence: KSH data may be reused free of charge with the source named
(https://www.ksh.hu/apps/shop.licenc?lang=en).
"""

import csv
import io
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get

URL = 'https://www.ksh.hu/stadat_files/ara/en/ara0044.csv'
SOURCE_NAME = 'KSH Hungary, table ara0044'

# (KSH code, label KSH uses — checked, catalogue name, unit, factor)
PRODUCTS = [
    ('10401', 'Chicken ready to cook, kg',               'Whole Chicken',  'kg',    1.0),
    ('10407', 'Chicken wings, kg',                       'Chicken Wings',  'kg',    1.0),
    ('10408', 'Filleted turkey breast, kg',              'Turkey Breast',  'kg',    1.0),
    ('10409', 'Filleted chicken breast, kg',             'Chicken Breast', 'kg',    1.0),
    ('11001', 'Eggs, 10 pieces',                         'Eggs',           'dozen', 1.2),
    ('11101', 'Pasteurised ESL milk, 2.8% fat content, litre', 'Whole Milk', 'l',  1.0),
    ('11209', 'Trappist-style cheese block, kg',         'Cheese',         'kg',    1.0),
    ('13910', 'Acacia honey, kg',                        'Honey',          'kg',    1.0),
    ('14002', "'Old' potatoes, kg",                      'Potato',         'kg',    1.0),
    ('14101', 'Carrots, kg',                             'Carrot',         'kg',    1.0),
    ('14103', 'Red onions, kg',                          'Onion',          'kg',    1.0),   # vöröshagyma: the ordinary onion
    ('14107', 'Tomatoes, kg',                            'Tomato',         'kg',    1.0),
    ('14108', 'Green peppers, kg',                       'Bell Pepper',    'kg',    1.0),
    ('14110', 'Cucumbers, kg',                           'Cucumber',       'kg',    1.0),
    ('14111', 'Mushrooms, kg',                           'White Mushroom', 'kg',    1.0),
    ('14201', 'Apples, kg',                              'Apples',         'kg',    1.0),
    ('14202', 'Watermelons, kg',                         'Watermelon',     'kg',    1.0),
    ('14209', 'Pears, kg',                               'Pears',          'kg',    1.0),
    ('14221', 'Lemons, kg',                              'Lemons',         'kg',    1.0),
    ('14222', 'Bananas, kg',                             'Banana',         'kg',    1.0),
    ('14224', 'Oranges, kg',                             'Oranges',        'kg',    1.0),
    ('14701', 'Cleaned walnuts, without sugar, kg',      'Walnuts',        'kg',    1.0),
    ('15202', 'Paprika, 75–100 g, kg',                   'Paprika Powder', 'kg',    1.0),
]

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']


def period(header):
    """'2026 September' -> date(2026, 9, 1)."""
    y, m = header.split()
    return date(int(y), MONTHS.index(m) + 1, 1)


def number(cell):
    cell = cell.replace('\xa0', '').replace(' ', '').replace(',', '.').strip()
    try:
        return float(cell)
    except ValueError:
        return None             # '', '..', '–': not published


def figures(text):
    rows = list(csv.reader(io.StringIO(text), delimiter=';'))
    header = next(r for r in rows if r and r[0] == 'Code')
    by_code = {r[0]: r for r in rows if r and r[0].isdigit()}

    out = []
    for code, label, name, unit, factor in PRODUCTS:
        r = by_code.get(code)
        if r is None:
            continue
        if r[1].strip() != label:
            print(f'  {name}: KSH item {code} is now "{r[1]}", expected "{label}" — skipped', file=sys.stderr)
            continue
        for i in range(len(r) - 1, 1, -1):
            v = number(r[i])
            if v:
                out.append(Figure(name, round(v * factor, 4), unit, period(header[i])))
                break
    return out


def run():
    figs = figures(get(URL).decode('cp1250'))
    if not figs:
        raise RuntimeError('KSH ara0044 returned no prices — the table or its address has changed')
    for f in figs:
        print(f'  {f.name:22} {f.price:>9.0f} HUF/{f.unit:5} {f.snapshot}')
    return write('HU', SOURCE_NAME, 'retail', figs)


if __name__ == '__main__':
    run()
