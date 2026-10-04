#!/bin/sh
# docker compose for the production stack, run on the server from /srv/hkv: scripts/prod.sh ps | logs -f api | run --rm updater
set -eu
cd "$(dirname "$0")/.."
exec docker compose -f infra/compose.prod.yaml --env-file .env "$@"
