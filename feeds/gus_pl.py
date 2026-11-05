"""
Poland: Statistics Poland (GUS), Local Data Bank (BDL) API.

Three tables, all national, in złoty:

  P1466  average retail prices, annual     -> retail    (eggs, chicken, dairy, honey)
  P3155  procurement prices of fruit & veg,  -> farmgate  (what buyers pay growers)
         half-yearly
  P2968  marketplace prices received by     -> farmers_market (potatoes; the other
         farmers, monthly                       items are grain and live animals)

BDL gives every period its own variable id (January's potato price is one
variable, February's another), so each item lists the ids of its periods and
the newest one with a value wins.

The API works without a key (a weekly quota far above our dozen requests).
If BDL_API_KEY is set in the environment it is sent as X-ClientId, which
raises the quota. Register free at https://api.stat.gov.pl/Home/BdlApi.

Left out on purpose: the GUS shop table's meat cuts (bone-in roast beef,
"centre" pork) that match no catalogue cut, processed goods (boiled ham,
sausages, frozen fish), plain "cabbages" (the catalogue has only red, savoy
and napa) and "other fruit/vegetables".

    python feeds/gus_pl.py

Licence: GUS data are free to reuse with the source named
("Źródło: GUS, Bank Danych Lokalnych").
"""

import os
import sys
import time
import urllib.error
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get_json

API = 'https://bdl.stat.gov.pl/api/v1'
POLAND = '000000000000'

# Annual shop prices, P1466: (variable, catalogue name, unit, factor)
RETAIL = [
    (4993,    'Eggs',                 'dozen', 12.0),   # hen eggs, per piece
    (4961,    'Whole Chicken',        'kg',    1.0),    # disembowelled chicken
    (4976,    'Whole Milk',           'l',     1.0),    # 2-2.5% fat, per litre
    (1727955, 'Fresh Cottage Cheese', 'kg',    1.0),    # twaróg
    (4981,    'Butter',               'kg',    5.0),    # per 200 g
    (1727956, 'Honey',                'kg',    2.5),    # per 400 g
]

# Half-yearly prices paid to growers, P3155: catalogue name -> (unit, [first half, second half])
HALF = ['the first half', 'the second half']
FARMGATE = {
    'onion per kg':        ('Onion',        'kg'),
    'carrots per kg':      ('Carrot',       'kg'),
    'beetroots per kg':    ('Beetroot',     'kg'),
    'cucumbers per kg':    ('Cucumber',     'kg'),
    'tomatoes per kg':     ('Tomato',       'kg'),
    'cauliflowers per piece': ('Cauliflower', 'unit'),
    'apples per kg':       ('Apples',       'kg'),
    'pears per kg':        ('Pears',        'kg'),
    'plums per kg':        ('Plums',        'kg'),
    'peaches per kg':      ('Peaches',      'kg'),
    'cherries per kg':     ('Cherries',     'kg'),      # sour cherries, as GUS reports them
    'strawberries per kg': ('Strawberries', 'kg'),
    'raspberries per kg':  ('Raspberry',    'kg'),
    'gooseberries per kg': ('Gooseberry',   'kg'),
    'walnuts and hazelnuts per kg': None,               # two nuts in one figure
}

# Monthly marketplace prices, P2968: only potatoes are a catalogue product.
MARKET = {'edible potatoes per dt': ('Potato', 'kg', 0.01)}   # per 100 kg
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July',
          'August', 'September', 'October', 'November', 'December']
HALF_START = {HALF[0]: 1, HALF[1]: 7}


def _headers():
    key = os.environ.get('BDL_API_KEY')
    return {'X-ClientId': key} if key else {}


def bdl(path, **params):
    """One BDL request, 3 s apart; on 429 wait as long as BDL asks (up to 10 minutes), once."""
    query = '&'.join(f'{k.replace("_", "-")}={v}' for k, vs in params.items()
                     for v in (vs if isinstance(vs, list) else [vs]))
    url = f'{API}/{path}?format=json&lang=en&{query}'
    try:
        return get_json(url, headers=_headers(), retries=1, pause=3.0)
    except urllib.error.HTTPError as e:
        if e.code != 429:
            raise
        wait = int(''.join(c for c in (e.headers.get('Retry-After') or '60') if c.isdigit()) or 60)
        if wait > 600:
            raise
        print(f'  BDL asked us to wait {wait} s')
        time.sleep(wait + 5)
        return get_json(url, headers=_headers(), retries=1, pause=3.0)


def variables(subject):
    out, page = [], 0
    while True:
        d = bdl('variables', subject_id=subject, page_size=100, page=page)
        out += d['results']
        if len(out) >= d['totalRecords'] or not d['results']:
            return out
        page += 1


def values(var_ids, years):
    """{variable id: {year: value}} for Poland."""
    out = {}
    ids = list(var_ids)
    for i in range(0, len(ids), 50):          # page-size, or BDL returns only 10 variables
        d = bdl(f'data/by-unit/{POLAND}', var_id=ids[i:i + 50], year=years, page_size=100)
        for r in d['results']:
            out[r['id']] = {int(v['year']): v['val'] for v in r['values'] if v['val'] is not None}
    return out


def retail(years):
    got = values([v for v, *_ in RETAIL], years)
    figures = []
    for var, name, unit, factor in RETAIL:
        series = got.get(var) or {}
        if series:
            y = max(series)
            figures.append(Figure(name, series[y] * factor, unit, date(y, 1, 1)))
    return figures


def periodic(subject, wanted, period_start, years):
    """Newest value per item from a table with one variable per period."""
    vs = [v for v in variables(subject) if v.get('n2') in wanted and v.get('n1') in period_start]
    got = values([v['id'] for v in vs], years)
    best = {}
    for v in vs:
        for y, val in (got.get(v['id']) or {}).items():
            when = date(y, period_start[v['n1']], 1)
            if v['n2'] not in best or when > best[v['n2']][0]:
                best[v['n2']] = (when, val)
    return best


def main():
    this = date.today().year
    years = [this - 2, this - 1, this]

    write('PL', 'GUS Poland, BDL average retail prices (annual)', 'retail', retail(years))

    picked = {k: v for k, v in FARMGATE.items() if v}
    figures = [Figure(picked[k][0], val, picked[k][1], when)
               for k, (when, val) in periodic('P3155', picked, HALF_START, years).items()]
    write('PL', 'GUS Poland, BDL procurement prices of fruit and vegetables', 'farmgate', figures)

    months = {m: i + 1 for i, m in enumerate(MONTHS)}
    figures = [Figure(MARKET[k][0], val * MARKET[k][2], MARKET[k][1], when)
               for k, (when, val) in periodic('P2968', MARKET, months, years).items()]
    write('PL', 'GUS Poland, BDL marketplace prices received by farmers', 'farmers_market', figures)


if __name__ == '__main__':
    main()
