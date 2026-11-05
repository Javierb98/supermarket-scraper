"""
Croatian shelf names → catalogue products.

The names come from the price lists Croatian chains must publish by law
(NN 75/2025), read through cijene.dev's daily archives (feeds/cijene_hr.py).
They are written every which way: "RAJČICA GRAPPOLO", "Rajčica mini roma
250 g", "JABUKA ZLATNI DEL.", sometimes without the diacritics. So every
pattern here is loosened before it is compiled: č and ć also match c, š
matches s, ž matches z, đ matches dj and d (see loose()).

A rule's name is the catalogue's English name where the catalogue has the
product; otherwise it is a name of its own listed in TARGETS as None — it
still matches, so "kupus" (white cabbage) is not left for a looser rule to
misread, but its prices stay out of the averages.

The helpers loose() and to_cyrillic() are used by the Serbian rules too.
"""

import re

LANG = 'hr'

# ── Pattern helpers ─────────────────────────────────────────────────────

_LATIN_LOOSE = {
    'č': 'čćc', 'ć': 'ćčc', 'š': 'šs', 'ž': 'žz',
}


def _walk(pattern, single, multi=None):
    """Rewrite a regex letter by letter, leaving escapes alone.

    single: char → string of alternative characters (one of them matches)
    multi:  char → list of alternative strings, used outside [...] only
    """
    out, i, in_class = [], 0, False
    multi = multi or {}
    while i < len(pattern):
        c = pattern[i]
        if c == '\\' and i + 1 < len(pattern):
            out.append(pattern[i:i + 2])
            i += 2
            continue
        if in_class:
            if c == ']':
                in_class = False
                out.append(c)
            else:
                out.append(single.get(c, c))
            i += 1
            continue
        if c == '[':
            in_class = True
            out.append(c)
            # A leading ^ or ] belongs to the class syntax.
            if pattern[i + 1:i + 2] == '^':
                out.append('^')
                i += 1
            i += 1
            continue
        if c == '(' and pattern[i + 1:i + 2] == '?':
            # (?:  (?=  (?!  (?<=  (?<!  — copy the group's opening as is.
            j = i + 2
            while j < len(pattern) and pattern[j] in ':=!<':
                j += 1
            out.append(pattern[i:j])
            i = j
            continue
        if c in multi:
            out.append('(?:' + '|'.join(multi[c]) + ')')
        elif c in single:
            out.append('[' + single[c] + ']')
        else:
            out.append(c)
        i += 1
    return ''.join(out)


def loose(pattern):
    """Croatian/Serbian Latin: diacritics optional (č→[čćc], đ→đ|dj|d …)."""
    return _walk(pattern, _LATIN_LOOSE, {'đ': ['đ', 'dj', 'd']})


_CYR = {
    'a': 'а', 'b': 'б', 'v': 'в', 'g': 'г', 'd': 'д', 'đ': 'ђ', 'e': 'е', 'ž': 'ж', 'z': 'з', 'i': 'и',
    'j': 'ј', 'k': 'к', 'l': 'л', 'm': 'м', 'n': 'н', 'o': 'о', 'p': 'п', 'r': 'р', 's': 'с', 't': 'т',
    'ć': 'ћ', 'u': 'у', 'f': 'ф', 'h': 'х', 'c': 'ц', 'č': 'ч', 'š': 'ш',
}
_DIGRAPHS = {'lj': 'љ', 'nj': 'њ', 'dž': 'џ'}


def to_cyrillic(pattern):
    """Serbian Latin regex → the same regex in Serbian Cyrillic."""
    out, i, in_class = [], 0, False
    while i < len(pattern):
        c = pattern[i]
        if c == '\\' and i + 1 < len(pattern):
            out.append(pattern[i:i + 2])
            i += 2
            continue
        if c == '[':
            in_class = True
        elif c == ']':
            in_class = False
        if c == '(' and pattern[i + 1:i + 2] == '?':
            j = i + 2
            while j < len(pattern) and pattern[j] in ':=!<':
                j += 1
            out.append(pattern[i:j])
            i = j
            continue
        two = pattern[i:i + 2]
        if not in_class and two in _DIGRAPHS:
            out.append(_DIGRAPHS[two])
            i += 2
            continue
        out.append(_CYR.get(c, c))
        i += 1
    return ''.join(out)


