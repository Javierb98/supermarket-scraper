"""
Portugal: Continente online shelf prices (continente.pt), read politely.

Continente (Sonae, Portugal's largest chain) publishes its whole catalogue on
continente.pt as ordinary server-rendered pages. Its robots.txt allows the
aisle pages and product pages and forbids search, the basket, the account
area and every query-string variant (?start=, ?sz=, ?pmin=, …) — so this reads
only the first page of each aisle, the way a visitor arriving from a link
would, and never pages through results. An aisle shows up to 36 products;
the aisles below are the small "leaf" aisles (Maçã, Batata, Ovos, Frango, …),
almost all of which have fewer than that. The service policy
(/loja-online/politica-de-servicos/) has no clause against reading the pages.

Prices are the online shop's, one national price list, so region is None.
Each product tile says:

    Banana Continente | Quant. Mínima = 600 gr (3 un) | 1,19€/kg | 0,24€/un
    Uva Branca sem Grainha Continente | emb. 500 gr | 2,79€ | 5,58€/kg
    (on offer)  1,69€ struck through | 1,49€/kg | 0,45€/un

and becomes a raw row in the structured format pipeline/prices.py reads:

    item=2.79;per_kg=5.58            item=1.19;per_kg=1.19;per_unit=0.24;regular=1.69

Eggs, sold per box, are also given per dozen. The aisle path goes to
shop_category so normalize can tell a fresh-produce aisle from a dried-fruit
one. Matching to the catalogue is pipeline/rules_pt.py, then normalize and
market_average for PT, as for any shop:

    python feeds/continente.py
    python pipeline/normalize.py --country PT
    python pipeline/market_average.py --country PT
"""

import html
import json
import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get  # noqa: E402
from utils.db import get_connection, ensure_raw_schema, save_raw  # noqa: E402

CHAIN = 'Continente'
BASE = 'https://www.continente.pt/supermercado/'

# Leaf aisles with things a farm sells. First page only (robots.txt forbids ?start=).
AISLES = [
    'frutas-e-legumes/frutas/banana/',
    'frutas-e-legumes/frutas/maca/',
    'frutas-e-legumes/frutas/pera/',
    'frutas-e-legumes/frutas/laranja-e-clementina/',
    'frutas-e-legumes/frutas/limao-e-lima/',
    'frutas-e-legumes/frutas/kiwi/',
    'frutas-e-legumes/frutas/uvas/',
    'frutas-e-legumes/frutas/pessego-e-ameixa/',
    'frutas-e-legumes/frutas/morango-e-frutos-vermelhos/',
    'frutas-e-legumes/frutas/melao-e-melancia/',
    'frutas-e-legumes/frutas/frutas-sazonais/',
    'frutas-e-legumes/frutas/frutas-tropicais/',
    'frutas-e-legumes/legumes/batata/',
    'frutas-e-legumes/legumes/tomate-e-alface/',
    'frutas-e-legumes/legumes/cebola-e-alho/',
    'frutas-e-legumes/legumes/cenoura-e-abobora/',
    'frutas-e-legumes/legumes/couve-e-brocolo/',
    'frutas-e-legumes/legumes/curgete-e-beringela/',
    'frutas-e-legumes/legumes/pepino-e-pimento/',
    'frutas-e-legumes/legumes/feijao-verde/',
    'frutas-e-legumes/legumes/espinafres/',
    'frutas-e-legumes/legumes/nabo-e-beterraba/',
    'frutas-e-legumes/legumes/cogumelos/',
    'frutas-e-legumes/legumes/espargos-e-exoticos/',
    'frutas-e-legumes/aromaticas/',
    'laticinios-e-ovos/ovos/',
    'laticinios-e-ovos/leites/inteiro/',
    'laticinios-e-ovos/manteigas-e-cremes/manteigas/',
    'charcutaria-e-queijos/queijo-curado/ovelha/',
    'charcutaria-e-queijos/queijo-curado/cabra/',
    'charcutaria-e-queijos/queijos-frescos/queijo-fresco/',
    'charcutaria-e-queijos/queijos-frescos/requeijao/',
    'charcutaria-e-queijos/queijos-frescos/ricotta/',
    'charcutaria-e-queijos/queijos-frescos/mozzarella/',
    'mercearia/compotas-cremes-e-mel/mel/',
    'mercearia/azeite-oleo-e-vinagre/azeite/',
    'talho/frango/',
    'talho/peru/',
    'talho/pato-e-coelho/',
    'talho/porco/',
    'talho/cabrito-e-borrego/',
    'talho/novilho-vitela-e-vitelao/',
]

NUM = r'(\d+(?:[.,]\d+)?)'


def num(s):
    return float(s.replace('.', '').replace(',', '.')) if ',' in s else float(s)


def text(fragment):
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', '', fragment or ''))).strip()


def price_and_unit(s):
    """'2,79€' → (2.79, None); '1,19€/kg' → (1.19, 'kg'); '5,58€/lt' → (5.58, 'l')."""
    m = re.search(NUM + r'\s*€\s*(?:/\s*([a-zA-Z]+))?', s or '')
    if not m:
        return None, None
    unit = (m.group(2) or '').lower() or None
    unit = {'lt': 'l', 'ltr': 'l', 'l': 'l', 'kg': 'kg', 'un': 'unit', 'dz': 'dozen', 'doz': 'dozen'}.get(unit, unit)
    return num(m.group(1)), unit


