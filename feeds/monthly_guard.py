"""
A guard in front of common.write() for the monthly official feeds (Stats NZ,
BLS, MAPA). Not a feed itself, so it is not in registry.py.

It deals with two things common.write() does not:

1. Another source already holding the same key. market_average is unique on
   (canonical_name, country, region, snapshot_date, standard_unit,
   price_stage) and the source is not part of it, so a monthly figure dated
   the 1st would silently overwrite a USDA week or a shop scrape that also
   happened to be dated the 1st. Those figures are dropped and reported, never
   written over.

2. National figures (region NULL). MySQL treats NULLs in a unique key as
   distinct, so ON DUPLICATE KEY never fires for them and every rerun would
   add another copy. This feed's own earlier national rows for the same key
   are deleted first, so a rerun replaces rather than piles up.

If common.write() ever learns both, this file can go.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from feeds import common
from utils.db import get_connection, ensure_market_average_schema

EXISTING = """
SELECT source_name FROM market_average
WHERE canonical_name = %s AND country = %s AND region <=> %s AND snapshot_date = %s
  AND standard_unit = %s AND price_stage = %s
"""

DELETE_OWN_NATIONAL = """
DELETE FROM market_average
WHERE canonical_name = %s AND country = %s AND region IS NULL AND snapshot_date = %s
  AND standard_unit = %s AND price_stage = %s AND source_name = %s
"""


def write(country, source_name, stage, figures):
    """common.write(), minus figures that would collide with another source."""
    country = country.upper()
    catalog = common.products()
    keep, collisions = [], []

    conn = get_connection()
    try:
        ensure_market_average_schema(conn)
        with conn.cursor() as c:
            for f in figures:
                p = catalog.get(f.name.lower())
                if p is None:
                    keep.append(f)          # common.write() reports it as not in the catalogue
                    continue
                c.execute(EXISTING, (p['name'], country, f.region, f.snapshot, f.unit, stage))
                others = sorted({r['source_name'] or '(scrape)' for r in c.fetchall()} - {source_name})
                if others:
                    collisions.append((f, others))
                    continue
                if f.region is None:
                    c.execute(DELETE_OWN_NATIONAL, (p['name'], country, f.snapshot, f.unit, stage, source_name))
                keep.append(f)
        conn.commit()
    finally:
        conn.close()

    for f, others in collisions:
        print(f'  COLLISION, not written: {f.name} / {f.region or "national"} / {f.snapshot} / {f.unit} '
              f'is already held by {", ".join(others)}', file=sys.stderr)

    written, refused = common.write(country, source_name, stage, keep)
    return written, refused, collisions
