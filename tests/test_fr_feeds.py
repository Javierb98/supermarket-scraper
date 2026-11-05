"""
The French feeds (INSEE average prices, FranceAgriMer RNM) on real rows from
the 4 November 2026 pages, without the network or the database.

    python -m unittest tests.test_fr_feeds
"""

import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import insee, rnm
from pipeline.catalog import products

INSEE_XML = '''<message:DataSet>
<Series REF_AREA="FM" FREQ="M" SERIE_ARRETEE="FALSE" IDBANK="000641429" TITLE_FR="Prix moyens mensuels de vente au détail en métropole - Tomates (1 kg)"><Obs TIME_PERIOD="2026-09" OBS_VALUE="5.23"/></Series>
<Series REF_AREA="FM" FREQ="M" SERIE_ARRETEE="FALSE" IDBANK="001791254" TITLE_FR="Prix moyens mensuels de vente au détail en métropole - Chou-fleur (pièce)"><Obs TIME_PERIOD="2026-09" OBS_VALUE="3.6"/></Series>
<Series REF_AREA="FM" FREQ="A" SERIE_ARRETEE="FALSE" IDBANK="000641999" TITLE_FR="Prix moyens annuels - Tomates (1 kg)"><Obs TIME_PERIOD="2025" OBS_VALUE="3.9"/></Series>
<Series REF_AREA="FM" FREQ="M" SERIE_ARRETEE="TRUE" IDBANK="000641406" TITLE_FR="Prix moyens mensuels - Cabillaud en tranche (1 kg) - Série arrêtée"><Obs TIME_PERIOD="2015-12" OBS_VALUE="18.16"/></Series>
<Series REF_AREA="FM" FREQ="M" SERIE_ARRETEE="FALSE" IDBANK="000442588" TITLE_FR="Prix moyens mensuels - Gazole (1 litre)"><Obs TIME_PERIOD="2026-09" OBS_VALUE="2.34"/></Series>
</message:DataSet>'''


class Insee(unittest.TestCase):
    def test_live_monthly_series_only(self):
        rows = insee.parse(INSEE_XML)
        self.assertEqual({r[0] for r in rows}, {'000641429', '001791254', '000442588'})

    def test_figures_keep_insee_units(self):
        figs = {f.name: f for f in insee.figures(insee.parse(INSEE_XML), today=date(2026, 11, 4))}
        self.assertEqual(set(figs), {'Tomato', 'Cauliflower'})          # diesel is not a product
        self.assertEqual((figs['Tomato'].price, figs['Tomato'].unit), (5.23, 'kg'))
        self.assertEqual(figs['Cauliflower'].unit, 'unit')
        self.assertEqual(figs['Tomato'].snapshot, date(2026, 9, 1))

    def test_every_mapped_name_is_in_the_catalogue(self):
        for name, unit, _ in insee.SERIES.values():
            self.assertIn(name.lower(), products(), name)
            self.assertIn(unit, ('kg', 'l', 'dozen', 'unit'))


