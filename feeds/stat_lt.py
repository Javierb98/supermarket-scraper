"""
Lithuania: two monthly tables from Statistics Lithuania's SDMX service
(osp-rs.stat.gov.lt), national, euros.

1. S7R244 (dataflow S7R244_M2021135_1), average monthly retail prices of the
   most popular products -> 'retail'. About 90 items, shop prices.
2. S7R307 (dataflow S7R307_M9100110, compiled by the Agricultural Data
   Centre, ŽŪDC), average prices of agricultural and food products in
   Lithuanian markets -> 'farmers_market'. Marketplace (turgus) stall prices,
   with Lithuanian-grown and imported produce priced separately; only the
   Lithuanian-grown lines are used, since those are what a farm competes with.

The SDMX answer is generic XML: each observation carries the item code, the
period ('2026M09') and the value. Item names come from the data structure's
code list, fetched once to check that each code still means what this feed
thinks it means.

Left out: processed and cooked goods, fish, beef/pork/veal cuts without a
catalogue twin, white cabbage (no catalogue product), sour cream, kefir,
"Curd cheese" (varškės sūris, a pressed curd cheese; plain varškė is used),
long greenhouse cucumbers (the short field cucumber is the market one),
"Fermented cheese" (cheese type unstated), and imported produce on the market
table.

    python feeds/stat_lt.py

Licence: Statistics Lithuania data are open, CC BY 4.0
(https://osp.stat.gov.lt/en/duomenu-naudojimo-salygos).
"""

import os
import re
import sys
import urllib.parse
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get

BASE = 'https://osp-rs.stat.gov.lt/rest_xml/'

RETAIL = {
    'flow': 'S7R244_M2021135_1', 'agency': 'LSD', 'dsd': 'M2021135_1', 'dim': 'Populiar_pr_kainos',
    'source': 'Statistics Lithuania, table S7R244', 'stage': 'retail',
    # (code, English label as published, catalogue name, unit, factor)
    'products': [
        ('01-1-4-8-1-00-00-02', 'Hen eggs, category M and L, 10 pcs', 'Eggs',            'dozen', 1.2),
        ('01-1-4-5-0-04-01-02', 'Curd, 5–9% fat, 200 g',              'Fresh Cottage Cheese', 'kg', 5.0),   # varškė
        ('01-1-2-2-4-01-00-03', 'Broiler chiken fillet, kg',          'Chicken Breast',  'kg',    1.0),
        ('01-1-2-2-4-01-00-01', 'Broiler chicken, kg',                'Whole Chicken',   'kg',    1.0),
        ('01-1-2-2-4-02-00-02', 'Turkey breast fillet, kg',           'Turkey Breast',   'kg',    1.0),
        ('01-1-2-2-2-00-00-08', 'Minced pork, kg',                    'Ground Pork',     'kg',    1.0),
        ('01-1-2-3-2-00-00-01', 'Hot-smoked pork loin without bone, kg', 'Smoked Pork',  'kg',    1.0),
        ('01-1-5-2-1-00-00-01', 'Butter, 82%, 200 g',                 'Butter',          'kg',    5.0),
        ('01-1-4-2-0-00-00-02', 'Pasteurised milk, 2.5% fat, l',      'Whole Milk',      'l',     1.0),
        ('01-1-6-3-1-00-00-02', 'Apples, up to 8 cm in diameter, kg', 'Apples',          'kg',    1.0),
        ('01-1-6-2-3-00-00-01', 'Oranges, kg',                        'Oranges',         'kg',    1.0),
        ('01-1-6-1-2-00-00-01', 'Bananas, kg',                        'Banana',          'kg',    1.0),
        ('01-1-6-2-2-00-00-01', 'Lemons, kg',                         'Lemons',          'kg',    1.0),
        ('01-1-6-5-1-00-00-02', 'Green grapes, kg',                   'Grapes Green',    'kg',    1.0),
        ('01-1-7-4-9-00-00-01', 'Beetroot, kg',                       'Beetroot',        'kg',    1.0),
        ('01-1-7-5-1-00-00-01', 'Potatoes, kg',                       'Potato',          'kg',    1.0),
        ('01-1-7-4-3-00-00-01', 'Onions, kg',                         'Onion',           'kg',    1.0),
        ('01-1-7-2-4-00-00-01', 'Tomatoes, kg',                       'Tomato',          'kg',    1.0),
        ('01-1-7-4-1-00-00-01', 'Carrots, kg',                        'Carrot',          'kg',    1.0),
        ('01-1-8-3-1-00-00-01', 'Natural honey, kg',                  'Honey',           'kg',    1.0),
    ],
}

