"""
Write data/catalog.json from Evocultiva's product catalogue.

Every price the scraper keeps is a price *for a product on the website*: the
site compares a farm's "Tomato" against the market's "Tomato" by name. A
canonical name the catalogue does not have is a price no farm can ever be
compared with. Half the old rules produced exactly that ("Red Apple",
"Chicken", "Iceberg Lettuce"), and the prices went nowhere.

So the catalogue is the target list, and this file is its copy on the Pi,
which has no access to the website's database. The names in other languages
seed the matching for the countries that speak them.

    EVO_DB_HOST=127.0.0.1 EVO_DB_PORT=3309 EVO_DB_USER=... EVO_DB_PASSWORD=... \
        python tools/export_catalog.py

Run it again when the catalogue changes, and commit the result.
"""

import json
import os
import sys

import pymysql

LANGS = ['es', 'fr', 'eu', 'de', 'pt', 'it']
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'catalog.json')


def main():
    conn = pymysql.connect(
        host=os.environ.get('EVO_DB_HOST', '127.0.0.1'),
        port=int(os.environ.get('EVO_DB_PORT', 3309)),
        user=os.environ['EVO_DB_USER'],
        password=os.environ['EVO_DB_PASSWORD'],
        database=os.environ.get('EVO_DB_NAME', 'Evocultiva-org'),
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor,
    )
    cols = ', '.join(f'product_name_{l}' for l in LANGS)
    with conn.cursor() as c:
        c.execute(f'SELECT id, product_name, product_category, pricing_method, {cols} FROM farm_product_categories ORDER BY id')
        rows = c.fetchall()
    conn.close()

    products = []
    for r in rows:
        names = {'en': r['product_name'].strip()}
        for l in LANGS:
            v = (r[f'product_name_{l}'] or '').strip()
            if v:
                names[l] = v
        products.append({
            'id': r['id'],
            'name': names['en'],
            'category': r['product_category'],
            'pricing': r['pricing_method'],
            'names': names,
        })

    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(products, f, ensure_ascii=False, indent=1)
    print(f'{len(products)} products written to {OUT}', file=sys.stderr)


if __name__ == '__main__':
    main()
