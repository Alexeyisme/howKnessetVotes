#!/bin/sh
# Deploy the committed tree to the server and restart what changed: scripts/deploy.sh
# Copies tracked files only (the repo is private, so the server holds no GitHub credentials);
# .env and backups/ on the server are left alone.
set -eu
cd "$(dirname "$0")/.."
HOST="${HKV_HOST:-deploy@<hkv-1 address>}"
SSH="ssh -i ${HKV_SSH_KEY:-$HOME/.ssh/hkv_hetzner}"

git ls-files | rsync -az --files-from=- -e "$SSH" . "$HOST:/srv/hkv/"
$SSH "$HOST" 'cd /srv/hkv && scripts/prod.sh up -d --build --remove-orphans && scripts/prod.sh ps'
