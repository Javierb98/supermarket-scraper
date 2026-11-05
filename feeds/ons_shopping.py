"""
United Kingdom: ONS average shop prices (the Shopping prices comparison tool).

The Office for National Statistics stopped publishing individual grocery
price quotes in 2026 (from March, groceries in the CPI come from retailers'
scanner data), but it still publishes monthly UK average prices for some
200 grocery items in its Shopping prices comparison tool:

    https://www.ons.gov.uk/economy/inflationandpriceindices/articles/shoppingpricescomparisontool/2023-05-03

The tool reads its data from ONS's own public GitHub repository, refreshed
on CPI release days; this feed reads the same two files:

    avgprice.csv   item -> average price per month (GBP)
    metadata.csv   item -> the pack size that price is for ("1000 g", "250 g", "each", "12 pack")

Stage: retail (a shop-shelf average), national, monthly. Crown copyright,
Open Government Licence v3.

Every price is converted from the pack size ONS states, read from
metadata.csv each run, so a change of pack size never turns into a wrong
per-kilo price; a pack size we cannot read is skipped and reported.

Mapped only where the ONS item is the product a farm sells. Left out:
"Cabbage" and "Lettuce" (no single catalogue product), "Clementines and
mandarins" and "Grapes" (mixed), liver (animal not stated), bacon, gammon,
beef joints, processed and packaged foods.

    python feeds/ons_shopping.py
"""

import csv
import io
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get
from feeds.gbie_shared import clear_national

BASE = 'https://raw.githubusercontent.com/ONSdigital/cpi-items-actions/main/'
SOURCE_NAME = 'ONS shopping prices comparison tool'
STAGE = 'retail'

# ONS item (ID_NAME, exactly) -> (catalogue name, unit to store)
MAP = {
    'Apples - not cooking':                    ('Apples', 'kg'),
    'Bananas':                                 ('Banana', 'kg'),
    'Pears':                                   ('Pears', 'kg'),
    'Plums':                                   ('Plums', 'kg'),
    'Strawberries':                            ('Strawberries', 'kg'),
    'Raspberries':                             ('Raspberry', 'kg'),
    'Blueberries':                             ('Blueberries', 'kg'),
    'Avocados':                                ('Avocado', 'unit'),
    'Kiwis':                                   ('Kiwi', 'unit'),
    'Lemons':                                  ('Lemons', 'unit'),
    'Oranges':                                 ('Oranges', 'unit'),
    'Mangoes (fresh)':                         ('Mango', 'unit'),
    'Melons':                                  ('Melon', 'unit'),
    'Pineapple (fresh)':                       ('Pineapple', 'unit'),
    'Broccoli':                                ('Broccoli', 'kg'),
    'Carrots':                                 ('Carrot', 'kg'),
    'Cauliflower':                             ('Cauliflower', 'unit'),
    'Courgette':                               ('Zucchini', 'kg'),
    'Cucumber':                                ('Cucumber', 'unit'),
    'Mushrooms':                               ('White Mushroom', 'kg'),
    'Onions':                                  ('Onion', 'kg'),
    'Peppers':                                 ('Bell Pepper', 'unit'),
    'Tomatoes':                                ('Tomato', 'kg'),
    'Beans - fresh (excl. soya or edamame)':   ('Green Beans', 'kg'),
    'Potatoes - white':                        ('Potato', 'kg'),
    'Potatoes - sweet':                        ('Sweet Potato', 'kg'),
    'Eggs - free-range':                       ('Eggs', 'dozen'),
    "Milk - cow's (whole, fresh)":             ('Whole Milk', 'l'),
    'Cream - pouring and cooking (e.g. single, whipping)': ('Cream', 'l'),
    'Butter - dairy (block or tub)':           ('Butter', 'kg'),
    'Cheese - Cheddar':                        ('Cheddar Cheese', 'kg'),
    'Honey':                                   ('Honey', 'kg'),
    'Chicken - whole':                         ('Whole Chicken', 'kg'),
    'Chicken - fillet or steak':               ('Chicken Breast', 'kg'),
    'Beef - minced or diced':                  ('Ground Beef', 'kg'),
    'Beef - steak or chops':                   ('Beef Steak', 'kg'),
    'Pork - steak or chops':                   ('Pork Chops', 'kg'),
    'Pork sausages':                           ('Pork Sausage', 'kg'),
    'Lamb - steaks, chops or fillets':         ('Lamb Chops', 'kg'),
    'Oil - olive':                             ('Olive Oil', 'l'),
}


def per_unit(price, size, unit):
    """Price for ONS's pack `size` -> price per `unit`, or None if the size cannot be read for that unit."""
    s = (size or '').strip().lower()
    m = re.fullmatch(r'([\d.]+)\s*(g|kg|ml|l|pack)', s)
    if unit == 'unit':
        return price if s == 'each' else None
    if not m:
        return None
    n, u = float(m.group(1)), m.group(2)
    if n <= 0:
        return None
    if unit == 'kg' and u in ('g', 'kg'):
        return price / (n / 1000 if u == 'g' else n)
    if unit == 'l' and u in ('ml', 'l'):
        return price / (n / 1000 if u == 'ml' else n)
    if unit == 'dozen' and u == 'pack':
        return price * 12 / n
    return None


def parse(avg_text, meta_text):
    sizes = {r['ID_NAME']: r['WEIGHT_SIZE'] for r in csv.DictReader(io.StringIO(meta_text))}
    figures, problems = [], []
    for r in csv.DictReader(io.StringIO(avg_text)):
        item = r.get('ID_NAME')
        if item not in MAP:
            continue
        name, unit = MAP[item]
        months = sorted((k for k in r if re.fullmatch(r'\d{4}-\d{2}-\d{2}', k or '') and (r[k] or '').strip()))
        if not months:
            problems.append(f'{item}: no figures')
            continue
        month = months[-1]
        price = per_unit(float(r[month]), sizes.get(item), unit)
        if price is None:
            problems.append(f'{item}: pack size {sizes.get(item)!r} does not convert to {unit}')
            continue
        figures.append(Figure(name, round(price, 4), unit, date.fromisoformat(month)))
    missing = set(MAP) - {r for r in sizes}
    problems += [f'{m}: no longer in the tool' for m in sorted(missing)]
    return figures, problems


def run():
    avg = get(BASE + 'avgprice.csv').decode('utf-8-sig')
    meta = get(BASE + 'metadata.csv').decode('utf-8-sig')
    figures, problems = parse(avg, meta)
    for p in problems:
        print(f'  skipped: {p}')
    if not figures:
        raise RuntimeError('ONS shopping prices: nothing usable — the files have changed')
    for f in figures:
        print(f'  {f.name:16} {f.price:>7.2f} GBP/{f.unit:5} {f.snapshot}')
    clear_national('GB', SOURCE_NAME, STAGE, [f.snapshot for f in figures])
    written, _ = write('GB', SOURCE_NAME, STAGE, figures)
    return written


if __name__ == '__main__':
    run()