# ── States ──────────────────────────────────────────────────────────────

FROZEN = re.compile(loose(r'smrznut|zamrznut|duboko smrz|\bledo\b|frikom|\bsmrz|hortex|\bfrizo\b|frozy|garden good|bakina kuhinja'), re.I)
CANNED = re.compile(loose(r'konzerv|limenk|\bstaklenk|u salamuri|ukiseljen|pasteriziran'), re.I)


def detect_state(raw_name):
    n = raw_name.lower()
    if FROZEN.search(n):
        return 'frozen'
    if CANNED.search(n):
        return 'canned'
    return 'fresh'


# Words a shelf name may start with that are not the product. Compared with
# accents stripped (the matcher folds them first).
LEADING = [
    'bio', 'eko', 'ekoloski', 'ekoloska', 'ekolosko', 'organski', 'organska', 'domaci', 'domaca', 'domace',
    'svjezi', 'svjeza', 'svjeze', 'mladi', 'mlada', 'mlado', 'hrvatski', 'hrvatska', 'hrvatsko', 'baby', 'mini',
    'zeleni', 'zelena', 'zuti', 'zuta', 'crveni', 'crvena', 'bijeli', 'bijela', 'k', 'classic', 's', 'budget',
    'spar', 'konzum', 'plodine', 'kaufland', 'lidl', 'premium', 'extra', 'ekstra', 'fresh', 'nas', 'nase',
    'pak', 'kg', 'rinfuza', 'rfz', 'rfs', 'vl', 'slavonski', 'slavonska', 'istarski', 'istarska', 'dalmatinski',
]


# ── What is not a fresh product ─────────────────────────────────────────
#
# Patterns, loosened like the rules. Shelf names abbreviate freely ("RAJČICA
# PASIR", "SIR NAM", "LIM." for a tin), so several are prefixes.

