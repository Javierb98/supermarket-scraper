"""
Norway: shelf prices from Oda (oda.com), the national online grocer.

Oda's website searches its catalogue through a public JSON endpoint
(/api/v1/search/?q=…), no key and no login. One price list for the whole
country, so the figures are national. Kassalapp, which gathers every
Norwegian chain, is a paid API and so not used.

Oda's robots.txt sets three conditions for automated reading, all kept:
a User-Agent with "bot", a name and a contact (BOT_AGENT below); backing off
on 429 and 5xx, honouring Retry-After; and no `filter_` parameters. Nothing
else is disallowed for these paths.

Oda has no public category listing, so the catalogue is read by searching
for what farms sell: one Norwegian word per product (TERMS), at most two
pages of 40 each, a second and a half apart — some 150 requests and 4,000
products, a few minutes a week.

Mathem (mathem.se) runs on the same platform with the same rules, and
feeds/mathem.py reads Sweden from it with this code.

Each product is stored in the structured form pipeline/prices.py reads:

    item       what one pack costs (gross_price)
    per_kg / per_l / per_unit
               Oda's own unit price, by its unit (kg, l, stk/st)
    per_dozen  eggs, from the pack count
    regular    the price before a discount, when there is one

then matched by pipeline/rules_no.py and averaged, in this same run.

    python feeds/oda.py
"""

import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection, ensure_raw_schema, save_raw

BOT_AGENT = 'Evocultiva-price-bot/1.0 (+https://evocultiva.org; price comparison for small farms)'
PAUSE = 1.5
MAX_PAGES = 2
PER_PAGE = 40   # what the endpoint returns; it takes no size parameter

NO_TERMS = [
    # vegetables
    'tomater', 'cherrytomater', 'agurk', 'paprika', 'chili', 'løk', 'rødløk', 'vårløk', 'sjalottløk',
    'hvitløk', 'purreløk', 'poteter', 'søtpotet', 'gulrøtter', 'rødbeter', 'blomkål', 'brokkoli',
    'rosenkål', 'kål', 'grønnkål', 'selleri', 'pastinakk', 'fennikel', 'squash', 'gresskar',
    'aubergine', 'asparges', 'spinat', 'ruccola', 'salat', 'reddik', 'sjampinjong', 'sopp', 'bønner',
    'sukkererter', 'maiskolbe', 'ingefær', 'jordskokk',
    # fruit and berries
    'epler', 'pærer', 'bananer', 'appelsiner', 'klementiner', 'mandariner', 'sitroner', 'lime', 'druer',
    'jordbær', 'bringebær', 'blåbær', 'bjørnebær', 'rips', 'solbær', 'kirsebær', 'plommer', 'fersken',
    'kiwi', 'mango', 'avokado', 'ananas', 'melon', 'vannmelon', 'granateple', 'fiken', 'pasjonsfrukt',
    'kaki',
    # eggs and dairy
    'egg', 'melk', 'fløte', 'smør', 'ost', 'kremost', 'cottage cheese', 'mozzarella', 'feta', 'brie',
    'parmesan', 'cheddar',
    # meat
    'kjøttdeig', 'kylling', 'kyllingfilet', 'kyllinglår', 'kyllingvinger', 'kalkun', 'andebryst',
    'lam', 'svinekjøtt', 'kotelett', 'ribbe', 'svinebog', 'biff', 'entrecote', 'indrefilet',
    'ytrefilet', 'storfe', 'reinsdyr', 'elg', 'hjort',
]

SE_TERMS = [
    # vegetables
    'tomat', 'körsbärstomater', 'gurka', 'paprika', 'chili', 'lök', 'rödlök', 'salladslök', 'schalottenlök',
    'vitlök', 'purjolök', 'potatis', 'sötpotatis', 'morötter', 'rödbetor', 'blomkål', 'broccoli',
    'brysselkål', 'kål', 'grönkål', 'selleri', 'palsternacka', 'fänkål', 'zucchini', 'pumpa',
    'aubergine', 'sparris', 'spenat', 'rucola', 'sallad', 'rädisor', 'champinjoner', 'svamp', 'bönor',
    'sockerärtor', 'majskolv', 'ingefära', 'jordärtskocka', 'kålrabbi',
    # fruit and berries
    'äpplen', 'päron', 'bananer', 'apelsiner', 'clementiner', 'mandariner', 'citroner', 'lime',
    'vindruvor', 'jordgubbar', 'hallon', 'blåbär', 'björnbär', 'vinbär', 'körsbär', 'plommon',
    'persikor', 'kiwi', 'mango', 'avokado', 'ananas', 'melon', 'vattenmelon', 'granatäpple', 'fikon',
    'passionsfrukt', 'kaki',
    # eggs and dairy
    'ägg', 'mjölk', 'grädde', 'smör', 'ost', 'färskost', 'keso', 'mozzarella', 'fetaost', 'brie',
    'parmesan', 'cheddar', 'getost', 'ädelost',
    # meat
    'nötfärs', 'fläskfärs', 'kyckling', 'kycklingfilé', 'kycklinglår', 'kycklingvingar', 'kalkon',
    'ankbröst', 'lamm', 'fläskkött', 'kotlett', 'sidfläsk', 'revbensspjäll', 'entrecote', 'oxfilé',
    'ryggbiff', 'högrev', 'nötkött', 'älg', 'vilt',
]

