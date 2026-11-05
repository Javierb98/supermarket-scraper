"""
Norway, Sweden and Estonia: the shelf-name rules, the shop price readers and
the official tables, on real names and payloads from November 2026.

    python -m unittest tests.test_nordic
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline import prices
from pipeline.matcher import Matcher, detect_state, check_fresh
from feeds import oda, selver, sjv_producer

M = Matcher()


def priced(name, lang):
    """The catalogue product a shelf name prices, or None."""
    p, how, _ = M.match(name, lang)
    if p is None:
        return None
    if check_fresh(p, name, lang, detect_state(name, lang)):
        return None
    return p['name']


class Norwegian(unittest.TestCase):
    def test_produce(self):
        for name, want in [
            ('Tomater klase, Norge Mijøgartneriet, 500 g', 'Vine Tomatoes'),
            ('Tomater Vår Laveste Pris, Nederland / Polen', 'Tomato'),
            ('Cherrytomater Vår Laveste Pris, Nederland/ Spania', 'Cherry Tomato'),
            ('Agurk Norge, Norge, 1 stk', 'Cucumber'),
            ('Liten Agurk Vår laveste pris Klasse 2, Norge, 1 stk', 'Cucumber'),
            ('Økologisk Agurk Nederland / Spania, 1 stk', 'Cucumber'),
            ('Aubergine Spania / Nederland, 1 stk', 'Eggplant'),
            ('Rødløk, Norge, 500 g', 'Red Onion'),
        ]:
            self.assertEqual(priced(name, 'no'), want, name)

    def test_processed_is_turned_away(self):
        for name in [
            'Sylteagurker, 490 g', 'Agurk i staver, 80 g', 'Grovhakkede tomater, 400 g',
            'Makrell i tomat, 80 g', 'Tomatpuré, 140 g', 'Suppe med tomat, squash og basilikum, 530 g',
            'Eggesalat, 180 g', 'Eggnudler, 250 g', 'Flytende eggehvite, 500 g',
            'Laktosefri Lettmelk 1% fett, 1 l', 'Lettmelk Sjokolade Usøtet, 1 l',
        ]:
            self.assertIsNone(priced(name, 'no'), name)

    def test_dairy_and_eggs(self):
        self.assertEqual(priced('Helmelk, 1,75 l', 'no'), 'Whole Milk')
        self.assertEqual(priced('Fettfri Melk Skummet 0,1% fett, 1 l', 'no'), 'Skim Milk')
        self.assertEqual(priced('Frokostegg fra frittgående høner Str L, Str L, 12 stk', 'no'), 'Eggs')
        self.assertIsNone(priced('Lettmelk 0,5% fett, 1,75 l', 'no'))     # semi-skimmed: not listed

    def test_meat(self):
        self.assertEqual(priced('Kyllingfilet, 800 g', 'no'), 'Chicken Breast')
        self.assertEqual(priced('Kjøttdeig av storfe 14%, 400 g', 'no'), 'Ground Beef')
        self.assertIsNone(priced('Kyllingkjøttdeig, 400 g', 'no'))
        self.assertIsNone(priced('Kyllingfilet marinert, 600 g', 'no'))


class Swedish(unittest.TestCase):
    def test_produce(self):
        for name, want in [
            ('Potatis Kok/Fast Klass1, Sverige, 900 g', 'Potato'),
            ('Potatis Mos/Mjölig Klass1, Sverige, 2 kg', 'Potato'),
            ('Sötpotatis Klass1, Egypt, 500 g', 'Sweet Potato'),
            ('Lök Röd styck Klass1, Sverige, 90 g', 'Red Onion'),
            ('Tomat Fantastika  Klass1, Nederländerna, 400 g', 'Tomato'),
        ]:
            self.assertEqual(priced(name, 'sv'), want, name)

    def test_processed_is_turned_away(self):
        for name in ['Potatisbullar Frysta, 1500 g', 'Potatisgratäng, 800 g', 'Fries Super Crunch Fryst, 750 g',
                     'Kinder Ägg 3x60g, 180 g', 'Flytande Äggvitor, 1 kg', 'Pasta Tagliatelle Ägg, 500 g']:
            self.assertIsNone(priced(name, 'sv'), name)

    def test_eggs(self):
        self.assertEqual(priced('Ägg Frigående M/L, 20 st', 'sv'), 'Eggs')


class Estonian(unittest.TestCase):
    def test_produce(self):
        for name, want in [
            ('Porgand pestud, kg', 'Carrot'), ('Mugulsibul pakitud võrgus, 1 kg', 'Onion'),
            ('Kartul punane pestud Baltic Red, kg', 'Potato'), ('Kirss-ploomtomat, 500g', 'Cherry Tomato'),
            ('Lihatomat kollane, VÕISTE AIAND, kg', 'Beefsteak Tomatoes'), ('Mahe Banaan, kg', 'Banana'),
            ('Õun Granny Smith, kg', 'Apples'), ('Saaremaa lehtkapsas ehk Kale, RAUTSI TALU, 200 g', 'Kale'),
        ]:
            self.assertEqual(priced(name, 'et'), want, name)

    def test_processed_is_turned_away(self):
        for name in ['Mais vaakumis, 450 g', 'Riivitud porgand, KADARBIKU KÖÖGIVILI, 250 g',
                     'Hapukapsas porgandiga, KADARBIKU KÖÖGIVILI, 500 g', 'Peedikuubikud, DIMDINI, 350 g',
                     'Broileri pooltiivad mango-tšillimarinaadis, SELVER, kg', 'Keefir 2,5%, VALIO GEFILUS, 1 kg',
                     'Brokoli võrsed, VÄIKE MAHETALU, 40 g']:
            self.assertIsNone(priced(name, 'et'), name)

    def test_dairy_meat_eggs(self):
        self.assertEqual(priced('Täispiim 3,6%-4,2% pure, FARMI, 1 L', 'et'), 'Whole Milk')
        self.assertEqual(priced('Eesti Juust täispiimast viilud, ESTOVER, 450 g', 'et'), 'Cheese')
        self.assertEqual(priced('Õrrekanade munad M10, DAVA, 10 tk', 'et'), 'Eggs')
        self.assertEqual(priced('Eestimaine broileririnnafilee, TALLEGG, kg', 'et'), 'Chicken Breast')
        self.assertEqual(priced('Veise abaliha kondita, RAKVERE LK, kg', 'et'), 'Fresh Chuck Roast')
        self.assertIsNone(priced('Sea välisfilee, RAKVERE, kg', 'et'))          # pork loin: not listed
        self.assertIsNone(priced('Piim 2,5% pure, FARMI, 1 L', 'et'))           # semi-skimmed: not listed


class ShopPrices(unittest.TestCase):
    def test_oda_eggs_by_the_dozen(self):
        p = {'name': 'Frokostegg fra frittgående høner Str L', 'name_extra': 'Str L, 12 stk',
             'gross_price': '62.90', 'gross_unit_price': '77.08', 'unit_price_quantity_abbreviation': 'kg'}
        s = oda.structured(p, oda.SITES['NO']['eggs'])
        self.assertEqual(s, 'item=62.9;per_dozen=62.9')
        price = prices.read('Oda', s, None, 'Frokostegg fra frittgående høner Str L, Str L, 12 stk')
        self.assertEqual(price.basis(), ('dozen', 62.9))

    def test_mathem_eggs_from_the_price_per_egg(self):
        p = {'name': 'Ägg Frigående M/L', 'name_extra': '20 st', 'gross_price': '55.79',
             'gross_unit_price': '2.79', 'unit_price_quantity_abbreviation': 'st'}
        self.assertEqual(oda.structured(p, oda.SITES['SE']['eggs']), 'item=55.79;per_dozen=33.48')

    def test_oda_discount_keeps_the_regular_price(self):
        p = {'name': 'Potatis Kok/Fast Klass1', 'name_extra': 'Sverige, 900 g', 'gross_price': '10.00',
             'gross_unit_price': '11.11', 'unit_price_quantity_abbreviation': 'kg',
             'discount': {'is_discounted': True, 'undiscounted_gross_price': '13.95'}}
        s = oda.structured(p, oda.SITES['SE']['eggs'])
        self.assertEqual(s, 'item=10.0;per_kg=11.11;regular=13.95')
        self.assertTrue(prices.read('Mathem', s, None, 'Potatis').promo)

    def test_selver_guest_price_and_offer(self):
        p = {'name': 'Kartul Soraya, ANTSU KARTUL, 2 kg', 'unit_price': 1.35, 'product_compare_unit': 75,
             'prices': [{'customer_group_id': 0, 'price': 2.69, 'original_price': 3.89},
                        {'customer_group_id': 4, 'price': 2.49, 'original_price': 3.89}]}
        self.assertEqual(selver.structured(p), 'item=2.69;per_kg=1.35;regular=3.89')

    def test_selver_eggs(self):
        p = {'name': 'Munad M10, KALEVIPOJA MUNAD, 10 tk', 'unit_price': 0.28, 'product_compare_unit': 18,
             'prices': [{'customer_group_id': 0, 'price': 2.79, 'original_price': 2.79}]}
        self.assertEqual(selver.structured(p, eggs=True), 'item=2.79;per_dozen=3.36')


class Jordbruksverket(unittest.TestCase):
    def test_latest_month_per_product(self):
        ds = {
            'id': ['Produkter', 'Månad'],
            'dimension': {
                'Produkter': {'category': {'index': {'19': 0, '22': 1}}},
                'Månad': {'category': {'index': {'138': 0, '139': 1},
                                       'label': {'138': '2026M07', '139': '2026M08'}}},
            },
            'value': [225.12, 230.0, 4281.05, None],
        }
        self.assertEqual(sjv_producer.latest(ds), {'19': ('2026M08', 230.0), '22': ('2026M07', 4281.05)})


if __name__ == '__main__':
    unittest.main()
