"""
France: weekly supermarket shelf prices for fruit and vegetables from
FranceAgriMer's RNM (Réseau des Nouvelles des Marchés), "DETAIL GMS".

A feed, not a scrape of a shop. RNM's surveyors note the shelf prices of
fresh produce in supermarkets ("grandes et moyennes surfaces") across France
every week and publish the averages as an HTML table, one page for fruit
(market 2503) and one for vegetables (market 2502):

    https://rnm.franceagrimer.fr/prix?M2502:MARCHE

Each row is one product as sold: "TOMATE ronde rouge France 57-67 ou
67-82mm vrac  3.56  -0.14  2.99  3.99" — average, change, low, high, in euros
including VAT, per kilo unless the label says otherwise ("(la pièce)",
"(les 6 pièces)", "(la barq. 125g)"). Rows priced by the bunch, the pack or
the case are left out: there is no honest per-kilo or per-piece figure in
them.

How rows become one figure per catalogue product:
  * organic rows are left out (except for the catalogue's Organic Tomatoes);
  * French-grown rows are used when there are any, imports otherwise — a
    French farm is compared with French produce;
  * at retail, loose ("vrac") rows are preferred to bags and nets when both
    exist, being what a farm stall sells;
  * the rest are averaged; low and high are the extremes of the rows.

The same page format is used by RNM's wholesale markets (Rungis and the
other MINs); feeds/rnm_wholesale.py reuses the parser and mapping below.

Terms: FranceAgriMer's open licence (Licence Ouverte), reuse allowed
including commercially, with the source named: "FranceAgriMer – RNM".
robots.txt only disallows /catalogue?*.

    python feeds/rnm.py
"""

import html as htmllib
import os
import re
import sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import common

BASE = 'https://rnm.franceagrimer.fr/prix?M{}:MARCHE'
SOURCE_NAME = 'FranceAgriMer RNM, prix au détail GMS'
MARKETS = ['2503', '2502']          # fruit, vegetables — supermarket retail, national
MAX_AGE_DAYS = 31

# --- what each row is -------------------------------------------------------

