import re
from utils.db import get_connection

def parse_price_string(raw_price):
    actual_price = None
    unit_price   = None
    unit         = None

    merc_100g = re.search(r'1 100 G A\s*([\d]+[.,][\d]+)', raw_price, re.IGNORECASE)
    merc_kg   = re.search(r'1 KG A\s*([\d]+[.,][\d]+)', raw_price, re.IGNORECASE)
    merc_l    = re.search(r'1 L A\s*([\d]+[.,][\d]+)', raw_price, re.IGNORECASE)
    merc_dz   = re.search(r'1 D(?:C|Z|OCENA) A\s*([\d]+[.,][\d]+)', raw_price, re.IGNORECASE)
    ero_kg    = re.search(r'1 KILO A\s*([\d]+[,.][\d]+)', raw_price, re.IGNORECASE)
    ero_l     = re.search(r'1 LITRO A\s*([\d]+[,.][\d]+)', raw_price, re.IGNORECASE)
    ero_dz    = re.search(r'1 DOCENA A\s*([\d]+[,.][\d]+)', raw_price, re.IGNORECASE)

    if merc_100g:
        unit_price = round(float(merc_100g.group(1).replace(',', '.')) * 10, 4)
        unit = '€/kg'
    elif merc_kg or ero_kg:
        m = merc_kg or ero_kg
        unit_price = float(m.group(1).replace(',', '.'))
        unit = '€/kg'
    elif merc_l or ero_l:
        m = merc_l or ero_l
        unit_price = float(m.group(1).replace(',', '.'))
        unit = '€/l'
    elif merc_dz or ero_dz:
        m = merc_dz or ero_dz
        unit_price = float(m.group(1).replace(',', '.'))
        unit = '€/docena'

    ahora = re.search(r'Ahora([\d]+[,.][\d]+)', raw_price)
    if ahora:
        actual_price = float(ahora.group(1).replace(',', '.'))

    if not actual_price:
        prices = re.findall(r'([\d]+[,.][\d]+)\s*€', raw_price)
        valid = [float(p.replace(',', '.')) for p in prices if 0.1 < float(p.replace(',', '.')) < 500]
        if valid:
            actual_price = min(valid)

    if actual_price and not unit:
        unit = '€/unit'
    return actual_price, unit_price, unit

CANNED_SIGNALS = [r'\blata\b', r'\bfrasco\b', r'\bbrik\b', r'\buht\b', r'\bconserva\b', r'\bpasteurizad', r'\bbote\b', r'\btarro\b']
FROZEN_SIGNALS = [r'\bcongelad', r'\bsurgelad', r'\bultracongelad']

def detect_state(raw_name):
    n = raw_name.lower()
    if any(re.search(p, n) for p in FROZEN_SIGNALS):
        return 'frozen'
    if any(re.search(p, n) for p in CANNED_SIGNALS):
        return 'canned'
    return 'fresh'

