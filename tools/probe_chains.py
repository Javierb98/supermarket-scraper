"""
Which chains will talk to this machine?

Run it on the Pi. The answer is different there, and that is the whole point:
supermarket bot protection scores datacentre addresses harshly and residential
ones gently, so a chain that refuses a laptop on a cloud connection will often
serve a house without complaint. Probing from anywhere else tells you about
that connection, not about the Pi's.

    python tools/probe_chains.py

It fetches one small page per chain, a few seconds apart, and prints whether
anything usable came back. Nothing is written to the database. A chain that
answers here is one worth writing a scraper for; a chain that does not is one
to leave alone rather than guess at.
"""

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                  'AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'es-ES,es;q=0.9',
}

# Each entry: a name, a URL that should return a product or two, and a hint of
# where the products live in the response so a reply that is merely a 200 can
# be told from a reply with prices in it.
CANDIDATES = [
    ('Consum (in use)', 'https://tienda.consum.es/api/rest/V1.0/catalog/searcher/products?q=tomate&limit=2',
     ('catalog', 'products')),
    ('Dia',             'https://www.dia.es/api/v1/search-back/search/reduced?q=tomate&page=1',
     ('search_items',)),
    ('Carrefour',       'https://www.carrefour.es/cloudapi/plp-food/v1/search?query=tomate',
     ('results',)),
    ('Alcampo',         'https://www.compra.alcampo.es/api/v5/products?filter%5Bterm%5D=tomate&page%5Bsize%5D=2',
     ('data',)),
    ('Bonpreu/Esclat',  'https://www.bonpreuesclat.cat/api/v2/products/search?q=tomaquet',
     ('products',)),
    ('Condis',          'https://www.condisline.com/api/catalog/search?q=tomate',
     ('products',)),
    ('Ahorramas',       'https://www.ahorramas.com/on/demandware.store/Sites-Ahorramas-Site/es_ES/SearchServices-GetSuggestions?q=tomate',
     ('product',)),
    ('Gadis',           'https://www.gadisline.com/api/search?q=tomate',
     ('products',)),

    # ── United States, Canada, UK ────────────────────────────────────────
    #
    # Probed from a datacentre address these answered: Kroger 401 (a real API
    # wanting a token), Publix an HTML page with no products, Target 401,
    # Trader Joe's and Safeway 403, and Walmart 418 with an Akamai "Access
    # Denied" — which is not a wall a residential address gets through either.
    # Worth re-running here to see which of those soften.
    ('Kroger (needs key)', 'https://api.kroger.com/v1/locations?filter.zipCode.near=45202',
     ('data',)),
    ('Trader Joe\'s',   'https://www.traderjoes.com/api/graphql',
     ('data',)),
    ('Publix',          'https://services.publix.com/api/v1/product/search?searchTerm=milk',
     ('products',)),
    ('Walmart',         'https://www.walmart.com/orchestra/home/graphql',
     ('data',)),
    ('Target',          'https://redsky.target.com/redsky_aggregations/v1/web/plp_search_v2?keyword=milk',
     ('data',)),
    ('Safeway',         'https://www.safeway.com/abs/pub/xapi/search/products?q=milk&storeid=1',
     ('primaryProducts',)),
    ('Tesco (UK)',      'https://www.tesco.com/groceries/en-GB/search?query=milk',
     ('results',)),
    ('Sainsbury (UK)',  'https://www.sainsburys.co.uk/groceries-api/gol-services/product/v1/product?filter[keyword]=milk',
     ('products',)),
]


def dig(payload, path):
    """Follow a path into the response, tolerating a shape that has changed."""
    node = payload
    for key in path:
        if isinstance(node, dict):
            node = node.get(key)
        elif isinstance(node, list) and node:
            node = node[0].get(key) if isinstance(node[0], dict) else None
        else:
            return None
    return node


def probe(name, url, path):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=20) as r:
            body = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        # 403 is the interesting failure: it usually means a bot wall rather
        # than a wrong address, and it is the one that differs by connection.
        note = {
            401: '— a real API wanting a key; register rather than scrape',
            403: '— blocked, probably bot protection',
            418: '— bot wall (Akamai); this one does not soften by address',
            429: '— rate limited; slow down',
        }.get(e.code, '')
        return f'{e.code} {note}'.strip()
    except Exception as e:
        return f'no answer ({type(e).__name__})'

    try:
        found = dig(json.loads(body), path)
    except Exception:
        return f'{status} but not JSON ({len(body)} bytes) — likely an HTML challenge page'

    if isinstance(found, list):
        return f'{status} OK — {len(found)} products in the reply' if found else f'{status} but no products at {".".join(path)}'

    return f'{status} JSON, but nothing at {".".join(path)} — the shape has changed'


if __name__ == '__main__':
    print('Probing from this machine. Run it on the Pi for the answer that matters.\n')

    for i, (name, url, path) in enumerate(CANDIDATES):
        print(f'  {name:18} {probe(name, url, path)}')
        if i < len(CANDIDATES) - 1:
            time.sleep(3)   # one at a time, unhurried

    print('\nAnything reporting products is worth a scraper. Paths are guesses for')
    print('the chains not yet written: a JSON reply with nothing where expected')
    print('means the endpoint is reachable and only the path needs finding.')
