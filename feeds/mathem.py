"""
Sweden: shelf prices from Mathem (mathem.se), the national online grocer.

Mathem belongs to the Oda group and runs on the same platform: the same
public search endpoint, the same robots.txt conditions (a "bot" User-Agent
with a contact, backing off on 429/5xx, no `filter_` parameters). So it is
read with feeds/oda.py's code, with Swedish search words, and matched by
pipeline/rules_sv.py. National prices, one list for the country.

Willys (Axfood) also has a public category JSON, but its robots.txt asks for
ten seconds between requests and visits only between 04:00 and 08:45 UTC;
Mathem has no such window, so it is the Swedish shop source.

    python feeds/mathem.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds.oda import run, finish

if __name__ == '__main__':
    run('SE')
    if '--no-average' not in sys.argv:
        finish('SE')
