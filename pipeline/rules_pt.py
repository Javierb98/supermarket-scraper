"""
Portuguese shelf names → catalogue products.

Written for Continente's names ("Maçã Gala Continente, emb. 1 kg",
"Perna de Frango com Costa Continente, emb. 900 gr (aprox.)") and plain
enough for Pingo Doce's or Auchan's later.

Every rule is anchored at the start of the name, after nothing but plain
words ("mini", "metade", "biológico"): a product named after something else
is that something else — "Mix Maçã e Pera", "Salada de Manga",
"Preparado para Sopa de Alho Francês", "Palitos de Cenoura".

The catalogue's Portuguese names are plural ("Maçãs", "Laranjas") where
shelves are singular ("Maçã Fuji"), which is why the catalogue fallback in
the matcher alone found almost no fruit; these rules close that gap.

A rule whose product the catalogue does not have (Iceberg lettuce, white
cabbage, "queijo fresco") still matches, pointing at None, so the name does
not fall through to a wrong product; it is counted as 'unlisted'.
"""

import re

LANG = 'pt'

# Plain words a name may start with before the product.
LEADING = ['mini', 'metade', 'metades', 'meia', 'bio', 'biologico', 'biologica', 'novo', 'nova', 'fresco', 'fresca']

LEAD = r'^(?:(?:mini|metade|metades|meia|bio|biol[oó]gic[oa]s?|nov[oa]s?|fresc[oa]s?)\s+)*'


def _a(pattern):
    """Anchored at the start (after the plain words), ending at a word end."""
    return LEAD + r'(?:' + pattern + r')(?![a-zà-ÿ])'


CANNED_SIGNALS = [r'\bem lata\b', r'\bconserva', r'\bfrasco\b', r'\buht\b', r'\bpasteurizad', r'\bem calda\b']
FROZEN_SIGNALS = [r'congelad', r'ultracongelad', r'\bfrozen\b']


def detect_state(raw_name):
    n = raw_name.lower()
    if any(re.search(p, n) for p in FROZEN_SIGNALS):
        return 'frozen'
    if any(re.search(p, n) for p in CANNED_SIGNALS):
        return 'canned'
    return 'fresh'


# Things that look like a product but are a dish, a snack or a preparation.
REJECT = [re.compile(p, re.IGNORECASE) for p in [
    r'\bpreparado\b|\bsopa\b|\bcreme de\b|\bsalada de\b|\bpalitos\b|\bespirais\b|\bsnack\b|\bfloretes\b',
    r'\bralad[oa]\b|\bpara barrar\b|\bpanad[oa]s?\b|\bhamb[uú]rguer|\balm[oô]ndegas\b|\bstrogonoff\b|\bespetadas?\b',
    r'\bsalsichas?\b|\brolo de carne\b|\bfatiad[oa] (?:americano|para)\b|\bdesidratad|\bcristalizad|\bem calda\b',
    r'\bprote[ií]na\b|\bsabor\b|\baroma\b|\bdoce (?:de )?(?:ab[oó]bora|frutos)\b|\bem azeite\b|\bconservad[oa] em\b',
    # cut, cubed or ready-to-cook: not the price of the thing itself
    r'\bripad[oa]s?\b|\bcubos\b|\bgomos\b|\bairfryer\b|\bmarinad|\bassad[oa]s?\b|\bem tiras\b|\b[aà]s tiras\b',
    r'\bsupreme\b|\bfrubis\b|\bpeda[cç]os\b|(?:abacaxi|anan[aá]s|manga|mel[aã]o|melancia|papaia|mam[aã]o)\s+fatiad',
]]

# Organic produce is its own product where the catalogue has one, and is
# otherwise kept out: a 250 g organic cucumber at 10 €/kg next to two
# ordinary ones is not "the price of cucumbers".
_ORGANIC = r'.*\b(?:biol[oó]gic[oa]s?|bio)\b'
_ORGANIC_RULES = [
    (r'^(?:mini\s+)?tomates?\b' + _ORGANIC, 'Organic Tomatoes'),
    (r'^espinafres?\b' + _ORGANIC, 'Organic Spinach'),
    (r'^alfaces?\b' + _ORGANIC, 'Organic Lettuce'),
    (r'^acelgas?\b' + _ORGANIC, 'Organic Chard'),
    (r'^ovos?\b' + _ORGANIC, 'Organic Eggs'),          # no catalogue product without a size
    (r'^' + _ORGANIC, 'Organic'),                        # anything else organic: not compared
]

