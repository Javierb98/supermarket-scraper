"""
Italy: ISMEA Mercati weekly average prices, at origin (farm-gate) and wholesale.

ISMEA (Istituto di Servizi per il Mercato Agricolo Alimentare, part of the
Ministry of Agriculture) runs a national network that records prices on the
most representative origin markets every week, and publishes the national
weekly averages per product and variety as plain HTML tables on
ismeamercati.it. No key, no login.

What is used, and why:

  origin ("prezzi medi all'origine")  -> stage 'farmgate'
      fruit, vegetables, citrus, eggs, dairy, sheep's-milk cheese, olive oil,
      honey: what the producer (or, for cheese, the dairy) is paid, VAT
      excluded (honey VAT included).
  wholesale ("prezzi medi all'ingrosso") -> stage 'wholesale'
      poultry meat and pork cuts. The origin prices for livestock are per kilo
      of live animal, which no farm's price list could be compared with, so
      they are not used; the wholesale carcass/cut prices are.

Several ISMEA varieties can be the same catalogue product (Fuji, Gala and
Golden are all "Apples"): their prices are averaged, and the lowest and
highest kept as the range. A variety that is not the same thing as any
catalogue product (nectarines, Iceberg lettuce, Grana Padano) is not used.
Nuts are left out on purpose: ISMEA quotes them in shell, and a farm selling
shelled almonds would look five times dearer than "the market".

ISMEA weeks are written "2026-10-5": the fifth week of October. The snapshot
is the first of the month plus seven days per week, so "2026-10-5" is
29 October 2026 — close enough to sort weeks correctly and to age them.

Everything is national (region None). San Marino has no figures of its own,
so the same figures are also stored for SM, labelled as Italian.

Terms: ismeamercati.it "Note legali" — material is ISMEA's, protected by
copyright unless stated otherwise. We use the published figures (facts) with
ISMEA named as the source; see SOURCES.md.

    python feeds/ismea.py
"""

import html
import os
import re
import sys
from collections import defaultdict
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, get, write  # noqa: E402

BASE = 'https://www.ismeamercati.it/flex/cm/pages/ServeBLOB.php/L/IT/IDPagina/'
SOURCE_ORIGIN = 'ISMEA Mercati, prezzi medi all\'origine'
SOURCE_WHOLESALE = 'ISMEA Mercati, prezzi medi all\'ingrosso'
BORROWERS = ['SM']          # countries that show Italy's figures, labelled as such
MAX_AGE_DAYS = 120          # an older quote (a product out of season) is not a current price

# Weekly averages per variety, by page.
ORIGIN_PAGES = {
    507: 'vegetables',
    559: 'fruit',
    591: 'citrus',
    790: 'poultry and eggs',
    685: 'cow\'s milk products',
    3073: 'sheep and goat milk products',
    652: 'olive oil',
    11023: 'honey',
}
WHOLESALE_PAGES = {
    794: 'poultry meat',
    759: 'pork',
}

