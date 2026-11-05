"""
Estonia: what dairy farmers are paid for milk, from Statistics Estonia,
table PM18 "Purchase of milk (monthly)", indicator AVP (average price of
milk, euros per tonne).

Official statistics through the PxWeb API at andmed.stat.ee, no key. It is
the only food price Statistics Estonia still publishes as a price: its
average consumer prices of foodstuffs (LE13) stopped in 2007, and the rest
are indices. Estonian shelf prices come from Selver (feeds/selver.py).

A purchase price is what the dairy pays the producer, so the figure is
`farmgate`: shown to the farmer, labelled, never used for badges.

    € per tonne ÷ 1000 × 1.03 → € per litre (a litre of milk weighs 1.03 kg)

    python feeds/stat_ee_milk.py
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get_json

API = ('https://andmed.stat.ee/api/v1/en/stat/majandus/pellumajandus/pellumajandussaaduste-tootmine/'
       'loomakasvatussaaduste-tootmine/PM18.PX')
SOURCE_NAME = 'Statistics Estonia, table PM18 (purchase of milk)'
MILK_KG_PER_LITRE = 1.03


def run():
    meta = get_json(API)
    codes = {v['code']: v for v in meta['variables']}
    indicator = next(c for c in codes if c.lower().startswith('n'))       # Näitaja
    period = next(c for c in codes if c != indicator)                      # Vaatlusperiood
    query = {
        'query': [
            {'code': indicator, 'selection': {'filter': 'item', 'values': ['AVP']}},
            # The newest three months by name: "top" is not reliable on this server.
            {'code': period, 'selection': {'filter': 'item', 'values': sorted(codes[period]['values'])[-3:]}},
        ],
        'response': {'format': 'json-stat2'},
    }
    d = get_json(API, data=query)
    cat = d['dimension'][period]['category']
    by_pos = {v: k for k, v in cat['index'].items()}             # position → '2026M09'
    figures = []
    for j in sorted(by_pos, key=lambda j: by_pos[j], reverse=True):
        v = d['value'][j]
        if v is None:
            continue
        ref = by_pos[j]                                                    # '2026M09'
        per_litre = float(v) / 1000 * MILK_KG_PER_LITRE
        figures.append(Figure('Raw Cow Milk', round(per_litre, 4), 'l', date(int(ref[:4]), int(ref[5:7]), 1)))
        print(f'  Raw Cow Milk {float(v):8.2f} €/t → {per_litre:.4f} €/l  {ref}')
        break

    if not figures:
        raise RuntimeError('Statistics Estonia returned no milk price — the table has changed')
    return write('EE', SOURCE_NAME, 'farmgate', figures)


if __name__ == '__main__':
    run()
