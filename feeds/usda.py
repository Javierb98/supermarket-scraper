"""
United States: retail food prices from USDA Market News.

A feed, not a scrape. Walmart answers 418 behind an Akamai wall and Kroger
wants a key, but the USDA surveys more than 270 retailers across some 29,000
stores every week and publishes the result — by region, which is what the
site needs and what no American chain will hand over.

Authentication is an API key used as the username of an HTTP Basic pair, with
an empty password. It is free on registration at mymarketnews.ams.usda.gov
and lives in .env as USDA_API_KEY.

Run it with no arguments to load prices. Run it with `explore` to print what
the API actually returns without writing anything:

    python feeds/usda.py explore

That mode exists because the shape of these reports is documented loosely and
guessing at it is how you end up storing nonsense. Look first, then map.

What it found, for the next person: the data is not in the report itself —
every row there is header. It lives in a named section, `Report by Region`,
which is slow enough to need a minute's patience, and the response is capped
at 100,000 rows taken from the *oldest* end, so a date filter is not optional:

    ?q=report_begin_date=09/19/2026

Nine regions come back — National plus eight — with a weighted average price,
the number of stores advertising, a pack size, and an organic flag.
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection, ensure_market_average_schema

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass

BASE = 'https://marsapi.ams.usda.gov/services/v1.2'
SOURCE_NAME = 'USDA Market News'

# The weekly advertised retail prices for fruit and vegetables, broken out by
# region. This is the report the whole feed exists for.
RETAIL_SLUG = 'FVWRETAIL'


def api_key():
    key = (os.getenv('USDA_API_KEY') or '').strip()

    if not key or key == 'your_usda_key_here':
        raise SystemExit(
            'USDA_API_KEY is not set. Put it in .env — it is free from\n'
            'mymarketnews.ams.usda.gov and is used as the username of an\n'
            'HTTP Basic pair with an empty password.'
        )

    return key


def get(path, params=None):
    # The section names have spaces in them — "Report by Region" — so the path
    # is quoted, not just the query. Unencoded it reaches http.client as a
    # control character and never leaves the machine.
    url = f'{BASE}/{urllib.parse.quote(path.lstrip("/"))}'

    if params:
        url += '?' + urllib.parse.urlencode(params)

    # Basic auth with the key as the username and nothing as the password.
    token = base64.b64encode(f'{api_key()}:'.encode()).decode()
    req = urllib.request.Request(url, headers={
        'Authorization': f'Basic {token}',
        'Accept': 'application/json',
    })

    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')[:300]
        raise SystemExit(f'USDA {e.code} for {path}: {body}')


def explore():
    """Print the shape of what comes back. Writes nothing."""
    print('=== the report list, filtered to retail ===')
    reports = get('reports')
    rows = reports if isinstance(reports, list) else reports.get('results', [])
    print(f'{len(rows)} reports available')

    for r in rows:
        name = str(r.get('report_name') or r.get('reportName') or '')
        slug = r.get('slug_id') or r.get('slugId') or ''
        if 'retail' in name.lower():
            print(f'   {slug:12} {name[:70]}')

    print(f'\n=== {RETAIL_SLUG}: one page of rows ===')
    data = get(f'reports/{RETAIL_SLUG}', {'q': 'report_begin_date=>01/01/2026'})
    rows = data.get('results', data if isinstance(data, list) else [])
    print(f'{len(rows)} rows')

    if rows:
        print('\ncolumns:')
        for k, v in list(rows[0].items()):
            print(f'   {k:32} {str(v)[:50]}')
        print('\nfirst three rows:')
        for row in rows[:3]:
            print('  ', json.dumps(row, ensure_ascii=False)[:220])


# The retail reports, each a weekly survey of grocery store advertising.
REPORTS = [
    ('3324', 'specialty crops'),   # fruit and vegetables
    ('2757', 'eggs'),
    ('2995', 'dairy'),
    ('3228', 'beef'),
    ('2868', 'pork'),
    ('2756', 'chicken'),
]

# USDA commodity -> the canonical name the site uses, and its category.
COMMODITIES = {
    'Apples': ('Apples', 'fruit'),
    'Oranges': ('Oranges', 'fruit'),
    'Pears': ('Pears', 'fruit'),
    'Grapes': ('Grapes', 'fruit'),
    'Strawberries': ('Strawberries', 'fruit'),
    'Blueberries': ('Blueberries', 'fruit'),
    'Lemons': ('Lemons', 'fruit'),
    'Avocados': ('Avocados', 'fruit'),
    'Mangoes': ('Mangoes', 'fruit'),
    'Tangerines/Mandarins': ('Mandarins', 'fruit'),
    'Potatoes': ('Potatoes', 'veg'),
    'Tomatoes': ('Tomatoes', 'veg'),
    'Onions, Dry': ('Onions', 'veg'),
    'Peppers (Bell Type)': ('Peppers', 'veg'),
    'Lettuce': ('Lettuce', 'veg'),
    'Carrots': ('Carrots', 'veg'),
    'Squash': ('Squash', 'veg'),
    'Cucumbers': ('Cucumbers', 'veg'),
    'Broccoli': ('Broccoli', 'veg'),
    'Mushrooms': ('Mushrooms', 'veg'),
    'Cabbage': ('Cabbage', 'veg'),
    'Sweet Corn': ('Sweet Corn', 'veg'),
    'Eggs': ('Eggs', 'eggs'),
}

LB_PER_KG = 2.2046226

UPSERT = """
INSERT INTO market_average
    (canonical_name, category, country, region, source, source_name,
     snapshot_date, avg_price, min_price, max_price, standard_unit, sample_count)
