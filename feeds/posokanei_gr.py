"""
Greece: shelf prices from PosoKanei, the government's supermarket price
observatory, through its public daily archive on GitHub.

Greek supermarket chains must report their daily shelf prices to the state
(Law 4796/2021, art. 57; first the e-katanalotis platform, since 2026
posokanei.gov.gr). The site's API is undocumented and answers 403 from
outside Greece, so this reads the daily snapshots that the open project
spyrosavl/posokanei archives on GitHub — one JSON file a day with every
product and its price at every chain:

    https://raw.githubusercontent.com/spyrosavl/posokanei/main/data/latest.json
        → {"date": ..., "path": "data/2026/posokanei-<date>.json"}

Terms: the repository is MIT-licensed; it says the data are © the
operators of posokanei.gov.gr and archived for research and preservation.
No reuse licence is stated for the prices, so — as with the Dutch and
Austrian collections — they are used with attribution and would be removed
on request.

Coverage: about 10,000 products at 11 Greek chains (Sklavenitis, AB
Vassilopoulos, Lidl, Masoutis, My Market, Kritikos, Galaxias, Halkiadakis,
Synka, Market In, Bazaar). The observatory lists packaged goods only: eggs,
milk, yoghurt, butter, cream, cheese, fresh poultry and a few packed
vegetables (mushrooms, baby spinach) — no loose fruit and vegetables and
no red meat. Prices are in euro.

What is stored: the products in those fresh categories whose names the
Greek rules (pipeline/rules_el.py) map to a catalogue product, one row per
chain and product, at the regular price (a discount is undone with its
percentage).

    python feeds/posokanei_gr.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get_json
from feeds import lawlists

RAW = 'https://raw.githubusercontent.com/spyrosavl/posokanei/main/'

# The observatory's categories (English names) worth reading, with all
# their sub-categories.
FRESH_CATEGORIES = {
    'Eggs', 'Fresh/High-temperature pasteurized/Long-life', 'Yogurts', 'Butter / Margarine', 'Cream Custard',
    'Cheese', 'Fresh Poultry', 'Vegetables',
}

# Branches under which a "Vegetables" category is frozen or tinned.
NOT_FRESH = {'Frozen Food', 'Canned goods / Puree', 'Prepared Foods'}

PIECE = {'pcs', 'pc', 'τεμ'}


def fresh_category_ids(categories):
    """The ids of the fresh categories and everything below them, each with
    the English name of the fresh category it belongs to."""
    by_id = {c['category_id']: c for c in categories}
    out = {}
    for c in categories:
        node, seen, fresh = c, set(), None
        while node and node['category_id'] not in seen:
            seen.add(node['category_id'])
            name = (node.get('name_en') or '').strip()
            if name in NOT_FRESH:
                fresh = None
                break
            if name in FRESH_CATEGORIES and fresh is None:
                fresh = name
            node = by_id.get(node.get('parent_id'))
        if fresh:
            out[c['category_id']] = fresh
    return out


def shelf_name(product):
    """The product's name without the brand in front ("ΝΙΤΣΙΑΚΟΣ Κοτόπουλο
    Μπούτι" → "Κοτόπουλο Μπούτι"): the rules read the product, which the
    brand would otherwise hide."""
    name = ' '.join((product.get('name') or '').split())
    brand = ' '.join((product.get('brand') or '').split())
    if brand and name.upper().startswith(brand.upper() + ' '):
        name = name[len(brand):].strip()
    return name


def rows_from(snapshot, judge):
    greek = {r['id']: r for r in snapshot['retailers']['retailers'] if r.get('country') == 'GR'}
    allowed = fresh_category_ids(snapshot['categories']['categories'])
    out = []
    for p in snapshot['products']:
        cats = [allowed[c] for c in p.get('category_ids') or [] if c in allowed]
        if not cats:
            continue
        name = shelf_name(p)
        product = judge.product(name)
        if not product:
            continue
        unit = (p.get('unit') or '').lower()
        qty = p.get('unit_quantity') or 0
        for rp in p.get('retailer_prices') or []:
            if rp.get('retailer') not in greek or not rp.get('price'):
                continue
            price = float(rp['price'])
            regular = None
            pct = rp.get('discount_percentage')
            if rp.get('is_discount') and pct and 0 < float(pct) < 90:
                regular = round(price / (1 - float(pct) / 100), 2)
            per = {}
            norm = rp.get('price_normalized') or (price / qty if qty else None)
            if product['category'] == 'eggs':
                n = int(round(qty)) if unit in PIECE and qty else lawlists.egg_count(name)
                if n in lawlists.DOZEN_SIZES:
                    per['dozen'] = price / n * 12
                else:
                    continue
            elif norm and unit == 'kg':
                per['kg'] = float(norm)
            elif norm and unit == 'l':
                per['l'] = float(norm)
            elif norm and unit in PIECE and product['category'] in lawlists.FRESH_PIECES:
                per['unit'] = float(norm)
            if not per or not lawlists.sane(per):
                continue
            out.append({
                'chain': greek[rp['retailer']].get('name') or rp['retailer'],
                'raw_name': name,
                'raw_price': lawlists.structured(price, per, regular),
                'shop_category': cats[0],
                'stores': 0,
            })
    return out


def run():
    latest = get_json(RAW + 'data/latest.json')
    url = RAW + latest['path']
    print('PosoKanei snapshot %s' % latest['date'])
    path = lawlists.download(url, suffix='.json')
    try:
        with open(path, encoding='utf-8') as f:
            snapshot = json.load(f)
    finally:
        os.remove(path)
    rows = rows_from(snapshot, lawlists.Judge('el'))
    del snapshot
    if not rows:
        raise SystemExit('no Greek prices matched')
    lawlists.store('GR', rows, url)
    lawlists.run_pipeline('GR')


if __name__ == '__main__':
    run()
