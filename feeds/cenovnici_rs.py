"""
Serbia: shelf prices from the price lists chains must publish by law.

Under the Pravilnik o uslovima, sadržaju i načinu objavljivanja cenovnika
(Sl. glasnik RS 76/2026) Serbian retailers publish their full price lists
as CSV, and each list is registered as a dataset on the national open-data
portal, data.gov.rs, under the Serbian open data licence (Srpska licenca za
otvorene podatke: reuse allowed, name the source and the date it was
taken). One format for every chain, semicolon-separated:

    KATEGORIJA; NAZIV KATEGORIJE; Naziv proizvoda; Robna marka; Barkod;
    Jedinica mere; Naziv trgovca - formata; Datum cenovnika; Redovna cena;
    Cena po jedinici mere; Snižena cena; Datum početka/kraja sniženja;
    Stopa PDV; VRSTA_CENOVNIKA (VAZECI_CENOVNIK = today's list,
    MESECNI_PRESEK = the list on the 1st of each month)

When a chain's stores differ, the list gives the chain's highest price —
stated on every dataset page. Prices are in dinars (RSD).

Which chains: the big grocery chains that publish there. Each dataset is
looked up through the portal's API, so a chain moving its file to a new
address is followed. About 125 MB a week in all, read a line at a time.

What is stored: of each chain's current list, the products in the fresh
categories (fruit and vegetables, fresh and processed meat, milk and dairy
and eggs) whose names the Serbian rules (pipeline/rules_sr.py) map to a
fresh catalogue product, at the regular price; one row per product, the
median over the chain's formats (Maxi / Mega Maxi / Shop&Go, Idea / Roda /
Mercator, Univerexport S / M / L).

    python feeds/cenovnici_rs.py
"""

import csv
import io
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get_json
from feeds import lawlists

API = 'https://data.gov.rs/api/1/datasets/%s/'

# data.gov.rs dataset id → the name the site shows.
CHAINS = [
    ('68f203a18b8ba3a1d826fa77', 'Maxi (Delhaize)'),
    ('68f61c62dc53a8c8410427f1', 'Idea / Roda / Mercator'),
    ('68f61917f9daecc02d803b84', 'Lidl'),
    ('6a995df0dd81fa516823b4d2', 'Univerexport'),
    ('68f76ce9f9a700f329626af1', 'Gomex'),
    ('68f5fbaf18e768ba3e8ccc41', 'Aman'),
    ('68f0d59ff413b4011f0f9e12', 'Super Vero (Veropoulos)'),
]

FRESH = ('sveže voće i povrće', 'sveže i prerađeno meso', 'mleko, mlečni i mešoviti proizvodi, jaja',
         'свеже воће и поврће', 'свеже и прерађено месо', 'млеко, млечни и мешовити производи, јаја')

KG_UNITS = {'kg', 'kgr', 'кг'}
L_UNITS = {'l', 'lit', 'л'}
PIECE_UNITS = {'kom', 'kom.', 'komad', 'ком', 'kos'}


def csv_url(dataset_id):
    d = get_json(API % dataset_id)
    for r in d.get('resources', []):
        if (r.get('format') or '').lower() == 'csv' and 'ean' not in (r.get('title') or '').lower():
            return r['url']
    raise ValueError('no CSV in dataset %s' % dataset_id)


def read_list(path, chain, judge):
    """One chain's file → rows to store."""
    with open(path, 'rb') as f:
        head = f.read(4096)
    enc = 'utf-8-sig'
    try:
        head.decode('utf-8')
    except UnicodeDecodeError:
        enc = 'cp1250'

    current = defaultdict(list)    # list date → rows; the newest list is used
    vazeci = []
    with open(path, encoding=enc, errors='replace', newline='') as f:
        reader = csv.reader(f, delimiter=';')
        next(reader, None)
        for r in reader:
            if len(r) < 15 or r[1].strip().lower() not in FRESH:
                continue
            if r[14].strip() == 'VAZECI_CENOVNIK':
                vazeci.append(r)
            else:
                current[r[7].strip()].append(r)
    if vazeci:
        rows = vazeci
    elif current:
        def day(s):
            m = re.match(r'(\d{1,2})[.-](\d{1,2})[.-](\d{4})', s)
            return (int(m.group(3)), int(m.group(2)), int(m.group(1))) if m else (0, 0, 0)
        rows = current[max(current, key=day)]
    else:
        return []

    prices = defaultdict(list)
    meta = {}
    for r in rows:
        name = r[2].strip()
        p = judge.product(name)
        if not p:
            continue
        v = lawlists.num(r[8])
        if not v or v <= 0:
            continue
        prices[name].append(v)
        meta[name] = (p, r[5].strip().lower(), lawlists.num(r[9]), r[1].strip())

    out = []
    for name, values in prices.items():
        p, unit, unit_price, category = meta[name]
        price = lawlists.mid(values)
        # The unit price equals the price when the product is sold by the
        # unit it is quoted in: by the kilo at the counter, or by the piece.
        same = unit_price is not None and abs(unit_price - max(values)) < 0.011
        per = lawlists.per_basis(
            p, name, price,
            sold_by_kg=unit in KG_UNITS and same,
            sold_by_l=unit in L_UNITS and same,
            piece=unit in PIECE_UNITS and same,
        )
        if p['category'] == 'eggs' and not per:
            continue
        if not lawlists.sane(per, low=2, high=30000):
            continue
        out.append({'chain': chain, 'raw_name': name, 'raw_price': lawlists.structured(price, per),
                    'stores': 0})
    return out


def run():
    judge = lawlists.Judge('sr')
    rows, urls = [], []
    for dataset_id, chain in CHAINS:
        try:
            url = csv_url(dataset_id)
            path = lawlists.download(url, suffix='.csv')
        except Exception as e:
            print('  %-26s not read: %s' % (chain, e))
            continue
        try:
            got = read_list(path, chain, judge)
        finally:
            os.remove(path)
        print('  %-26s %4d products' % (chain, len(got)))
        rows.extend(got)
        urls.append(url)
    if not rows:
        raise SystemExit('no Serbian price list could be read')
    lawlists.store('RS', rows, 'https://data.gov.rs/ (Pravilnik o cenovnicima)')
    lawlists.run_pipeline('RS')


if __name__ == '__main__':
    run()