_RULES = [
    # ---- eggs ----
    (r'ovos? de codorniz', 'Quail Eggs'),
    (r'claras? de ovos?', 'Egg Whites'),
    (r'ovos? inteiros? pasteurizados?|ovos? l[ií]quidos?', 'Liquid Eggs'),
    (r'ovos?', 'Eggs'),

    # ---- poultry: cuts before birds ----
    (r'peitos? de frango|bifes? de frango|lombinhos? de frango|filetes? de frango', 'Chicken Breast'),
    (r'perninhas? de frango|pernas? de frango', 'Chicken Drumsticks'),
    (r'coxas? de frango|sobrecoxas? de frango', 'Chicken Thigh'),
    (r'as(?:inh)?as? de frango', 'Chicken Wings'),
    (r'f[ií]gados? de frango', 'Chicken Liver'),
    (r'moelas? de frango', 'Chicken Gizzard'),
    (r'frango (?:do campo )?inteiro|frango para churrasco|frango (?:do campo )?com mi[uú]dos', 'Whole Chicken'),
    (r'peitos? de peru|bifes? de peru|escalopes? de peru|lombinhos? de peru', 'Turkey Breast'),
    (r'perninhas? de peru|pernas? de peru|coxas? de peru', 'Turkey Legs'),
    (r'asas? de peru', 'Turkey Wings'),
    (r'peitos? de pato|magret', 'Duck Breast'),
    (r'pernas? de pato|coxas? de pato', 'Duck Leg'),
    (r'(?:\w+ de )?coelho(?: inteiro)?|metades de coelho|por[cç][oõ]es de coelho', 'Rabbit Meat'),

    # ---- meat ----
    (r'entremeada', 'Pork Belly'),
    (r'costeletas? (?:do (?:lombo|cacha[cç]o) )?de porco', 'Pork Chops'),
    (r'(?:tiras de )?entrecosto(?: de porco)?', 'Pork Ribs'),
    (r'p[aá] de porco', 'Pork Shoulder'),
    (r'carne picada de porco', 'Ground Pork'),
    (r'costeletas? (?:mistas )?de borrego', 'Lamb Chops'),
    (r'pernas? de borrego', 'Lamb Leg'),
    (r'p[aá] de borrego|m[aã]o de borrego', 'Lamb Shoulder'),
    (r'(?:metades|quartos) de cabrito|cabrito', 'Goat Meat'),
    (r'carne picada de (?:bovino|novilho|vaca)', 'Ground Beef'),
    (r'entrec[oô]te(?: de novilho)?', 'Fresh Ribeye'),
    (r'bifes? da vazia', 'Fresh Striploin'),
    (r'bifes? do lombo de novilho', 'Fresh Tenderloin'),
    (r'bifes? (?:do cora[cç][aã]o )?(?:de |da )?alcatra(?! de borrego)', 'Fresh Sirloin'),

    # ---- dairy ----
    (r'leite (?:uht )?(?:inteiro|gordo)|leite (?:de pastagem )?inteiro', 'Whole Milk'),
    (r'manteiga', 'Butter'),
    (r'queijo (?:curado |amanteigado )?de cabra|queijinhos? de cabra', 'Goat Cheese'),
    (r'queijo (?:curado |amanteigado )?de ovelha|queijinhos? de ovelha|merendeira(?: de ovelha)?|queijo (?:da )?serra', 'Sheep Cheese'),
    (r'(?:queijo )?mozzarell?a d[ie] b[uú]fala', 'Buffalo Mozzarella'),
    (r'(?:queijo )?mozzarell?a', 'Mozzarella'),
    (r'(?:queijo )?ricotta', 'Ricotta'),
    (r'queijo (?:de |da )?(?:ovelha )?(?:azeit[aã]o|[eé]vora|serpa|nisa)', 'Sheep Cheese'),
    (r'requeij[aã]o', 'Fresh Cottage Cheese'),       # the catalogue's own Portuguese name
    (r'queijo fresco', 'Queijo Fresco'),              # no catalogue product
    (r'queijo', 'Queijo'),                            # any other cheese: too general to compare
    (r'mel', 'Honey'),
    (r'azeite', 'Olive Oil'),

    # ---- fruit ----
    (r'bananas?[- ]p[aã]o', 'Plantain'),
    (r'bananas?', 'Banana'),
    (r'ma[cç][aã]s? pink lady', 'Pink Lady Apples'),
    (r'ma[cç][aã]s?', 'Apples'),
    (r'peras? nashi', 'Nashi Pear'),                 # no catalogue product
    (r'peras?', 'Pears'),
    (r'clementinas?(?:/mandarinas?)?', 'Clementine'),
    (r'mandarinas?|tangerinas?', 'Mandarin Oranges Fresh'),
    (r'laranjas? sangu[ií]neas?', 'Blood Oranges'),
    (r'laranjas?', 'Oranges'),
    (r'lim[aã]o|lim[oõ]es', 'Lemons'),
    (r'limas?', 'Lime'),
    (r'toranjas?', 'Grapefruit'),                    # no catalogue product
    (r'kiwis?', 'Kiwi'),
    (r'uvas? brancas? sem grainha', 'Green Grapes Seedless'),
    (r'uvas? (?:rosadas?|pretas?|tintas?)(?: ou preta)? sem grainha', 'Red Grapes Seedless'),
    (r'uvas? red globe|uvas? (?:pretas?|tintas?)', 'Grapes Red'),
    (r'uvas? brancas?', 'Grapes Green'),
    (r'p[eê]ssegos?', 'Peaches'),
    (r'ameixas?', 'Plums'),
    (r'morangos?', 'Strawberries'),
    (r'mirtilos?', 'Blueberries'),
    (r'framboesas?', 'Raspberry'),
    (r'amoras?', 'Blackberries'),
    (r'mel[aã]o|mel[oõ]es', 'Melon'),
    (r'melancias?', 'Watermelon'),
    (r'abacaxis?|anan[aá]s', 'Pineapple'),
    (r'mangas?', 'Mango'),
    (r'papaias?|mam[aã]o', 'Papaya'),
    (r'maracuj[aá]s?', 'Passion Fruit'),
    (r'abacates?', 'Avocado'),
    (r'di[oó]spiros?', 'Persimmon'),
    (r'rom[aã]s?', 'Pomegranate'),
    (r'figos? da [ií]ndia', 'Prickly Pear'),          # no catalogue product
    (r'figos?', 'Fig'),
    (r'castanhas?', 'Chestnuts'),
    (r'lichias?', 'Lychee'),
    (r'goiabas?', 'Guava'),
    (r'anonas?', 'Custard Apple'),
    (r'cocos?', 'Coconut'),

    # ---- vegetables ----
    (r'tomates? (?:cherry|cereja)', 'Cherry Tomato'),
    (r'tomates? (?:cacho|chucha)', 'Mini Tomatoes'),     # only after "mini": see _MINI
    (r'tomates? cora[cç][aã]o de boi', 'Beefsteak Tomatoes'),
    (r'tomates?', 'Tomato'),
    (r'alfaces? frisadas?', 'Frisée Lettuce'),
    (r'alfaces? romanas?', 'Romaine Lettuce'),
    (r'alfaces?', 'Lettuce'),                            # no catalogue product (iceberg, lisa, roxa)
    (r'batatas? doces?|batata-doce', 'Sweet Potato'),
    (r'batatas? vermelhas?', 'Red Potatoes'),
    (r'batatas?', 'Potato'),
    (r'cebolas? roxas?', 'Red Onion'),
    (r'cebolas? brancas?', 'White Onion'),
    (r'cebolinho', 'Chives'),
    (r'cebolinhas? frescas?', 'Spring Onions'),
    (r'cebolinhas?', 'Pearl Onions'),
    (r'cebolas? chalotas?', 'Shallots'),
    (r'cebolas?', 'Onion'),
    (r'chalotas?|echalotas?', 'Shallots'),
    (r'alho franc[eê]s|alhos franceses', 'Leek'),
    (r'(?:dentes de )?alhos?(?: secos?)?', 'Garlic'),
    (r'cenouras? babys?', 'Baby Carrots'),
    (r'cenouras?', 'Carrot'),
    (r'ab[oó]boras? (?:butternut|manteiga)', 'Butternut Squash'),
    (r'ab[oó]boras?', 'Pumpkin'),
    (r'couve[- ]flor', 'Cauliflower'),
    (r'(?:couve )?br[oó]colos?', 'Broccoli'),
    (r'couves? lombardas?(?:/saboia)?|couves? saboia', 'Savoy Cabbage'),
    (r'couves? roxas?', 'Red Cabbage'),
    (r'couves? chinesas?', 'Napa Cabbage'),
    (r'couves? kale', 'Kale'),
    (r'couves?[- ]de[- ]bruxelas', 'Brussels Sprouts'),
    (r'couves? pak ?choi|pak ?choi', 'Bok Choy'),
    (r'couves?', 'Cabbage'),                             # no catalogue product (branca, coração, portuguesa)
    (r'curgetes?', 'Zucchini'),
    (r'beringelas?', 'Eggplant'),
    (r'pepinos?', 'Cucumber'),
    (r'pimentos?', 'Bell Pepper'),
    (r'malaguetas?|piri piri', 'Chili Pepper'),
    (r'feij[aã]o verde', 'Green Beans'),
    (r'espinafres?(?: baby)?', 'Spinach'),
    (r'agri[aã]o', 'Watercress'),
    (r'r[uú]cula', 'Arugula'),
    (r'nabos?', 'Turnip'),
    (r'beterrabas?', 'Beetroot'),
    (r'rabanetes?', 'Radish'),
    (r'raiz de aipo|aipo[- ]r[aá]bano', 'Celeriac'),
    (r'aipo', 'Celery'),
    (r'funchos? (?:de )?rama', 'Fennel Fronds'),        # the herb, not the bulb: no catalogue product
    (r'funchos?', 'Fennel'),
    (r'cher[oó]vias?|pastinacas?', 'Parsnip'),
    (r'gengibre', 'Fresh Ginger'),
    (r'c[uú]rcuma', 'Fresh Turmeric'),
    (r'cogumelos? (?:branco|paris|champignon)s?', 'White Mushroom'),
    (r'cogumelos? shi(?:i)?take', 'Shiitake Mushroom'),
    (r'cogumelos? (?:pleurotus|pleurothus)', 'Oyster Mushroom'),
    (r'cogumelos? portobello', 'Portobello Mushroom'),
    (r'cogumelos?', 'Other Mushroom'),                   # marron, shimeji, eringi: no catalogue product
    (r'espargos? verdes?', 'Green Asparagus'),
    (r'espargos? brancos?', 'White Asparagus'),
    (r'espargos?', 'Asparagus'),
    (r'quiabos?', 'Okra'),
    (r'chuchus?', 'Chayote'),

    # ---- herbs ----
    (r'manjeric[aã]o', 'Genovese Basil'),
    (r'salsa', 'Parsley'),
    (r'coentros?', 'Cilantro'),
    (r'hortel[aã]', 'Mint'),
    (r'alecrim', 'Rosemary'),
    (r'tomilho', 'Thyme'),
    (r'louro', 'Bay Leaf'),
    (r'or[eé]g[aã]os', 'Oregano'),
    (r'endro|aneto', 'Dill'),
]

# "Mini tomate cacho" is a small vine tomato sold as such; a plain "tomate
# cacho" is an ordinary vine tomato.
_MINI = [
    (r'^mini\s+tomates?\s+(?:cacho|chucha)', 'Mini Tomatoes'),
    (r'^tomates?\s+(?:em\s+)?cacho', 'Vine Tomatoes'),
    (r'^tomates?\s+chucha', 'Plum Tomatoes'),
]

RULES = [(p, name, None, None) for p, name in _ORGANIC_RULES] + \
        [(p, name, None, None) for p, name in _MINI] + \
        [(_a(p), name, None, None) for p, name in _RULES if name != 'Mini Tomatoes']

# Rule names that are not catalogue products: matched, so they cannot fall
# through to something wrong, but kept out of the averages.
TARGETS = {
    'Queijo Fresco': None,
    'Nashi Pear': None,
    'Grapefruit': None,
    'Lettuce': None,
    'Cabbage': None,
    'Other Mushroom': None,
    'Queijo': None,
    'Prickly Pear': None,
    'Fennel Fronds': None,
    'Organic Eggs': None,
    'Organic': None,
}