def parse_tile(tile):
    """One product tile's HTML → dict, or None when it has no price."""
    m = re.search(r"data-product-tile-impression='([^']+)'", tile)
    if not m:
        return None
    meta = json.loads(html.unescape(m.group(1)))
    name = (meta.get('name') or '').strip()
    url = re.search(r'href="(https://www\.continente\.pt/produto/[^"]+)"', tile)
    qty = re.search(r'<p class="pwc-tile--quantity">(.*?)</p>', tile, re.S)
    primary = re.search(r'<span class="pwc-tile--price-primary">(.*?)</span>\s*</div>', tile, re.S)
    secondary = re.search(r'<div class="pwc-tile--price-secondary[^"]*">(.*?)</div>', tile, re.S)
    before = re.search(r'pwc-tile--price-dashed">\s*<span[^>]*>(.*?)</span>', tile, re.S)
    if not name or not primary:
        return None
    return {
        'id': meta.get('id'),
        'name': name,
        'aisle': meta.get('category') or '',
        'quantity': text(qty.group(1)) if qty else '',
        'primary': text(primary.group(1)).replace(' ', ''),     # "2<span>,79€</span>" → "2,79€"
        'secondary': text(secondary.group(1)) if secondary else '',
        'regular': text(before.group(1)) if before else '',
        'url': url.group(1) if url else '',
    }


def tiles(page_html):
    out = []
    for chunk in page_html.split('class="product-tile ')[1:]:
        t = parse_tile(chunk)
        if t:
            out.append(t)
    return out


def structured(t):
    """A tile → the structured raw_price ('item=…;per_kg=…'), or None."""
    fields = {}
    p, pu = price_and_unit(t['primary'])
    s, su = price_and_unit(t['secondary'])
    if p is None:
        return None
    fields['item'] = p                     # a pack's price; for something sold by weight, a kilo's
    for value, unit in ((p, pu), (s, su)):
        if value and unit in ('kg', 'l', 'unit', 'dozen'):
            fields.setdefault('per_' + unit, value)
    # A pack of pieces with no unit price on the tile ("Ovos Classe M, emb. 12 un",
    # "Abóbora Halloween, 1 un"): the price per piece is the pack's over the count.
    # (pipeline/pack.py does not read the Portuguese "un".)
    count = re.search(r'(\d+)\s*un\b', t['quantity'] or '')
    by_weight = re.search(r'\d\s*(?:k?g|gr|ml|cl|lt?)\b', t['quantity'] or '', re.I)
    if count and not by_weight and pu is None and 'per_unit' not in fields and int(count.group(1)) > 0:
        fields['per_unit'] = round(p / int(count.group(1)), 4)
    is_eggs = re.search(r'\bovos?\b', t['name'].lower()) or '/ovos' in t['aisle'].lower()
    if is_eggs and 'per_unit' in fields and 'per_dozen' not in fields:
        fields['per_dozen'] = round(fields['per_unit'] * 12, 4)
    # A price "per piece" means something for a melon or a lettuce, which
    # farms sell by the piece. For a tray of chicken breasts or a wedge of
    # cheese it is only the price of that pack, so it is not passed on.
    if 'per_unit' in fields and 'frutas e legumes' not in t['aisle'].lower():
        del fields['per_unit']
    r, _ = price_and_unit(t['regular'])
    if r and r > p:
        fields['regular'] = r
    return ';'.join(f'{k}={v}' for k, v in fields.items())


def run():
    conn = get_connection()
    ensure_raw_schema(conn)
    saved = seen = 0
    try:
        for aisle in AISLES:
            try:
                page = get(BASE + aisle, pause=2.0).decode('utf-8', 'replace')
            except Exception as e:
                print(f'  {aisle}: {e}', file=sys.stderr)
                continue
            found = tiles(page)
            seen += len(found)
            n = 0
            for t in found:
                raw_price = structured(t)
                if not raw_price:
                    continue
                # The pack size is part of what the shelf says; prices.py and
                # pack.py read it from the name.
                # "Quant. Mínima = 600 gr (3 un)" is the least you can order of
                # something sold by weight, not a pack, so it is left out.
                pack = t['quantity'] if t['quantity'] and not t['quantity'].lower().startswith('quant') else ''
                raw_name = f"{t['name']}, {pack}" if pack else t['name']
                save_raw(
                    conn, chain=CHAIN, store_name='Continente Online', postal_code='', city='',
                    region=None, category=aisle.strip('/').split('/')[-1], raw_name=raw_name[:250],
                    raw_price=raw_price, raw_unit_price=t['secondary'], url=t['url'],
                    shop_category=t['aisle'], country='PT',
                )
                n += 1
            conn.commit()
            saved += n
            print(f'  {aisle:55} {n:>3} products')
    finally:
        conn.close()
    print(f'Continente: {saved} prices saved from {seen} tiles ({date.today()})')
    if saved == 0:
        raise RuntimeError('Continente returned no products — the pages have changed or the site is refusing us')
    return saved


if __name__ == '__main__':
    run()
