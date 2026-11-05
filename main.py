"""
The scrapers, one at a time, each on its own.

    python main.py              every scraper
    python main.py Consum       just the one

Each scraper's outcome is recorded (utils/runs.py). One that fails no longer
stops the others or the rest of the run: a week Mercadona blocks us is still
a week with Consum's and Eroski's prices. The exit code says whether any
failed, so the weekly run can report it once everything else is done.
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.consum import run as consum_run
from scrapers.eroski import run as eroski_run
from scrapers.mercadona import run as mercadona_run
from utils.runs import record

SCRAPERS = [
    ('Consum',    consum_run),
    ('Eroski',    eroski_run),
    ('Mercadona', mercadona_run),
]

if __name__ == '__main__':
    only = set(sys.argv[1:])
    failures = []

    for name, run in SCRAPERS:
        if only and name not in only:
            continue
        started = time.time()
        try:
            run()
            record(f'scrape:{name}', 'ok', int(time.time() - started))
        except Exception as e:
            print(f'SCRAPER FAILED: {name}: {e}', file=sys.stderr)
            record(f'scrape:{name}', 'failed', int(time.time() - started))
            failures.append(name)

    if failures:
        print(f'{len(failures)} scraper(s) failed: {", ".join(failures)}', file=sys.stderr)
        sys.exit(1)
    print('All scrapers finished.')
