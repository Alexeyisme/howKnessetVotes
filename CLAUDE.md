# howKnessetVotes — agent onboarding

Public site + REST API: how Knesset factions and individual MKs voted, by name, with the faction each MK
belonged to *on the vote date* and a link to the official source for every number.
Live at **https://knessetvotes.org** (API docs at `/docs`). Private repo `Alexeyisme/howKnessetVotes`.

The owner writes in Russian or English — answer in the language of the message. Docs: `README.md` and
`docs/architecture.md` are in Russian; `docs/roadmap.md`, `docs/deploy.md` and code comments are in English.

## Read first

1. `docs/roadmap.md` — where we are, what is done, what is next (tracks U*/L*/D*/O*, per-phase status sections).
2. `README.md` — commands, data load, API endpoints, web pages.
3. `docs/deploy.md` — production server, deploy, timers, manual jobs, restore.
4. `docs/architecture.md` — the original design spec (target system; the roadmap says what is actually built).
5. `docs/audit/source-audit.md` — what the official sources contain and how complete they are.

## Layout

| Path | What |
|---|---|
| `db/migrations/NNNN_*.sql`, `db/migrate.py` | Postgres 17 schema, applied in order |
| `src/hkv/sources/odata.py` | Knesset OData v4 client (paced, raw pages saved to `data/raw/`) |
| `src/hkv/ingest/` | `loader`/`mapping` (v4 → DB), `backfill` (parallel history), `legacy` (old Votes.svc: official totals ≤ 2021-07), `update` (daily job), `verify` |
| `src/hkv/names/` + `curated/*.toml` | MK/faction names in he/en/ru/ar, photos, parties (`parties.toml`), faction short names (`factions.toml`) |
| `src/hkv/topics/` | topic taxonomy, rule-based + official law classification |
| `src/hkv/translate/` | machine translation of bill/vote titles (Claude API, glossary, checks); `text_translation` keyed by SHA-256 of the Hebrew |
| `src/hkv/coalition/` + `overrides.toml` | governments and coalition/opposition per faction derived from government posts; `vote_bloc` |
| `src/hkv/api/` | FastAPI: `app.py` (votes), `entities.py` (members, factions, parties, governments, bills, compare), `topics.py`, `names.py` (`?lang=` display names and titles), `suggestions.py` (visitor corrections), `common.py` |
| `src/hkv/cli.py` | `hkv` command: ingest, backfill, legacy, update, initiators, topics, names, coalition, verify, status |
| `apps/web/` | Next.js 16 site (see below); has its own `CLAUDE.md`/`AGENTS.md` |
| `tests/` | pytest; each test gets a fresh migrated throwaway database |
| `infra/` | `compose.yaml` (local DB), `compose.prod.yaml`, `Caddyfile`, `systemd/` units |
| `scripts/` | `deploy.sh`, `prod.sh` (compose wrapper on the server), `backup.sh`, `alert.sh` |
| `audit/` | one-off source audit scripts (stdlib only) |

## Run locally

```sh
docker compose -f infra/compose.yaml up -d --wait     # Postgres on localhost:5433 (knesset/knesset)
uv run db/migrate.py
uv run pytest -q                                      # needs the DB above
uv run hkv ingest --from 2025-01-01 --to 2025-03-31   # some data to look at
uv run uvicorn hkv.api.app:app --reload               # http://127.0.0.1:8000/docs
cd apps/web && npm run dev                            # http://localhost:3000 (HKV_API_URL defaults to 127.0.0.1:8000)
cd apps/web && npm run lint && npm run build          # what CI runs
```

CI (`.github/workflows/ci.yml`) runs pytest against Postgres plus web lint + build on every push.

## Rules for the data (do not break these)

- **Faction is resolved at the vote date**, never "current faction". Party ≠ faction: a faction is one list in one
  Knesset; a party spans Knessets (`party_faction`), and a joint list belongs to every member party.
- **Abstain, present-not-voting and no record are different things.** Never fold one into another.
- **Nothing from the source is silently dropped or fixed**: problems go to `data_issue`, every row points to its
  `source_snapshot`, source corrections keep the old version in `row_revision`.
