"""
Per country: the money its prices are in and the languages its shops write in.

Everything the scraper stores is in the country's own currency. The website
converts for display; converting here would bake one day's exchange rate
into a price for good.
"""

COUNTRIES = {
    'ES': {'currency': 'EUR', 'langs': ['es']},
    'PT': {'currency': 'EUR', 'langs': ['pt']},
    'FR': {'currency': 'EUR', 'langs': ['fr']},
    'DE': {'currency': 'EUR', 'langs': ['de']},
    'AT': {'currency': 'EUR', 'langs': ['de']},
    'CH': {'currency': 'CHF', 'langs': ['de', 'fr', 'it']},
    'LI': {'currency': 'CHF', 'langs': ['de']},
    'IT': {'currency': 'EUR', 'langs': ['it']},
    'SM': {'currency': 'EUR', 'langs': ['it']},
    'BE': {'currency': 'EUR', 'langs': ['nl', 'fr']},
    'NL': {'currency': 'EUR', 'langs': ['nl']},
    'LU': {'currency': 'EUR', 'langs': ['fr', 'de']},
    'IE': {'currency': 'EUR', 'langs': ['en']},
    'GB': {'currency': 'GBP', 'langs': ['en']},
    'US': {'currency': 'USD', 'langs': ['en']},
    'CA': {'currency': 'CAD', 'langs': ['en', 'fr']},
    'NZ': {'currency': 'NZD', 'langs': ['en']},
    'AU': {'currency': 'AUD', 'langs': ['en']},
    'NO': {'currency': 'NOK', 'langs': ['no']},
    'SE': {'currency': 'SEK', 'langs': ['sv']},
    'DK': {'currency': 'DKK', 'langs': ['da']},
    'FI': {'currency': 'EUR', 'langs': ['fi']},
    'EE': {'currency': 'EUR', 'langs': ['et']},
    'LV': {'currency': 'EUR', 'langs': ['lv']},
    'LT': {'currency': 'EUR', 'langs': ['lt']},
    'PL': {'currency': 'PLN', 'langs': ['pl']},
    'CZ': {'currency': 'CZK', 'langs': ['cs']},
    'SK': {'currency': 'EUR', 'langs': ['sk']},
    'HU': {'currency': 'HUF', 'langs': ['hu']},
    'SI': {'currency': 'EUR', 'langs': ['sl']},
    'HR': {'currency': 'EUR', 'langs': ['hr']},
    'RS': {'currency': 'RSD', 'langs': ['sr']},
    'RO': {'currency': 'RON', 'langs': ['ro']},
    'GR': {'currency': 'EUR', 'langs': ['el']},
}


def currency(country):
    return COUNTRIES.get((country or 'ES').upper(), {}).get('currency', 'EUR')


def language(country):
    return COUNTRIES.get((country or 'ES').upper(), {}).get('langs', ['en'])[0]