RULES = [
    # ---- EGGS ----
    (r'clara.*huevo|huevo.*clara', 'Egg Whites', 'eggs', 310),
    (r'yema.*huevo|huevo.*yema', 'Egg Yolks', 'eggs', 311),
    (r'huevo.*codorniz|codorniz.*huevo', 'Quail Eggs', 'eggs', 309),
    (r'huevo.*pato|pato.*huevo', 'Duck Eggs', 'eggs', 308),
    (r'huevo.*ecol[oó]g|ecol[oó]g.*huevo|huevo.*bio\b', 'Organic Eggs', 'eggs', 307),
    (r'huevo.*campero|campero.*huevo|huevo.*caser[ií]o|gallinas camperas', 'Free Range Eggs', 'eggs', 306),
    (r'huevo.*xxl|xxl.*huevo', 'Eggs XXL', 'eggs', 305),
    (r'huevo.*\bxl\b|\bxl\b.*huevo', 'Eggs XL', 'eggs', 301),
    (r'huevo.*\bl\b|huevo.*grande', 'Eggs L', 'eggs', 302),
    (r'huevo.*\bm\b|huevo.*median', 'Eggs M', 'eggs', 303),
    (r'huevo.*\bs\b|huevo.*peque', 'Eggs S', 'eggs', 304),
    (r'\bhuevo\b|\bhuevos\b', 'Eggs', 'eggs', 300),

    # ---- DAIRY: BUTTER & CREAM ----
    (r'nata.*montar|montar.*nata', 'Whipping Cream', 'dairy', 209),
    (r'nata.*cocinar|cocinar.*nata|nata.*fresca', 'Cooking Cream', 'dairy', 208),
    (r'\bmantequilla\b', 'Butter', 'dairy', 207),
    (r'leche.*evaporada|evaporada.*leche', 'Evaporated Milk', 'dairy', 206),
    (r'leche.*condensada|condensada.*leche', 'Condensed Milk', 'dairy', 205),

    # ---- DAIRY: MILK ----
    (r'leche.*oveja|oveja.*leche', 'Sheep Milk', 'dairy', 204),
    (r'leche.*cabra|cabra.*leche', 'Goat Milk', 'dairy', 203),
    (r'leche.*semidesnatada|semidesnatada.*leche', 'Semi-skimmed Milk', 'dairy', 201),
    (r'leche.*desnatada|desnatada.*leche', 'Skim Milk', 'dairy', 202),
    (r'leche.*entera|entera.*leche', 'Whole Milk', 'dairy', 200),

    # ---- DAIRY: CHEESE ----
    (r'mozzarella.*b[úu]fala|b[úu]fala.*mozzarella|bufala', 'Buffalo Mozzarella', 'dairy', 213),
    (r'\bmozzarella\b', 'Mozzarella', 'dairy', 212),
    (r'\bburrata\b', 'Burrata', 'dairy', 235),
    (r'\bidiazabal\b', 'Idiazabal Cheese', 'dairy', 232),
    (r'\blatxa urdina\b', 'Blue Sheep Cheese', 'dairy', 221),
    (r'\bmanchego\b', 'Manchego Cheese', 'dairy', 233),
    (r'queso.*burgos|burgos.*queso', 'Burgos Fresh Cheese', 'dairy', 234),
    (r'\broquefort\b', 'Roquefort', 'dairy', 228),
    (r'\bgorgonzola\b', 'Gorgonzola', 'dairy', 229),
    (r'\bcamembert\b', 'Camembert', 'dairy', 227),
    (r'\bbrie\b', 'Brie', 'dairy', 226),
    (r'queso.*azul|azul.*queso', 'Blue Cheese', 'dairy', 221),
    (r'\bprovolone\b', 'Provolone', 'dairy', 230),
    (r'grana padano', 'Grana Padano', 'dairy', 219),
    (r'\bparmesano\b|\bparmesan\b', 'Parmesan', 'dairy', 218),
    (r'\bemmental\b', 'Emmental Cheese', 'dairy', 224),
    (r'\bcheddar\b', 'Cheddar Cheese', 'dairy', 225),
    (r'\bgouda\b', 'Gouda Cheese', 'dairy', 222),
    (r'\bedam\b', 'Edam Cheese', 'dairy', 223),
    (r'\bfeta\b', 'Feta Cheese', 'dairy', 217),
    (r'\bricotta\b|reques[oó]n', 'Ricotta', 'dairy', 216),
    (r'\bmascarpone\b', 'Mascarpone', 'dairy', 220),
    (r'queso.*untar|untar.*queso|queso.*crema|philadelphia', 'Cream Cheese', 'dairy', 215),
    (r'queso.*cabra|cabra.*queso', 'Goat Cheese', 'dairy', 210),
    (r'queso.*oveja|oveja.*queso', 'Sheep Cheese', 'dairy', 211),
    (r'queso.*viejo|queso.*a[ñn]ejo|queso.*curado|queso.*semicurado|queso.*madurado', 'Cured Mixed Cheese', 'dairy', 236),
    (r'queso.*fresco|fresco.*queso', 'Fresh Cheese', 'dairy', 214),
    (r'queso.*rallado|queso.*lonchas|queso.*fundido|queso.*porciones|queso.*blando|queso.*tierno|queso.*tronch[oó]n|queso.*mezcla|queso.*iberico|queso.*arzua', 'Mixed Cheese', 'dairy', 236),

    # ---- CANNED TOMATO ----
    (r'tomate.*frito|frito.*tomate', 'Fried Tomato Sauce', 'canned', 405),
    (r'tomate.*triturado|triturado.*tomate', 'Canned Tomato Crushed', 'canned', 400),
    (r'tomate.*troceado|troceado.*tomate', 'Canned Tomato Chopped', 'canned', 402),
    (r'tomate.*entero.*pelado|pelado.*tomate', 'Canned Tomato Whole Peeled', 'canned', 401),
    (r'tomate.*concentrado|concentrado.*tomate|tomate.*doble', 'Canned Tomato Concentrate', 'canned', 403),
    (r'tomate.*tamizado|tamizado.*tomate', 'Tomato Puree', 'canned', 404),
    (r'tomate.*rallado|rallado.*tomate', 'Grated Tomato Spread', 'canned', 438),
    (r'tomate.*seco|seco.*tomate', 'Dried Tomato in Oil', 'canned', 425),
    (r'tomate.*untar', 'Tomato Puree', 'canned', 404),

    # ---- CANNED VEG ----
    (r'esp[áa]rrago.*tarro|esp[áa]rrago.*bote|esp[áa]rrago.*conserva|esp[áa]rrago.*blanco.*tarro', 'Canned White Asparagus', 'canned', 406),
    (r'esp[áa]rrago.*verde.*tarro|esp[áa]rrago.*verde.*bote', 'Canned Green Asparagus', 'canned', 407),
    (r'champi[ñn][oó]n.*bote|champi[ñn][oó]n.*lata|champi[ñn][oó]n.*conserva|seta.*conserva', 'Canned Mushrooms', 'canned', 408),
    (r'piquillo', 'Canned Piquillo Peppers', 'canned', 409),
    (r'pimiento.*rojo.*tarro|pimiento.*rojo.*bote|pimiento.*asado|pimiento.*conserva', 'Canned Red Peppers', 'canned', 410),
    (r'guisante.*tarro|guisante.*bote|guisante.*conserva|guisante.*lata', 'Canned Green Peas', 'canned', 411),
    (r'jud[ií]a.*verde.*tarro|jud[ií]a.*verde.*bote|jud[ií]a.*verde.*conserva', 'Canned Green Beans', 'canned', 412),
    (r'ma[íi]z.*dulce.*tarro|ma[íi]z.*dulce.*bote|ma[íi]z.*dulce.*conserva|ma[íi]z.*dulce.*lata', 'Canned Sweetcorn', 'canned', 413),
    (r'alcachofa.*tarro|alcachofa.*bote|coraz[oó]n.*alcachofa', 'Canned Artichoke Hearts', 'canned', 414),
    (r'remolacha.*tarro|remolacha.*bote|remolacha.*conserva', 'Canned Beetroot', 'canned', 415),
    (r'zanahoria.*tarro|zanahoria.*bote|zanahoria.*conserva', 'Canned Carrots', 'canned', 416),
    (r'patata.*tarro|patata.*bote|patata.*conserva|patata.*cocida', 'Canned Potatoes', 'canned', 417),
    (r'\bpisto\b', 'Canned Pisto', 'canned', 418),
    (r'menestra|macedonia.*verdura|verdura.*macedonia', 'Canned Mixed Vegetables', 'canned', 419),
    (r'palmito', 'Canned Palm Hearts', 'canned', 426),
    (r'mazorquita', 'Canned Baby Corn', 'canned', 428),
    (r'verdura.*asada|asada.*verdura', 'Roasted Vegetables', 'canned', 427),
    (r'acelga.*tarro|acelga.*bote|acelga.*conserva', 'Canned Swiss Chard', 'canned', 419),

    # ---- CANNED FRUIT ----
    (r'melocot[oó]n.*alm[íi]bar|alm[íi]bar.*melocot[oó]n', 'Canned Peach in Syrup', 'canned', 420),
    (r'pi[ñn]a.*jugo|pi[ñn]a.*alm[íi]bar|pi[ñn]a.*natural.*bote|pi[ñn]a.*natural.*tarro', 'Canned Pineapple in Juice', 'canned', 421),
    (r'pera.*alm[íi]bar|alm[íi]bar.*pera', 'Canned Pear in Syrup', 'canned', 422),
    (r'macedonia.*fruta|fruta.*macedonia', 'Canned Mixed Fruit', 'canned', 423),
    (r'membrillo', 'Quince Paste', 'canned', 424),

    # ---- VEGETABLES: TOMATOES ----
    (r'tomate.*cherry|cherry.*tomate|tomate.*picoteo|tomate.*sunstream|tomate.*s[aã]o paulo', 'Cherry Tomato', 'veg', 1),
    (r'tomate.*c[oó]ctel|tomate.*cocktail|tomate.*mini(?!atura)', 'Cocktail Tomato', 'veg', 57),
    (r'tomate.*rama|rama.*tomate|tomate.*racimo', 'Tomato on the Vine', 'veg', 53),
    (r'tomate.*rom[aá]ntic', 'Romantic Tomato', 'veg', 58),
    (r'tomate.*pera|pera.*tomate|tomate.*canario|tomate.*ciruelo', 'Plum Tomato', 'veg', 55),
    (r'tomate.*ensalada|tomate.*rosa|tomate.*coraz[oó]n|tomate.*muchamiel|tomate.*beef', 'Beef Tomato', 'veg', 54),
    (r'tomate.*negro|tomate.*kumato', 'Black Tomato', 'veg', 56),
    (r'\btomate\b|\btomates\b', 'Tomato', 'veg', 9),

    # ---- VEGETABLES: LETTUCE ----
    (r'lechuga.*batavia|batavia.*lechuga', 'Batavia Lettuce', 'veg', 4),
    (r'lechuga.*iceberg|iceberg.*lechuga', 'Iceberg Lettuce', 'veg', 3),
    (r'lechuga.*lollo|lollo.*lechuga|lollo rojo', 'Lollo Rosso Lettuce', 'veg', 38),
    (r'lechuga.*hoja.*roble|hoja.*roble', 'Oak Leaf Lettuce', 'veg', 39),
    (r'lechuga.*romana|romana.*lechuga|coraz[oó]n.*romana|cogollo', 'Romaine Lettuce', 'veg', 2),
    (r'can[oó]nigos', 'Lamb\'s Lettuce', 'veg', 40),
    (r'r[úu]cula', 'Rocket', 'veg', 41),
    (r'escarola', 'Escarole', 'veg', 42),
    (r'endibi[ao]|endivia', 'Endive', 'veg', 43),
    (r'espinaca.*baby|baby.*espinaca', 'Baby Spinach', 'veg', 44),
    (r'\blechuga\b', 'Romaine Lettuce', 'veg', 2),

    # ---- VEGETABLES: MUSHROOMS ----
    (r'seta.*ostra|ostra.*seta', 'Oyster Mushroom', 'veg', 67),
    (r'\bshiitake\b|\bshitake\b', 'Shiitake Mushroom', 'veg', 66),
    (r'\bportobello\b', 'Portobello Mushroom', 'veg', 68),
    (r'mix.*seta|seta.*mix|seta.*variada', 'Mixed Mushrooms', 'veg', 70),
    (r'champi[ñn][oó]n|seta\b', 'White Mushroom', 'veg', 69),

    # ---- VEGETABLES: ONION & GARLIC ----
    (r'ajo.*negro', 'Black Garlic', 'veg', 86),
    (r'ajo.*tierno', 'Spring Garlic', 'veg', 87),
    (r'ajo.*morado', 'Purple Garlic', 'veg', 88),
    (r'\bajo\b|\bajos\b', 'Garlic', 'veg', 16),
    (r'cebolla.*roja', 'Red Onion', 'veg', 75),
    (r'cebolla.*blanca', 'White Onion', 'veg', 76),
    (r'cebolla.*dulce', 'Sweet Onion', 'veg', 77),
    (r'cebolleta|cebolla.*tierna', 'Spring Onion', 'veg', 46),
    (r'cebollino', 'Chives', 'veg', 47),
    (r'\bcebolla\b|\bcebollas\b', 'Onion', 'veg', 15),

    # ---- VEGETABLES: PEPPERS ----
    (r'pimiento.*picante|pimiento.*guindilla|jalape[ñn]o', 'Chili Pepper', 'veg', 64),
    (r'\bpimiento\b|\bpimientos\b', 'Bell Pepper', 'veg', 11),

    # ---- VEGETABLES: CABBAGE ----
    (r'repollo.*morado|col.*morada|lombarda', 'Red Cabbage', 'veg', 58),
    (r'repollo.*rizado|col.*rizada|savoy', 'Savoy Cabbage', 'veg', 60),
    (r'col.*bruselas|coles.*bruselas', 'Brussels Sprouts', 'veg', 61),
    (r'\brepollo\b|\bcol\b', 'Cabbage', 'veg', 37),

    # ---- VEGETABLES: POTATO & ROOT ----
    (r'batata.*microondas|batata\b', 'Sweet Potato', 'veg', 34),
    (r'\bpatata\b|\bpatatas\b', 'Potato', 'veg', 14),
    (r'\byuca\b', 'Yuca', 'veg', 63),
    (r'remolacha', 'Beetroot', 'veg', 35),
    (r'nabicol|\bnabo\b', 'Kohlrabi', 'veg', 90),
    (r'r[áa]bano', 'Radish', 'veg', 79),

    # ---- VEGETABLES: BRASSICA ----
    (r'br[oó]coli|brocoli', 'Broccoli', 'veg', 17),
    (r'coliflor', 'Cauliflower', 'veg', 18),
    (r'\bkale\b|col rizada', 'Kale', 'veg', 20),

    # ---- VEGETABLES: GREENS ----
    (r'espinaca', 'Spinach', 'veg', 19),
    (r'acelga', 'Swiss Chard', 'veg', 84),
    (r'jud[ií]a.*verde|ejote', 'Green Beans', 'veg', 71),
    (r'guisante', 'Green Peas', 'veg', 72),
    (r'\bhaba\b|\bhabas\b', 'Fava Beans', 'veg', 73),

    # ---- VEGETABLES: OTHER ----
    (r'esp[áa]rrago.*verde', 'Green Asparagus', 'veg', 6),
    (r'esp[áa]rrago.*blanco|esp[áa]rrago', 'White Asparagus', 'veg', 5),
    (r'calabaza.*cacahuete|cacahuete.*calabaza|butternut', 'Butternut Squash', 'veg', 74),
    (r'\bcalabaza\b', 'Pumpkin', 'veg', 33),
    (r'calabac[íi]n', 'Zucchini', 'veg', 12),
    (r'berenjena', 'Eggplant', 'veg', 82),
    (r'zanahoria', 'Carrot', 'veg', 13),
    (r'pepino', 'Cucumber', 'veg', 10),
    (r'\bpuerro\b|\bpuerros\b', 'Leek', 'veg', 78),
    (r'alcachofa', 'Artichoke', 'veg', 81),
    (r'apio', 'Celery', 'veg', 36),
    (r'hinojo', 'Fennel', 'veg', 80),
    (r'ma[íi]z.*dulce|mazorca', 'Sweet Corn', 'veg', 62),
    (r'jengibre', 'Ginger', 'veg', 52),
    (r'albahaca', 'Basil', 'veg', 50),
    (r'perejil', 'Parsley', 'veg', 48),
    (r'cilantro', 'Coriander', 'veg', 49),
    (r'hierbabuena|\bmenta\b', 'Mint', 'veg', 51),
    (r'bok choy', 'Bok Choy', 'veg', 85),

    # ---- FRUIT: BERRIES ----
    (r'fres[oó]n|fresa', 'Strawberries', 'fruit', 100),
    (r'ar[áa]ndano', 'Blueberries', 'fruit', 101),
    (r'\bmora\b|\bmoras\b', 'Blackberries', 'fruit', 102),
    (r'frambuesa', 'Raspberries', 'fruit', 103),

    # ---- FRUIT: APPLES & PEARS ----
    (r'manzana.*pink lady|pink lady', 'Pink Lady Apple', 'fruit', 108),
    (r'manzana.*granny|granny smith', 'Granny Smith Apple', 'fruit', 106),
    (r'manzana.*golden|golden.*manzana', 'Golden Apple', 'fruit', 105),
    (r'manzana.*roja|manzana.*rojo', 'Red Apple', 'fruit', 107),
    (r'\bmanzana\b|\bmanzanas\b', 'Apples', 'fruit', 104),
    (r'pera.*conferencia|conferencia.*pera', 'Conference Pear', 'fruit', 110),
    (r'\bpera\b|\bperas\b', 'Pears', 'fruit', 109),

    # ---- FRUIT: CITRUS ----
    (r'mandarina|clementina', 'Tangerine', 'fruit', 132),
    (r'naranja', 'Oranges', 'fruit', 113),
    (r'\blim[oó]n\b|\blimones\b', 'Lemons', 'fruit', 114),
    (r'\blima\b', 'Lime', 'fruit', 134),
    (r'pomelo', 'Grapefruit', 'fruit', 135),

    # ---- FRUIT: TROPICAL ----
    (r'pl[áa]tano.*canarias|pl[áa]tano.*igp', 'Canary Islands Banana', 'fruit', 123),
    (r'pl[áa]tano|banana', 'Banana', 'fruit', 122),
    (r'\bmango\b', 'Mango', 'fruit', 125),
    (r'papaya', 'Papaya', 'fruit', 126),
    (r'\baguacate\b', 'Avocado', 'fruit', 115),
    (r'\bpi[ñn]a\b', 'Pineapple', 'fruit', 124),
    (r'\bkiwi\b', 'Kiwi', 'fruit', 129),
    (r'guayaba', 'Guava', 'fruit', 127),
    (r'maracuy[áa]|fruta.*pasi[oó]n', 'Passion Fruit', 'fruit', 128),

    # ---- FRUIT: OTHER ----
    (r'sand[íi]a', 'Watermelon', 'fruit', 116),
    (r'mel[oó]n.*piel.*sapo', 'Piel de Sapo Melon', 'fruit', 118),
    (r'\bmel[oó]n\b', 'Melon', 'fruit', 117),
    (r'melocot[oó]n', 'Peaches', 'fruit', 111),
    (r'ciruela', 'Plums', 'fruit', 112),
    (r'uva.*blanca|uva.*verde', 'Grapes Green', 'fruit', 121),
    (r'uva.*roja|uva.*negra', 'Grapes Red', 'fruit', 120),
    (r'\buva\b|\buvas\b', 'Grapes Green', 'fruit', 121),
    (r'\bhigo\b|\bhigos\b', 'Fig', 'fruit', 130),
    (r'granada', 'Pomegranate', 'fruit', 131),

    # ---- MEAT ----
    (r'pollo.*ecol[oó]g|ecol[oó]g.*pollo|pollo.*bio\b', 'Organic Chicken', 'meat', 500),
    (r'pollo.*campero|campero.*pollo', 'Free Range Chicken', 'meat', 501),
    (r'\bpollo\b', 'Chicken', 'meat', 502),
    (r'\bpavo\b', 'Turkey', 'meat', 503),
    (r'ternera.*ecol[oó]g|ecol[oó]g.*ternera', 'Organic Veal', 'meat', 510),
    (r'\bternera\b', 'Veal', 'meat', 511),
    (r'cerdo.*ecol[oó]g|ecol[oó]g.*cerdo', 'Organic Pork', 'meat', 520),
    (r'\bcerdo\b', 'Pork', 'meat', 521),
    (r'cordero.*ecol[oó]g|ecol[oó]g.*cordero', 'Organic Lamb', 'meat', 530),
    (r'\bcordero\b', 'Lamb', 'meat', 531),
    (r'\bvacuno\b', 'Beef', 'meat', 540),
]

