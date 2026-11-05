"""
Estonian shelf names → catalogue products (Selver).

The catalogue has no Estonian names, so nothing Estonian is priced unless a
rule here names it. A rule whose name the catalogue does not list (TARGETS →
None) still matches, so "sea-veise hakkliha" stops at "not a product we
list" rather than falling through to pork or beef.

Selver names lead with the product ("Porgand pestud, kg", "Täispiim 3,6%,
FARMI, 1 L"), and the brand comes after it in capitals. Processed food is
turned away by REJECT (pipeline/processed.py has no Estonian words).
Patterns run on the lower-cased shelf name, accents kept (õ, ä, ö, ü, š).
"""

import re

LANG = 'et'

# Words an Estonian shelf name may start with that are not the product.
# Folded: lower case, accents stripped (õ → o, ä → a, š → s).
LEADING = [
    'mahe', 'oko', 'eesti', 'eestimaine', 'varske', 'kodumaine', 'punane', 'punased', 'kollane',
    'kollased', 'roheline', 'rohelised', 'sinine', 'valge', 'valged', 'hele', 'suur', 'suured',
    'vaike', 'vaikesed', 'mini', 'seen', 'saaremaa', 'lahtine', 'pestud', 'pakitud', 'jahutatud', 'magus', 'magusad', 'noor',
]

FROZEN = re.compile(r'külmutatud|sügavkülm|\bkülm\b', re.I)
CANNED = re.compile(r'konserv|purgis|\bpurk\b|marineeritud|hapendatud', re.I)


def detect_state(raw_name):
    if FROZEN.search(raw_name):
        return 'frozen'
    if CANNED.search(raw_name):
        return 'canned'
    return 'fresh'


REJECT = [re.compile(p, re.I) for p in [
    # prepared and preserved vegetables
    r'\bmahl|smuuti|\bsupp|kaste\b|puljong|korea salat|kartulisalat|kimchi|hapukapsas|hapukurk|soolakurk|praekapsas',
    r'riivitud|kuubik|viilutatud|ribad\b|\bribad|tükid|ahjusegu|\bsegu\b|\bmix\b|krõps|friikart|püree|moos|keedis|kuivatatud|hoidis',
    # flavoured, plant-based and fermented dairy
    r'laktoosivaba|lakt\.? ?vaba|cappuccino|keefir|jogurt|\bjook|kaera|soja|mandli|kookos|kondenspiim|maitseline|šokolaadi|vanilli|magustoit|puding',
    r'kohuke|rjaženka|hapendatud|\bpett\b|kohvikoor|piimajook|kõrgkuum|kohvi|latte|vahustatav|määrdejuust|sulatatud|juustupul|snäkk|pihustiga|ghee|trühvli|kukeseene|pähklitega|tšilliga|küüslaugu|ürdi',
    r'margariin|võie\b|võidepuder|ürdivõi|küüslauguvõi|võileiv',
    # prepared meat
    r'marinaad|marineeritud|šašlõkk|sašlõkk|maitsestatud|suitsu|keedu|grill|paneeritud|pihv|šnitsel|snitsel|eelküpsetatud',
    r'küpsetatud|kotlet|vorst|viiner|\bsink|rulaad|pelmeen|tulised|küpsetuskarbis|piprane|ploomidega|sinepine|aasiapärane|juustuga|majonees|kreeka|toscana|kebab|burger',
    # combined products: "Kodujuust hapukoorega", "Mais sidruni ja tšilliga"
    r'\bja\b|&|\w{3,}[aeiu]ga\b|beebitoit',
    # not food, fish
    r'võrsed|\bidu|idusalat|\bkala\b|lõhe|forell|heeringas|räim|kilu|krevet|tuunikala|šampoon|seep|koer|kass',
]]

