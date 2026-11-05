"""
Greek shelf names → catalogue products.

The names come from the Greek government's price observatory, PosoKanei
(feeds/posokanei_gr.py): "Φρέσκο Γάλα Πλήρες 3.5% 1lt", "Αυγά Αχυρώνα
Large 6 Τεμάχια", "Φιλέτο Στήθος Κοτόπουλου Ελληνικό 700g". The feed takes
the brand off the front of the name, since the product follows it.

Greek is written with and without accents (uppercase names drop them), and
a final sigma is ς in one spelling and σ in another, so every pattern is
loosened: α also matches ά, σ matches ς, and so on (see loose()).

Rule names ending "(el)" are products the catalogue does not have.
"""

import re

from pipeline.rules_hr import _walk

LANG = 'el'

_GREEK_LOOSE = {
    'α': 'αά', 'ε': 'εέ', 'η': 'ηή', 'ι': 'ιίϊΐ', 'ο': 'οό', 'υ': 'υύϋΰ', 'ω': 'ωώ', 'σ': 'σς', 'ς': 'σς',
}


def loose(pattern):
    """Accents and final sigma optional."""
    return _walk(pattern, _GREEK_LOOSE)


FROZEN = re.compile(loose(r'κατεψυγμ|frozen|\bκτψ\b'), re.I)
CANNED = re.compile(loose(r'κονσερβ|σε αλμη|σε λαδι|τουρσι'), re.I)


def detect_state(raw_name):
    n = raw_name.lower()
    if FROZEN.search(n):
        return 'frozen'
    if CANNED.search(n):
        return 'canned'
    return 'fresh'


# Compared with accents stripped (the matcher folds first).
LEADING = [
    'φρεσκο', 'φρεσκα', 'φρεσκος', 'φρεσκια', 'νωπο', 'νωπα', 'νωπος', 'βιο', 'βιολογικο', 'βιολογικα',
    'βιολογικη', 'ελληνικο', 'ελληνικα', 'ελληνικη', 'ελληνικες', 'εισαγωγης', 'αβ', 'my', 'fresco', 'επιλογη',
    'baby', 'mini', 'λευκα', 'λευκο', 'bio', 'organic', 'συσκευασμενα', 'συσκευασμενο',
]

_REJECT = [
    # not plain: flavoured, sweet, drinks, spreads
    r'σοκολατ|καφε|κακαο|εβαπορε|συμπυκν|σκονη|βρεφ|παιδικ|γευση|γευσεις|χωρις λακτοζη|lactose|lacto free|'
    r'φυτικ|αμυγδαλ|σογια|βρωμη|ρυζιου|protein|πρωτεϊν|επιδορπ|ροφημα|τζατζικ|αλειμμα|αλοιφωμεν|μαργαριν|'
    r'σαντιγ|σπρει|ζαχαροπλαστ|smoothie|ice\b|πασχαλ|kinder|τυροπιτ|\bπιτα\b|τυρακια|τριμμεν|\bσε φετες\b|\bφετες\b|'
    r'κουβερτουρ|vegetop|\bsoft\b|αλειφωτ|στικ|tριμμ|\bstick',
    # meat that is not plain
    r'μπουκιε|nugget|σνιτσελ|\bπανε\b|παναρισμ|cordon|μπιφτεκ|σουβλακ|γυρο|λουκανικ|μαριναρισμ|ψητ|καπνιστ|'
    r'αλλαντ|μπεικον|ζαμπον|γεμιστ|κεφτεδ|burger|μπεργκερ|καλαμακ|crispy|τραγαν|\bρολο|μπαρμπεκιου|bbq|πικαντικ|'
    r'μπριζολακ|κεμπαπ|κοτομπουκ',
    # vegetables that are not fresh
    r'ατμο|βραστ|μαγειρ|τουρσι|σαλτσ|πουρε|σε αλμη|λιαστ|ξερ[αοε]\b|αποξηραμ|τηγαν|chips|τσιπς|σουπα',
]
REJECT = [re.compile(loose(p), re.I) for p in _REJECT]