COMPILED_RULES = [(re.compile(pattern, re.IGNORECASE), pattern, name, category, pid) for pattern, name, category, pid in RULES]

def _infer_confidence(pattern_str):
    return 'high' if '.*' in pattern_str else 'medium'

REJECT_PATTERNS = [re.compile(p, re.IGNORECASE) for p in [
    r'\byogur[t]?\b|\bkéfir\b|\bkefir\b|\bpostre\s+l[aá]cte',
    r'\batún\b|\batun\b|\bsardina[s]?\b|\bsardinilla[s]?\b|\bcaballa\b|\bboquer[oó]n\b|\banchos\b|\bmejill[oó]n\b',
    r'\ben\s+(?:salsa\s+de\s+)?tomate\b',
    r'\bmerluza\b|\bsalm[oó]n\b|\bbacalao\b|\bdorada\b|\blubina\b|\blenguado\b|\bcalamar\b|\bgamba[s]?\b|\bpulpo\b|\bsepia\b',
]]

def classify(raw_name):
    n = raw_name.lower()
    for pat in REJECT_PATTERNS:
        if pat.search(n):
            return None, None, None, None
    for pattern, pattern_str, name, category, pid in COMPILED_RULES:
        if pattern.search(n):
            return name, category, pid, _infer_confidence(pattern_str)
    return None, None, None, None

