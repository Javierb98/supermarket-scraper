"""
The Austrian feed (heisse-preise.io) and the German shelf-name rules, on real
names from Billa's file of 4 November 2026.

    python -m unittest tests.test_heisse_preise
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import heisse_preise as hp
from pipeline import normalize, prices
from pipeline.matcher import Matcher

TODAY = date(2026, 11, 4)


def doc(*items):
    """A file in the project's compressed layout, from (name, cat, unavailable, history, unit, qty, weighted)."""
    dates = sorted({d for it in items for d, _ in it[3]})
    data = []
    for name, cat, unavailable, history, unit, qty, weighted in items:
        data += [0, 'id-' + name, name, cat, unavailable, len(history)]
        for d, p in history:
            data += [dates.index(d), p]
        data += [unit, qty, weighted, 0, 'slug']
    return {'stores': ['billa'], 'n': len(items), 'dates': dates, 'data': data}


class Feed(unittest.TestCase):
    def rows(self, *items):
        out, why = hp.rows(doc(*items), 'billa', TODAY)
        return {r['raw_name']: r for r in out}, why

    def test_pack_becomes_a_price_per_kilo_litre_dozen_and_piece(self):
        rows, _ = self.rows(
            ('Clever Tomaten', '01', 0, [('20261103', 2.69)], 'g', 1000, 0),
            ('Ja! Natürlich Lauch', '01', 0, [('20260701', 2.85)], 'g', 350, 0),
            ('Clever Vollmilch', '34', 0, [('20260701', 1.32)], 'ml', 1000, 0),
            ('BILLA Freilandeier M', '30', 0, [('20261001', 2.89)], 'stk', 10, 0),
            ('BILLA immer gut Avocado essreif 2 Stk.', '00', 0, [('20260612', 2.99)], 'stk', 2, 0),
        )
        self.assertEqual(rows['Clever Tomaten (1000 g)']['raw_price'], 'item=2.69;per_kg=2.69')
        self.assertEqual(rows['Ja! Natürlich Lauch (350 g)']['raw_price'], 'item=2.85;per_kg=8.1429')
        self.assertEqual(rows['Clever Vollmilch (1000 ml)']['raw_price'], 'item=1.32;per_l=1.32')
        self.assertEqual(rows['BILLA Freilandeier M (10 Stück)']['raw_price'], 'item=2.89;per_dozen=3.468')
        self.assertIn('per_unit=1.495', rows['BILLA immer gut Avocado essreif 2 Stk. (2 Stück)']['raw_price'])

    def test_unlisted_products_other_aisles_and_dried_fruit_are_left_out(self):
        rows, why = self.rows(
            ('Clever Tomaten getrocknet', '53', 0, [('20261103', 2.17)], 'g', 280, 0),
            ('Clever Apfel Rot', '00', 1, [('20260701', 2.18)], 'g', 1000, 1),
            ('Ja! Natürlich Datteln mit Stein', '05', 0, [('20260701', 2.99)], 'g', 500, 0),
            ('BILLA Bio Walnusskerne', '05', 0, [('20260701', 3.49)], 'g', 150, 0),
        )
        self.assertEqual(list(rows), ['BILLA Bio Walnusskerne (150 g)'])
        self.assertEqual((why['other aisle'], why['not listed any more'], why['dried fruit']), (1, 1, 1))

    def test_a_recent_steep_drop_is_an_offer_at_the_earlier_price(self):
        rows, _ = self.rows(
            ('Ja! Natürlich Lauch', '01', 0, [('20261101', 2.24), ('20261001', 2.99)], 'g', 350, 0),
            # Austria's food VAT cut of 1 July 2026: 5% down, months ago, not an offer.
            ('BILLA Genusswelt Dattelcherrytomaten', '01', 0, [('20260701', 3.32), ('20260614', 3.49)], 'g', 200, 0),
        )
        p = prices.read('BILLA (heisse-preise.io)', rows['Ja! Natürlich Lauch (350 g)']['raw_price'], '', 'Lauch (350 g)')
        self.assertTrue(p.promo)
        self.assertEqual(p.regular, 2.99)
        self.assertNotIn('regular', rows['BILLA Genusswelt Dattelcherrytomaten (200 g)']['raw_price'])

    def test_stale_chains_are_recognised(self):
        d = doc(('X', '01', 0, [('20260927', 1.0)], 'g', 100, 0))
        self.assertEqual(hp.newest(d), date(2026, 9, 27))


class GermanRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Matcher()

    def name(self, raw):
        p, how, _ = self.m.match(raw, 'de')
        return p['name'] if p and how in ('rule', 'catalog') else how

    def test_austrian_and_german_words(self):
        for raw, want in [
            ('Clever Tomaten (1000 g)', 'Tomato'),
            ('BILLA Genusswelt Dattelcherrytomaten (200 g)', 'Cherry Tomato'),
            ('Da komm ich her! Rispenparadeiser (1000 g)', 'Vine Tomatoes'),
            ('Clever Erdäpfel festkochend (5000 g)', 'Potato'),
            ('Pfanni Erdäpfel Speckig (2000 g)', 'Potato'),
            ('Karfiol (1 Stück)', 'Cauliflower'),
            ('Ja! Natürlich Bio Melanzani (2 Stück)', 'Eggplant'),
            ('Fisolen breit (500 g)', 'Green Beans'),
            ('Speisekürbis Butternuss (1000 g)', 'Butternut Squash'),
            ('Tante Fanny Jonagold Apfel Tasse (1000 g)', 'Apples'),
            ('Zespri Riesenkiwi grün (1 Stück)', 'Kiwi'),
            ('Ja! Natürlich Bio Eier L (10 Stück)', 'Organic Eggs L'),
            ('Clever Eier aus Bodenhaltung M (10 Stück)', 'Eggs'),
            ('Clever Rinderfaschiertes (500 g)', 'Ground Beef'),
            ('Clever Hendl -Innenfilets (350 g)', 'Chicken Breast'),
            ('Hofstädter Fair zum Tier Puten-Unterkeule (1000 g)', 'Turkey Legs'),
            ('BILLA Heumilch Teebutter (250 g)', 'Butter'),
            ('BILLA Heumilch Gouda (100 g)', 'Gouda Cheese'),
            ('Clever Vollmilch (1000 ml)', 'Whole Milk'),
            ('Clever Schlagobers länger frisch 32% (500 ml)', 'Cream'),
            ('Ja! Natürlich Rote Rüben (1000 g)', 'Beetroot'),
            ('Ja! Natürlich Bio Schnittlauch im Topf (1 Stück)', 'Chives'),
            ('Kiri mit Sahne (108 g)', 'Cream Cheese'),
        ]:
            self.assertEqual(self.name(raw), want, raw)

    def test_what_must_not_be_priced_as_fresh(self):
        for raw in ['Clever Tomaten getrocknet (280 g)', 'Machland Delikatessgurken (670 g)',
                    'Clever Ei-Zwiebel Aufstrich (200 g)', 'Mirinda Orange (500 ml)', 'Alpro Kids Erdbeere (460 g)',
                    'Ja! Natürlich Kürbiskerne Natur geröstet & gesalzen (200 g)']:
            status, _ = normalize.judge(self.m, {
                'chain': 'BILLA (heisse-preise.io)', 'raw_name': raw, 'country': 'AT',
                'raw_price': 'item=1.99;per_kg=9.95', 'raw_unit_price': None, 'shop_category': None})
            self.assertNotEqual(status, 'ok', raw)

    def test_known_products_the_catalogue_lacks_are_counted_not_priced(self):
        for raw in ['Häuptelsalat (1 Stück)', 'Clever Faschiertes gemischt (500 g)', 'nöm Speisetopfen 20% (250 g)',
                    'Ja! Natürlich Leichtmilch (1000 ml)']:
            self.assertEqual(self.name(raw), 'unlisted', raw)

    def test_a_whole_row_is_judged_and_priced(self):
        status, out = normalize.judge(self.m, {
            'chain': 'BILLA (heisse-preise.io)', 'raw_name': 'Clever Tomaten (1000 g)', 'country': 'AT',
            'raw_price': 'item=2.69;per_kg=2.69', 'raw_unit_price': None, 'shop_category': 'Obst & Gemüse > Gemüse'})
        self.assertEqual(status, 'ok')
        self.assertEqual((out['product']['name'], out['basis'], out['value']), ('Tomato', 'kg', 2.69))


if __name__ == '__main__':
    unittest.main()
