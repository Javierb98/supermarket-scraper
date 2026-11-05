"""
Norwegian shelf names → catalogue products (Oda).

The catalogue has no Norwegian names, so nothing Norwegian is priced unless a
rule here names it. Each rule says which catalogue product the shelf name is;
a rule whose name the catalogue does not have (TARGETS → None, or a name not
in the catalogue) still matches, so that "kyllingkjøttdeig" stops at "not a
product we list" instead of falling through to something wrong.

Only the plain product a farm would sell: processed food is turned away by
REJECT below (pipeline/processed.py has no Norwegian words), and so are
lactose-free and flavoured dairy, smoked, marinated and cooked meat.

Patterns run on the lower-cased shelf name, accents kept (ø, å, æ).
"""

import re

LANG = 'no'

# Words a Norwegian shelf name may start with that are not the product
# ("Økologiske egg", "Gul løk", "Liten agurk"). Folded: lower case, accents
# stripped (å → a; ø and æ stay as they are).
LEADING = [
    'økologisk', 'økologiske', 'okologisk', 'okologiske', 'norsk', 'norske', 'fersk', 'ferske',
    'liten', 'lille', 'sma', 'stor', 'store', 'ekstra', 'mini', 'gul', 'gule', 'rød', 'røde',
    'grønn', 'grønne', 'hvit', 'hvite', 'søt', 'søte', 'var', 'laveste', 'pris', 'first', 'price',
    'eldorado', 'xtra', 'orange', 'klasse', 'løsvekt', 'losvekt', 'pakket', 'beger', 'kurv', 'nye',
]

FROZEN = re.compile(r'\bfryst|\bfrossen|\bfrosne|dypfryst', re.I)
CANNED = re.compile(r'\bhermetis|\bboks\b|\bi lake\b|\bsyltet|\bsylte', re.I)


def detect_state(raw_name):
    if FROZEN.search(raw_name):
        return 'frozen'
    if CANNED.search(raw_name):
        return 'canned'
    return 'fresh'


# Not the fresh product, whatever else the name says.
REJECT = [re.compile(p, re.I) for p in [
    # processed, ready, preserved
    r'juice|\bsaft\b|smoothie|nektar|suppe|stappe|\bsaus\b|dressing|majones|remulade|\bchips|snacks?\b|\bpur[eé]\b|\bmos\b',
    r'syltet|sylte|\bsyltetøy|marmelade|gelé|kompott|tørket|soltørket|\bhakkede\b|\bknuste\b|passata|\bpesto',
    r'\bpannekake|nudler|pasta\b|lasagne|pizza|\bpai\b|kake\b|kjeks|\bboller?\b|\bbrød\b|wraps?\b|taco',
    r'sjokolade|påskeegg|kinderegg|\bis\b|iskrem|\bdessert|pudding|\bgrøt|müsli|musli|granola',
    r'yoghurt|kefir|\bdrikk|\bdrink|\bsmak\b|\bmed smak|\bvanilje|jordbærsmak|laktosefri|proteinmelk|havre|soya|mandeldrikk',
    r'\bsalat med|eggesalat|rekesalat|potetsalat|coleslaw|italiensk salat|tzatziki|hummus|guacamole|salsa\b',
    r'marinert|\bkrydret|\bpanert|\bgrillet|\bstekt|\bkokt|røkt|røket|\bspeke|pålegg|\bskivet|kebab|pølse|burger|nuggets|\bgryte',
    r'ferdigrett|middag|\bwok\b|\bmiks\b|grønnsaksblanding|blanding|\bsticks?\b|\bstaver\b|\bstrimlet|\bfries|pommes|potetgull|chips',
    # combined products: "Popcorn med smør", "Cheddar og mozzarella", "Tomat & kikertgryte"
    r'\bmed\b|\bog\b|&|\brett i\b|\bmnd\b|\bmalt\b|spirer|kutta|kålris|brokkoliris|squashies|ristorante|grandiosa|tortelloni|girasoli|plantebasert|friterte|ostestenger|baguett|popcorn|maiskaker',
    r'pulver|krydder|\bkvern|løksalt|aioli|mayo|dumpling|carne|marinade|brød\b|kraft\b|buljong|nuggets|panett|wiener|bacon|crispy|texmex|chunks|wokkjøtt|energidrikk|\bbrus\b',
    r'chutney|curd\b|sukkerlake|\bskiver\b|\bbiter\b|kjerner|salami|\bfrø|oliven|stuing|forkokt|cider|kattemat|hundemat|\bfôr\b',
    r'noodles|skivede|betsalat|\bsukker\b|\bdipp?\b|fruktdrikk|ternet|grovkuttet|kokte\b|\bkaker\b',
    # not food, or fish (no farm here sells fish by these names)
    r'\bdeo\b|sjampo|såpe|krem\b|tannkrem|hund|katt|\bfisk|laks|torsk|reker|makrell|sild|\btunfisk',
]]

