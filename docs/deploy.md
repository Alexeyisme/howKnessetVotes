# Production: knessetvotes.org

One Hetzner Cloud server runs the whole site.

- **Server:** `hkv-1`, CPX22 (2 vCPU, 4 GB), Helsinki, Ubuntu 24.04, address <hkv-1 address>.
- **Stack:** [infra/compose.prod.yaml](../infra/compose.prod.yaml) runs four services:
  - `db` (Postgres 17);
  - `api` (FastAPI; runs migrations on start);
  - `web` (Next.js);
  - `caddy` (HTTPS with automatic Let's Encrypt certificates; `/api/*`, `/docs` and `/openapi.json`
    go to the API, everything else goes to the web app).
- **Code** lives in `/srv/hkv` and is owned by the `deploy` user.
- **Secrets** are in `/srv/hkv/.env` (`POSTGRES_PASSWORD`, `SITE_DOMAIN`, `TELEGRAM_*`, and `ANTHROPIC_API_KEY` for the title and bill-summary translations — with it set, every `hkv update` translates the titles and official summaries that are new since the last run with `HKV_TRANSLATE_MODEL`, default Haiku 4.5, into `HKV_TRANSLATE_LANGS` (default `en,ru,ar` since 2026-10-07; it was `en,ru` before) and makes no request when nothing is new; the backlog was loaded once with `hkv translate --lang en,ru` on 2026-10-05; titles that failed the checks are retried only with `hkv translate --retry-failed`). One update translates at most `HKV_UPDATE_TRANSLATE_LIMIT` (60) texts per language and kind and describes at most `HKV_UPDATE_NOTES_LIMIT` (20) bills from their explanatory notes and summarises the debate and the reservations of at most `HKV_UPDATE_POSITIONS_LIMIT` (5) bills each (contested final votes), so a backlog cannot hold it past its 2-hour limit (it did on 2026-10-07, when Arabic was added); a backlog goes as one Message Batch with `hkv translate --batch` / `hkv notes --batch` / `hkv debate --batch` / `hkv reservations --batch` (manual job, see below), and the log warns when a run hit the cap. They are not in git.

## Access

- **Hetzner Cloud:** `hcloud` CLI with context `hkv`. The user creates the token in the console.
- **SSH:** `ssh -i ~/.ssh/hkv_hetzner deploy@<hkv-1 address>`. Root login is key-only and password
  login is off.
- **Firewall:** the Hetzner firewall `hkv-web` allows tcp 22, 80 and 443, and icmp.
- **DNS:** Cloudflare (registrar and DNS). The `A`/`AAAA` records for `knessetvotes.org` and `www`
  point at the server.

## Deploy

```sh
scripts/deploy.sh   # rsync of committed files, then docker compose up -d --build on the server
```

The repo is private. The server holds no GitHub credentials and gets only the files that git tracks,
so **commit before deploying**. Files that are no longer tracked are removed from the server's code directories
(`apps src db infra scripts tests docs`); `.env`, `backups/` and everything else there is left alone.

A deploy does not wait for CI; check the GitHub Actions run first (`gh run list --limit 1`).

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
e.g. `ssh -i ~/.ssh/hkv_hetzner root@<hkv-1 address>`; all are safe to repeat):

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

## Restore

```sh
scripts/prod.sh exec -T db pg_restore -U knesset -d knesset --clean --if-exists --no-owner /backups/hkv-YYYY-MM-DD.dump
```

## Still to do

- **Deploy only from green CI:** tests run on every push (GitHub Actions); `scripts/deploy.sh` does not check the result yet.
- **26th Knesset (2026-11-10):** new factions need curated names in `factions.toml` and links in `parties.toml`; run `hkv names` once the Knesset website lists the new MKs (roadmap O7).
