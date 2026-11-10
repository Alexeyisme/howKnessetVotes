#!/bin/sh
# Failure alert for a systemd unit (hkv-alert@.service): scripts/alert.sh <unit>
# Sends to Telegram when TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in /srv/hkv/.env (scripts/notify.sh);
# always logs to the journal.
set -u
cd "$(dirname "$0")/.."
unit="${1:-unknown}"
tail=$(journalctl -u "$unit" -n 15 --no-pager -o cat 2>/dev/null | tail -c 3000)
echo "ALERT: $unit failed"
scripts/notify.sh "knessetvotes.org: $unit failed on $(hostname) at $(date '+%Y-%m-%d %H:%M %Z')

$tail"
