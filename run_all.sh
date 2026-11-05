#!/usr/bin/env bash
#
# The monthly run: scrape, normalise, average, push.
#
# Every step used to run whether or not the one before it worked, so a failed
# scrape still normalised nothing, averaged nothing, and pushed it — and the
# script said "Done!". That is how five months went by with the website
# serving April's prices: nothing ever returned a non-zero exit code to
# anybody who was listening.
#
# Now the steps everything depends on (normalise, average, push) stop the run
# when they fail. Sources do not: each is tried, recorded, and reported at
# the end, so one failing shop or office costs only its own figures.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "${SCRIPT_DIR}"

LOG_DIR="${SCRIPT_DIR}/logs"
mkdir -p "${LOG_DIR}"
LOG="${LOG_DIR}/run-$(date +%Y-%m-%d).log"

# Everything from here on is written to the log as well as the screen, so a
# run started by a timer leaves something to read afterwards.
exec > >(tee -a "${LOG}") 2>&1

echo "=== run started $(date -Is) ==="

# A run takes a while. If the timer fires again while one is still going —
# which happens after a reboot catches up a missed run — the second should
# wait rather than fight the first over the database.
exec 9>"${SCRIPT_DIR}/.run.lock"
if ! flock -n 9; then
    echo "another run is in progress; leaving it to finish"
    exit 0
fi

# A step the rest depend on: if it fails, stop.
step() {
    local name="$1"; shift
    echo
    echo "--- ${name} ---"
    if ! "$@"; then
        echo "FAILED: ${name}" >&2
        echo "=== run failed $(date -Is) ===" >&2
        exit 1
    fi
}

# A source: if it fails, say so, record it, and carry on with the others.
# One shop behind a bot wall or one statistics office down for maintenance
# should not cost every other country its week.
SOFT_FAILURES=()
source_step() {
    local name="$1"; shift
    local started=$SECONDS
    echo
    echo "--- ${name} ---"
    if "$@"; then
        python -m utils.runs record "${name}" ok $((SECONDS - started)) || true
    else
        echo "FAILED (carrying on): ${name}" >&2
        python -m utils.runs record "${name}" failed $((SECONDS - started)) || true
        SOFT_FAILURES+=("${name}")
    fi
}

source venv/bin/activate

# Shops. main.py records each chain itself and carries on past a failure.
if ! python main.py; then
    SOFT_FAILURES+=("one or more shops")
fi

# Feeds: official statistics, published price lists and price collections.
# Before normalising, because some (heisse-preise.io) bring shelf rows that
# the normaliser and the averaging still have to turn into figures.
for feed in $(python -m feeds.registry); do
    source_step "feed:${feed}" python "feeds/${feed}.py"
done

step "normalise" python pipeline/normalize.py
step "average"   python pipeline/market_average.py


step "push"      bash "${SCRIPT_DIR}/push_to_droplet.sh"

echo
python pipeline/normalize.py --report || true
echo
python -m utils.runs report || true

echo
if [[ ${#SOFT_FAILURES[@]} -gt 0 ]]; then
    echo "=== run finished with failures: ${SOFT_FAILURES[*]} — $(date -Is) ===" >&2
    exit 1
fi
echo "=== run finished $(date -Is) ==="
