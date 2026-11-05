"""
Serbian shelf names → catalogue products.

The names come from the price lists Serbian chains must publish (Pravilnik
o uslovima, sadržaju i načinu objavljivanja cenovnika, Sl. glasnik RS
76/2026), read from data.gov.rs by feeds/cenovnici_rs.py. They are in Latin
script today ("PAPRIKA ŠILJA", "Kiselo mleko 2,8%"), sometimes without the
diacritics, and Serbian may as well be written in Cyrillic; so every
pattern here is written once in Latin and matched three ways: as written,
without diacritics, and transliterated to Cyrillic (see rules_hr.loose and
rules_hr.to_cyrillic).

Serbian is ekavian and has words of its own (paradajz, šargarepa, krompir,
crni luk, pomorandža, pavlaka), so the rules are not Croatia's.

Rule names ending "(sr)" are products the catalogue does not have: matched,
so nothing looser takes them, and kept out of the averages.
"""

import re

from pipeline.rules_hr import loose, to_cyrillic

LANG = 'sr'


def both(p):
    """One Latin pattern → Latin (diacritics optional) or Cyrillic."""
    return '(?:%s)|(?:%s)' % (loose(p), to_cyrillic(p))


FROZEN = re.compile(both(r'zamrznut|smrznut|duboko zamrz|frikom|\bledo\b'), re.I)
CANNED = re.compile(both(r'konzerv|limenk|\btegl|ukiseljen|sterilisan|pasterizovan'), re.I)


def detect_state(raw_name):
    n = raw_name.lower()
    if FROZEN.search(n):
        return 'frozen'
    if CANNED.search(n) and not re.search(both(r'mlek'), n):
        # "Mleko pasterizovano" is milk as it is sold.
        return 'canned'
    return 'fresh'


# Compared with accents stripped (the matcher folds first).
LEADING = [
    'bio', 'eko', 'organski', 'organska', 'domaci', 'domaca', 'domace', 'svezi', 'sveza', 'sveze', 'mladi',
    'mlada', 'mlado', 'baby', 'mini', 'rinfuz', 'rinfuzni', 'k', 'plus', 'premium', 'extra', 'ekstra', 'voce',
    'povrce', 'gomex', 'maxi', 'idea', 'nase', 'nas', 'srpski', 'srpska', 'zeleni', 'zelena', 'zuta', 'zuti',
    'crvena', 'bela', 'beli',
    'био', 'еко', 'домаћи', 'домаћа', 'домаће', 'свеже', 'свежи', 'свежа', 'млади', 'млада', 'воће', 'поврће',
]

