"""
Estonia: shelf prices from Selver's public catalogue (selver.ee).

Selver is Estonia's second-largest grocery chain, and its e-shop reads its
catalogue from an Elasticsearch-style endpoint that robots.txt explicitly
allows (Allow: /api/catalog/vue_storefront_catalog_et/). No key, no login.
One price list for the whole country, so the figures are national.

Only the aisles where a farm's products sit are read — vegetables, fruit,
berries, mushrooms, eggs, milk and cream, butter, cottage cheese, cheese and
fresh meat — about 1,000 products in some 20 requests, a second apart.

What is stored per product, in the structured form pipeline/prices.py reads:

    item      the guest price (customer group 0) — what anyone pays
    per_kg / per_l / per_unit
              Selver's own unit price, by the product's comparison unit
    per_dozen eggs, from the price per egg
    regular   the price before an offer, when there is one

Then the Estonian rules (pipeline/rules_et.py) match the names and the
Estonian figures are averaged, in this same run: the weekly run normalises
and averages before it calls the feeds, so a feed that only saved raw rows
would be a week late.

    python feeds/selver.py
"""

import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get_json
from utils.db import get_connection, ensure_raw_schema, save_raw

API = 'https://www.selver.ee/api/catalog/vue_storefront_catalog_et/product/_search'
SHOP = 'https://www.selver.ee/'
CHAIN = 'Selver'
COUNTRY = 'EE'
PAGE = 100

# Aisle id → Selver's name for it (from the category index).
AISLES = [
    (213, 'Köögiviljad, juurviljad'),
    (215, 'Maitsetaimed, värsked salatid, piprad, idud'),
    (210, 'Õunad, pirnid'),
    (212, 'Troopilised, eksootilised viljad'),
    (217, 'Marjad'),
    (214, 'Seened'),
    (239, 'Munad'),
    (234, 'Piimad, koored'),
    (240, 'Võid, margariinid'),
    (235, 'Kohupiimad, kodujuustud'),
    (243, 'Juustud'),
    (245, 'Delikatessjuustud'),
    (222, 'Hakkliha'),
    (220, 'Linnuliha'),
    (219, 'Sealiha'),
    (221, 'Veise-, lamba- ja ulukiliha'),
]
EGG_AISLE = 239

# Selver's comparison units (product_compare_unit): what unit_price is per.
UNITS = {75: 'kg', 89: 'l', 18: 'unit', 468: 'unit'}

FIELDS = ','.join([
    'name', 'url_key', 'status', 'prices', 'final_price_incl_tax', 'unit_price',
    'product_compare_unit', 'product_volume',
])


def aisle(cat_id):
    """Every product in one aisle, a page at a time."""
    out, start = [], 0
    while True:
        q = urllib.parse.urlencode({
            'size': PAGE, 'from': start, 'q': f'category_ids:{cat_id}', '_source_include': FIELDS,
        })
        d = get_json(f'{API}?{q}', pause=1.0)
        hits = d['hits']['hits']
        out.extend(h['_source'] for h in hits)
        start += PAGE
        total = d['hits']['total']
        total = total['value'] if isinstance(total, dict) else total
        if not hits or start >= total:
            return out


def structured(p, eggs=False):
    """A Selver product → 'item=…;per_kg=…;regular=…', or None without a price."""
    guest = next((x for x in p.get('prices') or [] if x.get('customer_group_id') == 0), None)
    item = guest['price'] if guest else p.get('final_price_incl_tax')
    if not item or item <= 0:
        return None
    regular = guest.get('original_price') if guest else None
    fields = {'item': round(float(item), 2)}

    unit = UNITS.get(p.get('product_compare_unit'))
    per = p.get('unit_price')
    if unit and per and per > 0:
        if eggs and unit == 'unit':
            fields['per_dozen'] = round(float(per) * 12, 4)
        elif not eggs:
            fields['per_' + unit] = round(float(per), 4)
    if regular and regular > item + 0.004:
        fields['regular'] = round(float(regular), 2)
    return ';'.join(f'{k}={v}' for k, v in fields.items())


def run():
    conn = get_connection()
    saved = 0
    try:
        ensure_raw_schema(conn)
        seen = set()
        for cat_id, cat_name in AISLES:
            products = aisle(cat_id)
            kept = 0
            for p in products:
                name = (p.get('name') or '').strip()
                if not name or name in seen or p.get('status') not in (None, 1):
                    continue
                price = structured(p, eggs=(cat_id == EGG_AISLE))
                if price is None:
                    continue
                seen.add(name)
                # The aisle goes in `category`, not `shop_category`: the
                # fresh-aisle check (pipeline/processed.py) has no Estonian
                # words yet and would turn every vegetable away. These aisles
                # are chosen as fresh ones anyway.
                save_raw(conn, chain=CHAIN, store_name='Selver e-pood', postal_code='', city=None, region=None,
                         category=cat_name, raw_name=name, raw_price=price, raw_unit_price=None,
                         url=SHOP + (p.get('url_key') or ''), country=COUNTRY)
                kept += 1
            conn.commit()
            saved += kept
            print(f'  {cat_name:45} {len(products):4} products, {kept:4} stored')
    finally:
        conn.close()

    print(f'Selver: {saved} shelf prices stored')
    if saved == 0:
        raise RuntimeError('Selver returned nothing — the catalogue API has changed')
    return saved


def finish(country):
    """Match and average this country's new rows now, not a week from now."""
    from pipeline import normalize, market_average
    normalize.run(country)
    market_average.run(country)


if __name__ == '__main__':
    run()
    if '--no-average' not in sys.argv:
        finish(COUNTRY)
