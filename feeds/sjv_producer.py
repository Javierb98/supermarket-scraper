"""
Sweden: what farmers are paid, from Jordbruksverket (the Swedish Board of
Agriculture), table JO1001L2 "Avräkningspriser, månad".

Official statistics, monthly since 2015, national, through the board's
PxWeb API without a key. A settlement price (avräkningspris) is what the
buyer — dairy, packer, wholesaler — pays the producer, so these are
`farmgate` figures: shown to the farmer, labelled, never used for badges.

The table is in kronor per 100 kg, except eggs (öre per egg). Converted:

    vegetables, fruit, potatoes   kr/100 kg ÷ 100          → SEK per kg
    milk (weighed in, actual fat) kr/100 kg ÷ 100 × 1.03   → SEK per litre (a litre of milk weighs 1.03 kg)
    eggs (64 g, öre each)         öre × 12 ÷ 100           → SEK per dozen

Slaughter prices (kr/100 kg carcass) are left out: a carcass is not the
cut a farm sells. White cabbage is left out too — the catalogue has no plain
cabbage.

Each product's latest month with a figure, within the last six, is stored
for that month. Seasonal produce (strawberries, cauliflower) has gaps.

    python feeds/sjv_producer.py
"""

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, write, get_json

API = ('https://statistik.sjv.se/PXWeb/api/v1/sv/Jordbruksverkets%20statistikdatabas/'
       'Priser%20och%20prisindex/Priser/Avrakningspriser20/JO1001L2.px')
SOURCE_NAME = 'Jordbruksverket, avräkningspriser (JO1001L2)'
MONTHS = 6
MILK_KG_PER_LITRE = 1.03

# table code → (catalogue name, unit, factor from the table's figure)
PRODUCTS = {
    '13': ('Cauliflower',  'kg',    0.01),
    '14': ('Tomato',       'kg',    0.01),     # greenhouse, 1st quality
    '16': ('Cucumber',     'kg',    0.01),     # greenhouse, 1st quality
    '17': ('Carrot',       'kg',    0.01),
    '18': ('Onion',        'kg',    0.01),
    '19': ('Potato',       'kg',    0.01),     # table potatoes
    '21': ('Apples',       'kg',    0.01),
    '22': ('Strawberries', 'kg',    0.01),     # field-grown
    '36': ('Raw Cow Milk', 'l',     0.01 * MILK_KG_PER_LITRE),
    '41': ('Eggs',         'dozen', 0.12),     # öre per egg → kr per dozen
}


def latest(dataset):
    """json-stat2 → {code: (period 'YYYYMmm', value)} with each code's newest figure."""
    dims = dataset['id']
    prod = dataset['dimension'][dims[0]]['category']['index']
    cat = dataset['dimension'][dims[1]]['category']
    month = cat['index']
    n_months = len(month)
    # The keys are the table's positions ("139"); the labels say the month.
    by_pos = {v: cat.get('label', {}).get(k, k) for k, v in month.items()}
    out = {}
    for code, i in prod.items():
        for j in sorted(by_pos, reverse=True):
            v = dataset['value'][i * n_months + j]
            if v is not None:
                out[code] = (by_pos[j], float(v))
                break
    return out


def run():
    query = {
        'query': [
            {'code': 'Produkter', 'selection': {'filter': 'item', 'values': sorted(PRODUCTS)}},
            {'code': 'Månad', 'selection': {'filter': 'top', 'values': [str(MONTHS)]}},
        ],
        'response': {'format': 'json-stat2'},
    }
    figures = []
    for code, (period, value) in latest(get_json(API, data=query)).items():
        name, unit, factor = PRODUCTS[code]
        snapshot = date(int(period[:4]), int(period[5:7]), 1)
        figures.append(Figure(name, round(value * factor, 4), unit, snapshot))
        print(f'  {name:14} {value * factor:8.2f} SEK/{unit:5} {period}')

    if not figures:
        raise RuntimeError('Jordbruksverket returned nothing — the table or the API has changed')
    return write('SE', SOURCE_NAME, 'farmgate', figures)


if __name__ == '__main__':
    run()