# (pattern, rule name, -, -). The first that matches decides.
RULES_RAW = [
    # ---- EGGS ----
    (r'vaktelegg', 'Quail Eggs'),
    (r'andeegg', 'Duck Eggs'),
    (r'eggehvite|eggeplomme', 'Liquid egg'),                     # not listed
    (r'\begg\b|frokostegg|solegg|gårdsegg', 'Eggs'),

    # ---- DAIRY ----
    (r'kremfløte|\bfløte\b', 'Cream'),
    (r'\bsmør\b|meierismør|setersmør|kjernet smør|seterrømmesmør|rørossmør|kviteseidsmør', 'Butter'),
    (r'skummet ?melk|skummetmjølk|melk skummet|fettfri melk', 'Skim Milk'),
    (r'helmelk|helmjølk|gårdsmelk|gårdsmjølk', 'Whole Milk'),
    (r'lettmelk|lettmjølk|mellommelk|melk lett', 'Semi-skimmed Milk'),  # not listed
    (r'cottage cheese|\bcottage\b', 'Fresh Cottage Cheese'),
    (r'kremost|philadelphia', 'Cream Cheese'),
    (r'\bmozzarella', 'Mozzarella'),
    (r'parmesan|parmigiano', 'Parmesan'),
    (r'\bfeta\b|fetaost', 'Feta Cheese'),
    (r'\bcheddar', 'Cheddar Cheese'),
    (r'\bgouda\b', 'Gouda Cheese'),
    (r'\bedamer|\bedam\b', 'Edam Cheese'),
    (r'\bbrie\b', 'Brie'),
    (r'camembert', 'Camembert'),
    (r'blåmuggost|blåskimmel|gorgonzola|roquefort|creamy blue', 'Blue Cheese'),
    (r'\bricotta', 'Ricotta'),
    (r'mascarpone', 'Mascarpone'),
    (r'chèvre|chevre|hvit geitost|kvit geitost', 'Goat Cheese'),
    (r'brunost|geitost|gudbrandsdalsost|mysost|prim\b', 'Brown whey cheese'),  # not listed
    (r'jarlsberg', 'Swiss Cheese'),
    (r'\bgulost|gräddost|ridderost|västerbottensost|revet ost|norvegia|hvitost|nøkkelost|\bost\b.*\b(skorpefri|lagret|mild|vellagret)', 'Cheese'),

    # ---- MEAT & POULTRY ----
    (r'kylling.*kjøttdeig|kjøttdeig.*kylling|kalkun.*kjøttdeig|kjøttdeig.*kalkun', 'Ground poultry'),  # not listed
    (r'(svin|gris).*(kjøttdeig|karbonadedeig)|(kjøttdeig|karbonadedeig).*(svin|gris)', 'Ground Pork'),
    (r'lam.*kjøttdeig|kjøttdeig.*lam', 'Ground lamb'),          # not listed
    (r'karbonadedeig|kjøttdeig', 'Ground Beef'),
    (r'kyllingfilet|kyllingbryst|filet av kylling', 'Chicken Breast'),
    (r'kyllinglår|lårfilet|kyllinglårfilet', 'Chicken Thigh'),
    (r'kyllingvinger|kyllingving', 'Chicken Wings'),
    (r'kyllingklubb|kyllingtrommestikk', 'Chicken Drumsticks'),
    (r'kyllinglever', 'Chicken Liver'),
    (r'landkylling|hel kylling|kylling hel|\bhel\b.*\bkylling|grillkylling', 'Whole Chicken'),
    (r'kalkunfilet|kalkunbryst', 'Turkey Breast'),
    (r'andebryst', 'Duck Breast'),
    (r'lammekotelett', 'Lamb Chops'),
    (r'lammecarré|lammeracks?', 'Lamb Rib Rack'),
    (r'lammelår|lammestek', 'Lamb Leg'),
    (r'lammebog', 'Lamb Shoulder'),
    (r'svinekotelett|\bkotelett', 'Pork Chops'),
    (r'spareribs', 'Pork Ribs'),
    (r'\bribbe\b|svineribbe|\bsideflesk|\bsvinesid', 'Pork Belly'),
    (r'svinebog|\bbogstek', 'Pork Shoulder'),
    (r'svinefilet|svinemørbrad|(indre|ytre)filet av svin|svin.*(indre|ytre)filet', 'Pork tenderloin'),
    (r'(reinsdyr|elg|hjort).*(filet|stek)|(filet|stek) av (reinsdyr|elg|hjort)', 'Venison'),  # not listed
    (r'entrecôte|entrecote|ribeye', 'Fresh Ribeye'),
    (r'indrefilet', 'Fresh Tenderloin'),
    (r'ytrefilet', 'Fresh Sirloin'),
    (r'\bstorfebiff|\bbiff\b', 'Beef Steak'),
    (r'storfelever|kalvelever', 'Beef Liver'),
    (r'\breinsdyr|\bhjort\b|\belg\b|elgkjøtt|hjortekjøtt', 'Venison'),

    # ---- TOMATOES ----
    (r'cherrytomat|cherry ?tomat|tomat.*cherry|piccolo', 'Cherry Tomato'),
    (r'plommetomat', 'Plum Tomatoes'),
    (r'bifftomat', 'Beefsteak Tomatoes'),
    (r'tomater? klase|klasetomat', 'Vine Tomatoes'),
    (r'\btomat(er)?\b|hverdagstomat|runde tomater', 'Tomato'),

    # ---- OTHER VEGETABLES ----
    (r'\b(mini)?agurk(er)?\b|slangeagurk', 'Cucumber'),
    (r'chilipepper|\bchili,? (rød|grønn)', 'Chili Pepper'),
    (r'\bpaprika(?!pulver|krydder)', 'Bell Pepper'),
    (r'rødløk|\bløk rød', 'Red Onion'),
    (r'vårløk', 'Spring Onions'),
    (r'sjalottløk', 'Shallots'),
    (r'hvitløk', 'Garlic'),
    (r'purreløk|\bpurre\b', 'Leek'),
    (r'\bløk\b|\bgul løk|\bkepaløk', 'Onion'),
    (r'søtpotet', 'Sweet Potato'),
    (r'småpotet', 'Mini Potatoes'),
    (r'\bpotet(er)?\b|\bnypotet(er)?\b|mandelpotet|bakepotet', 'Potato'),
    (r'gulrot|gulrøtter', 'Carrot'),
    (r'rødbet', 'Beetroot'),
    (r'blomkål', 'Cauliflower'),
    (r'brokkoli', 'Broccoli'),
    (r'rosenkål', 'Brussels Sprouts'),
    (r'rødkål', 'Red Cabbage'),
    (r'savoykål', 'Savoy Cabbage'),
    (r'kinakål', 'Napa Cabbage'),
    (r'grønnkål', 'Kale'),
    (r'pak ?choi|bok ?choy', 'Bok Choy'),
    (r'hodekål|\bkål\b|kålhode', 'White cabbage'),                # not listed
    (r'kålrot|kålrabi', 'Rutabaga'),                              # not listed (Norwegian kålrabi is a swede)
    (r'sellerirot|knollselleri', 'Celeriac'),
    (r'stangselleri|selleri stang|\bselleri\b', 'Celery'),
    (r'pastinakk', 'Parsnip'),
    (r'persillerot', 'Parsley root'),                             # not listed
    (r'fennikel', 'Fennel'),
    (r'butternut', 'Butternut Squash'),
    (r'gresskar', 'Pumpkin'),
    (r'squash|zucchini', 'Zucchini'),
    (r'aubergine', 'Eggplant'),
    (r'hvit asparges', 'White Asparagus'),
    (r'\basparges\b|grønn asparges', 'Green Asparagus'),
    (r'babyspinat|\bspinat\b', 'Spinach'),
    (r'ruccola|ruccula|rucola|rukola', 'Arugula'),
    (r'romanosalat|romainesalat|\bromano\b', 'Romaine Lettuce'),
    (r'radicchio', 'Radicchio'),
    (r'sikori|\bendive', 'Endive'),
    (r'spisskål', 'White cabbage'),
    (r'kantarell', 'Chanterelle'),
    (r'hjertesalat', 'Mini Romaine'),
    (r'isbergsalat|issalat', 'Iceberg lettuce'),                  # not listed
    (r'\breddik', 'Radish'),
    (r'sjampinjong', 'White Mushroom'),
    (r'portobello', 'Portobello Mushroom'),
    (r'shiitake', 'Shiitake Mushroom'),
    (r'østerssopp', 'Oyster Mushroom'),
    (r'aspargesbønner|brekkbønner|haricots? verts|grønne bønner|\bbønner, grønne', 'Green Beans'),
    (r'sukkererter', 'Sugar Snap Peas'),
    (r'maiskolbe|\bmais\b', 'Sweet Corn'),
    (r'ingefær', 'Fresh Ginger'),
    (r'jordskokk', 'Jerusalem Artichoke'),
    (r'artisjokk', 'Artichoke'),
    (r'pepperrot', 'Horseradish'),
    (r'\bokra\b', 'Okra'),
    (r'\bnepe\b', 'Turnip'),

    # ---- FRUIT ----
    (r'pink lady', 'Pink Lady Apples'),
    (r'honeycrisp', 'Honeycrisp Apples'),
    (r'granateple', 'Pomegranate'),
    (r'\bepler?\b|\beple ', 'Apples'),
    (r'\bpærer?\b', 'Pears'),
    (r'\bbanan(er)?\b', 'Banana'),
    (r'blodappelsin', 'Blood Oranges'),
    (r'\bappelsin(er)?\b', 'Oranges'),
    (r'klementin', 'Clementine'),
    (r'mandarin', 'Mandarin Oranges Fresh'),
    (r'\bsitron(er)?\b', 'Lemons'),
    (r'\blime\b', 'Lime'),
    (r'grønne druer|druer.*grønn|hvite druer', 'Grapes Green'),
    (r'røde druer|blå druer|druer.*(rød|blå)', 'Grapes Red'),
    (r'\bjordbær\b', 'Strawberries'),
    (r'\bbringebær\b', 'Raspberry'),
    (r'\bblåbær\b', 'Blueberries'),
    (r'\bbjørnebær\b', 'Blackberries'),
    (r'\brips\b', 'Red Currant'),
    (r'\bsolbær\b', 'Black Currant'),
    (r'stikkelsbær', 'Gooseberry'),
    (r'\bkirsebær\b', 'Cherries'),
    (r'\bplommer?\b', 'Plums'),
    (r'\bfersken', 'Peaches'),
    (r'\bkiwi', 'Kiwi'),
    (r'\bmango\b', 'Mango'),
    (r'\bavokado', 'Avocado'),
    (r'\bananas\b', 'Pineapple'),
    (r'vannmelon', 'Watermelon'),
    (r'\b(honning|galia|cantaloupe|piel de sapo)?melon\b', 'Melon'),
    (r'\bfiken\b', 'Fig'),
    (r'pasjonsfrukt', 'Passion Fruit'),
    (r'\bkaki\b|sharonfrukt', 'Persimmon'),
    (r'\bpapaya', 'Papaya'),
    (r'\bkokosnøtt', 'Coconut'),
    (r'\blitchi|\blychee', 'Lychee'),
]

RULES = [(p, n, None, None) for p, n in RULES_RAW]

# Rule names the catalogue spells differently, or does not list (None).
TARGETS = {
    'Liquid egg': None,
    'Semi-skimmed Milk': None,
    'Brown whey cheese': None,
    'Ground poultry': None,
    'Ground lamb': None,
    'Pork tenderloin': None,
    'White cabbage': None,
    'Rutabaga': None,
    'Parsley root': None,
    'Iceberg lettuce': None,
    'Chanterelle': None,
}
