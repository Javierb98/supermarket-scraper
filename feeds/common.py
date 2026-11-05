"""
What every feed shares: writing its figures, and fetching politely.

A feed (an official statistic, a published price list, a third-party price
collection) works out its own figures and hands them to write(). write()
checks each against the website's catalogue, labels it with the feed's price
stage, currency and source, and stores it. A figure for a product the
catalogue does not have is reported, not stored: the site could never show it.

    figures = [Figure('Tomato', 2.31, 'kg', date(2026, 10, 1)), ...]
    write('CH', 'BLW consumer prices', 'retail', figures)

Each feed is runnable on its own (python feeds/<name>.py) and is listed in
feeds/registry.py so the weekly run picks it up.
"""

import json
import os
import sys
import time
import urllib.request
from dataclasses import dataclass
from datetime import date
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection, ensure_market_average_schema
from pipeline.catalog import products
from pipeline.countries import currency as currency_of

STAGES = ('retail', 'wholesale', 'farmers_market', 'farmgate')
UNITS = ('kg', 'l', 'dozen', 'unit')

USER_AGENT = 'Evocultiva-price-feed/1.0 (+https://evocultiva.org)'


@dataclass
class Figure:
    name: str                       # catalogue English name, exactly
    price: float                    # in the country's currency, per `unit`
    unit: str                       # kg | l | dozen | unit
    snapshot: date                  # the period the price is for (first of the month for monthly data)
    region: Optional[str] = None    # None = the whole country
    low: Optional[float] = None
    high: Optional[float] = None
    samples: int = 0                # 0 for an official average, which gives no count


UPSERT = """
INSERT INTO market_average
    (catalog_product_id, canonical_name, category, country, region, source, source_name,
     price_stage, currency, snapshot_date, avg_price, min_price, max_price, standard_unit, sample_count)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
ON DUPLICATE KEY UPDATE
    catalog_product_id = VALUES(catalog_product_id), category = VALUES(category),
    source = VALUES(source), source_name = VALUES(source_name), currency = VALUES(currency),
    avg_price = VALUES(avg_price), min_price = VALUES(min_price), max_price = VALUES(max_price),
    sample_count = VALUES(sample_count)
"""


def national_from_regions(figures, within_days=14):
    """
    A country figure from per-market ones, where a source gives no other.

    France's and Germany's wholesale prices are quoted per market (Rungis,
    Hamburg…), Romania's market-stall prices per county. The website compares
    most farms with a national figure, so without one these would never be
    shown. It is the median of each market's latest price, low and high are
    the cheapest and dearest market, and samples is the number of markets.
    """
    from statistics import median
    have_national = {(f.name, f.unit) for f in figures if f.region is None}
    latest = {}
    for f in figures:
        if f.region is None or (f.name, f.unit) in have_national:
            continue
        key = (f.name, f.unit, f.region)
        if key not in latest or f.snapshot > latest[key].snapshot:
            latest[key] = f
    groups = {}
    for (name, unit, _), f in latest.items():
        groups.setdefault((name, unit), []).append(f)
    out = []
    for (name, unit), fs in groups.items():
        newest = max(f.snapshot for f in fs)
        fs = [f for f in fs if (newest - f.snapshot).days <= within_days]
        prices = [f.price for f in fs]
        out.append(Figure(name, median(prices), unit, newest, None, min(prices), max(prices), len(prices)))
    return out


def write(country, source_name, stage, figures, source='official', currency=None):
    """Store figures; return (written, refused names)."""
    assert stage in STAGES, stage
    figures = list(figures)
    if stage != 'retail':
        figures += national_from_regions(figures)
    country = country.upper()
    currency = currency or currency_of(country)
    catalog = products()
    rows, refused = [], set()
    for f in figures:
        p = catalog.get(f.name.lower())
        if p is None:
            refused.add(f.name)
            continue
        if f.unit not in UNITS or f.price is None or f.price != f.price or f.price <= 0:
            refused.add(f'{f.name} ({f.unit}, {f.price})')
            continue
        rows.append((
            p['id'], p['name'], p['category'], country, f.region, source, source_name[:120],
            stage, currency, f.snapshot, round(f.price, 4),
            round(f.low if f.low is not None else f.price, 4), round(f.high if f.high is not None else f.price, 4),
            f.unit, f.samples,
        ))

    conn = get_connection()
    try:
        ensure_market_average_schema(conn)
        with conn.cursor() as c:
            c.executemany(UPSERT, rows)
        conn.commit()
    finally:
        conn.close()

    print(f'{country} {source_name}: {len(rows)} figures written ({stage}, {currency})')
    if refused:
        print(f'  not in the catalogue, so not stored: {", ".join(sorted(refused))}')
    return len(rows), refused


def get(url, data=None, headers=None, retries=3, timeout=60, pause=1.0):
    """One polite HTTP request: identified, retried with backoff, then a pause."""
    h = {'User-Agent': USER_AGENT, 'Accept': '*/*'}
    h.update(headers or {})
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, data=data, headers=h)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read()
            time.sleep(pause)
            return body
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))


def get_json(url, data=None, headers=None, **kw):
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode()
        headers = dict(headers or {}, **{'Content-Type': 'application/json'})
    return json.loads(get(url, data=data, headers=dict(headers or {}, Accept='application/json'), **kw))
