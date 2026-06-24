#!/usr/bin/env bash
# One-time dataset load for a fresh deployment.
#
# Runs scripts/load_mongodb.py INSIDE the running `api` container, which reads
# the transformed ndjson from DATA_DIR (mounted at /data/db_import) and bulk-
# loads MongoDB. It also seeds the core topics, the bootstrap admin user and
# the starter project.
#
# WARNING: load_mongodb.py DROPS the target database before loading. Only run
# this on a fresh deployment or when you deliberately want to reset the data.
#
# Usage (from the project root on the host, with the stack already up):
#   ./scripts/seed.sh

set -euo pipefail

COMPOSE_FILE="docker-compose.prod.yml"

echo "This will DROP and reload the '${MONGODB_DB:-acteu}' database."
read -r -p "Continue? [y/N] " reply
case "${reply}" in
    [yY][eE][sS]|[yY]) ;;
    *) echo "Aborted."; exit 1 ;;
esac

docker compose -f "${COMPOSE_FILE}" exec api python scripts/load_mongodb.py
echo "Done. Dataset loaded into MongoDB (persisted in the mongo_data volume)."
