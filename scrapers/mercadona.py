import requests
from utils.db import save_raw
import time
import random
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'es-ES,es;q=0.9',
    'Postal-Code': '31001',
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

def scrape_category(cat_id, scraper_category):
    logging.info(f'--- Scraping Mercadona category {cat_id} ({scraper_category}) ---')
    try:
        r = requests.get(
            f'https://tienda.mercadona.es/api/categories/{cat_id}/',
            headers=HEADERS,
            timeout=15
        )
        r.raise_for_status()
        data = r.json()

        saved = 0
        subcats = data.get('categories', [])

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
                        chain='Mercadona',
                        store_name='Mercadona Online',
                        postal_code=None,
                        city='Nacional',
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

        logging.info(f'Done: {saved} saved')
        time.sleep(random.uniform(3, 8))

    except Exception as e:
        logging.error(f'Failed category {cat_id}: {e}')

def run():
    logging.info('Starting Mercadona scraper...')
    cats = list(CATEGORIES)
    random.shuffle(cats)
    for cat_id, scraper_category in cats:
        scrape_category(cat_id, scraper_category)
    logging.info('Mercadona scrape complete.')
