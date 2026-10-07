# Roadmap (updated 2026-10-06)

## Where we are

**Live at <https://knessetvotes.org>** since 2026-10-04 (operations: [deploy.md](deploy.md)).

| Area | State |
|---|---|
| Data | 37,045 plenum votes (2003-10-20 … 2026-07-28), 2.02M ballots, 491 MKs who voted, 175 factions (16th–25th Knessets). Faction at the vote date for 99.999% of ballots. Official totals cross-checked up to 2021-07 (exact in 96.5%). 37 governments with coalition/opposition per faction (derived from official government posts); 31 parties linked across Knessets. |
| Updates | Server timers: daily, every 2 h on plenum days, and a quick check every 10 minutes during sittings. Since the Knesset's geo-block (2026-10-05) they go through a $4 proxy server in Israel ([knesset-proxy.md](knesset-proxy.md)). Nightly DB dump on the server. |
| Web | Russian, English and Hebrew sites (`/ru`, `/en`, `/he`, RTL for Hebrew) and an Arabic beta (`/ar`); home page for first-time visitors; MK pages with photo and a one-line summary; filterable roll call. Search in all four languages. Parties across Knessets; coalition/opposition labels; "Contested" votes. |
| API | `/api/v1`, documented at `/docs`; `?lang=` display fields, names in four languages on every response; `/parties`, `/governments`, coalition blocs per vote, `?contested=`. |
| Gaps | The Arabic version is a beta until a native speaker reviews it (L10). Bill titles and official summaries are machine-translated (L6, L7 step 1); descriptions from explanatory notes, the plenum debate and the reservations (L7 steps 1–3) are built but not yet run in production. No "voted with the coalition N of M" on MK pages yet (rest of U11). The 26th Knesset opens on 2026-11-10 and its new factions need curated names (O7). Deploys don't wait for green CI. |

The plan has four tracks, followed by a proposed order. Sizes are rough, for one developer with
Claude: S ≈ under a day, M ≈ 1–3 days, L ≈ a week.

## Track 1 — Simplicity and usability

The site answers the questions a voter asks, in plain words, before it shows tables.

| # | Improvement | Why | Size |
|---|---|---|---|
| U1 | **New home page**: one large search box (any language), "how did my party vote on…" by topic, recent final-reading votes with the result in words ("принят 64:52"), and entry tiles for members, parties and topics | The current home page is a raw vote list; first-time visitors don't know where to start | M |
| U2 | **Plain-language vote header**: what was decided, the result in one line, and what this stage means (preliminary / first / second / third reading, reservation, procedural) | Most votes are reservations and procedural motions, which confuse people | S |
| U3 | **Important votes by default**: lists show final readings and votes on the bill as a whole first; reservations and procedural votes are behind "all votes" | Noise reduction: reservation votes are the majority of the rows | S |
| U4 | **One page per bill as a story**: a timeline line preliminary → first → second/third, with dates and results, and a mini faction chart for the final vote | Turns 20 separate votes into one understandable narrative | M |
| U5 | **MK page summary**: photo, current party and role, a one-sentence summary ("участвовал в 63% голосований созыва; против своей фракции — 31 раз"), key votes by topic | Today the page starts with the statistics | M |
| U6 | **Ballot table usability**: filter by name, by party, and by "voted against own faction"; sticky header; mobile cards instead of a wide table | Long tables are hard to use on phones | S |
| U7 | **Compare**: two MKs, or two parties. The agreement rate on shared votes, then the list of votes where they differed | The most-requested kind of question ("does X vote like Y?") | M |
| U8 | **Glossary and methodology pages**: readings, reservations, "no record ≠ absent", how cohesion and deviation are computed, data sources | Trust; every number on the site links here | S |
| U9 | **Share cards**: OpenGraph images for a vote, MK or topic ("Как голосовал Ликуд по закону о …") | Sharing in WhatsApp and Telegram is how this content travels | M |
| U10 | **Follow**: a Telegram channel or bot and RSS for new votes by topic, MK or party | Russian-speaking Israelis live in Telegram | M |
| U11 | **Coalition/opposition everywhere**: badges on parties, and "voted with the coalition N of M" on MK pages | Context needed to read any vote (needs D3). **Badges, coalition history and per-vote blocs done (Phase 3); the MK-page number is left** | S after D3 |
| U12 | **Accessibility and speed pass**: keyboard navigation, screen-reader labels on charts, a Lighthouse budget, dark mode verified | A public civic site should meet WCAG AA | S |
| U13 | **Contested votes** ✅: final votes with ≥ 60 votes cast where the coalition and opposition majorities differed (`/votes?view=contested`) | The user's idea "filter by number of voters": turnout alone also catches routine bills on big voting days, so it is combined with the coalition/opposition split | S |
| U14 | **Recess notice**: "the Knesset is in recess until …" on the home page, from `KNS_KnessetDates` | Between sessions the latest vote can be months old; visitors should not think the site is stale | S |

