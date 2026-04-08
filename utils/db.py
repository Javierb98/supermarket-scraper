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

def save_raw(chain, store_name, postal_code, city, category, raw_name, raw_price, raw_unit_price, url):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO raw_scrapes
                    (chain, store_name, postal_code, city, category, raw_name, raw_price, raw_unit_price, url)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (chain, store_name, postal_code, city, category, raw_name, raw_price, raw_unit_price, url))
        conn.commit()
    finally:
        conn.close()
