"""
Swedish shelf names → catalogue products (Mathem; Willys would read the same).

The catalogue has no Swedish names, so nothing Swedish is priced unless a
rule here names it. A rule whose name the catalogue does not list (TARGETS →
None) still matches, so "blandfärs" stops at "not a product we list" rather
than falling through to beef.

Processed food is turned away by REJECT (pipeline/processed.py has no
Swedish words). Patterns run on the lower-cased shelf name, accents kept.
"""

import re

LANG = 'sv'

# Words a Swedish shelf name may start with that are not the product. Folded:
# lower case, accents stripped (ä → a, ö → o, å → a).
LEADING = [
    'eko', 'ekologisk', 'ekologiska', 'svensk', 'svenska', 'farsk', 'farska', 'sma', 'stor', 'stora',
    'liten', 'mini', 'gul', 'gula', 'rod', 'roda', 'gron', 'grona', 'vit', 'vita', 'sot', 'sota',
    'klass', 'krav', 'garant', 'ica', 'coop', 'eldorado', 'first', 'price', 'lösvikt', 'losvikt', 'nya',
]

FROZEN = re.compile(r'\bfryst|\bfrysta|djupfryst', re.I)
CANNED = re.compile(r'\bkonserv|\bburk\b|\binlagd|\binlagda|\bi lag\b', re.I)


def detect_state(raw_name):
    if FROZEN.search(raw_name):
        return 'frozen'
    if CANNED.search(raw_name):
        return 'canned'
    return 'fresh'


REJECT = [re.compile(p, re.I) for p in [
    r'juice|\bsaft\b|smoothie|nektar|soppa|\bsås\b|dressing|majonnäs|remoulad|\bchips|snacks?\b|\bpuré|potatismos',
    r'sylt\b|marmelad|gelé|kompott|torkad|soltorkad|krossade|passerade|passata|\bpesto',
    r'pannkak|nudlar|pasta\b|lasagne|pizza|\bpaj\b|kaka\b|kex\b|bulle|\bbröd\b|wraps?\b|taco',
    r'choklad|kinder|påskägg|\bglass\b|dessert|pudding|\bgröt|müsli|musli|granola',
    r'yoghurt|\bfil\b|filmjölk|kefir|\bdryck|\bdrink|\bsmak\b|smaksatt|vanilj|laktosfri|protein|havre|soja|mandeldryck|o’boy|oboy',
    r'äggvit|äggul|äggnudl|äggröra|äggsallad|äggtoddy|\bsallad med|räksallad|potatissallad|coleslaw|tzatziki|hummus|guacamole|salsa\b',
    r'\bmarinerad|\bkryddad|\bpanerad|\bgrillad|\bstekt|\bkokt|rökt|\bskivad|pålägg|kebab|korv|burgare|burger|nuggets|bullar\b|gratäng|kroketter',
    r'färdigrätt|\bwok\b|\bmix\b|blandning|\bstavar|\bstrimlad|\bfries|pommes|klyftor|rösti',
    r'bregott|margarin|\bbredbar|\bmatlagnings|creme fraiche|crème fraiche|gräddfil',
    r'\bmed\b|\boch\b|&|\bmån\b|popcorn|plantbaserad|vegansk|ristorante|grandiosa|tortellini|groddar|skott\b',
    r'pulver|malen\b|flakes|flingor|finhackad|krossad|chutney|curd\b|sockerlag|skivor\b|ananas bitar|kärnor|pesto|salami|frö\b|fröer|sås\b|oliver|stuvning|förkokt|cider|foder|kusar|ostbåge|babybel|\bdip\b|mjukost|spraygrädde|hållbarhet|betssallad|mor annas|garland',
    r'skivad|tärnad|grovskuren|kokta\b|\bsocker\b|fruktdryck|biffar|\bkakor\b|\bdipp?\b',
    r'bites\b|bågar|tripplers|spicy|fylld|kräm\b|mayo|\bshot\b|roasted|garlic|färskost paprika',
    r'hollandaise|tryffel|café de paris|gårdsgoda|färskost (vitlök|pepparrot|västerbotten|gräslök|örter)',
    r'\bdeo\b|schampo|tvål|\bkräm\b|tandkräm|hund|katt|\bfisk|lax|torsk|räkor|makrill|sill\b|\btonfisk',
]]

