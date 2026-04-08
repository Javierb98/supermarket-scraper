#!/bin/bash

# Load credentials from .env
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
set -a && source "${SCRIPT_DIR}/.env" && set +a

# Config
DROPLET_IP="134.209.250.206"
DROPLET_USER="deploy"
DROPLET_SSH_KEY="/home/node-admin/.ssh/id_ed25519_droplet"
DROPLET_DB="Evocultiva-org"
DROPLET_DB_USER="evocultiva_user"
DROPLET_DB_PASS="${DROPLET_DB_PASSWORD}"
LOCAL_DB_PASS="${DB_PASSWORD}"
TODAY=$(docker exec mysql mysql -u root -p"${LOCAL_DB_PASS}" scraper_db -se "SELECT MAX(snapshot_date) FROM market_average;" 2>/dev/null)
EXPORT_FILE="/tmp/market_average_${TODAY}.sql"

echo "[1/4] Exporting today's market_average snapshot (${TODAY})..."
docker exec mysql mysqldump \
  -u root \
  -p"${LOCAL_DB_PASS}" \
  --complete-insert \
  --where="snapshot_date = '${TODAY}'" \
  scraper_db market_average > "${EXPORT_FILE}"

echo "[2/4] Copying to droplet..."
scp -i "${DROPLET_SSH_KEY}" "${EXPORT_FILE}" ${DROPLET_USER}@${DROPLET_IP}:/tmp/

echo "[3/4] Inserting on droplet (appending to history)..."
ssh -i "${DROPLET_SSH_KEY}" ${DROPLET_USER}@${DROPLET_IP} << EOF
  mysql -u ${DROPLET_DB_USER} -p${DROPLET_DB_PASS} ${DROPLET_DB} < /tmp/$(basename ${EXPORT_FILE})
  rm /tmp/$(basename ${EXPORT_FILE})
EOF

echo "[4/4] Cleaning up local export..."
rm "${EXPORT_FILE}"

echo "Done! market_average snapshot for ${TODAY} pushed to droplet."