# First match wins. Patterns are matched against the row label, which starts
# with the product family in capitals.
RULES = [
    (r'^AIL ',                                   'Garlic'),
    (r'^AMANDE ',                                'Almonds'),
    (r'^ANANAS ',                                'Pineapple'),
    (r'^ARTICHAUT ',                             'Artichoke'),
    (r'^ASPERGE verte',                          'Green Asparagus'),
    (r'^ASPERGE blanche',                        'White Asparagus'),
    (r'^AUBERGINE Graffiti',                     'Graffiti Eggplant'),
    (r'^AUBERGINE ',                             'Eggplant'),
    (r'^AVOCAT (?!tropical)',                    'Avocado'),
    (r'^BANANE (?!Frécinette)',                  'Banana'),
    (r'^BETTE ',                                 'Swiss Chard'),
    (r'^BETTERAVE ROUGE .*crue',                 'Beetroot'),
    (r'^CAROTTE (?!jaune|pourpre)',              'Carrot'),
    (r'^CERISE ',                                'Cherries'),
    (r'^CHAMPIGNON DE PARIS ',                   'White Mushroom'),
    (r'^CHAYOTTE ',                              'Chayote'),
    (r'^CHICORÉE frisée',                        'Curly Endive'),
    (r'^CHOU Brocoli',                           'Broccoli'),
    (r'^CHOU Chinois',                           'Napa Cabbage'),
    (r'^CHOU DE BRUXELLES',                      'Brussels Sprouts'),
    (r'^CHOU FLEUR',                             'Cauliflower'),
    (r'^CHOU rouge',                             'Red Cabbage'),
    (r'^CHOU [Ff]risé',                          'Savoy Cabbage'),
    (r'^CITRON vert',                            'Lime'),
    (r'^CITRON ',                                'Lemons'),
    (r'^LIME ',                                  'Lime'),
    (r'^CLÉMENTINE ',                            'Clementine'),
    (r'^CONCOMBRE (?!mini)',                     'Cucumber'),
    (r'^COURGE Butternut',                       'Butternut Squash'),
    (r'^COURGE Spaghetti',                       'Spaghetti Squash'),
    (r'^POTIRON ',                               'Pumpkin'),
    (r'^COURGETTE (?!ronde)',                    'Zucchini'),
    (r'^CRESSON ',                               'Watercress'),
    (r'^CÉLERI-BRANCHE ',                        'Celery'),
    (r'^CÉLERI-RAVE ',                           'Celeriac'),
    (r'^DATTE ',                                 'Date'),
    (r'^ENDIVE ',                                'Endive'),
    (r'^FENOUIL ',                               'Fennel'),
    (r'^FIGUE (fraîche|noire)',                  'Fig'),
    (r'^FRAISE ',                                'Strawberries'),
    (r'^FRAMBOISE ',                             'Raspberry'),
    (r'^FRUIT DE LA PASSION',                    'Passion Fruit'),
    (r'^GINGEMBRE ',                             'Fresh Ginger'),
    (r'^GRENADE ',                               'Pomegranate'),
    (r'^GROSEILLE ',                             'Red Currant'),
    (r'^HARICOT VERT (?!Coco)',                  'Green Beans'),
    (r'^KAKI ',                                  'Persimmon'),
    (r'^KIWI (?!Gold|rouge)',                    'Kiwi'),     # green kiwi; gold and red are dearer
    (r'^LAITUE Romaine',                         'Romaine Lettuce'),
    (r'^LAITUE Sucrine',                         'Mini Romaine'),
    (r'^LAITUE Feuille de chêne rouge',          'Red Oak Lettuce'),
    (r'^LAITUE Feuille de chêne blonde',         'Green Oak Lettuce'),
    (r'^MANDARINE ',                             'Mandarin Oranges Fresh'),
    (r'^MANGUE ',                                'Mango'),
    (r'^MARRON CHATAIGNE',                       'Chestnuts'),
    (r'^MELON ',                                 'Melon'),
    (r'^MYRTILLE ',                              'Blueberries'),
    (r'^MÛRE ',                                  'Blackberries'),
    (r'^NAVET ',                                 'Turnip'),
    (r'^NOISETTE ',                              'Hazelnuts'),
    (r'^NOIX DE COCO',                           'Coconut'),
    (r'^NOIX ',                                  'Walnuts'),
    (r'^OIGNON rouge',                           'Red Onion'),
    (r'^OIGNON blanc sec',                       'White Onion'),
    (r'^OIGNON (?!rouge|blanc|Cebette|doux)',     'Onion'),
    (r'^ORANGE ',                                'Oranges'),
    (r'^PANAIS ',                                'Parsnip'),
    (r'^PAPAYE ',                                'Papaya'),
    (r'^PATATE DOUCE',                           'Sweet Potato'),
    (r'^PERSIL ',                                'Parsley'),
    (r'^PIMENT ',                                'Chili Pepper'),
    (r'^PLEUROTE ',                              'Oyster Mushroom'),
    (r'^POIRE (?!Nashi)',                        'Pears'),
    (r'^POIREAU ',                               'Leek'),
    (r'^POIS à écosser',                         'Green Peas'),
    (r'^POIVRON ',                               'Bell Pepper'),
    (r'^POMME DE TERRE ',                        'Potato'),
    (r'^POMME ',                                 'Apples'),
    (r'^PRUNE ',                                 'Plums'),
    (r'^PÊCHE ',                                 'Peaches'),
    (r'^RADIS (?!noir|Blue|Green|Red)',          'Radish'),
    (r'^RAISIN (blanc|Chasselas|Italia|Danlas)', 'Grapes Green'),
    (r'^RAISIN (noir|Muscat Hambourg|Lavallée|Palieri|Red Globe)', 'Grapes Red'),
    (r'^ROMARIN ',                               'Rosemary'),
    (r'^SAUGE ',                                 'Sage'),
    (r'^SHII-TAKE',                              'Shiitake Mushroom'),
    (r'^THYM ',                                  'Thyme'),
    (r'^TOMATE cerise',                          'Cherry Tomato'),
    (r'^TOMATE (allongée )?coeur|coeur de boeuf', 'Beefsteak Tomatoes'),
    (r'^TOMATE allongée rouge',                  'Plum Tomatoes'),
    (r'^TOMATE ronde',                           'Tomato'),
    (r'^TOPINAMBOUR ',                           'Jerusalem Artichoke'),
    (r'^ÉCHALOTE ',                              'Shallots'),
    (r'^ÉPINARD ',                               'Spinach'),
]
# Rows that are also a named variety the catalogue has, on top of the generic
# product above (a Pink Lady is an apple, and a Pink Lady).
VARIETIES = [
    (r'^POMME Pink-lady',                        'Pink Lady Apples'),
    (r'^POMME DE TERRE .*Ratte',                 'Fingerling Potatoes'),
    (r'^TOMATE ronde.*grappe',                   'Vine Tomatoes'),
    (r'^TOMATE anciennes',                       'Heirloom Tomatoes'),
]
ORGANIC_RULES = [
    (r'^TOMATE ronde.*biologique',               'Organic Tomatoes'),
]
# Left out on purpose: cooked beetroot, dried figs, prickly pears, round and
# mini courgettes, potimarron and other squashes, white/green cabbage, lamb's
# lettuce, batavia/butterhead lettuce, scarole, grapefruit, quince, rutabaga,
# wild mushrooms the catalogue lacks, "Muscat" grapes of unstated colour.