- **Curated data needs evidence.** `coalition/overrides.toml` entries carry an `evidence` field; names in
  `curated/*.toml` must exist in every language (ru, en, ar; Hebrew is the official name).
- Statistics show numerator and denominator; no hidden assumptions (see architecture §10, methodology page).

## Conventions

- **Migrations are append-only.** Never edit an applied migration; add `NNNN_name.sql` and add it to the expected
  list in `tests/conftest.py`. The API container runs migrations on start in production.
- **Knesset OData is slow (~2 s per 100 rows).** Short loads take ≤ 5 parallel workers, but after ~1.5 h of
  heavy paging the WAF starts throttling with random HTTP 481 (retried with backoff in `odata.py`); use 1–2 workers
  for multi-hour history loads. Long loads are resumable (`hkv backfill` continues where it stopped; `hkv status` shows progress).
- **Web is Next.js 16, not the version you remember**: `middleware` is `src/proxy.ts`, routes live under
  `app/[lang]` and read the locale with `next/root-params`. Read `apps/web/node_modules/next/dist/docs/` before
  using an API you are unsure of.
- **i18n:** every UI string goes in `apps/web/src/i18n/dict/{ru,en,he,ar}.tsx` (the `Dict` type comes from `ru`, so
  a missing key in en/he fails the build). Long texts are in `i18n/content/`. Use `makeT(locale)` helpers for
  names, dates, numbers and hrefs and the `components/Link` wrapper (adds the locale prefix). Hebrew
  and Arabic are RTL — use logical CSS properties (`margin-inline-start`, not `margin-left`). Arabic is a beta (roadmap L10):
  its texts are machine-translated and unreviewed, and the methodology page says so (section `translation`).
- API display names: endpoints take `?lang=he|en|ru|ar` and fill `name`/`short`/`label` via the mixins in
  `api/names.py`; add new name-bearing models there rather than translating in the web app.
- Match the existing style: small modules, short docstrings explaining *why*, no frameworks beyond what is there
  (psycopg, FastAPI, plain CSS modules).
- Commit messages: `Area: what changed` summary line, optional bullet body. Commit or push only when asked.

## Production

- One Hetzner server (`hkv-1`, <hkv-1 address>) running Docker Compose: db, api, web, caddy, plus an `updater`
  container for jobs. SSH key `~/.ssh/hkv_hetzner`; user `deploy` (no passwordless sudo) — manual
  `systemd-run` jobs go over `ssh root@…`. Examples in `docs/deploy.md`.
- **Deploy = `scripts/deploy.sh`** after committing (it rsyncs tracked files only and deletes untracked files in
  the code dirs). Check CI first: `gh run list --limit 1`. Deploying changes the public site — confirm with the
  owner unless they asked for it.
- `hkv update` runs from systemd timers (daily + every 2 h on sitting days, plus a 10-minute `--quick` check during
  sittings; in a recess reference data is reloaded once a day); failures of the full update alert to Telegram.
- Secrets live only in `/srv/hkv/.env` on the server. Never print them, never ask the owner to paste tokens into
  chat — they enter credentials themselves (e.g. `hcloud context`).

## Known pitfalls

- Stale pages in `next dev`: the fetch cache is in `apps/web/.next/dev/cache/fetch-cache`; delete it and restart.
- The API's connection pool uses `dict_row` (`row["col"]`); check the row factory of the connection you are
  given before indexing rows by position.
- Coalition derivation (`hkv coalition`) is a full rebuild; rerun it after loading history or editing
  `overrides.toml`. The Norwegian-law extension applies only from 2015-01-01.
- The plenum has no quorum: low-turnout votes are real, not missing data (the vote page explains this).
- The Knesset is in recess until the 26th Knesset convenes on 2026-11-10 (roadmap O7: new term readiness).
- Since 2026-10-05 the Knesset blocks requests from outside Israel (redirect to `maintenance-page-geo`); updates
  reach it through an SSH tunnel to a $4 proxy server in Israel (Kamatera `hkv-il-proxy`, <il-proxy address>;
  `HKV_KNESSET_PROXY`, [docs/knesset-proxy.md](docs/knesset-proxy.md)).
