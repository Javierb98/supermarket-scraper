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
# Now it stops at the first failure, says which step failed, and leaves the
# push to decide for itself whether there is anything worth sending.

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

source venv/bin/activate

step "scrape"    python main.py
step "normalise" python pipeline/normalize.py
step "average"   python pipeline/market_average.py
step "push"      bash "${SCRIPT_DIR}/push_to_droplet.sh"

echo
echo "=== run finished $(date -Is) ==="
