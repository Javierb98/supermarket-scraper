"""
France: wholesale fruit and vegetable prices from FranceAgriMer's RNM, by
wholesale market (Rungis and the regional MINs).

Same source, same page format and same row mapping as feeds/rnm.py; the
difference is the stage. These are trade-to-trade prices quoted by
wholesalers ("cours grossistes"), excluding VAT, so they are stored as
`wholesale` — shown to the farmer, labelled, never used for a badge.

One region per market, named after the market. Lyon-Corbas publishes fruit
and vegetables on two pages, combined here. The organic-only market pages
are not read.

Each market is quoted on its own day (most daily, Nice weekly, Avignon
twice a week); the figure carries the date of the market's latest prices.

Terms: FranceAgriMer's open licence (Licence Ouverte), source named:
"FranceAgriMer – RNM".

    python feeds/rnm_wholesale.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import common
from feeds.rnm import figures_for

SOURCE_NAME = 'FranceAgriMer RNM, cours grossistes'

# region (the market) -> RNM market page(s)
MARKETS = [
    ('MIN de Rungis',                 ['0123']),
    ('Marché de Lyon-Corbas',         ['0097', '0095']),
    ('MIN de Marseille',              ['0052']),
    ("MIN d'Avignon-Cavaillon",       ['0030']),
    ('MIN de Nice',                   ['0031']),
    ('MIN de Bordeaux-Brienne',       ['0071']),
    ('MIN de Toulouse',               ['0066']),
    ('MIN de Nantes',                 ['0110']),
    ('MIN de Strasbourg',             ['0027']),
    ('Marché de gros Lille',          ['0108']),
]


def run():
    figs = []
    for region, pages in MARKETS:
        try:
            got = figures_for(pages, region=region, wholesale=True)
        except Exception as e:                       # one market down is not the feed down
            print(f'  {region}: {e}', file=sys.stderr)
            continue
        print(f'  {region}: {len(got)} products')
        figs += got
    if not figs:
        raise RuntimeError('RNM returned no wholesale prices — the pages have changed')
    return common.write('FR', SOURCE_NAME, 'wholesale', figs)


if __name__ == '__main__':
    run()
