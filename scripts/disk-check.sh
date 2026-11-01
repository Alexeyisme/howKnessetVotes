#!/bin/sh
# Disk space check (hkv-disk timer): fails above the limit, so hkv-alert@ sends the output below to Telegram.
# The disk filled up unnoticed on 2026-11-01 and Postgres stopped; at ~3 GB a day, 80% leaves several days to act.
set -u
limit="${1:-80}"
used=$(df --output=pcent / | tail -1 | tr -dc '0-9')
echo "disk / ${used}% used (limit ${limit}%): $(df -h --output=used,avail / | tail -1)"
[ "$used" -lt "$limit" ] && exit 0
docker system df 2>&1
du -sh /srv/hkv/backups 2>/dev/null
exit 1
