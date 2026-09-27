"""
The scrapers, and only the scrapers.

This used to call normalize and market_average as well, which run_all.sh then
called again — so every run classified and averaged the same rows twice. The
pipeline belongs to run_all.sh, which can tell which step failed; this file
just gathers.

A chain that raises stops the run rather than being skipped. An empty
Mercadona is not a day with no Mercadona prices, it is a day whose averages
would quietly be drawn from whatever else happened to work.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.consum import run as consum_run
from scrapers.eroski import run as eroski_run
from scrapers.mercadona import run as mercadona_run

# Ordered cheapest first, so a run that is going to fail on a wall tends to
# fail after something has already been gathered rather than before.
SCRAPERS = [
    ('Consum',    consum_run),
    ('Eroski',    eroski_run),
    ('Mercadona', mercadona_run),
]

if __name__ == '__main__':
    failures = []

    for name, run in SCRAPERS:
        try:
            run()
        except Exception as e:
            # Keep going: one chain behind a bot wall should not cost the day's
            # prices from the others. The failure is reported at the end, and
            # the exit code carries it, so run_all.sh still stops the pipeline.
            print(f'SCRAPER FAILED: {name}: {e}', file=sys.stderr)
            failures.append(name)

    if failures:
        print(f'{len(failures)} of {len(SCRAPERS)} scrapers failed: {", ".join(failures)}', file=sys.stderr)
        sys.exit(1)

    print(f'All {len(SCRAPERS)} scrapers finished.')
