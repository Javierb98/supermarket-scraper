"""
Germany: shelf prices from ALDI Nord's public assortment pages (aldi-nord.de).

ALDI Nord's "Sortiment" pages are rendered on the server with the whole
product list of the category in them (the page's own search result, up to
1,000 products, inside __NEXT_DATA__): name, sales unit ("650-g-Schale",
"kg-Preis", "Stück", "10er-Packung"), current price, the struck-through
price when it is an offer, and the base price per kg or litre. So one page
per category is all it takes: about a dozen requests a week, two seconds
apart.

ALDI prices one price for its whole region; ALDI Nord covers the north,
west and east of Germany (ALDI Süd the south and west). Stored as national
figures for DE, chain "ALDI Nord".

robots.txt (checked 2026-11-04): /sortiment/ and /produkt/ are allowed to
every user agent. No login, no bot protection met, no terms forbidding
reading the public pages were found (the site's terms cover competitions
and the e-charging service only).

What is kept: fresh fruit and vegetables, eggs, milk, butter and cream,
cheese, and raw meat and poultry. Sausages, ham and ready meals are not
fetched. Each product is stored as a raw shelf row with a structured price
("item=1.69;per_kg=2.6;regular=2.19") for normalize.py and market_average.py,
which this feed then runs for DE.

    python feeds/aldi_nord.py              fetch, store, normalise, average (DE)
    python feeds/aldi_nord.py --dry-run    fetch and print, store nothing
"""

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get  # noqa: E402

BASE = 'https://www.aldi-nord.de'
CHAIN = 'ALDI Nord'
COUNTRY = 'DE'

# Category page -> the aisle name stored with each row (normalize.py reads it).
CATEGORIES = {
    '/sortiment/obst-gemuese/frisch.html': 'Obst & Gemüse > Frisches Obst & Gemüse',
    '/sortiment/vorraete/eier.html': 'Eier',
    '/sortiment/milchprodukte/milch-milchgetraenke.html': 'Milchprodukte > Milch',
    '/sortiment/milchprodukte/butter-sahne-sauerrahm.html': 'Milchprodukte > Butter & Sahne',
    '/sortiment/milchprodukte/hartkaese-kaese-am-stueck.html': 'Milchprodukte > Käse am Stück',
    '/sortiment/milchprodukte/scheibenkaese-geriebener-kaese.html': 'Milchprodukte > Scheibenkäse',
    '/sortiment/milchprodukte/frischkaese-weichkaese.html': 'Milchprodukte > Frischkäse & Weichkäse',
    '/sortiment/fleisch-wurst/gefluegel.html': 'Fleisch > Geflügel',
    '/sortiment/fleisch-wurst/gemischtes-hackfleisch.html': 'Fleisch > Hackfleisch',
    '/sortiment/fleisch-wurst/rind.html': 'Fleisch > Rind',
    '/sortiment/fleisch-wurst/schwein.html': 'Fleisch > Schwein',
    '/sortiment/bio-produkte/frisches-fleisch.html': 'Bio > Frisches Fleisch',
    '/sortiment/bio-produkte/eier-milchprodukte.html': 'Bio > Eier & Milchprodukte',
}

NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', re.S)
COUNT = re.compile(r'^(\d+)(?:er\b|-st[üu]ck)', re.I)   # "10-Stück-Packung", "6er-Schale", "2er-Schale"
EGGS = re.compile(r'\beier\b|\w+eier\b', re.I)


def hits(html):
    """The search hits a category page carries, or [] when it has none."""
    m = NEXT_DATA.search(html)
    if not m:
        return []
    found = []

    def walk(o):
        if isinstance(o, dict):
            if isinstance(o.get('hits'), list) and o.get('index'):
                found.extend(o['hits'])
            for v in o.values():
                walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)
    walk(json.loads(m.group(1)))
    return found


def structured(hit):
    """One product -> raw_price ("item=...;per_kg=...;regular=...") or None."""
    cp = hit.get('currentPrice') or {}
    price = cp.get('priceValue')
    if not price or price <= 0:
        return None
    fields = {'item': float(price)}
    unit = (hit.get('salesUnit') or '').strip()
    for b in cp.get('basePrice') or []:
        scale, value = (b.get('basePriceScale') or '').lower(), b.get('basePriceValue')
        if value and scale == 'kg':
            fields['per_kg'] = float(value)
        elif value and scale == 'l':
            fields['per_l'] = float(value)
    low = unit.lower()
    if low == 'kg-preis':
        fields['per_kg'] = float(price)
    elif low in ('stück', 'stueck', 'bund', 'kopf'):
        fields['per_unit'] = float(price)
    else:
        n = COUNT.match(unit)
        if n:
            n = int(n.group(1))
            if EGGS.search(hit.get('name') or ''):
                fields['per_dozen'] = price / n * 12
            elif 1 <= n <= 12 and 'per_kg' not in fields:
                fields['per_unit'] = price / n
    strike = (cp.get('strikePrice') or {}).get('strikePriceValue')
    if strike and strike > price:
        fields['regular'] = float(strike)
    if len(fields) == 1 or (fields.keys() == {'item', 'regular'}):
        return None          # nothing says what the price is per
    return ';'.join(f'{k}={round(v, 4)}' for k, v in fields.items())


def rows(hits_by_aisle):
    out, seen = [], set()
    for aisle, hs in hits_by_aisle:
        for h in hs:
            oid = h.get('objectID')
            if not oid or oid in seen or h.get('isAvailable') is False or h.get('isRecall'):
                continue
            seen.add(oid)
            raw = structured(h)
            if not raw:
                continue
            name = re.sub(r'\s+', ' ', h.get('name') or '').strip()
            unit = (h.get('salesUnit') or '').strip()
            out.append({
                'raw_name': f'{name} ({unit})' if unit else name,
                'raw_price': raw,
                'shop_category': aisle,
                'url': f"{BASE}/produkt/{h.get('productSlug') or oid}.html",
            })
    return out


def fetch():
    got = []
    for path, aisle in CATEGORIES.items():
        try:
            html = get(BASE + path, headers={'Accept': 'text/html'}, timeout=60, pause=2.0).decode('utf-8', 'replace')
        except Exception as e:
            print(f'  {path}: could not fetch ({e})')
            continue
        hs = hits(html)
        print(f'  {aisle}: {len(hs)} products')
        got.append((aisle, hs))
    return got


def run(dry_run=False):
    collected = rows(fetch())
    if dry_run:
        for r in collected:
            print(f'    {r["shop_category"][:28]:<28} {r["raw_name"][:55]:<55} {r["raw_price"]}')
        return len(collected)
    if not collected:
        raise RuntimeError('ALDI Nord: no products found — the pages have changed')

    from utils.db import get_connection, ensure_raw_schema, save_raw
    conn = get_connection()
    try:
        ensure_raw_schema(conn)
        for r in collected:
            save_raw(conn, chain=CHAIN, store_name=None, postal_code=COUNTRY, city=None, region=None,
                     category=None, raw_name=r['raw_name'], raw_price=r['raw_price'], raw_unit_price=None,
                     url=r['url'], shop_category=r['shop_category'], country=COUNTRY)
        conn.commit()
    finally:
        conn.close()
    print(f'{COUNTRY} {CHAIN}: {len(collected)} shelf rows stored')

    from pipeline import normalize, market_average
    normalize.run(COUNTRY)
    market_average.run(COUNTRY)
    return len(collected)


if __name__ == '__main__':
    run(dry_run='--dry-run' in sys.argv)
