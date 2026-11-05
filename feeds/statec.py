"""
Luxembourg: STATEC's average prices of basic products, measured each June.

STATEC (the national statistics office) publishes, once a year, the average
shop price in June of about twenty everyday things, seven of them food a
farm sells: apples, bananas, butter, eggs, milk, potatoes and pork chops.
It is dataflow DF_E5300 on LUSTAT, read through its open SDMX API without a
key. STATEC's data is published as open data under CC0
(data.public.lu, organisation STATEC).

Few products and once a year, but it is Luxembourg's own price: the country
otherwise borrows Belgium's or France's.

    COMMON_PRODUCT   what it is              → catalogue product, per
    APP              Apples (1 kg)           → Apples, kg
    BAN              Fresh bananas (1 kg)    → Banana, kg
    BUTT             Butter (250 g)          → Butter, kg   (× 4)
    EGGS             Eggs (a dozen)          → Eggs, dozen
    MILK             Fresh milk (1 l)        → Whole Milk, l   (as StatCan's "Milk")
    POT              Potatoes (5 kg)         → Potato, kg   (÷ 5)
    PORC             Pork chop (1 kg)        → Pork Chops, kg

The rest (bread, flour, sugar, coffee, water, croissants, fuel, tickets,
doctors) are not things a farm sells, or not as the same product.

    python feeds/statec.py
"""

import csv
import io
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, get, write

URL = 'https://lustat.statec.lu/rest/data/LU1,DSD_PRIX_PRODUIT@DF_E5300,1.0/all?startPeriod={start}'
SOURCE_NAME = 'STATEC, average prices of basic products (June)'

# code → (catalogue name, unit, what the published price is divided by)
PRODUCTS = {
    'APP': ('Apples', 'kg', 1),
    'BAN': ('Banana', 'kg', 1),
    'BUTT': ('Butter', 'kg', 0.25),
    'EGGS': ('Eggs', 'dozen', 1),
    'MILK': ('Whole Milk', 'l', 1),
    'POT': ('Potato', 'kg', 5),
    'PORC': ('Pork Chops', 'kg', 1),
}


def parse(text):
    """SDMX-CSV → {(code, year): price}."""
    out = {}
    reader = csv.DictReader(io.StringIO(text))
    for row in reader:
        code = (row.get('COMMON_PRODUCT') or '').split(':')[0].strip()
        year = (row.get('TIME_PERIOD') or '').strip()
        value = (row.get('OBS_VALUE') or '').strip()
        if code in PRODUCTS and year.isdigit() and value:
            out[(code, int(year))] = float(value)
    return out


def figures(values):
    """The latest year of each product → Figures, dated 1 June of that year."""
    latest = {}
    for (code, year), price in values.items():
        if year > latest.get(code, (0, None))[0]:
            latest[code] = (year, price)
    out = []
    for code, (year, price) in sorted(latest.items()):
        name, unit, per = PRODUCTS[code]
        out.append(Figure(name, round(price / per, 4), unit, date(year, 6, 1)))
    return out


def main():
    start = date.today().year - 3
    text = get(URL.format(start=start), headers={'Accept': 'application/vnd.sdmx.data+csv;version=1.0.0'}).decode('utf-8')
    found = figures(parse(text))
    if not found:
        raise SystemExit('STATEC: no figures in the response')
    write('LU', SOURCE_NAME, 'retail', found)


if __name__ == '__main__':
    main()