MARKETS = {
    'flow': 'S7R307_M9100110', 'agency': 'ŽŪDC', 'dsd': 'M9100110', 'dim': 'M9100110',
    'source': "Statistics Lithuania, table S7R307 (markets)", 'stage': 'farmers_market',
    'products': [
        ('T01', 'Drinking milk, l',                          'Whole Milk',           'l',     1.0),
        ('T03', 'Butter, kg',                                'Butter',               'kg',    1.0),
        ('T04', 'Cottage cheese, kg',                        'Fresh Cottage Cheese', 'kg',    1.0),
        ('T07', 'Fresh pork lard, kg',                       'Pork Fatback',         'kg',    1.0),
        ('T15', 'Chicken, kg',                               'Whole Chicken',        'kg',    1.0),
        ('T17', 'Turkey, breast, kg',                        'Turkey Breast',        'kg',    1.0),
        ('T18', 'Chicken eggs, 10 pcs.',                     'Eggs',                 'dozen', 1.2),
        ('T27', 'Honey, kg',                                 'Honey',                'kg',    1.0),
        ('T28', 'Lithuanian potatoes, old harvest, kg',      'Potato',               'kg',    1.0),
        ('T30', 'Lithuanian potatoes, new harvest, kg',      'Potato',               'kg',    1.0),
        ('T32', 'Beetroot, kg',                              'Beetroot',             'kg',    1.0),
        ('T33', 'Lithuanian carrots, old harvest, kg',       'Carrot',               'kg',    1.0),
        ('T35', 'Lithuanian carrots, new harvest, kg',       'Carrot',               'kg',    1.0),
        ('T42', 'Lithuanian cauliflowers, kg',               'Cauliflower',          'kg',    1.0),
        ('T44', 'Lithuanian short cucumbers, kg',            'Cucumber',             'kg',    1.0),   # field type; long ones are greenhouse
        ('T48', 'Lithuanian tomatoes, kg',                   'Tomato',               'kg',    1.0),
        ('T50', 'Lithuanian onions, kg',                     'Onion',                'kg',    1.0),
        ('T52', 'Lithuanian garlic, kg',                     'Garlic',               'kg',    1.0),
        ('T54', 'Lithuanian apples, kg',                     'Apples',               'kg',    1.0),
    ],
}

OBS = re.compile(r'<g:Obs>(.*?)</g:Obs>', re.S)
KEY = re.compile(r'<g:Value id="([^"]+)" value="([^"]*)"')
VAL = re.compile(r'<g:ObsValue value="([^"]*)"')


def labels(xml, dim):
    """Code list of one dimension: {code: English label}."""
    m = re.search(r'<str:Codelist[^>]*id="%s".*?</str:Codelist>' % re.escape(dim), xml, re.S)
    out = {}
    for c in re.finditer(r'<str:Code[^>]*id="([^"]+)"[^>]*>(.*?)</str:Code>', m.group(0) if m else '', re.S):
        en = re.search(r'<com:Name xml:lang="en">(.*?)</com:Name>', c.group(2))
        if en:
            out[c.group(1)] = en.group(1).strip()
    return out


def observations(xml, dim):
    """{item code: [(date, value), ...]} from a generic SDMX data message."""
    out = {}
    for o in OBS.finditer(xml):
        key = dict(KEY.findall(o.group(1)))
        v = VAL.search(o.group(1))
        if dim not in key or not v or not v.group(1):
            continue
        try:
            value = float(v.group(1))
        except ValueError:
            continue
        if value != value or value <= 0:        # 'NaN': not collected that month
            continue
        y, m = key['LAIKOTARPIS'].split('M')
        out.setdefault(key[dim], []).append((date(int(y), int(m), 1), value))
    return out


def figures(table, data_xml, structure_xml):
    names = labels(structure_xml, table['dim'])
    obs = observations(data_xml, table['dim'])
    best = {}           # (catalogue name, unit) -> Figure: new and old harvest share a product; newest wins
    for code, label, name, unit, factor in table['products']:
        if names and names.get(code) != label:
            print(f'  {name}: {code} is now "{names.get(code)}", expected "{label}" — skipped', file=sys.stderr)
            continue
        if not obs.get(code):
            continue
        when, value = max(obs[code])
        f = Figure(name, round(value * factor, 4), unit, when)
        k = (name, unit)
        if k not in best or f.snapshot > best[k].snapshot:
            best[k] = f
    return list(best.values())


def fetch(table, start):
    agency = urllib.parse.quote(table['agency'])
    data = get(f"{BASE}data/{table['flow']}/?startPeriod={start}").decode('utf-8')
    structure = get(f"{BASE}datastructure/{agency}/{table['dsd']}?references=children").decode('utf-8')
    return data, structure


def run():
    today = date.today()
    start = f'{today.year - 1}-{today.month:02d}'
    total = 0
    for table in (RETAIL, MARKETS):
        figs = figures(table, *fetch(table, start))
        for f in figs:
            print(f'  {f.name:22} {f.price:>9.2f} EUR/{f.unit:5} {f.snapshot}')
        if figs:
            write('LT', table['source'], table['stage'], figs)
        total += len(figs)
    if not total:
        raise RuntimeError('Statistics Lithuania returned no prices — the tables or the API have changed')
    return total


if __name__ == '__main__':
    run()
