# UI/UX requirements — "seconds to an answer" (draft, 2026-10-04)

A review of the live site as built in `apps/web` (code review of every page, component, dictionary and
stylesheet; the production site is not reachable from the sandbox, so no screenshots yet), followed
by requirements and a plan for proper UX analysis. Context that drives everything below: **elections are
weeks away** (the 26th Knesset convenes on 2026-11-10), and the audience is a voter who wants to know
how parties really voted, in seconds, mostly on a phone, mostly arriving from a Telegram/WhatsApp link.

## 1. Who comes and what they ask

| Persona | The question in their head | Today's path (from the code) | Verdict |
|---|---|---|---|
| **Voter, ru/en** ("Should I vote for them again?") | *How did Likud vote on housing / the budget?* | Home → topic chip → `/topics/housing` → find the faction row → read "majority for 12 of 14" | 3 clicks, but the number is a count of bills, not a stance; every coalition party reads "for" on every topic because coalition bills pass. The bill titles are Hebrew only. |
| **Voter, he** | *Same, in Hebrew* | Same | Same, minus the language wall. |
| **MK watcher** | *Did my MK vote for X? Does he break with his party?* | Search → `/members/[id]` → "Final votes" tab → scroll 30-per-page list | No topic filter on the MK page; "with the coalition N of M" missing (U11). Not answerable in seconds. |
| **Undecided voter** | *Which party actually votes the way I think?* | — | Not answerable at all today. The data can answer it (see R6). |
| **Sharer / journalist** | *Give me a link that shows it in one picture* | Vote page link; no OG image, Hebrew title in the preview | The preview in Telegram/WhatsApp is the product for most people; today it is text only (U9). |
| **Returning visitor** | *What happened this week?* | Home → "Latest final votes" (6) | During recess the newest vote is months old with no explanation (U14). |

Takeaway: the site is **honest and complete, vote-centred**; the voter is **party-centred and question-centred**.
The main redesign is a change of entry point and hierarchy, not of data.

## 1b. What the screenshots show (live site, 2026-10-04, 390 px and 1,280 px, ru/en/he)

Captured with `apps/web/scripts/screens.mjs`. Beyond §1, the renders add these concrete points:

- **Phone header is four rows** (brand, five nav links, full-width search, language row) ≈ 140 px before any content, and the home H1 then repeats the brand. A phone visitor sees the site name twice and no answer above the fold.
- **Home is 70 % Hebrew for a ru/en reader**: the six "latest final votes" are Hebrew titles; the only non-Hebrew words are the verdict line. The topic chips carry bill counts ("Courts and criminal law 415") that mean nothing to a visitor and make the chips look like filters.
- **End-of-session votes dominate "latest"**: "Law passed 5 for · 0 against" six times in a row. Correct (no quorum), but to a first-time visitor it reads as broken data. Low-turnout verdicts need the "5 of 120 voted" context inline, and the home feed should prefer contested/key votes over the most recent.
- **Party page on a phone hides the one thing that matters**: the table scrolls horizontally and the *Coalition / opposition* column is off-screen; the visible columns are Knesset number, list name ("Likud headed by Benjamin Netanyahu") and full date ranges. No votes anywhere on the page.
- **Vote page**: the hero (badges, Hebrew title, verdict) works; the full desktop page is ~5,600 px tall because the 103-row roll call is expanded by default. The faction breakdown rows put name, Hebrew name, badge, counts and "majority for" on one dense line and the bar is thin relative to the text.
- **Topic page**: the diverging bars are good, but "Likud 103 of 103 for · Shas 94 of 94 for" confirms that the chart measures bloc membership, not stance; the `Show` button next to the Knesset select is a form, not a switch.
- **Member page** on a phone: a 30-row list of Hebrew titles between the summary and the statistics; the photo is small; the faction history table is as long as the vote list.
- **Hebrew RTL is correct everywhere** sampled (header, chips, cards, bars, tables, forms).
- Two search boxes are visible at once on home (header + hero).

Second round (members, parties, factions, bills, bill, faction, search, glossary, methodology, "all votes"; dark mode for home, vote, member, members, bills):