VALUES (%s, %s, 'US', %s, 'official', %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    avg_price    = VALUES(avg_price),
    min_price    = VALUES(min_price),
    max_price    = VALUES(max_price),
    sample_count = VALUES(sample_count),
    source       = VALUES(source),
    source_name  = VALUES(source_name)
"""


def to_kg(price, size):
    """
    A shelf price and the size it was for, turned into a price per kilo.

    USDA quotes most things "per lb" but plenty by the bag, and a 3 lb bag of
    apples at $3.49 is not $3.49 a pound. Anything whose size cannot be read
    is returned as sold rather than guessed at, because inventing a weight is
    worse than declining to convert.
    """
    if not size:
        return None, None

    text = size.strip().lower()

    if text in ('per lb', 'lb', 'per pound'):
        return round(price * LB_PER_KG, 4), 'kg'

    if text in ('each', 'per each', 'per head', 'per bunch'):
        return round(price, 4), 'unit'

    # "3 lb bag", "5 lb bag", "1 lb package"
    import re
    m = re.match(r'^([\d.]+)\s*lb\b', text)
    if m:
        pounds = float(m.group(1))
        return (round((price / pounds) * LB_PER_KG, 4), 'kg') if pounds > 0 else (None, None)

    # "16 oz", "6 oz package", "24 oz bag"
    m = re.match(r'^([\d.]+)\s*oz\b', text)
    if m:
        ounces = float(m.group(1))
        return (round((price / (ounces / 16.0)) * LB_PER_KG, 4), 'kg') if ounces > 0 else (None, None)

    if 'dozen' in text or text == 'per dozen':
        return round(price, 4), 'dozen'

    return None, None


def to_average(row):
    """One survey row as the arguments of the upsert, or None if unusable."""
    commodity = (row.get('commodity') or '').strip()
    mapped = COMMODITIES.get(commodity)

    if mapped is None:
        return None

    name, category = mapped

    try:
        price = float(row.get('wtd_Avg_Price'))
    except (TypeError, ValueError):
        return None

    if price <= 0:
        return None

    value, unit = to_kg(price, row.get('size'))

    if value is None:
        return None

    # "National" is the fallback figure and is stored with no region, which is
    # how everything else in the table says the same thing.
    region = row.get('region')
    region = None if region in (None, '', 'National') else region

    # Organic is a different product at a different price, and mixing the two
    # would make the average describe neither.
    if (row.get('organic') or 'No').strip().lower() == 'yes':
        name = f'Organic {name}'

    end = row.get('report_end_date')
    snapshot = datetime.strptime(end, '%m/%d/%Y').date()

    # Unlike most official series this one says how many stores it saw, so the
    # count is real rather than zero.
    try:
        stores = max(0, int(row.get('stores_with_Ads') or 0))
    except (TypeError, ValueError):
        stores = 0

    return (name, category, region, SOURCE_NAME, snapshot, value, value, value, unit, stores)


def latest_week(slug):
    """The begin and end dates of the most recently published week."""
    header = get(f'reports/{slug}')
    rows = header if isinstance(header, list) else header.get('results', [])

    if not rows:
        return None

    row = rows[0]
    return row.get('report_begin_date'), row.get('report_end_date')


def run():
    """Load the latest published week of every retail report into market_average."""
    conn = get_connection()
    ensure_market_average_schema(conn)
    written = skipped = 0

    try:
        for slug, what in REPORTS:
            week = latest_week(slug)

            if week is None:
                print(f'{slug} ({what}): no published week found', file=sys.stderr)
                continue

            begin, end = week
            print(f'--- {what}: week ending {end} ---')

            try:
                rows = get(f'reports/{slug}/Report by Region', {'q': f'report_begin_date={begin}'})
            except SystemExit as e:
                print(f'   {e}', file=sys.stderr)
                continue

            rows = rows if isinstance(rows, list) else rows.get('results', [])

            """
               One row per commodity, region and week — not per variety.

               The survey reports every variety and pack size separately:
               Fuji in a 3 lb bag, Gala loose, organic Honeycrisp. Written
               straight through, each would overwrite the last and the stored
               "average" would be whichever variety happened to come last in
               the response.

               So they are combined here, weighted by the number of stores
               advertising each — which is what makes it an average of the
               market rather than an average of the varieties. It also gives
               min and max something real to hold instead of three copies of
               the same figure.
            """
            buckets = {}

            for row in rows:
                mapped = to_average(row)

                if mapped is None:
                    skipped += 1
                    continue

                name, category, region, _src, snapshot, price, _, _, unit, stores = mapped
                key = (name, category, region, snapshot, unit)
                weight = max(stores, 1)          # an unreported count still counts once

                bucket = buckets.setdefault(key, {'total': 0.0, 'stores': 0, 'lo': price, 'hi': price})
                bucket['total'] += price * weight
                bucket['stores'] += weight
                bucket['lo'] = min(bucket['lo'], price)
                bucket['hi'] = max(bucket['hi'], price)

            for (name, category, region, snapshot, unit), b in buckets.items():
                avg = round(b['total'] / b['stores'], 4)

                with conn.cursor() as cursor:
                    cursor.execute(UPSERT, (
                        name, category, region, SOURCE_NAME, snapshot,
                        avg, round(b['lo'], 4), round(b['hi'], 4), unit, b['stores'],
                    ))

                written += 1

            conn.commit()
            print(f'   {len(buckets)} averages from {len(rows)} rows')
            time.sleep(2)

        print(f'\nUSDA: {written} averages written from {skipped + written} usable rows.')

        if written == 0:
            raise RuntimeError('USDA returned nothing usable — the report or its columns have changed')

        return written

    finally:
        conn.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'explore':
        explore()
    else:
        run()
