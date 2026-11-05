"""
Ireland: CSO table CPM12, national average prices of selected consumer items.

The Central Statistics Office publishes monthly national average shop
prices for 76 items, read here as JSON-stat 2.0 from its PxStat API:

    https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/CPM12/JSON-stat/2.0/en

Stage: retail, national, monthly, EUR. Licensed CC BY 4.0
(https://www.cso.ie/en/aboutus/whoweare/copyrightpolicy/).

Prices are given per pack ("Full fat milk per 2 litre", "Butter per lb",
"Uncooked chicken medium size 1.6kg") and converted to the site's units
with the divisors below. Each item's figure is its latest month with a
value; CSO leaves suppressed items empty, and those are skipped.

Left out: low-fat milk (not skimmed), lamb's liver, ham, rashers, steak
cuts with no single catalogue product (topside-or-rib, diced beef, pork
steak), grapes (red and green mixed), the 7.5 kg potato sack (the 2.5 kg
bag is used, one Potato figure per month), medium eggs (large are used),
and everything that is not food a farm sells.

    python feeds/cso_ie.py
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get_json
from feeds.gbie_shared import clear_national

URL = 'https://ws.cso.ie/public/api.restful/PxStat.Data.Cube_API.ReadDataset/CPM12/JSON-stat/2.0/en'
SOURCE_NAME = 'CSO Ireland, table CPM12'
STAGE = 'retail'
LB = 0.45359237

# CSO item code -> (expected label, catalogue name, unit, what one CSO price is of that unit)
# The label is checked so a renumbered item is skipped, not mis-mapped.
ITEMS = {
    '10280': ('Sirloin steak per kg',              'Fresh Sirloin',  'kg',    1.0),
    '10290': ('Striploin steak per kg',            'Fresh Striploin', 'kg',   1.0),
    '10320': ('Pork loin chops per kg',            'Pork Chops',     'kg',    1.0),
    '10340': ('Lamb - whole leg / half leg per kg', 'Lamb Leg',      'kg',    1.0),
    '10350': ('Lamb loin chops per kg',            'Lamb Chops',     'kg',    1.0),
    '10370': ('Uncooked chicken medium size 1.6kg', 'Whole Chicken', 'kg',    1.6),
    '10450': ('Pork sausages per kg',              'Pork Sausage',   'kg',    1.0),
    '10630': ('Full fat milk per 2 litre',         'Whole Milk',     'l',     2.0),
    '10680': ('Irish cheddar per kg',              'Cheddar Cheese', 'kg',    1.0),
    '10730': ('Large eggs per half dozen',         'Eggs',           'dozen', 0.5),
    '10750': ('Butter per lb',                     'Butter',         'kg',    LB),
    '10850': ('Bananas per kg',                    'Banana',         'kg',    1.0),
    '10910': ('Tomatoes per kg',                   'Tomato',         'kg',    1.0),
    '10920': ('Onions per kg',                     'Onion',          'kg',    1.0),
    '10940': ('Broccoli per kg',                   'Broccoli',       'kg',    1.0),
    '10950': ('Carrots per kg',                    'Carrot',         'kg',    1.0),
    '10960': ('Mushrooms per kg',                  'White Mushroom', 'kg',    1.0),
    '11090': ('Potatoes 2.5 kg',                   'Potato',         'kg',    2.5),
}


def _ordered(category):
    idx = category['index']
    return list(idx) if isinstance(idx, list) else sorted(idx, key=idx.get)


def parse(ds):
    """JSON-stat 2.0 dataset -> (figures, problems). Expects dims STATISTIC x month x item."""
    ids, sizes, values = ds['id'], ds['size'], ds['value']
    dims = {k: ds['dimension'][k]['category'] for k in ids}
    time_key = next(k for k in ids if k.upper().startswith('TLIST'))
    item_key = next(k for k in ids if k not in ('STATISTIC', time_key))
    months = _ordered(dims[time_key])
    items = _ordered(dims[item_key])
    labels = dims[item_key].get('label', {})

    # row-major index over all dimensions
    strides, s = {}, 1
    for k, n in reversed(list(zip(ids, sizes))):
        strides[k] = s
        s *= n

    def value(month_i, item_i):
        i = month_i * strides[time_key] + item_i * strides[item_key]
        v = values.get(str(i)) if isinstance(values, dict) else values[i]
        return v

    figures, problems = [], []
    for code, (label, name, unit, size) in ITEMS.items():
        if code not in items:
            problems.append(f'{code} {label}: not in the table')
            continue
        if labels.get(code, '').strip() != label:
            problems.append(f'{code}: label is now {labels.get(code)!r}, expected {label!r}')
            continue
        j = items.index(code)
        for mi in range(len(months) - 1, -1, -1):
            v = value(mi, j)
            if v is not None:
                m = months[mi]
                figures.append(Figure(name, round(float(v) / size, 4), unit, date(int(m[:4]), int(m[4:6]), 1)))
                break
        else:
            problems.append(f'{code} {label}: no value')
    return figures, problems


def run():
    ds = get_json(URL, timeout=120)
    figures, problems = parse(ds)
    for p in problems:
        print(f'  skipped: {p}')
    if not figures:
        raise RuntimeError('CSO CPM12 returned nothing usable — the table has changed')
    for f in figures:
        print(f'  {f.name:16} {f.price:>7.2f} EUR/{f.unit:5} {f.snapshot}')
    clear_national('IE', SOURCE_NAME, STAGE, [f.snapshot for f in figures])
    written, _ = write('IE', SOURCE_NAME, STAGE, figures)
    return written


if __name__ == '__main__':
    run()