FRENCH = re.compile(r'\bFrance\b|Bretagne|Sud-Est|Sud-Ouest|Corse|Tarn|Lautrec|Cévennes|'
                    r'Moissac|Ventoux|Grenoble|Savoie')
NOT_FRENCH = re.compile(r'hors Fr\.|hors UE')


def names_for(label):
    """Row label -> catalogue names it is a price for ([] when none)."""
    if 'biologique' in label:
        return [n for p, n in ORGANIC_RULES if re.search(p, label)]
    names = []
    for p, n in RULES:
        if re.search(p, label):
            names.append(n)
            break
    if names:
        names += [n for p, n in VARIETIES if re.search(p, label)]
    return names


def unit_of(label, default=('kg', 1.0), wholesale=False):
    """Row label -> (unit, how many of that unit the price is for), or None to skip the row.

    Wholesale pages are not consistent: "colis de 12" or "barq.125g" with no
    unit is quoted by the case or punnet on one market and by the kilo on
    another, so such rows are skipped there. The supermarket pages always
    quote those per kilo."""
    m = re.search(r'\(([^()]*)\)\s*$', label)
    if not m or not re.search(r'[a-z]', m.group(1)):
        if wholesale and re.search(r'colis de \d|barq\. ?\d', label):
            return None
        return default
    u = m.group(1).strip()
    if u in ('la pièce', 'le fruit'):
        return 'unit', 1.0
    n = re.fullmatch(r'les (\d+) (pièces|fruits)', u)
    if n:
        return 'unit', float(n.group(1))
    g = re.fullmatch(r'(?:la barq\.|le sachet|les) ?(\d+(?:[.,]\d+)?) ?(g|kg)', u)
    if g:
        qty = float(g.group(1).replace(',', '.'))
        return 'kg', qty / 1000 if g.group(2) == 'g' else qty
    if re.search(r'botte|colis|cdt|filet|barq|sachet|pièces|fruits|caisse|plateau', u):
        return None                  # priced by the bunch, the pack or the case
    return default                   # a calibre in brackets, e.g. "(58-67mm)", "(18-22/kg)"


def num(s):
    s = (s or '').strip().replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return None


def cells_of(row):
    return [htmllib.unescape(re.sub(r'<[^>]+>', '', c)).strip()
            for c in re.findall(r'<td[^>]*>(.*?)</td>', row, flags=re.S)]


