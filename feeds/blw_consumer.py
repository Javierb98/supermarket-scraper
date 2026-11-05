"""
Switzerland (and Liechtenstein): monthly consumer prices from the Federal
Office for Agriculture (BLW/OFAG/UFAG) market observation.

A feed, not a scrape. BLW publishes its market figures as linked-data cubes
on LINDAS, the federal linked-data service, and we read them with one SPARQL
query per cube:

    FruitsVegetablesPotatoes/Consumption_Price_Month   fruit, veg, potatoes, mushrooms
                                                        Switzerland + the three language regions
    MilkDairyProducts/Consumption_Price_Month          milk, cream, butter, yoghurt, cheese
    Eggs/Consumption_Price_Month                       eggs (in Rappen per egg)

Prices are shop shelf prices ("ab Detailhandel"), VAT included: stage retail.
The whole country is stored with no region; the language regions under a
readable name. Liechtenstein, too small for a figure of its own, is given
the German-speaking figure (the Swiss one where there is none), labelled as
Swiss in source_name.

Terms: Swiss open government data, "open use, must provide the source"
(https://opendata.swiss/en/terms-of-use#terms_by). Source: BLW, agrarmarktdaten.ch.

    python feeds/blw_consumer.py              the last 12 months
    python feeds/blw_consumer.py --months 3
"""

import argparse
import os
import sys
import urllib.parse
from collections import defaultdict
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, get_json, write
from utils.db import get_connection

ENDPOINT = 'https://ld.admin.ch/query'
CUBE = 'https://agriculture.ld.admin.ch/foag/cube/'
PRODUCT = 'https://agriculture.ld.admin.ch/foag/product/'

SOURCE_NAME = 'BLW market observation, consumer prices (LINDAS)'
SOURCE_NAME_LI = 'BLW market observation, consumer prices (Swiss figures, LINDAS)'

# BLW's sales regions -> ours. Switzerland is the national figure: no region.
REGIONS = {
    'https://agriculture.ld.admin.ch/foag/sales-region/1': None,
    'https://agriculture.ld.admin.ch/foag/sales-region/L4-10005': 'German-speaking Switzerland',
    'https://agriculture.ld.admin.ch/foag/sales-region/L4-10006': 'French-speaking Switzerland',
    'https://agriculture.ld.admin.ch/foag/sales-region/L4-10007': 'Italian-speaking Switzerland',
}
LI_FROM = 'German-speaking Switzerland'

INCL_VAT = 'https://agriculture.ld.admin.ch/foag/cost-component/1'
EXCL_VAT = 'https://agriculture.ld.admin.ch/foag/cost-component/2'

