"""
Italy and Portugal: ISMEA, SIMA, the GPP Price Observatory, Continente and the
Portuguese shelf-name rules. No network, no database: each test feeds the
parser a fragment shaped like the real page.

    venv/bin/python -m unittest tests.test_itpt_feeds
"""

import unittest
from datetime import date

from feeds import continente, ismea, pt_observatorio, sima
from pipeline import prices
from pipeline.catalog import products
from pipeline.matcher import Matcher


ISMEA_PAGE = (
    "<table id='PMTable3' class='isAppTable'><tbody>"
    "<tr class='even'><th id='table3r0'>Pomodori - Tondo liscio</th><td headers='x'>2026-10-5</td>"
    "<td class='number'  headers='y'>1,35 &euro;/Kg</td><td>0%</td></tr>"
    "<tr class='odd'><th id='table3r1'>Pomodori serra - Tondi lisci</th><td headers='x'>2026-10-5</td>"
    "<td class='number'  headers='y'>1,30 &euro;/Kg</td><td>0%</td></tr>"
    "<tr class='odd'><th id='table3r2'>Carciofi - Tipo catanese</th><td headers='x'>2026-10-5</td>"
    "<td class='number'  headers='y'>0,63 &euro;/Capolino</td><td>0%</td></tr>"
    "<tr class='odd'><th id='table3r3'>Uova da allevamento all'aperto  - M (tra 53 e 63 gr)</th><td>2026-10-5</td>"
    "<td class='number'>24,10 &euro;/100 unità</td><td>0%</td></tr>"
    "<tr class='odd'><th id='table3r4'>Olio extravergine di oliva</th><td>2026-10-5</td>"
    "<td class='number'>5,18 &euro;/Kg</td><td>0%</td></tr>"
    "<tr class='odd'><th id='table3r5'>Lattuga - Iceberg</th><td>2026-10-5</td>"
    "<td class='number'>1,03 &euro;/Kg</td><td>0%</td></tr>"
    "<tr class='odd'><th id='table3r6'>Miele</th><td>2026-6-4</td><td class='number'>4,20 &euro;/Kg</td><td>0%</td></tr>"
    "</tbody></table>"
)


class Ismea(unittest.TestCase):
    def setUp(self):
        self.rows = ismea.parse(ISMEA_PAGE)
        self.figures, self.skipped = ismea.figures_from(self.rows, ismea.ORIGIN_MAP, today=date(2026, 11, 4))
        self.by = {f.name: f for f in self.figures}

    def test_week_of_month(self):
        self.assertEqual(ismea.week_date('2026-10-5'), date(2026, 10, 29))
        self.assertEqual(ismea.week_date('2026-10-1'), date(2026, 10, 1))
        self.assertEqual(ismea.week_date('2026-10'), date(2026, 10, 1))

    def test_varieties_of_one_product_are_averaged(self):
        tomato = self.by['Tomato']
        self.assertAlmostEqual(tomato.price, 1.325)
        self.assertEqual((tomato.low, tomato.high), (1.3, 1.35))

    def test_units_are_converted(self):
        self.assertAlmostEqual(self.by['Eggs'].price, 24.10 * 0.12, places=4)    # per 100 → per dozen
        self.assertEqual(self.by['Eggs'].unit, 'dozen')
        self.assertAlmostEqual(self.by['Olive Oil'].price, 5.18 * 0.916, places=4)  # per kg → per litre
        self.assertEqual(self.by['Artichoke'].unit, 'unit')

    def test_unmapped_and_stale_quotes_are_left_out(self):
        self.assertNotIn('Romaine Lettuce', self.by)          # Iceberg is not Romaine
        self.assertNotIn('Honey', self.by)                    # last quoted in June
        self.assertTrue(any('Iceberg' in s for s in self.skipped))

    def test_every_target_is_a_catalogue_product(self):
        catalog = products()
        for _, name, _, _ in ismea.ORIGIN_MAP + ismea.WHOLESALE_MAP:
            self.assertIn(name.lower(), catalog, name)


SIMA_ROWS = [
    # wholesale market, national and Spanish tomatoes
    ['Tomate*Redondo Estufa*II*67-81 mm*Caixa*Nacional*EUR/kg', 'Tomate', ' Ribatejo e Oeste', 'MARL', '44', '02-11-2026', '1.00', '2.00', '1.80', ''],
    ['Tomate*Redondo Estufa*II*67-81 mm*Caixa*Espanha*EUR/kg', 'Tomate', ' Ribatejo e Oeste', 'MARL', '44', '02-11-2026', '1.00', '2.00', '1.70', ''],
    ['Tomate*Redondo Estufa*II*67-81 mm*Caixa*Nacional*EUR/kg', 'Tomate', ' Ribatejo e Oeste', 'MARL', '43', '26-10-2026', '1.00', '2.00', '1.50', ''],
    ['Tomate*Sulcado Estufa*II*67-81 mm*Caixa*Nacional*EUR/kg', 'Tomate', ' Entre Douro e Minho', 'MAP', '44', '03-11-2026', '1.55', '1.65', '1.60', ''],
    ['Beterraba*Molho*Nacional*EUR/Molho', 'Beterraba', ' Ribatejo e Oeste', 'MARL', '44', '02-11-2026', '0.5', '0.6', '0.5', ''],
]

