"""
Dutch shelf names → catalogue products.

The catalogue has no Dutch names, so for Dutch shops these rules are the only
way a shelf name meets a catalogue product. They are written for the names
the Dutch chains use (checkjebon.nl's daily file: AH, Jumbo, Plus, Dirk,
Hoogvliet, Spar, DekaMarkt, Poiesz, Vomar), and for Flemish shelves later.

Every rule is anchored at the start of the name: the product must come
first, after nothing but the shop's own brand ("AH", "Jumbo", "1 de Beste",
"g'woon") and plain words such as "biologisch", "verse" or a colour. A
product named after another brand is that brand's product, not the fresh
thing: "Heinz Tomaten ketchup", "Wahid kipfilet" (sliced, halal cold cuts),
"Aarts Champignons" (a jar). This costs a few genuine fresh products from
other brands and keeps out a great many that are not.

Dutch writes compounds as one word ("scharreleieren", "rundergehakt",
"kipfilet"), so the patterns match word starts and whole compounds rather
than the separate words a Romance language would use.
"""

import re

LANG = 'nl'

# Words a Dutch shelf name may start with that are not the product: the
# chains' own brands and plain descriptions. Used by the anchored rules
# below and, through LEADING, by the matcher.
LEADING = [
    'ah', 'jumbo', 'jumbos', 'plus', 'spar', 'dirk', 'hoogvliet', 'dekamarkt', 'dekavers', 'vomar', 'poiesz',
    'lidl', 'aldi', 'coop', 'picnic', 'g', 'woon', 'gwoon', 'de', 'beste', 'boerentrots', 'excellent',
    'bio', 'biologisch', 'biologische', 'eko', 'demeter', 'verse', 'vers',
    'hollandse', 'nederlandse', 'nl', 'los', 'losse', 'grote', 'groot', 'kleine', 'hand', 'handige',
    'rode', 'rood', 'gele', 'geel', 'groene', 'groen', 'witte', 'wit', 'blauwe', 'zwarte', 'oranje',
    'scharrel', 'vrije', 'uitloop', 'kip', 'kipster', 'jonge', 'seizoens', 'echte', 'heerlijke', 'gewassen',
    'melkan', 'melkunie', 'campina', 'arla', 'kaasstuk',
]

_LEAD_WORDS = sorted({w for w in LEADING if len(w) > 1} | {"g'woon", '1', 'bio+', "jumbo's", 'vrije uitloop'},
                     key=len, reverse=True)
LEAD = r"^(?:(?:" + '|'.join(re.escape(w) for w in _LEAD_WORDS) + r")[\s\-:,.]+)*"


def _a(pattern):
    """A pattern anchored at the start of the name, after the leading words,
    and ending where a word ends: "ananas" is not "ananassap"."""
    return LEAD + r'(?:' + pattern + r')(?![a-zà-ÿ])'


CANNED_SIGNALS = [r'\bblik\b', r'\bin pot\b', r'\bglas\b', r'\bpot\b', r'\bpak\b.*\bhoudbaar\b', r'\bconserv',
                  r'\bop sap\b', r'\bop siroop\b', r'\bzuur\b', r'\bingemaakt']
FROZEN_SIGNALS = [r'diepvries', r'bevroren', r'\bijs\b', r'\bfrozen\b', r'\btk\b']


def detect_state(raw_name):
    n = raw_name.lower()
    if any(re.search(p, n) for p in FROZEN_SIGNALS):
        return 'frozen'
    if any(re.search(p, n) for p in CANNED_SIGNALS):
        return 'canned'
    return 'fresh'


