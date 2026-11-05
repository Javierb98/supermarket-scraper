"""
German shelf names → catalogue products (Germany, Austria, and German-speaking
Switzerland and Liechtenstein).

The catalogue's own German names ("Tomate", "Gurke") already match the
plainest shelf names. These rules add what a dictionary does not know:

  - Austrian words: Paradeiser (tomato), Erdäpfel (potato), Karfiol
    (cauliflower), Melanzani (aubergine), Fisolen (green beans), Kohlsprossen
    (Brussels sprouts), Hendl (chicken), Faschiertes (mince), Schlagobers
    (cream), Pfefferoni (chilli), Marillen (apricots).
  - German compounds, where the product comes last: "Dattelcherrytomaten",
    "Snackkarotten", "Rinderfaschiertes". A pattern for a compound starts
    with \\w* so the match begins at the start of the word; the matcher then
    only has to accept what comes before it.
  - Shop brands that lead a shelf name ("Ja! Natürlich Bio Lauch", "Clever
    Tomaten", "Da komm ich her! Apfel"): LEADING, below.

A rule whose product the catalogue does not have (TARGETS → None) still
matches, so "Eisbergsalat" does not fall through to something wrong; its
prices are kept out of the averages and counted as products worth adding.
"""

import re

LANG = 'de'

FROZEN_SIGNALS = [r'tiefgek[üu]hlt', r'tiefk[üu]hl', r'\btk\b', r'gefroren', r'tiefgefroren']
CANNED_SIGNALS = [r'\bdose\b', r'\bkonserve', r'\bim glas\b', r'\beingelegt', r'\bh-milch\b', r'haltbarmilch', r'\bhaltbar']


def detect_state(raw_name):
    n = raw_name.lower()
    if any(re.search(p, n) for p in FROZEN_SIGNALS):
        return 'frozen'
    if any(re.search(p, n) for p in CANNED_SIGNALS):
        return 'canned'
    return 'fresh'


# Words a shelf name may start with that are not the product: shop brands,
# producer labels, origin and quality words. Compared after fold() (lower
# case, no accents or punctuation), so "Ja! Natürlich" is "ja naturlich".
LEADING = [
    # Austrian shops' own brands
    'billa', 'clever', 'ja', 'naturlich', 'da', 'komm', 'ich', 'her', 'immer', 'gut', 'genusswelt', 'premium',
    'spar', 'natur', 'pur', 's', 'budget', 'hofer', 'zuruck', 'zum', 'ursprung', 'milsani', 'mpreis', 'unimarkt',
    'penny', 'wunderlinge', 'free', 'tierwohl',
    # German shops' own brands
    'rewe', 'beste', 'wahl', 'regional', 'edeka', 'herzstucke', 'k', 'classic', 'favorina', 'lidl', 'gartenkronen',
    'aldi', 'nord', 'sud', 'netto', 'kaufland', 'gutgunstig', 'gunstig', 'nahkauf', 'alnatura', 'demeter', 'bioland',
    'naturland', 'enerbio', 'dmbio',
    # Producers and labels seen leading fresh produce
    'sanlucar', 'zespri', 'tante', 'fanny', 'lgv', 'pfanni', 'sauwald', 'simply', 'good', 'hofstadter', 'fair',
    'tier', 'ama', 'seeberger', 'kaiser', 'midi', 'raritaten', 'chiquita', 'dole', 'del', 'monte', 'mini', 'snack', 'junge', 'junger', 'jung',
    # ALDI wording before the product
    'back', 'speise', 'tafel', 'deutsches',
    # Origin and quality words
    'osterreichische', 'osterreichischer', 'osterreichisches', 'osterreich', 'steirische', 'steirischer',
    'wiener', 'tiroler', 'heimische', 'heimischer', 'deutsche', 'deutscher', 'frische', 'frischer', 'frisches',
    'frisch', 'feine', 'feiner', 'zarte', 'zarter', 'knackige', 'knackiger', 'saftige', 'saftiger', 'suße', 'suße',
    'susse', 'susser', 'grosse', 'grosser', 'kleine', 'kleiner', 'lose', 'gelegt', 'regionale', 'regionaler',
    'bio', 'organic', 'premium', 'extra', 'kl', 'klasse', 'i', 'ii',
    # Apple and pear varieties before the word "Apfel" / "Birne"
    'die', 'grillerei', 'toni', 'schlogl', 'carnuntum', 'wiesen', 'da',
    'gala', 'royal', 'jonagold', 'jonagored', 'golden', 'delicious', 'elstar', 'braeburn', 'granny', 'smith',
    'idared', 'topaz', 'fuji', 'kanzi', 'boskoop', 'kronprinz', 'rudolf', 'evelina', 'rubens', 'jazz', 'envy',
    'red', 'santana', 'cox', 'orange', 'pinova', 'wellant', 'shampion', 'gloster', 'arlet', 'cameo',
    'williams', 'abate', 'fetel', 'xenia', 'alexander', 'lucas', 'forelle', 'gute', 'luise',
]

