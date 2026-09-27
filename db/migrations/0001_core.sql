-- 0001: core schema for plenum roll-call votes (MVP, see docs/adr/0001-mvp-scope.md)
--
-- Conventions (architecture.md §4, adapted by ADR 0001):
--   * internal PK: uuid; official Knesset IDs live in knesset_* columns, UNIQUE per table.
--     Knesset v4 and legacy Votes.svc share vote/person IDs (docs/audit/source-audit.md), so one
--     namespace per entity is enough for now.
--   * validity intervals are half-open daterange [from, to); open end = NULL upper bound.
--   * unknown is NULL or an explicit status, never 0.
--   * every imported row points at the snapshot it was last read from (source_snapshot_id)
--     and keeps the source's LastUpdatedDate (source_updated_at).

CREATE EXTENSION IF NOT EXISTS btree_gist;

-- ---------------------------------------------------------------------------
-- Provenance
-- ---------------------------------------------------------------------------

CREATE TABLE source_snapshot (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source          text NOT NULL CHECK (source IN ('knesset_odata_v4', 'knesset_votes_legacy', 'oknesset_dump', 'manual')),
    resource        text NOT NULL,                 -- e.g. 'KNS_PlenumVoteResult'
    request         text NOT NULL,                 -- URL or file name incl. query
    fetched_at      timestamptz NOT NULL DEFAULT now(),
    content_sha256  text NOT NULL,
    object_key      text,                          -- where the raw payload is stored
    row_count       integer CHECK (row_count >= 0),
    ingestion_run_id uuid
);

CREATE TABLE ingestion_run (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source          text NOT NULL,
    resource        text NOT NULL,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    status          text NOT NULL DEFAULT 'running' CHECK (status IN ('running', 'succeeded', 'failed')),
    watermark_before jsonb,
    watermark_after  jsonb,
    counts          jsonb NOT NULL DEFAULT '{}',
    error           text
);

ALTER TABLE source_snapshot
    ADD CONSTRAINT source_snapshot_run_fk FOREIGN KEY (ingestion_run_id) REFERENCES ingestion_run (id);

-- Prior versions of rows that changed on re-import (filled by trigger, see bottom).
CREATE TABLE row_revision (
    id              bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    table_name      text NOT NULL,
    row_id          uuid NOT NULL,
    old_row         jsonb NOT NULL,
    superseded_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX row_revision_row_idx ON row_revision (table_name, row_id);

CREATE TABLE data_issue (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_table    text,
    entity_id       uuid,
    external_ref    text,                          -- when there is no core row yet
    issue_type      text NOT NULL,                 -- e.g. 'no_faction_on_vote_date', 'totals_mismatch'
    severity        text NOT NULL CHECK (severity IN ('info', 'warning', 'error')),
    details         jsonb NOT NULL DEFAULT '{}',
    status          text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'accepted', 'resolved', 'wontfix')),
    source_snapshot_id uuid REFERENCES source_snapshot (id),
    created_at      timestamptz NOT NULL DEFAULT now(),
    resolved_at     timestamptz
);
CREATE INDEX data_issue_open_idx ON data_issue (issue_type) WHERE status = 'open';

CREATE TABLE data_release (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    published_at    timestamptz NOT NULL DEFAULT now(),
    pipeline_version text NOT NULL,
    metric_version  text NOT NULL,
    coverage        jsonb NOT NULL DEFAULT '{}',   -- manifest: per term/year counts, known gaps
    notes           text
);

-- ---------------------------------------------------------------------------
-- Parliament, people, factions
-- ---------------------------------------------------------------------------

CREATE TABLE knesset_term (
    number          smallint PRIMARY KEY CHECK (number > 0),
    name_he         text,
    started_on      date NOT NULL,
    ended_on        date,
    CHECK (ended_on IS NULL OR ended_on >= started_on)
);

CREATE TABLE person (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    knesset_person_id integer NOT NULL UNIQUE,
    first_name_he   text NOT NULL,
    last_name_he    text NOT NULL,
    gender          text CHECK (gender IN ('male', 'female')),
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id)
);

