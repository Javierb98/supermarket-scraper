"""
How much is in a pack, from the product's name, in any of the shop languages.

    "Tomate cherry pera, vaso 250 g"      → 0.25 kg
    "Patatas, malla 3 kg"                 → 3 kg
    "Leche entera, pack 6 x 1 l"          → 6 l
    "Huevos camperos L, 12 uds"           → 12 pieces
    "Media docena de huevos"              → 6 pieces
    "Kiwi, bandeja 4 x 100 g"             → 0.4 kg
"""

import re
from dataclasses import dataclass
from typing import Optional

N = r'(\d+(?:[.,]\d+)?)'

WEIGHT = {'kg': 1, 'kilo': 1, 'kilos': 1, 'kilogramos': 1, 'g': 0.001, 'gr': 0.001, 'grs': 0.001,
          'gramos': 0.001, 'gramm': 0.001, 'grammes': 0.001, 'grammi': 0.001, 'lb': 0.4536, 'lbs': 0.4536, 'oz': 0.02835}
VOLUME = {'l': 1, 'lt': 1, 'ltr': 1, 'litro': 1, 'litros': 1, 'liter': 1, 'litre': 1, 'litres': 1,
          'ml': 0.001, 'cl': 0.01, 'dl': 0.1}
COUNT = ['ud', 'uds', 'u', 'unidades', 'unidad', 'piezas', 'pzas', 'stück', 'stk', 'st', 'pièces', 'pcs',
         'pezzi', 'pz', 'unid', 'stuks', 'tk', 'stk.', 'un', 'eggs', 'huevos', 'oeufs', 'eier', 'uova', 'ovos']

UNIT_RX = '|'.join(sorted([re.escape(u) for u in list(WEIGHT) + list(VOLUME)], key=len, reverse=True))
COUNT_RX = '|'.join(sorted([re.escape(u) for u in COUNT], key=len, reverse=True))


@dataclass
class Pack:
    kg: Optional[float] = None
    litres: Optional[float] = None
    count: Optional[int] = None
    eggs: bool = False


def _n(s):
    return float(s.replace(',', '.'))


def from_name(name):
    if not name:
        return None
    n = ' ' + name.lower().replace('×', 'x') + ' '
    eggs = bool(re.search(r'\bhuevo|\begg|\boeuf|\beier\b|\beieren\b|\buov|\bovos?\b|\bägg|\bmuna', n))
    p = Pack(eggs=eggs)

    # "6 x 1 l", "4x100 g"
    m = re.search(r'(\d+)\s*x\s*' + N + r'\s*(' + UNIT_RX + r')\b', n)
    if m:
        times, v, u = int(m.group(1)), _n(m.group(2)), m.group(3)
        if u in WEIGHT:
            p.kg = round(times * v * WEIGHT[u], 4)
        else:
            p.litres = round(times * v * VOLUME[u], 4)
        p.count = times
    else:
        m = re.search(N + r'\s*(' + UNIT_RX + r')\b', n)
        if m:
            v, u = _n(m.group(1)), m.group(2)
            if u in WEIGHT:
                p.kg = round(v * WEIGHT[u], 4)
            else:
                p.litres = round(v * VOLUME[u], 4)

    if p.count is None:
        m = re.search(r'(\d+)\s*(?:' + COUNT_RX + r')\b\.?', n) or re.search(r'\b(?:pack|p)[\s-]*(\d+)\b', n)
        if m:
            p.count = int(m.group(1))
        elif re.search(r'media docena|half dozen|demi-douzaine', n):
            p.count = 6
        elif re.search(r'\bdocena\b|\bdozen\b|\bdouzaine\b|\bdutzend\b', n):
            p.count = 12
        elif re.search(r'\b(unidad|pieza|manojo|each|piece|bunch|stück|bund|pièce|botte|pezzo|mazzo|unidade|molho|stuk|bos)\b', n) \
                and p.kg is None and p.litres is None:
            # "Coco, unidad", "Puerro, manojo": sold as one.
            p.count = 1

    if p.kg is None and p.litres is None and p.count is None:
        return None
    return p
