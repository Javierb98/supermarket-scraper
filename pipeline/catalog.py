"""
The website's catalogue, for code that names products itself (the official
feeds): their names → the catalogue's.

The site compares prices by catalogue name. Statistics Canada says
"Potatoes" and the catalogue says "Potato", so for as long as the feeds
wrote their own names, Canadian and American potato prices matched no
farm's potatoes.
"""

import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Feed names → catalogue names. None: no catalogue product is the same thing
# (US "Lettuce" is mostly iceberg, which the catalogue does not have).
ALIASES = {
    'Avocados': 'Avocado',
    'Bananas': 'Banana',
    'Carrots': 'Carrot',
    'Cottage Cheese': 'Fresh Cottage Cheese',
    'Cucumbers': 'Cucumber',
    'Mangoes': 'Mango',
    'Mandarins': 'Mandarin Oranges Fresh',
    'Milk': 'Whole Milk',
    'Mushrooms': 'White Mushroom',
    'Onions': 'Onion',
    'Peppers': 'Bell Pepper',
    'Potatoes': 'Potato',
    'Sweet Potatoes': 'Sweet Potato',
    'Tomatoes': 'Tomato',
}

_catalog = None


def products():
    global _catalog
    if _catalog is None:
        with open(os.path.join(ROOT, 'data', 'catalog.json'), encoding='utf-8') as f:
            _catalog = {p['name'].lower(): p for p in json.load(f)}
    return _catalog


def resolve(name):
    """A feed's product name → (catalogue name, catalogue id), or (name, None) when it has none."""
    target = ALIASES.get(name, name)
    p = products().get((target or '').lower())
    return (p['name'], p['id']) if p else (name, None)