## Track 2 — Hebrew, English, Russian and Arabic

Rule: every displayed text records its origin:

- `knesset` (official);
- `wikidata`;
- `editor` (written or approved by a person);
- `machine` (LLM translation that nobody has reviewed yet).

Official text always wins. Machine text is visibly marked until someone reviews it. A change in the
Hebrew source puts the translation back into the review queue.

| # | Item | Source / method | Size |
|---|---|---|---|
| L1 | **MK names he/en/ru** for all 299 MKs who voted, plus aliases for search ("Биби", "Bibi") | Official Knesset site API (128 + 84 MKs), Wikidata P9770 (69), curated YAML (18) | M |
| L2 | **Party/faction names he/en/ru**, short and full form | Official names for current factions (site API); ~40 historic parties from Wikidata, reviewed in `data/curated/factions.yaml`; replaces 186 machine labels | S |
| L3 | **Locale routes `/ru`, `/en`, `/he`**: UI dictionaries per language, RTL for `/he`, a language switcher, `hreflang` links, date and number formats per locale. Default chosen from the browser's language, Russian otherwise | Next.js `[lang]` segment; `lib/labels.ts` → `dictionaries/{ru,en,he}.ts` | M |
| L4 | **Topics in English** (21 labels and aliases) | Written by hand | S |
| L5 | **Search in any language**: Russian and Latin names → MKs, transliteration-tolerant ("netanyahu", "нетаньяху", "натаниягу") | Trigram index on aliases in all languages | S |
| L6 | **Bill titles en/ru** for ~3,600 bills — *built 2026-10-05 (`hkv translate`, `text_translation`, marker and corrections on the site); in production since 2026-10-07, en/ru/ar, new titles translated by `hkv update`* | LLM with a fixed glossary (Amendment No. → «поправка №», Basic Law → «Основной закон», ministries…) and a style rule for Hebrew years; automatic checks (numbers and glossary terms preserved); a native speaker reviews a 100-title sample | M |
| L7 | **Bill descriptions he/en/ru/ar**, in three steps (sources: "Source research (2026-10-06)" below). **1. What the law does** — *built 2026-10-06*: the official `SummaryLaw` (1,144 voted bills, from the 20th Knesset on), machine-translated by `hkv translate` (kind `summary`) and shown on the bill page with the Hebrew original folded away; where it is missing — *built 2026-10-07* — `hkv notes` describes the bill from its sponsors' explanatory notes ("דברי הסבר"): KNS_DocumentBill links in `bill_document`, the sponsors' own proposal file (Word read locally, PDF sent to the model), a Hebrew machine description in `bill_explanation`, translated as kind `notes`; the bill page labels it as the sponsors' account and links the file. Covers ~2,600 voted bills (2,400 private bills with a Word file, ~220 government bills with a PDF); first production run pending (`hkv notes --documents --batch`). **2. What the sides argued** — *built 2026-10-07*: `hkv debate` cuts the bill's agenda items out of the transcripts (`KNS_DocumentPlenumSession` → `plenum_document`) of every sitting where it was voted on — the 2nd/3rd reading alone is often just the committee chair and the reservations' presenters, the general debate is at the first or preliminary reading — in all three transcript formats (2018+ .docx markers, 2009–2017 hidden Word 97 markers, earlier the table of contents); speakers are listed without a model and resolved to the member and faction on the day of their first speech; a machine summary and up to five arguments per side, each pointing to the speeches it comes from (checked), in `bill_debate`; the bill page shows the arguments, every speaker with faction, coalition/opposition and their final vote, and links the transcripts. **3. Objections** — *built 2026-10-07*: `hkv reservations` reads the section "הסתייגויות ובקשות רשות דיבור" of the committee version (latest of groups 4/101/46/49/103/104); the model assigns reservation numbers to proposers (groups, single members, joint ones) and the job checks them against the numbers printed; PDFs whose numbers are not text (automatic numbering, reversed lines) go to the model as pages and are marked unchecked; counts per faction (a joint reservation counts for each), who asked to speak, a one-sentence gist per proposer. Both default to the contested final votes (`--all` for every final vote) and run in `hkv update` (5 bills per run each); first production run pending (`hkv debate --batch`, `hkv reservations --batch`). Not covered: a debate held at a sitting without a vote on the bill (a filibuster that ran past midnight into the next sitting), committee discussions, and arrangements laws whose reservations section exceeds 300,000 characters | L |
| L8 | **API language**: `?lang=` picks the display fields; every response also carries `{he, en, ru}` objects | — | S |
| L9 | **Review screen**: approve or fix machine translations and topic assignments; sets `review_state` and removes the "machine" mark | Small admin page behind a login | M |
| L10 | **Arabic** (`/ar`) — *beta, Phase 4*: about 21% of Israelis are Arab citizens, and Arabic-speaking voters have no Knesset voting tracker in their language | **Names:** the Knesset website's API returns official Arabic MK names and faction names (`languageKey=ar`, checked 2026-10-04: "بنيامين نتنياهو", "الليكود"), fetched by the same `hkv names` code. **Data:** the schema already allows `ar` in `person_alias`, `topic_label` and `topic_alias`; `faction_label` needs `ar` added back to its language check. **Site:** RTL layout from the Hebrew site; `dict/ar.tsx`, glossary and methodology need a native Arabic-speaking reviewer for Knesset terms (قراءة أولى، تحفّظ، حجب الثقة); Arabic search with alef/hamza and ta marbuta normalisation; Arabic topic labels and aliases; `?lang=ar` in the API. Curated short names for the 16th–25th Knesset factions where the website has none. **Later:** bill titles in Arabic come with L6 | M |

