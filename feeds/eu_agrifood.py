"""
EU: member-state prices from the European Commission's Agri-food data portal.

A feed, not a scrape. The Commission publishes, per member state, the
prices the national ministries notify to it under Regulation (EU) 2017/1185:
fruit and vegetables along the supply chain, raw milk paid to farmers,
wholesale dairy products, eggs, poultry and meat cuts. The JSON API at
api.tech.ec.europa.eu/agrifood answers without a key (rate-limited; a burst
gets a 500 "endpoint SUSPENDED", which common.get retries after a pause).

What is used, and the stage each is stored under:

  fruitAndVegetable/pricesSupplyChain     weekly (some monthly), national average, EUR/100 kg
      "Farmgate price"                     -> farmgate
      "Ex-packaging station price"         -> wholesale  (packing station's selling price)
      "Retail buying price"                -> wholesale  (what the retailer pays its supplier;
                                                          preferred over ex-packaging when both exist)
      "Retail selling price"               -> retail     (shelf price)
  rawMilk/prices                          monthly, price paid to the producer -> farmgate
  dairy/prices                            weekly ex-works (bulk) prices -> wholesale
  poultry/egg/prices                      weekly, class A eggs at packing-centre level -> wholesale
  poultry/prices ("Selling price")        weekly, slaughterhouse selling price -> wholesale
  pigmeat/cuts/prices ("Selling price")   weekly, cutting-plant selling price -> wholesale
  beef/cuts/prices ("Selling price")      weekly, cutting-plant selling price -> wholesale

Money: every figure the API gives is in euro (the "€" prefix; poultry's unit
label says "national currency" but Hungarian, Czech and Polish values are
plainly euro: 2.45/kg for a broiler, not 2.45 forint). The site compares in
local money, so for the countries outside the euro (CZ, HU, PL, RO, SE, DK)
each price is converted at the ECB euro reference rate, averaged over the
week or month the price is for (ECB data API, keyless), and the source is
named "... (converted from EUR at ECB rate)". Euro countries are stored as given.

Overlap: the national statistics feeds already give CZ, HU, LV, LT and SI
shelf prices and SI's producer milk price, so this feed writes no figures
for those country-stage pairs (SKIP). Elsewhere, a figure a national source
already stored for the same product, stage, unit and date is left to it.

Units: EUR/100 kg -> per kg. Raw milk: per 100 kg -> per litre (1.03 kg/l).
Eggs: per 100 kg -> per dozen at 62.5 g an egg (0.75 kg a dozen).

Only the latest period per product and stage is written, and only if it is
recent (MAX_AGE_DAYS): a summer strawberry price is not November's. Where a
country's own national source already wrote the same product, stage and
date, that figure is kept and ours is dropped.

Varieties: where the member state gives a national average or "All types and
varieties" that is used; otherwise the plain mean of its varieties (low/high
the cheapest and dearest). Processing grades and organic lines are left out,
and tomato and onion types map to their own catalogue products.

Terms: CC BY 4.0, attribution "European Commission, Agri-food data portal"
(https://agridata.ec.europa.eu, legal notice https://commission.europa.eu/legal-notice_en).

    python feeds/eu_agrifood.py              fetch and store
    python feeds/eu_agrifood.py --dry-run    fetch and print
"""

import os
import re
import sys
from datetime import date, datetime, timedelta
from statistics import mean

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import common  # noqa: E402
from pipeline.countries import currency as currency_of  # noqa: E402

BASE = 'https://api.tech.ec.europa.eu/agrifood/api/'
SOURCE_NAME = 'European Commission agri-food data portal'

# The EU's code -> ours, for the countries Evocultiva has farms in.
COUNTRIES = {c: c for c in ('DE', 'FR', 'IT', 'ES', 'AT', 'BE', 'NL', 'PT', 'SI', 'LV', 'CZ', 'SE', 'DK', 'PL',
                            'EE', 'IE', 'HR', 'FI', 'SK', 'HU', 'LU', 'LT', 'RO')}
COUNTRIES['EL'] = 'GR'

MAX_AGE_DAYS = {'week': 70, 'month': 130}

# Country-stage pairs a national statistics feed already covers.
SKIP = {('CZ', 'retail'), ('HU', 'retail'), ('LV', 'retail'), ('LT', 'retail'), ('SI', 'retail'), ('SI', 'farmgate')}

ECB = ('https://data-api.ecb.europa.eu/service/data/EXR/D.{}.EUR.SP00.A'
       '?startPeriod={:%Y-%m-%d}&endPeriod={:%Y-%m-%d}&format=csvdata')
