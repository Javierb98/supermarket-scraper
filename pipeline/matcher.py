"""
Which catalogue product a shelf name is.

Two ways, in order:

  1. A language's hand-written rules, where there are any (Spanish today).
     They know a shop's vocabulary: "cogollo" is romaine, "tomate pera" is a
     plum tomato.

  2. The catalogue's own name for the product in the shop's language, at the
     start of the shelf name: "Calabacín, Pieza" is the catalogue's
     "Calabacín". Only at the start, because a product's name leads and what
     follows describes it — "Bífidus con kiwi" is not a kiwi. The longest
     name wins, so "Tomate Cherry" beats "Tomate".

Then two checks before a match counts for a fresh product: it must not be
processed or non-food (pipeline/processed.py), and it must not be frozen.
"""

import json
import os
import re
import unicodedata

from pipeline import processed

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Rules per language: pipeline/rules_<lang>.py, picked up when present.
# Each defines LANG, RULES [(pattern, catalogue-or-rule name, ...)], TARGETS
# {rule name: catalogue name or None} and REJECT [compiled patterns]; it may
# define detect_state(raw_name) and LEADING [words to skip at the start].
import glob as _glob  # noqa: E402
import importlib as _importlib  # noqa: E402

RULES = {}
for _path in sorted(_glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rules_*.py'))):
    _mod = _importlib.import_module('pipeline.' + os.path.basename(_path)[:-3])
    RULES[_mod.LANG] = _mod

# Words a shelf name may start with that are not the product.
LEADING = {
    'es': ['bio', 'ecologico', 'ecologica', 'ecologicos', 'ecologicas', 'eco', 'nuevo', 'nueva'],
    'fr': ['bio', 'nouveau', 'nouvelle'],
    'de': ['bio', 'neu'],
    'it': ['bio', 'biologico', 'biologica', 'nuovo'],
    'pt': ['bio', 'biologico', 'biologica', 'novo'],
    'nl': ['bio', 'biologisch', 'biologische', 'nieuw', 'ah', 'jumbo'],
    'en': ['organic', 'new', 'fresh'],
}


# Fresh produce is named first on a shelf; other products often are not
# ("Leche entera", but also "Queso de cabra" and "Pechuga de pollo").
LEADS_REQUIRED = {'vegetables', 'fruit'}


def fold(s):
    """Lower case, no accents, single spaces."""
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'\s+', ' ', re.sub(r'[^\w\s]', ' ', s)).strip()


def plurals(word, lang):
    out = {word}
    if lang in ('es', 'pt', 'fr', 'en', 'nl'):
        out |= {word + 's', word + 'es'}
    if lang == 'es' and word.endswith('z'):
        out.add(word[:-1] + 'ces')
    if lang == 'it' and word[-1:] in 'aoe':
        out |= {word[:-1] + 'i', word[:-1] + 'e'}
    if lang == 'de':
        out |= {word + 'n', word + 'en', word + 'e'}
    if lang == 'nl':
        out |= {word + 'en', word + 'n'}
    return out


class Matcher:
    def __init__(self, catalog_path=None):
        path = catalog_path or os.path.join(ROOT, 'data', 'catalog.json')
        with open(path, encoding='utf-8') as f:
            self.catalog = json.load(f)
        self.by_name = {p['name'].lower(): p for p in self.catalog}
        self._prefix = {}

    def product(self, english_name):
        return self.by_name.get((english_name or '').lower())

    def _prefixes(self, lang):
        if lang not in self._prefix:
            entries = []
            for p in self.catalog:
                name = p['names'].get(lang)
                if not name:
                    continue
                words = fold(name).split()
                if not words:
                    continue
                # Plural forms on the head word, which is the first in the
                # Romance languages and the last in German, Dutch and English.
                head = 0 if lang in ('es', 'fr', 'it', 'pt', 'eu') else len(words) - 1
                for form in plurals(words[head], lang):
                    w = list(words)
                    w[head] = form
                    entries.append((' '.join(w), p))
            entries.sort(key=lambda e: len(e[0]), reverse=True)
            self._prefix[lang] = entries
        return self._prefix[lang]

    @staticmethod
    def _leads(before, lang):
        """Whether only throwaway words come before the matched product."""
        words = fold(before).split()
        extra = getattr(RULES.get(lang), 'LEADING', [])
        return all(w in LEADING.get(lang, []) or w in extra or w.isdigit() for w in words)

    def match(self, raw_name, lang):
        """
        → (product or None, how, label)
            how: 'rule' | 'catalog' | 'unlisted' (a rule matched a product the
                 catalogue does not have) | 'rejected' | None
        """
        rules = RULES.get(lang)
        n = raw_name.lower()
        if rules:
            for rx in getattr(rules, 'REJECT', []):
                if rx.search(n):
                    return None, 'rejected', None
            for rx, name in _compiled(rules):
                m = rx.search(n)
                if m:
                    target = rules.TARGETS.get(name, name)
                    p = self.product(target) if target else None
                    if p and p['category'] in LEADS_REQUIRED and not self._leads(n[:m.start()], lang):
                        # "Escalivada con cebolla", "Paté de pato con cebolla":
                        # the product is named first, and here it is not.
                        return None, 'not_lead', name
                    return (p, 'rule', name) if p else (None, 'unlisted', name)

        folded = fold(raw_name)
        lead = LEADING.get(lang, []) + list(getattr(rules, 'LEADING', []) if rules else [])
        words = folded.split()
        while words and words[0] in lead:
            words = words[1:]
        folded = ' '.join(words)
        for prefix, p in self._prefixes(lang):
            if folded == prefix or folded.startswith(prefix + ' '):
                return p, 'catalog', prefix
        return None, None, None


_COMPILED = {}


def _compiled(rules):
    key = rules.__name__
    if key not in _COMPILED:
        _COMPILED[key] = [(re.compile(p, re.I), name) for p, name, *_ in rules.RULES]
    return _COMPILED[key]


def detect_state(raw_name, lang):
    rules = RULES.get(lang)
    if rules and hasattr(rules, 'detect_state'):
        return rules.detect_state(raw_name)
    n = raw_name.lower()
    if re.search(r'frozen|surgel|tiefgek|congel|surgelat|diepvries', n):
        return 'frozen'
    return 'fresh'


def check_fresh(product, raw_name, lang, state):
    """None if the match can price a fresh product, else why it cannot."""
    if product['category'] not in processed.FRESH_CATEGORIES:
        return None
    if state == 'frozen':
        return 'frozen'
    # Milk in a carton and pasteurised egg whites are how those are sold;
    # a tinned vegetable is not a vegetable's price.
    if state == 'canned' and product['category'] in ('vegetables', 'fruit', 'meat', 'poultry'):
        return 'canned'
    # The product's own name is not a sign of processing: "Joghurt natur"
    # matched to Yogurt is yogurt, not something made with it.
    checked = fold(raw_name)
    for own in (product['names'].get(lang), product['name']):
        if own:
            checked = checked.replace(fold(own), ' ')
    why = processed.why_processed(checked, lang)
    return 'processed' if why else None
