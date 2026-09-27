"""
Canada: monthly average retail food prices from Statistics Canada.

A feed, not a scrape, and kept apart from scrapers/ for that reason. Nothing
here reads a shop's pages: table 18-10-0245 is a published statistic, free,
without a key, covering 110 products across Canada and every province, monthly
since 2017.

It is better than anything we could gather ourselves there. The figures are
already averaged from a survey whose method is documented, and they come with
the provinces broken out — so Canada gets both halves of what the site wants,
a national fallback and a genuinely local figure, from one source.

    geo 11  = Canada            -> stored with no region, the national fallback
    geo 1-10 = the provinces    -> stored as the region

Because it is already averaged it carries no observation count, and the site
knows not to ask for one: rows land with source='official' and are published
on their age rather than on a tally we were never given.

    python feeds/statcan.py
"""

import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection

API = 'https://www150.statcan.gc.ca/t1/wds/rest/getDataFromCubePidCoordAndLatestNPeriods'
PRODUCT_ID = 18100245
SOURCE_NAME = 'Statistics Canada, table 18-10-0245'

# memberId 11 is the country; the rest are where people actually live.
GEOGRAPHIES = [
    (11, None),                      # Canada — the national fallback
    (1,  'Newfoundland and Labrador'),
    (2,  'Prince Edward Island'),
    (3,  'Nova Scotia'),
    (4,  'New Brunswick'),
    (5,  'Quebec'),
    (6,  'Ontario'),
    (7,  'Manitoba'),
    (8,  'Saskatchewan'),
    (9,  'Alberta'),
    (10, 'British Columbia'),
]

# StatCan product -> the canonical name the site already uses, the unit the
# price should end up in, and what to divide by to get there.
#
# The divisor is the point of the third column: StatCan prices butter by the
# 454g block and cheese by the 500g one, and a farm sells butter by the kilo.
# Comparing a farm's kilo against a shop's half-kilo would make every farm in
# Canada look twice as expensive as it is.
PRODUCTS = [
    # (memberId, canonical name, category, unit, divisor)
    (20, 'Eggs',            'eggs',  'dozen', 1.0),
    (21, 'Apples',          'fruit', 'kg',    1.0),
    (22, 'Oranges',         'fruit', 'kg',    1.0),
    (24, 'Bananas',         'fruit', 'kg',    1.0),
    (25, 'Pears',           'fruit', 'kg',    1.0),
    (27, 'Grapes',          'fruit', 'kg',    1.0),
    (46, 'Potatoes',        'veg',   'kg',    1.0),
    (47, 'Sweet Potatoes',  'veg',   'kg',    1.0),
    (31, 'Tomatoes',        'veg',   'kg',    1.0),
    (32, 'Cabbage',         'veg',   'kg',    1.0),
    (34, 'Onions',          'veg',   'kg',    1.0),
    (40, 'Peppers',         'veg',   'kg',    1.0),
    (85, 'Squash',          'veg',   'kg',    1.0),
    (48, 'Iceberg Lettuce', 'veg',   'unit',  1.0),
    (49, 'Romaine Lettuce', 'veg',   'unit',  1.0),
    (13, 'Milk',            'dairy', 'l',     1.0),     # sold by the litre
    (16, 'Cream',           'dairy', 'l',     1.0),
    (17, 'Butter',          'dairy', 'kg',    0.454),   # 454 g block
    (18, 'Cheese',          'dairy', 'kg',    0.5),     # 500 g block
    (19, 'Yogurt',          'dairy', 'kg',    0.5),     # 500 g pot
    (4,  'Ground Beef',     'meat',  'kg',    1.0),
    (1,  'Beef Stewing',    'meat',  'kg',    1.0),
    (5,  'Pork Loin',       'meat',  'kg',    1.0),
    (42, 'Pork Shoulder',   'meat',  'kg',    1.0),
    (7,  'Whole Chicken',   'meat',  'kg',    1.0),
    (8,  'Chicken Breast',  'meat',  'kg',    1.0),
    (9,  'Chicken Thigh',   'meat',  'kg',    1.0),
    (78, 'Salmon',          'meat',  'kg',    1.0),
]

UPSERT = """
INSERT INTO market_average
    (canonical_name, category, country, region, source, source_name,
     snapshot_date, avg_price, min_price, max_price, standard_unit, sample_count)
VALUES (%s, %s, 'CA', %s, 'official', %s, %s, %s, %s, %s, %s, 0)
ON DUPLICATE KEY UPDATE
    avg_price   = VALUES(avg_price),
    min_price   = VALUES(min_price),
    max_price   = VALUES(max_price),
    source      = VALUES(source),
    source_name = VALUES(source_name)
"""


def fetch(geo_id, product_id, retries=3):
    """One figure: the latest month for this product in this geography."""
    body = json.dumps([{
        'productId': PRODUCT_ID,
        'coordinate': f'{geo_id}.{product_id}.0.0.0.0.0.0.0.0',
        'latestN': 1,
    }]).encode()

    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                API, data=body,
                headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            )
            with urllib.request.urlopen(req, timeout=30) as r:
                payload = json.load(r)[0]
        except Exception as e:
            if attempt == retries - 1:
                print(f'  geo {geo_id} product {product_id}: {e}', file=sys.stderr)
                return None
            time.sleep(2 ** attempt)
            continue

        if payload.get('status') != 'SUCCESS':
            return None

        points = (payload.get('object') or {}).get('vectorDataPoint') or []
        if not points:
            return None

        point = points[0]
        value = point.get('value')

        # A suppressed or unavailable figure comes back as a null value rather
        # than an error, and must not be stored as a price of nothing.
        if value is None:
            return None

        return point.get('refPer'), float(value)

    return None


def run():
    conn = get_connection()
    written = skipped = 0

    try:
        for geo_id, region in GEOGRAPHIES:
            where = region or 'Canada (national)'
            print(f'--- {where} ---')

            for product_id, name, category, unit, divisor in PRODUCTS:
                got = fetch(geo_id, product_id)

                if got is None:
                    skipped += 1
                    continue

                ref_period, value = got
                price = round(value / divisor, 4)
                snapshot = datetime.strptime(ref_period, '%Y-%m-%d').date()

                with conn.cursor() as cursor:
                    # min and max are the same figure: an average is all the
                    # source gives, and inventing a spread around it would be
                    # making up a range nobody measured.
                    cursor.execute(UPSERT, (
                        name, category, region, SOURCE_NAME,
                        snapshot, price, price, price, unit,
                    ))

                written += 1
                print(f'  {name:16} {price:>8.2f} /{unit:5} {snapshot}')

                # Unhurried: this is somebody's public service.
                time.sleep(0.4)

            conn.commit()

        print(f'\nStatistics Canada: {written} figures written, {skipped} unavailable.')

        if written == 0:
            raise RuntimeError('Statistics Canada returned nothing at all — the table or the API has changed')

        return written

    finally:
        conn.close()


if __name__ == '__main__':
    run()