# ISMEA "Product - variety" (lower case, prefix match on the whole label) →
# (catalogue name, unit, factor). The price is multiplied by factor:
#   eggs are quoted per 100 → ×0.12 per dozen;
#   olive oil per kg → ×0.916 per litre (density of olive oil).
# Order matters: the first prefix that matches wins.
ORIGIN_MAP = [
    ('agli', 'Garlic', 'kg', 1),
    ('carciofi', 'Artichoke', 'unit', 1),          # €/capolino: per head
    ('carote', 'Carrot', 'kg', 1),
    ('cavolfiori', 'Cauliflower', 'kg', 1),
    ('cavoli broccoli - verde tipo romanesco', 'Romanesco', 'kg', 1),
    ('cavoli broccoli', 'Broccoli', 'kg', 1),
    ('cavolo verza', 'Savoy Cabbage', 'kg', 1),
    ('cetrioli', 'Cucumber', 'kg', 1),
    ('cipolle - tonde bianche', 'White Onion', 'kg', 1),
    ('cipolle - tonde rosse', 'Red Onion', 'kg', 1),
    ('cipolle', 'Onion', 'kg', 1),
    ('fagiolini', 'Green Beans', 'kg', 1),
    ('finocchi', 'Fennel', 'kg', 1),
    ('indivia', 'Endive', 'kg', 1),
    ('lattuga - romana', 'Romaine Lettuce', 'kg', 1),
    ('melanzane', 'Eggplant', 'kg', 1),
    ('patate comuni', 'Potato', 'kg', 1),
    ('peperoni - colorati', 'Bell Pepper', 'kg', 1),
    ('peperoni serra - colorati', 'Bell Pepper', 'kg', 1),
    ('pomodori - ciliegini', 'Cherry Tomato', 'kg', 1),
    ('pomodori serra - ciliegini', 'Cherry Tomato', 'kg', 1),
    ('pomodori - cuore di bue', 'Beefsteak Tomatoes', 'kg', 1),
    ('pomodori - lunghi verdi', 'Green Tomatoes', 'kg', 1),
    ('pomodori - tipo s.marzano', 'Plum Tomatoes', 'kg', 1),
    ('pomodori serra - tondi lisci rossi a grappolo', 'Vine Tomatoes', 'kg', 1),
    ('pomodori - tondo liscio', 'Tomato', 'kg', 1),
    ('pomodori serra - tondi lisci', 'Tomato', 'kg', 1),
    ('pomodori - costoluti', 'Tomato', 'kg', 1),
    ('radicchio', 'Radicchio', 'kg', 1),
    ('ravanelli', 'Radish', 'kg', 1),
    ('sedani', 'Celery', 'kg', 1),
    ('spinaci', 'Spinach', 'kg', 1),
    ('zucchine', 'Zucchini', 'kg', 1),
    ('bieta', 'Swiss Chard', 'kg', 1),
    ('asparagi', 'Asparagus', 'kg', 1),
    ('fave', 'Broad Beans Fresh', 'kg', 1),
    ('piselli', 'Green Peas', 'kg', 1),
    ('patate novelle', 'Potato', 'kg', 1),
    # fruit
    ('fragole', 'Strawberries', 'kg', 1),
    ('kiwi', 'Kiwi', 'kg', 1),
    ('loti', 'Persimmon', 'kg', 1),
    ('mele - cripps pink', 'Pink Lady Apples', 'kg', 1),
    ('mele', 'Apples', 'kg', 1),
    ('pere', 'Pears', 'kg', 1),
    ('pesche', 'Peaches', 'kg', 1),
    ('uva da tavola - crimson', 'Red Grapes Seedless', 'kg', 1),
    ('uva da tavola - red globe', 'Grapes Red', 'kg', 1),
    ('uva da tavola - italia', 'Grapes Green', 'kg', 1),
    ('uva da tavola - victoria', 'Grapes Green', 'kg', 1),
    ('ciliegie', 'Cherries', 'kg', 1),
    ('susine', 'Plums', 'kg', 1),
    ('fichi', 'Fig', 'kg', 1),
    ('castagne', 'Chestnuts', 'kg', 1),
    ('mirtilli', 'Blueberries', 'kg', 1),
    ('lamponi', 'Raspberry', 'kg', 1),
    # citrus
    ('arance - tarocco', 'Blood Oranges', 'kg', 1),
    ('arance - moro', 'Blood Oranges', 'kg', 1),
    ('arance - sanguinello', 'Blood Oranges', 'kg', 1),
    ('arance', 'Oranges', 'kg', 1),
    ('clementine', 'Clementine', 'kg', 1),
    ('limoni', 'Lemons', 'kg', 1),
    ('satsuma', 'Mandarin Oranges Fresh', 'kg', 1),
    ('mandarini', 'Mandarin Oranges Fresh', 'kg', 1),
    # eggs: free-range ("all'aperto") is what a farm's eggs compare with
    ("uova da allevamento all'aperto", 'Eggs', 'dozen', 0.12),
    # dairy (the dairy's selling price at origin)
    ('parmigiano reggiano - stagionato 12', 'Parmesan', 'kg', 1),
    ('parmigiano reggiano - stagionato 24', 'Aged Parmesan', 'kg', 1),
    ('mozzarella', 'Mozzarella', 'kg', 1),
    ('gorgonzola', 'Blue Cheese', 'kg', 1),
    ('provolone', 'Provolone', 'kg', 1),
    ('mascarpone', 'Mascarpone', 'kg', 1),
    ('ricotta', 'Ricotta', 'kg', 1),
    ('pecorino romano dop - destinazione italia', 'Sheep Cheese', 'kg', 1),
    # olive oil, bulk at the mill; honey, ex-farm
    ('olio extravergine di oliva', 'Olive Oil', 'l', 0.916),
    ('miele', 'Honey', 'kg', 1),
]

WHOLESALE_MAP = [
    ('carni di pollo - interi', 'Whole Chicken', 'kg', 1),
    ('carni di pollo - petto', 'Chicken Breast', 'kg', 1),
    ('carni di faraona - intere', 'Guinea Fowl Meat', 'kg', 1),
    ('carni di tacchino - fesa', 'Turkey Breast', 'kg', 1),
    ('pancetta fresca', 'Pork Belly', 'kg', 1),
    ('spalla senza osso', 'Pork Shoulder', 'kg', 1),
]

