# Roadmap after the MVP (2026-10-04)

The MVP covers 17,319 votes, 1.21M ballots, 3,647 bills, 299 MKs and 101 factions. It has pages for
members, factions, bills and topics, and Russian/Hebrew search. This plan covers what comes next, in
order:

1. clean Hebrew, English and Russian content;
2. automatic updates;
3. deployment to Hetzner;
4. a backlog of improvements.

Every fact below about a source was checked on 2026-10-04. The checks are listed in "Source research".

## 1. Trilingual content (he / en / ru)

Rule: every displayed text records where it came from. `origin` is one of:

- `knesset`: published by the Knesset;
- `wikidata`;
- `editor`: written or approved by a person;
- `machine`: an LLM translation that nobody has reviewed yet.

The UI marks machine text. Official text always wins over machine text. A change in the Hebrew
source puts its translation back into the queue.

### 1a. MK names — official, almost fully automatic

| Tier | Source | MKs (of 299) |
|---|---|---|
| 1 | Open Knesset `mk_individual` → website ID < 30000 → `GetMkdetailsHeader?mkId=…&languageKey=en/ru` | 128 |
| 2 | Current Knesset list `MKs/GetMks` (site IDs), matched by normalised Hebrew name | 84 |
| 3 | Wikidata P9770 (Knesset member ID = website ID), matched by Hebrew label, then the site API (or the Wikidata labels as a fallback) | 69 |
| 4 | Manual: Ganz, Saida, Kozhinov, Moati, Bezalel and 13 others | 18 |

- The site returns official Russian names, for example "Биньямин Нетаньяху" and "Итамар Бен-Гвир". It
  also returns English and Arabic names, the current faction name in each language, and a photo URL.
- New table `person_external_id (person_id, scheme, value)`, with schemes `knesset_site` and
  `wikidata`.
- Names go into the existing `person_alias` table with origin set. Wikidata aliases are added as
  `alias_type='variant'` to improve search, for example "Bibi" and "Биби".
- Tier 4 goes into a reviewed YAML file in the repo (`data/curated/mk_names.yaml`), so it survives
  rebuilds.
- Done when:
  - all 299 MKs have en and ru names;
  - the API returns `name: {he, en, ru}`;
  - Russian and English member search works through a trigram index on aliases.

### 1b. Party / faction names

- Current factions: official ru/en names come from the site's `Faction` field for each MK.
- Historic factions: there are ~40 distinct parties, seeded from Wikidata party items (he/en/ru
  labels) and then reviewed by hand in `data/curated/factions.yaml`. The 186 machine Russian labels
  are replaced.
- Two names per faction:
  - `short_name`, for example "Ликуд" or "Еш Атид";
  - the full list name, for example "«Оцма Йехудит» во главе с Итамаром Бен-Гвиром".
- Done when:
  - all 101 factions that voted have reviewed ru and en names;
  - no faction label has `origin='machine'` in the UI.

### 1c. Bill titles

- No official English or Russian titles exist. Wikidata has only 153 laws, and only 39 in English
  and 7 in Russian; they are used where present.
- The other ~3,600 titles get an LLM translation. To keep them consistent:
  - a glossary: Amendment No. → «поправка № », Temporary Provision → «временное положение»,
    Basic Law → «Основной закон», ministry names, and so on;
  - one fixed style rule for the Hebrew year: "התשפ"ה–2025" → "2025";
  - translated in batches of related bills, so that amendments to the same law read the same way.
- New table `bill_text (bill_id, language, field, text, origin, model, prompt_version,
  source_sha256, review_state)`, where `field` is `title`, `summary` or `explanation`.
- QA:
  - checks for glossary terms and numbers: every number in the source must appear in the
    translation;
  - a review of a 100-title sample by a native Russian speaker before publishing.
- Cost: ~3,600 short titles, a few dollars of API usage. This needs an Anthropic API key.

### 1d. Bill descriptions

- Source:
  - `KNS_Bill.SummaryLaw` exists for 1,144 bills;
  - every bill also has its proposal documents in `KNS_DocumentBill` ("הצעת חוק לדיון מוקדם", first
    reading and so on, as DOCX/PDF), and these include the explanatory notes ("דברי הסבר").
- Pipeline:
  1. download the latest proposal document; DOCX is preferred because its text extracts cleanly;
  2. extract the explanatory-notes section;
  3. generate a neutral 2–3 sentence description in he/en/ru with a fixed prompt;
  4. store it with a link to the document.
- The descriptions are labelled "краткое описание по пояснительной записке, сгенерировано
  автоматически" ("short description from the explanatory notes, generated automatically"). The
  official `SummaryLaw` is shown when it exists.
- Neutrality rule: describe what the bill does, never whether it is good. The explanatory notes are
  the sponsor's own framing, so the description says "according to the sponsors…".

### 1e. Topics and UI strings

- Add English to `topic_label`, so there are 21 labels × 3 languages, written by hand.
- Move the UI to locale routes `/ru`, `/en`, `/he`, with `/he` in RTL. Russian is the default.
  - All labels in `lib/labels.ts` move to per-locale dictionaries.
  - Add `hreflang` links between the language versions.
- API: `?lang=` selects the display fields, and every response also includes all available
  languages.

## 2. Automatic updates

- `hkv update` already exists and has been tested against live data. It needs to run on the server,
  not on a laptop. Production schedule:
  - **systemd timer** daily at 05:30 Asia/Jerusalem;
  - plus every 2 hours on Monday–Wednesday during sessions, when plenum votes happen.
- Robustness:
  - a lock (`pg_advisory_lock`), so two runs never overlap;
  - exit codes and `data_release.notes` record failures.