CREATE TABLE person_alias (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       uuid NOT NULL REFERENCES person (id) ON DELETE CASCADE,
    language        text NOT NULL CHECK (language IN ('he', 'ru', 'en', 'ar')),
    full_name       text NOT NULL,
    alias_type      text NOT NULL CHECK (alias_type IN ('official', 'transliteration', 'former', 'source_variant')),
    origin          text NOT NULL CHECK (origin IN ('official', 'human', 'machine')),
    UNIQUE (person_id, language, full_name)
);
CREATE INDEX person_alias_name_idx ON person_alias (lower(full_name));

-- One row per continuous Knesset membership (PositionID 43/61). A gap = two rows.
CREATE TABLE mandate (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       uuid NOT NULL REFERENCES person (id),
    term_number     smallint NOT NULL REFERENCES knesset_term (number),
    valid           daterange NOT NULL CHECK (NOT isempty(valid) AND lower(valid) IS NOT NULL),
    knesset_position_row_id integer UNIQUE,        -- KNS_PersonToPosition.Id
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id),
    EXCLUDE USING gist (person_id WITH =, term_number WITH =, valid WITH &&)
);

CREATE TABLE faction (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    knesset_faction_id integer NOT NULL UNIQUE,
    term_number     smallint NOT NULL REFERENCES knesset_term (number),
    name_he         text NOT NULL,
    valid           daterange NOT NULL CHECK (lower(valid) IS NOT NULL),
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id)
);

CREATE TABLE faction_label (
    faction_id      uuid NOT NULL REFERENCES faction (id) ON DELETE CASCADE,
    language        text NOT NULL CHECK (language IN ('ru', 'en', 'ar')),
    name            text NOT NULL,
    short_name      text,
    origin          text NOT NULL CHECK (origin IN ('official', 'human', 'machine')),
    PRIMARY KEY (faction_id, language)
);

-- PositionID 54. Zero-length source intervals (start = finish) are not stored as memberships;
-- the importer records them as data_issue.
CREATE TABLE faction_membership (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    person_id       uuid NOT NULL REFERENCES person (id),
    faction_id      uuid NOT NULL REFERENCES faction (id),
    valid           daterange NOT NULL CHECK (NOT isempty(valid) AND lower(valid) IS NOT NULL),
    knesset_position_row_id integer UNIQUE,
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id),
    EXCLUDE USING gist (person_id WITH =, valid WITH &&)
);
CREATE INDEX faction_membership_faction_idx ON faction_membership USING gist (faction_id, valid);

CREATE TABLE government (
    number          smallint PRIMARY KEY CHECK (number > 0),
    term_number     smallint REFERENCES knesset_term (number),
    valid           daterange NOT NULL CHECK (lower(valid) IS NOT NULL),
    EXCLUDE USING gist (valid WITH &&)
);

-- Coalition / opposition. Curated (no single official table), so evidence is a free-text citation.
CREATE TABLE faction_alignment (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    faction_id      uuid NOT NULL REFERENCES faction (id),
    government_number smallint NOT NULL REFERENCES government (number),
    valid           daterange NOT NULL CHECK (NOT isempty(valid)),
    role            text NOT NULL CHECK (role IN ('coalition', 'opposition', 'external_support', 'unknown')),
    evidence        text NOT NULL,
    EXCLUDE USING gist (faction_id WITH =, valid WITH &&)
);

-- ---------------------------------------------------------------------------
-- Legislation (MVP subset of architecture.md §6)
-- ---------------------------------------------------------------------------

CREATE TABLE bill_status (
    knesset_status_id integer PRIMARY KEY,
    label_he        text NOT NULL,
    is_active       boolean,
    lifecycle       text CHECK (lifecycle IN ('pending', 'passed', 'rejected', 'withdrawn', 'merged', 'stopped', 'other'))
);

CREATE TABLE bill (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    knesset_bill_id integer NOT NULL UNIQUE,
    term_number     smallint NOT NULL REFERENCES knesset_term (number),  -- term the bill record belongs to
    title_he        text NOT NULL,
    origin_type     text CHECK (origin_type IN ('private', 'government', 'committee')),
    bill_number     integer,                       -- KNS_Bill.Number
    private_number  integer,                       -- KNS_Bill.PrivateNumber (P/…)
    status_id       integer REFERENCES bill_status (knesset_status_id),
    is_continuation boolean,
    published_on    date,
    summary_he      text,
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id)
);
CREATE INDEX bill_term_idx ON bill (term_number);