# Names that are never a fresh product, whatever they start with. The shared
# processed-food list (pipeline/processed.py) catches more; these are the
# Dutch words it does not have.
REJECT = [re.compile(p, re.IGNORECASE) for p in [
    # prepared, cut or cooked
    r'salade', r'\bsla\s*mix|slamix|maaltijd', r'soep', r'saus', r'ketchup', r'dressing', r'pesto',
    r'tapenade', r'spread', r'smeerbaar', r'\bdip\b', r'hummus', r'kroket', r'frites', r'friet', r'wedges', r'r[oö]sti',
    r'partjes', r'schijfjes', r'blokjes', r'reepjes', r'stukjes', r'plakjes', r'plakken', r'\bgesneden', r'geraspt',
    r'fijngesneden', r'spiralen', r'spaghetti', r'rijst', r'puree', r'stamppot', r'gratin', r'schotel', r'ovenschotel',
    r'wokgroente', r'roerbak', r'\bwok\b', r'\bmix\b', r'mengsel', r'gegrild', r'geroosterd', r'gerookt', r'gebraden',
    r'gekookt', r'voorgekookt', r'gestoomd', r'gebakken', r'gemarineerd', r'(?<!on)gekruid', r'gepaneerd', r'gevuld',
    r'gepeld', r'gezeefd', r'geconcentreerd', r'concentraat', r'gedroogd', r'zongedroogd', r'ingelegd', r'zoetzuur',
    r'opbak', r'a la minute', r'à la minute', r'flinterdun', r'vleeswaren', r'\bbeleg\b', r'carpaccio', r'shoarma', r'gyros',
    r'sat[eé]', r'spies', r'burger', r'schnitzel', r'cordon', r'nugget', r'haasjes', r'rollade', r'rolletjes', r'balletjes',
    r'worst', r'pat[eé]\b', r'kant\s*en\s*klaar', r'\bwrap', r'pizza', r'broodje', r'\bbrood', r'taart', r'\bcake',
    r'koek', r'gebak', r'snack', r'chips', r'crisps', r'popcorn', r'sap\b', r'nectar', r'smoothie',
    r'limonade', r'siroop', r'\bjam\b', r'compote', r'appelmoes', r'moes\b', r'vla\b', r'pudding', r'\bkwark', r'yoghurt',
    r'toetje', r'dessert', r'\bijs', r'sorbet', r'chocola', r'snoep(?!groente|tomaat|tomaten)', r'drop\b', r'poeder',
    r'gemalen', r'kruiden\b', r'smaak', r'aroma', r'\bthee', r'koffie', r'olie\b', r'azijn', r'mosterd', r'mayonaise',
    r'babyvoeding', r'olvarit', r'bonb[eé]b[eé]', r'\b\d+\+?\s*m(nd|aanden)\b', r'knijpfruit', r'fruithapje',
    r'protein', r'proteine', r'lactosevrij', r'lactofree', r'houdbaar', r'langlekker', r'\bdrink', r'drank',
    r'kerst(?!omat)', r'paas', r'chocolade', r'aardappel\s*anders', r'b[oö]rek', r'pancake', r'pannenkoek', r'bavarois',
    r'schnitte', r'slofje', r'flap', r'muffin', r'wafel', r'roosjes', r'tompouce', r'bonbon', r'cocktail', r'spiesj',
    r'sticks?\b', r'bekertje', r'fruitbak', r'fruitsalade', r'sushi', r'poke', r'quiche', r'lasagne', r'ovenklaar',
    r'pulled', r'bouillon', r'fond\b', r'marinade', r'kruidenmix', r'goulash', r'stoof(?!pe)', r'hachee',
    r'\bmet\b', r'ijsjes', r'schepijs', r'roomijs', r'waterijs', r'\bshot\b', r'berliner', r'cornet', r'vlaai', r'kaneel',
    r'schuim', r'soesjes', r'kano\'?s\b', r'spritsen', r'krakeling', r'croissant', r'carr[eé]e', r'cakeje', r'tongen',
    r'kletsmajoor', r'koggetje', r'amandel', r'jan\s*hagel', r'pasteibak', r'stengels', r'assorti', r'biesjes', r'rozetjes',
    r'kuikentjes', r'appelster', r'hoef\b', r'selectie', r'picolien', r'\bbollen\b', r'romeo', r'specu', r'specpop',
    r'eiercake', r'marmer', r'custard', r'doublies', r'ragout', r'champignon\s*steak', r'snippers', r'chutney', r'crouton',
    r'passata', r'cr[eè]me', r'(?:fijn|grof)\s*gehakt', r'\bvdv\b', r'\brasp\b', r'halvarine', r'zonne\s*pond',
    r'volle\s*pond', r'\blight\b', r'bewust', r'\bblend\b', r'halfvol\b', r'\bcups\b', r'cupjes', r'kuipjes',
    r'zonder\s*pit', r'ready\s*to\s*eat', r'bolletjes', r'\s&\s', r'kruidenboter', r'blaq', r'escargot', r'steak\s*peper',
    r'krokant', r'julienne', r'tortilla', r'spuitbus', r'schnitt', r'truffel', r'\bnaturel\b', r'\bpittig', r'bieslook', r'jalape', r'vegetarisch', r'vegan', r'plantaardig',
    # not food, or not to eat
    r'plant', r'kweekset', r'zaden', r'\bzaad\b', r'bloembol', r'\bbos bloemen', r'geur', r'kaars', r'shampoo', r'douche',
    r'zeep', r'wasmiddel', r'afwas', r'mesje', r'hond', r'\bkat\b', r'katten', r'vogel', r'dieren',
]]


