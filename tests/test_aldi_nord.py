"""
The ALDI Nord feed, offline: reading a category page and turning its
products into structured shelf prices.

    python -m unittest tests.test_aldi_nord
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import aldi_nord as an


def hit(name, unit, price, base=None, strike=None, oid='1', **kw):
    cp = {'priceValue': price}
    if base:
        cp['basePrice'] = [{'basePriceValue': base[0], 'basePriceScale': base[1]}]
    if strike:
        cp['strikePrice'] = {'strikePriceValue': strike}
    h = {'objectID': oid, 'name': name, 'salesUnit': unit, 'currentPrice': cp, 'productSlug': f'x-{oid}',
         'isAvailable': True, 'isRecall': False}
    h.update(kw)
    return h


def page(hits):
    data = {'props': {'pageProps': {'algoliaState': {'initialResults': {'an_prd_de_de_products2': {
        'results': [{'hits': hits, 'index': 'an_prd_de_de_products2', 'nbHits': len(hits)}]}}}}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></html>'


class Structured(unittest.TestCase):
    def test_pack_with_base_price_and_offer(self):
        self.assertEqual(an.structured(hit('Rispentomaten', '650-g-Schale', 1.69, (2.6, 'kg'), 2.19)),
                         'item=1.69;per_kg=2.6;regular=2.19')

    def test_sold_by_the_kilo(self):
        self.assertEqual(an.structured(hit('Chinakohl', 'kg-Preis', 1.11, (1.11, 'kg'))), 'item=1.11;per_kg=1.11')

    def test_by_the_piece_and_bunch(self):
        self.assertEqual(an.structured(hit('Gurke', 'Stück', 0.79)), 'item=0.79;per_unit=0.79')
        self.assertEqual(an.structured(hit('Dill', 'Bund', 1.19)), 'item=1.19;per_unit=1.19')

    def test_eggs_per_dozen(self):
        self.assertEqual(an.structured(hit('Eier aus Freilandhaltung', '10-Stück-Packung', 2.99, (0.3, 'Stück'))),
                         'item=2.99;per_dozen=3.588')

    def test_count_pack(self):
        self.assertEqual(an.structured(hit('Mangos', '2er-Schale', 2.49)), 'item=2.49;per_unit=1.245')

    def test_litre(self):
        self.assertEqual(an.structured(hit('Frische Vollmilch', '1-L-Packung', 0.95, (0.95, 'l'))),
                         'item=0.95;per_l=0.95')

    def test_nothing_to_go_by(self):
        self.assertIsNone(an.structured(hit('Schnitzel', 'Packung', 3.99)))
        self.assertIsNone(an.structured(hit('Gurke', 'Stück', 0)))


class Page(unittest.TestCase):
    def test_hits_and_rows(self):
        html = page([hit('Avocados', '500-g-Netz', 1.59, (3.18, 'kg'), 1.79, oid='7430'),
                     hit('Avocados', '500-g-Netz', 1.59, (3.18, 'kg'), 1.79, oid='7430'),       # listed twice
                     hit('Kaki', 'Stück', 0.49, oid='9', isAvailable=False)])
        hs = an.hits(html)
        self.assertEqual(len(hs), 3)
        rows = an.rows([('Obst & Gemüse > Frisch', hs)])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['raw_name'], 'Avocados (500-g-Netz)')
        self.assertEqual(rows[0]['url'], 'https://www.aldi-nord.de/produkt/x-7430.html')
        self.assertEqual(an.hits('<html></html>'), [])


class Matching(unittest.TestCase):
    """The German rules on ALDI Nord's own shelf names."""

    def test_names(self):
        from pipeline.matcher import Matcher
        m = Matcher()
        expect = {
            'Deutsches Brathähnchen (1,4-kg-Stück)': 'Whole Chicken',
            'Frische Bio-Milch (1-L-Packung)': 'Whole Milk',
            'Tafeltrauben dunkel (400-g-Schale)': 'Grapes Red',
            'Kleine Speisekartoffeln „Drillinge“ (1-kg-Schale)': 'Mini Potatoes',
            'Back- & Grillkartoffeln (2-kg-Beutel)': 'Potato',
            'Speisemöhren (1-kg-Beutel)': 'Carrot',
            'Körniger Frischkäse (200-g-Becher)': 'Fresh Cottage Cheese',
        }
        for raw, name in expect.items():
            p, how, _ = m.match(raw, 'de')
            self.assertEqual(p and p['name'], name, raw)
        p, how, _ = m.match('Käse-Krainer (300-g-Packung)', 'de')
        self.assertIsNone(p)
        p, how, _ = m.match('Fettarme Frischmilch (1-L-Packung)', 'de')
        self.assertIsNone(p)


if __name__ == '__main__':
    unittest.main()
