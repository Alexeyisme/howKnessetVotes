-- What the sides argued and what the opposition objected to (roadmap L7, steps 2 and 3).
--
-- plenum_document mirrors KNS_DocumentPlenumSession: the official files of a plenum sitting, above all the full
-- transcript ("דברי הכנסת", group 28). Loaded only for the sittings we need.
--
-- bill_debate is the plenum debate on a bill that reached a final (third-reading) vote: its agenda items cut out of
-- the transcripts of every sitting where the bill was voted on (preliminary, first, second/third reading; hkv.debate).
-- The speakers are listed from the transcripts themselves, without a model: name and affiliation as printed,
-- resolved to a member and the faction they belonged to on the day of their first speech where possible. summary_he and
-- the arguments are machine-written Hebrew; each argument points to the speakers (ordinals) it comes from.
--
-- bill_reservations are the reservations filed for the second reading, from the committee's version of the bill
-- (hkv.reservations): who proposed how many changes to which sections, and who asked to speak. Counts come from the
-- reservation numbers printed in the document; the model only says which numbers belong to whom, and the job checks
-- that the numbers it assigned are exactly the ones printed.
--
-- Machine Hebrew texts here are translated like every other text (text_translation, kind "positions").

CREATE TABLE plenum_document (
    knesset_document_id integer PRIMARY KEY,       -- KNS_DocumentPlenumSession.Id
    session_id      uuid NOT NULL REFERENCES plenum_session (id) ON DELETE CASCADE,
    group_type_id   integer NOT NULL,              -- 28 transcript ("דברי הכנסת")
    group_type_he   text,
    format          text,
    url             text NOT NULL,
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id)
);
CREATE INDEX plenum_document_session_idx ON plenum_document (session_id, group_type_id);

CREATE TABLE bill_debate (
    bill_id         uuid PRIMARY KEY REFERENCES bill (id) ON DELETE CASCADE,
    vote_id         uuid NOT NULL REFERENCES vote (id) ON DELETE CASCADE,   -- the final vote
    document_ids    integer[] NOT NULL,            -- plenum_document rows the segments come from
    file_sha256     text[] NOT NULL,
    segment_titles  text[] NOT NULL,               -- the agenda items as printed in the transcripts
    chars           integer NOT NULL,              -- length of the speeches sent to the model
    truncated       boolean NOT NULL,              -- long debates: every speech was shortened to fit
    summary_he      text NOT NULL CHECK (length(summary_he) > 0),
    arguments       jsonb NOT NULL,                -- [{"side": "for"|"against", "text_he": …, "speakers": [ordinal…]}]
    origin          text NOT NULL DEFAULT 'machine' CHECK (origin IN ('machine', 'editor')),
    model           text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    reviewed_at     timestamptz
);

CREATE TABLE bill_debate_speaker (
    bill_id         uuid NOT NULL REFERENCES bill_debate (bill_id) ON DELETE CASCADE,
    ordinal         smallint NOT NULL,             -- order of first speech
    label_he        text NOT NULL,                 -- as printed: "משה טור פז (יש עתיד)"
    name_he         text NOT NULL,
    affiliation_he  text,                          -- the parenthesis: faction, or "בשם ועדת …"
    person_id       uuid REFERENCES person (id),
    faction_id      uuid REFERENCES faction (id),  -- the person's faction on the day of their first speech
    speeches        smallint NOT NULL,
    chars           integer NOT NULL,
    stages          text[] NOT NULL,               -- readings they spoke at: preliminary, first, third
    PRIMARY KEY (bill_id, ordinal)
);

CREATE TABLE bill_reservations (
    bill_id         uuid PRIMARY KEY REFERENCES bill (id) ON DELETE CASCADE,
    document_id     integer NOT NULL REFERENCES bill_document (knesset_document_id),
    file_sha256     text NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),
    total           integer NOT NULL CHECK (total >= 0),   -- numbered reservations in the document
    numbers_checked boolean NOT NULL,              -- the numbers were checked against the document's text (false:
                                                   -- the PDF's text has no usable numbers, the model read the pages)
    summary_he      text,                                  -- null when there are none
    origin          text NOT NULL DEFAULT 'machine' CHECK (origin IN ('machine', 'editor')),
    model           text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    reviewed_at     timestamptz
);

-- A proposer as the document names it: a group ("קבוצת יש עתיד") or a single member.
CREATE TABLE bill_reservation_group (
    bill_id         uuid NOT NULL REFERENCES bill_reservations (bill_id) ON DELETE CASCADE,
    ordinal         smallint NOT NULL,
    label_he        text NOT NULL,
    numbers         integer[] NOT NULL,            -- the reservation numbers it (co-)proposed
    sections        text[] NOT NULL,               -- "לסעיף 1", as printed
    gist_he         text,                          -- one machine sentence: what its reservations would change
    PRIMARY KEY (bill_id, ordinal)
);

CREATE TABLE bill_reservation_person (
    bill_id         uuid NOT NULL REFERENCES bill_reservations (bill_id) ON DELETE CASCADE,
    role            text NOT NULL CHECK (role IN ('proposer', 'speaker')),   -- speaker: asked to speak (בקשת רשות דיבור)
    ordinal         smallint NOT NULL,
    group_ordinal   smallint,                      -- proposers: their group
    name_he         text NOT NULL,                 -- as printed
    person_id       uuid REFERENCES person (id),
    faction_id      uuid REFERENCES faction (id),  -- on the date of the final vote
    PRIMARY KEY (bill_id, role, ordinal)
);
