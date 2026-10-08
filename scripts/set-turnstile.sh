#!/bin/sh
# Store the Cloudflare Turnstile keys in /srv/hkv/.env on the server: scripts/set-turnstile.sh
# Asks for the site key and the secret key (the secret is not echoed). The keys travel over SSH stdin, never on a
# command line, so they stay out of shell history and the server's process list. Existing TURNSTILE_* lines are
# replaced, the rest of .env is kept, mode stays 600, and the previous file is kept as .env.bak. They take effect
# when the containers are recreated: the next scripts/deploy.sh.
set -eu
HOST="${HKV_HOST:-deploy@<hkv-1 address>}"
SSH="ssh -i ${HKV_SSH_KEY:-$HOME/.ssh/hkv_hetzner}"

valid() { printf '%s' "$1" | grep -Eq '^[A-Za-z0-9_-]{10,200}$'; }

printf 'Turnstile site key: '
read -r site
stty -echo 2>/dev/null || true
printf 'Turnstile secret key (hidden): '
read -r secret
stty echo 2>/dev/null || true
echo

valid "$site" || { echo "The site key does not look right (letters, digits, - and _ only)." >&2; exit 1; }
valid "$secret" || { echo "The secret key does not look right (letters, digits, - and _ only)." >&2; exit 1; }
[ "$site" != "$secret" ] || { echo "The site key and the secret key are the same: paste each one in its place." >&2; exit 1; }

printf '%s\n%s\n' "$site" "$secret" | $SSH "$HOST" '
  set -eu
  cd /srv/hkv
  read -r site
  read -r secret
  umask 077
  cp -p .env .env.bak
  { grep -v "^TURNSTILE_SITE_KEY=" .env | grep -v "^TURNSTILE_SECRET_KEY=" || true
    printf "TURNSTILE_SITE_KEY=%s\nTURNSTILE_SECRET_KEY=%s\n" "$site" "$secret"; } > .env.new
  chmod 600 .env.new
  mv .env.new .env
  echo "Saved in /srv/hkv/.env (previous version in .env.bak):"
  sed -n "s/^\(TURNSTILE_[A-Z_]*\)=\(.....\).*/  \1=\2…/p" .env
'
echo "They take effect with the next scripts/deploy.sh."
