#!/usr/bin/env bash
#
# Send the newest market_average snapshot to the droplet.
#
# What went wrong before, and what each fix is for:
#
#   The snapshot date came from a query whose failure was invisible. An empty
#   result made the WHERE clause `snapshot_date = ''`, which dumped no rows,
#   and the script reported success for pushing nothing.
#
#   The dump named every column including region. The droplet had no region
#   column, so MySQL rejected the whole import — and nothing checked, because
#   the exit code of a heredoc'd ssh session was never looked at.
#
#   One failed scp meant the month was simply missed. There was no retry, and
#   no record of what had actually been delivered, so the next run started
#   again on a new snapshot and the gap was permanent.
#
# So: refuse to push nothing, use INSERT IGNORE so a repeat is harmless,
# retry, verify the rows arrived by counting them on the far side, and keep
# a note of the last snapshot that was confirmed — which is what lets a run
# after a power cut send the one that was missed.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set -a && source "${SCRIPT_DIR}/.env" && set +a

DROPLET_IP="${DROPLET_IP:-134.209.250.206}"
DROPLET_USER="${DROPLET_USER:-deploy}"
DROPLET_SSH_KEY="${DROPLET_SSH_KEY:-/home/node-admin/.ssh/id_ed25519_droplet}"
DROPLET_DB="${DROPLET_DB:-Evocultiva-org}"
DROPLET_DB_USER="${DROPLET_DB_USER:-evocultiva_user}"

STATE_FILE="${SCRIPT_DIR}/.last_delivered"
ATTEMPTS=5

SSH=(ssh -i "${DROPLET_SSH_KEY}" -o BatchMode=yes -o ConnectTimeout=20
     -o ServerAliveInterval=10 -o ServerAliveCountMax=3 "${DROPLET_USER}@${DROPLET_IP}")

die() { echo "push: $*" >&2; exit 1; }

# Passwords go through the environment, never the command line: anything on
# the command line is readable in `ps` by every other user on the machine.
local_mysql() { docker exec -e MYSQL_PWD="${DB_PASSWORD}" -i mysql mysql -u root -N -s scraper_db "$@"; }

# ── 1. what is there to send? ────────────────────────────────────────────
SNAPSHOT="$(local_mysql -e 'SELECT MAX(snapshot_date) FROM market_average' 2>/dev/null || true)"

[[ "${SNAPSHOT}" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] \
    || die "could not read a snapshot date from the local database (got '${SNAPSHOT}')"

ROWS="$(local_mysql -e "SELECT COUNT(*) FROM market_average WHERE snapshot_date = '${SNAPSHOT}'")"
[[ "${ROWS}" -gt 0 ]] || die "snapshot ${SNAPSHOT} has no rows; refusing to push an empty import"

# A snapshot already confirmed on the far side needs no resending. This is
# also how a catch-up run knows it has nothing to do.
if [[ -f "${STATE_FILE}" && "$(cat "${STATE_FILE}")" == "${SNAPSHOT}" ]]; then
    echo "snapshot ${SNAPSHOT} was already delivered; nothing to do"
    exit 0
fi

echo "pushing snapshot ${SNAPSHOT} (${ROWS} rows)"

EXPORT_FILE="/tmp/market_average_${SNAPSHOT}.sql"
REMOTE_FILE="/tmp/$(basename "${EXPORT_FILE}")"
trap 'rm -f "${EXPORT_FILE}"' EXIT

# --insert-ignore, so a retry after a half-finished import is safe rather
# than a duplicate-key failure. The droplet's unique key covers region.
docker exec -e MYSQL_PWD="${DB_PASSWORD}" mysql mysqldump \
    -u root \
    --complete-insert \
    --insert-ignore \
    --no-create-info \
    --skip-add-locks \
    --where="snapshot_date = '${SNAPSHOT}'" \
    scraper_db market_average > "${EXPORT_FILE}"

[[ -s "${EXPORT_FILE}" ]] || die "the dump came out empty"

# ── 2. deliver it, and keep trying ───────────────────────────────────────
deliver() {
    scp -i "${DROPLET_SSH_KEY}" -o BatchMode=yes -o ConnectTimeout=20 \
        "${EXPORT_FILE}" "${DROPLET_USER}@${DROPLET_IP}:${REMOTE_FILE}"

    # MYSQL_PWD is set inside the remote shell, so the password never appears
    # in the remote process list either.
    "${SSH[@]}" "MYSQL_PWD='${DROPLET_DB_PASSWORD}' mysql -u '${DROPLET_DB_USER}' '${DROPLET_DB}' < '${REMOTE_FILE}' && rm -f '${REMOTE_FILE}'"
}

confirm() {
    "${SSH[@]}" "MYSQL_PWD='${DROPLET_DB_PASSWORD}' mysql -u '${DROPLET_DB_USER}' -N -s '${DROPLET_DB}' -e \"SELECT COUNT(*) FROM market_average WHERE snapshot_date = '${SNAPSHOT}'\""
}

for attempt in $(seq 1 "${ATTEMPTS}"); do
    echo "  attempt ${attempt}/${ATTEMPTS}"

    if deliver; then
        # Delivered is not the same as arrived. Count the rows on the far
        # side: this is the check whose absence hid the region failure for
        # five months.
        LANDED="$(confirm || echo 0)"

        if [[ "${LANDED}" == "${ROWS}" ]]; then
            echo "${SNAPSHOT}" > "${STATE_FILE}"
            echo "confirmed: ${LANDED} rows for ${SNAPSHOT} are on the droplet"
            exit 0
        fi

        echo "  import did not land in full (droplet has ${LANDED} of ${ROWS})" >&2
    fi

    if [[ "${attempt}" -lt "${ATTEMPTS}" ]]; then
        BACKOFF=$(( attempt * 60 ))
        echo "  retrying in ${BACKOFF}s"
        sleep "${BACKOFF}"
    fi
done

# Left unrecorded on purpose: the next run will find the state file still
# pointing at an older snapshot and try this one again.
die "gave up after ${ATTEMPTS} attempts; snapshot ${SNAPSHOT} is NOT on the droplet"
