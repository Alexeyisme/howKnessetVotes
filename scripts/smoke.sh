#!/bin/sh
# Is the site up after a deploy? scripts/smoke.sh [https://knessetvotes.org]
# Waits for the API (the containers were just restarted), then asks for one page of each kind and compares the HTTP
# status. Read-only; fails on the first surprise, so deploy.sh ends with an error instead of a silently broken site.
set -eu
SITE="${1:-${HKV_SITE:-https://knessetvotes.org}}"

status() { curl -s -o /dev/null -m 30 -w '%{http_code}' "$SITE$1" || true; }

i=0
until [ "$(status /api/v1/status)" = 200 ]; do
  i=$((i + 1))
  [ "$i" -lt 30 ] || { echo "smoke: $SITE/api/v1/status did not answer 200 in 2.5 minutes" >&2; exit 1; }
  sleep 5
done

# path, expected status. The web container answers a little after the API: each page gets a few tries.
failed=0
while read -r path want; do
  n=0
  got=$(status "$path")
  while [ "$got" != "$want" ] && [ "$n" -lt 6 ]; do n=$((n + 1)); sleep 5; got=$(status "$path"); done
  if [ "$got" = "$want" ]; then echo "ok   $got $path"; else echo "FAIL $got (expected $want) $path" >&2; failed=1; fi
done <<PAGES
/en 200
/ru/votes 200
/he/members?term=16 200
/ar/bills 200
/en/parties/likud 200
/en/compare 200
/en/topics 200
/en/match 200
/en/search?q=tax 200
/en/about/methodology 200
/en/no-such-page 404
/api/v1/votes?limit=1 200
/docs 200
PAGES
[ "$failed" = 0 ] || { echo "smoke: the site is not healthy" >&2; exit 1; }
