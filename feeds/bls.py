"""
United States: monthly average retail food prices from the Bureau of Labor
Statistics (CPI average price data, the "AP" series).

Alongside the USDA weekly feed: USDA is advertised prices by USDA region,
BLS is prices actually collected in stores for the CPI, for the U.S. city
average and the four census regions — Northeast, Midwest, South, West. They
are stored under BLS's own region names. Two of those ("Northeast",
"Midwest") are names USDA uses too, for different areas, so any figure that
would land on a key USDA already holds is dropped and reported
(feeds/monthly_guard.py), never written over.

    python feeds/bls.py              latest month
    python feeds/bls.py --months 6   the last six months

Data comes from the flat files at download.bls.gov/pub/time.series/ap/ (BLS
asks scripted downloads to identify themselves; common.USER_AGENT does). If
those are refused, the keyless public API v1 is used instead (25 series per
request, 25 requests a day — this feed needs two).

Licence: US government work, public domain.
https://www.bls.gov/opub/copyright-information.htm
"""

import json
import os
import sys
import time
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import common, monthly_guard

SOURCE_NAME = 'BLS average prices (CPI)'
FLAT = 'https://download.bls.gov/pub/time.series/ap/ap.data.3.Food'
API = 'https://api.bls.gov/publicAPI/v1/timeseries/data/'

AREAS = {'0000': None, '0100': 'Northeast', '0200': 'Midwest', '0300': 'South', '0400': 'West'}

LB = 0.45359237          # kg in a pound
GALLON = 3.785411784     # litres in a US gallon

# BLS item -> (catalogue name, unit, quantity the price is for, in that unit).
# Group averages ("All uncooked beef steaks"), mixed milk grades and processed
# foods are left out; so is iceberg lettuce, which the catalogue lacks.
ITEMS = {
    '703112': ('Ground Beef', 'kg', LB),            # Ground beef, 100% beef, per lb
    '703213': ('Fresh Chuck Roast', 'kg', LB),      # Chuck roast, USDA Choice, boneless
    '703613': ('Fresh Sirloin', 'kg', LB),          # Steak, sirloin, USDA Choice, boneless
    '704212': ('Pork Chops', 'kg', LB),             # Chops, boneless
    '706111': ('Whole Chicken', 'kg', LB),          # Chicken, fresh, whole
    'FF1101': ('Chicken Breast', 'kg', LB),         # Chicken breast, boneless
    '708111': ('Eggs', 'dozen', 1.0),               # Eggs, grade A, large, per doz.
    '709112': ('Whole Milk', 'l', GALLON),          # Milk, fresh, whole, fortified, per gal.
    '710212': ('Cheddar Cheese', 'kg', LB),         # Cheddar cheese, natural
    'FS1101': ('Butter', 'kg', LB),                 # Butter, stick
    'FJ4101': ('Yogurt', 'kg', 8 * LB / 16),        # Yogurt, per 8 oz.
    '711211': ('Banana', 'kg', LB),
    '711311': ('Oranges', 'kg', LB),                # Oranges, Navel
    '711412': ('Lemons', 'kg', LB),
    '711415': ('Strawberries', 'kg', 12 * LB / 16), # Strawberries, dry pint, per 12 oz.
    '712112': ('Potato', 'kg', LB),                 # Potatoes, white
    '712311': ('Tomato', 'kg', LB),                 # Tomatoes, field grown
    'FL2101': ('Romaine Lettuce', 'kg', LB),        # Lettuce, romaine, per lb
}


def series_ids():
    return [f'APU{area}{item}' for item in ITEMS for area in AREAS]


def parse_flat(text):
    """ap.data rows -> {series_id: {date: value}} for the mapped series."""
    wanted = set(series_ids())
    out = {}
    for line in text.splitlines()[1:]:
        parts = [p.strip() for p in line.split('\t')]
        if len(parts) < 4 or parts[0] not in wanted:
            continue
        sid, year, period, value = parts[:4]
        if not period.startswith('M') or period == 'M13':
            continue
        try:
            v = float(value)
        except ValueError:          # '-' = not available
            continue
        out.setdefault(sid, {})[date(int(year), int(period[1:]), 1)] = v
    return out


def fetch_api():
    """The same, from the keyless API v1, for when the flat files are refused."""
    ids, out = series_ids(), {}
    for i in range(0, len(ids), 25):
        payload = common.get_json(API, data={'seriesid': ids[i:i + 25]}, pause=2)
        if payload.get('status') != 'REQUEST_SUCCEEDED':
            raise RuntimeError(f'BLS API: {payload.get("status")} {payload.get("message")}')
        for s in payload['Results']['series']:
            for d in s.get('data', []):
                if not d['period'].startswith('M') or d['period'] == 'M13':
                    continue
                try:
                    v = float(d['value'])
                except ValueError:
                    continue
                out.setdefault(s['seriesID'], {})[date(int(d['year']), int(d['period'][1:]), 1)] = v
    return out


def load():
    try:
        return parse_flat(common.get(FLAT, timeout=180).decode('latin-1'))
    except Exception as e:
        print(f'BLS flat file refused ({e}); using the API', file=sys.stderr)
        return fetch_api()


def figures_from(series, months=1):
    if not series:
        return []
    newest = max(max(v) for v in series.values())
    out = []
    for sid, values in series.items():
        area, item = sid[3:7], sid[7:]
        name, unit, qty = ITEMS[item]
        periods = sorted(values)[-months:]
        # A series that has stopped (or paused) is not this month's price.
        if (newest.year - periods[-1].year) * 12 + newest.month - periods[-1].month > 2:
            continue
        for p in periods:
            out.append(common.Figure(name, round(values[p] / qty, 4), unit, p, region=AREAS[area]))
    return out


def run(months=1):
    t0 = time.time()
    figures = figures_from(load(), months)
    if not figures:
        raise RuntimeError('BLS returned none of the mapped series')
    written, refused, collisions = monthly_guard.write('US', SOURCE_NAME, 'retail', figures)
    print(f'  {len(figures)} figures, {written} written, {len(collisions)} collisions, {time.time() - t0:.0f}s')
    return written


if __name__ == '__main__':
    n = 1
    if '--months' in sys.argv:
        n = int(sys.argv[sys.argv.index('--months') + 1])
    run(n)
