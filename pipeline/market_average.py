from datetime import date
from utils.db import get_connection

CREATE_TABLE = """
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
    created_at          TIMESTAMP     DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_product_date_unit (canonical_name, country, snapshot_date, standard_unit)
) CHARACTER SET utf8mb4;
"""

MIGRATE_UNIQUE_KEY = """
SELECT COUNT(*) AS cnt
FROM information_schema.STATISTICS
WHERE TABLE_SCHEMA = DATABASE()
  AND TABLE_NAME = 'market_average'
  AND INDEX_NAME = 'uq_product_date'
"""

COMPUTE = """
SELECT
    NULL                            AS catalog_product_id,
    canonical_name,
    MAX(category)                   AS category,
    COALESCE(country, 'ES')         AS country,
    AVG(COALESCE(unit_price, price)) AS avg_price,
    MIN(COALESCE(unit_price, price)) AS min_price,
    MAX(COALESCE(unit_price, price)) AS max_price,
    CASE
        WHEN COALESCE(MAX(unit), '€/unit') = '€/kg'     THEN '€/kg'
        WHEN COALESCE(MAX(unit), '€/unit') = '€/l'      THEN '€/l'
        WHEN COALESCE(MAX(unit), '€/unit') = '€/docena' THEN '€/dozen'
        ELSE '€/unit'
    END                             AS standard_unit,
    COUNT(*)                        AS sample_count
FROM products_normalized
WHERE canonical_name IS NOT NULL
  AND category != 'unknown'
  AND DATE(scraped_at) = %s
  AND COALESCE(unit_price, price) IS NOT NULL
GROUP BY
    canonical_name,
    COALESCE(country, 'ES'),
    COALESCE(unit, '€/unit')
"""

INSERT = """
INSERT IGNORE INTO market_average
    (catalog_product_id, canonical_name, category, country,
     snapshot_date, avg_price, min_price, max_price, standard_unit, sample_count)
VALUES
    (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

def run():
    conn = get_connection()
    inserted = 0
    today = date.today()

    try:
        with conn.cursor() as cursor:
            cursor.execute(CREATE_TABLE)
        conn.commit()

        # Migrate old unique key (without standard_unit) if it still exists
        with conn.cursor() as cursor:
            cursor.execute(MIGRATE_UNIQUE_KEY)
            if cursor.fetchone()['cnt'] > 0:
                cursor.execute("ALTER TABLE market_average DROP INDEX uq_product_date")
                cursor.execute("ALTER TABLE market_average ADD UNIQUE KEY uq_product_date_unit (canonical_name, country, snapshot_date, standard_unit)")
        conn.commit()

        with conn.cursor() as cursor:
            cursor.execute("SELECT MAX(DATE(scraped_at)) AS scrape_date FROM products_normalized")
            scrape_date = cursor.fetchone()['scrape_date'] or today

        print(f"market_average table ready. Running snapshot for {scrape_date}.")

        with conn.cursor() as cursor:
            cursor.execute(COMPUTE, (scrape_date,))
            rows = cursor.fetchall()
        print(f"  {len(rows)} national averages computed.")

        with conn.cursor() as cursor:
            for row in rows:
                cursor.execute(INSERT, (
                    row['catalog_product_id'],
                    row['canonical_name'],
                    row['category'],
                    row['country'],
                    scrape_date,
                    round(float(row['avg_price']), 4),
                    round(float(row['min_price']), 4),
                    round(float(row['max_price']), 4),
                    row['standard_unit'],
                    row['sample_count'],
                ))
                inserted += 1

        conn.commit()
        print(f"\nDone! {inserted} rows inserted into market_average for {scrape_date}.")

        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT canonical_name, category, standard_unit,
                       ROUND(avg_price, 2) AS avg_price,
                       ROUND(min_price, 2) AS min_price,
                       ROUND(max_price, 2) AS max_price,
                       sample_count
                FROM market_average
                WHERE snapshot_date = %s
                ORDER BY category, canonical_name
                LIMIT 30
            """, (scrape_date,))
            rows = cursor.fetchall()
            print("\nSample output:")
            print(f"  {'Product':<35} {'Unit':<10} {'Avg':>8}  {'Min':>8}  {'Max':>8}  {'n':>5}")
            print("  " + "-" * 80)
            for r in rows:
                print(f"  {r['canonical_name']:<35} {r['standard_unit']:<10} {float(r['avg_price']):>8.2f}  {float(r['min_price']):>8.2f}  {float(r['max_price']):>8.2f}  {r['sample_count']:>5}")

    finally:
        conn.close()

if __name__ == '__main__':
    run()