SITES = {
    'NO': {'chain': 'Oda', 'store': 'Oda (oda.com)', 'base': 'https://oda.com', 'terms': NO_TERMS,
           'eggs': re.compile(r'\begg\b|frokostegg|solegg|gårdsegg', re.I)},
    'SE': {'chain': 'Mathem', 'store': 'Mathem (mathem.se)', 'base': 'https://www.mathem.se', 'terms': SE_TERMS,
           'eggs': re.compile(r'\bägg\b', re.I)},
}

UNIT = {'kg': 'kg', 'l': 'l', 'stk': 'unit', 'st': 'unit'}
COUNT = re.compile(r'(\d+)\s*(?:stk|st|pk|-pack|p)\b', re.I)


def fetch(url, tries=5):
    """One request, the way Oda asks: identified, backing off on 429 and 5xx."""
    wait = 5
    for attempt in range(tries):
        req = urllib.request.Request(url, headers={'User-Agent': BOT_AGENT, 'Accept': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.load(r)
            time.sleep(PAUSE)
            return body
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504) or attempt == tries - 1:
                raise
            retry = e.headers.get('Retry-After')
            delay = int(retry) if retry and retry.isdigit() else wait
            time.sleep(min(delay, 300))
            wait *= 2
        except urllib.error.URLError:
            if attempt == tries - 1:
                raise
            time.sleep(wait)
            wait *= 2


def search(base, term):
    """Up to MAX_PAGES pages of results for one word."""
    out = []
    for page in range(1, MAX_PAGES + 1):
        q = urllib.parse.urlencode({'q': term, 'page': page} if page > 1 else {'q': term})
        d = fetch(f'{base}/api/v1/search/?{q}')
        products = d.get('products') or []
        out.extend(products)
        total = (d.get('attributes') or {}).get('total_hits') or 0
        if not products or page * PER_PAGE >= total:
            break
    return out


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def structured(p, eggs_rx):
    """An Oda product → 'item=…;per_kg=…;regular=…', or None without a price."""
    item = _num(p.get('gross_price'))
    if not item or item <= 0:
        return None
    fields = {'item': round(item, 2)}
    name = f"{p.get('name') or ''} {p.get('name_extra') or ''}"

    unit = UNIT.get((p.get('unit_price_quantity_abbreviation') or '').lower())
    per = _num(p.get('gross_unit_price'))
    if eggs_rx.search(name):
        count = COUNT.search(p.get('name_extra') or '') or COUNT.search(p.get('name') or '')
        if unit == 'unit' and per:
            fields['per_dozen'] = round(per * 12, 4)
        elif count and int(count.group(1)) > 0:
            fields['per_dozen'] = round(item / int(count.group(1)) * 12, 4)
    elif unit and per and per > 0:
        fields['per_' + unit] = round(per, 4)

    disc = p.get('discount') or {}
    regular = _num(disc.get('undiscounted_gross_price')) if disc.get('is_discounted') else None
    if regular and regular > item + 0.004:
        fields['regular'] = round(regular, 2)
    return ';'.join(f'{k}={v}' for k, v in fields.items())


def run(country='NO'):
    site = SITES[country]
    conn = get_connection()
    saved = 0
    seen = set()
    try:
        ensure_raw_schema(conn)
        for term in site['terms']:
            kept = 0
            for p in search(site['base'], term):
                if p.get('id') in seen:
                    continue
                seen.add(p.get('id'))
                price = structured(p, site['eggs'])
                if price is None:
                    continue
                # The brand is left out: the product leads the name, which the
                # matcher needs ("Prior Frokostegg" → "Frokostegg …").
                name = (p.get('name') or '').strip()
                extra = (p.get('name_extra') or '').strip()
                raw_name = f'{name}, {extra}' if extra else name
                save_raw(conn, chain=site['chain'], store_name=site['store'], postal_code='', city=None,
                         region=None, category=term, raw_name=raw_name, raw_price=price, raw_unit_price=None,
                         url=p.get('front_url') or (site['base'] + (p.get('absolute_url') or '')),
                         country=country)
                kept += 1
            conn.commit()
            saved += kept
            print(f'  {term:20} {kept:4} new products')
    finally:
        conn.close()

    print(f"{site['chain']}: {saved} shelf prices stored ({country})")
    if saved == 0:
        raise RuntimeError(f"{site['chain']} returned nothing — the search API has changed or blocks us")
    return saved


def finish(country):
    """Match and average this country's new rows now, not a week from now."""
    from pipeline import normalize, market_average
    normalize.run(country)
    market_average.run(country)


if __name__ == '__main__':
    run('NO')
    if '--no-average' not in sys.argv:
        finish('NO')