_RULES = [
    # ---- EGGS ----
    (r'ορτυκ', 'Quail Eggs'),
    (r'βιολογικ\w*\s+(\w+\s+)?αυγ|αυγ\w*\s+(\w+\s+)?βιολογικ|\bbio\b.*αυγ|αυγ.*\bbio\b', 'Organic eggs (el)'),
    (r'αυγ[αοη]', 'Eggs'),

    # ---- flavoured yoghurt and kefir: not the plain product ----
    (r'(γιαουρτ|skyr|κεφιρ).*(μελι\b|βανιλ|φραουλ|ροδακιν|μπανανα|δημητριακ|κερασ|βυσσιν|μυρτιλ|μανγκο|'
     r'γρανολ|cereal|φρουτ|καρυδ|βερικοκ|ανανα|σοκολατ|καραμελ)', 'Flavoured yogurt (el)'),
    # ---- MILK ----
    (r'κεφιρ|ξινογαλ|αριαν|αϊραν', 'Fermented Milk'),
    (r'(κατσικισ\w*|γιδιν\w*)\s+(\w+\s+)?γαλα|γαλα\s+(\w+\s+)?(κατσικισ|γιδιν)', 'Goat Milk'),
    (r'προβει\w*\s+(\w+\s+)?γαλα|γαλα\s+(\w+\s+)?προβει', 'Sheep Milk'),
    (r'κρεμα\s+γαλακτ', 'Cream'),
    (r'\bγαλα\b.*(αποβουτυρ|\b0[.,]?[0-5]?\s*%)', 'Skim Milk'),
    (r'\bγαλα\b.*(πληρες|3[.,][2-9]|4[.,]\d)', 'Whole Milk'),
    (r'\bγαλα\b', 'Milk other fat (el)'),

    (r'προβει\w*\s+(\w+\s+)?γιαουρτ|γιαουρτ\w*\s+(\w+\s+)?προβει', 'Sheep Yogurt'),
    (r'στραγγιστ|ελληνικ\w*\s+γιαουρτ|greek yog', 'Greek Yogurt'),
    (r'skyr', 'Skyr'),
    (r'γιαουρτ', 'Yogurt'),

    # ---- BUTTER ----
    (r'βουτυρ', 'Butter'),

    # ---- CHEESE ----
    (r'\bφετα\b|\bfeta\b', 'Feta Cheese'),
    (r'(κατσικισ\w*|γιδιν\w*)\s+τυρ', 'Goat Cheese'),
    (r'mozzarel|μοτσαρελ', 'Mozzarella'),
    (r'ricotta|ρικοτα', 'Ricotta'),
    (r'cottage|κοταζ|κοτατζ', 'Fresh Cottage Cheese'),
    (r'κρεμα\s+τυρ|τυρι\s+κρεμα|cream cheese|philadelphia', 'Cream Cheese'),
    (r'gouda|γκουντα', 'Gouda Cheese'),
    (r'\bedam|ενταμ', 'Edam Cheese'),
    (r'emmental|εμενταλ', 'Swiss Cheese'),
    (r'cheddar|τσενταρ', 'Cheddar Cheese'),
    (r'parmigiano|παρμεζαν|παρμιτζ|grana padano', 'Parmesan'),
    (r'mascarpone|μασκαρπον', 'Mascarpone'),
    (r'gorgonzola|γκοργκοντζολ|roquefort|ροκφορ', 'Blue Cheese'),
    (r'provolone|προβολον', 'Provolone'),
    (r'γραβιερ|κεφαλογραβ|κασερι|κεφαλοτυρ|λαδοτυρ|μετσοβον|σαν μιχαλη', 'Cheese'),
    (r'λευκο τυρι|τελεμε|μανουρι|μυζηθρ|ανθοτυρ|κοπανιστ|τυρι', 'Other Greek cheese (el)'),

    # ---- POULTRY ----
    (r'γαλοπουλ\w*\s+(\w+\s+)?στηθ|στηθ\w*\s+(\w+\s+)?γαλοπουλ', 'Turkey Breast'),
    (r'γαλοπουλ', 'Turkey other (el)'),
    (r'στηθ', 'Chicken Breast'),
    (r'κοπαν', 'Chicken Drumsticks'),
    (r'μπουτ|\bμηρ(ος|ου|ο|οι)\b', 'Chicken Thigh'),
    (r'φτερουγ', 'Chicken Wings'),
    (r'συκωτ', 'Chicken Liver'),
    (r'στομαχ', 'Chicken Gizzard'),
    (r'κοτοπουλ\w*\s+(\w+\s+)?ολοκληρ|ολοκληρ\w*\s+κοτοπουλ|^κοτοπουλ\w*(\s+(νωπ|ελληνικ|φρεσκ)\w*)*(\s+\d|$)', 'Whole Chicken'),
    (r'κοτοπουλ|κοτα\b', 'Chicken other (el)'),

    # ---- VEGETABLES ----
    (r'πλευρωτ', 'Oyster Mushroom'),
    (r'portobel|πορτομπελ', 'Portobello Mushroom'),
    (r'shiitake|σιιτακε|σιτακε', 'Shiitake Mushroom'),
    (r'μανιταρ\w*\s+.*(καφε|brown)', 'Other mushrooms (el)'),
    (r'μανιταρ', 'White Mushroom'),
    (r'σπανακ', 'Spinach'),
    (r'ρουκολ', 'Arugula'),
    (r'αγγουρ', 'Cucumber'),
    (r'ντοματιν|ντοματακ|cherry', 'Cherry Tomato'),
    (r'ντοματ', 'Tomato'),
    (r'παντζαρ', 'Beetroot'),
    (r'καροτ', 'Carrot'),
    (r'γλυκοπατατ', 'Sweet Potato'),
    (r'πατατ', 'Potato'),
    (r'κρεμμυδακ', 'Spring Onions'),
    (r'κρεμμυδ', 'Onion'),
    (r'σκορδ', 'Garlic'),
    (r'μπροκολ', 'Broccoli'),
    (r'κουνουπιδ', 'Cauliflower'),
    (r'κολοκυθακ', 'Zucchini'),
    (r'κολοκυθ', 'Pumpkin'),
    (r'πιπερι', 'Bell Pepper'),
    (r'μελιτζαν', 'Eggplant'),
    (r'μαρουλ|σαλατ|λολο|iceberg|αισμπεργκ', 'Lettuce (el)'),
    (r'λαχαν', 'Cabbage (el)'),
    (r'^(φρεσκ\w*\s+)?βασιλικ', 'Genovese Basil'),
    (r'^(φρεσκ\w*\s+)?μαιντανο', 'Parsley'),
    (r'^(φρεσκ\w*\s+)?ανηθο', 'Dill'),
    (r'^(φρεσκ\w*\s+)?δυοσμο', 'Mint'),

    # ---- FRUIT ----
    (r'μηλ[αο]\b', 'Apples'),
    (r'αχλαδ', 'Pears'),
    (r'μπανανες|μπανανα', 'Banana'),
    (r'πορτοκαλ', 'Oranges'),
    (r'μανταριν', 'Mandarin Oranges Fresh'),
    (r'λεμονι', 'Lemons'),
    (r'φραουλ', 'Strawberries'),
    (r'ακτινιδ', 'Kiwi'),
    (r'σταφυλ', 'Grapes (el)'),
]

RULES = [(loose(p), n, None, None) for p, n in _RULES]

TARGETS = {n: None for _, n in _RULES if n.endswith('(el)')}