CONVERTED = ' (converted from EUR at ECB rate)'
MILK_KG_PER_L = 1.03
EGG_DOZEN_KG = 0.75

# --- fruit and vegetables ----------------------------------------------------

FV_STAGES = {
    'Farmgate price': ('farmgate', 0),
    'Retail buying price': ('wholesale', 0),      # preferred wholesale figure
    'Ex-packaging station price': ('wholesale', 1),
    'Retail selling price': ('retail', 0),
}

# EU product -> catalogue name. None: no catalogue product is the same thing
# (nectarines, apricots, white cabbage, table grapes of no stated colour,
# lettuces mostly iceberg, satsumas).
FV_PRODUCTS = {
    'Apples': 'Apples',
    'Asparagus': 'Asparagus',
    'Avocados': 'Avocado',
    'Bananas': 'Banana',
    'Beans': 'Green Beans',
    'Carrots': 'Carrot',
    'Cauliflowers': 'Cauliflower',
    'Cherries': 'Cherries',
    'Clementines': 'Clementine',
    'Courgettes': 'Zucchini',
    'Cucumbers': 'Cucumber',
    'Cultivated Mushrooms': 'White Mushroom',
    'Egg Plants': 'Eggplant',
    'Garlic': 'Garlic',
    'Kiwis Hayward': 'Kiwi',
    'Leeks': 'Leek',
    'Lemons': 'Lemons',
    'Mandarins': 'Mandarin Oranges Fresh',
    'Melons': 'Melon',
    'Onions': 'Onion',
    'Oranges': 'Oranges',
    'Peaches': 'Peaches',
    'Pears': 'Pears',
    'Peppers': 'Bell Pepper',
    'Plums': 'Plums',
    'Strawberries': 'Strawberries',
    'Tomatoes': 'Tomato',
    'Ware potatoes': 'Potato',
    'Water Melons': 'Watermelon',
}
# Varieties that are their own catalogue product (checked before FV_PRODUCTS).
# None: a variety left out of its product's average.
FV_VARIETIES = {
    'Tomatoes - Cherry/Special': 'Cherry Tomato',
    'Tomatoes - Trusses=Vine/"Grappes"': 'Vine Tomatoes',
    'Tomatoes - Round': 'Tomato',
    'Tomatoes - All types and varieties': None,       # cherries and vines mixed in
    'Onions - Oignons rouges': 'Red Onion',
    'Onions - Oignons blancs': 'White Onion',
    'Asparagus - Asperges blanches/violettes': 'White Asparagus',
    'Asparagus - Asperges vertes': 'Green Asparagus',
    'Bananas - EU Origins': None,                     # duplicate of the all-types row
}
WHOLE = re.compile(r'national weighted average|all types and varieties|all sweet varieties', re.I)


def fv_product(variety):
    """'Apples - Gala' -> ('Apples', is_whole_product_row) or (catalogue name, whole) / None."""
    if variety in FV_VARIETIES:
        name = FV_VARIETIES[variety]
        return (name, True) if name else None
    head = re.split(r'\s+[-–]\s+', variety, maxsplit=1)[0].strip()
    if head.lower().startswith(('organic', )) or 'processing' in head.lower():
        return None
    if head.startswith('Ware potatoes'):
        head = 'Ware potatoes'
    name = FV_PRODUCTS.get(head)
    if not name:
        return None
    return name, bool(WHOLE.search(variety))


