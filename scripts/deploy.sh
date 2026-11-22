#!/bin/sh
# Deploy the committed tree to the server and restart what changed: scripts/deploy.sh
# Refuses unless CI passed for the commit; ends with a check that the site answers (scripts/smoke.sh).
# Copies tracked files only (the server holds no GitHub credentials and needs none), then removes files under
# the code directories that are no longer tracked (moved or deleted pages would otherwise break the build).
# .env, backups/ and anything outside those directories on the server are left alone.
set -eu
cd "$(dirname "$0")/.."
HOST="${HKV_HOST:-hkv}"   # an alias in ~/.ssh/config (docs/deploy.md): the address is not kept in the repo
SSH="ssh"

CODE_DIRS="apps src db infra scripts tests docs"

# An empty list would make the server delete every code file below; a dirty tree would ship uncommitted edits
files=$(git ls-files 2>/dev/null) || files=""
[ -n "$files" ] || { echo "No tracked files: run this from a git checkout." >&2; exit 1; }
[ -z "$(git status --porcelain --untracked-files=no)" ] || {
  echo "Uncommitted changes (the working tree is what gets copied): commit or stash them first." >&2; exit 1; }

# Only what CI has passed goes out: the commit must be pushed and its latest CI run green. HKV_SKIP_CI=1 deploys
# anyway (GitHub down, or an urgent fix whose run you have read yourself).
if [ "${HKV_SKIP_CI:-}" != 1 ]; then
  sha=$(git rev-parse HEAD)
  ci=$(gh run list --workflow CI --commit "$sha" --limit 1 --json status,conclusion --jq '.[0] // empty | "\(.status) \(.conclusion)"' 2>/dev/null) || ci=""
  [ "$ci" = "completed success" ] || {
    echo "CI is not green for $(git rev-parse --short HEAD) (${ci:-no run found: is the commit pushed?}). Wait for it (gh run watch), or set HKV_SKIP_CI=1." >&2; exit 1; }
fi

printf '%s\n' "$files" | rsync -az --files-from=- -e "$SSH" . "$HOST:/srv/hkv/"
printf '%s\n' "$files" | $SSH "$HOST" "cd /srv/hkv && sort > /tmp/hkv-tracked && find $CODE_DIRS -type f | sort | comm -23 - /tmp/hkv-tracked \
  | while read -r f; do echo \"removed \$f\"; rm -f \"\$f\"; done; find $CODE_DIRS -type d -empty -delete"
$SSH "$HOST" 'cd /srv/hkv && scripts/prod.sh up -d --build --remove-orphans && scripts/prod.sh ps'
# every build adds layers to Docker's build cache and nothing removes them (16 GB by 2026-11-01); 3 GB keeps the
# dependency layers, so the next build stays fast
$SSH "$HOST" 'docker builder prune -f --max-used-space 3gb | tail -1'
# the site answers and each kind of page is there; a failure here means: look now (scripts/prod.sh logs web api)
scripts/smoke.sh
