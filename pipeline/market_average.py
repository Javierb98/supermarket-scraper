"""
Priced products → one typical price per product, unit, country and region.

What it does differently from the first version, and why:

  The typical price is the median, not the mean. One odd product (a 70 g
  bag of dehydrated tomato among fresh ones) moved a mean by a third; it
  barely moves a median. Prices far outside the middle half
  (1.5 × the interquartile range) are left out of the low–high range too.

  A product counts once, not once per shop. Mercadona prices the same
  "Huevos grandes L, 12 uds" identically in all 34 postcodes it is scraped
  from; that was 34 "samples" of one price. Now each distinct product is
  one sample (the median of its prices across the area), and sample_count
  says how many different products the figure rests on.

  An offer is counted at its regular price. A week of strawberries on
  promotion is not what strawberries cost.

  The country figure is drawn from every shop in the country. Before, it
  came only from the shops that do not report a region, so Spain's national
  price ignored Mercadona entirely.

  Every row says what kind of price it is (price_stage: retail here; the
  official feeds add wholesale and farmers'-market prices) and its currency.
"""

import os
import sys
from collections import defaultdict
from datetime import timedelta
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection, ensure_market_average_schema

# Prices gathered by someone else are credited to them on every figure.
CREDITS = {'NL': ' (via checkjebon.nl)'}

# A weekly run can straddle midnight, and chains are scraped one after the
# other: everything within this many days of the newest row is one snapshot.
WINDOW_DAYS = 3

BASES = [('per_kg', 'kg'), ('per_l', 'l'), ('per_dozen', 'dozen'), ('per_unit', 'unit')]

# What each kind of product is sensibly priced by. A strawberry "per litre"
# (a strawberry drink that slipped through) or eggs "per kilo" is a figure
# no farm would compare itself with.
ALLOWED = {
    'vegetables':   {'kg', 'unit'},
    'fruit':        {'kg', 'unit'},
    'h/s':          {'kg', 'unit'},
    'eggs':         {'dozen'},
    'dairy':        {'kg', 'l'},
    'meat':         {'kg'},
    'poultry':      {'kg', 'unit'},
    'canned_goods': {'kg', 'l', 'unit'},
}


def trimmed(values):
    """The values without the far outliers (Tukey's fences)."""
    if len(values) < 4:
        return sorted(values)
    v = sorted(values)
    q1, q3 = v[len(v) // 4], v[(3 * len(v)) // 4]
    iqr = q3 - q1
    lo, hi = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return [x for x in v if lo <= x <= hi]


def observations(row):
    """(basis, price) pairs one priced product contributes, at its regular price."""
    factor = 1.0
    if row['is_promo'] and row['regular_price'] and row['price']:
        factor = float(row['regular_price']) / float(row['price'])
    allowed = ALLOWED.get(row['category'], {'kg', 'l', 'dozen', 'unit'})
    out = []
    for col, basis in BASES:
        v = row.get(col)
        if basis in allowed and v is not None and float(v) > 0:
            out.append((basis, round(float(v) * factor, 4)))
    return out


def summarise(rows):
    """
    rows → {(product, basis, region-or-None): stats}

    Each distinct product (chain + shelf name) becomes one sample per area.
    """
    per_product = defaultdict(list)     # (catalog name, basis, region, chain, raw_name) → prices
    meta = {}
    for r in rows:
        for basis, price in observations(r):
            for region in {r['region'], None}:
                key = (r['canonical_name'], basis, region, r['chain'], r['raw_name'])
                per_product[key].append(price)
        meta[r['canonical_name']] = (r['catalog_product_id'], r['category'], r['currency'])

    samples = defaultdict(list)
    chains = defaultdict(set)
    for (name, basis, region, chain, _), prices in per_product.items():
        samples[(name, basis, region)].append(median(prices))
        chains[(name, basis, region)].add(chain)

    out = {}
    for key, values in samples.items():
        kept = trimmed(values)
        if not kept:
            continue
        out[key] = {
            'median': round(median(kept), 4),
            'min': round(min(kept), 4),
            'max': round(max(kept), 4),
            'n': len(kept),
            'chains': sorted(chains[key]),
            'meta': meta[key[0]],
        }
    return out


UPSERT = """
INSERT INTO market_average
    (catalog_product_id, canonical_name, category, country, region, source, source_name,
     price_stage, currency, snapshot_date, avg_price, min_price, max_price, standard_unit, sample_count)
VALUES (%s, %s, %s, %s, %s, 'scrape', %s, 'retail', %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    catalog_product_id = VALUES(catalog_product_id), category = VALUES(category),
    source = VALUES(source), source_name = VALUES(source_name), currency = VALUES(currency),
    avg_price = VALUES(avg_price), min_price = VALUES(min_price), max_price = VALUES(max_price),
    sample_count = VALUES(sample_count)
"""


def run(only=None):
    conn = get_connection()
    try:
        ensure_market_average_schema(conn)
        with conn.cursor() as c:
            c.execute("SELECT country, MAX(scrape_date) AS d FROM products_normalized WHERE scrape_date IS NOT NULL GROUP BY country")
            latest = {r['country']: r['d'] for r in c.fetchall()}

        for country, snapshot in sorted(latest.items()):
            if only and country != only:
                continue
            with conn.cursor() as c:
                c.execute("""
                    SELECT canonical_name, catalog_product_id, category, currency, chain, raw_name, region,
                           price, is_promo, regular_price, per_kg, per_l, per_dozen, per_unit
                    FROM products_normalized
                    WHERE country = %s AND scrape_date BETWEEN %s AND %s AND matched_by IS NOT NULL
                """, (country, snapshot - timedelta(days=WINDOW_DAYS), snapshot))
                rows = c.fetchall()
            stats = summarise(rows)

            with conn.cursor() as c:
                # The snapshot is rebuilt whole: a product the new rules no
                # longer match must not keep last run's figure.
                c.execute("DELETE FROM market_average WHERE country = %s AND snapshot_date = %s AND source = 'scrape'", (country, snapshot))
                c.executemany(UPSERT, [
                    (s['meta'][0], name, s['meta'][1], country, region, (', '.join(s['chains']) + CREDITS.get(country, ''))[:120],
                     s['meta'][2], snapshot, s['median'], s['min'], s['max'], basis, s['n'])
                    for (name, basis, region), s in stats.items()
                ])
            conn.commit()

            national = sum(1 for k in stats if k[2] is None)
            print(f"{country} {snapshot}: {len(rows)} priced rows → {national} national and "
                  f"{len(stats) - national} regional figures")
    finally:
        conn.close()


if __name__ == '__main__':
    run(sys.argv[sys.argv.index('--country') + 1].upper() if '--country' in sys.argv else None)
