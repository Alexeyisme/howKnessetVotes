#!/bin/bash
# Load test at rising request rates (docs/deploy.md#capacity): infra/loadtest/run.sh MODE "RATES..."
#   e.g. infra/loadtest/run.sh hot "20 40 60 80 120"; MODE is hot, tail or mix (load.js).
# Each rate: api, web, web-2 and cache restarted (cold processes, empty cache), 40 s of k6 at that constant rate, then
# 20 s at 10 req/s to see whether the site recovers. Stops climbing once p95 > 5 s or > 5% of requests fail.
# Env: CPUS (default "0,1", the containers' CPU set), API_WORKERS (2), LT_DB (database name, hkvlt). Never point this
# at the production site.
set -eu
cd "$(dirname "$0")"
MODE=$1; RATES=$2; mkdir -p results
COMPOSE="docker compose -p hkvlt -f compose.yaml"

# production's site block on :80 (no TLS, no stats/www hosts)
python3 - <<'PY'
src = open("../Caddyfile").read()
site, end = src.index("{$SITE_DOMAIN} {"), src.index("# Umami dashboard")
open(".Caddyfile", "w").write(src[:site].replace("{$SITE_DOMAIN}", "") + ":80" + src[site + len("{$SITE_DOMAIN}"):end])
PY
$COMPOSE build api web >/dev/null   # before `up`: web-2 uses the image that web builds
$COMPOSE up -d >/dev/null

summary() {  # summary FILE LABEL
  python3 - "$1" "$2" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))["metrics"]; d = m["http_req_duration"]; n = m["http_reqs"]["count"]; f = m["checks"]["fails"]
err = lambda k: m.get(k, {}).get("count", 0)
print(f"{sys.argv[2]:>18} | done {m['http_reqs']['rate']:6.1f}/s | p50 {d['med']:6.0f} ms p95 {d['p(95)']:6.0f} p99 {d['p(99)']:6.0f}"
      f" | failed {100 * f / max(n, 1):5.1f}% (timeout {err('err_timeout')}, 5xx {err('err_5xx')})")
sys.exit(1 if d["p(95)"] > 5000 or f > 0.05 * n else 0)
PY
}

echo "== $MODE (CPUs ${CPUS:-0,1})"
for R in $RATES; do
  $COMPOSE up -d --force-recreate api web web-2 cache >/dev/null 2>&1
  until curl -sf -o /dev/null localhost:8088/ru/topics; do sleep 1; done
  k6 run -q -e MODE="$MODE" -e RATE="$R" -e DUR=40s -e SEED="$R" --summary-export "results/$MODE-$R.json" load.js >/dev/null 2>&1 || true
  over=0; summary "results/$MODE-$R.json" "$R req/s" || over=1
  k6 run -q -e MODE="$MODE" -e RATE=10 -e DUR=20s -e SEED=99 --summary-export "results/$MODE-$R-after.json" load.js >/dev/null 2>&1 || true
  summary "results/$MODE-$R-after.json" "then 10 req/s" || true
  [ $over = 1 ] && break
done