L6 and L7 need an Anthropic API key. Expected cost: a few dollars for titles and tens of dollars for
descriptions. L7 steps 2–3 for the contested laws (estimate 2026-10-07, Sonnet 5 at $2/$10 per MTok, half price as a
Message Batch): debates ~20M input tokens (~$20), reservations ~8M (~$8).

## Track 3 — Database and history

| # | Item | Details | Size |
|---|---|---|---|
| D1 | **Extend history back to October 2003** (16th–20th Knessets) — *done, Phase 3* | Checked 2026-10-04: OData v4 has **19,152 more votes before 2016-10**, with per-MK ballots back to vote 6 on 2003-10-20. Legacy `Votes.svc` has official totals for the same years. Faction memberships go back to 1948, so the faction at the vote date works. This more than doubles the history. Audit first: some early votes have very few ballots (vote 5000 in 2005: 10 records). The existing backfill and legacy loaders can load it; expect 1.1M+ ballots and a few hours with 5 workers. | M |
| D2 | **Party lineage across Knessets** ✅: a `party` entity linking per-term factions (Likud 16th…25th, Yesh Atid, joint lists, splits and mergers) | Done as curated `parties.toml`: 31 parties, 219 faction links; a joint list belongs to every member party. Pages `/parties/[slug]` | M |
| D3 | **Governments and coalition membership** ✅ | Done without a hand-made list: derived from official government posts (`KNS_PersonToPosition` with `GovernmentNum`), plus 7 curated overrides with evidence. All 37 governments | M |
| D4 | **Bill history**: merged bills (`KNS_BillUnion`), initiator changes, committee referral, status changes over time | Status changes are captured from now on through `row_revision`; earlier ones come from vote stages | M |
| D5 | **Visible change history**: a "data changes" page and API with new votes per update and source corrections (old → new value). `row_revision` already holds 51 vote corrections; the `data_release` diff becomes the changelog | Transparency; lets journalists cite a fixed version | S |
| D6 | **Official totals after 2021-07** (Votes.svc stopped then) | Check whether the website's vote cards are reachable from the server; otherwise show "official total not published" | S |
| D7 | **Data-issue triage**: 383 open issues, grouped and shown on a methodology sub-page; known-unresolvable ones marked `accepted` | Honest coverage numbers | S |
| D8 | **Open data**: monthly CSV/Parquet dumps per release, with a checksum and the release ID | Researchers; reproducibility | S |
| D9 | **Bitemporal memberships** (spec §5): record *when we learned* about a membership change, not only when it applied | Needed once retroactive corrections appear; postponed until they do (ADR 0001) | L |

