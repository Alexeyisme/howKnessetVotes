# Production: knessetvotes.org

One Hetzner Cloud server runs the whole site.

- **Server:** `hkv-1`, CPX32 (4 vCPU, 8 GB; resized from CPX22 on 2026-10-09 with `--keep-disk`, so the 80 GB disk allows going back), Helsinki, Ubuntu 24.04. Its address is not in the repo: it is in your `~/.ssh/config` (see Access) and in `hcloud server list`.
- **Stack:** [infra/compose.prod.yaml](../infra/compose.prod.yaml) runs these services:
  - `db` (Postgres 17);
  - `api` (FastAPI; runs migrations on start);
  - `web` and `web-2` (Next.js, the same image twice: a Node process renders on one core only);
  - `cache` (nginx: keeps each page's HTML for 60 s and spreads requests over `web` and `web-2`,
    [infra/nginx-cache.conf](../infra/nginx-cache.conf); see [Capacity](#capacity));
  - `umami` (page-view statistics, see [Statistics](#statistics-umami));
  - `caddy` (HTTPS with automatic Let's Encrypt certificates; `/api/*`, `/docs` and `/openapi.json`
    go to the API, `/u/script.js` and `/u/api/send` to Umami, `stats.knessetvotes.org` to the Umami dashboard,
    everything else goes to `cache` and on to the web app).
- **Code** lives in `/srv/hkv` and is owned by the `deploy` user.
- **Secrets** are in `/srv/hkv/.env` (`POSTGRES_PASSWORD`, `SITE_DOMAIN`, `TELEGRAM_*`, and `ANTHROPIC_API_KEY` for the title and bill-summary translations — with it set, every `hkv update` translates the titles and official summaries that are new since the last run with `HKV_TRANSLATE_MODEL`, default Haiku 4.5, into `HKV_TRANSLATE_LANGS` (default `en,ru,ar` since 2026-10-07; it was `en,ru` before) and makes no request when nothing is new; the backlog was loaded once with `hkv translate --lang en,ru` on 2026-10-05; titles that failed the checks are retried only with `hkv translate --retry-failed`). One update translates at most `HKV_UPDATE_TRANSLATE_LIMIT` (60) texts per language and kind and describes at most `HKV_UPDATE_NOTES_LIMIT` (20) bills from their explanatory notes and summarises the debate and the reservations of at most `HKV_UPDATE_POSITIONS_LIMIT` (5) bills each (contested final votes), so a backlog cannot hold it past its 2-hour limit (it did on 2026-10-07, when Arabic was added); a backlog goes as one Message Batch with `hkv translate --batch` / `hkv notes --batch` / `hkv debate --batch` / `hkv reservations --batch` (manual job, see below), and the log warns when a run hit the cap. They are not in git. The Cloudflare Turnstile keys for the contact form (`TURNSTILE_SITE_KEY`, `TURNSTILE_SECRET_KEY`) are set from your machine with [scripts/set-turnstile.sh](../scripts/set-turnstile.sh), which asks for them and writes them to `.env` over SSH. With both set, the form shows the widget and the API verifies its token; empty keys turn the check off. `HKV_IP_SALT` (any random string, e.g. `openssl rand -hex 32`) salts the per-visitor hash behind the form's daily limit, so stored hashes cannot be reversed by trying every IPv4 address; changing it only resets that day's counts. After changing `infra/Caddyfile`, restart Caddy (`scripts/prod.sh restart caddy`): the file is bind-mounted and rsync replaces it, so the running container keeps the old one.

## Access

- **Hetzner Cloud:** `hcloud` CLI with context `hkv`. The user creates the token in the console.
- **SSH:** `ssh hkv` (user `deploy`) and `ssh hkv-root`; the Israeli proxy server ([knesset-proxy.md](knesset-proxy.md)) is
  `ssh hkv-il`. Root login is key-only and password login is off. The aliases live in your `~/.ssh/config`, so
  server addresses stay out of this public repo:

  ```text
  Host hkv hkv-root
      HostName <hkv-1 address>
      IdentityFile ~/.ssh/hkv_hetzner
  Host hkv
      User deploy
  Host hkv-root
      User root
  Host hkv-il
      HostName <Israeli server address>
      User root
      IdentityFile ~/.ssh/hkv_hetzner
  ```
- **Firewall:** the Hetzner firewall `hkv-web` allows tcp 22, 80 and 443, and icmp.
- **DNS:** Cloudflare (registrar and DNS). The `A`/`AAAA` records for `knessetvotes.org` and `www`
  point at the server.

## Statistics (Umami)

Which pages people open, from where (referrer, country), in which language and on what device: the dashboard at
**https://stats.knessetvotes.org** (Umami 3, self-hosted). It sets no cookies and keeps no IP addresses (a visitor is a
salted hash that changes daily). Search terms show up as the `q=` query of `/search` pages. The tracker is first-party
(`/u/script.js`, page views to `/u/api/send`) and counts client-side navigation too. Your own visits: in the browser
console on knessetvotes.org run `localStorage.setItem("umami.disabled", 1)` to stop counting that browser.

Its tables are in a separate `umami` database of the same Postgres; the nightly backup covers only `knesset`, so
the statistics are not backed up (Hetzner server backups still copy the whole disk).

One-time setup (done once per server):

1. Cloudflare DNS: `A` record `stats` → the server address (same as `knessetvotes.org`), proxied (like `www`).
2. On the server, from `/srv/hkv`: `scripts/prod.sh exec db createdb -U knesset umami`, and add
   `UMAMI_APP_SECRET=$(openssl rand -hex 32)` to `.env`.
3. Deploy, then `scripts/prod.sh restart caddy` (new Caddyfile). Umami creates its tables on first start.
4. Open https://stats.knessetvotes.org, log in as `admin` / `umami` and **change the password at once**
   (Settings → Profile). Settings → Websites → Add: name `knessetvotes`, domain `knessetvotes.org`; copy its Website ID.
5. Add `UMAMI_WEBSITE_ID=<id>` to `.env` and `scripts/prod.sh up -d web`. Empty = no tracker on the site.

## Deploy

```sh
scripts/deploy.sh   # rsync of committed files, then docker compose up -d --build on the server
```

The server holds no GitHub credentials and gets only the files that git tracks (`ssh hkv`, see Access),
so **commit before deploying**. Files that are no longer tracked are removed from the server's code directories
(`apps src db infra scripts tests docs`); `.env`, `backups/` and everything else there is left alone.

A deploy does not wait for CI; check the GitHub Actions run first (`gh run list --limit 1`).

Without the `hkv` alias (a new machine): `ssh-add ~/.ssh/hkv_hetzner && HKV_HOST=deploy@<hkv-1 address> scripts/deploy.sh`.
After a change to `infra/Caddyfile`, also `scripts/prod.sh restart caddy`: the file is bind-mounted, and the running
container keeps the old one.

## Scheduled jobs (systemd on the server, units in [infra/systemd](../infra/systemd))

| Timer | When (Asia/Jerusalem) | What |
|---|---|---|
| `hkv-update.timer` | daily 05:30; Mon–Wed 14:15–22:15 every 2 h; Tue–Thu 00:15 and 02:15 | `hkv update --days 30` in the `updater` container: reference data, the last 30 days of votes, topics, a `data_release` row. In a recess (no vote for 14 days) reference data (nearly all of the ~130 Knesset requests) is reloaded only if the last load is over 20 h old, so in practice by the 05:30 run; if new votes appear it is reloaded and the votes read again |
| `hkv-update-quick.timer` | every 10 min, Mon–Wed 11:00–23:50 and Tue–Thu 00:00–02:50 | `hkv update --quick --days 1`: today's and yesterday's votes only, no reference data; if no vote, ballot or correction is new it stops (a few seconds), otherwise topics, names, coalition blocs, title translations and a release. A shared lock (`flock /run/lock/hkv-update.lock`) keeps it from overlapping the full update: the quick run is skipped, the full one waits. No failure alert (it would repeat every 10 minutes); the full update alerts |
| `hkv-backup.timer` | daily 04:30 | `pg_dump -Fc` to `/srv/hkv/backups`, keeping the last 14 (Hetzner server backups copy them off the server daily, 7 kept) |

**Knesset geo-block (from 2026-10-05):** the Knesset redirects requests from outside Israel to `www.knesset.gov.il/maintenance-page-geo`. The client reports it as `SourceBlocked`: the full update fails and alerts, the quick check logs a warning and exits. `HKV_KNESSET_PROXY=http://host:port` in `/srv/hkv/.env` sends requests to knesset.gov.il (only) through an HTTP proxy in Israel; empty = direct. It points at `hkv-il-tunnel.service`, an SSH tunnel to a small proxy server in Israel; setup, checks and troubleshooting: [knesset-proxy.md](knesset-proxy.md). Check access from the server: `curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' https://www.knesset.gov.il/`.

Installing or changing units (as root): `cp /srv/hkv/infra/systemd/hkv-* /etc/systemd/system/ && systemctl daemon-reload && systemctl enable --now hkv-update.timer hkv-update-quick.timer hkv-backup.timer hkv-il-tunnel.service`.

```sh
systemctl list-timers 'hkv-*'
journalctl -u hkv-update -n 50        # last update run
sudo systemctl start hkv-update       # run an update now
scripts/prod.sh ps | logs -f api      # on the server, from /srv/hkv
```

Occasional manual jobs (run on the server from `/srv/hkv` as **root** — `deploy` has no passwordless sudo —
e.g. `ssh hkv-root`; all are safe to repeat):

```sh
sudo systemd-run --unit=hkv-names --uid=deploy --gid=deploy --working-directory=/srv/hkv /srv/hkv/scripts/prod.sh run --rm updater hkv names
sudo systemd-run --unit=hkv-topics --uid=deploy --gid=deploy --working-directory=/srv/hkv /srv/hkv/scripts/prod.sh run --rm updater hkv topics --official
sudo systemd-run --unit=hkv-coalition --uid=deploy --gid=deploy --working-directory=/srv/hkv /srv/hkv/scripts/prod.sh run --rm updater hkv coalition
```

- `hkv names` refreshes official faction names for the current Knesset and fills missing MK photo URLs (~10 min). New MKs get names and photos in every regular update; curated faction names (incl. Hebrew short names) are applied on every update. After adding a language (Arabic, 2026-10), run `hkv names --refresh` once so known MKs get it (~30 min).
- `hkv topics --official` reloads the official law classification (~3 min). Bills voted in the update window are refreshed automatically.
- `hkv coalition` reloads government posts and re-derives governments, coalition/opposition per faction and the per-vote blocs (~1 min). Every update does this too; run it after editing `src/hkv/coalition/overrides.toml` and deploying.

Bill texts (roadmap L7) — descriptions from explanatory notes, plenum debates and reservations of contested final votes,
then their translations. Each step sends its backlog as one Message Batch (half price; waits for the results, usually
within an hour) and is resumable; files are cached in the `raw` volume. Needs `ANTHROPIC_API_KEY` and the Knesset proxy:

```sh
sudo systemd-run --unit=hkv-l7 --uid=deploy --gid=deploy --working-directory=/srv/hkv sh -c "P=scripts/prod.sh; \
  \$P run --rm updater hkv notes --documents --batch; \$P run --rm updater hkv debate --batch; \
  \$P run --rm updater hkv reservations --batch; \$P run --rm updater hkv translate --batch"
```

Failures are `data_issue` rows (`explanation_failed`, `debate_failed`, `reservations_failed`) with the reason; `--retry-failed` retries them.
`hkv debate --redo --batch` summarises again the stored debates that were cut well below today's budget (1,300,000 characters, ~900k tokens) or were
written with the old one-list prompt and have no argument for one side; a debate is replaced only by a result that passes the checks.
`--bill ID` (repeatable) limits a run to those Knesset bills; with `--redo` it redoes their debates whatever they are (after a parser fix).
Run `hkv translate --kind positions` after it (or wait for the next `hkv update`).

Loading a historical period (as for D1, 2003–2016, done 2026-10-05). With 4 workers the Knesset WAF starts throttling (HTTP 481) after
~1.5 h; `odata.py` retries with backoff, but use `--workers 1` for multi-hour loads (~1.3 s per page, ~15 min per quarter). The load is
resumable: rerunning skips finished quarters. Logs go to the `raw` volume:

```sh
sudo systemd-run --unit=hkv-history --uid=deploy --gid=deploy --working-directory=/srv/hkv sh -c "P=scripts/prod.sh; \
  \$P run --rm updater hkv backfill --from 2003-10-01 --to 2016-10-30 --workers 1 --months 3 --log /data/raw/logs/backfill-history.log && \
  \$P run --rm updater hkv legacy --from 2003-10-01 --to 2016-10-30 --log /data/raw/logs/legacy-history.log && \
  \$P run --rm updater hkv initiators && \$P run --rm updater hkv topics --official && \$P run --rm updater hkv names && \
  \$P run --rm updater hkv coalition"
```

Take a backup first (`sudo systemctl start hkv-backup`).

Web pages cache API responses for 10 minutes, so an update appears on the site within 10 minutes.

The site is served under `/ru`, `/en` and `/he`; any path without a language redirects there (cookie, then the browser's language, then Russian), so old links keep working.

## Alerts

A failing update or backup triggers `hkv-alert@<unit>` ([scripts/alert.sh](../scripts/alert.sh)). It logs to the journal and sends the last log lines to Telegram via @knessetvotes_bot (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` in `/srv/hkv/.env`). Tested end to end on 2026-10-04. The same bot forwards every visitor correction and mistake report (`POST /api/v1/suggestions`, the `/suggest` page) as it arrives; the API container gets the two variables from `.env`, and the rows stay in `translation_suggestion` (status `open` until reviewed).

## Capacity

Load tests on 2026-10-09, on the CPX22 (2 vCPU, 4 GB) the server had before that day's resize: the production stack on a local copy of the database (half the production votes, no
translations), every container pinned to two CPUs and 4 GB of memory, as on `hkv-1`; k6 at a constant request rate for
40 s per step, starting each step from cold processes and an empty cache, then 20 s at 10 requests/s to check that the
site recovers. Three kinds of traffic:

- **hot:** a link shared widely: the home page, the vote lists, a few laws and parties, the quiz;
- **tail:** crawlers: any vote, member, bill or faction page in any language, almost never cached;
- **mix:** half of each.

| Traffic | Before (one Next.js process, no cache) | After |
|---|---|---|
| hot | fine up to 20 req/s; p95 2.6 s at 30; saturated at ~38 | 0 errors up to 80 req/s (median 5 ms); 1.6% errors at 120; with the cache warm, 300 req/s at p95 24 ms |
| tail | fine up to 20 req/s; saturated at ~25 | the same: fine up to 25 req/s, saturated at ~27 |
| mix | fine up to 20 req/s; saturated at ~28 | fine up to 30 req/s; at 40, 10% fast errors |
| after an overload | down for minutes: the API kept working through requests nobody waited for | back within seconds at every step |

What changed:

- `cache` (nginx) keeps every page's HTML for 60 s, sends one request per page to Next.js while the others wait, and
  serves the stale copy while it refreshes. Pages carry no Set-Cookie for this (the language cookie is set in the
  browser, `components/LangCookie.tsx`). It never marks a Next.js server down and does not retry a slow render on the
  other one: either made an overload worse in the tests.
- `web-2`: a second Next.js process, so a cold page's render can use the second core. Its effect was not measured on
  its own, and it does not raise the tail limit (below); with 2 GB of memory it made things worse (swapping).
- `--limit-concurrency 48` on the API: past that it answers 503 at once.
- `robots.txt` keeps crawlers off URL spaces without end (the correction form, search, paging and filters); the
  correction links are `nofollow` and not prefetched. These were ~8% of production requests on 2026-10-09, when
  crawlers made most of the traffic (~14 req/s).

**The limit for uncached pages is the CPU.** At 25 req/s of crawler traffic Postgres used about one of the two cores and
Next.js the other. Most of the database time is the member page's statistics (`GET /members/{id}`: 70 ms median,
180 ms for a long-serving member, all of it the "against own faction" count recomputed over every ballot). A
precomputed per-vote faction tally would remove most of it. The server got 4 vCPUs the same day (not load-tested
yet), which should roughly double the limit.

### Rerunning the load tests

The kit is in [infra/loadtest](../infra/loadtest): the production services built from this checkout ([compose.yaml](../infra/loadtest/compose.yaml),
Caddy with production's site block on port 8088), a k6 script ([load.js](../infra/loadtest/load.js)) and a runner that
climbs the request rate ([run.sh](../infra/loadtest/run.sh)). Needs Docker and k6 (`brew install k6`). **Never point it at
the production site.**

```sh
docker compose -f infra/compose.yaml up -d --wait          # the local database (container infra-db-1)
# a separate copy, so the dev database is left alone; then the current schema
docker exec infra-db-1 sh -c 'createdb -U knesset hkvlt && pg_dump -U knesset -Fc knesset | pg_restore -U knesset -d hkvlt --no-owner'
DATABASE_URL=postgresql://knesset:knesset@localhost:5433/hkvlt uv run db/migrate.py
uv run infra/loadtest/pools.py postgresql://knesset:knesset@localhost:5433/hkvlt   # IDs for load.js
docker update --cpuset-cpus 0,1 infra-db-1                 # the database shares the server's CPUs too
infra/loadtest/run.sh hot "20 40 60 80 120"
infra/loadtest/run.sh tail "10 20 25 30"
infra/loadtest/run.sh mix "20 30 40 60"
docker compose -p hkvlt -f infra/loadtest/compose.yaml down; docker update --cpuset-cpus 0-4 infra-db-1   # afterwards
```

To match the server, give Docker Desktop its memory (Settings → Resources; with 2 GB the tests swapped and the numbers
were meaningless) and set `CPUS` to its vCPUs, e.g. `CPUS=0-3 API_WORKERS=4` for the CPX32. Each step prints the
achieved rate, latency percentiles and failures split into timeouts and 5xx, then the same for 20 s at 10 req/s: if
that second line fails, the site did not recover. Results are kept as JSON in `infra/loadtest/results/`. The 2026-10-09
copy had half the production votes and no translations, so pages were a little lighter than in production.

### Crawlers

Crawlers made most of the traffic on 2026-10-09: of 222,000 requests in five hours, **ShapBot** sent 126,000 (57%,
~7 req/s day and night) from 9 Google Cloud addresses, one of them half of it, up to 82 requests in 10 s; 80% vote
pages. Its user agent (`…; compatible; ShapBot/0.1.0`) gives no contact or documentation. Recommended Cloudflare rule
(dashboard → knessetvotes.org → Security → Security rules → Rate limiting rules → Create rule):

| Field | Value |
|---|---|
| Rule name | `ShapBot rate limit` |
| If incoming requests match | `(http.user_agent contains "ShapBot")` |
| With the same characteristics | IP |
| When rate exceeds | 5 requests per 10 seconds |
| Then take action | Block (HTTP 429), for 10 seconds (the Free plan's only duration) |

That holds each address to 0.5 req/s (all of them to at most ~4.5 req/s), still ~40,000 pages a day per address. If
the Free plan's rule editor does not offer the user agent field, a custom rule (Security rules → Custom rules) with the
same expression and the action Block stops it entirely. To see who is crawling, count user agents in Caddy's log:

```sh
ssh hkv 'docker logs --since 1h hkv-caddy-1 2>&1' | grep -o '"User-Agent":\["[^"]*' | sort | uniq -c | sort -rn | head
```

### Resizing the server

Done on 2026-10-09, CPX22 → CPX32 (about 80 seconds offline). Check first that no update or backup is running
(`systemctl is-active hkv-update hkv-backup` on the server), then from your Mac:

```sh
hcloud server shutdown hkv-1                        # wait until `hcloud server describe hkv-1` says off
hcloud server change-type hkv-1 cpx32 --keep-disk   # --keep-disk: the disk stays 80 GB, so a smaller type stays possible
hcloud server poweron hkv-1
```

Docker, the containers (`restart: unless-stopped`), the timers and the tunnel to the Israeli server start on their own.
Check the services (`scripts/prod.sh ps`), `systemctl is-active hkv-il-tunnel`, and one Knesset request through the
proxy (as in [knesset-proxy.md](knesset-proxy.md)). Then fit [compose.prod.yaml](../infra/compose.prod.yaml) to the new
size: API workers (one per vCPU) and the Postgres memory settings, and deploy.

## Restore

```sh
scripts/prod.sh exec -T db pg_restore -U knesset -d knesset --clean --if-exists --no-owner /backups/hkv-YYYY-MM-DD.dump
```

## Still to do

- **Capacity:** set the ShapBot rule in Cloudflare ([Crawlers](#crawlers)); load-test the CPX32 (`CPUS=0-3 API_WORKERS=4`,
  Docker with 8 GB); precompute a per-vote faction tally so member pages stop recounting every ballot (most of the
  database time on uncached pages).
- **Deploy only from green CI:** tests run on every push (GitHub Actions); `scripts/deploy.sh` does not check the result yet.
- **26th Knesset (2026-11-10):** new factions need curated names in `factions.toml` and links in `parties.toml`; run `hkv names` once the Knesset website lists the new MKs (roadmap O7).
