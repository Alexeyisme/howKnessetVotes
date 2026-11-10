# A new Knesset: runbook

The 26th Knesset was sworn in on 2026-11-10 (roadmap O7). This page lists what happens on its own and what to do by
hand, in order, once the Knesset publishes the new Knesset's data. Every step is safe to repeat.

## Where it stands

- **2026-11-10, 20:40 UTC** (after the deploy of `3c5807b`): `hkv newterm` on the server reports *0 MKs, 0 factions*
  for the 26th Knesset, so the Knesset has not published them yet. Government 37 (formed in the 25th Knesset) continues.
  The site says the new Knesset's data appears as the Knesset publishes it, and lists the 25th Knesset until then.
- **How to know it has been published:** `hkv-newterm.timer` (hourly, from 2026-11-10) sends a Telegram message when
  the 26th Knesset's MKs and factions first appear in the database, and again when a government of the 26th Knesset is
  sworn in, each with the `hkv newterm` report ([scripts/newterm-check.sh](../scripts/newterm-check.sh)). The data comes
  in by itself; only steps 2–4 below wait for someone. The command in step 1 shows the same report at any time.
- **Timing of the first votes.** The 10-minute quick update loads votes only. A ballot by an MK who is not in the
  database yet is recorded as a `ballot_unknown_person` issue, then loaded by the next full update (every 2 h on
  sitting days, daily otherwise), which also reloads the MKs and factions. So on the first sitting day the new MKs'
  ballots can appear up to ~2 h after the vote itself.
- **Unrelated, seen while preparing this:** a copy of production from 2026-10-08 had three 25th-Knesset MKs not
  linked to the Knesset website (KNS ids 30921, 30922, 30923), so they have no names in other languages and no photos.
  `hkv names` may link them once the website lists them; otherwise they need `site_id` in `mk_names.toml`.

## What happens on its own

- **The data.** `hkv update` (systemd timers, [deploy.md](deploy.md)) loads MKs, factions, memberships, government posts
  and votes from Knesset OData as soon as they are published. Until the new Knesset's first vote the site counts as
  in recess, and reference data is reloaded once a day; when new votes arrive, the update reloads it at once, so new
  MKs exist before their ballots. Run `sudo systemctl start hkv-update` (as root) to load the data without waiting.
- **MK names and photos.** Every update gives new MKs their official en/ru/ar names and photos from the Knesset website
  once the website lists them. Until then they are shown by their Hebrew names, without photos.
- **The site.** The newest Knesset's MKs and factions are listed before its first vote (`LISTED_PERSON` /
  `LISTED_FACTION`, `src/hkv/api/common.py`). Until that first vote, the home, members and factions pages say that the
  new Knesset's data appears as the Knesset publishes it (`components/NewTermNotice.tsx`); the notice goes away by
  itself after the first vote. While the source has no MKs for the new Knesset, the members and factions pages show the
  previous one and say so.
- **No coalition yet.** While the outgoing government continues as a transitional government, the new Knesset's
  factions have role `unknown`, shown as "no government yet" (`TRANSITION_RULE_FROM`, `src/hkv/coalition`). Once the new
  government's first post appears in `KNS_PersonToPosition`, the next update derives coalition and opposition from it.

## What is done by hand

### 1. See what has been published

`hkv newterm` is read-only and takes a second. It needs the code from 2026-11-10 or later on the server.

```sh
ssh hkv 'cd /srv/hkv && scripts/prod.sh run --rm updater hkv newterm'
```

It prints the new Knesset's MKs and factions as the source has them, a to-do list, and entries to fill in and paste:
`[faction.N]` blocks for `factions.toml`, the likely party of each faction (where its members sat in the previous
Knesset), and `[mk.N]` entries for MKs the name steps could not link. "wait: the source has no MKs or factions" means
nothing is published yet: check again later, or run an update first.

### 2. Faction names: `src/hkv/names/curated/factions.toml`

Paste the `[faction.N]` blocks under a `# --- 26th Knesset (2026–) ---` heading and fill in **every** language
(`test_curated_files_have_every_language` fails on an empty name, so a half-filled block cannot be deployed).

- Take the names from the official lists (Central Elections Committee, the Knesset website), not from memory.
- `ru` as in Israeli Russian-language media, `en` as on the Knesset website, `ar` as on the Knesset website's Arabic
  pages; see the conventions at the top of the file.
- A long official list name ("X headed by Y") gets `he_short`, and `ru_short` / `en_short` / `ar_short`, so the party
  reads the same in tables as in earlier Knessets. The official full names from the Knesset website override ours
  once it lists the new MKs; the short names stay ours.

### 3. Parties: `src/hkv/names/curated/parties.toml`

Add each new faction ID to its party's `factions` list. A joint list goes into every member party (as Likud Yisrael
Beytenu in the 19th Knesset does). A party new to the Knesset gets its own `[party.<slug>]` block with `he`, `ru`, `en`, `ar`, placed
where it should appear in the list of parties on the site. The `hkv newterm` hints are only hints: check each one.

### 4. MKs the name steps cannot link: `src/hkv/names/curated/mk_names.toml`

Only after the Knesset website lists the new MKs, and after an update or `hkv names` has run. For each MK still listed
as "not linked to the website", find the website ID (`main.knesset.gov.il/mk/apps/mk/mk-personal-details/<site_id>`)
and fill in `site_id`.

### 5. Deploy and apply

```sh
uv run pytest -q && (cd apps/web && npm test && npm run lint && npm run build)
git commit ... && git push && gh run list --limit 1     # CI green
scripts/deploy.sh
```

Then, as root on the server, `hkv names` (applies the curated files and fetches names and photos now rather than at
the next update; [deploy.md](deploy.md) has the full `systemd-run` line), and run `hkv newterm` again: the to-do list
should be down to the coalition step.

### 6. Check the site

`/ru/members` and `/ru/factions` (26th Knesset by default), one new faction page, `/ru/parties` and a party with a new
faction, an MK page, then the same in `/en`, `/he` and `/ar`. New factions should show "no government yet", with no
coalition or opposition badge.

### 7. When the new government is sworn in

- The regular update loads the new posts and derives coalition and opposition. To do it at once:
  `hkv coalition` ([deploy.md](deploy.md)). `hkv newterm` then shows each faction's role today.
- Check the result against the coalition agreement. A party that supports the government without a ministry, or a
  faction whose role the posts get wrong, needs an `[[override]]` in `src/hkv/coalition/overrides.toml` with an
  `evidence` field, then a deploy and `hkv coalition`.

### 8. Close the step

Mark roadmap O7 done, with the date, in `docs/roadmap.md`, and stop the watch (as root):
`systemctl disable --now hkv-newterm.timer`. For the next Knesset, enable it again on the day it is sworn in.