RULES_RAW = [
    # ---- EGGS ----
    (r'vaktelägg', 'Quail Eggs'),
    (r'ankägg', 'Duck Eggs'),
    (r'\bägg\b', 'Eggs'),

    # ---- DAIRY ----
    (r'vispgrädde', 'Cream'),
    (r'\bsmör\b|svenskt smör|normalsaltat smör', 'Butter'),
    (r'minimjölk|skummjölk', 'Skim Milk'),
    (r'standardmjölk|helmjölk|gårdsmjölk', 'Whole Milk'),
    (r'mellanmjölk|lättmjölk', 'Semi-skimmed Milk'),             # not listed
    (r'keso|cottage cheese', 'Fresh Cottage Cheese'),
    (r'färskost|philadelphia', 'Cream Cheese'),
    (r'\bmozzarella', 'Mozzarella'),
    (r'parmesan|parmigiano', 'Parmesan'),
    (r'\bfeta\b|fetaost', 'Feta Cheese'),
    (r'\bcheddar', 'Cheddar Cheese'),
    (r'\bgouda\b', 'Gouda Cheese'),
    (r'\bedamer|\bedam\b', 'Edam Cheese'),
    (r'\bbrie\b', 'Brie'),
    (r'camembert', 'Camembert'),
    (r'ädelost|blåmögelost|gorgonzola|roquefort', 'Blue Cheese'),
    (r'\bricotta', 'Ricotta'),
    (r'mascarpone', 'Mascarpone'),
    (r'chèvre|chevre|getost', 'Goat Cheese'),
    (r'jarlsberg', 'Swiss Cheese'),
    (r'hushållsost|gräddost|grevé|greve\b|herrgård|prästost|präst\b|västerbotten', 'Cheese'),

    # ---- MEAT & POULTRY ----
    (r'blandfärs', 'Mixed mince'),                                # not listed
    (r'kycklingfärs|kalkonfärs', 'Ground poultry'),              # not listed
    (r'fläskfärs', 'Ground Pork'),
    (r'lammfärs', 'Ground lamb'),                                 # not listed
    (r'nötfärs|högrevsfärs', 'Ground Beef'),
    (r'kalkonlår', 'Turkey cut'),
    (r'lammentrecote|lamminnerfilé|lammfilé|lammytterfilé', 'Lamb loin'),
    (r'kycklinginnerfilé', 'Chicken tenders'),
    (r'kycklinglårfil|kycklinglår|kyckling.*lårfil', 'Chicken Thigh'),
    (r'kycklingfilé|kycklingbröst|kyckling bröstfilé|kycklingbröstfilé', 'Chicken Breast'),
    (r'kycklingvingar|kycklingving', 'Chicken Wings'),
    (r'kycklingklubb', 'Chicken Drumsticks'),
    (r'kycklinglever', 'Chicken Liver'),
    (r'hel kyckling|kyckling hel|\bhel\b.*\bkyckling|grillkyckling', 'Whole Chicken'),
    (r'kalkonfilé|kalkonbröst', 'Turkey Breast'),
    (r'ankbröst', 'Duck Breast'),
    (r'lammkotlett', 'Lamb Chops'),
    (r'lammracks?|lammcarré', 'Lamb Rib Rack'),
    (r'lammstek|lammlägg|lammfiol', 'Lamb Leg'),
    (r'lammbog', 'Lamb Shoulder'),
    (r'fläskkotlett|\bkotlett', 'Pork Chops'),
    (r'revbensspjäll|spareribs', 'Pork Ribs'),
    (r'sidfläsk|fläsksida', 'Pork Belly'),
    (r'fläskbog|bogstek', 'Pork Shoulder'),
    (r'fläskfilé|fläskytterfilé|fläskinnerfilé', 'Pork tenderloin'),  # not listed
    (r'entrecôte|entrecote|ribeye', 'Fresh Ribeye'),
    (r'oxfilé|nötfilé|oxinnerfilé', 'Fresh Tenderloin'),
    (r'ryggbiff', 'Fresh Sirloin'),
    (r'högrev', 'Fresh Chuck Roast'),
    (r'\bnötkött|\bbiff\b|\bbiffar\b', 'Beef Steak'),
    (r'nötlever|kalvlever', 'Beef Liver'),
    (r'\bälgkött|\bälg\b|hjortkött|\bhjort\b|renkött|renskav|rådjur|viltfärs', 'Venison'),

]

