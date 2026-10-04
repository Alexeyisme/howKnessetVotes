#!/bin/sh
# Failure alert for a systemd unit (hkv-alert@.service): scripts/alert.sh <unit>
# Sends to Telegram when TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in /srv/hkv/.env; always logs to the journal.
set -u
cd "$(dirname "$0")/.."
unit="${1:-unknown}"
tail=$(journalctl -u "$unit" -n 15 --no-pager -o cat 2>/dev/null | tail -c 3000)
text="knessetvotes.org: $unit failed on $(hostname) at $(date '+%Y-%m-%d %H:%M %Z')

$tail"
echo "ALERT: $unit failed"
TELEGRAM_BOT_TOKEN=$(sed -n 's/^TELEGRAM_BOT_TOKEN=//p' .env 2>/dev/null)
TELEGRAM_CHAT_ID=$(sed -n 's/^TELEGRAM_CHAT_ID=//p' .env 2>/dev/null)
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
  curl -fsS -m 20 "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
    --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" --data-urlencode "text=$text" >/dev/null && echo "sent to Telegram"
else
  echo "Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env)"
fi
