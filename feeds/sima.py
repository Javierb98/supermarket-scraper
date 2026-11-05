"""
Portugal: SIMA weekly market quotes (GPP, Ministry of Agriculture).

SIMA — Sistema de Informação de Mercados Agrícolas — is the ministry's price
reporting system, run by the GPP (Gabinete de Planeamento, Políticas e
Administração Geral). Its public query pages at regsima.gpp.pt answer a plain
GET with JSON, the same request the site's own "Pesquisar" button makes. No
key, no login.

Two kinds of market, two price stages:

  Mercados abastecedores (tipo 12)            -> 'wholesale'
      the wholesale markets: MARL (Lisbon), MAP (Porto), MAC (Coimbra),
      MAF (Faro); fruit and vegetables, quoted two or three days a week.
  Mercados de produção (tipo 8)                -> 'farmgate'
      what producers are paid, weekly, by agrarian region (SE/SP: at the
      farm or the producers' auction).
      The same pages also quote poultry, eggs and rabbit at markets whose
      name ends in " Gr." — the trade price out of the slaughterhouse or
      packing centre — and those are stored as 'wholesale'. Live-weight
      livestock prices are not used: no farm sells by the kilo of live animal.

Each quote has a minimum, a maximum and the most frequent price ("Freq").
The most frequent price is stored as the figure, min and max as its range.
Only Portuguese produce is used (origin "Nacional", Algarve, Madeira, Açores):
the wholesale markets also quote Spanish tomatoes and Costa Rican bananas,
which no Portuguese farm sells.

Regions are SIMA's agrarian regions ("Ribatejo e Oeste", "Entre Douro e
Minho", …). Each stage also gets a national figure (region None), the mean of
every quote used.

Terms: GPP public information, reused with attribution
(https://www.gpp.pt/index.php/avisos-legais/avisos-legais); see SOURCES.md.

    python feeds/sima.py
"""

import json
import os
import re
import sys
import unicodedata
import urllib.parse
from collections import defaultdict
from datetime import date, datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, get, write  # noqa: E402

BASE = 'https://regsima.gpp.pt/regsima/consulta/'
SOURCE = 'GPP SIMA'
WHOLESALE_MARKETS = ['33', '108', '179', '180']      # MARL, MAP, MAC, MAF
LOOKBACK_DAYS = 21          # how far back a query reaches
MAX_AGE_DAYS = 21           # a quote older than this is not this week's price

# (tipo, setor): which query, and what it covers.
QUERIES = [
    (12, 22, 'wholesale markets, fruit'),
    (12, 24, 'wholesale markets, vegetables'),
    (8, 22, 'production markets, fruit'),
    (8, 24, 'production markets, vegetables'),
    (8, 13, 'production markets, poultry'),
    (8, 14, 'production markets, eggs'),
    (8, 31, 'production markets, rabbit'),
]

NATIONAL_ORIGINS = {'nacional', 'algarve', 'madeira', 'acores', 'portugal'}
FOREIGN_ORIGINS = {
    'espanha', 'franca', 'italia', 'grecia', 'paisesbaixos', 'holanda', 'marrocos', 'chile', 'peru',
    'brasil', 'costarica', 'colombia', 'angola', 'africadosul', 'novazelandia', 'argentina', 'china',
    'equador', 'israel', 'egipto', 'turquia', 'belgica', 'alemanha', 'mexico', 'eua', 'uruguai',
}


def fold(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]', '', s)


