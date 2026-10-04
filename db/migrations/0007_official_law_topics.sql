-- Official classification of laws as a topic source (docs/roadmap.md T1).
-- KNS_LawBinding links a bill to the law(s) it creates or amends; KNS_IsraelLawClassificiation (sic) puts each law
-- into one or more of 51 official categories. A bill inherits the categories of the laws it binds to.

CREATE TABLE israel_law (
    id                integer PRIMARY KEY,          -- KNS_IsraelLaw.Id
    name_he           text NOT NULL,
    is_basic_law      boolean NOT NULL DEFAULT false,
    is_budget_law     boolean NOT NULL DEFAULT false
);

CREATE TABLE israel_law_classification (
    israel_law_id     integer NOT NULL,
    classification_id integer NOT NULL,
    label_he          text NOT NULL,
    PRIMARY KEY (israel_law_id, classification_id)
);

CREATE TABLE bill_law (
    bill_id           uuid NOT NULL REFERENCES bill (id) ON DELETE CASCADE,
    israel_law_id     integer NOT NULL,
    binding_type_he   text,
    -- the law named in the bill's title (an omnibus bill without one keeps every binding as primary);
    -- other bindings are consequential amendments and give no topic
    is_primary        boolean NOT NULL DEFAULT true,
    PRIMARY KEY (bill_id, israel_law_id)
);
CREATE INDEX bill_law_law_idx ON bill_law (israel_law_id);

ALTER TABLE bill_topic DROP CONSTRAINT bill_topic_origin_check;
ALTER TABLE bill_topic ADD CONSTRAINT bill_topic_origin_check CHECK (origin IN ('official', 'rule', 'machine', 'human'));
