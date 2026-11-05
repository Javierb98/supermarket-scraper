"""
United Kingdom: Defra's wholesale prices of home-grown fruit and vegetables.

The average of the "most usual" prices wholesalers charge for home-grown
produce at the Birmingham, Bristol, Manchester and a London market (New
Spitalfields or Western International). Published by Defra, updated
fortnightly with weekly figures, as a machine-readable CSV under the Open
Government Licence v3.

    https://www.gov.uk/government/statistical-data-sets/wholesale-fruit-and-vegetable-prices-weekly-average

The file name changes with every release, so the CSV is found through the
GOV.UK content API rather than hard-coded.

Stage: wholesale (trade to trade). Shown to farmers, labelled, never badged.
Region: none. The markets are in England, but the figure is Defra's national
average, so it is stored as the UK's national figure.

Varieties: where the site has one product and Defra several (Gala,
Braeburn, Cox... are all "Apples"), the figure is the plain mean of the
varieties quoted in the item's latest week, with the cheapest and dearest
variety as low and high. Bramley (a cooking apple) is left out of Apples.

Left out on purpose: coriander and spring onions (priced by the bunch,
though the CSV says kg), swede and rhubarb (no catalogue product), pointed
cabbage, iceberg/butterhead lettuce, runner beans, baby-leaf salad (no
matching catalogue product), and anything not quoted for eight weeks (out
of season).

    python feeds/defra_wholesale.py
"""

import csv
import io
import os
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get, get_json
from feeds.gbie_shared import clear_national, mean

CONTENT_API = 'https://www.gov.uk/api/content/government/statistical-data-sets/wholesale-fruit-and-vegetable-prices-weekly-average'
SOURCE_NAME = 'Defra wholesale fruit and vegetable prices'
STAGE = 'wholesale'
STALE_AFTER = timedelta(weeks=8)

# (Defra item, Defra variety or None for every variety) -> (catalogue name, unit)
# Defra's own unit must be the one given here, or the row is skipped: a
# per-head price is never stored as a per-kilo one.
MAP = [
    # fruit
    (('apples', ('braeburn', 'coxs_orange_group', 'egremont_russet', 'gala',
                 'other_early_season', 'other_mid_season', 'other_late_season')), 'Apples', 'kg', 'kg'),
    (('pears', None),             'Pears',          'kg', 'kg'),
    (('plums', None),             'Plums',          'kg', 'kg'),
    (('cherries', None),          'Cherries',       'kg', 'kg'),
    (('blackberries', None),      'Blackberries',   'kg', 'kg'),
    (('blueberries', None),       'Blueberries',    'kg', 'kg'),
    (('raspberries', None),       'Raspberry',      'kg', 'kg'),
    (('strawberries', None),      'Strawberries',   'kg', 'kg'),
    (('gooseberries', None),      'Gooseberry',     'kg', 'kg'),
    (('currants', ('black',)),    'Black Currant',  'kg', 'kg'),
    (('currants', ('red',)),      'Red Currant',    'kg', 'kg'),
    # vegetables
    (('asparagus', None),         'Asparagus',      'kg', 'kg'),
    (('beans', ('broad',)),       'Broad Beans Fresh', 'kg', 'kg'),
    (('beans', ('dwarf_french_or_kidney',)), 'Green Beans', 'kg', 'kg'),
    (('beetroot', None),          'Beetroot',       'kg', 'kg'),
    (('brussels_sprouts', None),  'Brussels Sprouts', 'kg', 'kg'),
    (('cabbage', ('red',)),       'Red Cabbage',    'kg', 'kg'),
    (('cabbage', ('savoy',)),     'Savoy Cabbage',  'head', 'unit'),
    (('calabrese', None),         'Broccoli',       'kg', 'kg'),
    (('capsicum', ('red', 'green', 'yelloworange')), 'Bell Pepper', 'kg', 'kg'),
    (('carrots', None),           'Carrot',         'kg', 'kg'),
    (('cauliflower', None),       'Cauliflower',    'head', 'unit'),
    (('celeriac', None),          'Celeriac',       'kg', 'kg'),
    (('celery', None),            'Celery',         'kg', 'kg'),
    (('chinese_leaf', None),      'Napa Cabbage',   'kg', 'kg'),
    (('courgettes', None),        'Zucchini',       'kg', 'kg'),
    (('cucumbers', None),         'Cucumber',       'kg', 'kg'),
    (('curly_kale', None),        'Kale',           'kg', 'kg'),
    (('leeks', None),             'Leek',           'kg', 'kg'),
    (('lettuce', ('cos',)),       'Romaine Lettuce', 'head', 'unit'),
    (('onion', ('bulb_brown',)),  'Onion',          'kg', 'kg'),
    (('onion', ('bulb_red',)),    'Red Onion',      'kg', 'kg'),
    (('pak_choi', None),          'Bok Choy',       'kg', 'kg'),
    (('parsnips', None),          'Parsnip',        'kg', 'kg'),
    (('peas', None),              'Green Peas',     'kg', 'kg'),
    (('rocket', None),            'Arugula',        'kg', 'kg'),
    (('spinach_leaf', None),      'Spinach',        'kg', 'kg'),
    (('sweetcorn', None),         'Sweet Corn',     'head', 'unit'),
    (('tomatoes', ('round',)),    'Tomato',         'kg', 'kg'),
    (('tomatoes', ('vine',)),     'Vine Tomatoes',  'kg', 'kg'),
    (('tomatoes', ('cherry',)),   'Cherry Tomato',  'kg', 'kg'),
    (('tomatoes', ('plum',)),     'Plum Tomatoes',  'kg', 'kg'),
    (('turnip', None),            'Turnip',         'kg', 'kg'),
    (('watercress', None),        'Watercress',     'kg', 'kg'),
]


