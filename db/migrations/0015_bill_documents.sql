-- Bill documents and descriptions from the sponsors' explanatory notes (roadmap L7).
--
-- bill_document mirrors KNS_DocumentBill: every official file of a bill (the proposal for each reading, committee
-- versions, debate excerpts), with its link on fs.knesset.gov.il. Steps 2 and 3 of L7 (debate, reservations) read the
-- same table.
--
-- bill_explanation is a short machine summary of the explanatory notes ("דברי הסבר") of the proposal, for voted bills
-- without an official SummaryLaw. The notes are written by the sponsors, so the site labels the text "according to the
-- sponsors". It is Hebrew; text_translation carries en/ru/ar keyed by the hash of summary_he, like titles.

CREATE TABLE bill_document (
    knesset_document_id integer PRIMARY KEY,       -- KNS_DocumentBill.Id
    bill_id         uuid NOT NULL REFERENCES bill (id) ON DELETE CASCADE,
    group_type_id   integer NOT NULL,              -- 1 preliminary, 2 first reading, 4/101 committee version, 15/45 debate…
    group_type_he   text,
    format          text,                          -- ApplicationDesc: DOC, PDF…
    url             text NOT NULL,
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id)
);
CREATE INDEX bill_document_bill_idx ON bill_document (bill_id, group_type_id);

CREATE TABLE bill_explanation (
    bill_id         uuid PRIMARY KEY REFERENCES bill (id) ON DELETE CASCADE,
    document_id     integer NOT NULL REFERENCES bill_document (knesset_document_id),
    file_sha256     text NOT NULL CHECK (file_sha256 ~ '^[0-9a-f]{64}$'),   -- the file the summary was made from
    notes_he        text,                          -- the notes as extracted; null when the model read a PDF itself
    summary_he      text NOT NULL CHECK (length(summary_he) > 0),
    origin          text NOT NULL DEFAULT 'machine' CHECK (origin IN ('machine', 'editor')),
    model           text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    reviewed_at     timestamptz
);
CREATE INDEX bill_explanation_sha_idx ON bill_explanation (title_sha(summary_he));
