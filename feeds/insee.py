"""
France: monthly average consumer prices from INSEE ("prix moyens de vente de
détail", dataflow IPC-PM-2015).

A feed, not a scrape. INSEE collects these shelf prices for the consumer
price index and publishes the average for metropolitan France each month,
for about 60 everyday items: fresh fruit and vegetables, mushrooms, cuts of
beef, pork and rabbit, alongside fuel and haircuts we have no use for.

The SDMX service on bdm.insee.fr answers without a key. One request returns
the latest observation of every series in the dataflow (~165 KB); the
stopped series (SERIE_ARRETEE=TRUE) and the annual ones are left out.

    REF_AREA FM = France métropolitaine -> stored with no region (national)

Every series says its unit in its title: "(1 kg)", "(pièce)". We keep that
unit as INSEE gives it — a cauliflower is priced by the head, an avocado by
the piece — rather than guess a weight.

Terms: Licence Ouverte / Etalab 2.0, attribution "Source: INSEE".

    python feeds/insee.py
"""

import os
import re
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import common

URL = 'https://bdm.insee.fr/series/sdmx/data/IPC-PM-2015?lastNObservations=1'
SOURCE_NAME = 'INSEE, prix moyens de vente au détail (IPC-PM)'

# INSEE series (IDBANK) -> catalogue name, unit. The French title is checked
# against the third column so that a re-used IDBANK can't slip a different
# product in under an old name.
SERIES = {
    '001791256': ('Artichoke',         'unit', 'Artichauts (pièce)'),
    '001791255': ('Avocado',           'unit', 'Avocat (pièce)'),
    '000641432': ('Banana',            'kg',   'Bananes (1 kg)'),
    '000641422': ('Carrot',            'kg',   'Carottes (1 kg)'),
    '000641423': ('White Mushroom',    'kg',   'Champignons de Paris (1 kg)'),
    '001791254': ('Cauliflower',       'unit', 'Chou-fleur (pièce)'),
    '000641434': ('Lemons',            'kg',   'Citrons (1 kg)'),
    '000641435': ('Clementine',        'kg',   'Clémentines (1 kg)'),
    '000641425': ('Zucchini',          'kg',   'Courgettes (1 kg)'),
    '000641426': ('Endive',            'kg',   'Endives (1 kg)'),
    '000641359': ('Green Beans',       'kg',   'Haricots verts (1 kg)'),
    '001791257': ('Kiwi',              'unit', 'Kiwi (pièce)'),
    '000641427': ('Onion',             'kg',   'Oignons (1 kg)'),
    '000641365': ('Oranges',           'kg',   'Oranges (1 kg)'),
    '000641428': ('Leek',              'kg',   'Poireaux (1 kg)'),
    '000641369': ('Pears',             'kg',   'Poires (1 kg)'),
    '010596274': ('Bell Pepper',       'kg',   'Poivrons (1 kg)'),
    '000641367': ('Apples',            'kg',   'Pommes (1 kg)'),
    '000641360': ('Potato',            'kg',   'Pommes de terre de conservation (1 kg)'),
    '000641429': ('Tomato',            'kg',   'Tomates (1 kg)'),
    # Meat: only where the French cut is the catalogue's cut.
    '000442435': ('Fresh Ribeye',      'kg',   'Boeuf : entrecôte (1 kg)'),
    '000442432': ('Fresh Tenderloin',  'kg',   'Boeuf : filet (1 kg)'),
    '000442433': ('Fresh Sirloin',     'kg',   'Boeuf : faux filet (1 kg)'),
    '000442437': ('Beef Ribs',         'kg',   'Boeuf : côte avec os (1 kg)'),
    '000442436': ('Beef Steak',        'kg',   'Boeuf : bifteck dans la bavette (1 kg)'),
    '000442450': ('Pork Shoulder',     'kg',   'Porc : échine avec os (1 kg)'),
    '000442453': ('Rabbit Meat',       'kg',   'Lapin entier (1 kg)'),
}
# Left out on purpose: new potatoes, rump steak, pork loin roast, veal, calf's
# liver, cooked ham ("jambon supérieur"), grapefruit, fish and shellfish, bread
# — no catalogue product is the same thing.

ATTR = re.compile(r'(\w+)="([^"]*)"')


def parse(xml):
    """SDMX structure-specific XML -> [(idbank, title_fr, period, value)] for live monthly series."""
    out = []
    for m in re.finditer(r'<Series ([^>]*)>(.*?)</Series>', xml, flags=re.S):
        a = dict(ATTR.findall(m.group(1)))
        if a.get('FREQ') != 'M' or a.get('SERIE_ARRETEE') == 'TRUE' or a.get('REF_AREA') != 'FM':
            continue
        obs = [dict(ATTR.findall(o)) for o in re.findall(r'<Obs ([^>]*)/>', m.group(2))]
        obs = [o for o in obs if o.get('OBS_VALUE') not in (None, '', 'NaN')]
        if not obs:
            continue
        last = max(obs, key=lambda o: o['TIME_PERIOD'])
        title = a.get('TITLE_FR', '').split(' - ', 1)[-1]
        out.append((a.get('IDBANK'), title, last['TIME_PERIOD'], float(last['OBS_VALUE'])))
    return out


def figures(rows, today=None):
    today = today or date.today()
    out = []
    for idbank, title, period, value in rows:
        if idbank not in SERIES:
            continue
        name, unit, expected = SERIES[idbank]
        if not title.startswith(expected.split(' (')[0]):
            print(f'  {idbank}: title is now "{title}", expected "{expected}" — skipped', file=sys.stderr)
            continue
        y, mth = (int(x) for x in period.split('-')[:2])
        snapshot = date(y, mth, 1)
        # A series that has not moved for over a year has quietly stopped.
        if (today.year - y) * 12 + today.month - mth > 13:
            continue
        out.append(common.Figure(name, value, unit, snapshot))
    return out


def run():
    xml = common.get(URL, headers={'Accept': 'application/xml'}, timeout=120).decode('utf-8')
    rows = parse(xml)
    figs = figures(rows)
    for f in sorted(figs, key=lambda f: f.name):
        print(f'  {f.name:18} {f.price:>8.2f} /{f.unit:5} {f.snapshot}')
    if not figs:
        raise RuntimeError('INSEE returned no usable series — the dataflow or the API has changed')
    return common.write('FR', SOURCE_NAME, 'retail', figs)


if __name__ == '__main__':
    run()
