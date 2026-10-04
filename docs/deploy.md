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
| `hkv-backup.timer` | daily 04:30 | `pg_dump -Fc` to `/srv/hkv/backups`, keeping the last 14 |

```sh
systemctl list-timers 'hkv-*'
journalctl -u hkv-update -n 50        # last update run
sudo systemctl start hkv-update       # run an update now
scripts/prod.sh ps | logs -f api      # on the server, from /srv/hkv
```

Web pages cache API responses for 10 minutes, so an update appears on the site within 10 minutes.

## Restore

```sh
scripts/prod.sh exec -T db pg_restore -U knesset -d knesset --clean --if-exists --no-owner /backups/hkv-YYYY-MM-DD.dump
```

## Still to do

- **Off-server backups:** backups exist only on the server itself. Options are a Hetzner Storage Box
  or Hetzner's own server backups, each a few euros a month.
- **Failure alerts** for the update and backup timers (Telegram or email). Until then, check
  `systemctl list-timers` and the "data as of" date in the site footer.
- **CI:** run the tests on every push, before deploying.