def csv_url():
    doc = get_json(CONTENT_API)
    for a in doc.get('details', {}).get('attachments', []):
        url = a.get('url') or ''
        if url.endswith('.csv') or a.get('content_type') == 'text/csv':
            return url
    raise RuntimeError('Defra: no CSV attachment on the data set page — the page has changed')


def read_rows(text):
    """CSV text -> {(item, variety): [(date, price, unit), ...]}"""
    out = defaultdict(list)
    for r in csv.DictReader(io.StringIO(text)):
        try:
            d = date.fromisoformat(r['date'].strip())
            p = float(r['price'])
        except (KeyError, ValueError):
            continue
        if p <= 0:
            continue
        out[(r['item'].strip(), r['variety'].strip())].append((d, p, r['unit'].strip().lower()))
    return out


def figures_from(rows):
    newest = max(d for series in rows.values() for d, _, _ in series)
    figures = []
    for (item, varieties), name, defra_unit, unit in MAP:
        # every variety's latest quote for this item, if recent and in the expected unit
        latest = {}
        for (it, var), series in rows.items():
            if it != item or (varieties and var not in varieties):
                continue
            d, p, u = max(series)
            if u != defra_unit or newest - d > STALE_AFTER:
                continue
            latest[var] = (d, p)
        if not latest:
            continue
        # a product's figure is for its most recent week; varieties not quoted that week are left out
        week = max(d for d, _ in latest.values())
        prices = [p for d, p in latest.values() if d == week]
        figures.append(Figure(name, round(mean(prices), 4), unit, week,
                              low=min(prices), high=max(prices)))
    return figures


def run():
    url = csv_url()
    print(f'Defra CSV: {url}')
    rows = read_rows(get(url).decode('utf-8-sig'))
    figures = figures_from(rows)
    if not figures:
        raise RuntimeError('Defra returned no usable figures — the CSV has changed')
    for f in figures:
        print(f'  {f.name:18} {f.price:>7.2f} GBP/{f.unit:4} {f.snapshot}  ({f.low}–{f.high})')
    clear_national('GB', SOURCE_NAME, STAGE, [f.snapshot for f in figures])
    written, _ = write('GB', SOURCE_NAME, STAGE, figures)
    return written


if __name__ == '__main__':
    run()