## Track 4 — Operations

| # | Item | Size |
|---|---|---|
| O1 ✅ | Off-server backups: Hetzner server backups (~€1–2/month) or Storage Box (~€4/month); monthly restore test | S |
| O2 ✅ | Failure alerts: Telegram bot for the update and backup timers, and for "no update in 36 h" | S |
| O3 ✅ (tests; deploy gate open) | CI: GitHub Actions runs the tests on push; deploy only from green `main` | S |
| O4 | Uptime check on `/api/v1/status` (external) | S |
| O5 | Raw source pages (366 MB) archived off-server for provenance | S |
| O6 | Privacy-friendly analytics (self-hosted Umami) to learn what people search for | S |
| O7 | **26th Knesset readiness** (opens 2026-11-10): curated ru/en/ar names for the new factions in `factions.toml`, their links in `parties.toml`, and `hkv names` for new MKs' names and photos once the website lists them. Open `faction_name_missing` issues show what is left | S |
| O8 ✅ | **Knesset geo-block** (2026-10-05): updates reach the Knesset through an SSH tunnel to a $4/month proxy server in Israel (Kamatera), which relays only to `knesset.gov.il` ([knesset-proxy.md](knesset-proxy.md)). In a recess the 2-hourly runs skip reference data (about 1,200 instead of 3,900 requests a week) | S |

## Proposed order

| Phase | Content | Outcome |
|---|---|---|
| 1 ✅ | O1, O2, O3 · L1, L2, L4, L5 · U2, U3, U8 · T1 | Safe operations; every MK and party has proper names in 3 languages; votes read in plain words |
| 2 ✅ | L3, L8 · U1, U5, U6 | Full English and Hebrew site; a home page and MK pages built for first-time visitors |
| 3 (in progress) | D1, D2, D3 · U11, U13 | History back to 2003; parties across Knessets; coalition context; contested votes |
| 4 | O7, U14 · L10 · L6, L7, L9 · U4 | Arabic site; bills readable in Russian and English, with descriptions and a review workflow |
| 5 | U7, U9, U10 · D4, D5, D8 | Compare, share and follow; changelog and open data |

Phases 1–2 change what every visitor sees. Phase 3 doubles the data and should come before any
public launch or press, so that early coverage isn't based on a partial history.

## Phase 1 — implementation plan (started 2026-10-04)