# --- the other sectors: (endpoint, product field, product value) -> name, stage, unit, factor
# factor converts the API's EUR/100 kg to EUR per our unit.
PER_KG = 0.01
OTHER = [
    # (endpoint, filter on row, catalogue name, stage, unit, factor, preference)
    ('rawMilk/prices', lambda r: r.get('product') == 'Raw milk', 'Raw Cow Milk', 'farmgate', 'l', PER_KG * MILK_KG_PER_L, 0),
    ('dairy/prices', lambda r: r.get('product') == 'BUTTER', 'Butter', 'wholesale', 'kg', PER_KG, 0),
    ('dairy/prices', lambda r: r.get('product') == 'EDAM', 'Edam Cheese', 'wholesale', 'kg', PER_KG, 0),
    ('dairy/prices', lambda r: r.get('product') == 'GOUDA', 'Gouda Cheese', 'wholesale', 'kg', PER_KG, 0),
    ('dairy/prices', lambda r: r.get('product') == 'EMMENTAL', 'Swiss Cheese', 'wholesale', 'kg', PER_KG, 0),
    ('dairy/prices', lambda r: r.get('product') == 'CHEDDAR', 'Cheddar Cheese', 'wholesale', 'kg', PER_KG, 0),
    # Eggs: free-range is what a farm sells; barn where a country gives no free-range price.
    ('poultry/egg/prices', lambda r: r.get('farmingMethod') == 'Free range', 'Eggs', 'wholesale', 'dozen', PER_KG * EGG_DOZEN_KG, 0),
    ('poultry/egg/prices', lambda r: r.get('farmingMethod') == 'Barn', 'Eggs', 'wholesale', 'dozen', PER_KG * EGG_DOZEN_KG, 1),
    ('poultry/prices', lambda r: r.get('priceType') == 'Selling price' and r.get('productName', '').startswith('Whole broiler'),
     'Whole Chicken', 'wholesale', 'kg', PER_KG, 0),
    ('poultry/prices', lambda r: r.get('priceType') == 'Selling price' and r.get('productName') == 'Breast Fillet',
     'Chicken Breast', 'wholesale', 'kg', PER_KG, 0),
    ('pigmeat/cuts/prices', lambda r: r.get('priceType') == 'Selling price' and r.get('category') == 'Belly', 'Pork Belly', 'wholesale', 'kg', PER_KG, 0),
    ('pigmeat/cuts/prices', lambda r: r.get('priceType') == 'Selling price' and r.get('category') == 'Shoulder', 'Pork Shoulder', 'wholesale', 'kg', PER_KG, 0),
    ('beef/cuts/prices', lambda r: r.get('priceType') == 'Selling price' and r.get('category') == 'Minced meat', 'Ground Beef', 'wholesale', 'kg', PER_KG, 0),
]
# Left out on purpose: organic raw milk, drinking milk and cream (bulk tanker
# products), milk powders, whey, pork loin and ham (whole primals; "Schinken"
# is cured), pork "minced meat" (in DE and AT it is priced below belly, i.e.
# processing trimmings, elsewhere finished mince: not one product), beef quarters, chicken legs (thigh and drumstick together), cage
# and organic eggs (organic is a catalogue product per size, not given here).


def euros(text):
    """'€1,013.83' -> 1013.83."""
    t = re.sub(r'[^0-9.,-]', '', str(text or ''))
    if not t:
        return None
    t = t.replace(',', '')
    try:
        v = float(t)
    except ValueError:
        return None
    return v if v > 0 else None


def day(text):
    return datetime.strptime(text, '%d/%m/%Y').date()


def fetch(endpoint, begin, end):
    q = f'beginDate={begin:%d/%m/%Y}&endDate={end:%d/%m/%Y}'
    if endpoint == 'rawMilk/prices':
        years = sorted({begin.year, end.year})
        q = 'years=' + ','.join(str(y) for y in years)
    return common.get_json(BASE + endpoint + '?' + q, timeout=120, pause=3.0)


def latest_figures(points, today):
    """
    points: [(country, name, stage, unit, preference, period, snapshot, price, whole)]
    -> Figures per (country, stage): latest period, best preference, whole-product row or variety mean.
    """
    best = {}
    for p in points:
        country, name, stage, unit, pref, period, snap, price, whole = p
        if (today - snap).days > MAX_AGE_DAYS[period]:
            continue
        key = (country, name, stage, unit)
        # Rank: preferred source first, then newest, then weekly over monthly.
        rank = (-pref, snap, period == 'week')
        cur = best.get(key)
        if cur is None or rank > cur[0]:
            best[key] = (rank, [p])
        elif rank == cur[0]:
            cur[1].append(p)
    out = {}
    for (country, name, stage, unit), (_, ps) in best.items():
        wholes = [p for p in ps if p[8]]
        use = wholes or ps
        prices = [p[7] for p in use]
        f = common.Figure(name, mean(prices), unit, use[0][6],
                          low=min(prices), high=max(prices))
        out.setdefault((country, stage), []).append(f)
    return out


def fv_points(rows):
    out = []
    for r in rows:
        country = COUNTRIES.get(r.get('memberStateCode'))
        stage_pref = FV_STAGES.get(r.get('productStage'))
        if not country or not stage_pref or r.get('isCalculated') == 'Y':
            continue
        if '100kg' not in (r.get('unit') or '').lower().replace(' ', ''):
            continue
        got = fv_product(r.get('variety', ''))
        price = euros(r.get('price'))
        if not got or not price:
            continue
        name, whole = got
        period = 'month' if r.get('periodType') == 'Month' else 'week'
        stage, pref = stage_pref
        out.append((country, name, stage, 'kg', pref, period, day(r['beginDate']), price * PER_KG, whole))
    return out


