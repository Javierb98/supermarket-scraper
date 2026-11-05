"""
The Netherlands (checkjebon.nl + the Dutch rules) and Luxembourg (STATEC),
on real names and figures from the 4 November 2026 files.

    python -m unittest tests.test_benelux
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import prices
from pipeline.matcher import Matcher
from pipeline.normalize import judge
from feeds import checkjebon, statec

M = Matcher()


def match(name):
    p, how, label = M.match(name, 'nl')
    return p['name'] if p else (label if how == 'unlisted' else None)


def judged(chain, name, price, size):
    raw = checkjebon.raw_name(name, size)
    rp = checkjebon.structured(name, price, size)
    return judge(M, {'raw_name': raw, 'country': 'NL', 'chain': chain, 'raw_price': rp, 'raw_unit_price': ''})


class DutchRules(unittest.TestCase):
    def test_fresh_products_after_the_shops_own_brand(self):
        for name, want in [
            ('AH Tomaten, 500 g', 'Tomato'),
            ('Hoogvliet Trostomaten, 500 gram', 'Vine Tomatoes'),
            ('AH Cherrytomaten, 250 g', 'Cherry Tomato'),
            ('Roma tomaten, 750 g', 'Plum Tomatoes'),
            ('AH Witte champignons, 400 g', 'White Mushroom'),
            ('AH Oesterzwammen, 150 g', 'Oyster Mushroom'),
            ("1 de Beste Aardappelen vastkokend, 3 kg", 'Potato'),
            ("G'woon Rode uien, 1 kg", 'Red Onion'),
            ('AH Gele uien, 1 kg', 'Onion'),
            ('AH Scharreleieren, 12 stuks', 'Eggs'),
            ('AH Volle melk, 1 l', 'Whole Milk'),
            ('Jumbo Kipfilet 800 g', 'Chicken Breast'),
            ('PLUS Rundergehakt, Per 500 g', 'Ground Beef'),
            ('AH Roomboter ongezouten, 250 g', 'Butter'),
            ('Melkan Kaasstuk Goudse jong 48+, 960 gram', 'Gouda Cheese'),
            ('PLUS Handappels Jonagold, Per 1000 gram', 'Apples'),
            ('Hollandse Conference peren, 1 kg (ca. 5 stuks)', 'Pears'),
            ('AH Paprika rood, per stuk', 'Bell Pepper'),
            ('Jumbo Aardappelen Zoet 1 kg', 'Sweet Potato'),
        ]:
            self.assertEqual(match(name), want, name)

    def test_other_brands_and_prepared_food_are_not_the_fresh_product(self):
        for name in [
            'Heinz Tomaten ketchup, 1170 ml',
            'Wahid Kipfilet, 125 g',                 # sliced halal chicken
            'Aardappel Anders Bacon - ui, 390 ml',   # a sauce called "Aardappel Anders"
            'AH Ananassap, 1 l',
            'AH Champignons gesneden, 250 g',
            'Aviko Aardappelkroketjes, 750 g',
            'AH Ananas, 150 g',                      # cut pineapple
            'AH Ananas appel druif, 150 g',          # a fruit cup
            'Jumbo Galiameloen 150 g',
            'AH Scharrel kipfilet pittig, 125 g',
            'AH Roomboter spritsen, 250 g',
            "Gouda's Glorie Volle pond, 500 g",
            'Pruimen zonder pit ready to eat, 250 g',
            'AH Spinazie à la crème, 750 g',
            'Jumbo Rode Kool 350 g',
            'Lay\'s Paprika, 200 g',
        ]:
            self.assertIsNone(match(name), name)

    def test_products_the_catalogue_does_not_have_are_held_back(self):
        self.assertEqual(M.match('AH Biologisch Scharreleieren, 6 stuks', 'nl')[1], 'unlisted')
        self.assertEqual(M.match('eieren vrije uitloop m/l, 6 Stuks', 'nl')[1], 'unlisted')
        self.assertEqual(M.match('AH Halfvolle melk, 1 l', 'nl')[1], 'unlisted')
        self.assertEqual(M.match('AH Puntpaprika rood, per stuk', 'nl')[1], 'unlisted')
        self.assertEqual(M.match('AH Rode bieten, 340 g', 'nl')[1], 'unlisted')   # cooked

    def test_kerstomaten_is_not_christmas(self):
        self.assertEqual(match('Kerstomaten, 250 g'), 'Cherry Tomato')


class Checkjebon(unittest.TestCase):
    def test_sizes(self):
        self.assertEqual(checkjebon.parse_size('500 g'), (0.5, None, None))
        self.assertEqual(checkjebon.parse_size('Per 464 g'), (0.464, None, None))
        self.assertEqual(checkjebon.parse_size('1,5 liter'), (None, 1.5, None))
        self.assertEqual(checkjebon.parse_size('12 stuks'), (None, None, 12))
        self.assertEqual(checkjebon.parse_size('per stuk'), (None, None, 1))
        self.assertEqual(checkjebon.parse_size('1 kg (ca. 4 stuks)'), (1.0, None, None))
        self.assertEqual(checkjebon.parse_size('ca. 400 g'), (0.4, None, None))
        kg, l, n = checkjebon.parse_size('3 x 100 g')
        self.assertAlmostEqual(kg, 0.3)
        self.assertEqual(checkjebon.parse_size('los per kilo'), (1.0, None, None))
        self.assertEqual(checkjebon.parse_size('Tros'), (None, None, None))

    def test_structured_price_reads_back(self):
        rp = checkjebon.structured('AH Tomaten', 1.55, '500 g')
        self.assertEqual(rp, 'item=1.55;per_kg=3.1000')
        self.assertEqual(prices.read('AH', rp, '', 'AH Tomaten, 500 g').basis(), ('kg', 3.1))

    def test_eggs_by_the_dozen(self):
        self.assertEqual(checkjebon.structured('AH Scharreleieren', 3.19, '12 stuks'), 'item=3.19;per_dozen=3.1900')
        status, out = judged('AH', 'AH Verse scharreleieren M L', 4.67, '10 stuks')
        self.assertEqual(status, 'ok')
        self.assertEqual((out['basis'], round(out['value'], 2)), ('dozen', 5.6))

    def test_size_in_the_name_when_the_field_is_empty(self):
        status, out = judged('Jumbo', 'Jumbo Kipfilet 800 g', 9.59, '')
        self.assertEqual((status, out['basis']), ('ok', 'kg'))
        self.assertAlmostEqual(out['value'], 11.99, places=2)

    def test_two_sizes_of_one_product_are_two_rows(self):
        self.assertNotEqual(checkjebon.raw_name('AH Aardappelen voor de stamppot', '600 g'),
                            checkjebon.raw_name('AH Aardappelen voor de stamppot', '1 kg'))
        self.assertEqual(checkjebon.raw_name('Jumbo Kipfilet 800 g', '800 g'), 'Jumbo Kipfilet 800 g')

    def test_lidl_and_bad_prices_are_left_out(self):
        data = [
            {'n': 'lidl', 'c': 'Lidl', 'u': '', 'd': [{'n': 'Tomaten', 'p': 1.69, 's': '1000 g', 'l': '1'}]},
            {'n': 'ah', 'c': 'AH', 'u': 'https://www.ah.nl/producten/product/', 'd': [
                {'n': 'AH Tomaten', 'p': 1.55, 's': '500 g', 'l': 'wi4088/ah-tomaten'},
                {'n': 'AH Tomaten', 'p': 0.01, 's': '500 g', 'l': 'x'},
                {'n': 'AH Shampoo', 'p': 3.0, 's': '250 ml', 'l': 'y'},
            ]},
        ]
        rows, seen = checkjebon.rows(data, M)
        self.assertEqual(rows, [('AH', 'AH Tomaten, 500 g', 'item=1.55;per_kg=3.1000',
                                 'https://www.ah.nl/producten/product/wi4088/ah-tomaten')])


STATEC_CSV = """DATAFLOW,MEASURE,UNIT_MEASURE,FREQ,MOTOR_ENERGY,COMMON_PRODUCT,BASE_PERIOD,TIME_PERIOD,OBS_VALUE
LU1:DSD_PRIX_PRODUIT@DF_E5300(1.0),PRIX_P,EUR,A,_Z,POT,_Z,2025,11.02
LU1:DSD_PRIX_PRODUIT@DF_E5300(1.0),PRIX_P,EUR,A,_Z,POT,_Z,2026,10.87
LU1:DSD_PRIX_PRODUIT@DF_E5300(1.0),PRIX_P,EUR,A,_Z,BUTT,_Z,2026,3.67
LU1:DSD_PRIX_PRODUIT@DF_E5300(1.0),PRIX_P,EUR,A,_Z,EGGS,_Z,2026,4.64
LU1:DSD_PRIX_PRODUIT@DF_E5300(1.0),PRIX_P,EUR,A,_Z,MOVIE,_Z,2026,13.3
LU1:DSD_PRIX_PRODUIT@DF_E5300(1.0),PRIX_P,EUR,A,_Z,TICKET,_Z,2026,
"""


class Statec(unittest.TestCase):
    def test_latest_year_per_kilo_and_dozen(self):
        got = {(f.name, f.unit): (f.price, f.snapshot.isoformat()) for f in statec.figures(statec.parse(STATEC_CSV))}
        self.assertEqual(got, {
            ('Potato', 'kg'): (2.174, '2026-06-01'),
            ('Butter', 'kg'): (14.68, '2026-06-01'),
            ('Eggs', 'dozen'): (4.64, '2026-06-01'),
        })

    def test_every_product_is_in_the_catalogue(self):
        for name, unit, _ in statec.PRODUCTS.values():
            self.assertIsNotNone(M.product(name), name)


if __name__ == '__main__':
    unittest.main()