# Products, processed or not food, that the fresh-produce patterns below
# would otherwise catch.
REJECT = [re.compile(p, re.I) for p in [
    r'gew[üu]rzgurk', r'essiggurk', r'delikatessgurk', r'senfgurk', r'cornichon', r'salzgurk',
    r'r[öo]stzwiebel', r'zwiebelring', r'zwiebelschmalz', r'knoblauchbrot', r'knoblauch.?butter', r'kr[äa]uterbutter',
    r'butterschmalz', r'erdnussbutter', r'butterkeks', r'streichfett', r'margarine',
    r'aufstrich', r'streichk[äa]se', r'schmelzk[äa]se', r'k[äa]secreme', r'\bdip\b', r'pesto', r'\bsugo\b',
    r'paniert', r'mariniert', r'gew[üu]rzt', r'cordon', r'kebab', r'gyros', r'[cč]evap', r'nugget', r'leberk[äa]se',
    r'wurst', r'schinken', r'salami', r'\bspeck\b', r'sous.?vide', r'gegrillt', r'gebraten', r'gekocht',
    r'ger[öo]stet', r'gesalzen', r'kandiert', r'schoko', r'studentenfutter', r'knabber', r'\bmus\b', r'apfelmus',
    r'fruchtzwerg', r'fruchtjoghurt', r'\bdrink\b', r'\blikör', r'liqueur', r'nudeln', r'\bvegan', r'veggie',
    r'pflanzlich', r'hafer', r'\bsoja', r'mandeldrink', r'kokosdrink', r'proteindrink', r'tramezzin', r'eiersalat',
    r'passiert', r'passata', r'ketchup', r'vanille', r'\bshots?\b', r'crespelle', r'ravioli', r'tortell', r'lasagne',
    r'(ananas|melone|mango|obst|fr[üu]chte|papaya)\w*\s+(geschnitten|st[üu]cke|w[üu]rfel)', r'fruchtsalat', r'obstsalat',
    r'snack.?(box|becher)', r'\bsticks?\b', r'\bkerne\b', r'gegart', r'\bgesch[äa]lt',
    r'gnocchi', r'pizza', r'toast', r'sandwich', r'\bbowl\b', r'\bsalat\b', r'strudel', r'auflauf',
    r'eier.?likör', r'ostereier', r'gef[äa]rbt', r'bemalt', r'pastete', r'babynahrung', r'quetsch',
]]

