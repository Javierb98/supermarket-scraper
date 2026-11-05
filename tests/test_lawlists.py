"""
Croatian, Serbian and Greek rules and the law-list feeds' price handling,
on real shelf names from the 4 November 2026 lists.

    python -m unittest tests.test_lawlists
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline.matcher import Matcher
from pipeline import prices
from feeds import lawlists
from feeds.cijene_hr import qty_is_one

M = Matcher()


def name(raw, lang):
    p, how, _ = M.match(raw, lang)
    return p['name'] if p and how in ('rule', 'catalog') else None


class Croatian(unittest.TestCase):
    def test_fresh(self):
        for raw, want in [('RAJČICA GRAPPOLO', 'Vine Tomatoes'), ('JABUKA ZLATNI DELIŠES', 'Apples'),
                          ('KRUMPIR 2,5 kg', 'Potato'), ('JAJA L 10/1 LUNETA', 'Eggs'),
                          ('PILEĆI ZABATAK RINFUZO', 'Chicken Thigh'), ('MLIJEKO SVJ.3,2% 1l DUKAT', 'Whole Milk'),
                          ('LUK LJUBIČASTI', 'Red Onion'), ('CESNJAK kg', 'Garlic'), ('Svježi sir', 'Fresh Cottage Cheese')]:
            self.assertEqual(name(raw, 'hr'), want, raw)

    def test_not_fresh(self):
        for raw in ['RAJČICA PASIR 200 g PODRAVKA', 'KRUMPIR KROKETI 1 KG LEDO', 'USKRŠNJA DEKOR JAJA 8 cm',
                    'KRUŠKOVAC 0,70 L', 'ZAČIN BOSILJAK KOTANYI 15 g', 'JOGURT FORTIA JAGODA 330 G',
                    'MASLAC ZA TIJELO 250ml', 'HOBBY VIT HRANA ZA KUNIĆE 500 g']:
            self.assertIsNone(name(raw, 'hr'), raw)


class Serbian(unittest.TestCase):
    def test_latin_and_cyrillic(self):
        self.assertEqual(name('PARADAJZ ŠLJIVAR', 'sr'), 'Plum Tomatoes')
        self.assertEqual(name('Sargarepa domaca', 'sr'), 'Carrot')
        self.assertEqual(name('ПАРАДАЈЗ', 'sr'), 'Tomato')
        self.assertEqual(name('КРОМПИР ЦРВЕНИ', 'sr'), 'Potato')
        self.assertEqual(name('SVEZE MESO PILECE GRUDI RF CEKIN', 'sr'), 'Chicken Breast')

    def test_not_fresh(self):
        for raw in ['Paprika u pavlaci Meggle casa 400g', 'SIR MLEKOPRODUKT BISER GAUDA PUNOMASNI 45% 250G',
                    'KOBASICA ČAJNA SLAJS XXL 170G ND']:
            self.assertNotIn(name(raw, 'sr'), ('Bell Pepper', 'Whole Milk', 'Cheese'), raw)


class Greek(unittest.TestCase):
    def test_accents_and_case(self):
        self.assertEqual(name('Φρέσκο Γάλα Πλήρες 3,5% Λιπαρά 1lt', 'el'), 'Whole Milk')
        self.assertEqual(name('ΦΡΕΣΚΟ ΓΑΛΑ ΠΛΗΡΕΣ 3,5% 1LT', 'el'), 'Whole Milk')
        self.assertEqual(name('Φιλέτο Στήθος Κοτόπουλου Ελληνικό 700g', 'el'), 'Chicken Breast')
        self.assertEqual(name('Αυγά Αχυρώνα Large 10 Τεμάχια 63/73g', 'el'), 'Eggs')
        self.assertIsNone(name('Κοτόπουλο Σνίτσελ 470g', 'el'))


class Prices(unittest.TestCase):
    def test_eggs_by_the_dozen(self):
        p = {'category': 'eggs'}
        self.assertAlmostEqual(lawlists.per_basis(p, 'JAJA M 10/1', 3.0)['dozen'], 3.6)
        self.assertEqual(lawlists.egg_count('Jaja razred M, klasa A, 30 komada'), 30)

    def test_weighed_and_packed(self):
        veg = {'category': 'vegetables'}
        self.assertEqual(lawlists.per_basis(veg, 'RAJČICA', 2.25, sold_by_kg=True), {'kg': 2.25})
        self.assertEqual(lawlists.per_basis(veg, 'KRUMPIR 5 kg', 3.49, sold_by_kg=True), {})   # reader uses the 5 kg
        self.assertEqual(lawlists.per_basis(veg, 'Paprika ljuta komad', 22.99, sold_by_kg=True), {'unit': 22.99})
        raw = lawlists.structured(3.49, {})
        self.assertAlmostEqual(prices.read('Konzum', raw, None, 'KRUMPIR 5 kg').basis()[1], 0.698)

    def test_quantity_column(self):
        self.assertTrue(qty_is_one('1,0000'))
        self.assertTrue(qty_is_one('1000 g'))
        self.assertFalse(qty_is_one('0.500 kg'))


if __name__ == '__main__':
    unittest.main()
