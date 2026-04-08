import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.eroski import run as eroski_run
from scrapers.mercadona import run as mercadona_run

if __name__ == '__main__':
    eroski_run()
    mercadona_run()