- **Dark mode is sound**: tokens hold on every page sampled, the for/against colours stay distinguishable, no white flashes or unstyled blocks. Keep it; add a manual toggle only if analytics show demand.
- **`/members` on a phone is unusable**: a four-column table (name, latest party, Knessets, roll-call records) at 390 px wraps every cell and runs to ~11,800 px for one Knesset. It should be a grid of photo chips (name + party badge) with letter navigation and the same typeahead as everywhere; "roll-call records" is an internal number and should go.
- **`/bills/[id]` lists all 77 plenum votes**, mostly second-reading reservations, as a flat ~7,400 px list. This is the U4 "bill as a story" gap: three or four stage milestones with their verdict, reservations collapsed under a count.
- **Faction page**: cohesion 99.9 % and "voted unanimously 98.6 %" for Likud are true but uninformative for a coalition party (they measure bloc discipline on routine bills); the interesting number — splits — is behind a "Party split" tab. Lead with contested and split votes; put cohesion in the statistics block with the denominator, as now.
- **`/parties` is the best list page on the site** (name, Knessets, coalition badge, one line each) and should be the model for members and factions; its "Factions by Knesset →" link exposes the internal concept and should become the Knesset switch of R10.
- **`/factions` for the 25th Knesset shows a 5-day "Religious Zionism" row with 10 records** (the pre-split list) next to the real one. Correct data, confusing list: hide or fold sub-month technical factions into their successor in lists (keep them on the detail pages).
- **Search "likud"** returns "Ayoob Kara" as the first member (an alias match that nobody expects) and then ten "Likud · Nth Knesset" faction rows. Results should be grouped: one party card (→ `/parties/likud`) with the Knessets inside it, members only on name matches.
- **"All votes" is 70 % reservation votes** ("2 for · 8 against") — confirms the U3 default; the view needs a stage/motion filter row rather than one undifferentiated feed.
- Glossary and methodology read well and are the right length on a phone; link them from the places where the terms appear (the stage chip, the "no record" note) rather than only from the footer.
- No page shows a *loading* or *error* state distinct from "no votes"; a slow API reply renders an empty card.

## 2. What is good and must stay

- Plain-language verdict line per vote ("Law passed: 64 for, 52 against") and the stage explanation — keep as the hero.
- One colour system: for = blue, against = red, abstain = grey; every bar carries its numbers.
- Numerator/denominator on every rate, "no record ≠ absent", source link on every page. This is the trust layer — keep it, but move it **below** the answer.
- Faction at the vote date, coalition/opposition badges, "Contested" view — the raw material for everything below.
- Three locales with real RTL, logical CSS, dark mode, no client-side framework weight.

## 3. Principles for the redesign

1. **Answer first, evidence second.** Each page opens with one sentence and one picture that answer the page's question; tables, codes and methodology notes come after a fold or inside `<details>`.
2. **Party is the hub.** The voter thinks "Likud", not "faction 1234 in the 25th Knesset". Every list, chart and search result leads to a party page; the faction/Knesset split becomes a term switch, not a separate concept.
3. **One screen, one picture.** The signature visuals are (a) a party × topic matrix and (b) a single stacked bar per vote split by coalition/opposition. Both are readable in two seconds on a phone.
4. **Same thing, same look, everywhere.** One vote card, one party chip, one member chip, reused on home, lists, pages and share images.
5. **Readable without Hebrew.** Until bill titles are translated (L6), every vote shows topic + stage + outcome in the UI language before the Hebrew title.
6. **Thumb first.** 390 px wide, one hand, RTL and LTR, no horizontal scroll, tap targets ≥ 44 px.

## 4. Requirements

Sizes as in the roadmap (S < 1 day, M 1–3 days, L a week). "Ship before elections" = can be done in the next two weeks without new data work.

### R1 — Party page becomes the hub (M, before elections)

Today `/parties/[slug]` is a table of factions by Knesset; votes live on `/factions/[id]`.

- Header: party name (3 languages), current/last list, **coalition / opposition** badge for the current Knesset, number of MKs, link to members.
- "Where they stand" strip: the party's row of the topic matrix (R2) — one tile per topic: *for / against / split* with the count underneath ("8 of 9 bills").
- "Votes that mattered" (R5): the party's choice on each key vote, as a horizontal list of vote cards.
- Cohesion and "voted with the coalition N of M" as two big numbers with the denominator in small text.
- Members as photo chips (the Knesset portraits already exist, 299/299).
- History (the old factions table) and the methodology note go into collapsed sections at the end.
- `/factions/[id]` keeps its URL but renders the same layout with the Knesset switch preset; the nav item "Parties" always lands on parties.

Acceptance: a visitor can answer "did Shas vote for the 2025 budget?" from the party page in ≤ 2 taps without reading Hebrew.

### R2 — Party × topic matrix (M, before elections)