SIMA_PRODUCTION = [
    ['Peito de Frango*EUR/kg', 'Frango', ' Ribatejo e Oeste', 'Ribatejo e Oeste Gr.', '44', '26-10-2026', '5.60', '6.00', '5.80', ''],
    ['Frango*Vivo-1.8 kg*EUR/kg P. Vivo', 'Frango', ' Ribatejo e Oeste', 'Ribatejo e Oeste', '44', '26-10-2026', '1.20', '1.30', '1.25', ''],
    ['Courgette*SP (Leilão)*Não Calibrado*Caixa*EUR/kg', 'Courgette', ' Ribatejo e Oeste', 'Oeste', '44', '26-10-2026', '0.35', '0.98', '0.84', ''],
    ['Coelho*Abatido-1,1 a 1,3 kg*EUR/kg P. Carcaça', 'Coelho', ' Continente', 'Portugal - Continente Gr.', '45', '02-11-2026', '6.40', '6.95', '6.70', ''],
]


class Sima(unittest.TestCase):
    def test_wholesale_keeps_portuguese_produce_and_the_latest_quote(self):
        got = sima.figures_from(SIMA_ROWS, 12, today=date(2026, 11, 4))
        tomato = {f.region: f for f in got['wholesale'] if f.name == 'Tomato'}
        self.assertEqual(tomato['Ribatejo e Oeste'].price, 1.80)            # not Spain's 1.70, not last week's 1.50
        self.assertEqual(tomato['Entre Douro e Minho'].price, 1.60)
        self.assertAlmostEqual(tomato[None].price, 1.70)                     # the national figure
        self.assertNotIn('Beetroot', {f.name for f in got['wholesale']})    # per bunch, not per kg

    def test_production_markets_split_by_stage_and_skip_live_weight(self):
        got = sima.figures_from(SIMA_PRODUCTION, 8, today=date(2026, 11, 4))
        self.assertEqual({f.name for f in got['wholesale']}, {'Chicken Breast', 'Rabbit Meat'})
        self.assertEqual({f.name for f in got['farmgate']}, {'Zucchini'})
        rabbit = [f.region for f in got['wholesale'] if f.name == 'Rabbit Meat']
        self.assertEqual(rabbit, [None])                                    # "Continente" is the mainland, not a region

    def test_old_quotes_are_dropped(self):
        got = sima.figures_from(SIMA_ROWS, 12, today=date(2026, 12, 31))
        self.assertEqual(dict(got), {})

    def test_every_target_is_a_catalogue_product(self):
        catalog = products()
        for _, _, name, _ in sima.MAP:
            self.assertIn(name.lower(), catalog, name)


OBS_PAGE = """
<th scope="col" id="table-header-3-2"><strong>Período 10</strong><br>(2026-09-07 a 2026-10-04)</th>
<tr class="all-tr tr-137" hidden ><th scope="row" id="table-header-4-137">Tomate - Produção (€/kg)</th>
<td headers="a">1,24€</td><td headers="b">0,74€</td></tr>
<tr class="all-tr tr-1033"  ><th scope="row" id="table-header-4-1033">Tomate - Consumo (€/kg)</th>
<td headers="a">2,61€</td><td headers="b">2,17€</td></tr>
<tr><th scope="row" id="table-header-4-9">Ovo - Consumo (€/6 ovos)</th><td headers="a">1,58€</td></tr>
<tr><th scope="row" id="table-header-4-10">Carne de Frango - Consumo (€/kg)</th><td headers="a">4,78€</td></tr>
"""


class Observatorio(unittest.TestCase):
    def test_stages_units_and_period(self):
        start, rows = pt_observatorio.parse(OBS_PAGE)
        self.assertEqual(start, date(2026, 9, 7))
        got = pt_observatorio.figures_from(start, rows)
        retail = {f.name: f for f in got['retail']}
        self.assertEqual(retail['Tomato'].price, 2.61)
        self.assertEqual((retail['Eggs'].price, retail['Eggs'].unit), (3.16, 'dozen'))
        self.assertNotIn('Whole Chicken', retail)                           # a group average is not used
        self.assertEqual([(f.name, f.price) for f in got['farmgate']], [('Tomato', 1.24)])

    def test_every_target_is_a_catalogue_product(self):
        catalog = products()
        for name, _, _ in pt_observatorio.MAP.values():
            self.assertIn(name.lower(), catalog, name)


