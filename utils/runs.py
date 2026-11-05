"""
A record of every source's every run, and a check for the ones gone quiet.

The weekly log says what happened this week. It does not say that the
Canadian feed has not succeeded since September, because nothing reads
September's log. This table does, and `report` prints the sources whose last
success is older than their schedule allows — at the end of every run, where
it is seen.

    python -m utils.runs record <source> ok|failed [seconds]
    python -m utils.runs report
"""

import sys
from datetime import datetime, timedelta

from utils.db import get_connection

# How long each kind of source may go without a success before it is
# reported. Weekly scrapes get two missed weeks; monthly statistics are
# published late and irregularly, so they get two months.
CADENCE_DAYS = {
    'scrape:': 15,
    'feed:': 62,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS source_runs (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    source      VARCHAR(60)  NOT NULL,
    status      VARCHAR(10)  NOT NULL,
    seconds     INT          NULL,
    ran_at      DATETIME     NOT NULL,
    KEY ix_source_ran (source, ran_at)
) CHARACTER SET utf8mb4
"""


def record(source, status, seconds=None):
    conn = get_connection()
    try:
        with conn.cursor() as c:
            c.execute(SCHEMA)
            c.execute("INSERT INTO source_runs (source, status, seconds, ran_at) VALUES (%s, %s, %s, %s)",
                      (source[:60], status[:10], seconds, datetime.now()))
        conn.commit()
    finally:
        conn.close()


def report():
    """Print each source's last success; return the number that are overdue."""
    conn = get_connection()
    overdue = 0
    try:
        with conn.cursor() as c:
            c.execute(SCHEMA)
            c.execute("""
                SELECT source,
                       MAX(CASE WHEN status = 'ok' THEN ran_at END) AS last_ok,
                       MAX(ran_at) AS last_run
                FROM source_runs GROUP BY source ORDER BY source
            """)
            rows = c.fetchall()
        now = datetime.now()
        print('source health:')
        for r in rows:
            allowed = next((d for prefix, d in CADENCE_DAYS.items() if r['source'].startswith(prefix)), 15)
            late = r['last_ok'] is None or now - r['last_ok'] > timedelta(days=allowed)
            overdue += late
            last = r['last_ok'].strftime('%Y-%m-%d') if r['last_ok'] else 'never'
            print(f"  {'OVERDUE' if late else 'ok':8} {r['source']:<28} last success {last}")
    finally:
        conn.close()
    return overdue


if __name__ == '__main__':
    if len(sys.argv) >= 4 and sys.argv[1] == 'record':
        record(sys.argv[2], sys.argv[3], int(sys.argv[4]) if len(sys.argv) > 4 else None)
    elif len(sys.argv) >= 2 and sys.argv[1] == 'report':
        sys.exit(1 if report() else 0)
    else:
        print(__doc__)
        sys.exit(2)
