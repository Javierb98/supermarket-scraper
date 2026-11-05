"""
Switzerland (and Liechtenstein): monthly producer prices from the Federal
Office for Agriculture (BLW/OFAG) market observation, read from LINDAS the
same way as the consumer prices (feeds/blw_consumer.py).

What the farmer is paid, ex farm ("ab Hof"): stage farmgate, VAT excluded.
Shown to the farmer, labelled, never badged.

    Eggs/Production_Price_Month               Swiss eggs, all housing systems, weighted mean
    MilkDairyProducts/Production_Price_Month  Swiss milk, all channels ("Milch CH, total")

BLW publishes both in Rappen (per egg, per kg of milk); they are stored in
francs per dozen and per litre (milk at 1.03 kg a litre). The milk cube's
five milk regions are numbered, not named, so only the national figure is
kept. Its other producer cube with monthly figures (meat, slaughter-weight
prices franco abattoir) prices carcasses, which no farm sells by, and is left
out.

Terms: Swiss open government data, "open use, must provide the source"
(https://opendata.swiss/en/terms-of-use#terms_by).

    python feeds/blw_producer.py              the last 12 months
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.blw_consumer import EXCL_VAT, figures, for_liechtenstein, months_back, replace

SOURCE_NAME = 'BLW market observation, producer prices (LINDAS)'
SOURCE_NAME_LI = 'BLW market observation, producer prices (Swiss figures, LINDAS)'

SWITZERLAND = {'https://agriculture.ld.admin.ch/foag/sales-region/1': None}
SWISS_ORIGIN = {'https://agriculture.ld.admin.ch/foag/product-origin/1'}

MILK_KG_PER_L = 1.03

EGGS = {
    235: ('Eggs', None, 1 / 12, 'dozen'),             # all systems, CH, weighted mean; per egg
}
MILK = {
    271: ('Raw Cow Milk', None, 1 / MILK_KG_PER_L, 'l'),  # Milch CH, total; per kg -> per litre
}

CUBES = [
    ('Eggs/Production_Price_Month', EGGS),
    ('MilkDairyProducts/Production_Price_Month', MILK),
]


def run(months=12):
    since = months_back(months)
    figs = []
    for cube, mapping in CUBES:
        got = figures(cube, mapping, {}, since, SWITZERLAND, want_vat=EXCL_VAT, origins=SWISS_ORIGIN)
        print(f'  {cube}: {len(got)} figures since {since}')
        figs.extend(got)
    if not figs:
        raise RuntimeError('BLW/LINDAS returned no producer prices: the cubes or the endpoint have changed')
    written, _ = replace('CH', SOURCE_NAME, 'farmgate', figs)
    replace('LI', SOURCE_NAME_LI, 'farmgate', for_liechtenstein(figs))
    return written


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--months', type=int, default=12)
    run(ap.parse_args().months)
