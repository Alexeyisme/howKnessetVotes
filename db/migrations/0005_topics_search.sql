-- Topics (architecture.md §9, MVP subset) and search.
-- Official Knesset data stays separate from our classification: topics are editorial, every assignment
-- records how it was made and whether a person has reviewed it.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Hebrew normalisation for search (same rules as hkv.topics.he_norm): drop niqqud/cantillation (U+0591..U+05C7 except maqaf U+05BE);
-- maqaf and dashes become spaces; quote marks, geresh and gershayim are removed, so מע"מ = מע״מ = מעמ.
-- translate(): the first four characters map to spaces, the remaining five have no counterpart and are deleted.
CREATE FUNCTION he_norm(t text) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT btrim(lower(regexp_replace(
               translate(regexp_replace(coalesce(t, ''), '[\u0591-\u05BD\u05BF-\u05C7]', '', 'g'),
                         U&'\05BE\2013\2014-\05F4"\05F3''`', '    '),
               '\s+', ' ', 'g')))
$$;

CREATE INDEX bill_title_trgm ON bill USING gin (he_norm(title_he) gin_trgm_ops);
CREATE INDEX person_name_trgm ON person USING gin (he_norm(first_name_he || ' ' || last_name_he) gin_trgm_ops);
CREATE INDEX faction_name_trgm ON faction USING gin (he_norm(name_he) gin_trgm_ops);

CREATE TABLE topic (
    id              serial PRIMARY KEY,
    slug            text NOT NULL UNIQUE CHECK (slug ~ '^[a-z0-9-]+$'),
    parent_id       integer REFERENCES topic (id),
    sort            integer NOT NULL DEFAULT 0,
    CHECK (parent_id IS DISTINCT FROM id)
);

CREATE TABLE topic_label (
    topic_id        integer NOT NULL REFERENCES topic (id) ON DELETE CASCADE,
    language        text NOT NULL CHECK (language IN ('ru', 'he', 'en', 'ar')),
    label           text NOT NULL,
    description     text,
    PRIMARY KEY (topic_id, language)
);

-- Words people use for a topic (search); keywords used by the rule classifier live in code with the taxonomy.
CREATE TABLE topic_alias (
    topic_id        integer NOT NULL REFERENCES topic (id) ON DELETE CASCADE,
    language        text NOT NULL CHECK (language IN ('ru', 'he', 'en', 'ar')),
    alias           text NOT NULL,
    PRIMARY KEY (topic_id, language, alias)
);
CREATE INDEX topic_alias_trgm ON topic_alias USING gin (lower(alias) gin_trgm_ops);

CREATE TABLE bill_topic (
    bill_id         uuid NOT NULL REFERENCES bill (id) ON DELETE CASCADE,
    topic_id        integer NOT NULL REFERENCES topic (id) ON DELETE CASCADE,
    origin          text NOT NULL CHECK (origin IN ('rule', 'machine', 'human')),
    evidence        text,                          -- e.g. the keyword that matched
    review_state    text NOT NULL DEFAULT 'unreviewed' CHECK (review_state IN ('unreviewed', 'accepted', 'rejected')),
    rules_version   text,
    assigned_at     timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (bill_id, topic_id)
);
CREATE INDEX bill_topic_topic_idx ON bill_topic (topic_id, bill_id) WHERE review_state <> 'rejected';
