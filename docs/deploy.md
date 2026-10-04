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
- **Secrets** are in `/srv/hkv/.env` (`POSTGRES_PASSWORD`, `SITE_DOMAIN`). They are not in git.

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
so **commit before deploying**.

## Scheduled jobs (systemd on the server, units in [infra/systemd](../infra/systemd))

| Timer | When (Asia/Jerusalem) | What |
|---|---|---|
| `hkv-update.timer` | daily 05:30; Mon–Wed 14:15–22:15 every 2 h; Tue–Thu 00:15 and 02:15 | `hkv update --days 30` in the `updater` container: reference data, the last 30 days of votes, topics, a `data_release` row |
| `hkv-backup.timer` | daily 04:30 | `pg_dump -Fc` to `/srv/hkv/backups`, keeping the last 14 (Hetzner server backups copy them off the server daily, 7 kept) |

```sh
systemctl list-timers 'hkv-*'
journalctl -u hkv-update -n 50        # last update run
sudo systemctl start hkv-update       # run an update now
scripts/prod.sh ps | logs -f api      # on the server, from /srv/hkv
```

Occasional manual jobs (run on the server from `/srv/hkv`; both are safe to repeat):

```sh
sudo systemd-run --unit=hkv-names --uid=deploy --gid=deploy --working-directory=/srv/hkv /srv/hkv/scripts/prod.sh run --rm updater hkv names
sudo systemd-run --unit=hkv-topics --uid=deploy --gid=deploy --working-directory=/srv/hkv /srv/hkv/scripts/prod.sh run --rm updater hkv topics --official
```

- `hkv names` refreshes official faction names for the current Knesset and fills missing MK photo URLs (~10 min). New MKs get names and photos in every regular update; curated faction names (incl. Hebrew short names) are applied on every update.
- `hkv topics --official` reloads the official law classification (~3 min). Bills voted in the update window are refreshed automatically.

Web pages cache API responses for 10 minutes, so an update appears on the site within 10 minutes.

The site is served under `/ru`, `/en` and `/he`; any path without a language redirects there (cookie, then the browser's language, then Russian), so old links keep working.

## Alerts

A failing update or backup triggers `hkv-alert@<unit>` ([scripts/alert.sh](../scripts/alert.sh)). It logs to the journal and sends the last log lines to Telegram via @knessetvotes_bot (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` in `/srv/hkv/.env`). Tested end to end on 2026-10-04.

## Restore

```sh
scripts/prod.sh exec -T db pg_restore -U knesset -d knesset --clean --if-exists --no-owner /backups/hkv-YYYY-MM-DD.dump
```

## Still to do

- **Deploy only from green CI:** tests run on every push (GitHub Actions); `scripts/deploy.sh` does not check the result yet.