- Alerting: a Telegram bot message (or email) on failure, and when a release adds open
  `data_issue` rows.
- Web freshness: after a successful release, the updater calls the `/api/revalidate` webhook, so
  Next.js pages refresh without a rebuild.
- Weekly: a full re-read of the reference data and the last 180 days, to catch late corrections.
  Monthly: `hkv verify` against a source sample, with the report kept.
- New-MK and new-bill hooks: after each update,
  - run the 1a/1b name resolution for new persons and factions;
  - queue new bills for translation (1c/1d).
  Anything that cannot be resolved becomes a `data_issue`, never a silent gap.

## 3. Deployment to Hetzner (next step)

- **Server:** one CPX31 (4 vCPU, 8 GB), Ubuntu 24.04, about €15 a month. The DB is 760 MB and raw
  pages are 366 MB, so a CPX21 would also work, but Next.js builds and the LLM backfill like the extra
  RAM.
- **Services**, in `infra/compose.prod.yaml`:
  - `postgres:17` on a volume;
  - `api` (uvicorn behind gunicorn, 2–4 workers);
  - `web` (Next.js standalone build);
  - `caddy` (automatic HTTPS, gzip/zstd, caching headers);
  - an `updater` image run by the systemd timer.
- **Images:** built in GitHub Actions after the tests pass, pushed to GHCR, and deployed by SSH
  (`docker compose pull && up -d`). Migrations run before the API starts.
- **Initial data:** `pg_dump -Fc` from the local DB, restored on the server. There is no need to
  re-backfill. Raw pages are copied to a Storage Box for provenance.
- **Backups:**
  - nightly `pg_dump` to a Hetzner Storage Box (BX11, about €4 a month), keeping 14 daily and 8
    weekly copies;
  - a monthly restore test.
- **Security:**
  - SSH keys only;
  - ufw opens 80/443/22 only;
  - Postgres is not exposed to the internet;
  - unattended-upgrades;
  - API rate limit at Caddy.
- **Observability:**
  - Uptime Kuma or a free external ping on `/api/v1/status`;
  - the update-failure alerts from section 2;
  - optional self-hosted Umami for privacy-friendly analytics.
- **Needed from you:**
  - a Hetzner account and API token, or a server I can SSH into;
  - a domain name;
  - an Anthropic API key for 1c/1d.

## 4. Improvement backlog (ranked by value ÷ effort)

1. **Coalition vs opposition view**: "voted with the coalition N of M". The `government` and
   `faction_alignment` tables already exist and only need data.
2. **Compare two MKs or two factions**: an agreement rate on shared votes, with the votes where they
   differed.
3. **MK photos and short bios** from the site API. The photo licence needs checking; otherwise link
   to the site.
4. **Bill progress funnel**: preliminary, first, second and third readings, with dates, as one line
   per bill.
5. **Telegram channel / RSS**: new votes for a topic, an MK or a faction. This fits the
   Russian-speaking audience.
6. **Share cards**: OpenGraph images for a vote or an MK ("Как голосовал X по закону Y").
7. **Editor review screen** for topic assignments and translations. It sets `review_state`, and the
   machine label disappears once a text is reviewed.
8. **LLM-assisted topics**: multi-label classification from title plus explanatory notes, replacing
   the keyword rules. The keyword rules stay as an auditable baseline.
9. **Open data**: monthly CSV/Parquet dumps, an OpenAPI docs page, and a stable `/api/v1` with
   documented rate limits.
10. **Attendance and rebels rankings**, with careful wording ("no record" ≠ absent) and every
    denominator shown.
11. **Explain special votes**: reservations, articles and "המשך דיון", with plain-language hints on
    every vote page.
12. **Ministers' votes**: flag MKs who held government office at the vote date.

## Proposed order

| Step | Content | Size |
|---|---|---|
| A | Hetzner deploy + server-side auto-update + backups (sections 2, 3) | 1–2 days |
| B | MK and faction names he/en/ru (1a, 1b) + member search in ru/en | 1 day |
| C | Locale routing and UI dictionaries, topics in en (1e) | 1–2 days |
| D | Bill titles en/ru (1c), with native review of a sample | 1 day + review |
| E | Bill descriptions from explanatory notes (1d) | 2 days |
| F | Backlog items 1–6 | ongoing |

A goes first because the data is already worth publishing in Russian and Hebrew. B to E then ship
continuously to the live site.

## Source research (2026-10-04)

- **Wikidata P9770 "Knesset member ID"** is the Knesset website's `mk_individual_id`, not
  `KNS_Person.Id`.
  - 1,073 items have it, but only 121 of our 299 MKs can be reached through the ID.
  - Hebrew-label matching reaches more.
  - **P7390 "Knesset law ID"** covers 153 laws: 39 with an English label, 7 with a Russian one.
- **Open Knesset `members/mk_individual`** maps `mk_individual_id` ↔ `PersonID` for all 299 MKs.
  - The English name columns are empty.
  - For MKs elected since about 2019 the ID is a placeholder (30xxx = PersonID) that the site
    rejects.
- **Knesset site API** (`knesset.gov.il/WebSiteApi/knessetapi/`):
  - `MKs/GetMkdetailsHeader?mkId={site id}&languageKey=he|en|ru|ar` returns the official name,
    faction, position and photo.
  - `MKs/GetMks?languageKey=…` lists the current Knesset only (120 MKs, with Hebrew names and site
    IDs).
  - It is undocumented: treat it as unstable, cache the responses as raw pages, and keep the
    curated YAML as a fallback.
- **`KNS_DocumentBill`** lists proposal documents per bill, as DOC/PDF on `fs.knesset.gov.il`.