def parse_page(page):
    """An RNM market page -> (market title, date of the prices, default unit, [(label, avg, low, high)])."""
    title = re.search(r'<h1[^>]*>(.*?)</h1>', page, flags=re.S)
    title = htmllib.unescape(re.sub(r'<[^>]+>', ' ', title.group(1))).split('(cours')[0].strip() if title else ''
    when = None
    h2 = re.search(r'<h2[^>]*>(.*?)</h2>', page, flags=re.S)
    if h2:
        d = re.search(r'(\d{2})-(\d{2})-(\d{4})', h2.group(1))
        if d:
            when = date(int(d.group(3)), int(d.group(2)), int(d.group(1)))
    i = page.find('id="tabcotmar"')
    if i < 0:
        return title, when, None, []
    table = page[i:page.find('</table>', i)]
    head = htmllib.unescape(re.sub(r'<[^>]+>', ' ', ' '.join(re.findall(r'<th[^>]*>(.*?)</th>', table, flags=re.S)[:1])))
    default = ('kg', 1.0) if re.search(r'le kg', head) else None
    rows = []
    for r in re.findall(r'<tr[^>]*>(.*?)</tr>', table, flags=re.S):
        c = cells_of(r)
        if len(c) >= 2 and num(c[1]):
            rows.append((re.sub(r'\s+', ' ', c[0]), num(c[1]),
                         num(c[3]) if len(c) > 3 else None, num(c[4]) if len(c) > 4 else None))
    return title, when, default, rows


def combine(rows, default=('kg', 1.0), prefer_loose=False, wholesale=False):
    """Rows of one market -> {(name, unit): (avg, low, high, n rows)}."""
    lines = {}
    for label, avg, low, high in rows:
        names = names_for(label)
        if not names:
            continue
        u = unit_of(label, default, wholesale) if default else None
        if u is None:
            continue
        unit, qty = u
        french = bool(FRENCH.search(label)) and not NOT_FRENCH.search(label)
        loose = 'vrac' in label
        for name in names:
            lines.setdefault((name, unit), []).append(
                (french, loose, avg / qty, (low or avg) / qty, (high or avg) / qty))

    out = {}
    for key, ls in lines.items():
        if any(l[0] for l in ls):
            ls = [l for l in ls if l[0]]
        if prefer_loose and any(l[1] for l in ls):
            ls = [l for l in ls if l[1]]
        avg = sum(l[2] for l in ls) / len(ls)
        out[key] = (round(avg, 4), round(min(l[3] for l in ls), 4), round(max(l[4] for l in ls), 4), len(ls))
    return out


def fetch(market):
    return common.get(BASE.format(market), headers={'Accept': 'text/html'}, timeout=60, pause=2.0).decode('utf-8', 'replace')


def figures_for(markets, region=None, prefer_loose=False, wholesale=False, today=None):
    """Fetch and combine one or more RNM market pages into Figures for one region."""
    today = today or date.today()
    rows, when, default = [], None, ('kg', 1.0)
    for m in markets:
        title, d, dflt, rs = parse_page(fetch(m))
        if d is None or today - d > timedelta(days=MAX_AGE_DAYS):
            print(f'  {title or m}: no recent prices ({d}) — skipped', file=sys.stderr)
            continue
        if dflt is None:
            print(f'  {title or m}: prices are not per kilo by default — skipped', file=sys.stderr)
            continue
        print(f'  {title}: {len(rs)} rows, {d}')
        rows += rs
        when = max(when, d) if when else d
    if not rows:
        return []
    return [common.Figure(name, avg, unit, when, region=region, low=low, high=high)
            for (name, unit), (avg, low, high, n) in sorted(combine(rows, default, prefer_loose, wholesale).items())]


def run():
    figs = figures_for(MARKETS, region=None, prefer_loose=True)
    for f in figs:
        print(f'  {f.name:24} {f.price:>8.2f} /{f.unit:5} ({f.low:.2f}–{f.high:.2f}) {f.snapshot}')
    if not figs:
        raise RuntimeError('RNM returned no supermarket prices — the pages have changed')
    return common.write('FR', SOURCE_NAME, 'retail', figs)


if __name__ == '__main__':
    run()