# (pattern, rule or catalogue name). The first match wins, so the specific
# come before the general. Patterns are searched in the lower-cased name.
RULES = [
    # ---- EGGS ----
    (r'wachtelei', 'Quail Eggs'),
    (r'enteneier|entenei\b', 'Duck Eggs'),
    (r'\bbio\b.*eier\b.*\bl\b|eier\b.*\bbio\b.*\bl\b', 'Organic Eggs L'),
    (r'\bbio\b.*eier\b.*\bm\b|eier\b.*\bbio\b.*\bm\b', 'Organic Eggs M'),
    (r'eier\b.*\bxxl\b', 'Eggs XXL'),
    (r'eier\b.*\bs\b', 'Eggs S'),
    (r'\w*eier\b|\beier\b', 'Eggs'),

    # ---- DAIRY: before milk, so "Heumilch Gouda" and "Heumilch Teebutter" are not milk ----
    (r'buttermilch', 'Buttermilk'),
    (r'kondensmilch|kaffeemilch|kaffeeobers|kaffeesahne', None),
    (r'cottage cheese|h[üu]ttenk[äa]se', 'Fresh Cottage Cheese'),
    (r'k[öo]rniger frischk[äa]se', 'Fresh Cottage Cheese'),
    (r'k[äa]se.?krainer', 'unlisted:kase krainer'),                  # a sausage with cheese in it
    (r'\bskyr\b(?!.*(beere|erdbeer|kirsch|pfirsich|mango|frucht|protein|drink|schoko))', 'Skyr'),
    (r'topfen|quark', None),
    (r'b[üu]ffel.?mozzarella|mozzarella.*b[üu]ffel|mozzarella di bufala', 'Buffalo Mozzarella'),
    (r'mozzarella', 'Mozzarella'),
    (r'ricotta', 'Ricotta'),
    (r'mascarpone', 'Mascarpone'),
    (r'\bfeta\b', 'Feta Cheese'),
    (r'parmigiano|parmesan', 'Parmesan'),
    (r'grana padano', None),
    (r'gorgonzola|blauschimmel|edelschimmel|dolcelatte|roquefort|cambozola', 'Blue Cheese'),
    (r'ziegenk[äa]se|ziegen.?frischk[äa]se|ziegen.?camembert|ch[èe]vre', 'Goat Cheese'),
    (r'schafk[äa]se|schaf.?camembert|schafsk[äa]se|pecorino', 'Sheep Cheese'),
    (r'frischk[äa]se|philadelphia|\bkiri\b|\bbresso\b|\bboursin\b', 'Cream Cheese'),
    (r'\w*(gouda|gauda)\b', 'Gouda Cheese'),
    (r'\bedamer\b|\bedam\b', 'Edam Cheese'),
    (r'emmentaler|emmental', 'Swiss Cheese'),
    (r'cheddar', 'Cheddar Cheese'),
    (r'provolone', 'Provolone'),
    (r'camembert|\bbrie\b', None),
    (r'bergk[äa]se|almk[äa]se|sennk[äa]se|alpk[äa]se|heumilchk[äa]se|tilsiter|\w*k[äa]se\b', 'Cheese'),
    (r'sauerrahmbutter', 'Cultured Butter'),
    (r'\w*butter\b|\bbeurre\b', 'Butter'),
    (r'sauerrahm|saure sahne|sauerer? rahm|saurer halbrahm|schmand|cr[èe]me fra[îi]che', None),
    (r'schlagobers|schlagsahne|schlagrahm|vollrahm|halbrahm|\bobers\b|(?<!mit )\bsahne\b', 'Cream'),
    (r'kochcreme|kochsahne|cremefine', None),

    # ---- DAIRY: MILK ----
    (r'ziegenmilch', 'Goat Milk'),
    (r'schafmilch', 'Sheep Milk'),
    (r'b[üu]ffelmilch', 'Buffalo Milk'),
    (r'kakao|schokomilch|vanillemilch|erdbeermilch|milchshake|eiskaffee|latte', None),
    (r'sauermilch|acidophilus', 'Fermented Milk'),
    (r'magermilch|entrahmte milch|milch\b.*\b0[.,][1-5] ?%', 'Skim Milk'),
    (r'fettarme frischmilch', 'unlisted:fettarme frischmilch'),     # semi-skimmed
    (r'^frische bio.?milch\b', 'Whole Milk'),                       # ALDI Nord: 3.8 % fat
    (r'leichtmilch|fettarme milch|teilentrahmt|milch\b.*\b(1[.,]5|0[.,]9|1[.,]8|2[.,]7) ?%', None),     # semi-skimmed: not in the catalogue
    (r'vollmilch|\w*heumilch\b|\w*alpenmilch\b|\w*wiesenmilch\b|\w*bergbauern ?milch\b|\bfrische milch|milch\b.*\b3[.,][5-9] ?%', 'Whole Milk'),

    # ---- POULTRY ----
    (r'(puten|truthahn)\w*.*(brust|schnitzel|filet)|\w*puten(brust|schnitzel|filet)', 'Turkey Breast'),
    (r'(puten|truthahn)\w*.*(keule|oberkeule|unterkeule)', 'Turkey Legs'),
    (r'(puten|truthahn)\w*.*fl[üu]ge(l|rl)', 'Turkey Wings'),
    (r'(puten|truthahn)\w*.*leber|putenleber', 'Turkey Liver'),
    (r'maishendl|maish[äa]hnchen|maispoulard', 'Corn-Fed Chicken'),
    (r'(hendl|h[äa]hnchen|h[üu]hner|huhn|chicken)\w*.*(brust|filet|schnitzel)|\w*(hendl|h[äa]hnchen|h[üu]hner)(brust|filet)', 'Chicken Breast'),
    (r'(hendl|h[äa]hnchen|h[üu]hner|chicken)\w*.*(fl[üu]gel|flügerl|wings)|\w*(hendl|h[äa]hnchen)fl[üu]gel', 'Chicken Wings'),
    (r'(hendl|h[äa]hnchen|h[üu]hner)\w*.*unterkeule|drumstick', 'Chicken Drumsticks'),
    (r'(hendl|h[äa]hnchen|h[üu]hner)\w*.*(schenkel|keule|haxerl|haxe|viertel)|\w*(hendl|h[äa]hnchen|h[üu]hner)(schenkel|keule|haxerl|keulen)', 'Chicken Thigh'),
    (r'(hendl|h[üu]hner|h[äa]hnchen)\w*.*leber|h[üu]hnerleber|hendlleber', 'Chicken Liver'),
    (r'(hendl|h[äa]hnchen|h[üu]hner)\w*.*faschiert', None),
    (r'\bbrath[äa]hnchen\b(?!.*(paprika|gew[üu]rz|mariniert|halb))', 'Whole Chicken'),   # ALDI Nord "Deutsches Brathähnchen"
    (r'brathendl|ganzes (hendl|h[äa]hnchen)|\bhendl\b.*\bganz|\w*hendl\b\s*(\(|$)|\bh[äa]hnchen\b.*\bganz|grillh[äa]hnchen|suppenhuhn', 'Whole Chicken'),
    (r'entenbrust|ente.*brust', 'Duck Breast'),
    (r'entenkeule|ente.*keule', 'Duck Leg'),

    # ---- MEAT ----
    (r'(rind|rinder|rinds)\w*\s*faschiert|\w*rinderfaschiert|\w*rindsfaschiert|rinderhack|faschiertes? vom rind|hackfleisch.*rind', 'Ground Beef'),
    (r'(schwein|schweins|schweine)\w*\s*faschiert|schweinehack|faschiertes? vom schwein|hackfleisch.*schwein', 'Ground Pork'),
    (r'faschiert|hackfleisch', None),       # mixed beef and pork
    (r'lungenbraten.*rind|rinderfilet|rindsfilet|rind.*filet', 'Fresh Tenderloin'),
    (r'rib.?eye|entrec[ôo]te', 'Fresh Ribeye'),
    (r'rumpsteak|beiried|roastbeef|striploin', 'Fresh Striploin'),
    (r'h[üu]ftsteak|tafelspitz|h[üu]fte', 'Fresh Sirloin'),
    (r't-?\s*bone|porterhouse', 'Fresh Porterhouse'),
    (r'markknochen|marksknochen', 'Beef Marrow Bones'),
    (r'(rind|rinder|rinds)\w*\s*steak|\w*rind\w*steak|flanksteak|flank steak', 'Beef Steak'),
    (r'rinderbrust|rindsbrust|brust vom rind', 'Beef Brisket'),
    (r'ochsenschwanz', 'Beef Tail'),
    (r'rinderzunge|rindszunge', 'Beef Tongue'),
    (r'rinderleber|rindsleber', 'Beef Liver'),
    (r'(schwein|schweins)\w*\s*bauch|\w*bauchfleisch|schweinebauch|schweinsbauch', 'Pork Belly'),
    (r'spare.?ribs|\w*ripperl|schweinerippchen|rippchen', 'Pork Ribs'),
    (r'(schwein|schweins)\w*\s*kotelett|\w*schweinskotelett|\w*schweinekotelett|karreekotelett|stielkotelett|schopfkotelett|lachskotelett', 'Pork Chops'),
    (r'(schwein|schweins)\w*\s*schulter|schweineschulter|schweinsschulter', 'Pork Shoulder'),
    (r'lammkotelett|lammkarree|lammracks?\b', 'Lamb Chops'),
    (r'lammkeule|lammstelze|lamm.?keule', 'Lamb Leg'),
    (r'lammschulter|lamm.?schulter', 'Lamb Shoulder'),
    (r'kaninchen', 'Rabbit Meat'),
    (r'wildschwein', 'Wild Boar'),
    (r'hirsch', 'Venison'),

    # ---- VEGETABLES: TOMATOES ----
    (r'\w*(cherry|cocktail|kirsch|dattel|snack|mini|perl|trauben)\w*\s*(-\s*)?(tomate|tomaten|paradeiser)\b|\w*(cherry|kirsch|dattel|cocktail)\w*(tomate|tomaten|paradeiser)\b', 'Cherry Tomato'),
    (r'\w*(rispen|strauch)\w*\s*(tomate|tomaten|paradeiser)\b|\w*(rispen|strauch)(tomate|tomaten|paradeiser)\b', 'Vine Tomatoes'),
    (r'\w*(fleisch|ochsenherz|coeur de boeuf)\w*\s*(tomate|tomaten|paradeiser)\b|\w*fleischtomaten?\b', 'Beefsteak Tomatoes'),
    (r'\bromatomaten?\b|\broma\s*(-\s*)?(tomate|tomaten|paradeiser)\b|\w*pflaumen\s*(-\s*)?(tomate|tomaten)\b|\w*pflaumentomaten?\b|san marzano\w*\s*(tomate|tomaten)?', 'Plum Tomatoes'),
    (r'\w*(tomate|tomaten|paradeiser)\b', 'Tomato'),

    # ---- VEGETABLES ----
    (r'\w*s[üu][sß]+kartoffel\w*|\w*batate\w*', 'Sweet Potato'),
    (r'speisekartoffeln?\b.*drillinge', 'Mini Potatoes'),          # "Kleine Speisekartoffeln „Drillinge“"
    (r'drillinge|mini.?(kartoffel|erd[äa]pfel)|baby.?(kartoffel|erd[äa]pfel)', 'Mini Potatoes'),
    (r'\w*(kartoffel|kartoffeln|erd[äa]pfel)\b', 'Potato'),
    (r'\w*(snack|baby|mini)(karotte|karotten|m[öo]hre|m[öo]hren)\b', 'Baby Carrots'),
    (r'\w*(karotte|karotten|m[öo]hre|m[öo]hren|r[üu]ebli)\b', 'Carrot'),
    (r'\w*(fr[üu]hlings|jung|lauch|bund)zwiebel\w*', 'Spring Onions'),
    (r'\w*rote zwiebel\w*|\w*zwiebeln? rot\b|\w*rotezwiebel', 'Red Onion'),
    (r'\w*(weiße|weisse) zwiebel\w*|\w*zwiebeln? wei(ß|ss)\b|gem[üu]sezwiebel', 'White Onion'),
    (r'schalotte\w*', 'Shallots'),
    (r'perlzwiebel\w*', 'Pearl Onions'),
    (r'\w*zwiebel\w*', 'Onion'),
    (r'(junger|jung|frischer) knoblauch|knoblauch.*frisch', 'Baby Garlic'),
    (r'\w*knoblauch\w*', 'Garlic'),
    (r'\w*(salatgurke|feldgurke|minigurke|snackgurke|landgurke|gurke|gurken)\b', 'Cucumber'),
    (r'\w*(mini|snack|baby)\w*\s*paprika|\w*(mini|snack|baby)paprika', 'Baby Pepper'),
    (r'\w*paprika(schoten?|s)?\b', 'Bell Pepper'),
    (r'jalape[ñn]o', 'Jalapeño'),
    (r'habanero', 'Habanero'),
    (r'\w*pfefferoni\w*|\w*peperoni\w*|\bchili\b|\bchilis\b|chilischote', 'Chili Pepper'),
    (r'\w*zucchin[ie]\b', 'Zucchini'),
    (r'\w*(melanzani|aubergine|auberginen)\b', 'Eggplant'),
    (r'\w*(brokkoli|broccoli)\b', 'Broccoli'),
    (r'\w*(karfiol|blumenkohl)\b', 'Cauliflower'),
    (r'romanesco', 'Romanesco'),
    (r'\w*(blattspinat|jungspinat|babyspinat|spinat)\b', 'Spinach'),
    (r'gr[üu]nkohl|\bkale\b', 'Kale'),
    (r'\w*(rucola|rauke)\b', 'Arugula'),
    (r'chicor[ée]e|chicoree', 'Endive'),
    (r'radicchio', 'Radicchio'),
    (r'eichblatt', 'Oak Leaf Lettuce'),
    (r'fris[ée]e', 'Frisée Lettuce'),
    (r'endivie', 'Curly Endive'),
    (r'\w*(r[öo]mersalat|romana|salatherz|salatherzen)\b', 'Romaine Lettuce'),
    (r'eisberg|eissalat|h[äa]uptel|kopfsalat|butterkopf|lollo|vogerl|feldsalat|batavia|blattsalat|pflücksalat|mischsalat|salatmix', None),
    (r'(\w*k[üu]rbis\s+)?\w*(butternuss|butternut)\w*', 'Butternut Squash'),
    (r'spaghettik[üu]rbis', 'Spaghetti Squash'),
    (r'\w*k[üu]rbis\b|\bhokkaido\b', 'Pumpkin'),
    (r'\w*(rote r[üu]be|rote r[üu]ben|rote bete|rote beete|randen)\b', 'Beetroot'),
    (r'\w*(knollensellerie|zeller|sellerieknolle)\b', 'Celeriac'),
    (r'\w*(stangensellerie|staudensellerie|stangenzeller|sellerie)\b', 'Celery'),
    (r'\b(lauch|porree|lauchstange)\w*', 'Leek'),
    (r'radieschen', 'Radish'),
    (r'schwarzer? rettich|rettich schwarz', None),
    (r'\w*rettich\b', 'Daikon Radish'),
    (r'\w*fenchel\b', 'Fennel'),
    (r'kohlrabi', 'Kohlrabi'),
    (r'\w*(rotkraut|rotkohl|blaukraut)\b', 'Red Cabbage'),
    (r'\w*(wirsing|wirsingkohl)\b|^kohl\b', 'Savoy Cabbage'),
    (r'chinakohl', 'Napa Cabbage'),
    (r'pak.?choi|pak.?choy|bok.?choy', 'Bok Choy'),
    (r'\w*(kohlsprossen|rosenkohl)\b', 'Brussels Sprouts'),
    (r'wei(ß|ss)kraut|wei(ß|ss)kohl|spitzkraut|spitzkohl|\bkraut\b', None),
    (r'\w*(maiskolben|zuckermais|grillmais|\bmais\b)', 'Sweet Corn'),
    (r'pastinake|pastinaken', 'Parsnip'),
    (r'mangold', 'Swiss Chard'),
    (r'(wei(ß|ss)er|wei(ß|ss)e|bleich)\w*\s*spargel|spargel\w*\s*wei(ß|ss)', 'White Asparagus'),
    (r'gr[üu]ne?r?\s*spargel|spargel\w*\s*gr[üu]n', 'Green Asparagus'),
    (r'\w*spargel\b', 'Asparagus'),
    (r'artischocke', 'Artichoke'),
    (r'\w*(fisolen|prinzessbohnen|buschbohnen|stangenbohnen|gr[üu]ne bohnen|brechbohnen)\b', 'Green Beans'),
    (r'zuckerschote|kaiserschote', 'Snow Peas'),
    (r'\w*ingwer\b', 'Fresh Ginger'),
    (r'kurkuma', 'Fresh Turmeric'),
    (r'\bkren\b|meerrettich', 'Horseradish'),
    (r'shiitake', 'Shiitake Mushroom'),
    (r'austernpilz\w*|austernseitling\w*', 'Oyster Mushroom'),
    (r'portobello', 'Portobello Mushroom'),
    (r'enoki', 'Enoki Mushroom'),
    (r'(braune|brauner|steinpilz)\w*\s*champignon|champignons? braun', None),
    (r'\w*champignon\w*', 'White Mushroom'),
    (r'eierschwammerl|pfifferling|kr[äa]uterseitling|steinpilz|pilzmix|pilze\b', None),
    (r'topinambur', 'Jerusalem Artichoke'),
    (r'schwarzwurzel', 'Salsify'),
    (r'okra', 'Okra'),
    (r'maniok|yuca', 'Yuca'),
    (r'peterwurz|petersilienwurzel', None),
    (r'brunnenkresse', 'Watercress'),
    (r'\bkresse\b', None),
    (r'sprossen', None),

    # ---- HERBS ----
    (r'petersilie', 'Parsley'),
    (r'schnittlauch', 'Chives'),
    (r'basilikum', 'Genovese Basil'),
    (r'\bdill\b', 'Dill'),
    (r'\bminze\b|pfefferminze', 'Mint'),
    (r'rosmarin', 'Rosemary'),
    (r'thymian', 'Thyme'),
    (r'koriander', 'Cilantro'),

    # ---- FRUIT ----
    (r'pink lady', 'Pink Lady Apples'),
    (r'honeycrisp', 'Honeycrisp Apples'),
    (r'ambrosia', 'Ambrosia Apples'),
    (r'granatapfel|granat[äa]pfel', 'Pomegranate'),
    (r'\w*(apfel|[äa]pfel)\b', 'Apples'),
    (r'nashi', None),
    (r'\w*(birne|birnen)\b', 'Pears'),
    (r'kochbanane', 'Plantain'),
    (r'\w*(banane|bananen)\b', 'Banana'),
    (r'blutorange', 'Blood Oranges'),
    (r'\w*(orange|orangen)\b', 'Oranges'),
    (r'\w*(clementine|clementinen|klementine|klementinen)\b', 'Clementine'),
    (r'\w*(mandarine|mandarinen|satsuma|satsumas)\b', 'Tangerine'),
    (r'cranberr', 'Cranberry'),
    (r'\w*(zitrone|zitronen)\b', 'Lemons'),
    (r'\w*(limette|limetten)\b', 'Lime'),
    (r'grapefruit|pomelo|orangina', None),
    (r'(trauben|weintrauben).*(wei(ß|ss)\s*/\s*rot|rot\s*/\s*wei(ß|ss))', None),
    (r'tafeltrauben\b.*(dunkel|rot|blau)', 'Grapes Red'),
    (r'tafeltrauben\b.*(hell|wei(ß|ss)|gr[üu]n)', 'Grapes Green'),
    (r'(trauben|weintrauben).*(rot|blau|dunkel|schwarz)|(rote|blaue|dunkle)\w*\s*(trauben|weintrauben)', 'Grapes Red'),
    (r'(trauben|weintrauben).*(wei(ß|ss)|hell|gr[üu]n)|(wei(ß|ss)e|helle|gr[üu]ne)\w*\s*(trauben|weintrauben)', 'Grapes Green'),
    (r'\w*(trauben|weintrauben)\b', None),      # white and red mixed
    (r'\w*erdbeere?n?\b', 'Strawberries'),
    (r'\w*himbeere?n?\b', 'Raspberry'),
    (r'\w*(heidelbeere|heidelbeeren|blaubeere|blaubeeren)\b', 'Blueberries'),
    (r'\w*brombeere?n?\b', 'Blackberries'),
    (r'rote johannisbeere|ribisel rot|johannisbeeren rot', 'Red Currant'),
    (r'schwarze johannisbeere|ribisel schwarz', 'Black Currant'),
    (r'stachelbeere', 'Gooseberry'),
    (r'\w*(kirsche|kirschen)\b', 'Cherries'),
    (r'marille|aprikose', None),
    (r'nektarine', None),
    (r'\w*(pfirsich|pfirsiche)\b', 'Peaches'),
    (r'\w*(zwetschke|zwetschken|zwetschge|zwetschgen|pflaume|pflaumen)\b', 'Plums'),
    (r'\w*kiwi\b|\w*kiwis\b|kiwi gold', 'Kiwi'),
    (r'riesenmango', 'Giant Mango'),
    (r'\w*mango\b|\w*mangos\b', 'Mango'),
    (r'mini.?ananas', 'Mini Pineapple'),
    (r'\w*ananas\b', 'Pineapple'),
    (r'\w*avocados?\b', 'Avocado'),
    (r'wassermelone', 'Watermelon'),
    (r'\w*(honigmelone|zuckermelone|galiamelone|cantaloupe|charentais|melone)\b', 'Melon'),
    (r'\w*(feige|feigen)\b', 'Fig'),
    (r'\w*(dattel|datteln)\b', 'Date'),
    (r'\bkaki\b|sharon', 'Persimmon'),
    (r'\w*papaya\b', 'Papaya'),
    (r'maracuja|passionsfrucht', 'Passion Fruit'),
    (r'litschi|lychee', 'Lychee'),
    (r'\w*kokosnuss\w*', 'Coconut'),
    (r'drachenfrucht|pitahaya|pitaya', 'Dragon Fruit'),
    (r'physalis|kaktusfeige|quitte|rhabarber|kiwano|granadilla', None),
    (r'maroni|esskastanie|edelkastanie', 'Chestnuts'),
    (r'walnu(ss|ß)|walnüsse|walnusskern', 'Walnuts'),
    (r'haselnu(ss|ß)|haselnüsse|haselnusskern', 'Hazelnuts'),
    (r'\bmandeln\b|mandelkern', 'Almonds'),
    (r'pinienkern', 'Pine Nuts'),
    (r'k[üu]rbiskern', 'Pumpkin Seeds'),
]

TARGETS = {'unlisted:fettarme frischmilch': None, 'unlisted:kase krainer': None}

# A rule's name is its catalogue name unless TARGETS says otherwise; None as
# a name (above) means the product is known and the catalogue does not have
# it. The matcher looks names up in TARGETS, so give each None a label.
_unlisted = []
for _i, (_p, _n) in enumerate(RULES):
    if _n is None:
        _label = 'unlisted:' + re.sub(r'[^a-z]+', ' ', _p.split('|')[0].lower()).strip()[:40]
        RULES[_i] = (_p, _label)
        TARGETS[_label] = None
