from bs4 import BeautifulSoup
from utils.db import get_connection, ensure_raw_schema, save_raw
from utils.http import get_session
import time, random, logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0',
]

CATEGORIES = [
    ('vegetables', 'https://supermercado.eroski.es/es/supermercado/2059698-frescos/2059710-verduras-y-hortalizas/'),
    ('fruits',     'https://supermercado.eroski.es/es/supermercado/2059698-frescos/2059699-frutas/'),
    ('eggs',       'https://supermercado.eroski.es/es/supermercado/2059698-frescos/2059760-huevos/'),
    ('dairy',      'https://supermercado.eroski.es/es/supermercado/2059806-alimentacion/2059807-leche-batidos-y-bebidas-vegetales/'),
    ('dairy',      'https://supermercado.eroski.es/es/supermercado/2059806-alimentacion/2059851-mantequilla-nata-y-cremas/'),
    ('dairy',      'https://supermercado.eroski.es/es/supermercado/2059698-frescos/2059858-queso-y-membrillo/'),
]

def get_headers(referer=None):
    h = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }
    if referer:
        h['Referer'] = referer
    return h

def human_delay(a=4, b=12):
    d = random.uniform(a, b)
    logging.info(f'Waiting {d:.1f}s...')
    time.sleep(d)

def scrape_page(conn, session, cat, page_url, referer):
    saved = 0
    r = session.get(page_url, headers=get_headers(referer), timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, 'html.parser')
    products = (soup.select('li.product-item') or
                soup.select('div.product-item') or
                soup.select('article.product') or
                soup.select('[class*="product-card"]'))
    logging.info(f'  Found {len(products)} products on {page_url}')
    for p in products:
        try:
            name_el = p.select_one('[class*="name"],[class*="title"],h2,h3')
            if not name_el:
                continue
            raw_name = name_el.get_text(strip=True)
            price_els = p.select('[class*="price"]')
            prices_raw = ' | '.join(el.get_text(strip=True) for el in price_els if el.get_text(strip=True))
            unit_el = p.select_one('[class*="unit"],[class*="kg"],[class*="litro"]')
            unit_raw = unit_el.get_text(strip=True) if unit_el else ''
            save_raw(conn, 'Eroski', 'Eroski Online', '31001', 'Pamplona', 'Navarra', cat, raw_name, prices_raw, unit_raw, page_url)
            logging.info(f'  Saved: "{raw_name[:60]}" | prices: {prices_raw}')
            saved += 1
            time.sleep(random.uniform(0.5, 1.5))
        except Exception as e:
            logging.warning(f'Product error: {e}')
    return soup, saved

def scrape_category(conn, session, cat, url):
    logging.info(f'--- Scraping: {cat} @ {url} ---')
    try:
        session.get('https://supermercado.eroski.es/es/', headers=get_headers(), timeout=15)
        human_delay(2, 5)

        soup, saved = scrape_page(conn, session, cat, url, 'https://supermercado.eroski.es/es/')

        # Collect all page links from the first page
        page_links = [a['href'] for a in soup.select('div.pages a.page') if a.get('href')]
        logging.info(f'  Found {len(page_links)} additional page(s)')

        for page_url in page_links:
            human_delay(4, 10)
            try:
                _, page_saved = scrape_page(conn, session, cat, page_url, url)
                saved += page_saved
            except Exception as e:
                logging.error(f'Failed page {page_url}: {e}')

        conn.commit()
        logging.info(f'Done: {saved} saved across {1 + len(page_links)} page(s)')
    except Exception as e:
        logging.error(f'Failed {cat}: {e}')

def run():
    logging.info('Starting Eroski scraper...')
    conn = get_connection()
    session = get_session()
    try:
        ensure_raw_schema(conn)
        cats = list(CATEGORIES)
        random.shuffle(cats)
        for cat, url in cats:
            scrape_category(conn, session, cat, url)
            human_delay(15, 40)
    finally:
        conn.close()
    logging.info('Eroski scrape complete.')
