"""
Is this a fresh product, or something made from one?

The matcher finds "fresa" in "Gel dental sabor fresa" and "manzana" in
"Papilla pera y manzana". Those were counted as strawberries and apples:
on 2 November a quarter of the fruit, vegetable and egg prices were
processed food or not food at all, and they pushed the apple average from
€3.15 to €5.25 a kilo.

A farm sells the fresh thing, so a fresh product's price is drawn only from
fresh products. These words, in any of the shop's languages, mark the rest.
Tinned and jarred products have rules of their own (they are products too:
"Canned Tomatoes"), so this applies only to what is matched as fresh.
"""

import re

SIGNALS = {
    # Not food at all.
    'nonfood': [
        r'\bgel\b', r'dent[aií]', r'champ[uú]', r'shampoo', r'jab[oó]n', r'colonia', r'desodorante', r'ambientador',
        r'detergente', r'suavizante', r'\bvela\b', r'perfum', r'loci[oó]n', r'mascarilla', r'toallita', r'perro', r'gato',
        r'pienso', r'zahnpasta', r'duschgel', r'seife', r'dentifrice', r'savon', r'dentifricio', r'sapone', r'toothpaste',
        r'\bsoap\b', r'tandpasta', r'\bzeep\b', r'katzen', r'hunde', r'\bchien', r'\bchat\b', r'\bcane\b', r'\bdog\b', r'\bcat\b',
    ],
    'es': [
        r'sabor', r'\bzumo', r'bebida', r'b[ií]fidus', r'papilla', r'pur[eé]\b', r'\bsnack', r'gelatina', r'mermelada', r'confitura',
        r'\btarta', r'galleta', r'helado', r'n[eé]ctar', r'batido', r'yogur', r'\bsalsa', r'\bcrema\b', r'\bchips\b', r'compota',
        r'caramelo', r'chicle', r'infusi[oó]n', r'\bt[eé]\b', r'cereal', r'muesli', r'bizcocho', r'barrita', r'pastel', r'empanad',
        r'tortilla', r'\bwrap', r'pizza', r'croqueta', r'lasa[ñn]a', r's[aá]ndwich', r'bocadillo', r'hummus', r'guacamole',
        r'gazpacho', r'salmorejo', r'\bsopa\b', r'\bcaldo\b', r'\bfrit[ao]s\b', r'deshidratad', r'almíbar', r'alm[ií]bar',
        r'en polvo', r'\baroma', r'licor', r'vinagre', r'\baceite\b', r'chocolate', r'bomb[oó]n', r'turr[oó]n', r'mazap',
        r'rellen[oa]', r'cocinad', r'\bcocid[oa]', r'preparad', r'\bpan\b', r'\bpanes\b', r'smoothie', r'agua\b', r'refresco',
        r'polo\b', r'\btostad', r'\bpatatas? fritas', r'\bfrito\b', r'\bdulce de\b', r'\bpasas\b', r'orej[oó]n', r'confitad',
        r'\bmix de\b', r'bolsita', r'\bpot(?:ito)?\b', r'macedonia', r'frutos secos', r'congelad', r'\bal horno\b', r'a la plancha',
        r'(?<!tomate )(?<!tomates )(?<!tomate de )\bensalada', r'guarnici[oó]n', r'\bwok\b', r'salteado', r'hamburguesa', r'nugget',
        r'molid', r'crujiente', r'caramelizad', r'\bpat[eé]\b', r'pasta fresca', r'focaccia', r'morcilla', r'escalivada',
        r'tri[aá]ngulo', r'granizad', r'sorbete', r'aderezo', r'tinto de verano', r'lavavajillas', r'insecticida', r'limpiador',
        r'friegasuelos', r'gnocchi', r'\bbravas\b', r'prefrit', r'\bstick', r'palitos', r'ruedas', r'\baros\b', r'sazonador',
        r'ondulad', r'\blisas\b', r'campesinas', r'churrer', r'sour cream', r'delicatessen', r'jam[oó]n',
    ],
    'en': [
        r'flavou?r', r'\bjuice', r'\bdrink', r'yogh?urt', r'baby food', r'pur[eé]e', r'\bsnack', r'jelly', r'\bjam\b', r'marmalade',
        r'\bpie\b', r'biscuit', r'cookie', r'ice cream', r'smoothie', r'\bsauce', r'\bcrisps\b', r'\bchips\b',
        r'\btea\b', r'cereal', r'muesli', r'\bcake', r'\bbar\b', r'\bwrap', r'pizza', r'sandwich', r'hummus', r'guacamole', r'\bsoup',
        r'dried', r'in syrup', r'powder', r'vinegar', r'\boil\b', r'stuffed', r'cooked', r'ready meal', r'\bfried',
        r'\braisins', r'candied', r'frozen', r'salad bowl', r'coleslaw', r'stir fry', r'burger', r'nugget',
    ],
    'de': [
        r'geschmack', r'\bsaft', r'getränk', r'joghurt', r'jogurt', r'babynahrung', r'brei\b', r'p[uü]ree', r'\bsnack(?!karott|tomat|gurk|paprika)', r'gelee',
        r'marmelade', r'konfitüre', r'kuchen', r'keks', r'\beis\b', r'smoothie', r'soße', r'sauce', r'chips', r'bonbon', r'\btee\b',
        r'müsli', r'riegel', r'pizza', r'suppe', r'getrocknet', r'pulver', r'essig', r'\böl\b', r'schokolade', r'gefüllt', r'gekocht',
        r'fertig', r'frittiert', r'rosinen', r'kandiert', r'tiefgekühlt', r'\btk[\s-]', r'salatbowl', r'krautsalat', r'pfannen', r'burger',
    ],
    'fr': [
        r'saveur', r'\bgo[uû]t\b', r'\bjus\b', r'boisson', r'yaourt', r'petit pot', r'pur[eé]e', r'compote', r'gel[eé]e', r'confiture',
        r'\btarte', r'biscuit', r'glace', r'smoothie', r'\bsauce', r'\bchips\b', r'bonbon', r'\bth[eé]\b', r'c[eé]r[eé]ale', r'muesli',
        r'g[aâ]teau', r'barre', r'pizza', r'sandwich', r'houmous', r'soupe', r'velout[eé]', r's[eé]ch[eé]', r'au sirop', r'poudre',
        r'vinaigre', r'\bhuile\b', r'chocolat', r'farci', r'cuisin[eé]', r'\bcuit', r'frit', r'raisins secs', r'confit', r'surgel[eé]',
        r'taboul[eé]', r'po[eê]l[eé]e', r'burger', r'nugget',
    ],
    'it': [
        r'gusto', r'\bsucco', r'bevanda', r'yogurt', r'omogeneizzat', r'pur[eè]\b', r'\bsnack', r'gelatina', r'marmellata',
        r'confettura', r'\btorta', r'biscott', r'gelato', r'smoothie', r'\bsalsa', r'\bsugo', r'\bchips\b', r'caramell', r'\bt[eè]\b',
        r'cereali', r'muesli', r'merendin', r'barretta', r'pizza', r'tramezzin', r'hummus', r'zuppa', r'minestr', r'essiccat',
        r'sciroppo', r'polvere', r'aceto', r'\bolio\b', r'cioccolat', r'ripien', r'cott[oaie]\b', r'fritt', r'uvetta', r'candit',
        r'surgelat', r'insalatona', r'burger', r'nugget',
    ],
    'pt': [
        r'sabor', r'\bsumo', r'bebida', r'iogurte', r'papa\b', r'pur[eé]', r'\bsnack', r'gelatina', r'compota', r'doce de',
        r'\bbolo', r'bolacha', r'gelado', r'n[eé]ctar', r'batido', r'smoothie', r'molho', r'\bchips\b', r'rebuçado', r'\bch[aá]\b',
        r'cereais', r'muesli', r'barra', r'pizza', r'sandes', r'h[uú]mus', r'\bsopa', r'desidratad', r'calda', r'\bem p[oó]\b',
        r'vinagre', r'azeite', r'\b[oó]leo\b', r'chocolate', r'recheado', r'cozid', r'frit', r'passas', r'cristalizad', r'congelad',
        r'hamb[uú]rguer', r'nugget',
    ],
    'nl': [
        r'smaak', r'\bsap\b', r'drank', r'drink', r'yoghurt', r'babyvoeding', r'pur[eé]e', r'\bsnack', r'gelei', r'\bjam\b',
        r'taart', r'koek', r'\bijs\b', r'smoothie', r'\bsaus', r'chips', r'snoep', r'\bthee\b', r'muesli', r'reep', r'pizza',
        r'soep', r'gedroogd', r'poeder', r'azijn', r'\bolie\b', r'chocolade', r'gevuld', r'gekookt', r'kant[- ]en[- ]klaar',
        r'gefrituurd', r'rozijn', r'gekonfijt', r'diepvries', r'rauwkost', r'roerbak', r'burger', r'nugget',
    ],
}