| Step | Item | Implementation | Done when |
|---|---|---|---|
| 1 | O1 backups | Hetzner server backups on `hkv-1`: 7 daily snapshots, stored separately from the server | `hcloud server describe` shows a backup window |
| 2 | O2 alerts | `scripts/alert.sh` sends a Telegram message when `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID` are set in `/srv/hkv/.env`, and logs to the journal otherwise. The update and backup units get `OnFailure=hkv-alert@%n` | A forced failure produces an alert (journal until the bot token is added) |
| 3 | O3 CI | GitHub Actions: Postgres 17 service, `uv run pytest`, `next build` | Green check on `main` |
| 4 | L1 MK names | Migration 0006: `person_external_id`; `person_alias` gains origins `wikidata`/`curated` and alias type `variant`. Module `hkv.names`: Open Knesset `mk_individual` → site ID; site API `GetMks` and `GetMkdetailsHeader` (en/ru); Wikidata P9770 and labels; `curated/mk_names.toml` for the rest. Raw responses are kept as source snapshots. `hkv names` command, also run inside `hkv update` for new MKs | All 299 MKs who voted have en and ru names; unresolved ones become a `data_issue` |
| 5 | L2 party names | `curated/factions.toml` keyed by Knesset faction ID: ru/en short and full name, written by hand; current-Knesset names from the site API override with `origin='official'`. Replaces the machine labels and `FACTIONS_RU` | All 101 factions that voted have ru and en labels; none `machine` |
| 6 | L4 topics en | English label and aliases in `TOPICS` | 21 × 3 labels |
| 7 | L5 search | Cyrillic and Latin queries match `person_alias` (trigram), so MKs are findable in any language | "нетаньяху", "netanyahu", "ben gvir" find the MK |
| 8 | API/UI names | Members and factions return `name: {he, en, ru}`; Russian pages show the Russian name with Hebrew underneath | Member list, member, vote and faction pages show Russian names |
| 9 | U2 + U3 | Vote page header in plain words (what was decided, the result, what the stage means); lists default to "important" votes (final readings and whole-bill votes), with a switch to "all" | — |
| 10 | U8 | `/about/glossary` and `/about/methodology` pages; numbers link to them | — |

### Phase 1 — status (2026-10-04)

| Item | State | Result |
|---|---|---|
| O1 backups | done | Hetzner daily server backups (7 kept, window 06–10 UTC), plus the nightly `pg_dump` |
| O2 alerts | done | `hkv-alert@` runs on failure of the update or backup: journal plus a Telegram message from @knessetvotes_bot (tested) |
| O3 CI | done | GitHub Actions: 81 Python tests on Postgres 17; web lint, type check and build |
| L1 MK names | done | **All 299 MKs: official en/ru names from the Knesset website.** Website ID via `KNS_MkSiteCode` (128), the current and replaced MK lists (100), Wikidata P9770 (63), curated (8). All 171 name-based matches were verified against the website's Hebrew names. 370 search variants from Wikidata |
| L2 party names | done | Curated ru/en full and short names for all 101 factions that voted; official names for the current Knesset (full name official, short name curated so a party reads the same across Knessets). Fixed machine labels (e.g. the Joint List was labelled as Ra'am's name) |
| L4 topics en | done | 21 English labels and aliases |
| L5 search | done | Russian and English names and nicknames find MKs ("нетаньяху", "биби", "ben gvir") |
| API/UI names | done | `name_en`/`name_ru` for members, `name_*`/`short_*` for factions on every response; Russian name first, Hebrew original alongside |
| U2 plain-language votes | done | Outcome line per vote type ("Закон принят: 64 за, 52 против"), official before 2021-07, otherwise derived and labelled; a sentence on what the stage means |
| U3 main votes by default | done | Home page shows whole-bill votes and no-confidence motions; final, first, preliminary and "all votes" are one click away |
| U8 glossary and methodology | done | `/about/glossary`, `/about/methodology`; footer credits all sources, including Open Knesset |
| T1 official law topics | done | Official classification of the law a bill amends (only the law named in the title; omnibus laws with more than 3 categories skipped). Topic coverage 69% → 78% of voted bills; agrees with keyword rules on 91% of bills that have both. Also found and fixed a keyword false positive (legal capacity ≠ kashrut) |

