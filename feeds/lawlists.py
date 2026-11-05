"""
What the feeds reading legally published price lists share (Croatia, Serbia,
Greece): downloading big files without holding them in memory, turning a
list's price into the structured form the pipeline reads, and storing the
products as shop rows that then go through normalise and average like any
scraped shop.

Not a feed itself, so not in feeds/registry.py.

Why shop rows and not ready-made averages (common.write): these lists are
shelf prices of named products, and the pipeline already knows how to judge
a shelf name (fresh or processed, which catalogue product) and how to
average fairly (one sample per distinct product, offers at their regular
price). Only the products the rules match are stored — a Croatian archive
has 300,000 products a day, nearly all of them not food a farm sells.
"""

import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
from statistics import median

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import USER_AGENT, TLS
from utils.db import get_connection, ensure_raw_schema, save_raw
from pipeline.matcher import Matcher, detect_state, check_fresh
from pipeline.pack import from_name

FRESH_PIECES = ('vegetables', 'fruit', 'h/s')
APPROX = re.compile(r'\bc?ca\.?\s*\d', re.I)
PIECE_WORD = re.compile(r'\bkomad\b|\bkom\b\.?(?!\s*\d)|\bкомад\b|\bτεμ', re.I)


def download(url, suffix='', retries=3, timeout=120):
    """Stream url to a temporary file; return its path (the caller deletes it)."""
    for attempt in range(retries):
        fd, path = tempfile.mkstemp(prefix='lawlist-', suffix=suffix)
        try:
            req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT, 'Accept': '*/*'})
            with urllib.request.urlopen(req, timeout=timeout, context=TLS) as r, os.fdopen(fd, 'wb') as f:
                shutil.copyfileobj(r, f, 1 << 20)
            time.sleep(1.0)
            return path
        except Exception:
            try:
                os.remove(path)
            except OSError:
                pass
            if attempt == retries - 1:
                raise
            time.sleep(2 ** (attempt + 1))


def num(s):
    """'1,29' / '1.29' / '1.234,50' → float, or None."""
    s = (s or '').strip().replace(' ', '')
    if not s:
        return None
    if ',' in s and '.' in s:
        s = s.replace('.', '').replace(',', '.') if s.rfind(',') > s.rfind('.') else s.replace(',', '')
    else:
        s = s.replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


# How many eggs: "10/1", "30 komada", "6 kom", "10 ком", "6τμχ", "6 Τεμάχια", "6x 53-63gr".
EGG_COUNT = re.compile(
    r'(\d{1,2})\s*(?:/\s*1\b|kom|ком|ko\b|τεμ|τμχ|pcs|x\s*\d{2}\s*-|\s*jaja|\s*јаја|\s*αυγ)', re.I)
DOZEN_SIZES = {4, 6, 8, 10, 12, 15, 18, 20, 24, 30}


def egg_count(*texts):
    for t in texts:
        for m in EGG_COUNT.finditer(t or ''):
            n = int(m.group(1))
            if n in DOZEN_SIZES:
                return n
    return None


def structured(item, per=None, regular=None):
    """item and per-unit prices → 'item=2.49;per_kg=4.98;regular=2.99'."""
    parts = ['item=%.4f' % item]
    for k, v in (per or {}).items():
        if v and v > 0:
            parts.append('per_%s=%.4f' % (k, v))
    if regular and regular > item:
        parts.append('regular=%.4f' % regular)
    return ';'.join(parts)


class Judge:
    """Which shelf names are worth storing: those a rule maps to a fresh
    catalogue product (the same test normalise applies later)."""

    def __init__(self, lang):
        self.lang = lang
        self.matcher = Matcher()

    def product(self, name):
        p, how, _ = self.matcher.match(name, self.lang)
        if not p or how not in ('rule', 'catalog'):
            return None
        state = detect_state(name, self.lang)
        if check_fresh(p, name, self.lang, state):
            return None
        return p


def per_basis(product, name, price, sold_by_kg=False, sold_by_l=False, piece=False, unit_count=None, size_text=''):
    """
    The per-unit prices one shelf price gives, as the structured reader
    wants them. The pack size in the name is used by the reader itself
    ("2 kg", "500 g", "1 l"), so it is only filled in here when the name does
    not say: a product weighed at the till ("RAJČICA", unit kg), eggs by
    the count, a piece of fruit.
    """
    per = {}
    pack = from_name(name)
    named_size = bool(pack and (pack.kg or pack.litres))
    if product['category'] == 'eggs':
        n = unit_count or egg_count(name)
        if n:
            per['dozen'] = price / n * 12
        return per
    # "cca 1,78 kg", "ca. 500g": the weight of a piece priced by the kilo,
    # when the list says it is sold by the kilo.
    if named_size and sold_by_kg and APPROX.search(name):
        named_size = False
    if named_size:
        return per
    # The list's own size column ("500g", "1kg") when the name has none.
    size = from_name(size_text) if size_text else None
    if size and size.kg:
        per['kg'] = price / size.kg
    elif size and size.litres:
        per['l'] = price / size.litres
    elif PIECE_WORD.search(name) and product['category'] in FRESH_PIECES:
        # "Paprika ljuta komad": a piece, whatever the unit column says.
        per['unit'] = price
    elif sold_by_kg:
        per['kg'] = price
    elif sold_by_l:
        per['l'] = price
    elif piece and product['category'] in FRESH_PIECES:
        per['unit'] = price
    return per


def sane(per, low=0.05, high=300):
    """Leave out per-unit prices no shelf product has (bad unit data). The
    bounds are in the country's currency: euro by default."""
    return all(low <= v <= high for v in per.values())


def store(country, rows, url):
    """rows: dicts with chain, raw_name, raw_price, stores (count), shop_category, region."""
    conn = get_connection()
    try:
        ensure_raw_schema(conn)
        for r in rows:
            save_raw(conn, r['chain'], '%s (%d stores)' % (r['chain'], r['stores']) if r.get('stores') else r['chain'],
                     r.get('postal_code', ''), None, r.get('region'), None, r['raw_name'][:500], r['raw_price'], None,
                     url[:500], shop_category=r.get('shop_category'), country=country)
        conn.commit()
    finally:
        conn.close()
    print('%s: %d shop products stored' % (country, len(rows)))


def run_pipeline(country):
    """Normalise and average this country's new rows (the weekly run does
    those steps before the feeds, so a feed that stores shop rows does them
    itself)."""
    from pipeline import normalize, market_average
    normalize.run(country)
    market_average.run(country)


def mid(values):
    return round(median(values), 4)
