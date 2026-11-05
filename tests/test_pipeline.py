"""
The price readers, pack sizes, processed-food check and matcher, on real
shelf strings from the 2 November run.

    python -m unittest discover tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import prices, processed
from pipeline.pack import from_name
from pipeline.matcher import Matcher
from pipeline.market_average import trimmed, summarise
from pipeline.catalog import resolve


class Prices(unittest.TestCase):
    def test_mercadona_per_kilo_and_pack(self):
        p = prices.read('Mercadona', 'Ahora2.00€ | 1 KG A 2.000 € | unidad 4.32€ | 2.16 kg', '', 'Piña, Pieza')
        self.assertEqual(p.item, 4.32)
        self.assertEqual(p.basis(), ('kg', 2.0))

    def test_mercadona_hundred_grams(self):
        p = prices.read('Mercadona', 'Ahora77.50€ | 1 100 G A 7.750 € | unidad 1.55€ | 0.02 kg', '', 'Albahaca, Bandeja')
        self.assertEqual(p.per['kg'], 77.5)

    def test_mercadona_eggs_by_the_dozen(self):
        p = prices.read('Mercadona', 'Ahora0.36€ | 1 DC A 4.300 € | unidad 4.30€ | 12.0 ud', '', 'Huevos grandes L')
        self.assertEqual(p.basis(), ('dozen', 4.3))

    def test_mercadona_piece_with_weight_gets_a_kilo_price(self):
        p = prices.read('Mercadona', 'Ahora4.00€ | 1 UD A 4.000 € | 0.366 kg', '', 'Queso fresco, Pieza')
        self.assertAlmostEqual(p.per['kg'], 10.929, places=2)

    def test_consum_price_per_kilo_is_read(self):
        # The old parser ignored this column: every Consum price was "per item".
        p = prices.read('Consum', '2.99 €', '6.5 €/1 Kg', 'Activia 0% Muesli')
        self.assertEqual(p.basis(), ('kg', 6.5))
        self.assertEqual(prices.read('Consum', '1.20 €', '12 €/100 Gr', 'Eneldo').per['kg'], 120.0)

    def test_eroski_offer_is_flagged_with_its_regular_price(self):
        p = prices.read('Eroski', '1 KILO A  5,96 € | -6% | 1,60€AntesAhora1,49€ | 1,60€Antes | 1,60 | € | Ahora1,49€ | 1,49 | €',
                        '', 'Tomate cherry pera, vaso 250 g')
        self.assertTrue(p.promo)
        self.assertEqual((p.item, p.regular), (1.49, 1.60))
        self.assertEqual(p.per['kg'], 5.96)

    def test_structured_prices_from_new_sources(self):
        p = prices.read('REWE', 'item=2.49;per_kg=4.98;regular=2.99', '', 'Tomaten 500 g')
        self.assertEqual(p.basis(), ('kg', 4.98))
        self.assertTrue(p.promo)

    def test_number_formats(self):
        self.assertEqual(prices.num('1.234,56'), 1234.56)
        self.assertEqual(prices.num('1,234.56'), 1234.56)
        self.assertEqual(prices.num('2,50'), 2.5)


class Packs(unittest.TestCase):
    def test_sizes_from_names(self):
        self.assertEqual(from_name('Tomate cherry pera, vaso 250 g').kg, 0.25)
        self.assertEqual(from_name('Patata para freír EROSKI NATUR, malla 2 kg').kg, 2)
        self.assertEqual(from_name('Leche entera, pack 6 x 1 l').litres, 6)
        self.assertEqual(from_name('Kiwi, bandeja 4 x 100 g').kg, 0.4)
        self.assertEqual(from_name('Huevos camperos, 12 uds').count, 12)
        self.assertEqual(from_name('Media docena de huevos').count, 6)
        self.assertEqual(from_name('Coco, unidad').count, 1)
        self.assertIsNone(from_name('Calabacín'))


class Processed(unittest.TestCase):
    def test_processed_and_non_food_are_caught(self):
        for name in ['Gel Dental 2 a 6 Años Sabor Fresa', 'Papilla pera y manzana Hacendado +4 meses',
                     'Bífidus con kiwi probióticos Hacendado', 'Cebolla Crujiente Paquete',
                     'Ensalada completa mixta con huevo FLORETTE, bowl 230 g', 'Patatas Sabor Jamón Bolsa']:
            self.assertIsNotNone(processed.why_processed(name, 'es'), name)

    def test_fresh_produce_is_not(self):
        for name in ['Manzana Granny Smith, Pieza', 'Tomate ensalada, al peso', 'Fresas, Tarrina', 'Cebollas, Malla']:
            self.assertIsNone(processed.why_processed(name, 'es'), name)

    def test_the_shops_aisle(self):
        self.assertTrue(processed.aisle_is_fresh('Cebollas, ajos y puerros'))
        self.assertFalse(processed.aisle_is_fresh('Fruta congelada'))
        self.assertFalse(processed.aisle_is_fresh('Patatas fritas'))
        self.assertIsNone(processed.aisle_is_fresh(None))


class Matching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Matcher()

    def name(self, raw):
        p, how, _ = self.m.match(raw, 'es')
        return p['name'] if p else how

    def test_rules_point_at_catalogue_products(self):
        self.assertEqual(self.name('Manzana Granny Smith, Pieza'), 'Apples')
        self.assertEqual(self.name('Tomate pera, al peso'), 'Plum Tomatoes')
        self.assertEqual(self.name('Pechugas de pollo, Bandeja'), 'Chicken Breast')
        self.assertEqual(self.name('Judía verde plana, malla 500 g'), 'Green Beans')

    def test_setas_are_oyster_mushrooms(self):
        self.assertEqual(self.name('Setas, Bandeja'), 'Oyster Mushroom')
        self.assertEqual(self.name('Champiñón laminado, Bandeja'), 'White Mushroom')

    def test_the_product_must_lead(self):
        self.assertEqual(self.name('Escalivada con Cebolla Bandeja'), 'not_lead')
        self.assertEqual(self.name('Paté de Pato C/Cebolla Caramelizada'), 'not_lead')

    def test_catalogue_names_are_a_fallback(self):
        self.assertEqual(self.name('Kiwis verdes, Bandeja'), 'Kiwi')

    def test_feeds_use_catalogue_names(self):
        self.assertEqual(resolve('Potatoes')[0], 'Potato')
        self.assertEqual(resolve('Salmon'), ('Salmon', None))


class Averages(unittest.TestCase):
    def row(self, raw, kg, chain='Mercadona', region='Navarra', promo=False, regular=None, price=1.0):
        return {'canonical_name': 'Apples', 'catalog_product_id': 24, 'category': 'fruit', 'currency': 'EUR',
                'chain': chain, 'raw_name': raw, 'region': region, 'price': price, 'is_promo': promo,
                'regular_price': regular, 'per_kg': kg, 'per_l': None, 'per_dozen': None, 'per_unit': None}

    def test_a_product_counts_once_however_many_shops(self):
        rows = [self.row('Manzana roja', 2.0, region=r) for r in ['Navarra', 'Madrid', 'Galicia']]
        rows.append(self.row('Manzana golden', 3.0, chain='Consum', region=None))
        national = summarise(rows)[('Apples', 'kg', None)]
        self.assertEqual(national['n'], 2)
        self.assertEqual(national['median'], 2.5)

    def test_an_offer_counts_at_its_regular_price(self):
        rows = [self.row('Manzana', 1.5, promo=True, regular=2.0, price=1.5)]
        self.assertEqual(summarise(rows)[('Apples', 'kg', None)]['median'], 2.0)

    def test_far_outliers_are_left_out(self):
        self.assertNotIn(40.0, trimmed([2.0, 2.2, 2.4, 2.5, 2.6, 40.0]))


if __name__ == '__main__':
    unittest.main()
