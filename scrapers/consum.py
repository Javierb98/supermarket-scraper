"""
Consum — a cooperative chain across Valencia, Murcia, Cataluña, Castilla-La
Mancha, Andalucía and Aragón.

Its shop exposes a plain JSON search endpoint with no key and no bot wall:

    /api/rest/V1.0/catalog/searcher/products?q=<term>&limit=<n>&offset=<n>

Prices come back twice over, which is the useful part. `centAmount` is what
you pay for the item as sold and `centUnitAmount` is the same price expressed
per kilo or litre, next to `unitPriceUnitType` saying which. The per-unit
figure is what the averages want: a farm sells tomatoes by the kilo, and
comparing that against the price of one 400g tray is not a comparison.

Searching rather than browsing categories. The normaliser matches raw Spanish
names against about two hundred canonical products, so asking for the terms
those rules already recognise gathers what will actually be used instead of
everything the shop sells.

No region. Nothing in the API prices by store or postcode — the same query
with a centre or store parameter returns the same figures — so these are
recorded as national rather than labelled with a region they do not have.
That still earns its place: a national average is the fallback the site uses
wherever a region is too thin to publish, so it is the one that most needs
the observations.
"""

import logging
import random
import time

from utils.db import get_connection, ensure_raw_schema, save_raw
from utils.http import get_session

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

API = 'https://tienda.consum.es/api/rest/V1.0/catalog/searcher/products'
PAGE_SIZE = 50
MAX_PAGES = 4          # a term with more than 200 matches has stopped being that term

# The terms the normaliser's rules already recognise. Anything it cannot
# classify is dropped later anyway, so asking for it is only load.
SEARCH_TERMS = [
    # veg
    ('tomate', 'vegetables'), ('patata', 'vegetables'), ('cebolla', 'vegetables'),
    ('zanahoria', 'vegetables'), ('lechuga', 'vegetables'), ('pimiento', 'vegetables'),
    ('calabacin', 'vegetables'), ('berenjena', 'vegetables'), ('pepino', 'vegetables'),
    ('brocoli', 'vegetables'), ('coliflor', 'vegetables'), ('ajo', 'vegetables'),
    ('judia verde', 'vegetables'), ('espinaca', 'vegetables'), ('champinon', 'vegetables'),
    ('puerro', 'vegetables'), ('calabaza', 'vegetables'), ('acelga', 'vegetables'),
    ('alcachofa', 'vegetables'), ('esparrago', 'vegetables'), ('guisante', 'vegetables'),
    ('remolacha', 'vegetables'), ('col', 'vegetables'), ('apio', 'vegetables'),
    # fruit
    ('manzana', 'fruits'), ('platano', 'fruits'), ('naranja', 'fruits'),
    ('pera', 'fruits'), ('fresa', 'fruits'), ('uva', 'fruits'),
    ('melon', 'fruits'), ('sandia', 'fruits'), ('limon', 'fruits'),
    ('aguacate', 'fruits'), ('kiwi', 'fruits'), ('melocoton', 'fruits'),
    ('ciruela', 'fruits'), ('cereza', 'fruits'), ('albaricoque', 'fruits'),
    ('mandarina', 'fruits'), ('higo', 'fruits'), ('granada', 'fruits'),
    ('nectarina', 'fruits'), ('frambuesa', 'fruits'), ('arandano', 'fruits'),
    # meat
    ('pollo', 'meat'), ('ternera', 'meat'), ('cerdo', 'meat'),
    ('cordero', 'meat'), ('pavo', 'meat'), ('conejo', 'meat'),
    # eggs and dairy
    ('huevos', 'eggs'), ('leche', 'milk'), ('queso', 'cheese'),
    ('yogur', 'yogurt'), ('mantequilla', 'butter_cream'), ('nata', 'butter_cream'),
    ('miel', 'honey'),
]


def headers():
    return {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                      'AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'es-ES,es;q=0.9',
    }


def format_price(price_data):
    """
    The price as sold and the price per kilo or litre, on one line, in the
    same shape the other scrapers write so the normaliser needs no special
    case for this chain.
    """
    prices = (price_data or {}).get('prices') or []
    if not prices:
        return None, None

    value = prices[0].get('value') or {}
    sold = value.get('centAmount')
    per_unit = value.get('centUnitAmount')
    unit_type = (price_data.get('unitPriceUnitType') or '').strip()

    if sold is None:
        return None, None

    raw_price = f'{sold} €'
    raw_unit_price = f'{per_unit} €/{unit_type}' if per_unit and unit_type else ''

    return raw_price, raw_unit_price


def scrape_term(conn, session, term, category):
    logging.info(f'--- Consum: "{term}" ({category}) ---')
    saved = 0

    for page in range(MAX_PAGES):
        try:
            r = session.get(
                API,
                params={'q': term, 'limit': PAGE_SIZE, 'offset': page * PAGE_SIZE},
                headers=headers(),
                timeout=20,
            )
            r.raise_for_status()
            catalog = (r.json() or {}).get('catalog') or {}
        except Exception as e:
            logging.warning(f'Consum "{term}" page {page}: {e}')
            return saved

        products = catalog.get('products') or []
        if not products:
            break

        for product in products:
            try:
                data = product.get('productData') or {}
                name = (data.get('name') or '').strip()
                if not name:
                    continue

                raw_price, raw_unit_price = format_price(product.get('priceData'))
                if raw_price is None:
                    continue

                save_raw(
                    conn,
                    chain='Consum',
                    store_name='Consum Online',
                    postal_code='',
                    city='',
                    # Priced nationally, so it says so rather than claiming a region.
                    region=None,
                    category=category,
                    raw_name=name,
                    raw_price=raw_price,
                    raw_unit_price=raw_unit_price,
                    url=data.get('url', ''),
                )
                saved += 1

            except Exception as e:
                logging.warning(f'Consum product error: {e}')

        conn.commit()

        if not catalog.get('hasMore'):
            break

        time.sleep(random.uniform(0.8, 1.8))

    logging.info(f'  {saved} saved for "{term}"')
    return saved


def run():
    logging.info('Starting Consum scraper...')
    conn = get_connection()
    session = get_session()
    total = 0

    try:
        ensure_raw_schema(conn)

        # Shuffled so a run that is cut short does not always lose the same
        # end of the list.
        terms = list(SEARCH_TERMS)
        random.shuffle(terms)

        for term, category in terms:
            total += scrape_term(conn, session, term, category)
            time.sleep(random.uniform(1.0, 2.5))

        conn.commit()
        logging.info(f'Consum finished: {total} rows saved.')

        # A run that gathered nothing is a failure, not a quiet success. The
        # caller stops the pipeline rather than averaging an empty day.
        if total == 0:
            raise RuntimeError('Consum returned no products at all — the API or the markup has changed')

        return total

    finally:
        conn.close()


if __name__ == '__main__':
    run()
