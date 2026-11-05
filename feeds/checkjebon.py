"""
The Netherlands: shelf prices from nine Dutch chains, via checkjebon.nl.

Checkjebon.nl is an open-source price comparison site (code MIT,
github.com/supermarkt/checkjebon). It gathers the chains' online prices
itself and publishes them as one JSON file, updated every few days, which
its README offers for reuse: "Product price data is updated frequently and
may be reused in other projects." We read that one file (about 10 MB) from
GitHub — nothing from the shops themselves — and credit checkjebon.nl as
the source.

    [{"n": "ah", "c": "AH", "u": "https://www.ah.nl/producten/product/",
      "d": [{"n": "AH Tomaten", "p": 1.55, "s": "500 g", "l": "wi4088/ah-tomaten"}, ...]}, ...]

n is the shelf name, p the price in euros, s the pack size as the shop
writes it ("500 g", "Per 464 g", "12 stuks", "per stuk", "1,5 liter",
"ca. 400 g", "3 x 100 g", or nothing). There is no regular price, so an
offer cannot be told apart; the median in market_average takes care of the
odd one.

These are shop shelf prices, so they go in as raw rows like any shop scrape
(chain = the shop, national, structured raw_price with the price per kilo,
litre, dozen or piece worked out from the pack size). The Dutch rules in
pipeline/rules_nl.py then decide which are fresh produce, eggs, dairy and
meat, and this feed runs normalise and average for NL itself, because the
weekly run calls the feeds after its own normalise and average steps.

Only rows the Dutch rules recognise are stored: of ~100,000 products a
few thousand are fresh food, and storing the rest every week would fill
raw_scrapes with shampoo.

Left out:
  * Lidl. Checkjebon gets it second-hand (boodschaapje.nl), most rows have
    no size and some sizes are wrong ("Scharreleieren 12st." at 70 g,
    "Kipfilet testsieger" at €0.01).
  * Chains with no products in the file (ALDI and Ekoplaza at present).

    python feeds/checkjebon.py            download, store, normalise, average
    python feeds/checkjebon.py --dry-run  download and print what would be stored
"""

import json
import os
import re
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get

URL = 'https://raw.githubusercontent.com/supermarkt/checkjebon/main/data/supermarkets.json'
COUNTRY = 'NL'
SKIP_CHAINS = {'lidl'}

# Prices outside this range are a data error, not a price.
LOW, HIGH = 0.05, 500.0

_N = r'(\d+(?:[.,]\d+)?)'
WEIGHT = {'kg': 1, 'kilo': 1, 'kilogram': 1, 'kilogramm': 1, 'g': 0.001, 'gr': 0.001, 'gram': 0.001,
          'grm': 0.001, 'grams': 0.001, 'gramm': 0.001}
VOLUME = {'l': 1, 'liter': 1, 'litre': 1, 'ltr': 1, 'ml': 0.001, 'milliliter': 0.001, 'mililiter': 0.001,
          'mililiters': 0.001, 'milliliters': 0.001, 'cl': 0.01, 'centiliter': 0.01, 'dl': 0.1}
COUNT = ('stuks', 'stuk', 'st', 'stk', 'eieren', 'ei')
_UNITS = '|'.join(sorted(list(WEIGHT) + list(VOLUME), key=len, reverse=True))
_COUNTS = '|'.join(sorted(COUNT, key=len, reverse=True))

EGGS = re.compile(r'eieren|\beitjes\b', re.I)


def _f(s):
    return float(s.replace(',', '.'))


def parse_size(text):
    """'500 g' / 'Per 464 g' / '3 x 100 g' / '12 stuks' / 'per stuk' / '1 kg (ca. 8 stuks)'
    → (kg, litres, count); any may be None."""
    s = ' ' + (text or '').lower().replace('×', 'x') + ' '
    kg = litres = count = None
    m = re.search(r'(\d+)\s*x\s*' + _N + r'\s*(' + _UNITS + r')\b', s)
    if m:
        v = int(m.group(1)) * _f(m.group(2))
        u = m.group(3)
        if u in WEIGHT:
            kg = v * WEIGHT[u]
        else:
            litres = v * VOLUME[u]
    else:
        m = re.search(_N + r'\s*(' + _UNITS + r')\b', s)
        if m:
            v, u = _f(m.group(1)), m.group(2)
            if u in WEIGHT:
                kg = v * WEIGHT[u]
            else:
                litres = v * VOLUME[u]
    m = re.search(r'(\d+)\s*(?:' + _COUNTS + r')\b\.?', s)
    if m and kg is None and litres is None:
        count = int(m.group(1))
    elif kg is None and litres is None and count is None:
        if re.search(r'\bper\s*(kilo|kg)\b|^\s*(kilo|kg)\s*$', s):
            kg = 1.0
        elif re.search(r'\b(per\s*)?(stuk|stuks|st|bos|krop)\b', s) and not re.search(r'\d', s):
            count = 1
    return kg, litres, count


