import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.eroski import run as eroski_run
from scrapers.mercadona import run as mercadona_run
from pipeline.normalize import run as normalize_run
from pipeline.market_average import run as market_average_run

if __name__ == '__main__':
    eroski_run()
    mercadona_run()
    normalize_run()
    market_average_run()