class _TwoFruits:
    """A fruit cup or a juice names two fruits: "Ananas appel druif", "Appel-peer"."""
    FRUIT = re.compile(r'(ananas|appel|aardbei|banaan|bananen|bes\b|bessen|cantaloupe|citroen|druif|druiven|framboos|'
                       r'frambozen|kiwi|limoen|mandarijn|mango|meloen|papaja|papaya|passievrucht|peer|peren|perzik|'
                       r'pruim|sinaas|watermeloen|kers\b|kersen)', re.I)

    def search(self, name):
        found = {m.group(1).lower() for m in self.FRUIT.finditer(name)}
        found = {'peer' if f == 'peren' else 'banaan' if f == 'bananen' else f for f in found}
        if {'appel', 'sinaas'} <= found or {'appel', 'granaat'} <= found:
            found.discard('appel')
        if 'meloen' in found and 'watermeloen' in found:
            found.discard('meloen')
        return len(found) >= 2


# A fruit a farm sells whole, in a pack of under half a kilo, is cut fruit:
# "AH Ananas, 150 g" is a tub of pieces at €15 a kilo.
_CUT_FRUIT = re.compile(r'\b(ananas|mango|meloen|watermeloen|papaja|papaya|kokos\w*)\b.*,\s*(?:ca\.?\s*)?\d{1,3}\s*g(?:ram)?\s*$', re.I)


class _SmallPack:
    """A product in a pack smaller than it is sold fresh in: a 125 g pack of
    "kipfilet" is sliced chicken for sandwiches, a 180 g tub of "tomaten" is
    snack tomatoes, "AH Ananas, 150 g" is cut pineapple at €15 a kilo."""
    SIZE = re.compile(r'(?<![\d.,])(\d{1,4})\s*(?:g|gr|gram|grams)\b\.?(?!\s*x)', re.I)

    def __init__(self, product, min_grams):
        self.product = re.compile(product, re.I)
        self.min_grams = min_grams

    def search(self, name):
        if not self.product.search(name):
            return False
        sizes = [int(m.group(1)) for m in self.SIZE.finditer(name)]
        return bool(sizes) and max(sizes) < self.min_grams


