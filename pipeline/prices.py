"""
What a shelf price actually says: what you pay, for how much, and whether it
is an offer.

Each shop writes its price differently, so each has its own reader here. They
all give back the same Price, and from that the price per kilo, litre, dozen
or piece is worked out the same way for everyone.

The old parser had one set of Spanish patterns for every shop. It never
looked at Consum's price per kilo (which the shop sends separately), so all
3,000 of Consum's weighed products were averaged as "per item"; and it read
Eroski's "was 1,60 now 1,49" as an ordinary price.
"""

import re
from dataclasses import dataclass, field
from typing import Optional

from pipeline.pack import Pack, from_name

NUM = r'(\d+(?:[.,]\d+)?)'


def num(s):
    """'1.234,56' / '1,234.56' / '2,50' / '2.50' → float."""
    s = s.strip().replace(' ', '').replace(' ', '')
    if ',' in s and '.' in s:
        # Whichever comes last is the decimal mark.
        if s.rfind(',') > s.rfind('.'):
            s = s.replace('.', '').replace(',', '.')
        else:
            s = s.replace(',', '')
    elif ',' in s:
        s = s.replace(',', '.')
    return float(s)


@dataclass
class Price:
    item: Optional[float] = None          # what one pack costs, in the shop's currency
    pack: Optional[Pack] = None           # how much is in it
    per: dict = field(default_factory=dict)   # basis ('kg', 'l', 'dozen', 'unit') → price
    regular: Optional[float] = None       # the price before an offer, when there is one
    promo: bool = False

    def basis(self):
        """The one price this observation contributes, and what it is per.

        Weight first: a farm sells by the kilo, and a kilo is comparable
        across pack sizes in a way a "piece" is not. Eggs by the dozen.
        A piece only when nothing better is known.
        """
        for b in ('dozen', 'kg', 'l', 'unit'):
            if b in self.per and self.per[b] and self.per[b] > 0:
                return b, self.per[b]
        return None, None


def _fill_from_pack(p):
    """Work out per-kg / per-litre / per-dozen / per-piece from the pack."""
    if p.item is None or p.pack is None:
        return p
    q = p.pack
    if q.kg:
        p.per.setdefault('kg', round(p.item / q.kg, 4))
    if q.litres:
        p.per.setdefault('l', round(p.item / q.litres, 4))
    if q.count:
        if q.count in (6, 10, 12, 15, 18, 20, 24, 30) and q.eggs:
            p.per.setdefault('dozen', round(p.item / q.count * 12, 4))
        if q.count <= 12:
            # Two lettuce hearts, four avocados: each is a piece a farm sells.
            p.per.setdefault('unit', round(p.item / q.count, 4))
        else:
            # One of 20 butter portions or 30 cherry tomatoes is not what a
            # farm's "each" means.
            p.per.pop('unit', None)
    return p


# ── Mercadona ────────────────────────────────────────────────────────────
#   Ahora2.90€ | 1 KG A 2.900 € | unidad 1.45€ | 0.5 kg
#   Ahora77.50€ | 1 100 G A 7.750 € | unidad 1.55€ | 0.02 kg
#   Ahora0.36€ | 1 DC A 4.300 € | unidad 4.30€ | 12.0 ud
#   Ahora1.70€ | 1 UD A 1.700 € | 1.0 ud
# "Ahora" is the reference price (per kilo, or per egg) and is ignored; the
# price you pay is "unidad", or the "1 UD A" figure for something sold singly.

def mercadona(raw_price, raw_unit_price, raw_name):
    p = Price()
    s = raw_price or ''
    m = re.search(r'unidad\s*' + NUM, s, re.I)
    if m:
        p.item = num(m.group(1))
    size = re.search(NUM + r'\s*(kg|l|ud)\s*$', s.strip(), re.I)
    if size:
        v, u = num(size.group(1)), size.group(2).lower()
        p.pack = Pack(kg=v if u == 'kg' else None, litres=v if u == 'l' else None,
                      count=int(round(v)) if u == 'ud' else None)
    for rx, basis, factor in (
        (r'1 100 G A\s*' + NUM, 'kg', 10),
        (r'1 KG A\s*' + NUM, 'kg', 1),
        (r'1 100 ML A\s*' + NUM, 'l', 10),
        (r'1 L A\s*' + NUM, 'l', 1),
        (r'1 D(?:C|Z|OCENA) A\s*' + NUM, 'dozen', 1),
        (r'1 UD A\s*' + NUM, 'unit', 1),
    ):
        m = re.search(rx, s, re.I)
        if m:
            p.per[basis] = round(num(m.group(1)) * factor, 4)
            break
    if p.item is None and p.per.get('unit') and (p.pack is None or p.pack.count in (None, 1)):
        p.item = p.per['unit']
    if p.pack and p.pack.count:
        p.pack.eggs = 'dozen' in p.per
    return _fill_from_pack(p)