RULES_RAW = [
    # ---- EGGS ----
    (r'vutimuna', 'Quail Eggs'),
    (r'munavalge|munakollane|munapulber', 'Liquid egg'),           # not listed
    (r'\bmunad?\b|kanamuna|talumuna|peremuna|õrrekanade', 'Eggs'),

    # ---- DAIRY ----
    (r'vahukoor', 'Cream'),
    (r'\bvõi\b', 'Butter'),
    (r'kodujuust', 'Fresh Cottage Cheese'),
    (r'toorjuust|philadelphia', 'Cream Cheese'),
    (r'kohupiim', 'Quark'),                                        # not listed
    (r'hapukoor|smetana', 'Sour cream'),                           # not listed
    (r'\bmozzarella', 'Mozzarella'),
    (r'parmesan|parmigiano', 'Parmesan'),
    (r'\bfeta\b|fetajuust', 'Feta Cheese'),
    (r'\bcheddar', 'Cheddar Cheese'),
    (r'\bgouda\b', 'Gouda Cheese'),
    (r'\bedam\b|edami', 'Edam Cheese'),
    (r'\bbrie\b', 'Brie'),
    (r'camembert', 'Camembert'),
    (r'sinihallitus|gorgonzola|roquefort|dor blu', 'Blue Cheese'),
    (r'\bricotta', 'Ricotta'),
    (r'mascarpone', 'Mascarpone'),
    (r'kitsejuust|kitsepiimajuust|chèvre|chevre', 'Goat Cheese'),
    (r'\bjuust\b|eesti juust|hollandi juust|vene juust|atleet|saare juust', 'Cheese'),
    # Milk after the cheeses: "Eesti Juust täispiimast" is a cheese.
    (r'rasvata piim|rasvatu piim|piim rasvatu|rasvavaba piim|\blõss\b', 'Skim Milk'),
    (r'täispiim|mahetäispiim|piim 3[,.][5-9]|piim 4[,.]', 'Whole Milk'),
    (r'\bpiim\b', 'Semi-skimmed Milk'),                            # not listed (2.5 %, 1.8 %)

    # ---- MEAT & POULTRY ----
    (r'sea-veise|veise-sea|segahakkliha|seguhakkliha|hakklihasegu', 'Mixed mince'),  # not listed
    (r'kana.*hakkliha|broileri.*hakkliha|kalkuni.*hakkliha|linnuhakkliha|hakkliha.*(kana|broileri)', 'Ground poultry'),  # not listed
    (r'sea(liha)?[- ]?hakkliha', 'Ground Pork'),
    (r'veise(liha)?[- ]?hakkliha|loomaliha hakkliha', 'Ground Beef'),
    (r'pardi ?rinna', 'Duck Breast'),
    (r'pardikoib|pardi koib', 'Duck Leg'),
    (r'pardi ?tiiv', 'Duck Wings'),
    (r'kalkuni ?rinna|kalkunifilee', 'Turkey Breast'),
    (r'kalkuni', 'Turkey cut'),                                    # not listed
    (r'rinnafilee|kanafilee|kanarinna', 'Chicken Breast'),
    (r'kintsuliha|kintsud seljata', 'Chicken Thigh'),
    (r'(pool)?koiv|(pool)?koib\b', 'Chicken Drumsticks'),
    (r'tiivad|pooltiib|tiib\b', 'Chicken Wings'),
    (r'kanamaks|broilerimaks', 'Chicken Liver'),
    (r'ahjubroiler|terve broiler|broiler terve|ahjukana|terve kana|\bbroiler,', 'Whole Chicken'),
    (r'sea ?sisefilee|seafilee', 'Pork tenderloin'),               # not listed
    (r'kaelakarbonaad|karbonaad', 'Pork Chops'),
    (r'seakülg|külgliha', 'Pork Belly'),
    (r'veise ?ribid|veiseribi', 'Beef Ribs'),
    (r'ribid|ribi\b', 'Pork Ribs'),
    (r'sea ?abaliha|seaabaliha', 'Pork Shoulder'),
    (r'veise ?abaliha', 'Fresh Chuck Roast'),
    (r'sea ?välisfilee|seavälisfilee', 'Pork loin'),
    (r'antrekoo[td]|ribeye', 'Fresh Ribeye'),
    (r'veise ?sisefilee|veise.*sisefilee', 'Fresh Tenderloin'),
    (r'veise ?välisfilee|veise.*välisfilee', 'Fresh Sirloin'),
    (r'veisemaks', 'Beef Liver'),
    (r'lambakarree', 'Lamb Rib Rack'),
    (r'lambakoot|lambakints', 'Lamb Leg'),
    (r'põdra|hirve|metskitse', 'Venison'),
    (r'metssea|metssiga', 'Wild Boar'),

    # ---- TOMATOES ----
    (r'kirsstomat|kirss-?ploomtomat|kirsskobartomat|cherry ?tomat|tomat.*cherry', 'Cherry Tomato'),
    (r'ploomtomat', 'Plum Tomatoes'),
    (r'lihatomat', 'Beefsteak Tomatoes'),
    (r'kobartomat|tomat.*kobar|tomat.*oksal', 'Vine Tomatoes'),
    (r'\btomat(id)?\b', 'Tomato'),

    # ---- OTHER VEGETABLES ----
    (r'\b(mini|aed|kasvuhoone|lühi|pikk)?kurk\b|\bkurgid\b', 'Cucumber'),
    (r'tšilli|tsilli|\bchili\b', 'Chili Pepper'),
    (r'\bpaprika', 'Bell Pepper'),
    (r'punane sibul|sibul punane|salatisibul', 'Red Onion'),
    (r'šalottsibul|salottsibul', 'Shallots'),
    (r'roheline sibul|lehtsibul|sibulapealsed', 'Spring Onions'),
    (r'küüslauk', 'Garlic'),
    (r'porrulauk|\bporru\b', 'Leek'),
    (r'mugulsibul|\bsibul\b', 'Onion'),
    (r'bataat|maguskartul', 'Sweet Potato'),
    (r'beebikartul|noorkartul|väikekartul|minikartul', 'Mini Potatoes'),
    (r'\bkartul(id)?\b', 'Potato'),
    (r'beebiporgand', 'Baby Carrots'),
    (r'\bporgand(id)?\b', 'Carrot'),
    (r'\bpeet\b|\bpeedid\b|punapeet', 'Beetroot'),
    (r'lillkapsas', 'Cauliflower'),
    (r'beebibrokoli', 'Baby Broccoli'),
    (r'brokoli|spargelkapsas', 'Broccoli'),
    (r'rooskapsas|brüsseli kapsas', 'Brussels Sprouts'),
    (r'punane kapsas|kapsas punane|punakapsas', 'Red Cabbage'),
    (r'savoia|kähar kapsas', 'Savoy Cabbage'),
    (r'hiina ?kapsas', 'Napa Cabbage'),
    (r'lehtkapsas|käharkapsas', 'Kale'),
    (r'nuikapsas', 'Kohlrabi'),
    (r'pak ?choi|bok ?choy', 'Bok Choy'),
    (r'peakapsas|valge kapsas|\bkapsas\b|teravapeakapsas', 'White cabbage'),  # not listed
    (r'kaalikas', 'Rutabaga'),                                     # not listed
    (r'naeris', 'Turnip'),
    (r'juurseller', 'Celeriac'),
    (r'varsseller|lehtseller', 'Celery'),
    (r'pastinaak', 'Parsnip'),
    (r'petersellijuur', 'Parsley root'),                           # not listed
    (r'fenkol', 'Fennel'),
    (r'suvikõrvits|tsukiini|kabatšokk', 'Zucchini'),
    (r'butternut|muskaatkõrvits|võikõrvits', 'Butternut Squash'),
    (r'kõrvits', 'Pumpkin'),
    (r'baklažaan|baklazaan', 'Eggplant'),
    (r'valge spargel', 'White Asparagus'),
    (r'spargel', 'Green Asparagus'),
    (r'beebispinat|spinat', 'Spinach'),
    (r'rukola|rucola|ruccola', 'Arugula'),
    (r'rooma salat|romaine', 'Romaine Lettuce'),
    (r'jääsalat', 'Iceberg lettuce'),                              # not listed
    (r'\bredis', 'Radish'),
    (r'šampinjon|sampinjon', 'White Mushroom'),
    (r'portobello', 'Portobello Mushroom'),
    (r'shiitake', 'Shiitake Mushroom'),
    (r'austerservik', 'Oyster Mushroom'),
    (r'kukeseen', 'Chanterelle'),                                  # not listed
    (r'aeduba|rohelised oad|türgiuba|uba roheline', 'Green Beans'),
    (r'suhkruhernes|herne ?kaun|kaunhernes', 'Sugar Snap Peas'),
    (r'maisitõlvik|mais tõlvik', 'Sweet Corn'),
    (r'ingver', 'Fresh Ginger'),
    (r'maapirn', 'Jerusalem Artichoke'),
    (r'artišokk|artisokk', 'Artichoke'),
    (r'mädarõigas', 'Horseradish'),
    (r'\bokra\b', 'Okra'),

    # ---- FRUIT ----
    (r'granaatõun', 'Pomegranate'),
    (r'pink lady', 'Pink Lady Apples'),
    (r'honeycrisp', 'Honeycrisp Apples'),
    (r'\bõun(ad)?\b', 'Apples'),
    (r'\bpirn(id)?\b', 'Pears'),
    (r'\bbanaan(id)?\b', 'Banana'),
    (r'verev apelsin|punane apelsin', 'Blood Oranges'),
    (r'\bapelsin(id)?\b', 'Oranges'),
    (r'klementiin', 'Clementine'),
    (r'mandariin', 'Mandarin Oranges Fresh'),
    (r'\bsidrun(id)?\b', 'Lemons'),
    (r'\blaim(id)?\b', 'Lime'),
    (r'viinamari hele|viinamarjad hele|heledad viinamarjad|rohelised viinamarjad', 'Grapes Green'),
    (r'viinamari (punane|tume|must)|viinamarjad (punased|tumedad)|punased viinamarjad|tumedad viinamarjad', 'Grapes Red'),
    (r'\bmaasika(d)?\b|\bmaasikas\b', 'Strawberries'),
    (r'\bvaarika(d)?\b|\bvaarikas\b', 'Raspberry'),
    (r'\bmustika(d)?\b|\bmustikas\b', 'Blueberries'),
    (r'põldmurakad?|põldmurakas', 'Blackberries'),
    (r'punane sõstar|punased sõstrad', 'Red Currant'),
    (r'must sõstar|mustad sõstrad', 'Black Currant'),
    (r'karusmari|karusmarjad', 'Gooseberry'),
    (r'\bkirsid\b|maguskirs', 'Cherries'),
    (r'\bploom(id)?\b', 'Plums'),
    (r'\bvirsik', 'Peaches'),
    (r'\bkiivi', 'Kiwi'),
    (r'\bmango\b', 'Mango'),
    (r'\bavokaado', 'Avocado'),
    (r'\bananass', 'Pineapple'),
    (r'\barbuus', 'Watermelon'),
    (r'\bmelon\b', 'Melon'),
    (r'viigimari|viigimarjad', 'Fig'),
    (r'passionivili|granadill', 'Passion Fruit'),
    (r'hurmaa|\bkaki\b|persimon', 'Persimmon'),
    (r'papaia|papaya', 'Papaya'),
    (r'kookospähkel', 'Coconut'),
    (r'liitši|litši', 'Lychee'),
    (r'pitahaia|pitaya', 'Dragon Fruit'),
]

RULES = [(p, n, None, None) for p, n in RULES_RAW]

TARGETS = {
    'Liquid egg': None,
    'Semi-skimmed Milk': None,
    'Quark': None,
    'Sour cream': None,
    'Mixed mince': None,
    'Ground poultry': None,
    'Turkey cut': None,
    'Pork tenderloin': None,
    'Pork loin': None,
    'White cabbage': None,
    'Rutabaga': None,
    'Parsley root': None,
    'Iceberg lettuce': None,
    'Chanterelle': None,
}
