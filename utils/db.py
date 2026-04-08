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

def save_raw(conn, chain, store_name, postal_code, city, region, category, raw_name, raw_price, raw_unit_price, url):
    with conn.cursor() as cursor:
        cursor.execute("""
            INSERT IGNORE INTO raw_scrapes
                (chain, store_name, postal_code, city, region, category,
                 raw_name, raw_price, raw_unit_price, url, scrape_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, CURDATE())
        """, (chain, store_name, postal_code, city, region, category, raw_name, raw_price, raw_unit_price, url))
