"""
Small helpers shared by the United Kingdom and Ireland feeds
(defra_wholesale, ons_shopping, cso_ie).

clear_national() exists because market_average's unique key includes
`region`, and MySQL never treats two NULLs as equal: a national figure
(region NULL) written twice is two rows, not one updated row. Until
common.write() handles that itself, these feeds remove their own national
rows for the periods they are about to write, so a re-run replaces rather
than duplicates. It touches only rows with this country, this source_name
and these snapshot dates.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.db import get_connection, ensure_market_average_schema


def clear_national(country, source_name, stage, snapshots):
    snapshots = sorted(set(snapshots))
    if not snapshots:
        return 0
    conn = get_connection()
    try:
        ensure_market_average_schema(conn)
        with conn.cursor() as c:
            marks = ', '.join(['%s'] * len(snapshots))
            n = c.execute(
                f"DELETE FROM market_average WHERE country = %s AND source_name = %s "
                f"AND price_stage = %s AND region IS NULL AND snapshot_date IN ({marks})",
                [country.upper(), source_name[:120], stage] + snapshots,
            )
        conn.commit()
        return n
    finally:
        conn.close()


def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs)
