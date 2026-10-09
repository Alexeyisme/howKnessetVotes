#!/bin/sh
# Give the contact form's per-visitor hash its salt on the server: scripts/set-ip-salt.sh
# Without HKV_IP_SALT the stored hash is sha256 of the IP and the day, which anyone can reverse by trying every IPv4
# address. The salt is generated on the server and never printed or sent over the network. If .env has no salt yet,
# it is added (the previous file is kept as .env.bak, mode stays 600), only the api container is recreated, and the
# unsalted hashes already stored in translation_suggestion are replaced (they serve only the one-day rate limit, so
# today's limit starts over). Safe to repeat: an existing salt is kept and nothing else is done.
set -eu
HOST="${HKV_HOST:-hkv}"   # an alias in ~/.ssh/config (docs/deploy.md): the address is not kept in the repo

# the script travels on stdin, so every docker command below reads /dev/null rather than the rest of it
ssh "$HOST" sh -s <<'REMOTE'
set -eu
cd /srv/hkv
if grep -q '^HKV_IP_SALT=.' .env; then
  echo "HKV_IP_SALT is already set in /srv/hkv/.env: nothing to do."
  exit 0
fi

umask 077
cp -p .env .env.bak
{ grep -v '^HKV_IP_SALT=' .env || true
  printf 'HKV_IP_SALT=%s\n' "$(od -An -tx1 -N32 /dev/urandom | tr -d ' \n')"; } > .env.new
chmod 600 .env.new
mv .env.new .env
echo "Salt added to /srv/hkv/.env (previous version in .env.bak)."

scripts/prod.sh up -d --no-deps api </dev/null
printf 'Waiting for the API to become healthy'
api=$(scripts/prod.sh ps -q api </dev/null)
for i in $(seq 60); do
  [ "$(docker inspect -f '{{.State.Health.Status}}' "$api")" = healthy ] && break
  printf .; sleep 2
done
echo
[ "$(docker inspect -f '{{.State.Health.Status}}' "$api")" = healthy ] || { echo "The API is not healthy: scripts/prod.sh logs api" >&2; exit 1; }
scripts/prod.sh exec -T api sh -c 'test -n "$HKV_IP_SALT"' </dev/null \
  || { echo "The API container has no HKV_IP_SALT: check infra/compose.prod.yaml" >&2; exit 1; }
echo "The API container has the salt."

echo "Replacing the unsalted hashes stored before the salt:"
scripts/prod.sh exec -T db psql -U knesset -d knesset -v ON_ERROR_STOP=1 \
  -c "UPDATE translation_suggestion SET ip_hash = 'unsalted, cleared' WHERE created_at < now()" </dev/null
REMOTE