_REJECT = [
    # drinks, sweets, spreads, sauces
    r'\bsok\b|sokovi|nektar|napitak|smoothie|shake|limunad|sirup|\bčaj\b|kafa|coffee|kakao|čokolad|keks|kolač|'
    r'torta|sladoled|bombon|žvak|napolitank|puding|džem|marmelad|pekmez|kompot|namaz|\bsos\b|kečap|ajvar|'
    r'majonez|senf|\bkrem\b|krema\b|\bpire\b|\bsupa\b|čorba|instant|dezert|desert|\bmus\b|\bvoda\b',
    # tins, jars, pickles, dried, cooked
    r'pelat|pasiran|seckan|koncentrat|konzerv|limenk|\btegl|ukiseljen|kisel[ai]\s+(krastav|paprik|kupus)|turšij|'
    r'salamur|sušen|\bsuv[aeio]\b|\bsuvo\b|kandiran|u prahu|dehidrir|\bpečen[aeio]?\b|\bkuvan[aeio]?\b|'
    r'gril\b|grill|roštilj|gotov|pohovan|paniran|dimljen|mariniran|\bmar\b|začinjen|punjen|rolovan|'
    r'\brezan[aio]?\b|narez|slajs|u pavlac|tzatzik|caciki|u omotu|delikates|\bbaren|stick|faši|sniž|carsk|bbq|'
    r'polupriprem|marinad|\bulj[eu]\b|u ulju|kriške|kocke\b|\bmix\b|mešavin',
    # meat products
    r'salam|kobasic|hrenovk|viršl|šunk|pršut|slanin|kulen|pašte|čvarc|ćevap|pljeskavic|burger|nugget|giros|'
    r'gyros|kebab|ražnji|pečenic|\bposebn|mesni doručak|čajna|mortadel|budimsk|kare dimlj|krvavic|ćufte|'
    r'čufte|musaka|sarma|gulaš|\btun[ae]?\b|losos|\briba\b|oslić',
    # bakery, pasta, ready meals
    r'testenin|rezanci|pizza|\bpica\b|burek|\bpita\b|štrudl|\bhleb|pecivo|tortilj|kroket|pomfrit|\bčips|flips|'
    r'štapić|smoki|kreker|salata (od|sa|s)\b|lazanj|đuveč|proja|brašn|griz|ovsen|musli|cerealij|pahuljic|'
    r'\bpasta\b|tortel|raviol|\bsa? (krompir|pirinč|testen|mesom|šunk|sirom|pavlak|graš|mrkv|luk)',
    # dairy that is not plain
    r'ukus|aroma|vanil|bez laktoze|laktoz|protein|čokoladn|topljen|margarin|biljn|kikirik|kinder|zabelj|'
    r'u spreju|kondenzov|za kafu|cappuccino|latte|mlečni napitak|ice\b|ajran|ayran|\bfit\b',
    # pets, household, cosmetics
    r'za pse|za mačke|\bpas\b|mačk|whiskas|pedigree|friskies|felix|purina|hrana za|granule|šampon|\bgel\b|'
    r'sapun|deterdž|omekšiv|krema za|losion|mleko za|dezodor|parfem|sveć|osveživ|toalet|čišćenj|pasta za zube|'
    r'balzam|kozmet|\bmaska\b|tablet|kapsul|sredstvo|maramic|sprej|spužv|igračk|ukras|dekor|uskrš|rasad|'
    r'\bseme\b|sadnic|\bcvet',
    # alcohol
    r'liker|rakij|\bvino\b|\bpivo\b|\bgin\b|votk|vodka|whisk|\brum\b|šljivovic|lozovač',
    # spice brands and ground spices
    r'aleva|mleven\w*\s+(paprik|biber)|začin|vegeta|kotanyi|podravk|\bc ?\+|bočic|kesic',
]
REJECT = [re.compile(both(p), re.I) for p in _REJECT]

CH = r'^(\S+\s+){0,2}'
HERB = r'^(svež\w*\s+)?'
BEEF = r'(junet|june[ćc]|govedin|gove[đd]|\bjun\b)'

