#!/bin/sh
# Send a message to the owner's Telegram: scripts/notify.sh "<text>"
# Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from /srv/hkv/.env; without them it only prints. Always prints the text,
# so the message is in the journal of the unit that sent it.
set -u
cd "$(dirname "$0")/.."
text="$1"
printf '%s\n' "$text"
TELEGRAM_BOT_TOKEN=$(sed -n 's/^TELEGRAM_BOT_TOKEN=//p' .env 2>/dev/null)
TELEGRAM_CHAT_ID=$(sed -n 's/^TELEGRAM_CHAT_ID=//p' .env 2>/dev/null)
if [ -n "$TELEGRAM_BOT_TOKEN" ] && [ -n "$TELEGRAM_CHAT_ID" ]; then
  # the URL holds the token, so it goes to curl as config on stdin, not on the command line seen in `ps`
  printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$TELEGRAM_BOT_TOKEN" | curl -fsS -m 20 -K - \
    --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" --data-urlencode "text=$text" >/dev/null && echo "sent to Telegram"
else
  echo "Telegram not configured (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID in .env)"
fi
