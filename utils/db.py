import pymysql
from dotenv import load_dotenv
import os

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def get_connection():
    return pymysql.connect(
        host=os.getenv('DB_HOST', '127.0.0.1'),
        port=int(os.getenv('DB_PORT', 3306)),
        user=os.getenv('DB_USER', 'root'),
        password=os.getenv('DB_PASSWORD'),
        database=os.getenv('DB_NAME', 'scraper_db'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def ensure_raw_schema(conn):
    with conn.cursor() as cursor:
        for col, definition in [
            ('region',     'VARCHAR(100) NULL AFTER city'),
            ('scrape_date', 'DATE NULL AFTER url'),
            # The shop's own aisle for the product, where it says: a search
            # for "cebolla" also finds onion pâté, and the aisle tells them apart.
            ('shop_category', 'VARCHAR(200) NULL AFTER category'),
            ('country', "VARCHAR(2) NOT NULL DEFAULT 'ES' AFTER postal_code"),
        ]:
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME   = 'raw_scrapes'
                  AND COLUMN_NAME  = %s
            """, (col,))
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute(f"ALTER TABLE raw_scrapes ADD COLUMN {col} {definition}")
                print(f"  Added {col} column to raw_scrapes.")

        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME   = 'raw_scrapes'
              AND INDEX_NAME   = 'uq_raw_scrape_day'
        """)
        if cursor.fetchone()['cnt'] == 0:
            cursor.execute("""
                ALTER TABLE raw_scrapes
                ADD UNIQUE KEY uq_raw_scrape_day (chain, raw_name(200), postal_code, scrape_date)
            """)
            print("  Added deduplication key to raw_scrapes.")
    conn.commit()

def save_raw(conn, chain, store_name, postal_code, city, region, category, raw_name, raw_price, raw_unit_price, url,
             shop_category=None, country='ES'):
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT IGNORE INTO raw_scrapes
                (chain, store_name, postal_code, country, city, region, category, shop_category,
                 raw_name, raw_price, raw_unit_price, url, scrape_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE())
        """, (chain, store_name, postal_code, country, city, region, category, (shop_category or None) and shop_category[:200],
              raw_name, raw_price, raw_unit_price, url))


def ensure_market_average_schema(conn):
    """
    Bring market_average up to what everything writing to it expects.

    Three things write here now — the aggregation of our own scrapes, and the
    Canadian and American feeds — and each used to assume the table already
    looked right. It did not: region was added by the aggregation step alone,
    which had been failing since April, so a feed run first met a table
    without it.

    Order matters. The unique key names region, so the column has to exist
    before the key is created or the ALTER fails with 1072 and takes the whole
    run with it.
    """
    with conn.cursor() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_average (
                id                  INT AUTO_INCREMENT PRIMARY KEY,
                catalog_product_id  INT           NULL,
                canonical_name      VARCHAR(255)  NOT NULL,
                category            VARCHAR(100),
                country             VARCHAR(2)    NOT NULL DEFAULT 'ES',
                snapshot_date       DATE          NOT NULL,
                avg_price           DECIMAL(10,4) NOT NULL,
                min_price           DECIMAL(10,4) NOT NULL,
                max_price           DECIMAL(10,4) NOT NULL,
                standard_unit       VARCHAR(20)   NOT NULL,
                sample_count        INT           NOT NULL,
                created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP
            ) CHARACTER SET utf8mb4
        """)

        # Columns first, every time, before anything that references them.
        #
        # The widths match Evocultiva's entity mapping, which is what the site
        # reads these rows back through. A column wider here than the mapping
        # there is a value the site would accept and then fail to store.
        for column, definition in [
            ('region',      "VARCHAR(60) NULL AFTER country"),
            ('source',      "VARCHAR(30) NOT NULL DEFAULT 'scrape' AFTER region"),
            ('source_name', "VARCHAR(120) NULL AFTER source"),
            # What kind of price: 'retail' (a shop shelf), 'wholesale' (a
            # wholesale market), 'farmers_market', 'farmgate' (paid to the
            # producer). They are different prices and are never averaged
            # together or shown as one another.
            ('price_stage', "VARCHAR(20) NOT NULL DEFAULT 'retail' AFTER source_name"),
            ('currency',    "VARCHAR(3) NOT NULL DEFAULT 'EUR' AFTER price_stage"),
        ]:
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME   = 'market_average'
                  AND COLUMN_NAME  = %s
            """, (column,))
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute(f"ALTER TABLE market_average ADD COLUMN {column} {definition}")
                print(f"  market_average: added {column}")

        # Older keys that did not know about region, which would collide the
        # moment two regions reported the same product on the same day.
        for stale in ('uq_product_date', 'uq_product_date_unit', 'uq_product_date_unit_region'):
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME   = 'market_average'
                  AND INDEX_NAME   = %s
            """, (stale,))
            if cursor.fetchone()['cnt'] > 0:
                cursor.execute(f"ALTER TABLE market_average DROP INDEX {stale}")
                print(f"  market_average: dropped {stale}")

        # A national figure has no region, and MySQL never treats two NULLs
        # as equal, so a unique key on region let the same national figure
        # in twice (every re-run of a feed, every retried push). The key is
        # on region_key instead: the region, or '' for the whole country.
        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'market_average' AND COLUMN_NAME = 'region_key'
        """)
        if cursor.fetchone()['cnt'] == 0:
            cursor.execute("""
                DELETE a FROM market_average a JOIN market_average b
                  ON a.canonical_name = b.canonical_name AND a.country = b.country
                 AND a.region IS NULL AND b.region IS NULL AND a.snapshot_date = b.snapshot_date
                 AND a.standard_unit = b.standard_unit AND a.price_stage = b.price_stage AND a.id < b.id
            """)
            print(f"  market_average: removed {cursor.rowcount} duplicate national rows")
            cursor.execute("ALTER TABLE market_average ADD COLUMN region_key VARCHAR(60) "
                           "AS (COALESCE(region, '')) STORED AFTER region")
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM information_schema.STATISTICS
                WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'market_average' AND INDEX_NAME = 'uq_market_figure'
            """)
            if cursor.fetchone()['cnt'] > 0:
                cursor.execute("ALTER TABLE market_average DROP INDEX uq_market_figure")

        cursor.execute("""
            SELECT COUNT(*) AS cnt FROM information_schema.STATISTICS
            WHERE TABLE_SCHEMA = DATABASE()
              AND TABLE_NAME   = 'market_average'
              AND INDEX_NAME   = 'uq_market_figure'
        """)
        if cursor.fetchone()['cnt'] == 0:
            # A shelf price and a wholesale price for the same product, place
            # and day are two figures, not a duplicate.
            cursor.execute("""
                ALTER TABLE market_average
                ADD UNIQUE KEY uq_market_figure
                    (canonical_name, country, region_key, snapshot_date, standard_unit, price_stage)
            """)
            print("  market_average: added the unique key with price_stage")

    conn.commit()