# BLW product id -> (catalogue name, organic?, divisor[, our unit]).
#
# organic says which production system the row must be: BLW gives organic
# fruit and veg their own product ids, but dairy shares one id between "Bio"
# and "Konventionell", so the system is checked on every row either way.
# The divisor turns the published unit into ours (a 3-piece pack -> a piece;
# per egg -> per dozen is a divisor of 1/12; Rappen -> francs is done from the
# currency on each row, see to_francs).
#
# Several varieties mapped to one catalogue name (apples, pears, cherries,
# melons, potatoes) are averaged, their spread kept as low/high. BLW's own
# group averages ("Übrige", "alle Produktionssysteme" mixes of packs and
# imports) are left out, as are products the catalogue does not have
# (apricots, nectarines, white cabbage, iceberg, lamb's lettuce, Swiss hard
# cheeses other than Emmental/Edam, oils, flour, bread).
FRUIT_VEG = {
    # fruit
    1439: ('Pineapple', False, 1),            # per piece
    1440: ('Avocado', False, 1),              # per piece
    1253: ('Banana', False, 1),
    1136: ('Pears', False, 1),                # Conférence I
    1143: ('Pears', False, 1),                # Gute Luise I
    1173: ('Pears', False, 1),                # Williams I
    1469: ('Pears', False, 1),                # Abate Fetel I
    1152: ('Pears', False, 1),                # Kaiser I
    1258: ('Oranges', False, 1),              # Blondorangen
    1479: ('Blood Oranges', False, 1),
    1262: ('Blackberries', False, 1),
    1268: ('Clementine', False, 1),
    1271: ('Strawberries', False, 1),         # Inland only: what a Swiss farm competes with
    1276: ('Blueberries', False, 1),
    1277: ('Raspberry', False, 1),
    1278: ('Red Currant', False, 1),
    1215: ('Cherries', False, 1),             # 24 mm+
    1221: ('Cherries', False, 1),             # 28 mm+
    1024: ('Kiwi', False, 1),                 # per piece
    1442: ('Mango', False, 1),                # per piece
    1443: ('Melon', False, 1),                # Charentais, per piece
    1027: ('Melon', False, 1),                # Galia, per piece
    1485: ('Peaches', False, 1),
    1441: ('Persimmon', False, 1),            # Kaki Persimon, per piece
    1012: ('Green Grapes Seedless', False, 1),
    1445: ('Lemons', False, 1),               # per piece
    1018: ('Plums', False, 1),                # Zwetschgen
    1039: ('Apples', False, 1),               # Boskoop I
    1050: ('Apples', False, 1),               # Braeburn I
    1061: ('Apples', False, 1),               # Gala I
    1070: ('Apples', False, 1),               # Golden I
    1084: ('Apples', False, 1),               # Gravensteiner I
    1079: ('Apples', False, 1),               # Granny Smith I
    1102: ('Apples', False, 1),               # Jazz
    1477: ('Pink Lady Apples', False, 1),
    # vegetables
    1245: ('Eggplant', False, 1),
    1259: ('Cauliflower', False, 1),
    1261: ('Broccoli', False, 1),
    1263: ('Endive', False, 1),               # Brüsseler Witloof
    1029: ('Spring Onions', False, 1),        # Bundzwiebeln, per bunch
    1264: ('White Mushroom', False, 1),       # Champignons weiss
    1265: ('Napa Cabbage', False, 1),
    1267: ('Radicchio', False, 1),            # Cicorino rot
    1020: ('Oak Leaf Lettuce', False, 1),     # per head
    1272: ('Fennel', False, 1),
    1273: ('Potato', False, 1),               # firm (line green)
    1283: ('Potato', False, 1),               # floury (line blue)
    1482: ('Potato', False, 1),               # line red
    1289: ('Mini Potatoes', False, 1),        # Raclettekartoffeln
    1279: ('Carrot', False, 1),
    1481: ('Garlic', False, 1),
    1280: ('Celeriac', False, 1),
    1025: ('Kohlrabi', False, 1),             # per piece
    1281: ('Swiss Chard', False, 1),          # Krautstiele
    1282: ('Leek', False, 1),
    1444: ('Mini Romaine', False, 3),         # Mini Lattich, pack of 3 -> per head
    1288: ('Bell Pepper', False, 1),
    1484: ('Plum Tomatoes', False, 1),        # Perettitomaten
    1480: ('Grape Tomatoes', False, 1),       # Datteltomaten
    1030: ('Radish', False, 1),               # Radieschen, per bunch
    999:  ('Brussels Sprouts', False, 1),
    1000: ('Red Cabbage', False, 1),
    1001: ('Arugula', False, 1),
    1028: ('Cucumber', False, 1),             # per piece
    1003: ('Celery', False, 1),               # Stangensellerie
    1008: ('Spinach', False, 1),
    1437: ('Sweet Potato', False, 1),
    1009: ('Cherry Tomato', False, 1),
    1438: ('Cherry Tomatoes Mix', False, 1),
    1010: ('Beefsteak Tomatoes', False, 1),
    1011: ('Vine Tomatoes', False, 1),        # Rispentomaten ...
    1014: ('Savoy Cabbage', False, 1),        # Wirz
    1015: ('Zucchini', False, 1),
    1019: ('Onion', False, 1),                # Zwiebeln gelb
    1005: ('Green Asparagus', False, 1),      # Inland
    1436: ('White Asparagus', False, 1),      # Inland
    # organic, only where the catalogue has an organic product
    1064: ('Organic Spinach', True, 1),
    1131: ('Organic Chard', True, 1),
    1067: ('Organic Tomatoes', True, 1),      # Rispentomaten, Bio
    1083: ('Organic Lettuce', True, 1),       # Kopfsalat grün, Bio, per head
}
# ... and the Rispentomate is also the everyday Swiss tomato.
ALSO = {1011: 'Tomato'}