def ensure_schema(conn):
    with conn.cursor() as cursor:
        for col, definition in [
            ('confidence',    "ENUM('high','medium','low') NULL AFTER catalog_product_id"),
            ('review_needed', "TINYINT(1) DEFAULT 0 AFTER confidence"),
            ('region',        "VARCHAR(100) NULL AFTER city"),
        ]:
            cursor.execute("""
                SELECT COUNT(*) AS cnt FROM information_schema.COLUMNS
                WHERE TABLE_SCHEMA = DATABASE()
                  AND TABLE_NAME   = 'products_normalized'
                  AND COLUMN_NAME  = %s
            """, (col,))
            if cursor.fetchone()['cnt'] == 0:
                cursor.execute(f"ALTER TABLE products_normalized ADD COLUMN {col} {definition}")
                print(f"  Added {col} column.")

def run():
    conn = get_connection()
    inserted = discarded = errors = 0
    try:
        ensure_schema(conn)
        conn.commit()
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT r.* FROM raw_scrapes r
                LEFT JOIN products_normalized p ON p.raw_scrape_id = r.id
                WHERE p.id IS NULL
            """)
            rows = cursor.fetchall()
        total = len(rows)
        print(f"Found {total} raw records to normalize...\n")
        for i, row in enumerate(rows):
            raw_name = row['raw_name']
            actual_price, unit_price, unit = parse_price_string(row.get('raw_price') or '')
            if not actual_price:
                discarded += 1
                print(f"  [{i+1}/{total}] NO PRICE: {raw_name[:60]}")
                continue
            canonical_name, category, cat_id, confidence = classify(raw_name)
            if not canonical_name:
                discarded += 1
                print(f"  [{i+1}/{total}] NO MATCH: {raw_name[:60]}")
                continue
            state = detect_state(raw_name)
            print(f"  [{i+1}/{total}] OK: '{raw_name[:45]}' → {canonical_name} [{confidence}]")
            try:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO products_normalized
                            (raw_scrape_id, chain, postal_code, city, region,
                             category, state, canonical_name,
                             catalog_product_id, confidence, review_needed,
                             raw_name, price, unit_price, unit, scraped_at)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """, (
                        row['id'], row.get('chain'), row.get('postal_code'),
                        row.get('city'), row.get('region'), category, state, canonical_name,
                        cat_id, confidence, 0,
                        raw_name, actual_price, unit_price, unit,
                        row.get('scraped_at')
                    ))
                inserted += 1
            except Exception as e:
                errors += 1
                print(f"    DB error: {e}")
            if (i + 1) % 10 == 0:
                conn.commit()
                print(f"  --- committed {i+1}/{total} ---")
        conn.commit()
        print(f"\nDone!")
        print(f"  {inserted} inserted")
        print(f"  {discarded} discarded/no match")
        print(f"  {errors} db errors")
    finally:
        conn.close()

if __name__ == '__main__':
    run()