def other_points(endpoint, rows):
    out = []
    for r in rows:
        country = COUNTRIES.get(r.get('memberStateCode'))
        price = euros(r.get('price'))
        if not country or not price:
            continue
        for ep, test, name, stage, unit, factor, pref in OTHER:
            if ep != endpoint or not test(r):
                continue
            period = 'month' if endpoint == 'rawMilk/prices' else 'week'
            out.append((country, name, stage, unit, pref, period, day(r['beginDate']), price * factor, True))
    return out


def taken_by_others(country, stage, figures, source_name=SOURCE_NAME):
    """(name, unit, snapshot) already in market_average for this country and stage from another source."""
    from utils.db import get_connection
    if not figures:
        return set()
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("""SELECT canonical_name, standard_unit, snapshot_date FROM market_average
                         WHERE country = %s AND price_stage = %s AND region IS NULL
                           AND (source_name IS NULL OR source_name <> %s)
                           AND snapshot_date >= %s""",
                      (country, stage, source_name, min(f.snapshot for f in figures)))
            return {(r['canonical_name'], r['standard_unit'], r['snapshot_date']) for r in c.fetchall()}
    finally:
        conn.close()


def ecb_rates(currencies, begin, end):
    """{currency: {date: units per euro}} from the ECB's daily reference rates."""
    if not currencies:
        return {}
    text = common.get(ECB.format('+'.join(sorted(currencies)), begin, end),
                      headers={'Accept': 'text/csv'}, timeout=60).decode('utf-8')
    out = {}
    lines = text.strip().splitlines()
    head = lines[0].split(',')
    ci, ti, vi = head.index('CURRENCY'), head.index('TIME_PERIOD'), head.index('OBS_VALUE')
    for line in lines[1:]:
        f = line.split(',')
        try:
            out.setdefault(f[ci], {})[date.fromisoformat(f[ti])] = float(f[vi])
        except (ValueError, IndexError):
            continue
    return out


def rate_for(rates, period, snapshot):
    """Mean ECB rate over the week or month starting at snapshot; else the latest rate before it."""
    if period == 'month':
        nxt = date(snapshot.year + snapshot.month // 12, snapshot.month % 12 + 1, 1)
        end = nxt - timedelta(days=1)
    else:
        end = snapshot + timedelta(days=6)
    inside = [v for d, v in rates.items() if snapshot <= d <= end]
    if inside:
        return mean(inside)
    before = [d for d in rates if d <= end]
    return rates[max(before)] if before else None


def to_local(points, rates):
    """EUR points -> the country's own currency; a point with no rate is dropped."""
    out = []
    for p in points:
        cur = currency_of(p[0])
        if cur == 'EUR':
            out.append(p)
            continue
        r = rate_for(rates.get(cur, {}), p[5], p[6])
        if r:
            out.append(p[:7] + (p[7] * r,) + p[8:])
    return out


def collect(today=None):
    today = today or date.today()
    begin = today - timedelta(days=MAX_AGE_DAYS['month'])
    points = fv_points(fetch('fruitAndVegetable/pricesSupplyChain', begin, today))
    for endpoint in sorted({o[0] for o in OTHER}):
        try:
            points += other_points(endpoint, fetch(endpoint, begin, today))
        except Exception as e:
            print(f'  {endpoint}: could not fetch ({e})', file=sys.stderr)
    points = [p for p in points if (p[0], p[2]) not in SKIP]
    foreign = {currency_of(p[0]) for p in points} - {'EUR'}
    rates = ecb_rates(foreign, begin - timedelta(days=10), today)
    return latest_figures(to_local(points, rates), today)


def run(dry_run=False):
    groups = collect()
    if not groups:
        raise RuntimeError('EU agri-food portal returned no usable prices — the API has changed')
    total = 0
    for (country, stage), figs in sorted(groups.items()):
        cur = currency_of(country)
        name = SOURCE_NAME + ('' if cur == 'EUR' else CONVERTED)
        if dry_run:
            for f in sorted(figs, key=lambda f: f.name):
                print(f'  {country} {stage:9} {f.name:24} {f.price:>9.3f} {cur}/{f.unit:5} {f.snapshot}')
            continue
        taken = taken_by_others(country, stage, figs, name)
        keep = [f for f in figs if (f.name, f.unit, f.snapshot) not in taken]
        if len(keep) < len(figs):
            print(f'  {country} {stage}: {len(figs) - len(keep)} left to the national source already stored')
        if keep:
            n, _ = common.write(country, name, stage, keep, currency=cur)
            total += n
    return total


if __name__ == '__main__':
    run(dry_run='--dry-run' in sys.argv)