DAIRY = {
    292: ('Whole Milk', False, 1),            # Vollmilch pasteurised, per litre
    322: ('Skim Milk', False, 1),             # Magermilch UHT, per litre
    283: ('Whole Cream', False, 1),           # Vollrahm 35 %, per litre
    285: ('Half & Half', False, 1),           # Kaffeerahm 15 %, per litre
    328: ('Butter', False, 1),                # Vorzugsbutter
    296: ('Yogurt', False, 1),                # Joghurt nature, per kg
    317: ('Fresh Cottage Cheese', False, 1),  # Hüttenkäse
    311: ('Mozzarella', False, 1),
    330: ('Edam Cheese', False, 1),
    316: ('Swiss Cheese', False, 1),          # Emmentaler mild
}
ALSO_DAIRY = {283: 'Cream'}

EGGS = {
    163: ('Eggs', None, 1 / 12, 'dozen'),     # all systems, raw, Swiss; per egg -> per dozen
}

CUBES = [
    ('FruitsVegetablesPotatoes/Consumption_Price_Month', FRUIT_VEG, ALSO),
    ('MilkDairyProducts/Consumption_Price_Month', DAIRY, ALSO_DAIRY),
    ('Eggs/Consumption_Price_Month', EGGS, {}),
]

UNITS = {'kg': 'kg', 'liter': 'l', 'litre': 'l', 'l': 'l', 'stück': 'unit', 'bund': 'unit'}

QUERY = """
PREFIX cube: <https://cube.link/>
PREFIX schema: <http://schema.org/>
PREFIX d: <https://agriculture.ld.admin.ch/foag/dimension/>
SELECT ?product ?date ?region ?origin ?cost ?system ?unit ?currency ?price WHERE {
  <%(cube)s> cube:observationSet/cube:observation ?o .
  ?o d:product ?product ; d:date ?date ; d:sales-region ?region ;
     <https://agriculture.ld.admin.ch/foag/measure/price> ?price .
  VALUES ?product { %(products)s }
  FILTER(STR(?date) >= "https://ld.admin.ch/time/month/%(since)s")
  OPTIONAL { ?o d:cost-component ?cost }
  OPTIONAL { ?o d:product-origin ?origin }
  OPTIONAL { ?o d:production-system/schema:name ?system FILTER(LANG(?system) = "de") }
  OPTIONAL { ?o d:unit/schema:name ?unit FILTER(LANG(?unit) = "de") }
  OPTIONAL { ?o d:currency/schema:name ?currency FILTER(LANG(?currency) = "de") }
}
"""


def sparql(query):
    """Rows of a SELECT as dicts of plain strings."""
    body = urllib.parse.urlencode({'query': query}).encode()
    res = get_json(ENDPOINT, data=body, headers={
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/sparql-results+json',
    }, timeout=120)
    return [{k: v['value'] for k, v in b.items()} for b in res['results']['bindings']]


def months_back(n, today=None):
    today = today or date.today()
    y, m = today.year, today.month - n
    while m <= 0:
        y, m = y - 1, m + 12
    return f'{y:04d}-{m:02d}'


def to_francs(price, currency):
    """CHF as is; Rappen / centimes / 1/100; anything else (Eurocent) is not ours."""
    c = (currency or 'CHF').strip().lower()
    if c == 'chf':
        return price
    if c in ('rappen', 'rp.', 'centime', 'centesimo'):
        return price / 100.0
    return None


def is_organic(system):
    return (system or '').strip().lower() in ('bio', 'biologisch')