### Phase 2 — status (2026-10-04)

| Item | State | Result |
|---|---|---|
| L3 locale routes | done | `/ru`, `/en`, `/he` with full UI dictionaries, RTL for Hebrew, language switcher in the header, `hreflang` alternates, dates and numbers per locale. Unprefixed links (all old URLs) redirect by cookie → `Accept-Language` → Russian. Glossary and methodology written in all three languages |
| L8 API language | done | `?lang=he|en|ru` on every endpoint fills `name` / `short` / `faction_name` / `label`, falling back to Hebrew; `label_en` on topics; search returns full faction name objects |
| Hebrew short names | done (new) | Long official list names ("התאחדות הספרדים שומרי תורה…") get curated short forms (`he_short`, 38 factions) for tables and charts; the official name stays as a tooltip |
| U1 home page | done | Search box for any language with examples, top topics, the latest final votes with the outcome in words, tiles for the sections. The vote feed moved to `/votes` (old `/?view=` links redirect) |
| U5 MK page | done | Official photo (from the Knesset website, 299/299; since 2026-10-07 a stored copy served from `/api/v1/members/{id}/photo`, because `fs.knesset.gov.il` is geo-blocked outside Israel); since 2026-10-07 also 96 px and 240 px copies (~3 KB and ~12 KB instead of ~115 KB) for member chips and the member page, as `.jpg` URLs that Cloudflare caches, current or last party, a one-sentence summary (participation, votes against own faction, bills sponsored); the vote list opens on final votes |
| U6 roll call | done | Filter by name (any language), by faction and "against own faction's majority"; sticky header; cards on phones |
| Quorum | done (new) | Glossary entry and a note on votes with fewer than 40 votes cast: the plenum has no quorum, a simple majority of those voting decides |

### Phase 3 — status (2026-10-04)

| Item | State | Result |
|---|---|---|
| D1 history to 2003 | done | Loaded 2026-10-05: **37,045 votes** from 2003-10-20 (19,726 before 2016-10-31) and **2.02M ballots**. Roll call vs official totals (24,739 votes up to 2021-07): exact match 96.5%, within two votes 99.9%. Weaker years: 2003 (86%), 2004 (88.5%), 2013 (87%), 2018 (90%) — almost all off by one or two votes, logged as `totals_mismatch` (878 open). 11 ballots have no faction on the vote date. The WAF throttled the first run with HTTP 481 after ~1.5 h; now retried with backoff, and the rerun used one worker |
| D3 governments and coalitions | done | `gov_position` (all government posts), 37 governments, coalition/opposition per faction per day. Rules: a member holds a post → coalition; ministers who left the Knesset under the Norwegian law (2015+) count for their faction; gaps under 30 days don't flip a faction; no posts at all → `unknown` (between election and swearing-in). 7 curated overrides with evidence: Yamina 2020 (opposition), Ra'am 2021–22, Shas from 2025-07, Degel HaTorah 2019–21, Agudat Yisrael and Degel HaTorah Jan–Mar 2005. Checked against governments 30–37 |
| D2 parties | done | 31 parties, 219 faction links; curated ru/en/he names for the 91 factions of the 16th–19th Knessets (192 factions curated in total) |
| U11 coalition context | mostly done | Badges on vote breakdowns, faction lists and party pages; coalition history on faction pages; coalition vs opposition counts on every vote (`vote_bloc`). Left: "voted with the coalition N of M" on MK pages |
| U13 contested votes | done (new) | `/votes?view=contested`: final votes, ≥ 60 cast, coalition and opposition majorities differ. API `contested`, `min_cast` |
| Deploy cleanup | done | `scripts/deploy.sh` now removes files no longer tracked from the server's code directories (moved pages broke the first Phase 2 build) |

