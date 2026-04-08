from utils.db import get_connection, ensure_raw_schema, save_raw
from utils.http import get_session
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

POSTAL_CODES = [
    ('04001', 'Andalucia'), ('41001', 'Andalucia'),
    ('22001', 'Aragon'),    ('50001', 'Aragon'),
    ('33001', 'Asturias'),  ('33400', 'Asturias'),
    ('07001', 'Baleares'),  ('07800', 'Baleares'),
    ('35001', 'Canarias'),  ('38001', 'Canarias'),
    ('39001', 'Cantabria'), ('39300', 'Cantabria'),
    ('45001', 'Castilla-La Mancha'), ('02001', 'Castilla-La Mancha'),
    ('47001', 'Castilla y Leon'),    ('37001', 'Castilla y Leon'),
    ('08001', 'Cataluna'),           ('43001', 'Cataluna'),
    ('46001', 'Comunidad Valenciana'), ('03001', 'Comunidad Valenciana'),
    ('06001', 'Extremadura'), ('10001', 'Extremadura'),
    ('15001', 'Galicia'),   ('36001', 'Galicia'),
    ('26001', 'La Rioja'),  ('26500', 'La Rioja'),
    ('28001', 'Madrid'),    ('28801', 'Madrid'),
    ('30001', 'Murcia'),    ('30500', 'Murcia'),
    ('31001', 'Navarra'),   ('31500', 'Navarra'),
    ('48001', 'Pais Vasco'), ('20001', 'Pais Vasco'),
]

def get_headers(postal_code):
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9',
        'Postal-Code': postal_code,
    }

CATEGORIES = [
    (27,  'fruits'),
    (28,  'vegetables'),
    (29,  'vegetables'),
    (31,  'fish'),
    (32,  'seafood'),
    (38,  'meat'),
    (37,  'meat'),
    (40,  'meat'),
    (44,  'meat'),
    (72,  'milk'),
    (75,  'butter_cream'),
    (77,  'eggs'),
    (54,  'cheese'),
    (56,  'cheese'),
    (53,  'cheese'),
    (104, 'yogurt'),
    (109, 'yogurt'),
    (105, 'yogurt'),
    (122, 'canned_fish'),
    (123, 'canned_fish'),
    (126, 'canned_veg'),
    (127, 'canned_veg'),
]

def format_price(product):
    pi = product.get('price_instructions', {})
    bulk_price  = pi.get('bulk_price', '')
    ref_price   = pi.get('reference_price', '')
    ref_format  = pi.get('reference_format', '')
    unit_price  = pi.get('unit_price', '')
    unit_size   = pi.get('unit_size', '')
    size_format = pi.get('size_format', '')

    parts = []
    if bulk_price:
        parts.append(f"Ahora{bulk_price}€")
    if ref_price and ref_format:
        parts.append(f"1 {ref_format.upper()} A {ref_price} €")
    if unit_price and unit_price != bulk_price:
        parts.append(f"unidad {unit_price}€")
    if unit_size and size_format:
        parts.append(f"{unit_size} {size_format}")

    return ' | '.join(parts)

def scrape_category(conn, session, cat_id, scraper_category, postal_code, region):
    logging.info(f'--- Scraping Mercadona category {cat_id} ({scraper_category}) [{region} / {postal_code}] ---')
    try:
        r = session.get(
            f'https://tienda.mercadona.es/api/categories/{cat_id}/',
            headers=get_headers(postal_code),
            timeout=15
        )
        if r.status_code == 404:
            logging.warning(f'STALE ID: category {cat_id} ({scraper_category}) returned 404 — ID may have changed')
            return 'stale'
        r.raise_for_status()
        data = r.json()

        saved = 0
        subcats = data.get('categories', [])

        if not subcats:
            logging.warning(f'EMPTY: category {cat_id} ({scraper_category}) returned no subcategories — ID may have changed')
            return 'empty'

        for subcat in subcats:
            products = subcat.get('products', [])
            for product in products:
                try:
                    name = product.get('display_name', '')
                    if not name:
                        continue

                    raw_price = format_price(product)
                    packaging = product.get('packaging', '')
                    url = product.get('share_url', '')

                    save_raw(
                        conn,
                        chain='Mercadona',
                        store_name='Mercadona Online',
                        postal_code=postal_code,
                        city=region,
                        region=region,
                        category=scraper_category,
                        raw_name=f"{name}, {packaging}" if packaging else name,
                        raw_price=raw_price,
                        raw_unit_price='',
                        url=url
                    )
                    logging.info(f'Saved: "{name}" | {raw_price}')
                    saved += 1
                    time.sleep(random.uniform(0.2, 0.6))

                except Exception as e:
                    logging.warning(f'Product error: {e}')

        conn.commit()
        logging.info(f'Done: {saved} saved')
        time.sleep(random.uniform(3, 8))
        return 'ok'

    except Exception as e:
        logging.error(f'Failed category {cat_id}: {e}')
        return 'error'

def run():
    logging.info('Starting Mercadona scraper...')
    conn = get_connection()
    session = get_session()
    # Track how each category ID performs across all postal codes
    cat_results = {cat_id: [] for cat_id, _ in CATEGORIES}
    try:
        ensure_raw_schema(conn)
        postal_codes = list(POSTAL_CODES)
        random.shuffle(postal_codes)
        for postal_code, region in postal_codes:
            logging.info(f'=== Postal code {postal_code} ({region}) ===')
            cats = list(CATEGORIES)
            random.shuffle(cats)
            for cat_id, scraper_category in cats:
                status = scrape_category(conn, session, cat_id, scraper_category, postal_code, region)
                cat_results[cat_id].append(status)
    finally:
        conn.close()

    # Summarise any category IDs that never returned data
    logging.info('=== Category ID health check ===')
    all_ok = True
    for cat_id, scraper_category in CATEGORIES:
        statuses = cat_results[cat_id]
        if all(s in ('stale', 'empty', 'error') for s in statuses):
            logging.warning(f'  REVIEW: category {cat_id} ({scraper_category}) returned no data across all postal codes')
            all_ok = False
    if all_ok:
        logging.info('  All category IDs returned data.')
    logging.info('Mercadona scrape complete.')