class Rnm(unittest.TestCase):
    def test_units(self):
        self.assertEqual(rnm.unit_of('TOMATE ronde rouge France 57-67 ou 67-82mm vrac'), ('kg', 1.0))
        self.assertEqual(rnm.unit_of('CHOU FLEUR France (la pièce)'), ('unit', 1.0))
        self.assertEqual(rnm.unit_of('AVOCAT Hass Pérou colis de 16 (les 16 pièces)'), ('unit', 16.0))
        self.assertEqual(rnm.unit_of('ASPERGE verte Amérique du sud cat.I 16-22mm botte 420g (les 420g)'), ('kg', 0.42))
        self.assertEqual(rnm.unit_of('KIWI Hayward Nouvelle-Zélande cat.I 85-95g - 33 - colis (les 10kg)'), ('kg', 10.0))
        self.assertEqual(rnm.unit_of('CITRON Espagne cat.I 4(58-67mm)'), ('kg', 1.0))
        self.assertIsNone(rnm.unit_of('CAROTTE France cat.I botte (la botte)'))
        self.assertIsNone(rnm.unit_of('POIVRON carré France biologique cdt 2 (le cdt 2)'))
        # by the case on one market, by the kilo on another: skipped
        self.assertIsNone(rnm.unit_of('ARTICHAUT blanc Espagne cat.I +13cm colis de 12', wholesale=True))
        self.assertIsNone(rnm.unit_of('FRAMBOISE Espagne barq.125g', wholesale=True))
        self.assertEqual(rnm.unit_of('FRAMBOISE Maroc barq.125g (la barq. 125g)', wholesale=True), ('kg', 0.125))
        self.assertEqual(rnm.unit_of('FRAMBOISE France barq.125g'), ('kg', 1.0))      # supermarket page: per kilo

    def test_names(self):
        self.assertEqual(rnm.names_for('CHAMPIGNON DE PARIS France pied entier cat.I plateau'), ['White Mushroom'])
        self.assertEqual(rnm.names_for('POMME Pink-lady France plateau rg'), ['Apples', 'Pink Lady Apples'])
        self.assertEqual(rnm.names_for('POMME DE TERRE de conservation France vrac'), ['Potato'])
        self.assertEqual(rnm.names_for('OIGNON jaune France filet 1kg'), ['Onion'])
        self.assertEqual(rnm.names_for('OIGNON rouge France sac'), ['Red Onion'])
        self.assertEqual(rnm.names_for('POMME Golden France biologique'), [])
        self.assertEqual(rnm.names_for('TOMATE ronde ou ronde grappe France biologique'), ['Organic Tomatoes'])
        self.assertEqual(rnm.names_for('BETTERAVE ROUGE ronde cuite France'), [])
        self.assertEqual(rnm.names_for('KIWI Gold France cat.I plateau'), [])

    def test_every_mapped_name_is_in_the_catalogue(self):
        for _, name in rnm.RULES + rnm.VARIETIES + rnm.ORGANIC_RULES:
            self.assertIn(name.lower(), products(), name)

    def test_french_loose_rows_win_at_retail(self):
        rows = [
            ('TOMATE ronde rouge France 57-67 ou 67-82mm vrac', 3.56, 2.99, 3.99),
            ('TOMATE ronde rouge France 77-82 ou 82-102mm vrac', 4.26, 3.49, 4.99),
            ('TOMATE ronde rouge France filet 1kg', 2.35, 1.89, 2.49),
            ('TOMATE ronde rouge Maroc filet 1kg', 2.20, 1.89, 2.59),
            ('CLÉMENTINE Corse cal.3-4-5 vrac', 5.39, 4.99, 5.99),
            ('CLÉMENTINE hors Fr. vrac', 2.82, 1.69, 3.99),
        ]
        out = rnm.combine(rows, prefer_loose=True)
        self.assertAlmostEqual(out[('Tomato', 'kg')][0], (3.56 + 4.26) / 2)
        self.assertEqual(out[('Tomato', 'kg')][1:3], (2.99, 4.99))
        self.assertEqual(out[('Clementine', 'kg')][0], 5.39)

    def test_page(self):
        page = '''<h1 class="bleu">MIN de Rungis : fruits et légumes <small>(cours Grossistes)</small></h1>
<h2>march&eacute; du  04-11-2026<br /></h2>
<table class="tabcot" id="tabcotmar"><thead><tr><th class="thcot">cours du 04/11/26<br />en <span class="euro">&euro; HT</span> le kg*</th>
<th>Prix<br />moyen</th></tr></thead><tbody>
<tr><td class="tdcotl"><a href="#">CHOU FLEUR France couronné cat.I gros (les 6 pièces)</a></td><td>10.00</td><td>=</td><td>9.00</td><td>11.00</td></tr>
<tr><td class="tdcotl"><a href="#">CHAMPIGNON DE PARIS France pied entier cat.I plateau</a></td><td>3.80</td><td>=</td><td>3.20</td><td>4.50</td></tr>
</tbody></table>'''
        title, when, default, rows = rnm.parse_page(page)
        self.assertEqual(title, 'MIN de Rungis : fruits et légumes')
        self.assertEqual(when, date(2026, 11, 4))
        self.assertEqual(default, ('kg', 1.0))
        out = rnm.combine(rows, default)
        self.assertAlmostEqual(out[('Cauliflower', 'unit')][0], 10 / 6, places=3)
        self.assertEqual(out[('White Mushroom', 'kg')], (3.8, 3.2, 4.5, 1))


if __name__ == '__main__':
    unittest.main()