# ── Eroski ───────────────────────────────────────────────────────────────
#   1 KILO A  17,96 € | Ahora4,49€ | Ahora4,49€ | 4,49 | €
#   1 KILO A  5,96 € | -6% | 1,60€AntesAhora1,49€ | 1,60€Antes | ...
# The pack size is in the name ("bandeja 250 g").

def eroski(raw_price, raw_unit_price, raw_name):
    p = Price()
    s = raw_price or ''
    m = re.search(r'Ahora\s*' + NUM, s)
    if m:
        p.item = num(m.group(1))
    before = re.search(NUM + r'\s*€?\s*Antes', s)
    if before:
        p.regular = num(before.group(1))
        p.promo = p.item is not None and p.regular > p.item
    for rx, basis in ((r'1 KILO A\s*' + NUM, 'kg'), (r'1 LITRO A\s*' + NUM, 'l'), (r'1 DOCENA A\s*' + NUM, 'dozen')):
        m = re.search(rx, s, re.I)
        if m:
            p.per[basis] = num(m.group(1))
    if p.item is None:
        prices = [num(x) for x in re.findall(NUM + r'\s*€', s)]
        prices = [x for x in prices if 0.05 < x < 500]
        p.item = min(prices) if prices else None
    if p.promo and p.per:
        # The per-kilo figure is the offer's; so is the item price. Both stay
        # as they are, flagged — an average can then leave offers out.
        pass
    p.pack = from_name(raw_name)
    return _fill_from_pack(p)


# ── Consum ───────────────────────────────────────────────────────────────
#   raw_price "2.99 €", raw_unit_price "6.5 €/1 Kg" | "€/100 ml" | "€/1 L" |
#   "€/1 U" | "€/100 Gr" | "€/1 Dc" (dozen)

CONSUM_UNITS = {
    '1 kg': ('kg', 1), '100 gr': ('kg', 10), '100 g': ('kg', 10),
    '1 l': ('l', 1), '100 ml': ('l', 10),
    '1 u': ('unit', 1), '1 dc': ('dozen', 1), '1 do': ('dozen', 1),
}


def consum(raw_price, raw_unit_price, raw_name):
    p = Price()
    m = re.search(NUM, raw_price or '')
    if m:
        p.item = num(m.group(1))
    m = re.match(r'\s*' + NUM + r'\s*€\s*/\s*(.+?)\s*$', raw_unit_price or '')
    if m:
        unit = CONSUM_UNITS.get(m.group(2).lower())
        if unit:
            p.per[unit[0]] = round(num(m.group(1)) * unit[1], 4)
    p.pack = from_name(raw_name)
    return _fill_from_pack(p)


# ── Anything else: an item price, and a pack size from the name ─────────

def generic(raw_price, raw_unit_price, raw_name):
    p = Price()
    m = re.search(NUM, raw_price or '')
    if m:
        p.item = num(m.group(1))
    p.pack = from_name(raw_name)
    return _fill_from_pack(p)


# ── Structured: what new shop sources store ─────────────────────────────
#   raw_price "item=2.49;per_kg=4.98;regular=2.99"
# Any of item, per_kg, per_l, per_dozen, per_unit, regular; numbers with a
# dot. A source that already knows its prices writes them this way, and the
# pack size still comes from the name where the source gives none.

def structured(raw_price, raw_unit_price, raw_name):
    p = Price()
    fields = dict(kv.split('=', 1) for kv in raw_price.split(';') if '=' in kv)
    f = {k.strip(): float(v) for k, v in fields.items() if v.strip()}
    p.item = f.get('item')
    for k, basis in (('per_kg', 'kg'), ('per_l', 'l'), ('per_dozen', 'dozen'), ('per_unit', 'unit')):
        if f.get(k):
            p.per[basis] = f[k]
    if f.get('regular') and p.item and f['regular'] > p.item:
        p.regular, p.promo = f['regular'], True
    p.pack = from_name(raw_name)
    return _fill_from_pack(p)


READERS = {'Mercadona': mercadona, 'Eroski': eroski, 'Consum': consum}


def read(chain, raw_price, raw_unit_price, raw_name):
    if (raw_price or '').startswith('item=') or (raw_price or '').startswith('per_'):
        return structured(raw_price, raw_unit_price or '', raw_name or '')
    return READERS.get(chain, generic)(raw_price or '', raw_unit_price or '', raw_name or '')