_REJECT = [
    # drinks, sweets, spreads, sauces
    r'\bsok\b|sokovi|u soku|\bnektar|\bne ktar|napitak|\bpi[ćc]e\b|smoothie|shake|limunad|sirup|\bčaj\b|kava|kakao|'
    r'čokolad|\bčok\b|keks|kolač|torta|sladoled|bombon|žvak|napolitank|puding|džem|marmelad|pekmez|kompot|namaz|'
    r'\bnam\b|umak|kečap|ajvar|majonez|senf|\bkrem\b|krema\b|\bpire\b|juha|\bjuhe\b|temeljac|instant|krokant|'
    r'pločic|kiflic|smokvenjak|bananko|bananic|breskvic|\bvoda\b|cedevit|\bjana\b|fuze|\btea\b|dressing|šećer|'
    r'glazur|orahnja|klipi[ćc]|passata|kolutic|spray|bbq|nadjev|cannellon|voćn|tijest|tanjur|maslac od|tijel|'
    r'pjen|panad|kroasan|croissant|ogulj|\bpulp|\bbib\b|stočn|nivea|afrodit|'
    r'za lice|tamnjenj|\bbody\b|\bspa\b|\bkids\b|polpa|\bkorn\b|\bdel\b|pancet|skutom',
    # tins, jars, pickles, dried, preserved, cut
    r'pelat|pasir|sjeck|\bsjec\b|siječen|briket|\bsj\b|\bfil\b|\bpeč\b|\bdim\b|slan[ia]?\b|\bneto\b|\bkonc|konzerv|\blim\b|limenk|stakl|\bst\b|naljev|ukiseljen|kisel[ai]\b|\bkis\b|turšij|'
    r'salamur|marinad|sušen|\bsuh[aeio]\b|\bsuho\b|kandiran|u prahu|\bprah\b|dehidrir|liofiliz|\bpečen[aeio]?\b|'
    r'\bkuhan[aeio]?\b|blanširan|na pari|grill|roštilj|gotov|pohan|panir|dimljen|marinir|\bmar\b|začinjen|punjen|'
    r'filovan|zapečen|pržen|\brezan[aio]?\b|\brez\b|kriškam|kriške|narez|\bnar\b\s*\d|trakic|ribani|\bulj[eu]\b|'
    r'golic|sjemenk|\bsjem',
    # meat products
    r'salam|kobasic|hrenovk|šunk|pršut|slanin|kulen|pašte|narezak|čvarc|ćevap|pljeskavic|burger|nugget|gyros|'
    r'kebab|ražnji|mesni doručak|čajna|mortadel|špek|carsko|buđola|krvavic|polpet|okruglic|ovitk|filetino|'
    r'rillette|guanciale|gavrilovi[ćc]|\blino\b|\btun[ae]?\b|losos|\briba\b|bakalar|osli[ćc]|lignj|kozic|škamp',
    # flour, bakery, pasta, ready meals
    r'tjestenin|njoki|rezanci|pizza|burek|\bpita\b|štrudl|\bkruh|pecivo|tortilj|kroket|pomfrit|\bčips|chips|flips|'
    r'štapić|grickalic|kreker|krumpir salat|krumpiri[ćc]|salata (od|sa|s)\b|lazanj|musaka|sarma|varivo|rižot|'
    r'\bmix\b|mješavina|brašn|griz|zobene|musli|müsli|cerealij|pahuljic|\bpasta\b|tortel|raviol|sushi|gratin|'
    r'combo|\bs[a]? (krumpir|orz|riž|tjesten|mesom|šunk|sirom|vrhnj|graš|mrkv|luk|grožđ)|\borzo',
    # dairy that is not plain
    r'okus|aroma|vanilij|bez laktoze|laktoz|proteinsk|\bprot\b|\bprotein\b|čokoladno|topljen|margarin|biljn|'
    r'kikirik|kinder|\bdesert|zabijelj|u spreju|\bprip\b|kondenzir|za kavu|cappuccino|latte|shea|kakao maslac',
    # pets, household, cosmetics, decorations
    r'\bza pse\b|za mačke|\bpas\b|mačk|whiskas|pedigree|friskies|felix|purina|gourmet|adventuros|training|'
    r'hrana za|hrana sp|granule|poslastic|šampon|gel za|sapun|deterdžent|omekšivač|krema za|losion|mlijeko za|'
    r'dezodor|\bdeo\b|parfem|svijeć|osvježivač|toaletn|čišćenj|\bjar\b|pasta za zube|\bbalzam|kozmetik|\bmaska\b|'
    r'\bruž za|lak za|dezinf|prašak|tablete|kapsul|sredstvo|maramic|sprej|spužvic|melem|pavlović|uskr|dekor|'
    r'ukras|rezač|naljepnic|sličic|vafl|magičn|za jaja|u boji|gnijezd|gnjezd|\bset\b|\bigr\b|plisan|igračk|keramič|keramik|\bdoza\b|oral-b|konac|'
    r'\bposud[ae]\b|zdjel',
    # alcohol, clearance prices, seeds and plants
    r'liker|rakij|\bvino\b|\bpivo\b|\bgin\b|votk|vodka|whisk|\brum\b|šljivovic|kruškovac|travaric|orahovac|'
    r'višnjevac|medica|pelinkovac|sniž|\bsjeme\b|sadnic|lukovic|presadnic|\bcvijet|\bbiljka\b',
    # spice and preserve brands: a fresh product is not sold under them
    r'kotany|vegeta|maestro|podravk|zorela|doora|giana|\beva\b|franck|bonduelle|cirio|mutti|nadalin|šafram|'
    r'aleva|derma|italpepe|\bultra\b|bočic|\bboč\b|vrećic|\bvreć\b|mlinac|\bzrn|začin|usitnjen|\busit\b|listići|'
    r'(paprik|papar|čili|chili)\w*.*mlje|\bmlj\b|delikates|\bdelik\b|ponti|\bneri\b|zvijezda|vitaminka|bonvita|natureta|'
    r'mikado|o.plant',
]
REJECT = [re.compile(loose(p), re.I) for p in _REJECT]


# ── Rules: (pattern, rule name). First match wins. ─────────────────────
#
# Fruit and vegetables must be named first (the matcher checks), so their
# patterns can be short. Dairy, eggs and meat are not checked that way, so
# cheeses and milks are anchored here to the first words of the name:
# "SALATA MOZZARELLA MINUTE" is a salad.

CH = r'^(\S+\s+){0,2}'      # the product within the first three words
HERB = r'^(svjež\w*\s+)?'   # a herb named first, as fresh herbs are

BEEF = r'(junet|govedin|gove[đd]|june[ćc]|\bjun\b)'