A new `/compass` (or on `/topics`) page: rows = parties of the chosen Knesset (ordered coalition → opposition), columns = the ~12 largest topics, cell = the party's majority on final votes (blue/red/grey with the count on hover/tap). Use the existing `/topics/{slug}` data; one request per topic, cached.

- Default to the current Knesset; term switch at the top.
- **Label the mechanics in one line**: "Coalition parties vote for government bills; look for the cells that differ from the bloc." Add a toggle *all bills / contested only* — contested cells are where parties actually differ, and that is the voter's question.
- Tap a cell → list of those votes with verdict lines.
- Mobile: horizontal scroll with a sticky party column; or topics as a vertical accordion per party.

Acceptance: the whole 25th Knesset fits on one phone screen; a cell tap shows the underlying votes.

### R3 — Vote card and vote page hierarchy (S, before elections)

One `VoteCard` component used on home, `/votes`, member, party and bill pages:

```
[topic chip] [stage chip]                 [date]
Verdict in words — "Law passed 64:52"      ← UI language, bold
Hebrew title (one line, ellipsis)          ← secondary
▮▮▮▮▮▮▮▮▮▮▯▯▯▯  for | abstain | against    ← one thin bar, counts at the ends
Coalition 60 for · Opposition 4 for 50 against   ← only when blocs exist
```

Vote page: keep the verdict box as the hero, then the **bloc bar** (coalition vs opposition, two rows) above the faction breakdown; the four tally tiles, official-total reconciliation, "only members with a record…" and source codes move under one collapsed "Numbers and sources" section. The ballot table stays, after the breakdown, with the filters it has.

Acceptance: on a 390 px screen, verdict + bar + bloc line are visible without scrolling.

### R4 — Law titles translated under the Hebrew title (M, before elections = L6)

Every bill and vote title is Hebrew in all three UIs. Decision (owner, 2026-10-04): show an **automatic translation
in the UI language directly under the Hebrew title**, visibly marked, everywhere a title appears:

```
הצעת חוק לעידוד פעילות בשוק ההון (תיקוני חקיקה), התשפ"ד-2024
Law for the Encouragement of Activity in the Capital Market (Legislative Amendments)   · automatic translation
```

- **Scope**: distinct Hebrew title strings of bills (3,647) and votes (17,319, mostly the bill title plus a stage, so
  far fewer distinct strings), plus `subject_he` on vote pages. Languages: en, ru, ar (Arabic rides on the same
  table when L10 lands). Hebrew UI shows nothing extra.
- **Storage**: one table `text_translation(source_sha256, lang, text, origin, model, reviewed_at, created_at)` keyed
  by the hash of the Hebrew source, so the same title translated once serves every vote that carries it and a
  source correction (new hash) automatically re-queues the translation — this is the roadmap's "machine text is
  marked until reviewed; a change in the Hebrew puts it back in the queue" rule. `origin` ∈ `machine | editor`.
  Append-only migration `db/migrations/00NN_text_translation.sql`.