ROW = re.compile(
    r"<th id='table\d+r\d+'[^>]*>(.*?)</th>\s*<td[^>]*>([^<]*)</td>\s*<td[^>]*>([^<]*)</td>", re.S)


def decode(raw):
    try:
        return raw.decode('utf-8')
    except UnicodeDecodeError:
        return raw.decode('latin-1')


def week_date(s):
    """'2026-10-5' → the fifth week of October 2026; '2026-10' → the month."""
    parts = [int(x) for x in s.strip().split('-')]
    if len(parts) < 2:
        return None
    first = date(parts[0], parts[1], 1)
    if len(parts) == 2:
        return first
    d = first + timedelta(days=7 * (parts[2] - 1))
    return d if d.month == first.month else first.replace(day=28)


def parse_price(s):
    """'3,11 €/Kg' → (3.11, 'kg'); '19,57 €/100 unità' → (19.57, '100 unit')."""
    s = html.unescape(s).replace('\xa0', ' ').strip()
    m = re.match(r'(\d+(?:\.\d{3})*(?:,\d+)?)\s*€\s*/\s*(.+)$', s)
    if not m:
        return None, None
    value = float(m.group(1).replace('.', '').replace(',', '.'))
    unit = m.group(2).strip().lower()
    if unit.startswith('kg'):
        unit = 'kg'
    elif unit.startswith('capolino'):
        unit = 'head'
    elif unit.startswith('100 unit'):
        unit = '100 unit'
    return value, unit


# What each catalogue unit expects the source to be quoted in.
SOURCE_UNIT = {'kg': {'kg'}, 'l': {'kg'}, 'dozen': {'100 unit'}, 'unit': {'head'}}


def parse(page_html):
    """A price page → [(label, snapshot, price, source unit)]."""
    out = []
    for label, when, price in ROW.findall(page_html):
        label = re.sub(r'\s+', ' ', html.unescape(re.sub('<[^>]+>', '', label))).strip()
        value, unit = parse_price(price)
        snapshot = week_date(when) if re.match(r'\d{4}-\d{1,2}', when.strip()) else None
        if value and snapshot:
            out.append((label, snapshot, value, unit))
    return out


def lookup(label, mapping):
    key = re.sub(r'\s+', ' ', label.lower())
    for prefix, name, unit, factor in mapping:
        if key.startswith(prefix):
            return name, unit, factor
    return None


def figures_from(rows, mapping, today=None):
    """Map ISMEA rows to catalogue figures; varieties of one product are averaged."""
    today = today or date.today()
    groups = defaultdict(list)
    skipped = []
    for label, snapshot, value, src_unit in rows:
        hit = lookup(label, mapping)
        if not hit:
            skipped.append(label)
            continue
        name, unit, factor = hit
        if src_unit not in SOURCE_UNIT[unit]:
            skipped.append(f'{label} (quoted per {src_unit})')
            continue
        if (today - snapshot).days > MAX_AGE_DAYS:
            skipped.append(f'{label} (last quoted {snapshot})')
            continue
        groups[(name, unit)].append((snapshot, value * factor))

    figures = []
    for (name, unit), obs in sorted(groups.items()):
        latest = max(s for s, _ in obs)
        values = [v for s, v in obs if s == latest]
        figures.append(Figure(name, round(sum(values) / len(values), 4), unit, latest,
                              low=round(min(values), 4), high=round(max(values), 4)))
    return figures, skipped


def collect(pages, mapping):
    rows = []
    for page, what in pages.items():
        try:
            got = parse(decode(get(BASE + str(page), pause=1.5)))
        except Exception as e:
            print(f'  page {page} ({what}): {e}', file=sys.stderr)
            continue
        print(f'  {what}: {len(got)} quotes')
        rows.extend(got)
    return figures_from(rows, mapping)


def run():
    written = 0
    for stage, source, pages, mapping in (
        ('farmgate', SOURCE_ORIGIN, ORIGIN_PAGES, ORIGIN_MAP),
        ('wholesale', SOURCE_WHOLESALE, WHOLESALE_PAGES, WHOLESALE_MAP),
    ):
        print(f'--- {source} ---')
        figures, skipped = collect(pages, mapping)
        for f in figures:
            print(f'  {f.name:22} {f.price:>8.2f} /{f.unit:5} {f.snapshot}')
        if skipped:
            print(f'  not used: {len(skipped)} quotes ({", ".join(sorted(set(skipped))[:12])}…)')
        n, _ = write('IT', source, stage, figures)
        written += n
        for country in BORROWERS:
            write(country, source + ' (Italian figures)', stage, figures)

    if written == 0:
        raise RuntimeError('ISMEA returned nothing usable — the pages have changed')
    return written


if __name__ == '__main__':
    run()