_RULES = [
    # ---- EGGS ----
    (r'prepeli[čc]\w* jaj|jaj\w* prepel', 'Quail Eggs'),
    (r'pa[čc]j\w* jaj|jaj\w* pa[čc]j', 'Duck Eggs'),
    (r'\bjaja\b.*(\beko\b|\bbio\b|ekolo|organsk)|(\beko\b|\bbio\b|ekolo|organsk).*\bjaja\b', 'Organic eggs (hr)'),
    (r'\bjaja\b', 'Eggs'),

    # ---- POULTRY (turkey first: "PUREĆI FILE ZABATAK") ----
    (r'pure[ćc]\w*\s+(prsa|file|prsni)', 'Turkey Breast'),
    (r'pure[ćc]\w*\s+(\w+\s+)?(batak|zabat)', 'Turkey Legs'),
    (r'pure[ćc]\w*\s+krila', 'Turkey Wings'),
    (r'pile[ćc].*zabat|zabat.*pile[ćc]|^(\S+\s+)?(file\s+)?zabat', 'Chicken Thigh'),
    (r'pile[ćc]\w*\s+(prsa|file|fileti|prsni)|prsa\s+pile|file\s+pile', 'Chicken Breast'),
    (r'pile[ćc]\w*\s+(\w+\s+)?batak|batak\w*\s+pile', 'Chicken Drumsticks'),
    (r'pile[ćc]\w*\s+(krila|krilca)|krilc\w*\s+pile|pile\W+krilc', 'Chicken Wings'),
    (r'pile[ćc]\w*\s+(jetr|jetric)', 'Chicken Liver'),
    (r'pile[ćc]\w*\s+(želu)', 'Chicken Gizzard'),
    (r'pile[ćc]\w*\s+(noge|nogice|šapic)', 'Chicken Feet'),
    (r'pile[ćc]\w*\s+vrat', 'Chicken Neck'),
    (r'^(\w+\s+)?pile\b|piletina cijel|cijelo pile', 'Whole Chicken'),
    (r'(pa[čc]j|patk)\w*\s+prsa|file pa[čc]j', 'Duck Breast'),
    (r'(pa[čc]j|patk)\w*\s+(batak|but)', 'Duck Leg'),
    (r'^(\S+\s+)?(guska|gu[šs][čc]\w*\s+(meso|but|prsa))', 'Goose Meat'),
    (r'^(\S+\s+)?prepelic', 'Quail Meat'),
    (r'^(\S+\s+)?biserk', 'Guinea Fowl Meat'),
    (r'piletin|pile[ćc]|puretin|pure[ćc]|patk|zabatak', 'Poultry other (hr)'),

    # ---- MEAT ----
    (r'mljeven\w*\s+(\w+\s+)?' + BEEF + r'|' + BEEF + r'\w*\s+mljeven', 'Ground Beef'),
    (r'mljeven\w*\s+(\w+\s+)?svinj|svinj\w*\s+mljeven', 'Ground Pork'),
    (r'mljeven', 'Mixed minced meat (hr)'),
    (r'telet|tele[ćc]|\btel\b', 'Veal (hr)'),
    (r'biftek', 'Fresh Tenderloin'),
    (r'rozbratn|entrecote|antrikot|rib ?eye', 'Fresh Ribeye'),
    (r'ramstek|\brump', 'Fresh Sirloin'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?(rebra|rebarc)', 'Beef Ribs'),
    (BEEF + r'\w*\.?\s+jetr', 'Beef Liver'),
    (BEEF + r'\w*\.?\s+jezik', 'Beef Tongue'),
    (BEEF + r'\w*\.?\s+obraz', 'Beef Cheek'),
    (BEEF + r'\w*\.?\s+rep\b', 'Beef Tail'),
    (BEEF + r'\w*\.?\s+(koljenic|buncek)', 'Beef Shank'),
    (BEEF + r'\w*\.?\s+(prsa|prsni)', 'Beef Brisket'),
    (BEEF + r'\w*\.?\s+potrbu', 'Beef flank (hr)'),
    (r'tripic|fileki', 'Beef Tripe'),
    (BEEF + r'\w*\.?\s+(\w+\s+)?(odrez|steak|šnicl)|odrez\w*\s+june', 'Beef Steak'),
    (BEEF, 'Beef other (hr)'),
    (r'svinj\w*\s+(\w+\s+)?(kotlet|krmenadl)|krmenadl|kotlet\w*\s+svinj', 'Pork Chops'),
    (r'svinj\w*\s+(\w+\s+)?(rebra|rebarc)|rebarc\w*\s+svinj', 'Pork Ribs'),
    (r'svinj\w*\s+(trbuh|potrbu)|^(\S+\s+)?potrbušin|svježa panceta', 'Pork Belly'),
    (r'svinj\w*\s+(ple[ćc]k|lopatic)|ple[ćc]k\w*\s+svinj', 'Pork Shoulder'),
    (r'svinj\w*\s+but\b|but\s+svinj', 'Pork Ham'),
    (r'svinj\w*\s+obraz', 'Pork Jowl'),
    (r'svinj\w*\s+(koža|kožic)', 'Pork Skin'),
    (r'svinj\w*\s+bubre', 'Pork Kidney'),
    (r'svinj\w*\s+mast|mast\s+svinj|^mast\b', 'Lard'),
    (r'svinj', 'Pork other (hr)'),
    (r'janj\w*\s+(\w+\s+)?kotlet', 'Lamb Chops'),
    (r'janj\w*\s+(\w+\s+)?but\b', 'Lamb Leg'),
    (r'janj\w*\s+(ple[ćc]k|lopatic)', 'Lamb Shoulder'),
    (r'janj\w*\s+vrat', 'Lamb Neck'),
    (r'janj\w*\s+(rebr|kare)', 'Lamb Rib Rack'),
    (r'janj', 'Lamb other (hr)'),
    (r'kozlet|jaretin', 'Goat Meat'),
    (r'zečetin|^(\S+\s+)?kuni[ćc]\b', 'Rabbit Meat'),
    (r'^(\S+\s+)?(srnetin|jelenj\w* meso|jelenetin)', 'Venison'),
    (r'^(\S+\s+)?(veprovin|divlj\w* svinj)', 'Wild Boar'),

    # ---- DAIRY: milk named in the first two words ----
    (r'^(\S+\s+)?(kozj\w*\s+mlijek|mlijek\w*\s+kozj)', 'Goat Milk'),
    (r'^(\S+\s+)?(ov[čc]j\w*\s+mlijek|mlijek\w*\s+ov[čc]j)', 'Sheep Milk'),
    (r'^(\S+\s+)?(mlaćenic|stepk)', 'Buttermilk'),
    (r'^(\S+\s+)?(kiselo mlijek|kefir|acidofil)', 'Fermented Milk'),
    (r'^(\S+\s+)?mlijek[oa]\b.*(3[.,][2-9]|4[.,]\d|punomasn)', 'Whole Milk'),
    (r'^(\S+\s+)?mlijek[oa]\b.*(0[.,][0-5]\s*%|obran)', 'Skim Milk'),
    (r'mlijek[oa]\b', 'Milk other fat (hr)'),
    # yoghurt: plain only; a flavoured one is its own (unlisted) thing
    (r'(jogurt|skyr|kefir).*(jagod|breskv|vanil|borovnic|šumsk|banan|marelic|višnj|ananas|kokos|žitar|voć|kurkum|panna|'
     r'stracciatel|limun|mang|malin|kupin|trešnj|ribiz|grožđ|krušk|jabuk|\bmed\b|lješnj|kesten|smokv|\bzob|'
     r'aloe|pistac|tiramisu|cimet|karamel|\bjag\b|\bvan\b|bobbas|jogobella|pineapple|coconut|strawber|\bkru\b|'
     r'\bban\b|\bki\b)', 'Flavoured yogurt (hr)'),
    (CH + r'(grčk\w*\s+jogurt|jogurt\w*\s+grčk|jogurt grčki tip)', 'Greek Yogurt'),
    (CH + r'(ov[čc]j\w*\s+jogurt|jogurt\w*\s+ov[čc]j)', 'Sheep Yogurt'),
    (CH + r'skyr', 'Skyr'),
    (CH + r'(tekuć\w*\s+)?jogurt', 'Yogurt'),
    (r'jogurt', 'Yogurt other (hr)'),
    (r'^(\S+\s+)?(kiselo vrhnj|vrhnje kiselo)', 'Sour cream (hr)'),
    (r'^(\S+\s+)?(slatko\s+)?vrhnj|^šlag\b', 'Cream'),
    (r'maslac.*\d\s*ml\b|tekuć\w* maslac', 'Not butter (hr)'),
    (r'^(\S+\s+)?maslac|^puter\b', 'Butter'),
    # cheeses
    (CH + r'(svjež\w*\s+sir|sir\w*\s+svjež|\bskuta|cottage)', 'Fresh Cottage Cheese'),
    (CH + r'(krem sir|sir za mazanje|cream cheese|philadelphia)', 'Cream Cheese'),
    (CH + r'(sir\s+)?(mozzarel|mocarel)', 'Mozzarella'),
    (CH + r'(sir\s+)?feta\b', 'Feta Cheese'),
    (CH + r'(sir\s+)?gouda', 'Gouda Cheese'),
    (CH + r'(sir\s+)?(polutv\w*\s+)?edam', 'Edam Cheese'),
    (CH + r'(sir\s+)?(emmental|ementaler|ementhal)', 'Swiss Cheese'),
    (CH + r'(sir\s+)?(tvrdi\s+)?(parmez|parmigian|grana padano)', 'Parmesan'),
    (CH + r'(sir\s+)?mascarpone', 'Mascarpone'),
    (CH + r'(sir\s+)?(ricotta|rikota)', 'Ricotta'),
    (CH + r'(sir\s+)?cheddar', 'Cheddar Cheese'),
    (CH + r'(sir\s+)?(gorgonzol|roquefort)', 'Blue Cheese'),
    (CH + r'(sir\s+)?provolone', 'Provolone'),
    (CH + r'(kozj\w*\s+sir|sir\w*\s+(sv\s+)?kozj)', 'Goat Cheese'),
    (CH + r'(ov[čc]j\w*\s+sir|sir\w*\s+ov[čc]j|(sir\s+)?paški sir|sir paški)', 'Sheep Cheese'),
    (CH + r'(sir\s+)?(trapist|polutvrd|tvrd\w*\s+sir|sir\s+tvrd)', 'Cheese'),
    (r'\bsir\b|\bsira\b', 'Cheese other (hr)'),

    # ---- VEGETABLES ----
    (r'rajčic\w*\s+.*(cherry|čeri|mini|koktel|datterin|daterin|cocktail|ternetto|papelett|campari|bumblebee|harmony)'
     r'|cherry rajčic|čeri rajčic', 'Cherry Tomato'),
    (r'rajčic\w*\s+.*kumato', 'Black Tomatoes'),
    (r'rajčic\w*\s+.*(grappolo|grapolo|grozd|na grani|grančic|vine)', 'Vine Tomatoes'),
    (r'rajčic\w*\s+.*(šljivar|šljiva|\broma\b|san marzano)', 'Plum Tomatoes'),
    (r'rajčic\w*\s+.*(beef|volovsk)', 'Beefsteak Tomatoes'),
    (r'rajčic|paradajz', 'Tomato'),
    (r'kornišon', 'Pickling Cucumbers'),
    (r'krastav\w*\s+.*\d\s*ml\b', 'Pickles (hr)'),
    (r'krastav', 'Cucumber'),
    (r'feferon', 'Pickled peppers (hr)'),
    (r'paprik\w*\s+.*(ljut|čili|chili)|ljut\w*\s+paprik|čili papri|^chili\b', 'Chili Pepper'),
    (r'jalape', 'Jalapeño'),
    (r'paprik|babur', 'Bell Pepper'),
    (r'tikvic', 'Zucchini'),
    (r'butternut|tikva puter|puter tikv', 'Butternut Squash'),
    (r'bundev|buča|\btikva|hokaido|hokkaido', 'Pumpkin'),
    (r'mrkv', 'Carrot'),
    (r'batat|slatk\w*\s+krumpir|krumpir\w*\s+(\(?slatk|batat)', 'Sweet Potato'),
    (r'krumpir', 'Potato'),
    (r'poriluk|\bpor\b', 'Leek'),
    (r'bijel\w*\s+luk|luk\s+bijel|češnjak', 'Garlic'),
    (r'mlad\w*\s+luk|luk\s+mlad|luk\s+vlasac', 'Spring Onions'),
    (r'crven\w*\s+luk|luk\s+crven|ljubičast\w*\s+luk|luk\s+ljubi', 'Red Onion'),
    (r'luk\s+srebren|srebrenac', 'Pearl Onions'),
    (r'ljutik|šalot', 'Shallots'),
    (r'\bluk\b', 'Onion'),
    (r'brokul|brokol', 'Broccoli'),
    (r'cvjeta[čc]|karfiol', 'Cauliflower'),
    (r'romanesc', 'Romanesco'),
    (r'kelj pup|prokulic', 'Brussels Sprouts'),
    (r'\bkale\b|kovrčav\w*\s+kelj', 'Kale'),
    (r'raštik', 'Collard Greens'),
    (r'\bkelj', 'Savoy Cabbage'),
    (r'kinesk\w*\s+kupus|pekinšk\w*\s+kupus', 'Napa Cabbage'),
    (r'crven\w*\s+kupus|kupus\s+crven|ljubičast\w*\s+kupus|kupus\s+ljubi', 'Red Cabbage'),
    (r'kupus', 'Cabbage (hr)'),
    (r'pak cho|bok cho', 'Bok Choy'),
    (r'špinat', 'Spinach'),
    (r'blitv', 'Swiss Chard'),
    (r'rikol|rukol', 'Arugula'),
    (r'potočark', 'Watercress'),
    (r'endivij', 'Endive'),
    (r'radi[čc]\b|radicchio|radiči', 'Radicchio'),
    (r'rimsk\w*\s+salat|salat\w*\s+romana|romaine|^romana\b(?! nares)', 'Romaine Lettuce'),
    (r'hrastov', 'Oak Leaf Lettuce'),
    (r'frize|frisee|frisée', 'Frisée Lettuce'),
    (r'matovilac|salat|lollo|kristalk|puteric', 'Lettuce (hr)'),
    (r'cikl(?!on)', 'Beetroot'),
    (r'celer\w*\s+.*(stablj|rebr|list)', 'Celery'),
    (r'celer', 'Celeriac'),
    (r'rotkvic', 'Radish'),
    (r'rotkv', 'Black or white radish (hr)'),
    (r'komorač|koromač', 'Fennel'),
    (r'artičok', 'Artichoke'),
    (r'patlidžan', 'Eggplant'),
    (r'bamij|\bokra\b', 'Okra'),
    (r'pastrnjak|pastrnak', 'Parsnip'),
    (r'korabic|korab', 'Kohlrabi'),
    (r'^(\S+\s+)?(repa|bijel\w* rep[ae])\b', 'Turnip'),
    (r'kukuruz\w*\s+.*klip|klip\w*\s+kukuruz', 'Sweet Corn'),
    (r'kukuruz', 'Corn kernels (hr)'),
    (r'mahun(?!ark)', 'Green Beans'),
    (r'grašak', 'Peas (hr)'),
    (r'\bbob\b', 'Fava Beans'),
    (r'šparog\w*\s+.*bijel|bijel\w*\s+šparog', 'White Asparagus'),
    (r'šparog\w*\s+.*zelen|zelen\w*\s+šparog', 'Green Asparagus'),
    (r'šparog', 'Asparagus'),
    (r'đumbir', 'Fresh Ginger'),
    (r'kurkum\w*\s+(svjež|korijen)', 'Fresh Turmeric'),
    (r'kurkum', 'Turmeric spice (hr)'),
    (r'\bhren\b\s+(korijen|svjež)', 'Fresh Horseradish Root'),
    (r'\bhren\b', 'Horseradish preserve (hr)'),
    (r'čičok', 'Jerusalem Artichoke'),
    (r'bukovač', 'Oyster Mushroom'),
    (r'shiitake|šitake', 'Shiitake Mushroom'),
    (r'portobel|portabel', 'Portobello Mushroom'),
    (r'enoki', 'Enoki Mushroom'),
    (r'vrganj|lisičark|smeđ\w*\s+šampinj|šampinjon\w*\s+smeđ', 'Other mushrooms (hr)'),
    (r'šampinjon|gljiv', 'White Mushroom'),

    # ---- FRESH HERBS: named first (a jar of dried basil is "ZAČIN BOSILJAK") ----
    (HERB + r'peršin\w*\s+korij', 'Parsley root (hr)'),
    (HERB + r'peršin', 'Parsley'),
    (HERB + r'kopar', 'Dill'),
    (HERB + r'bosiljak', 'Genovese Basil'),
    (HERB + r'vlasac', 'Chives'),
    (HERB + r'(metvic|menta\b)', 'Mint'),
    (HERB + r'ružmarin', 'Rosemary'),
    (HERB + r'(timijan|majčina dušic)', 'Thyme'),
    (HERB + r'kadulj', 'Sage'),
    (HERB + r'korijand', 'Cilantro'),
    (HERB + r'limun\w* trav', 'Lemongrass'),

    # ---- FRUIT ----
    (r'jabuk\w*\s+.*pink lady|pink lady', 'Pink Lady Apples'),
    (r'jabuk\w*\s+.*honeycrisp', 'Honeycrisp Apples'),
    (r'jabuk\w*\s+.*ambrosia', 'Ambrosia Apples'),
    (r'jabuk', 'Apples'),
    (r'krušk', 'Pears'),
    (r'nektarin', 'Nectarine (hr)'),
    (r'breskv', 'Peaches'),
    (r'šljiv\w*\s+.*(b\.k|koštic|natura)', 'Prunes (hr)'),
    (r'šljiv', 'Plums'),
    (r'crven\w*\s+naranč|naranč\w*\s+crven|krvav\w*\s+naranč|naranč\w*\s+(moro|tarocco|krvav)', 'Blood Oranges'),
    (r'naranč|naranđ', 'Oranges'),
    (r'limet|\blime\b|lajm', 'Lime'),
    (r'limun(?!sk)', 'Lemons'),
    (r'grejp', 'Grapefruit (hr)'),
    (r'mandarin', 'Mandarin Oranges Fresh'),
    (r'klementin', 'Clementine'),
    (r'avokad|avocad', 'Avocado'),
    (r'lubenic', 'Watermelon'),
    (r'dinj', 'Melon'),
    (r'malin', 'Raspberry'),
    (r'jagod', 'Strawberries'),
    (r'borovnic', 'Blueberries'),
    (r'kupin', 'Blackberries'),
    (r'grožđ\w*\s+.*(bijel|zelen|žut)|(bijel|zelen)\w*\s+grožđ', 'Grapes Green'),
    (r'grožđ\w*\s+.*(crn|crven|plav)|(crn|crven)\w*\s+grožđ', 'Grapes Red'),
    (r'grožđ', 'Grapes (hr)'),
    (r'banan(?!ic|ko)', 'Banana'),
    (r'ananas', 'Pineapple'),
    (r'\bmang[oa]\b', 'Mango'),
    (r'papaj', 'Papaya'),
    (r'marakuj|passion', 'Passion Fruit'),
    (r'\bkiwi|\bkivi', 'Kiwi'),
    (r'smokv', 'Fig'),
    (r'\bnar\b|\bnarovi\b|šipak', 'Pomegranate'),
    (r'\bliči\b|lychee', 'Lychee'),
    (r'kokos\w*\s+orah|^kokos\s+(kom|svjež)', 'Coconut'),
    (r'kokos', 'Coconut products (hr)'),
    (r'\bkaki\b|japansk\w* jabuk', 'Persimmon'),
    (r'trešnj', 'Cherries'),
    (r'višnj', 'Sour cherry (hr)'),
    (r'marelic', 'Apricot (hr)'),
    (r'dunj', 'Quince (hr)'),
    (r'crven\w*\s+ribiz|ribiz\w*\s+crven', 'Red Currant'),
    (r'crn\w*\s+ribiz|ribiz\w*\s+crn', 'Black Currant'),
    (r'ogrozd', 'Gooseberry'),
    (r'pitaj|zmajev', 'Dragon Fruit'),
    (r'kesten', 'Chestnuts'),
    (r'lješnj', 'Hazelnuts'),
    (r'orah\w*\s+brazil|brazilsk\w*\s+orah', 'Brazil Nuts'),
    (r'\borah|\borasi\b|jezgr\w* oraha', 'Walnuts'),
    (r'badem', 'Almonds'),
]

RULES = [(loose(p), n, None, None) for p, n in _RULES]

# Rule names the catalogue has no product for: matched, so nothing looser
# takes them, and counted as products worth adding.
TARGETS = {n: None for _, n in _RULES if n.endswith('(hr)')}