# (product, variety prefix or '', catalogue name, unit) — folded keys, first
# match wins. The variety is the label's second field ("Tomate*Cacho*II*...").
MAP = [
    ('tomate', 'cereja', 'Cherry Tomato', 'kg'),
    ('tomate', 'cherry', 'Cherry Tomato', 'kg'),
    ('tomate', 'cacho', 'Vine Tomatoes', 'kg'),
    ('tomate', 'coracaodeboi', 'Beefsteak Tomatoes', 'kg'),
    ('tomate', 'chucha', 'Plum Tomatoes', 'kg'),
    ('tomate', 'alongado', 'Plum Tomatoes', 'kg'),
    ('tomate', 'redondo', 'Tomato', 'kg'),
    ('tomate', 'sulcado', 'Tomato', 'kg'),
    ('tomate', 'rosa', 'Tomato', 'kg'),
    ('batatadoce', '', 'Sweet Potato', 'kg'),
    ('batata', 'conservacaovermelha', 'Red Potatoes', 'kg'),
    ('batata', 'conservacao', 'Potato', 'kg'),
    ('cebola', 'branca', 'White Onion', 'kg'),
    ('cebola', 'roxa', 'Red Onion', 'kg'),
    ('cebola', 'conservacao', 'Onion', 'kg'),
    ('cenoura', '', 'Carrot', 'kg'),
    ('courgette', '', 'Zucchini', 'kg'),
    ('couve', 'brocolo', 'Broccoli', 'kg'),
    ('couve', 'flor', 'Cauliflower', 'kg'),
    ('couve', 'lombardo', 'Savoy Cabbage', 'kg'),
    ('couve', 'roxa', 'Red Cabbage', 'kg'),
    ('alface', 'frisada', 'Frisée Lettuce', 'kg'),
    ('alhofrances', '', 'Leek', 'kg'),
    ('alhoseco', '', 'Garlic', 'kg'),
    ('beringela', '', 'Eggplant', 'kg'),
    ('beterraba', '', 'Beetroot', 'kg'),
    ('pepino', '', 'Cucumber', 'kg'),
    ('pimento', '', 'Bell Pepper', 'kg'),
    ('espinafre', '', 'Spinach', 'kg'),
    ('feijaoverde', '', 'Green Beans', 'kg'),
    ('abobora', 'butternut', 'Butternut Squash', 'kg'),
    ('abobora', 'buternet', 'Butternut Squash', 'kg'),
    ('abobora', '', 'Pumpkin', 'kg'),
    ('nabo', 'semrama', 'Turnip', 'kg'),
    ('cogumelo', 'shitake', 'Shiitake Mushroom', 'kg'),
    ('cogumelo', 'caixa', 'White Mushroom', 'kg'),
    ('agriao', '', 'Watercress', 'kg'),
    ('coentro', '', 'Cilantro', 'kg'),
    ('salsa', '', 'Parsley', 'kg'),
    ('hortela', '', 'Mint', 'kg'),
    ('quiabo', '', 'Okra', 'kg'),
    ('chuchu', '', 'Chayote', 'kg'),
    # fruit
    ('maca', 'pinklady', 'Pink Lady Apples', 'kg'),
    ('maca', '', 'Apples', 'kg'),
    ('pera', '', 'Pears', 'kg'),
    ('laranja', '', 'Oranges', 'kg'),
    ('clementina', '', 'Clementine', 'kg'),
    ('tangera', '', 'Mandarin Oranges Fresh', 'kg'),
    ('tangerina', '', 'Mandarin Oranges Fresh', 'kg'),
    ('limao', '', 'Lemons', 'kg'),
    ('lima', '', 'Lime', 'kg'),
    ('banana', '', 'Banana', 'kg'),
    ('kiwi', '', 'Kiwi', 'kg'),
    ('diospiro', '', 'Persimmon', 'kg'),
    ('roma', '', 'Pomegranate', 'kg'),
    ('castanha', '', 'Chestnuts', 'kg'),
    ('morango', '', 'Strawberries', 'kg'),
    ('mirtilo', '', 'Blueberries', 'kg'),
    ('framboesa', '', 'Raspberry', 'kg'),
    ('amora', '', 'Blackberries', 'kg'),
    ('uva', 'redglobe', 'Grapes Red', 'kg'),
    ('uva', 'preta', 'Grapes Red', 'kg'),
    ('uva', 'branca', 'Grapes Green', 'kg'),
    ('uva', 'dmaria', 'Grapes Green', 'kg'),
    ('pessego', '', 'Peaches', 'kg'),
    ('ameixa', '', 'Plums', 'kg'),
    ('melancia', '', 'Watermelon', 'kg'),
    ('melao', '', 'Melon', 'kg'),
    ('abacate', '', 'Avocado', 'kg'),
    ('manga', '', 'Mango', 'kg'),
    ('maracuja', '', 'Passion Fruit', 'kg'),
    ('goiaba', '', 'Guava', 'kg'),
    ('anona', '', 'Custard Apple', 'kg'),
    ('papaia', '', 'Papaya', 'kg'),
    # poultry, eggs, rabbit (slaughtered / packed, never live weight)
    ('peitodefrango', '', 'Chicken Breast', 'kg'),
    ('pernadefrangocomcosta', '', 'Chicken Drumsticks', 'kg'),
    ('frango', '65', 'Whole Chicken', 'kg'),
    ('peitodeperusemossosempele', '', 'Turkey Breast', 'kg'),
    ('pernadeperucomossocompele', '', 'Turkey Legs', 'kg'),
    ('coelho', 'abatido', 'Rabbit Meat', 'kg'),
    ('ovodearlivreclassificado', '', 'Eggs', 'dozen'),
]


def lookup(label):
    fields = label.split('*')
    product = fold(fields[0])
    variety = fold(fields[1]) if len(fields) > 1 else ''
    for p, v, name, unit in MAP:
        if product == p and variety.startswith(v):
            return name, unit
    return None


def quoted_unit(label):
    """The label's last field: 'EUR/kg', 'EUR/Dúzia', 'EUR/kg P. Carcaça', …"""
    last = fold(label.split('*')[-1])
    if last.startswith('eurkgpvivo'):
        return 'live'
    if last.startswith('eurkg'):
        return 'kg'
    if last.startswith('eurduzia'):
        return 'dozen'
    return None