TILE = """class="product-tile col-product-tile pid-2597619 ct-product-tile"
 data-product-tile-impression='{&quot;name&quot;:&quot;Laranja Continente&quot;,&quot;id&quot;:&quot;2597619&quot;,&quot;price&quot;:1.49,&quot;category&quot;:&quot;Supermercado/Frutas e Legumes/Frutas/Laranja e Clementina&quot;}'>
 <a class="image-link pb-1" href="https://www.continente.pt/produto/laranja-continente-2597619.html"></a>
 <p class="pwc-tile--quantity">
   Quant. M&iacute;nima = 900 gr (3 un)
 </p>
 <div class="prices-wrapper"> <div class="list "> <span class="strike-through pwc-tile--price-dashed">
 <span class="value pwc-tile--price-value" content="1.49"> 1,69&euro; </span> </span> </div>
 <span class="pwc-tile--price-primary">
   1<span class="decimalPrice">,49&euro;/kg</span>
 </span>
</div>
<div class="pwc-tile--price-secondary ">
    0,45&euro;/un
</div>"""


class Continente(unittest.TestCase):
    def test_tile_to_structured_price(self):
        t = continente.tiles(TILE)[0]
        self.assertEqual(t['name'], 'Laranja Continente')
        self.assertEqual(continente.structured(t), 'item=1.49;per_kg=1.49;per_unit=0.45;regular=1.69')
        p = prices.read('Continente', continente.structured(t), '', 'Laranja Continente')
        self.assertEqual(p.basis(), ('kg', 1.49))
        self.assertTrue(p.promo)

    def test_eggs_by_the_dozen(self):
        t = {'name': 'Ovos de Solo Classe M Continente', 'aisle': 'Supermercado/Laticínios e Ovos/Ovos',
             'quantity': 'emb. 12 un', 'primary': '2,99€', 'secondary': '', 'regular': ''}
        self.assertIn('per_dozen=2.99', continente.structured(t))

    def test_no_piece_price_for_meat(self):
        t = {'name': 'Peito de Frango Continente', 'aisle': 'Supermercado/Talho/Frango',
             'quantity': 'emb. 700 gr (aprox.)', 'primary': '6,59€/kg', 'secondary': '4,61€/un', 'regular': ''}
        self.assertEqual(continente.structured(t), 'item=6.59;per_kg=6.59')


class PortugueseNames(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = Matcher()

    def name(self, raw):
        p, how, _ = self.m.match(raw, 'pt')
        return p['name'] if p else how

    def test_singular_shelf_names(self):
        self.assertEqual(self.name('Maçã Gala Continente, emb. 1 kg'), 'Apples')
        self.assertEqual(self.name('Pera Rocha DOP Oeste Continente'), 'Pears')
        self.assertEqual(self.name('Tomate em Cacho Continente'), 'Vine Tomatoes')
        self.assertEqual(self.name('Perna de Frango com Costa Continente, emb. 900 gr (aprox.)'), 'Chicken Drumsticks')
        self.assertEqual(self.name('Queijo de Évora DOP Continente Seleção'), 'Sheep Cheese')
        self.assertEqual(self.name('Requeijão de Ovelha de Seia Continente'), 'Fresh Cottage Cheese')

    def test_the_product_must_lead(self):
        self.assertEqual(self.name('Mix Maçã e Pera Rocha Continente, emb. 800 gr'), None)
        self.assertEqual(self.name('Salada de Manga Continente, emb. 225 gr'), 'rejected')
        self.assertEqual(self.name('Preparado para Sopa de Alho Francês com Cenoura Continente'), 'rejected')

    def test_not_the_same_product(self):
        self.assertEqual(self.name('Banana Pão Continente'), 'Plantain')
        self.assertEqual(self.name('Alface Iceberg Continente, emb. 400 gr'), 'unlisted')
        self.assertEqual(self.name('Pepino Biológico Continente Bio, emb. 500 gr'), 'unlisted')
        self.assertEqual(self.name('Melancia Mini Continente'), 'Watermelon')
        self.assertEqual(self.name('Mel de Rosmaninho Serramel, emb. 500 gr'), 'Honey')

    def test_rule_targets_are_catalogue_products(self):
        from pipeline import rules_pt
        catalog = products()
        for _, name, _, _ in rules_pt.RULES:
            target = rules_pt.TARGETS.get(name, name)
            if target is not None:
                self.assertIn(target.lower(), catalog, name)


if __name__ == '__main__':
    unittest.main()
