"""
Raw shelf rows → priced catalogue products.

For each new raw row: read the price (pipeline/prices.py), find the
catalogue product (pipeline/matcher.py), check a fresh product's price comes
from a fresh product, and store the result with the price per kilo, litre,
dozen and piece that could be worked out.

Every raw row gets a status, matched or not, and the rules version it was
judged by. Before, a row that did not match was never marked, so it was
looked at again every week, forever: the "83,179 no match" in the log was
every unmatched row since April, not one week's. Now a row is judged once,
and again only when the rules change (RULES_VERSION) and it is recent enough
to still matter.

    python pipeline/normalize.py            new and recent rows
    python pipeline/normalize.py --report   the week's misses, most common first
"""

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection
from pipeline import prices, processed
from pipeline.countries import currency, language
from pipeline.matcher import Matcher, detect_state, check_fresh

# Raise when the rules, the catalogue or the price readers change, so the
# last fortnight is judged again by the new ones.
RULES_VERSION = 8
RECENT_DAYS = 14

RAW_COLUMNS = [
    ('status',        "VARCHAR(20) NULL"),
    ('rules_version', "SMALLINT NULL"),
]

NORMALIZED_COLUMNS = [
    ('confidence',    "ENUM('high','medium','low') NULL AFTER catalog_product_id"),
    ('review_needed', "TINYINT(1) DEFAULT 0 AFTER confidence"),
    ('region',        "VARCHAR(100) NULL AFTER city"),
    ('country',       "VARCHAR(2) NOT NULL DEFAULT 'ES' AFTER region"),
    ('currency',      "VARCHAR(3) NOT NULL DEFAULT 'EUR' AFTER country"),
    ('matched_by',    "VARCHAR(10) NULL"),
    ('per_kg',        "DECIMAL(10,4) NULL"),
    ('per_l',         "DECIMAL(10,4) NULL"),
    ('per_unit',      "DECIMAL(10,4) NULL"),
    ('per_dozen',     "DECIMAL(10,4) NULL"),
    ('is_promo',      "TINYINT(1) NOT NULL DEFAULT 0"),
    ('regular_price', "DECIMAL(10,4) NULL"),
    ('scrape_date',   "DATE NULL"),
]


def _add_columns(cursor, table, columns):
    for col, definition in columns:
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND COLUMN_NAME = %s
        """, (table, col))
        if cursor.fetchone()['cnt'] == 0:
            cursor.execute(f"ALTER TABLE {table} ADD COLUMN {col} {definition}")
            print(f"  {table}: added {col}")


def _add_index(cursor, table, name, cols):
    cursor.execute("""
        SELECT COUNT(*) AS cnt FROM information_schema.STATISTICS
        WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s AND INDEX_NAME = %s
    """, (table, name))
    if cursor.fetchone()['cnt'] == 0:
        cursor.execute(f"ALTER TABLE {table} ADD INDEX {name} ({cols})")
        print(f"  {table}: added index {name}")


def ensure_schema(conn):
    with conn.cursor() as cursor:
        _add_columns(cursor, 'raw_scrapes', RAW_COLUMNS)
        _add_columns(cursor, 'products_normalized', NORMALIZED_COLUMNS)
        _add_index(cursor, 'raw_scrapes', 'ix_raw_judged', 'scraped_at, rules_version')
        _add_index(cursor, 'products_normalized', 'ix_norm_raw', 'raw_scrape_id')
        _add_index(cursor, 'products_normalized', 'ix_norm_date', 'scrape_date, country')
    conn.commit()


def judge(matcher, row):
    """One raw row → (status, normalized dict or None)."""
    raw_name = row['raw_name'] or ''
    country = (row.get('country') or 'ES').upper()
    lang = language(country)

    price = prices.read(row['chain'], row.get('raw_price'), row.get('raw_unit_price'), raw_name)
    if not price.item and not price.per:
        return 'no_price', None

    product, how, label = matcher.match(raw_name, lang)
    if how == 'rejected':
        return 'rejected', None
    if how == 'not_lead':
        return 'not_lead', None
    if how == 'unlisted':
        return 'unlisted', {'label': label}
    if product is None:
        return 'no_match', None

    state = detect_state(raw_name, lang)
    why = check_fresh(product, raw_name, lang, state)
    if not why and product['category'] in ('vegetables', 'fruit') and processed.aisle_is_fresh(row.get('shop_category')) is False:
        why = 'processed'
    if why:
        return why, None

    basis, value = price.basis()
    if basis is None:
        return 'no_price', None

    return 'ok', {
        'product': product,
        'matched_by': how,
        'state': state,
        'country': country,
        'currency': currency(country),
        'price': price,
        'basis': basis,
        'value': value,
    }


INSERT = """
INSERT INTO products_normalized
    (raw_scrape_id, chain, postal_code, city, region, country, currency,
     category, state, canonical_name, catalog_product_id, confidence, review_needed, matched_by,
     raw_name, price, unit_price, unit, per_kg, per_l, per_unit, per_dozen,
     is_promo, regular_price, scraped_at, scrape_date)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