# English words are checked on every shelf name, whatever its language, so
# they must not be variety names elsewhere: "Super Sweet" pineapples and
# "Chocolate" tomatoes are fresh.
COMPILED = {k: re.compile('|'.join(v), re.I) for k, v in SIGNALS.items()}

# Catalogue categories whose products must be priced from the plain product:
# everything but tinned goods (which are their own products) and herbs and
# spices (which are rightly sold dried and ground).
FRESH_CATEGORIES = {'vegetables', 'fruit', 'eggs', 'dairy', 'meat', 'poultry'}


def why_processed(name, lang):
    """The kind of signal found ('nonfood' or the language), or None."""
    n = name.lower()
    if COMPILED['nonfood'].search(n):
        return 'nonfood'
    for l in (lang, 'en'):
        rx = COMPILED.get(l)
        if rx and rx.search(n):
            return l
    return None


# Shop aisles fresh fruit and vegetables are sold in, and aisles that look
# like it but are not. Used where a shop says which aisle a product is in.
FRESH_AISLE = re.compile(
    r'frut|verdur|hortaliz|cebolla|ajo|puerro|patata|tomate|lechug|seta|champi|hongo|arom[aá]tic|tub[eé]rculo|c[ií]tric|'
    r'temporada|ex[oó]tic|fruit|vegetable|veg\b|produce|obst|gemüse|l[eé]gume|frutta|verdur|fruta|legume|groente|fruit|'
    r'köögivil|puuvil|juurvil|marjad|seened|frukt|grønt|grönt|grønnsak|grönsak|vo[cć]e|povr[cć]e|воће|поврће|λαχανικ|φρούτ|φρουτ', re.I)
NOT_FRESH_AISLE = re.compile(
    r'congelad|zumo|conserva|deshidrat|frutos secos|helad|surgel|frozen|juice|tinned|canned|dried|tiefkühl|konserv|frit[ao]s|snack|aperitiv|crisps|'
    r'jus|conserve|surgelat|succo|sumo|diepvries|ingeblikt', re.I)


def aisle_is_fresh(aisle):
    """True / False where the aisle says, None where there is no aisle."""
    if not aisle:
        return None
    return bool(FRESH_AISLE.search(aisle)) and not NOT_FRESH_AISLE.search(aisle)
