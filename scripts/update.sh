#!/bin/sh
# Daily update entry point for cron/launchd. Exit code != 0 means the update failed (see logs/update.log).
set -eu
cd "$(dirname "$0")/.."
export PATH="$HOME/.local/bin:/usr/local/bin:/opt/homebrew/bin:$PATH"
exec uv run hkv update --days "${HKV_UPDATE_DAYS:-30}"