"""


def run(country=None):
    conn = get_connection()
    matcher = Matcher()
    counts = Counter()
    try:
        ensure_schema(conn)
        with conn.cursor() as c:
            c.execute(f"""
                SELECT * FROM raw_scrapes
                WHERE scraped_at >= NOW() - INTERVAL {RECENT_DAYS} DAY
                  AND (rules_version IS NULL OR rules_version <> %s)
                  {'AND country = %s' if country else ''}
            """, (RULES_VERSION, country) if country else (RULES_VERSION,))
            rows = c.fetchall()
        print(f"{len(rows)} raw rows to judge (rules v{RULES_VERSION})")

        for i in range(0, len(rows), 1000):
            chunk = rows[i:i + 1000]
            ids = [r['id'] for r in chunk]
            with conn.cursor() as c:
                # A row judged by older rules is replaced, not added to.
                c.execute(f"DELETE FROM products_normalized WHERE raw_scrape_id IN ({','.join(['%s'] * len(ids))})", ids)
                inserts, statuses = [], []
                for row in chunk:
                    status, out = judge(matcher, row)
                    counts[status] += 1
                    statuses.append((status, RULES_VERSION, row['id']))
                    if status != 'ok':
                        continue
                    p, pr = out['product'], out['price']
                    sd = row.get('scrape_date') or (row['scraped_at'].date() if row.get('scraped_at') else None)
                    inserts.append((
                        row['id'], row['chain'], row.get('postal_code'), row.get('city'), row.get('region'),
                        out['country'], out['currency'],
                        p['category'], out['state'], p['name'], p['id'],
                        'high' if out['matched_by'] == 'rule' else 'medium', 0, out['matched_by'],
                        row['raw_name'], pr.item, out['value'], out['basis'],
                        pr.per.get('kg'), pr.per.get('l'), pr.per.get('unit'), pr.per.get('dozen'),
                        1 if pr.promo else 0, pr.regular,
                        row.get('scraped_at'), sd,
                    ))
                if inserts:
                    c.executemany(INSERT, inserts)
                c.executemany("UPDATE raw_scrapes SET status = %s, rules_version = %s WHERE id = %s", statuses)
            conn.commit()

        total = sum(counts.values())
        print(f"Done. {total} rows judged:")
        for k, v in counts.most_common():
            print(f"  {k:<10} {v:>7}  {100 * v / max(total, 1):5.1f}%")
    finally:
        conn.close()


def report(limit=40):
    """The most common shelf names of the latest week that priced nothing."""
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute("SELECT MAX(scraped_at) AS m FROM raw_scrapes")
            latest = c.fetchone()['m']
            c.execute("""
                SELECT country, status, raw_name, COUNT(*) AS n FROM raw_scrapes
                WHERE scraped_at >= %s - INTERVAL 4 DAY AND status IN ('no_match', 'unlisted')
                GROUP BY country, status, raw_name ORDER BY n DESC LIMIT %s
            """, (latest, limit))
            for r in c.fetchall():
                print(f"  {r['country']} {r['status']:<9} {r['n']:>4}  {r['raw_name'][:80]}")
    finally:
        conn.close()


def _country_arg():
    if '--country' in sys.argv:
        return sys.argv[sys.argv.index('--country') + 1].upper()
    return None


if __name__ == '__main__':
    report() if '--report' in sys.argv else run(_country_arg())