CREATE TABLE bill_relation (
    from_bill_id    uuid NOT NULL REFERENCES bill (id),
    to_bill_id      uuid NOT NULL REFERENCES bill (id),
    relation_type   text NOT NULL CHECK (relation_type IN ('union', 'split', 'continuation', 'related')),
    knesset_row_id  integer,                       -- KNS_BillUnion/KNS_BillSplit.Id
    PRIMARY KEY (from_bill_id, to_bill_id, relation_type),
    CHECK (from_bill_id <> to_bill_id)
);

CREATE TABLE bill_initiator (
    bill_id         uuid NOT NULL REFERENCES bill (id) ON DELETE CASCADE,
    person_id       uuid NOT NULL REFERENCES person (id),
    role            text NOT NULL CHECK (role IN ('initiator', 'joined', 'withdrew')),
    ordinal         smallint,
    PRIMARY KEY (bill_id, person_id, role)
);

-- ---------------------------------------------------------------------------
-- Votes (architecture.md §7)
-- ---------------------------------------------------------------------------

CREATE TABLE plenum_session (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    knesset_session_id integer NOT NULL UNIQUE,
    term_number     smallint NOT NULL REFERENCES knesset_term (number),
    official_number integer,
    started_at      timestamptz,
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id)
);

-- Classification of the question put to vote, keyed by the stable Knesset option ID.
CREATE TABLE vote_option_kind (
    knesset_option_id integer PRIMARY KEY,
    label_he        text NOT NULL,
    motion_type     text NOT NULL CHECK (motion_type IN ('adopt_bill', 'reject_bill', 'adopt_section', 'reservation',
                                                         'no_confidence', 'agenda', 'secondary_legislation', 'procedural', 'other', 'unknown')),
    stage           text NOT NULL CHECK (stage IN ('preliminary', 'first', 'second', 'third', 'not_applicable', 'unknown')),
    reviewed        boolean NOT NULL DEFAULT false
);

CREATE TABLE vote (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    knesset_vote_id integer NOT NULL UNIQUE,       -- shared by OData v4 and legacy Votes.svc
    session_id      uuid REFERENCES plenum_session (id),
    knesset_item_id integer,                       -- agenda item; = KNS_Bill.Id for bills
    term_number     smallint NOT NULL REFERENCES knesset_term (number),
    occurred_at     timestamptz,
    occurred_on     date NOT NULL,                 -- Asia/Jerusalem calendar date
    ordinal         integer,
    title_he        text NOT NULL,
    subject_he      text,                          -- VoteSubject, e.g. 'סעיפים 1–13'
    for_option_id   integer REFERENCES vote_option_kind (knesset_option_id),
    for_option_he   text,
    against_option_id integer,
    against_option_he text,
    method          text NOT NULL CHECK (method IN ('electronic', 'roll_call', 'show_of_hands_counted', 'show_of_hands', 'secret', 'unknown')),
    is_no_confidence boolean,
    status          text NOT NULL DEFAULT 'valid' CHECK (status IN ('valid', 'cancelled', 'superseded', 'pending_verification')),
    source_status_code smallint,
    present_in      text[] NOT NULL CHECK (present_in <@ ARRAY['knesset_odata_v4', 'knesset_votes_legacy']::text[] AND cardinality(present_in) > 0),
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id),
    CHECK (occurred_at IS NULL OR (occurred_at AT TIME ZONE 'Asia/Jerusalem')::date = occurred_on)
);
CREATE INDEX vote_occurred_idx ON vote (occurred_on, id);
CREATE INDEX vote_session_idx ON vote (session_id, ordinal);
CREATE INDEX vote_item_idx ON vote (knesset_item_id);
CREATE INDEX vote_option_idx ON vote (for_option_id, occurred_on);

