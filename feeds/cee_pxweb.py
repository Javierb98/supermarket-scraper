"""
Reading a PxWeb table (the API most Central and Eastern European statistics
offices publish through): Latvia's CSB and Slovenia's SURS here.

Not a feed itself, so it is not in registry.py. It asks for a table in
JSON-stat 2 and hands back one plain row per cell, so a feed only has to say
which items it wants and what they are called in the catalogue.

    rows = query(URL, [{'code': 'TIME', 'selection': {'filter': 'top', 'values': ['3']}}])
    rows[0] == {'GOODS_SERVICES': ('01.1.7.2.4.104', 'Tomatoes, 1 kg'),
                'TIME': ('2026M09', '2026M09'), 'value': 2.77}
"""

import itertools
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import get_json


def query(url, selections):
    """POST a PxWeb query; one dict per cell, dimension code -> (value code, label), plus 'value'."""
    payload = {'query': selections, 'response': {'format': 'json-stat2'}}
    return cells(get_json(url, data=payload))


def cells(stat):
    """A JSON-stat 2 dataset as rows (missing cells come back with value None)."""
    dims = []
    for dim_id in stat['id']:
        cat = stat['dimension'][dim_id]['category']
        codes = sorted(cat['index'], key=lambda k: cat['index'][k]) if isinstance(cat['index'], dict) else cat['index']
        dims.append((dim_id, [(c, cat.get('label', {}).get(c, c)) for c in codes]))

    values = stat['value']
    if isinstance(values, dict):            # the sparse form: {"12": 3.4, ...}
        values = {int(k): v for k, v in values.items()}
        get = values.get
    else:
        get = lambda i: values[i] if i < len(values) else None

    rows = []
    for i, combo in enumerate(itertools.product(*[d[1] for d in dims])):
        row = {dim_id: pair for (dim_id, _), pair in zip(dims, combo)}
        row['value'] = get(i)
        rows.append(row)
    return rows


def month(code):
    """'2026M09' -> date(2026, 9, 1)."""
    y, m = code.upper().split('M')
    return date(int(y), int(m), 1)


def latest(rows, item_dim, time_dim, parse_time):
    """Per item, its most recent non-empty cell: {item code: (snapshot date, value)}."""
    out = {}
    for r in rows:
        v = r['value']
        if v is None:
            continue
        code = r[item_dim][0]
        when = parse_time(r[time_dim][0])
        if code not in out or when > out[code][0]:
            out[code] = (when, float(v))
    return out
