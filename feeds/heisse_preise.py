"""
Austria: supermarket shelf prices from heisse-preise.io.

Heisse Preise (github.com/badlogic/heissepreise, code MIT) reads the
Austrian chains' online shops every morning and publishes what it found,
one file per chain, and its README invites others to use the raw data. The
prices are the project's own scrape of the shops' public sites: their reuse
is not licensed in so many words, so they are used with attribution (the
chain is stored as "BILLA (heisse-preise.io)") and removed on request.

What it gives, per product: the chain, the shelf name, the pack size
(quantity + unit: g, ml, stk, ...), whether it is sold by weight, the price
history (newest first), whether the shop still lists it, and the project's
own aisle code (Billa's aisles, "00" fruit, "01" vegetables, "30" eggs, ...).

What this feed does with it:

  - Reads the small per-chain files (latest-canonical.<chain>.compressed.json,
    gzip on the wire: ~1.8 MB for Billa), not the 300 MB CSV.
  - Keeps only chains that are still being read: a chain whose newest price
    is more than STALE_DAYS old is skipped and said so. In November 2026 only
    Billa is live (Spar stopped on 27 September, Hofer in November 2025,
    MPREIS and Unimarkt in 2024, Lidl and Penny publish empty files).
  - Keeps only products the shop still lists, in the fresh aisles (fruit,
    vegetables, salads, herbs, mushrooms, eggs, cheese, dairy, raw meat), and
    from the nuts-and-dried-fruit aisle only plain nuts and chestnuts.
  - Stores each as a raw shelf row with a structured price (item, per kg /
    litre / dozen / piece worked out from the pack), so normalize.py and
    market_average.py turn them into figures exactly as for a scraped shop.
    The run then does that for AT itself: the weekly run_all.sh normalises
    before it runs the feeds.

An offer: the history only says what the price was and when it changed. A
price at least 15% below the one before it, set within the last three weeks,
is taken as an offer and stored with the earlier price as the regular one,
which is what market_average counts.

    python feeds/heisse_preise.py            fetch, store, normalise, average (AT)
    python feeds/heisse_preise.py --dry-run  fetch and print, store nothing
"""

import gzip
import json
import os
import re
import sys
from collections import Counter
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get  # noqa: E402

BASE = 'https://heisse-preise.io/data/latest-canonical.{}.compressed.json'
SOURCE = 'heisse-preise.io'
COUNTRY = 'AT'

# The project's store key → the chain's name, and where its product pages are.
STORES = {
    'billa':    ('BILLA',    'https://shop.billa.at/produkte/'),
    'spar':     ('SPAR',     'https://www.interspar.at/shop/lebensmittel'),
    'hofer':    ('HOFER',    'https://www.roksh.at/hofer/produkte/'),
    'lidl':     ('Lidl',     'https://www.lidl.at'),
    'penny':    ('PENNY',    'https://www.penny.at/produkte/'),
    'mpreis':   ('MPREIS',   'https://www.mpreis.at/shop/p/'),
    'unimarkt': ('Unimarkt', 'https://shop.unimarkt.at'),
}

# A chain whose newest price is older than this is no longer being read.
STALE_DAYS = 10

# The project's aisle codes (in its live data) that hold fresh products,
# and the aisle name stored with each row (the normaliser reads it).
AISLES = {
    '00': 'Obst & Gemüse > Obst',
    '01': 'Obst & Gemüse > Gemüse',
    '02': 'Obst & Gemüse > Salate',
    '03': 'Obst & Gemüse > Kräuter',
    '04': 'Obst & Gemüse > Pilze',
    '05': 'Obst & Gemüse > Nüsse',
    '30': 'Kühlwaren > Eier',
    '32': 'Kühlwaren > Käse',
    '34': 'Kühlwaren > Milchprodukte',
    'F0': 'Fleisch > Geflügel',
    'F1': 'Fleisch > Faschiertes',
    'F2': 'Fleisch > Schwein',
    'F3': 'Fleisch > Rind',
    'F4': 'Fleisch > Lamm & Wild',
}
EGG_AISLE = '30'
# The nuts-and-dried-fruit aisle: a dried fig is not a fig's price.
NUT_AISLE = '05'
NUTS = re.compile(r'walnu|haselnu|mandeln|pinienkern|maroni|kastanie|paranu|pekannu|macadamia|cashew', re.I)

OFFER_DROP = 0.15
OFFER_DAYS = 21


def fetch(store):
    """The project's file for one chain, decoded."""
    body = get(BASE.format(store), headers={'Accept-Encoding': 'gzip', 'Accept': 'application/json'},
               timeout=120, pause=2.0)
    if body[:2] == b'\x1f\x8b':
        body = gzip.decompress(body)
    return json.loads(body)


def items(doc):
    """
    The compressed file → one dict per product.

    Layout (analysis.js compress()): a flat list, per item
      store index, id, name, category, unavailable, n,
      n × (date index, price), unit, quantity, isWeighted, bio, url
    """
    stores, dates, data = doc['stores'], doc['dates'], doc['data']
    i = 0
    while i < len(data):
        store, iid, name, cat, unavailable, n = data[i:i + 6]
        i += 6
        history = []
        for k in range(n):
            d = dates[data[i + 2 * k]]
            history.append((date(int(d[:4]), int(d[4:6]), int(d[6:8])), data[i + 2 * k + 1]))
        i += 2 * n
        unit, quantity, weighted, bio, url = data[i:i + 5]
        i += 5
        yield {
            'store': stores[store], 'id': iid, 'name': name, 'category': cat or '',
            'available': not unavailable, 'history': history, 'unit': (unit or '').lower(),
            'quantity': quantity, 'weighted': bool(weighted), 'bio': bool(bio), 'url': url or '',
        }