CREATE TABLE vote_subject (
    vote_id         uuid NOT NULL REFERENCES vote (id) ON DELETE CASCADE,
    bill_id         uuid NOT NULL REFERENCES bill (id),
    link_method     text NOT NULL CHECK (link_method IN ('item_id', 'manual')),
    verified        boolean NOT NULL DEFAULT false,
    PRIMARY KEY (vote_id, bill_id)
);
CREATE INDEX vote_subject_bill_idx ON vote_subject (bill_id, vote_id);

-- Official totals (legacy Votes.svc header; not available in OData v4).
CREATE TABLE vote_result_official (
    vote_id         uuid PRIMARY KEY REFERENCES vote (id) ON DELETE CASCADE,
    for_count       smallint NOT NULL CHECK (for_count >= 0),
    against_count   smallint NOT NULL CHECK (against_count >= 0),
    abstain_count   smallint NOT NULL CHECK (abstain_count >= 0),
    is_accepted     boolean,
    source          text NOT NULL CHECK (source IN ('knesset_votes_legacy', 'knesset_website', 'manual')),
    source_snapshot_id uuid REFERENCES source_snapshot (id)
);

-- One current row per (vote, person). Source codes (v4 ResultCode):
--   7 for, 8 against, 9 abstain -> participation 'cast'
--   6 present                   -> 'present_not_voting'
--   11 voted, choice unknown    -> 'participated_choice_unavailable'
--   10 not present              -> 'absent_reported'
-- No row for an MK does NOT mean absent (docs/audit/source-audit.md §3).
CREATE TABLE ballot (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    vote_id         uuid NOT NULL REFERENCES vote (id) ON DELETE CASCADE,
    person_id       uuid NOT NULL REFERENCES person (id),
    mandate_id      uuid REFERENCES mandate (id),
    choice          text CHECK (choice IN ('for', 'against', 'abstain')),
    participation   text NOT NULL CHECK (participation IN ('cast', 'present_not_voting', 'declared_nonparticipation',
                                                           'absent_reported', 'participated_choice_unavailable', 'unknown')),
    source_result_code smallint NOT NULL,
    -- legacy vote_rslts_kmmbr_shadow.reason; 5 = not included in official totals (audit §4). NULL = no legacy row.
    legacy_reason   smallint,
    counted_in_official_total boolean,             -- NULL when unknowable (v4-only votes)
    -- faction at vote time (architecture.md §5): resolved from faction_membership
    faction_id      uuid REFERENCES faction (id),
    faction_method  text NOT NULL DEFAULT 'unresolved' CHECK (faction_method IN ('temporal_join', 'source', 'manual', 'unresolved')),
    faction_ambiguous boolean NOT NULL DEFAULT false,
    knesset_ballot_id integer UNIQUE,              -- KNS_PlenumVoteResult.Id; NULL for legacy-only votes
    voted_at        timestamptz,
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id),
    UNIQUE (vote_id, person_id),
    CHECK ((participation = 'cast') = (choice IS NOT NULL)),
    CHECK (faction_method = 'unresolved' OR faction_id IS NOT NULL)
);
CREATE INDEX ballot_person_idx ON ballot (person_id, vote_id);
CREATE INDEX ballot_faction_idx ON ballot (faction_id, vote_id);

-- ---------------------------------------------------------------------------
-- Revision capture: an UPDATE of imported facts keeps the previous version.
-- ---------------------------------------------------------------------------

CREATE FUNCTION capture_revision() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF to_jsonb(OLD) - 'source_snapshot_id' IS DISTINCT FROM to_jsonb(NEW) - 'source_snapshot_id' THEN
        INSERT INTO row_revision (table_name, row_id, old_row) VALUES (TG_TABLE_NAME, OLD.id, to_jsonb(OLD));
    END IF;
    RETURN NEW;
END $$;

CREATE TRIGGER vote_revision BEFORE UPDATE ON vote FOR EACH ROW EXECUTE FUNCTION capture_revision();
CREATE TRIGGER ballot_revision BEFORE UPDATE ON ballot FOR EACH ROW EXECUTE FUNCTION capture_revision();
CREATE TRIGGER faction_membership_revision BEFORE UPDATE ON faction_membership FOR EACH ROW EXECUTE FUNCTION capture_revision();
CREATE TRIGGER mandate_revision BEFORE UPDATE ON mandate FOR EACH ROW EXECUTE FUNCTION capture_revision();
