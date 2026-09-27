"""
United States: retail food prices from USDA Market News.

A feed, not a scrape. Walmart answers 418 behind an Akamai wall and Kroger
wants a key, but the USDA surveys more than 270 retailers across some 29,000
stores every week and publishes the result — by region, which is what the
site needs and what no American chain will hand over.

Authentication is an API key used as the username of an HTTP Basic pair, with
an empty password. It is free on registration at mymarketnews.ams.usda.gov
and lives in .env as USDA_API_KEY.

Run it with no arguments to load prices. Run it with `explore` to print what
the API actually returns without writing anything:

    python feeds/usda.py explore

That mode exists because the shape of these reports is documented loosely and
guessing at it is how you end up storing nonsense. Look first, then map.
"""

import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
except ImportError:
    pass

BASE = 'https://marsapi.ams.usda.gov/services/v1.2'
SOURCE_NAME = 'USDA Market News'

# The weekly advertised retail prices for fruit and vegetables, broken out by
# region. This is the report the whole feed exists for.
RETAIL_SLUG = 'FVWRETAIL'


def api_key():
    key = (os.getenv('USDA_API_KEY') or '').strip()

    if not key or key == 'your_usda_key_here':
        raise SystemExit(
            'USDA_API_KEY is not set. Put it in .env — it is free from\n'
            'mymarketnews.ams.usda.gov and is used as the username of an\n'
            'HTTP Basic pair with an empty password.'
        )

    return key


def get(path, params=None):
    url = f'{BASE}/{path.lstrip("/")}'

    if params:
        import urllib.parse
        url += '?' + urllib.parse.urlencode(params)

    # Basic auth with the key as the username and nothing as the password.
    token = base64.b64encode(f'{api_key()}:'.encode()).decode()
    req = urllib.request.Request(url, headers={
        'Authorization': f'Basic {token}',
        'Accept': 'application/json',
    })

    try:
        with urllib.request.urlopen(req, timeout=40) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        body = e.read().decode(errors='replace')[:300]
        raise SystemExit(f'USDA {e.code} for {path}: {body}')


def explore():
    """Print the shape of what comes back. Writes nothing."""
    print('=== the report list, filtered to retail ===')
    reports = get('reports')
    rows = reports if isinstance(reports, list) else reports.get('results', [])
    print(f'{len(rows)} reports available')

    for r in rows:
        name = str(r.get('report_name') or r.get('reportName') or '')
        slug = r.get('slug_id') or r.get('slugId') or ''
        if 'retail' in name.lower():
            print(f'   {slug:12} {name[:70]}')

    print(f'\n=== {RETAIL_SLUG}: one page of rows ===')
    data = get(f'reports/{RETAIL_SLUG}', {'q': 'report_begin_date=>01/01/2026'})
    rows = data.get('results', data if isinstance(data, list) else [])
    print(f'{len(rows)} rows')

    if rows:
        print('\ncolumns:')
        for k, v in list(rows[0].items()):
            print(f'   {k:32} {str(v)[:50]}')
        print('\nfirst three rows:')
        for row in rows[:3]:
            print('  ', json.dumps(row, ensure_ascii=False)[:220])


def run():
    """
    Deliberately not written until explore() has been run against a real key.

    Every other feed here was built by looking at the payload first —
    Statistics Canada's coordinates, Consum's price fields, DEFRA's columns.
    Writing a mapping for a shape nobody has seen is how a feed silently
    stores the wrong column for a year.
    """
    raise SystemExit(
        'Run `python feeds/usda.py explore` first and map the columns from\n'
        'what it prints. The report is FVWRETAIL; what is needed is the\n'
        'commodity, the region, the price, the unit and the week.'
    )


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'explore':
        explore()
    else:
        run()