REJECT += [
    _TwoFruits(),
    _SmallPack(r'ananas|mango|meloen|papaja|papaya|kokos|granaatappel', 1000),
    _SmallPack(r'^(?:ah|jumbo|plus|spar|dirk|hoogvliet|dekamarkt|vomar|poiesz|g\'woon|\s)*\s*(?:tomaten|tomaat)\b', 250),
    _SmallPack(r'rode\s*kool|rodekool', 1000),        # a jar, or shredded
    _SmallPack(r'kipfilet|kipdij|kalkoenfilet|biefstuk|ossenhaas|entrec|rib\s*eye|ribeye|varkens|runder|lams|eendenborst', 150),
]


# (pattern, rule name, old category, old id). Most specific first: the first
# match wins.
_RULES = [
    # ---- EGGS ----
    (r'kwartel\s*eieren|kwarteleitjes', 'Quail Eggs'),
    (r'eenden\s*eieren', 'Duck Eggs'),
    (r'(?:scharrel|kooivrije|kip)?\s*eieren', 'Eggs'),

    # ---- DAIRY ----
    (r'volle\s*melk', 'Whole Milk'),
    (r'magere\s*melk', 'Skim Milk'),
    (r'halfvolle\s*melk', 'Semi-skimmed Milk'),
    (r'karnemelk', 'Buttermilk'),
    (r'geitenmelk', 'Goat Milk'),
    (r'(?:boeren|room|ongezouten|gezouten)?\s*boter\b|roomboter', 'Butter'),
    (r'slagroom', 'Cream'),
    (r'kookroom', 'Cooking Cream'),
    (r'(?:jong|jong\s*belegen|belegen|extra\s*belegen|oud|oude|overjarige)?\s*(?:goudse|gouda(?!\'s))(?:\s*kaas)?', 'Gouda Cheese'),
    (r'(?:jong|jong\s*belegen|belegen|extra\s*belegen|oud|oude|overjarige?)\s*(?:48\+?\s*)?kaas\b', 'Gouda Cheese'),
    (r'edammer|edam\b', 'Edam Cheese'),
    (r'geitenkaas', 'Goat Cheese'),
    (r'feta\b', 'Feta Cheese'),
    (r'buffel\s*mozzarella|mozzarella\s*di\s*bufala', 'Buffalo Mozzarella'),
    (r'mozzarella', 'Mozzarella'),
    (r'ricotta', 'Ricotta'),
    (r'mascarpone', 'Mascarpone'),
    (r'parmezaan|parmigiano', 'Parmesan'),
    (r'cheddar', 'Cheddar Cheese'),
    (r'cottage\s*cheese|h[uü]ttenk[aä]se', 'Fresh Cottage Cheese'),
    (r'roomkaas', 'Cream Cheese'),
    (r'skyr', 'Skyr'),

    # ---- POULTRY ----
    (r'kipfilet|kippenborst|kipborst', 'Chicken Breast'),
    (r'kippendij(?:en|filet)?|kipdij(?:en|filet)?|dijfilet', 'Chicken Thigh'),
    (r'kippenvleugel|kipvleugel|vleugeltjes', 'Chicken Wings'),
    (r'drumsticks?|kippenpoot|kippenpoten|kippenbout|kipbout', 'Chicken Drumsticks'),
    (r'hele\s*kip|kip\s*heel|braadkip|soepkip', 'Whole Chicken'),
    (r'kippenlever|kiplever', 'Chicken Liver'),
    (r'kalkoenfilet|kalkoenborst', 'Turkey Breast'),
    (r'eendenborst|eendfilet', 'Duck Breast'),

    # ---- MEAT ----
    (r'runder\s*gehakt|rundgehakt', 'Ground Beef'),
    (r'varkens\s*gehakt', 'Ground Pork'),
    (r'biefstuk|kogelbiefstuk|rundersteak|runder\s*steak|sukadelap', 'Beef Steak'),
    (r'rib\s*eye|ribeye|entrec[oô]te', 'Fresh Ribeye'),
    (r'ossenhaas', 'Fresh Tenderloin'),
    (r'runderlappen|riblappen', 'Fresh Chuck Roast'),
    (r'runderlever', 'Beef Liver'),
    (r'karbonade|varkenskotelet|schouderkarbonade|haaskarbonade', 'Pork Chops'),
    (r'speklappen|buikspek|varkensbuik|procureur', 'Pork Belly'),
    (r'spareribs|varkensribben', 'Pork Ribs'),
    (r'varkensschouder', 'Pork Shoulder'),
    (r'lamskotelet|lamskarbonade|lamsrack', 'Lamb Chops'),
    (r'lamsbout', 'Lamb Leg'),
    (r'lamsschouder', 'Lamb Shoulder'),
    (r'konijn', 'Rabbit Meat'),
    (r'hertenbiefstuk|hertenvlees|hert\b', 'Venison'),

    # ---- VEGETABLES: tomatoes ----
    (r'cherry\s*tros\s*tomaten|cherry\s*trostomaten|cherrytomaten|cherry\s*tomaten|kerstomaten|kers\s*tomaten|'
     r'snoep\s*tomaten|snoeptomaatjes|snoeptomaten', 'Cherry Tomato'),
    (r'tros\s*tomaten|trostomaten', 'Vine Tomatoes'),
    (r'roma\s*tomaten|romatomaten|pruim\s*tomaten|pruimtomaten|san\s*marzano', 'Plum Tomatoes'),
    (r'vleestomaten|vlees\s*tomaten|vleestomaat', 'Beefsteak Tomatoes'),
    (r'(?:hollandse\s*)?tomaten|tomaat', 'Tomato'),

    # ---- VEGETABLES: the rest ----
    (r'komkommers?', 'Cucumber'),
    (r'puntpaprika|snack\s*paprika|minipaprika|mini\s*paprika|paprikapoeder|paprikamix|paprika\s*mix', 'Pointed or Snack Pepper'),
    (r'paprika(?:\'s)?', 'Bell Pepper'),
    (r'courgettes?', 'Zucchini'),
    (r'zoete\s*aardappel(?:en)?|zoete\s*aardappels?|bataat', 'Sweet Potato'),
    (r'aardappel(?:en|s)?\s*zoet', 'Sweet Potato'),
    (r'krieltjes|kriel\s*aardappel(?:en|s)?|aardappel(?:en|s)?\s*(?:mini\s*)?kriel\w*', 'Mini Potatoes'),
    (r'(?:(?:iets\s*)?kruimige|vastkokende|nieuwe|roodschillige|bildstar|opperdoezer|frieslander|eigenheimer|nicola|gewassen|ongewassen)?\s*aardappel(?:en|s)?\b', 'Potato'),
    (r'rode\s*ui(?:en)?\b', 'Red Onion'),
    (r'zilveruitjes|bosui|lente\s*ui', 'Spring Onions'),
    (r'sjalot(?:ten)?', 'Shallots'),
    (r'(?:gele\s*)?ui(?:en)?\b|uien\b', 'Onion'),
    (r'knoflook\b', 'Garlic'),
    (r'winterpeen|bospeen|waspeen|wortel(?:en|s)?\b|peen\b', 'Carrot'),
    (r'broccoli', 'Broccoli'),
    (r'bloemkool', 'Cauliflower'),
    (r'(?:verse\s*)?spinazie|bladspinazie', 'Spinach'),
    (r'boerenkool', 'Kale'),
    (r'butternut|flespompoen', 'Butternut Squash'),
    (r'pompoen', 'Pumpkin'),
    # Most Dutch beetroot is sold cooked; only raw ("los", "rauw") is a farm's.
    (r'(?:rode\s*)?bie(?:ten|tjes|t)\s*(?:los|rauw|ongekookt)', 'Beetroot'),
    (r'(?:rode\s*)?bie(?:ten|tjes|t)', 'Cooked Beetroot'),
    (r'bleekselderij|selderijstengels', 'Celery'),
    (r'knolselderij', 'Celeriac'),
    (r'prei\b', 'Leek'),
    (r'radijs(?:jes)?', 'Radish'),
    (r'venkel', 'Fennel'),
    (r'aubergines?', 'Eggplant'),
    (r'(?:mei)?rapen\b|raap\b|meiraap', 'Turnip'),
    (r'pastinaak', 'Parsnip'),
    (r'snijbiet', 'Swiss Chard'),
    (r'paksoi|pak\s*choi|bok\s*choy', 'Bok Choy'),
    (r'chinese\s*kool', 'Napa Cabbage'),
    (r'rode\s*kool|rodekool', 'Red Cabbage'),
    (r'savooiekool|savooie\s*kool', 'Savoy Cabbage'),
    (r'witte\s*kool|spitskool|zuurkool', 'White or Pointed Cabbage'),
    (r'spruitjes|spruiten', 'Brussels Sprouts'),
    (r'ma[iï]skolf|ma[iï]skolven|ma[iï]s\s*kolf', 'Sweet Corn'),
    (r'kastanje\s*champignons|kastanjechampignons|bruine\s*champignons', 'Chestnut Mushroom'),
    (r'portobello', 'Portobello Mushroom'),
    (r'oesterzwam(?:men)?', 'Oyster Mushroom'),
    (r'shii?take', 'Shiitake Mushroom'),
    (r'enoki', 'Enoki Mushroom'),
    (r'(?:witte\s*)?champignons?|champignon', 'White Mushroom'),
    (r'waterkers', 'Watercress'),
    (r'rucola', 'Arugula'),
    (r'witlof', 'Endive'),
    (r'radicchio', 'Radicchio'),
    (r'(?:verse\s*)?gember', 'Fresh Ginger'),
    (r'koolrabi', 'Kohlrabi'),
    (r'romanesco', 'Romanesco'),
    (r'sperziebonen|haricots\s*verts|boontjes', 'Green Beans'),
    (r'peultjes', 'Snow Peas'),
    (r'sugar\s*snaps?', 'Sugar Snap Peas'),
    (r'tuinbonen', 'Fava Beans'),
    (r'groene\s*asperges', 'Green Asparagus'),
    (r'(?:witte\s*)?asperges', 'White Asparagus'),
    (r'romaine\s*sla|romeinse\s*sla|romaine\b', 'Romaine Lettuce'),
    (r'little\s*gem|mini\s*romaine', 'Mini Romaine'),
    (r'eikenblad\s*sla|eikenbladsla', 'Oak Leaf Lettuce'),
    (r'fris[eé]e\s*sla|fris[eé]e\b|krulandijvie', 'Frisée Lettuce'),
    (r'ijsbergsla|ijsberg|veldsla|kropsla|andijvie', 'Iceberg or Other Lettuce'),
    (r'(?:rode\s*)?pepers?\b|chilipepers?|chili\s*pepers?|spaanse\s*pepers?', 'Chili Pepper'),
    (r'jalape[nñ]o', 'Jalapeño'),
    (r'artisjok(?:ken)?', 'Artichoke'),
    (r'mierikswortel', 'Horseradish'),
    (r'aardpeer|aardperen|topinamboer', 'Jerusalem Artichoke'),
    (r'schorseneren', 'Salsify'),
    (r'okra', 'Okra'),

    # ---- FRUIT ----
    (r'pink\s*lady', 'Pink Lady Apples'),
    (r'handsinaasappel(?:s|en)?|sinaasappel(?:s|en)?|sinaas\s*appel(?:s|en)?|perssinaasappel(?:s|en)?', 'Oranges'),
    (r'bloedsinaasappel(?:s|en)?', 'Blood Oranges'),
    (r'granaatappel(?:s|en)?|granaatappelpitjes', 'Pomegranate'),
    (r'(?:elstar|jonagold|jonagored|junami|kanzi|braeburn|granny\s*smith|golden|gala|fuji|santana|wellant|'
     r'evelina|rode\s*boskoop|goudrenet|cox|tentation|honeycrisp)?\s*appel(?:s|en)?\b|handappel(?:s|en)?', 'Apples'),
    (r'(?:conference|doyenn[eé]|gieser\s*wildeman|comice|williams|stoof)?\s*peren\b|peer\b|handperen', 'Pears'),
    (r'bananen|banaan', 'Banana'),
    (r'mandarijn(?:en)?', 'Mandarin Oranges Fresh'),
    (r'clementine(?:s|n)?', 'Clementine'),
    (r'citroen(?:en)?\b', 'Lemons'),
    (r'limoen(?:en)?\b|limes?\b', 'Lime'),
    (r'aardbeien', 'Strawberries'),
    (r'blauwe\s*bessen|bosbessen', 'Blueberries'),
    (r'frambo(?:os|zen)', 'Raspberry'),
    (r'bramen', 'Blackberries'),
    (r'rode\s*bessen', 'Red Currant'),
    (r'zwarte\s*bessen', 'Black Currant'),
    (r'kruisbessen', 'Gooseberry'),
    (r'(?:witte|groene)\s*(?:pitloze\s*)?druiven', 'Grapes Green'),
    (r'(?:rode|blauwe)\s*(?:pitloze\s*)?druiven', 'Grapes Red'),
    (r'kiwi(?:\'s|s)?\b|kiwibes', 'Kiwi'),
    (r'mango(?:\'s|s)?\b', 'Mango'),
    (r'ananas', 'Pineapple'),
    (r'avocado(?:\'s|s)?\b', 'Avocado'),
    (r'watermeloen(?:en)?', 'Watermelon'),
    (r'(?:galia|cantaloupe|honing|piel\s*de\s*sapo|charentais)?\s*meloen(?:en)?', 'Melon'),
    (r'perzik(?:ken)?|platte\s*perzik', 'Peaches'),
    (r'pruim(?:en)?\b', 'Plums'),
    (r'kersen\b', 'Cherries'),
    (r'vijg(?:en)?\b', 'Fig'),
    (r'kaki\b|kaki\'s|sharon(?:fruit)?|persimoen', 'Persimmon'),
    (r'passievrucht(?:en)?|passiefruit', 'Passion Fruit'),
    (r'papaya', 'Papaya'),
    (r'lychee(?:s)?|litchi', 'Lychee'),
    (r'kokosnoot', 'Coconut'),
]

