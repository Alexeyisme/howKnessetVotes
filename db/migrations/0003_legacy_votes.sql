-- Legacy Votes.svc (2003 - 2021-07): official totals, votes missing from OData v4, and per-MK
-- flags for ballots not included in the official totals. See docs/audit/source-audit.md §4-5.

-- Loaders may be running: take both locks up front, ballot first (loaders hold ballot and then need
-- vote for FK checks), so this migration waits instead of deadlocking.
SET LOCAL lock_timeout = '60s';
LOCK TABLE ballot, vote IN ACCESS EXCLUSIVE MODE;

-- Votes known only from the legacy source have no ForOptionID; classify them directly.
-- API and statistics use coalesce(vote_option_kind.*, vote.*).
ALTER TABLE vote
    ADD COLUMN motion_type text CHECK (motion_type IN ('adopt_bill', 'reject_bill', 'adopt_section', 'reservation', 'no_confidence',
                                                      'agenda', 'secondary_legislation', 'procedural', 'other', 'unknown')),
    ADD COLUMN stage text CHECK (stage IN ('preliminary', 'first', 'second', 'third', 'not_applicable', 'unknown')),
    ADD COLUMN legacy_item_he text;               -- View_vote_rslts_hdr_Approved.vote_item_dscr, e.g. 'הסתייגות'

-- Where the ballot row came from. For 'knesset_votes_legacy' source_result_code is the legacy
-- vote_result (1 for, 2 against, 3 abstain, 4 did not vote/present, 0 cancelled).
ALTER TABLE ballot
    ADD COLUMN source text NOT NULL DEFAULT 'knesset_odata_v4' CHECK (source IN ('knesset_odata_v4', 'knesset_votes_legacy'));

-- Legacy kmmbr_id is a separate "vip" ID: equal to KNS_Person.Id for long-serving MKs, different for
-- newer ones. Resolved by name among MKs holding a mandate at the vote date, never by ID alone.
CREATE TABLE legacy_person_map (
    vip_id          integer PRIMARY KEY,
    person_id       uuid NOT NULL REFERENCES person (id),
    name_he         text NOT NULL,                -- legacy kmmbr_name as seen
    method          text NOT NULL CHECK (method IN ('id_and_name', 'full_name', 'last_name', 'manual')),
    resolved_at     timestamptz NOT NULL DEFAULT now()
);

-- Filling fields from a second source is enrichment, not a correction of the fact.
DROP TRIGGER vote_revision ON vote;
CREATE TRIGGER vote_revision BEFORE UPDATE ON vote FOR EACH ROW
    EXECUTE FUNCTION capture_revision('present_in', 'motion_type', 'stage', 'legacy_item_he');
DROP TRIGGER ballot_revision ON ballot;
CREATE TRIGGER ballot_revision BEFORE UPDATE ON ballot FOR EACH ROW
    EXECUTE FUNCTION capture_revision('faction_id', 'faction_method', 'faction_ambiguous', 'mandate_id',
                                      'legacy_reason', 'counted_in_official_total');