def is_national(label):
    fields = [fold(f) for f in label.split('*')]
    if any(f in FOREIGN_ORIGINS for f in fields):
        return False
    return True


def num(s):
    try:
        return float((s or '').replace(',', '.'))
    except ValueError:
        return None


def query(tipo, setor, start, end):
    """All quotes for one sector and market type between two dates."""
    def call(path, params):
        return get(BASE + path + '?' + urllib.parse.urlencode(params, doseq=True), pause=1.0).decode('utf-8', 'replace')

    def options(html):
        return re.findall(r"value='(\d+)'", html)

    # Species 4 is "Todas" (all), which the server does not expand: ask for each.
    especies = [v for v in options(call('get_especie', {'setor': setor, 'tipo': tipo})) if v != '4']
    params = {'setor': setor, 'especie': especies, 'tipo': tipo, 'export': 0,
              'ini': start.isoformat(), 'fim': end.isoformat()}
    if tipo == 12:
        params['mercado'] = WHOLESALE_MARKETS
    else:
        params['regiao'] = options(call('get_regiao', {'setor': setor, 'especie': especies, 'tipo': tipo}))
        params['mercado'] = options(call('get_mercado', {'setor': setor, 'especie': especies,
                                                          'regiao': params['regiao'], 'tipo': tipo}))
    data = json.loads(call('get_cotacoes', params)).get('data') or []
    return [r for r in data if len(r) >= 9 and r[5] and r[5] != '-']


def figures_from(rows, tipo, today=None):
    """SIMA rows → {stage: [Figure]} (regional and national)."""
    today = today or date.today()
    # The latest quote of each label at each market.
    latest = {}
    for label, _species, region, market, _week, day, low, high, freq, *_ in rows:
        try:
            when = datetime.strptime(day, '%d-%m-%Y').date()
        except ValueError:
            continue
        key = (label, market)
        if key not in latest or when > latest[key][0]:
            latest[key] = (when, region.strip(), market.strip(), num(low), num(high), num(freq))

    groups = defaultdict(list)
    for (label, _), (when, region, market, low, high, freq) in latest.items():
        if (today - when).days > MAX_AGE_DAYS or not freq or freq <= 0:
            continue
        hit = lookup(label)
        unit = quoted_unit(label)
        if not hit or unit in (None, 'live') or unit != hit[1] or not is_national(label):
            continue
        stage = 'wholesale' if tipo == 12 or market.endswith(' Gr.') else 'farmgate'
        obs = (when, freq, low or freq, high or freq)
        if region.lower() not in ('continente', 'portugal - continente'):
            groups[(stage, hit[0], hit[1], region)].append(obs)
        groups[(stage, hit[0], hit[1], None)].append(obs)

    out = defaultdict(list)
    for (stage, name, unit, region), obs in sorted(groups.items(), key=lambda kv: [str(x) for x in kv[0]]):
        values = [o[1] for o in obs]
        out[stage].append(Figure(
            name, round(sum(values) / len(values), 4), unit, max(o[0] for o in obs), region=region or None,
            low=round(min(o[2] for o in obs), 4), high=round(max(o[3] for o in obs), 4),
        ))
    return out


def run():
    end = date.today()
    start = end - timedelta(days=LOOKBACK_DAYS)
    by_stage = defaultdict(list)
    for tipo, setor, what in QUERIES:
        try:
            rows = query(tipo, setor, start, end)
        except Exception as e:
            print(f'  {what}: {e}', file=sys.stderr)
            continue
        got = figures_from(rows, tipo, today=end)
        print(f'  {what}: {len(rows)} quotes → {sum(len(v) for v in got.values())} figures')
        for stage, figures in got.items():
            by_stage[stage].extend(figures)

    written = 0
    for stage in ('wholesale', 'farmgate'):
        figures = merge(by_stage.get(stage, []))
        for f in figures:
            print(f'  {stage:9} {f.name:22} {f.region or "(Portugal)":22} {f.price:>7.2f} /{f.unit:5} {f.snapshot}')
        label = SOURCE + (', mercados abastecedores e grossistas' if stage == 'wholesale' else ', mercados de produção')
        n, _ = write('PT', label, stage, figures)
        written += n
    if written == 0:
        raise RuntimeError('SIMA returned nothing usable — the query pages have changed')
    return written


def merge(figures):
    """One figure per product and region: the fruit and vegetable queries can
    both reach the same product's national figure only in theory, but poultry
    comes from two sectors (13 and 31) — keep it to one row per key."""
    by_key = {}
    for f in figures:
        k = (f.name, f.unit, f.region)
        if k in by_key:
            g = by_key[k]
            g.price = round((g.price + f.price) / 2, 4)
            g.low, g.high = min(g.low, f.low), max(g.high, f.high)
            g.snapshot = max(g.snapshot, f.snapshot)
        else:
            by_key[k] = f
    return list(by_key.values())


if __name__ == '__main__':
    run()