# Fresh produce. Swedish shops grade it on the label ("Klass1", "Klass 2"),
# and nothing else carries a grade: "Chilipeppar Chipotle, 33 g" (dried),
# "Mango Mayo" and "Champinjonkräm" do not. So a produce rule counts only
# when the name has one.
PRODUCE = [
    # ---- TOMATOES ----
    (r'körsbärstomat|cherrytomat|cherry ?tomat|tomat.*cherry|piccolo', 'Cherry Tomato'),
    (r'plommontomat|tomat plommon', 'Plum Tomatoes'),
    (r'bifftomat|biff tomat', 'Beefsteak Tomatoes'),
    (r'kvisttomat|tomat.*kvist|tomater? på kvist', 'Vine Tomatoes'),
    (r'\btomat(er)?\b|\btomat ', 'Tomato'),

    # ---- OTHER VEGETABLES ----
    (r'\b(mini|snack)?gurk(a|or)\b', 'Cucumber'),
    (r'\bchili(peppar|frukt)?\b', 'Chili Pepper'),
    (r'\bpaprika(?!pulver|krydda)', 'Bell Pepper'),
    (r'rödlök|\blök röd|röd lök', 'Red Onion'),
    (r'salladslök|vårlök', 'Spring Onions'),
    (r'schalott', 'Shallots'),
    (r'vitlök', 'Garlic'),
    (r'purjolök|\bpurjo\b', 'Leek'),
    (r'\blök\b|gul lök|\bgullök', 'Onion'),
    (r'sötpotatis', 'Sweet Potato'),
    (r'\bpotatis\b|färskpotatis|bakpotatis|delikatesspotatis|mandelpotatis', 'Potato'),
    (r'\bmorot|morötter', 'Carrot'),
    (r'rödbet', 'Beetroot'),
    (r'blomkål', 'Cauliflower'),
    (r'broccoli', 'Broccoli'),
    (r'brysselkål', 'Brussels Sprouts'),
    (r'rödkål', 'Red Cabbage'),
    (r'savoykål', 'Savoy Cabbage'),
    (r'salladskål|kinakål', 'Napa Cabbage'),
    (r'grönkål', 'Kale'),
    (r'pak ?choi|bok ?choy', 'Bok Choy'),
    (r'spetskål|vitkål', 'White cabbage'),                        # not listed
    (r'kålrot', 'Rutabaga'),                                      # not listed
    (r'kålrabbi|kålrabi', 'Kohlrabi'),
    (r'rotselleri|selleri rot', 'Celeriac'),
    (r'blekselleri|stjälkselleri|stangselleri', 'Celery'),
    (r'palsternacka', 'Parsnip'),
    (r'persiljerot', 'Parsley root'),                             # not listed
    (r'fänkål', 'Fennel'),
    (r'butternut', 'Butternut Squash'),
    (r'\bpumpa\b|hokkaido', 'Pumpkin'),
    (r'zucchini|squash', 'Zucchini'),
    (r'aubergine', 'Eggplant'),
    (r'vit sparris', 'White Asparagus'),
    (r'\bsparris\b|grön sparris', 'Green Asparagus'),
    (r'babyspenat|\bspenat\b', 'Spinach'),
    (r'ruccola|rucola', 'Arugula'),
    (r'romansallad', 'Romaine Lettuce'),
    (r'hjärtsallad|minisallad', 'Mini Romaine'),
    (r'isbergssallad|isbergsallad', 'Iceberg lettuce'),           # not listed
    (r'\brädis', 'Radish'),
    (r'champinjon', 'White Mushroom'),
    (r'portobello', 'Portobello Mushroom'),
    (r'shiitake', 'Shiitake Mushroom'),
    (r'ostronskivling|ostronsvamp', 'Oyster Mushroom'),
    (r'haricots? verts|brytbönor|gröna bönor|sockerbönor', 'Green Beans'),
    (r'sugarsnaps?|sockerärt', 'Sugar Snap Peas'),
    (r'majskolv', 'Sweet Corn'),
    (r'ingefära', 'Fresh Ginger'),
    (r'jordärtskocka', 'Jerusalem Artichoke'),
    (r'kronärtskocka', 'Artichoke'),
    (r'pepparrot', 'Horseradish'),
    (r'\bokra\b', 'Okra'),
    (r'\bmajrova|\brova\b', 'Turnip'),

    # ---- FRUIT ----
    (r'pink lady', 'Pink Lady Apples'),
    (r'honeycrisp', 'Honeycrisp Apples'),
    (r'granatäpple', 'Pomegranate'),
    (r'\bäpple|\bäpplen\b', 'Apples'),
    (r'\bpäron\b', 'Pears'),
    (r'\bbanan(er)?\b', 'Banana'),
    (r'blodapelsin', 'Blood Oranges'),
    (r'\bapelsin(er)?\b', 'Oranges'),
    (r'klementin|clementin', 'Clementine'),
    (r'mandarin', 'Mandarin Oranges Fresh'),
    (r'\bcitron(er)?\b', 'Lemons'),
    (r'\blime\b', 'Lime'),
    (r'gröna vindruvor|vita vindruvor|vindruvor.*grön|vindruvor.*vit', 'Grapes Green'),
    (r'röda vindruvor|blå vindruvor|vindruvor.*röd|vindruvor.*blå', 'Grapes Red'),
    (r'\bjordgubbar?\b', 'Strawberries'),
    (r'\bhallon\b', 'Raspberry'),
    (r'\bblåbär\b', 'Blueberries'),
    (r'\bbjörnbär\b', 'Blackberries'),
    (r'röda vinbär', 'Red Currant'),
    (r'svarta vinbär', 'Black Currant'),
    (r'krusbär', 'Gooseberry'),
    (r'\bkörsbär\b', 'Cherries'),
    (r'\bplommon\b', 'Plums'),
    (r'\bpersika|\bpersikor', 'Peaches'),
    (r'\bkiwi', 'Kiwi'),
    (r'\bmango\b', 'Mango'),
    (r'\bavokado|\bavocado', 'Avocado'),
    (r'\bananas\b', 'Pineapple'),
    (r'vattenmelon', 'Watermelon'),
    (r'\b(honungs|galia|cantaloupe|nät|piel de sapo)?melon\b', 'Melon'),
    (r'\bfikon\b', 'Fig'),
    (r'passionsfrukt', 'Passion Fruit'),
    (r'\bkaki\b|sharonfrukt', 'Persimmon'),
    (r'\bpapaya', 'Papaya'),
    (r'\bkokosnöt', 'Coconut'),
    (r'\blitchi|\blychee', 'Lychee'),
]

GRADED = r'(?=.*\bklass ?[12i]\b)'

RULES = [(p, n, None, None) for p, n in RULES_RAW] + [('(?:' + p + ')' + GRADED, n, None, None) for p, n in PRODUCE]

TARGETS = {
    'Semi-skimmed Milk': None,
    'Mixed mince': None,
    'Ground poultry': None,
    'Ground lamb': None,
    'Pork tenderloin': None,
    'Turkey cut': None,
    'Lamb loin': None,
    'Chicken tenders': None,
    'White cabbage': None,
    'Rutabaga': None,
    'Parsley root': None,
    'Iceberg lettuce': None,
}
