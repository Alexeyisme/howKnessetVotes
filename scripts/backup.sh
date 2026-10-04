#!/bin/sh
# Nightly database dump on the server (hkv-backup timer). Keeps the last 14 dumps in /srv/hkv/backups.
set -eu
cd "$(dirname "$0")/.."
name="hkv-$(date +%Y-%m-%d).dump"
scripts/prod.sh exec -T db pg_dump -U knesset -Fc -f "/backups/$name.tmp" knesset
mv "backups/$name.tmp" "backups/$name"
ls -1t backups/hkv-*.dump | tail -n +15 | xargs -r rm --
echo "backup ok: $name ($(du -h "backups/$name" | cut -f1))"