To check: the official data shows Yisrael Eichler (UTJ) as deputy communications minister from 2026-01-19, so UTJ is shown back in the coalition from then. This is later than the editor's own knowledge; if UTJ did not rejoin, add an override.

### Phase 4 — status (2026-10-05)

| Item | State | Result |
|---|---|---|
| L10 Arabic | beta | `/ar` with the full UI, glossary and methodology in Arabic (RTL, Western digits, 24-hour time). Official Arabic MK names from the Knesset website (`hkv names --refresh` fills them for known MKs; new MKs get them automatically); curated Arabic names for all 192 factions and 31 parties; Arabic topic labels and aliases. API `?lang=ar`, `name_ar`/`short_ar`/`label_ar`; search ignores hamza forms, ta marbuta and harakat (`ar_norm`, migration 0012). Every Arabic page carries a beta note; the methodology page has a "Translation" section in all four languages saying how each version was made. **Left:** review by a native Arabic speaker (Knesset terms, glossary, methodology), then remove `translation.beta` |

## Open Knesset (oknesset.org) — what we can reuse

[Open Knesset](https://oknesset.org) is run by Hasadna (the Public Knowledge Workshop). The site is
Hebrew only and centred on members and committees, with no vote-centred UI. It updates daily from
the official Knesset APIs. Its pipeline ([hasadna/knesset-data-pipelines](https://github.com/hasadna/knesset-data-pipelines))
publishes everything as CSV under `production.oknesset.org/pipelines/data/`. The data requires
attribution, so the site footer and the methodology page will credit Open Knesset for the tables we
use.

| Dataset | What it gives | Use | Roadmap item |
|---|---|---|---|
| `members/mk_individual` | `mk_individual_id` ↔ `PersonID` | Already used for the MK name lookup | L1 |
| `members/member_english_names` | English names for 797 MKs (by `mk_individual_id`) | Fallback English names. Covers 121 of our 299 MKs, all older ones | L1 |
| `members/kns_mksitecode` (also `KNS_MkSiteCode` in OData v4) | Official `PersonID` ↔ website ID | Preferred over Open Knesset's `mk_individual` where present. Only 128 of our 299 MKs, all older ones | L1 |
| `laws/kns_israel_law_classification` + `kns_law_binding` | Official classification of laws into 51 categories (taxation, health, security, welfare…), and which law each bill amends | **Official topics**: covers 1,203 of our 3,647 bills. Use it to validate and extend the keyword topics, shown as "official classification" | new T1 |
| `laws/kns_israel_law`, `kns_israel_law_name` | Laws in force: basic law, budget law, validity, name history | "Which law does this bill amend", Basic Law badges | U4, D4 |
| `bills/kns_billunion`, `kns_billsplit`, `kns_billname`, `kns_billhistoryinitiator` | Merged and split bills, name changes across stages, initiator history | Bill story page, related bills | U4, D4 |
| `knesset/kns_govministry` | Ministries by government | Ministry glossary for translations; government data | L6, D3 |
| `people/mk_voted_against_majority` | Open Knesset's own "voted against faction majority" | A cross-check for our deviation metric (definitions may differ: document any difference) | D7 |
| `committees/*` (sessions, protocols, speaker-divided text) | Committee meetings and full protocols | Out of scope for now (plenum votes only); possible later "what was said in committee" | later |
| `lobbyists/*` | Registered lobbyists and their clients | Out of scope; possible later | later |
| `members/presence` | Hours each MK was present in the building | **Not usable**: stale since 2025-09-05 | — |
| Redash (`redash.hasadna.org.il`) | SQL over the same data | Ad-hoc checks during audits | — |

New item:

- **T1 — official law classification as a topic source (S).** Map the 51 official categories to
  our 21 topics. Store assignments with `origin='official'`. A bill keeps its rule-based topics, and
  where they disagree with the official category the bill is queued for review. Topic pages say
  which assignments are official.

## Source research (2026-10-04)

- **Knesset site API** (`knesset.gov.il/WebSiteApi/knessetapi/`, undocumented, so responses are
  cached as raw pages):
  - `MKs/GetMkdetailsHeader?mkId={site id}&languageKey=he|en|ru|ar` returns the official name,
    faction, position and photo;
  - `MKs/GetMks?languageKey=…` returns the current Knesset only (120 MKs, Hebrew names, site IDs).
- **Wikidata**:
  - P9770 "Knesset member ID" = the website's `mk_individual_id`, not `KNS_Person.Id`. 1,073 items;
    121 of our 299 MKs are reachable by ID.
  - P7390 "Knesset law ID": 153 laws (39 with an English label, 7 with a Russian one).
- **Open Knesset `members/mk_individual`** maps `mk_individual_id` ↔ `PersonID` for all 299 MKs.
  - Its English columns are empty.
  - For MKs elected since about 2019 the ID is a placeholder (30xxx) that the site rejects.
- **`KNS_DocumentBill`** has proposal documents per bill (DOC/PDF) with explanatory notes.
- **History**: `KNS_PlenumVote` starts at Id 6 (2003-10-20) and `KNS_PlenumVoteResult` has
  ballots from then on. Legacy `Votes.svc` covers 2003 – 2021-07-13.
- **Access from the server**: all of the above are reachable from Hetzner Helsinki (<hkv-1 address>).
  60 paced requests all returned 200.

## Source research (2026-10-06): bill descriptions and the coalition–opposition fight

Scope: the 3,060 bills with a contested vote on the whole bill (adopt or reject; coalition and opposition
majorities differed), and within them the **423 laws whose third reading was contested**. Document lists came from
`KNS_DocumentBill` (all 3,060 bills); samples from 2016, 2017, 2023 and 2026 were read.

| Source | 16th–19th Knesset (112 laws) | 20th–25th Knesset (311 laws) | What it is |
|---|---|---|---|
| `KNS_Bill.SummaryLaw` | 0 | 284 (91%) | Official neutral summary, ~850 characters on average |
| Explanatory notes (`KNS_DocumentBill` group 1 preliminary, 2 first reading) | 107 | 292 | Written by the sponsor (government or MK), so one-sided |
| Committee version for the 2nd/3rd reading (groups 4, 101 "פונץ' בננה", 5/50/102/105 amendment tables, 46/49/103/104 re-tabled) | 87 | 311 (100%) | Ends with "הסתייגויות ובקשות רשות דיבור": who proposed which change to which section (legal edits, not reasons; in the 25th Knesset grouped by opposition faction) and who asked to speak |
| Debate excerpt for one bill (groups 15, 45 "קטע מדברי הכנסת", 28) | 66 | 14 | The plenum debate on that bill, every speaker with their faction. **Not published after November 2017** |
| Full plenum transcript (`KNS_DocumentPlenumSession`, group 28 "דברי הכנסת", DOC) | yes | yes | The whole sitting; available ~2 months after it |

- **Cutting one bill's debate out of a sitting** works: the transcript DOC marks agenda items with
  `<< הצח >> title << הצח >>` and speakers with `<< דובר >>`, `<< יור >>`, `<< דובר_המשך >>` ("שרון ניר (ישראל ביתנו):").
  A 2023 law came out as a clean 16,000-character segment. A vote after midnight belongs to the sitting that started
  the day before (`KNS_PlenumSession` StartDate/FinishDate).
- Old `.doc` files convert with `textutil` (macOS) or LibreOffice; PDFs with `pypdf`.
- Other official sources, not linked to a bill ID: Knesset Research and Information Center (ממ"מ) papers, Knesset
  press releases.
- Since 2026-10-05 these files are geo-blocked like the rest of `knesset.gov.il` (see `docs/knesset-proxy.md`).