_RULES = [
    # ---- EGGS ----
    (r'prepeli[čc]\w* jaj|jaj\w* prepel', 'Quail Eggs'),
    (r'\bjaja\b.*(\beko\b|\bbio\b|organsk)|(\beko\b|\bbio\b|organsk).*\bjaja\b', 'Organic eggs (sr)'),
    (r'\bjaja\b', 'Eggs'),

    # ---- POULTRY ----
    (r'ćure[ćc]\w*\s+(\w+\s+)?(file|belo meso|grudi|prsa)|ćuretina file', 'Turkey Breast'),
    (r'ćure[ćc]\w*\s+(\w+\s+)?(batak|karabatak)', 'Turkey Legs'),
    (r'ćure[ćc]\w*\s+(\w+\s+)?krila', 'Turkey Wings'),
    (r'ćure|ćuret', 'Turkey other (sr)'),
    (r'pile[ćc]\w*\s+(\w+\s+)?karabatak|batak i karabatak|^(\S+\s+)?karabatak', 'Chicken Thigh'),
    (r'pile[ćc]\w*\s+(\w+\s+)?(file|belo meso|grudi|prsa)|belo pile[ćc]\w* meso|^(\S+\s+)?belo meso', 'Chicken Breast'),
    (r'pile[ćc]\w*\s+(\w+\s+)?batak|^(\S+\s+)?batak', 'Chicken Drumsticks'),
    (r'pile[ćc]\w*\s+(\w+\s+)?(krila|krilca)|^(\S+\s+)?pil\w*\.?\s*kril', 'Chicken Wings'),
    (r'pile[ćc]\w*\s+(\w+\s+)?(džigeric|jetr|jetric)', 'Chicken Liver'),
    (r'pile[ćc]\w*\s+(\w+\s+)?(želu)', 'Chicken Gizzard'),
    (r'pile[ćc]\w*\s+(\w+\s+)?(nogice|noge)', 'Chicken Feet'),
    (r'^(\w+\s+)?pile\b|celo pile|pile celo|trup pile', 'Whole Chicken'),
    (r'pa[čc]j\w*\s+(\w+\s+)?(file|grudi|prsa)', 'Duck Breast'),
    (r'pile[ćc]|piletin|patk|guš[čc]|\bguska', 'Poultry other (sr)'),

    # ---- MEAT ----
    (r'mleven\w*\s+(\w+\s+)?' + BEEF + r'|' + BEEF + r'\w*\s+(\w+\s+)?mleven', 'Ground Beef'),
    (r'mleven\w*\s+(\w+\s+)?svinj|svinj\w*\s+(\w+\s+)?mleven', 'Ground Pork'),
    (r'mleven', 'Mixed minced meat (sr)'),
    (r'telet|tele[ćc]', 'Veal (sr)'),
    (r'biftek', 'Fresh Tenderloin'),
    (r'rib ?eye|antrikot|entrecote', 'Fresh Ribeye'),
    (r'ramstek|\brump', 'Fresh Sirloin'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?(rebra|rebarc)', 'Beef Ribs'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?(jetr|džigeric)', 'Beef Liver'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?jezik', 'Beef Tongue'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?obraz', 'Beef Cheek'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?rep\b', 'Beef Tail'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?(grudi|prsa)', 'Beef Brisket'),
    (r'tripice|škembe|fileki', 'Beef Tripe'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?(steak|stek|šnicl|odrez)', 'Beef Steak'),
    (BEEF, 'Beef other (sr)'),
    (r'svinj\w*\s+(\w+\s+)?(kotlet|krmenadl)|krmenadl|kotlet\w*\s+svinj', 'Pork Chops'),
    (r'svinj\w*\s+(\w+\s+)?(rebra|rebarc)|rebarc\w*\s+svinj', 'Pork Ribs'),
    (r'svinj\w*\s+(\w+\s+)?(potrbu|trbuh)|^(\S+\s+)?potrbušin', 'Pork Belly'),
    (r'svinj\w*\s+(\w+\s+)?(ple[ćc]k|lopatic)', 'Pork Shoulder'),
    (r'svinj\w*\s+(\w+\s+)?but\b', 'Pork Ham'),
    (r'svinj\w*\s+(\w+\s+)?obraz', 'Pork Jowl'),
    (r'svinj\w*\s+(\w+\s+)?(koža|kožic)', 'Pork Skin'),
    (r'svinj\w*\s+(\w+\s+)?bubre', 'Pork Kidney'),
    (r'svinj\w*\s+(\w+\s+)?mast|mast\s+svinj|^mast\b', 'Lard'),
    (r'svinj', 'Pork other (sr)'),
    (r'jagnje\w*\s+(\w+\s+)?kotlet', 'Lamb Chops'),
    (r'jagnje\w*\s+(\w+\s+)?but\b', 'Lamb Leg'),
    (r'jagnje\w*\s+(\w+\s+)?(ple[ćc]k|lopatic)', 'Lamb Shoulder'),
    (r'jagnje|jagnjet', 'Lamb other (sr)'),
    (r'jaretin|kozlet', 'Goat Meat'),
    (r'zečetin|^(\S+\s+)?kuni[ćc]\b', 'Rabbit Meat'),

    # ---- DAIRY ----
    (r'^(\S+\s+)?(kiselo mlek|mlek\w* kisel|kefir|acidofil)', 'Fermented Milk'),
    (r'^(\S+\s+)?(kozj\w*\s+mlek|mlek\w*\s+kozj)', 'Goat Milk'),
    (r'^(\S+\s+)?(ov[čc]ij\w*\s+mlek|mlek\w*\s+ov[čc])', 'Sheep Milk'),
    (r'^(\S+\s+)?(mlaćenic|buttermilk)', 'Buttermilk'),
    (r'^(\S+\s+)?(sveže\s+)?mlek[oa]\b.*(3[.,][2-9]|4[.,]\d|punomasn)', 'Whole Milk'),
    (r'^(\S+\s+)?mlek[oa]\b.*(0[.,][0-5]\s*%|obran)', 'Skim Milk'),
    (r'^(\S+\s+)?mlek[oa]\b', 'Milk other fat (sr)'),
    (r'(jogurt|skyr|kefir).*(jagod|breskv|vanil|borovnic|šumsk|banan|kajsij|višnj|ananas|kokos|žitar|voć|'
     r'limun|mang|malin|kupin|trešnj|ribizl|grožđ|krušk|jabuk|\bmed\b|lešnik|smokv|ovas|ovsen|aloe|'
     r'pistać|karamel|cimet)', 'Flavoured yogurt (sr)'),
    (CH + r'(grčk\w*\s+jogurt|jogurt\w*\s+grčk)', 'Greek Yogurt'),
    (CH + r'skyr', 'Skyr'),
    (CH + r'(tečn\w*\s+)?jogurt', 'Yogurt'),
    (r'jogurt', 'Yogurt other (sr)'),
    (r'kisel\w*\s+pavlak|pavlak\w*\s+kisel', 'Sour cream (sr)'),
    (r'^(\S+\s+)?(slatk\w*\s+|neutraln\w*\s+)?pavlak', 'Cream'),
    (r'kajmak', 'Kajmak (sr)'),
    (r'^(\S+\s+)?(maslac|puter)\b', 'Butter'),
    (CH + r'(krem sir|sir za mazanje|cream cheese|philadelphia)', 'Cream Cheese'),
    (CH + r'(sir\s+)?(mozzarel|mocarel)', 'Mozzarella'),
    (CH + r'(sir\s+)?feta\b', 'Feta Cheese'),
    (CH + r'(sir\s+)?(gouda|gauda)', 'Gouda Cheese'),
    (CH + r'(sir\s+)?edam', 'Edam Cheese'),
    (CH + r'(sir\s+)?(emmental|ementaler)', 'Swiss Cheese'),
    (CH + r'(sir\s+)?(parmez|parmigian|grana padano)', 'Parmesan'),
    (CH + r'(sir\s+)?(mascarpone|maskarpone)', 'Mascarpone'),
    (CH + r'(sir\s+)?(ricotta|rikota)', 'Ricotta'),
    (CH + r'(sir\s+)?(cheddar|čedar)', 'Cheddar Cheese'),
    (CH + r'(sir\s+)?(gorgonzol|roquefort|rokfor)', 'Blue Cheese'),
    (CH + r'(sir\s+)?provolone', 'Provolone'),
    (CH + r'(kozj\w*\s+sir|sir\w*\s+(\w+\s+)?kozj)', 'Goat Cheese'),
    (CH + r'(ov[čc]ij?\w*\s+sir|sir\w*\s+(\w+\s+)?ov[čc]ij?)', 'Sheep Cheese'),
    (CH + r'(sir\s+)?(trapist|polutvrd|tvrd\w*\s+sir|kačkavalj)', 'Cheese'),
    (CH + r'(mlad\w*\s+sir|sitn\w*\s+sir|svež\w*\s+sir|sir\s+svež|cottage|posni sir)', 'Fresh Cottage Cheese'),
    (r'\bsir\b|\bsira\b', 'Cheese other (sr)'),

    # ---- VEGETABLES ----
    (r'paradajz\w*\s+.*(cherry|čeri|mini|koktel|datterin)|čeri paradajz|cherry paradajz', 'Cherry Tomato'),
    (r'paradajz\w*\s+.*(grozd|na grani|grančic)', 'Vine Tomatoes'),
    (r'paradajz\w*\s+.*(šljiv|\broma\b)', 'Plum Tomatoes'),
    (r'paradajz\w*\s+.*(beef|volovsk)', 'Beefsteak Tomatoes'),
    (r'paradajz|rajčic', 'Tomato'),
    (r'kornišon', 'Pickling Cucumbers'),
    (r'krastav', 'Cucumber'),
    (r'ljut\w*\s+paprik|paprik\w*\s+.*ljut|feferon|čili|chili', 'Chili Pepper'),
    (r'paprik|babur', 'Bell Pepper'),
    (r'tikvic', 'Zucchini'),
    (r'butternut', 'Butternut Squash'),
    (r'bundev|\btikva|hokaido|hokkaido', 'Pumpkin'),
    (r'šargarep|mrkv', 'Carrot'),
    (r'batat|slatk\w*\s+krompir', 'Sweet Potato'),
    (r'krompir', 'Potato'),
    (r'praziluk|poriluk', 'Leek'),
    (r'beli luk|luk beli|bel\w*\s+luk|češnjak', 'Garlic'),
    (r'mlad\w*\s+luk|luk\s+mlad', 'Spring Onions'),
    (r'crven\w*\s+luk|luk\s+crven|ljubičast\w*\s+luk', 'Red Onion'),
    (r'ljutik|šalot', 'Shallots'),
    (r'arpadžik', 'Onion sets (sr)'),
    (r'crn\w*\s+luk|luk\s+crn|\bluk\b', 'Onion'),
    (r'brokol', 'Broccoli'),
    (r'karfiol', 'Cauliflower'),
    (r'romanesk|romanesc', 'Romanesco'),
    (r'prokelj|kelj pup', 'Brussels Sprouts'),
    (r'\bkale\b|kovrdžav\w*\s+kelj', 'Kale'),
    (r'\bkelj', 'Savoy Cabbage'),
    (r'kinesk\w*\s+kupus', 'Napa Cabbage'),
    (r'crven\w*\s+kupus|kupus\s+crven|ljubičast\w*\s+kupus', 'Red Cabbage'),
    (r'kupus', 'Cabbage (sr)'),
    (r'pak cho|bok cho', 'Bok Choy'),
    (r'spanać', 'Spinach'),
    (r'blitv|mangold', 'Swiss Chard'),
    (r'rukol|rikol', 'Arugula'),
    (r'endivij', 'Endive'),
    (r'radič|radicchio', 'Radicchio'),
    (r'rimsk\w*\s+salat|romain|romana', 'Romaine Lettuce'),
    (r'salat|lolo|lollo|ajsberg|iceberg|zelen\b', 'Lettuce (sr)'),
    (r'cvekl', 'Beetroot'),
    (r'celer\w*\s+.*(list|stablj|rebr)', 'Celery'),
    (r'celer', 'Celeriac'),
    (r'rotkvic', 'Radish'),
    (r'rotkv', 'Black or white radish (sr)'),
    (r'morač|komorač', 'Fennel'),
    (r'artičok', 'Artichoke'),
    (r'patlidžan', 'Eggplant'),
    (r'bamij|\bokra\b', 'Okra'),
    (r'paškanat|pastrnak|pastrnjak', 'Parsnip'),
    (r'keleraba|korab', 'Kohlrabi'),
    (r'^(\S+\s+)?repa\b', 'Turnip'),
    (r'kukuruz\w*\s+.*klip|klip\w*\s+kukuruz', 'Sweet Corn'),
    (r'kukuruz', 'Corn kernels (sr)'),
    (r'boranij|mahun', 'Green Beans'),
    (r'grašak', 'Peas (sr)'),
    (r'šparg', 'Asparagus'),
    (r'đumbir', 'Fresh Ginger'),
    (r'bukovač', 'Oyster Mushroom'),
    (r'shiitake|šitake', 'Shiitake Mushroom'),
    (r'portobel', 'Portobello Mushroom'),
    (r'(pečurk|šampinjon)\w*\s+.*(braon|smeđ)|vrganj|lisičark|lavlj\w* griv|šumsk\w* pile', 'Other mushrooms (sr)'),
    (r'pečurk|šampinjon|gljiv', 'White Mushroom'),

    # ---- FRESH HERBS ----
    (HERB + r'peršun\w*\s+(\w+\s+)?koren', 'Parsley root (sr)'),
    (HERB + r'peršun', 'Parsley'),
    (HERB + r'mirođij', 'Dill'),
    (HERB + r'bosiljak', 'Genovese Basil'),
    (HERB + r'vla[šs]ac', 'Chives'),
    (HERB + r'(nana|menta)\b', 'Mint'),
    (HERB + r'ruzmarin|' + HERB + r'ružmarin', 'Rosemary'),
    (HERB + r'(timijan|majčina dušica)', 'Thyme'),
    (HERB + r'žalfij', 'Sage'),
    (HERB + r'korijand', 'Cilantro'),

    # ---- FRUIT ----
    (r'jabuk\w*\s+.*pink lady|pink lady', 'Pink Lady Apples'),
    (r'jabuk', 'Apples'),
    (r'krušk', 'Pears'),
    (r'nektarin', 'Nectarine (sr)'),
    (r'breskv', 'Peaches'),
    (r'šljiv', 'Plums'),
    (r'crven\w*\s+pomorand|krvav\w*\s+pomorand|pomorand\w*\s+(crven|krvav|moro|tarocco)', 'Blood Oranges'),
    (r'pomorandž|narandž', 'Oranges'),
    (r'limet|\blajm', 'Lime'),
    (r'limun(?!ad)', 'Lemons'),
    (r'grejp', 'Grapefruit (sr)'),
    (r'mandarin', 'Mandarin Oranges Fresh'),
    (r'klementin', 'Clementine'),
    (r'avokad|avocad', 'Avocado'),
    (r'lubenic', 'Watermelon'),
    (r'dinj', 'Melon'),
    (r'malin', 'Raspberry'),
    (r'jagod', 'Strawberries'),
    (r'borovnic', 'Blueberries'),
    (r'kupin', 'Blackberries'),
    (r'grožđ\w*\s+.*(bel|zelen|žut)|(bel|zelen)\w*\s+grožđ', 'Grapes Green'),
    (r'grožđ\w*\s+.*(crn|crven|plav)|(crn|crven)\w*\s+grožđ', 'Grapes Red'),
    (r'grožđ', 'Grapes (sr)'),
    (r'banan', 'Banana'),
    (r'ananas', 'Pineapple'),
    (r'\bmang[oa]\b', 'Mango'),
    (r'papaj', 'Papaya'),
    (r'marakuj|passion', 'Passion Fruit'),
    (r'\bkiwi|\bkivi', 'Kiwi'),
    (r'smokv', 'Fig'),
    (r'\bnar\b', 'Pomegranate'),
    (r'\bliči\b|lychee', 'Lychee'),
    (r'kokos\w*\s+orah|^kokos\s+(kom|svež)', 'Coconut'),
    (r'kokos', 'Coconut products (sr)'),
    (r'\bkaki\b|persimon|japansk\w* jabuk', 'Persimmon'),
    (r'trešnj', 'Cherries'),
    (r'višnj', 'Sour cherry (sr)'),
    (r'kajsij', 'Apricot (sr)'),
    (r'dunj', 'Quince (sr)'),
    (r'crven\w*\s+ribizl|ribizl\w*\s+crven', 'Red Currant'),
    (r'crn\w*\s+ribizl|ribizl\w*\s+crn', 'Black Currant'),
    (r'ogrozd', 'Gooseberry'),
    (r'pitaj|zmajev', 'Dragon Fruit'),
    (r'kesten', 'Chestnuts'),
    (r'lešnik', 'Hazelnuts'),
    (r'orah\w*\s+brazil|brazilsk\w*\s+orah', 'Brazil Nuts'),
    (r'\borah|\borasi\b', 'Walnuts'),
    (r'badem', 'Almonds'),
]

RULES = [(both(p), n, None, None) for p, n in _RULES]

TARGETS = {n: None for _, n in _RULES if n.endswith('(sr)')}
