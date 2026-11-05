"""
Croatia: shelf prices from the price lists every chain must publish by law.

Since May 2025 (Odluka o objavi cjenika …, NN 75/2025) every Croatian chain
publishes its full price list, store by store, every day. cijene.dev
(DobarKod, open source) collects them all and offers each day as one ZIP of
CSV files, free and without registration:

    https://api.cijene.dev/v0/list            the archives, newest first
    https://api.cijene.dev/v0/archive/<date>.zip
        <chain>/stores.csv    store_id, type, address, city, zipcode
        <chain>/products.csv  product_id, barcode, name, brand, category, unit, quantity
        <chain>/prices.csv    store_id, product_id, price, unit_price, best_price_30,
                              anchor_price, special_price, available, ...

Their API has a free tier of 1,000 requests a day and asks heavy commercial
users for a paid plan, so this reads only the archive files, which the site
offers for free download ("Besplatni pristup sirovim podacima"). Terms:
https://cijene.dev/uvjeti-koristenja ("Korisnik može slobodno koristiti
podatke u svojim aplikacijama"); the prices themselves are public by law.

One archive is ~140 MB zipped (~770 MB of CSV); it is streamed to a
temporary file and read a row at a time, so memory stays small.

What is stored: for each chain, each product whose name the Croatian rules
(pipeline/rules_hr.py) map to a fresh catalogue product, one row with the
median regular price over the chain's stores. The country figure comes out
of normalise and average as for any shop. Metro (cash & carry, trade
prices) and dm (a drugstore) are left out.

    python feeds/cijene_hr.py               newest archive
    python feeds/cijene_hr.py 2026-11-03    that day's
"""

import csv
import io
import os
import re
import sys
import zipfile
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get_json
from feeds import lawlists

LIST_URL = 'https://api.cijene.dev/v0/list'
SKIP = {'metro', 'dm'}
NAMES = {
    'konzum': 'Konzum', 'spar': 'Spar', 'lidl': 'Lidl', 'kaufland': 'Kaufland', 'plodine': 'Plodine',
    'studenac': 'Studenac', 'tommy': 'Tommy', 'eurospin': 'Eurospin', 'ntl': 'NTL', 'ribola': 'Ribola',
    'ktc': 'KTC', 'zabac': 'Žabac', 'vrutak': 'Vrutak', 'roto': 'Roto', 'trgocentar': 'Trgocentar',
    'boso': 'Boso', 'gavranovic': 'Gavranović', 'jadranka_trgovina': 'Jadranka', 'bure': 'Bure',
    'djelo_vodice': 'Djelo Vodice', 'branka': 'Branka', 'stanic': 'Stanić', 'stridon': 'Stridon',
    'trgovina-krk': 'Trgovina Krk', 'dukat': 'Dukat',
}

KG_UNITS = {'kg', 'kgm', 'kgr', '1kg', 'kilogram'}
L_UNITS = {'l', 'lit', 'lt', 'ltr', '1l', 'litra'}
PIECE_UNITS = {'kom', 'ko', 'kom.', 'komad', 'pz', 'pak', 'kos', 'kut', 'pce', 'st'}

# A chain's internal suffix on a name ("Jabuka zelena 2 kg_OC").
CODE_SUFFIX = re.compile(r'_[A-Z]{1,3}$')
# "KG" written in the name without a number: weighed at the till.
BY_KG = re.compile(r'(?<![\d.,])\s(kg|kilogram)\b', re.I)


def qty_is_one(qty):
    """The quantity column says one kilo, litre or piece (or nothing)."""
    m = re.match(r'^\s*([\d.,]+)?\s*([a-z]*)', qty or '')
    v = lawlists.num(m.group(1)) if m and m.group(1) else None
    u = m.group(2) if m else ''
    if v is None:
        return True
    if u in ('g', 'ml', 'gr'):
        return abs(v - 1000) < 1e-6
    return abs(v - 1) < 1e-6


def archive(date=None):
    archives = get_json(LIST_URL)['archives']
    if date:
        archives = [a for a in archives if a['date'] == date]
    if not archives:
        raise SystemExit('no archive for %s' % date)
    return archives[0]


def read_chain(z, chain, judge):
    """→ list of stored rows for one chain."""
    keep = {}           # product_id → (name, catalogue product, unit, quantity)
    with z.open(chain + '/products.csv') as f:
        for r in csv.DictReader(io.TextIOWrapper(f, 'utf-8', errors='replace')):
            name = CODE_SUFFIX.sub('', (r.get('name') or '').strip())
            p = judge.product(name) if name else None
            if p:
                keep[r['product_id']] = (name, p, (r.get('unit') or '').strip().lower(), (r.get('quantity') or '').strip().lower())
    if not keep:
        return []

    prices = defaultdict(list)
    with z.open(chain + '/prices.csv') as f:
        reader = csv.reader(io.TextIOWrapper(f, 'utf-8', errors='replace'))
        head = next(reader)
        i_pid, i_price = head.index('product_id'), head.index('price')
        i_avail = head.index('available') if 'available' in head else None
        for row in reader:
            if len(row) <= i_price or row[i_pid] not in keep:
                continue
            if i_avail is not None and len(row) > i_avail and row[i_avail] == '0':
                continue
            v = lawlists.num(row[i_price])
            if v and v > 0:
                prices[row[i_pid]].append(v)

    # The same name under several product ids (a chain's regional codes) is
    # one shelf product.
    by_name = defaultdict(list)
    meta = {}
    for pid, values in prices.items():
        name, p, unit, qty = keep[pid]
        by_name[name].extend(values)
        meta[name] = (p, unit, qty)

    out = []
    for name, values in by_name.items():
        p, unit, qty = meta[name]
        price = lawlists.mid(values)
        unit_word = unit.split()[0] if unit else ''
        one = qty_is_one(qty)
        per = lawlists.per_basis(
            p, name, price,
            sold_by_kg=(unit_word in KG_UNITS and one) or bool(BY_KG.search(' ' + name)),
            sold_by_l=unit_word in L_UNITS and one,
            piece=unit_word in PIECE_UNITS and one,
            size_text=unit if any(c.isdigit() for c in unit) else '',
            unit_count=lawlists.egg_count(unit, qty, name) if p['category'] == 'eggs' else None,
        )
        if p['category'] == 'eggs' and not per:
            continue
        if not lawlists.sane(per):
            continue
        out.append({
            'chain': NAMES.get(chain, chain.replace('_', ' ').title()),
            'raw_name': name,
            'raw_price': lawlists.structured(price, per),
            'stores': len(values),
        })
    return out


def run(date=None):
    a = archive(date)
    print('cijene.dev archive %s (%.0f MB)' % (a['date'], a['size'] / 1e6))
    path = lawlists.download(a['url'], suffix='.zip')
    judge = lawlists.Judge('hr')
    rows = []
    try:
        with zipfile.ZipFile(path) as z:
            chains = sorted({n.split('/')[0] for n in z.namelist() if n.endswith('/prices.csv')})
            for chain in chains:
                if chain in SKIP:
                    continue
                got = read_chain(z, chain, judge)
                print('  %-18s %4d products' % (chain, len(got)))
                rows.extend(got)
    finally:
        os.remove(path)
    lawlists.store('HR', rows, a['url'])
    lawlists.run_pipeline('HR')


if __name__ == '__main__':
    run(sys.argv[1] if len(sys.argv) > 1 else None)