def figures(cube, mapping, also, since, regions, want_vat=INCL_VAT, origins=None):
    """One cube's rows -> Figures, varieties of one catalogue product averaged.

    origins, when given, keeps only rows of those product-origin IRIs (the
    milk producer cube files its five milk regions under origin).
    """
    query = QUERY % {
        'cube': CUBE + cube,
        'products': ' '.join(f'<{PRODUCT}{pid}>' for pid in mapping),
        'since': since,
    }
    rows = sparql(query)

    # (name, region, month) -> {pid: price}; per pid one price (the VAT basis we want).
    picked = {}
    for r in rows:
        pid = int(r['product'].rsplit('/', 1)[1])
        name, organic, divisor = mapping[pid][:3]
        unit_as = mapping[pid][3] if len(mapping[pid]) > 3 else None
        if r['region'] not in regions:
            continue
        if origins is not None and r.get('origin') not in origins:
            continue
        if organic is not None and is_organic(r.get('system')) != organic:
            continue
        unit = UNITS.get((r.get('unit') or '').strip().lower())
        price = to_francs(float(r['price']), r.get('currency'))
        if unit is None or price is None or price <= 0:
            continue
        unit = unit_as or unit
        price = price / divisor
        month = r['date'].rsplit('/', 1)[1]
        key = (pid, r['region'], month, unit)
        cost = r.get('cost')
        # Prefer the VAT basis asked for; take the other only when it is all there is.
        rank = 0 if cost == want_vat or cost is None else 1
        if key not in picked or rank < picked[key][0]:
            picked[key] = (rank, price)

    grouped = defaultdict(list)
    for (pid, region, month, unit), (_, price) in picked.items():
        names = [mapping[pid][0]] + ([also[pid]] if pid in also else [])
        for name in names:
            grouped[(name, regions[region], month, unit)].append(price)

    out = []
    for (name, region, month, unit), prices in grouped.items():
        y, m = month.split('-')
        out.append(Figure(
            name=name, price=sum(prices) / len(prices), unit=unit,
            snapshot=date(int(y), int(m), 1), region=region,
            low=min(prices), high=max(prices),
        ))
    return out


def replace(country, source_name, stage, figs):
    """
    Clear this feed's own rows for the months it is about to write, then write.

    The table's unique key includes region, and MySQL never treats two NULLs
    as equal, so a national row (region NULL) would be inserted again on
    every run instead of updated. Deleting our own rows first keeps a re-run
    idempotent without touching anyone else's.
    """
    months = sorted({f.snapshot for f in figs})
    if months:
        conn = get_connection()
        try:
            with conn.cursor() as c:
                c.execute(
                    'DELETE FROM market_average WHERE country = %s AND source_name = %s '
                    'AND price_stage = %s AND snapshot_date IN (' + ','.join(['%s'] * len(months)) + ')',
                    [country, source_name[:120], stage] + months,
                )
            conn.commit()
        except Exception as e:  # a missing table on a first run is fine: write() creates it
            print(f'  (could not clear old rows: {e})', file=sys.stderr)
        finally:
            conn.close()
    return write(country, source_name, stage, figs)


def for_liechtenstein(figs):
    """The German-speaking figure for each product and month, else the Swiss one; no region."""
    best = {}
    for f in figs:
        key = (f.name, f.snapshot, f.unit)
        if f.region == LI_FROM or (f.region is None and key not in best):
            best[key] = f
    return [Figure(f.name, f.price, f.unit, f.snapshot, None, f.low, f.high, f.samples)
            for f in best.values()]


def run(months=12):
    since = months_back(months)
    figs = []
    for cube, mapping, also in CUBES:
        got = figures(cube, mapping, also, since, REGIONS)
        print(f'  {cube}: {len(got)} figures since {since}')
        figs.extend(got)
    if not figs:
        raise RuntimeError('BLW/LINDAS returned no consumer prices: the cubes or the endpoint have changed')
    written, _ = replace('CH', SOURCE_NAME, 'retail', figs)
    replace('LI', SOURCE_NAME_LI, 'retail', for_liechtenstein(figs))
    return written


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--months', type=int, default=12)
    run(ap.parse_args().months)
