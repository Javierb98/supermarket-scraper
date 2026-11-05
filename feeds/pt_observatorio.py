"""
Portugal: the agri-food Price Observatory (Observatório de Preços, GPP).

The Ministry of Agriculture's planning office (GPP) publishes, for a basket of
representative foods, the average price at production and at consumption
("Consumo": the shop shelf) for four-week periods, nationally. Each product
sector has a page whose summary table is plain HTML:

    Tomate - Produção (€/kg)   1,24€ ...
    Tomate - Consumo (€/kg)    2,61€ ...

"Consumo" is stored as 'retail' and "Produção" as 'farmgate'. The consumer
prices are national averages over the period (methodology PDF linked on each
page); there is no regional breakdown, so region is None.

A row that is a group average ("Carne de Frango", "Carne de Porco", "Peixe")
or a product the catalogue does not have (rice, bread, pasta, UHT semi-skimmed
milk, sea bream) is not used. Eggs are quoted per six and stored per dozen.
Olive oil at "Produção" is the bottler's price, not the grower's, so it is
left out.

The snapshot is the first day of the four-week period.

Terms: GPP public information, free access (observatorioagroalimentar.gov.pt,
Política de Privacidade / GPP Avisos legais); used with attribution.

    python feeds/pt_observatorio.py
"""

import html
import os
import re
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.common import Figure, get, write  # noqa: E402

BASE = 'https://observatorioagroalimentar.gov.pt/setor/{}/'
SOURCE = 'GPP Observatório de Preços Agroalimentar'

SECTORS = [
    'alface', 'banana', 'batata', 'carne-de-frango', 'carne-de-porco', 'cebola', 'cenoura',
    'couve', 'curgete', 'laranja', 'maca', 'ovos-de-galinha', 'pera', 'pessego', 'tomate',
    'azeite-3', 'laticinios-de-vaca',
]

# (row label before " - ", stage) → (catalogue name, unit, factor)
MAP = {
    ('Tomate', 'Consumo'): ('Tomato', 'kg', 1),
    ('Tomate', 'Produção'): ('Tomato', 'kg', 1),
    ('Batata', 'Consumo'): ('Potato', 'kg', 1),
    ('Batata', 'Produção'): ('Potato', 'kg', 1),
    ('Cenoura', 'Consumo'): ('Carrot', 'kg', 1),
    ('Cenoura', 'Produção'): ('Carrot', 'kg', 1),
    ('Curgete', 'Consumo'): ('Zucchini', 'kg', 1),
    ('Curgete', 'Produção'): ('Zucchini', 'kg', 1),
    ('Laranja', 'Consumo'): ('Oranges', 'kg', 1),
    ('Laranja', 'Produção'): ('Oranges', 'kg', 1),
    ('Pêssego', 'Consumo'): ('Peaches', 'kg', 1),
    ('Pêssego', 'Produção'): ('Peaches', 'kg', 1),
    ('Cebola', 'Consumo'): ('Onion', 'kg', 1),
    ('Banana', 'Consumo'): ('Banana', 'kg', 1),
    ('Maçã', 'Consumo'): ('Apples', 'kg', 1),
    ('Pêra', 'Consumo'): ('Pears', 'kg', 1),
    ('Brócolo', 'Consumo'): ('Broccoli', 'kg', 1),
    ('Ovo', 'Consumo'): ('Eggs', 'dozen', 2),                 # €/6 ovos
    ('Frango peito', 'Consumo'): ('Chicken Breast', 'kg', 1),
    ('Frango perna', 'Consumo'): ('Chicken Drumsticks', 'kg', 1),   # "pernas de frango"
    ('Porco entremeada', 'Consumo'): ('Pork Belly', 'kg', 1),
    ('Azeite Virgem Extra', 'Consumo'): ('Olive Oil', 'l', 1),
}

# The unit each mapped row must be quoted in, as the page writes it.
EXPECTED = {'kg': '€/kg', 'l': '€/l', 'dozen': '€/6 ovos'}

STAGES = {'Consumo': 'retail', 'Produção': 'farmgate'}

ROW = re.compile(r'<th scope="row" id="table-header-4-\d+">([^<]+)</th>\s*<td[^>]*>([^<]*)</td>')
PERIOD = re.compile(r'<strong>Per[ií]odo \d+</strong><br>\((\d{4}-\d{2}-\d{2}) a (\d{4}-\d{2}-\d{2})\)')
LABEL = re.compile(r'^(.+?) - (Consumo|Produção)\b.*\(([^)]+)\)\s*$')


def parse(page_html):
    """A sector page → (period start, [(product, stage word, unit text, price)])."""
    m = PERIOD.search(page_html)
    if not m:
        return None, []
    start = datetime.strptime(m.group(1), '%Y-%m-%d').date()
    rows = []
    for label, value in ROW.findall(page_html):
        label = html.unescape(label).strip()
        lm = LABEL.match(label)
        v = html.unescape(value).replace('€', '').strip()
        if not lm or not re.match(r'^\d+(,\d+)?$', v):
            continue
        rows.append((lm.group(1).strip(), lm.group(2), lm.group(3).strip(), float(v.replace(',', '.'))))
    return start, rows


def figures_from(start, rows):
    out = {'retail': [], 'farmgate': []}
    for product, stage_word, unit_text, price in rows:
        hit = MAP.get((product, stage_word))
        if not hit:
            continue
        name, unit, factor = hit
        if unit_text != EXPECTED[unit]:
            print(f'  {product} {stage_word}: quoted {unit_text}, expected {EXPECTED[unit]} — skipped', file=sys.stderr)
            continue
        out[STAGES[stage_word]].append(Figure(name, round(price * factor, 4), unit, start))
    return out


def run():
    by_stage = {'retail': [], 'farmgate': []}
    for sector in SECTORS:
        try:
            start, rows = parse(get(BASE.format(sector), pause=1.5).decode('utf-8', 'replace'))
        except Exception as e:
            print(f'  {sector}: {e}', file=sys.stderr)
            continue
        if not start:
            print(f'  {sector}: no period on the page', file=sys.stderr)
            continue
        for stage, figures in figures_from(start, rows).items():
            by_stage[stage].extend(figures)

    written = 0
    for stage, figures in by_stage.items():
        for f in figures:
            print(f'  {stage:8} {f.name:20} {f.price:>7.2f} /{f.unit:5} {f.snapshot}')
        n, _ = write('PT', SOURCE + (', consumo' if stage == 'retail' else ', produção'), stage, figures)
        written += n
    if written == 0:
        raise RuntimeError('Observatório de Preços returned nothing usable — the pages have changed')
    return written


if __name__ == '__main__':
    run()
