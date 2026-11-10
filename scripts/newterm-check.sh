#!/bin/sh
# New Knesset watch (docs/new-term.md, hkv-newterm.timer): a Telegram message when the newest Knesset reaches a new
# stage (`hkv newterm --state`: the source publishes its MKs and factions; a government of its own is sworn in), with
# the `hkv newterm` report of what is left by hand. Silent while nothing changes.
set -eu
cd "$(dirname "$0")/.."
file=state/newterm            # outside the code directories that scripts/deploy.sh cleans
now=$(scripts/prod.sh run --rm updater hkv newterm --state 2>/dev/null)
[ -n "$now" ] || { echo "hkv newterm printed nothing" >&2; exit 1; }
last=$(cat "$file" 2>/dev/null || true)
if [ "$now" = "$last" ]; then echo "unchanged: $now"; exit 0; fi
# the first run only records the state, unless there is already something to act on
case "$last$now" in
  *"waiting for the source") ;;
  *) report=$(scripts/prod.sh run --rm updater hkv newterm 2>/dev/null | head -c 3200)
     scripts/notify.sh "knessetvotes.org: $now${last:+ (was: $last)}. What is left by hand (docs/new-term.md):

$report" ;;
esac
mkdir -p state && printf '%s\n' "$now" > "$file"