- **Translation job**: `hkv translate --lang en,ru [--missing]`, run inside `hkv update` for new titles. LLM with a
  fixed glossary and style sheet so 3,600 titles read consistently: הצעת חוק → *Bill*, חוק → *Law*, תיקון מס' N →
  *Amendment No. N*, חוק יסוד → *Basic Law*, הוראת שעה → *temporary provision*, the Hebrew year suffix
  (התשפ"ד-2024) → keep only the Gregorian year; ministries and law names from a glossary table; Russian keeps the
  established forms («Основной закон», «поправка №»). Automatic checks before a translation is stored: numbers and
  glossary terms preserved, no added facts, length within 2× of the source; failures go to `data_issue`. Cost is a
  few dollars for the whole backlog; store the model name per row.
- **API**: `title_en` / `title_ru` (null when missing) and `title_origin` on every bill and vote response; `?lang=`
  fills `title` through the mixins in `api/names.py`. Search indexes the translations too, so "capital market"
  finds the bill.
- **Web**: a `Title` component replaces the ad-hoc `<He>{title_he}</He>` in `VoteLine`, home, `/votes`, bill, topic
  and search lists and on the vote/bill page headers. Hebrew line as today; translation on the next line in the UI
  font; a muted "automatic translation" marker (`t.d.common.machine`) with a tooltip/link to the methodology
  paragraph on translations; when `origin = editor` the marker disappears. In compact lists the marker collapses to
  an icon-sized "auto" tag so it never takes a line of its own. Metadata `title` of the page uses the translation
  (the browser tab and share preview stop being Hebrew for en/ru readers).
- **Review**: L9's small review screen marks a translation `editor` and removes the tag; not needed to ship this.
- **Order**: this moves ahead of L10 Arabic UI strings and L7 descriptions; the interim idea of hand-written lines for
  key votes only (R5) stays for the summaries, which are not titles.

Acceptance: every list and page in `/en` and `/ru` shows a translated title under each Hebrew title within a day of
the vote appearing; a Hebrew source correction shows the Hebrew immediately and the old translation never.

### R5 — Key votes: "the votes that mattered" (S curation + S UI, before elections)

A curated list (`curated/key_votes.toml`, with an `evidence`/`why` field per the project's curated-data rule): ~20–30 final or no-confidence votes of the 25th Knesset that defined it (budget, judicial reform bills, draft law, …), each with a one-line title and a two-line summary in he/en/ru.

- Home hero shows them as swipeable cards; party page shows the party's choice on each; member page shows the MK's choice on each (R7).
- A `key` flag in the API (`/votes?key=true`) so the web stays thin.
- "Contested" remains the automatic fallback for Knessets with no curation.

### R6 — VoteMatch: "which party votes like you?" (M, the pre-election feature)

Twelve of the key votes (R5), each as a swipe card: *Should the Knesset have passed … ?* — For / Against / Skip. At the end: parties ranked by agreement with the visitor, with the denominator shown ("agrees with you on 9 of 12") and a link to each vote. No accounts, nothing stored server-side; result encoded in the share URL and rendered as an OG image (R9).

This is the one feature that is both catchy and strictly factual: the parties' answers are their real votes. It needs only R5's curated texts. Acceptance: finishes in under 60 seconds on a phone; result shareable.

### R7 — Member page: answer first (S)

- Add the missing "voted with the coalition N of M" (U11) and the MK's choice on the key votes (R5) above the tabs.
- Add a **topic filter** to the MK's vote list (the API's `/members/{id}/votes` needs `topic=`).
- "Against own party" tab → rename to "Broke with the party" and show the count in the tab label.
- The stats row moves below the votes; the factions table into a collapsed section.

### R8 — Search that feels instant (S)

Typeahead on the header and home search (members, parties, topics, with photos/flags), from the existing `/search` endpoint, 150 ms debounce, keyboard-navigable. Zero-result state suggests the three nearest names. Keep the full `/search` page for bills.

### R9 — Share cards (M, before elections if possible)

OpenGraph images (`/[lang]/votes/[id]/opengraph-image`, `…/parties/[slug]/opengraph-image`, `…/compass/…`, VoteMatch result) rendered with `next/og` from the same vote card: verdict line, one stacked bar, bloc line, site name. This is how the content travels on Telegram and WhatsApp; today the preview is a Hebrew title. Add a "Copy link" / "Share" button on vote, party and member pages (Web Share API on phones).

### R10 — Navigation and vocabulary (S)

- Mobile header: brand + search icon + menu; a bottom tab bar on phones (Parties · Topics · Votes · Members · Search) — the header currently wraps to three rows on a 390 px screen (brand, five links, full-width search, language switcher).
- One **Knesset switch** in the header (defaults to the current Knesset), applied to parties, members, topics and the matrix, instead of a `<select>` in a form per page.
- Drop the word "faction" from the UI language except in the glossary; "Parties" everywhere, with "(25th Knesset)" where the term matters.
- Breadcrumb line on detail pages ("Parties › Likud · 25th Knesset").
- The language switcher stays, but as a compact menu, not three inline links.

### R11 — Visual identity (S–M)

The current look is clean but generic (system font, grey cards). For "catchy and minimalistic":

- **One typeface for four scripts**: Rubik (Hebrew, Cyrillic, Latin, Arabic in one family; self-hosted via `next/font` — no Google request, matches the privacy stance) or Noto Sans. Headlines 32–40 px, big numerals with `tabular-nums`.
- Keep the diverging for/against palette; add a single **accent** (not blue, to avoid being read as "for") for interactive elements; coalition = filled badge, opposition = outlined, consistent everywhere.
- Fewer boxes: section titles and hairlines instead of nested cards; 24/32 px rhythm; 1,040 px max width with the content column at 680 px for text.
- Home: a hero with three big numbers ("17,319 votes · 1.2 M ballots · since 2003") and the key-vote cards; the four "Browse" tiles become the bottom tab bar / footer.
- Motion: none beyond a 150 ms hover/expand; respect `prefers-reduced-motion`.
- Dark mode is already tokenised; verify contrast of `--muted` on `--surface` (AA needs ≥ 4.5:1 for small text).

### R12 — Freshness and empty states (S)

- Recess banner on home and `/votes` ("The Knesset is in recess until …; elections on …; the 26th Knesset convenes 2026-11-10") from `KNS_KnessetDates` (U14).
- "Data updated 3 days ago" in the header area, not only the footer.
- Empty filters say what to try next; 404 pages offer search.

### R13 — Accessibility and performance budget (S)

- Lighthouse ≥ 95 on mobile for home, vote, party; LCP < 2 s on 4G; no layout shift from the photo.
- axe clean on every page; charts expose text (already partly done with `role="img"` + aria-label) — keep when the matrix lands.
- Keyboard path through typeahead, tabs and `<details>`; visible focus (exists).
- Screen-reader check in Hebrew (NVDA/VoiceOver) once per release; RTL sanity on Android Chrome.

### R14 — Compare (M, after elections)

U7 as designed: two parties or two MKs, agreement rate on shared final votes, then the votes where they differed. A party × party agreement heatmap is a strong visual for the matrix page later.

## 5. How to do the UX analysis (methods, in order of value for cost)

1. **Top-task benchmark (do first, 2 h).** Fix the 6 questions from §1. For each: the ideal path, the current path, number of taps, whether a ru/en reader can finish without Hebrew, and whether the answer is a *stance* or a *count*. Repeat after each release; this is the KPI ("seconds to an answer").
2. **Analytics baseline before changing anything (O6, 1 day).** Self-hosted Umami with events: search query (and zero results), filter chip, breakdown expand, outbound source click, share click, language switch. Two weeks of data tells you what people actually ask; search strings are the cheapest user research available.
3. **Think-aloud tests, 5 people per language (ru, he; en later), 20 min each, remote over a phone (1–2 days).** Recruit from the Russian-speaking Telegram groups the site targets. Script: "You are deciding whether to vote for X again. Find out how they voted on …", "Find your MK and see if they broke with their party", "Share this with a friend". Measure success, time, first tap, and the words they use (vocabulary feeds the dictionaries). Five people find ~80 % of the issues; more languages beat more people.
4. **Heuristic review with a civic-data checklist (half a day).** Nielsen's ten, plus: is the stance distinguishable from the count; is the denominator visible; is "no record" explained where it appears; does every number lead to its source in one tap; does every page have a one-sentence answer. Score 0–2 per page, keep the table in this file.
5. **Comparative review (half a day).** TheyWorkForYou (UK), GovTrack and VoteSmart (US), VoteWatch/HowTheyVote (EU), abgeordnetenwatch (DE), Open Knesset (IL) for structure; Wahl-O-Mat / Smartvote for the VoteMatch pattern; Datawrapper and the Guardian's election graphics for the matrix and bar visuals. Record what to borrow, not what they look like.
6. **Screenshot matrix for design review (done: `apps/web/scripts/screens.mjs`).** Captures home, votes, vote, party, member, topic, search at 390 px and 1,280 px in ru/en/he, light and dark — 84 images; add compass when it exists. Review them side by side (and let an AI reviewer go through them); re-run before every deploy to catch RTL and dark-mode regressions. Chromium is already available in CI.
7. **Five-second test on home and on the share image (free, 10 people).** Show for five seconds, ask "what is this site, what can you do here?" — the brand/tagline and OG card must pass this.
8. **Tree test for navigation labels (free tier of Optimal Workshop, or a Google Form).** Ten tasks against the proposed nav in each language; the Hebrew and Russian words for party/list/faction are the known trouble spot.
9. **Accessibility pass (half a day).** axe DevTools on every page, Lighthouse budget in CI, one screen-reader session in Hebrew, keyboard-only walk-through.
10. **Content test of the plain-language layer.** Give the verdict lines, stage hints and the glossary to three non-expert readers per language; ask them to retell each in their own words. Rewrite anything retold wrongly.

## 6. Suggested order

| When | Items | Outcome |
|---|---|---|
| Next two weeks (before elections) | R3 vote card, R10 nav/mobile, R12 recess banner, R1 party hub, R2 matrix, R5 key votes (curation starts day 1), R9 share cards, R8 typeahead | A voter can answer "how did my party vote" in two taps and share it as a picture |
| Right after, still in the campaign window | R6 VoteMatch, R7 member page, R4 interim labels, R11 identity | The catchy piece; the site has a face |
| After elections | L6/L7 (the real fix for R4), R14 compare, R13 budget in CI, Arabic (L10), methods 2–3 repeated on the new site | Sustained |

Measure with method 1 before and after each row.