def structured(name, price, size):
    """The structured raw_price prices.py reads: item, and per_kg / per_l / per_dozen / per_unit."""
    kg, litres, count = parse_size(size)
    if kg is None and litres is None and count is None:
        kg, litres, count = parse_size(name)        # Jumbo writes the size in the name
    parts = ['item=%.2f' % price]
    if kg and kg >= 0.005:
        parts.append('per_kg=%.4f' % (price / kg))
    if litres and litres >= 0.005:
        parts.append('per_l=%.4f' % (price / litres))
    if count:
        if EGGS.search(name):
            if 4 <= count <= 30:
                parts.append('per_dozen=%.4f' % (price / count * 12))
        elif count <= 12:
            parts.append('per_unit=%.4f' % (price / count))
    return ';'.join(parts) if len(parts) > 1 else None


def raw_name(name, size):
    """The shelf name with its pack size, so two sizes of one product are two rows."""
    name = re.sub(r'\s+', ' ', name).strip()
    size = re.sub(r'\s+', ' ', size or '').strip()
    if size and size.lower().replace('per ', '') not in name.lower():
        return '%s, %s' % (name, size)
    return name


def rows(data, matcher):
    """The file → (chain, store, raw name, raw price, url) for products the Dutch rules know."""
    seen = Counter()
    out = []
    for shop in data:
        if shop.get('n') in SKIP_CHAINS or not shop.get('d'):
            continue
        chain = (shop.get('c') or shop['n'])[:50]
        base = shop.get('u') or ''
        for p in shop['d']:
            name, price = p.get('n') or '', p.get('p')
            if not name or not isinstance(price, (int, float)) or not LOW <= price <= HIGH:
                seen['bad price'] += 1
                continue
            full = raw_name(name, p.get('s'))
            product, how, _ = matcher.match(full, 'nl')
            if how not in ('rule', 'unlisted'):
                seen[how or 'no match'] += 1
                continue
            rp = structured(name, float(price), p.get('s'))
            if rp is None:
                seen['no size'] += 1
                continue
            seen['kept'] += 1
            link = p.get('l') or ''
            out.append((chain, full, rp, (base + link)[:500] if link else base[:500]))
    return out, seen


def main(dry_run=False):
    from pipeline.matcher import Matcher
    body = get(URL, timeout=120)
    data = json.loads(body)
    print('checkjebon.nl: %.1f MB, %s' % (len(body) / 1e6, ', '.join(
        '%s %d' % (s.get('c') or s['n'], len(s.get('d') or [])) for s in data)))
    del body
    found, seen = rows(data, Matcher())
    del data
    print('  ' + ', '.join('%s %d' % kv for kv in seen.most_common()))
    if dry_run:
        for r in found[:40]:
            print('  ', r[0], '|', r[1], '|', r[2])
        return

    from utils.db import get_connection, ensure_raw_schema, save_raw
    from pipeline import normalize, market_average
    conn = get_connection()
    try:
        ensure_raw_schema(conn)
        for chain, name, rp, url in found:
            save_raw(conn, chain=chain, store_name='%s online (via checkjebon.nl)' % chain, postal_code='',
                     city='', region=None, category='checkjebon.nl', raw_name=name, raw_price=rp,
                     raw_unit_price='', url=url, country=COUNTRY)
        conn.commit()
    finally:
        conn.close()
    print('  %d rows stored for %s' % (len(found), COUNTRY))
    normalize.run(COUNTRY)
    market_average.run(COUNTRY)


if __name__ == '__main__':
    main(dry_run='--dry-run' in sys.argv)