RULES = [(_a(p), name, None, None) for p, name in _RULES]

# Organic and free-range eggs say so anywhere in the name ("Biologisch PLUS
# Eieren", "Eieren vrije uitloop m/l"), so these two look ahead first.
_EGGS = r'(?:scharrel|kooivrije|kip|witte|bruine)?\s*eieren'
RULES[:0] = [
    (r'^(?=[^,]*\bbio)' + _a(_EGGS), 'Organic Eggs', None, None),
    (r'^(?=[^,]*vrije[\s-]*uitloop)' + _a(_EGGS), 'Free Range Eggs', None, None),
]

# Rule names the catalogue calls something else, or does not have. None:
# the rule still matches, so the product does not fall through to a wrong,
# more general rule ("puntpaprika" is not a bell pepper), but its prices
# stay out of the averages and are counted as products worth adding.
TARGETS = {
    'Free Range Eggs': None,           # as in Spain: not the catalogue's plain "Eggs"
    'Organic Eggs': None,              # the catalogue has organic eggs only by size
    'Semi-skimmed Milk': None,
    'Cooking Cream': None,
    'Pointed or Snack Pepper': None,
    'White or Pointed Cabbage': None,
    'Chestnut Mushroom': None,         # brown, not the catalogue's white mushroom
    'Iceberg or Other Lettuce': None,
    'Cooked Beetroot': None,
}