def clean(name):
    return re.sub(r'\s+', ' ', (name or '').replace('\xa0', ' ')).strip()


def structured(item, today):
    """
    One product → (raw_price, pack label) or None.

    raw_price is the structured form pipeline/prices.py reads:
    "item=2.49;per_kg=4.98;regular=2.99".
    """
    if not item['history']:
        return None
    (when, price), earlier = item['history'][0], item['history'][1:]
    if not price or price <= 0:
        return None
    q, unit = item['quantity'], item['unit']
    try:
        q = float(q)
    except (TypeError, ValueError):
        return None
    if q <= 0:
        return None

    fields = {'item': price}
    if unit == 'g':
        fields['per_kg'] = price / q * 1000
        label = f'{q:g} g'
    elif unit == 'kg':
        fields['per_kg'] = price / q
        label = f'{q:g} kg'
    elif unit == 'ml':
        fields['per_l'] = price / q * 1000
        label = f'{q:g} ml'
    elif unit == 'l':
        fields['per_l'] = price / q
        label = f'{q:g} l'
    elif unit in ('stk', 'stück', 'stuck'):
        n = int(round(q))
        if n < 1 or item['category'].startswith('F'):
            # Meat by the piece ("2 Stk.") says nothing a farm's kilo price can be held to.
            return None
        if item['category'] == EGG_AISLE:
            fields['per_dozen'] = price / n * 12
        elif n <= 12:
            fields['per_unit'] = price / n
        label = f'{n} Stück'
    else:
        return None

    if earlier:
        before = earlier[0][1]
        if before and price <= before * (1 - OFFER_DROP) and (today - when).days <= OFFER_DAYS:
            fields['regular'] = before

    raw = ';'.join(f'{k}={round(v, 4)}' for k, v in fields.items())
    return raw, label


def rows(doc, store, today):
    """Products worth storing, and a tally of what was left out and why."""
    chain, url_base = STORES[store]
    why = Counter()
    out = []
    for it in items(doc):
        if it['store'] != store:
            continue
        if not it['available']:
            why['not listed any more'] += 1
            continue
        aisle = AISLES.get(it['category'])
        if aisle is None:
            why['other aisle'] += 1
            continue
        name = clean(it['name'])
        if it['category'].startswith('F'):
            # "Puten-Schnitzel 2 Stk." sold by the kilo: the count is not a
            # price per piece, and pipeline/pack.py would read it as one.
            name = clean(re.sub(r'\b\d+\s*(stk|stück)\b\.?', ' ', name, flags=re.I))
        if not name or (it['category'] == NUT_AISLE and not NUTS.search(name)):
            why['dried fruit'] += 1
            continue
        got = structured(it, today)
        if got is None:
            why['no usable price or pack'] += 1
            continue
        raw_price, label = got
        url = it['url'] if it['url'].startswith('http') else url_base.rstrip('/') + '/' + it['url'].lstrip('/')
        out.append({
            'chain': f'{chain} ({SOURCE})',
            # The pack goes in the name: the shop lists the same name in
            # several sizes, and each is its own shelf product.
            'raw_name': f'{name} ({label})',
            'raw_price': raw_price,
            'shop_category': aisle,
            'url': url[:500],
        })
    return out, why


def newest(doc):
    latest = doc['dates'][-1] if doc.get('dates') else None
    return datetime.strptime(latest, '%Y%m%d').date() if latest else None


def run(dry_run=False):
    today = date.today()
    collected = []
    for store in STORES:
        try:
            doc = fetch(store)
        except Exception as e:
            print(f'  {store}: could not fetch ({e})')
            continue
        if not doc.get('n'):
            print(f'  {store}: the project publishes no products for this chain')
            continue
        last = newest(doc)
        if last is None or (today - last).days > STALE_DAYS:
            print(f'  {store}: newest price {last}, not being read any more; skipped')
            continue
        got, why = rows(doc, store, today)
        print(f'  {store}: {doc["n"]} products, newest price {last}; {len(got)} kept '
              f'({", ".join(f"{v} {k}" for k, v in why.most_common())})')
        collected.extend(got)

    if dry_run:
        for r in collected[:40]:
            print(f'    {r["chain"]:<28} {r["raw_name"][:60]:<60} {r["raw_price"]}')
        return len(collected)

    if not collected:
        raise RuntimeError('heisse-preise.io: no live chain returned anything')

    from utils.db import get_connection, ensure_raw_schema, save_raw
    conn = get_connection()
    try:
        ensure_raw_schema(conn)
        for r in collected:
            save_raw(conn, chain=r['chain'], store_name=None, postal_code=COUNTRY, city=None, region=None,
                     category=None, raw_name=r['raw_name'], raw_price=r['raw_price'], raw_unit_price=None,
                     url=r['url'], shop_category=r['shop_category'], country=COUNTRY)
        conn.commit()
    finally:
        conn.close()
    print(f'{COUNTRY} {SOURCE}: {len(collected)} shelf rows stored')

    # run_all.sh normalises and averages before it runs the feeds, so a
    # feed that stores shelf rows finishes the job for its own country.
    from pipeline import normalize, market_average
    normalize.run(COUNTRY)
    market_average.run(COUNTRY)
    return len(collected)


if __name__ == '__main__':
    run(dry_run='--dry-run' in sys.argv)
