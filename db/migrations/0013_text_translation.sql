-- Machine translations of Hebrew source strings (bill and vote titles first; docs/ux-requirements.md R4).
-- Keyed by the SHA-256 of the Hebrew text, so one translation serves every row carrying the same title and a
-- corrected Hebrew source automatically has no translation until the job runs again. origin says who wrote it:
-- 'machine' until a person reviews it ('editor'); the site marks machine text as automatic.

CREATE TABLE text_translation (
    source_sha256   text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    language        text NOT NULL CHECK (language IN ('en', 'ru', 'ar')),
    text            text NOT NULL CHECK (length(text) > 0),
    origin          text NOT NULL DEFAULT 'machine' CHECK (origin IN ('machine', 'editor')),
    model           text,                      -- the model that produced a machine translation
    created_at      timestamptz NOT NULL DEFAULT now(),
    reviewed_at     timestamptz,
    PRIMARY KEY (source_sha256, language)
);

-- Corrections proposed by visitors (never applied automatically; an editor accepts one in the review queue).
-- source_sha256 is null for a general "report a mistake" about a page.
CREATE TABLE translation_suggestion (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_sha256   text CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),
    language        text NOT NULL CHECK (language IN ('he', 'en', 'ru', 'ar')),
    page            text,
    suggested_text  text NOT NULL CHECK (length(suggested_text) BETWEEN 1 AND 2000),
    note            text CHECK (length(note) <= 2000),
    ip_hash         text NOT NULL,              -- sha256(ip + day): enough for a rate limit, not an identity
    status          text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'accepted', 'rejected')),
    created_at      timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX translation_suggestion_open_idx ON translation_suggestion (created_at) WHERE status = 'open';
CREATE INDEX translation_suggestion_ip_idx ON translation_suggestion (ip_hash, created_at);

-- The hash of a Hebrew string as the translation table keys it (same bytes as Python's hashlib on UTF-8).
-- convert_to is not marked immutable although the encoding is fixed here; the wrapper is, so it can be indexed.
CREATE FUNCTION title_sha(t text) RETURNS text
    LANGUAGE sql IMMUTABLE STRICT PARALLEL SAFE
    AS $$ SELECT encode(sha256(convert_to(t, 'UTF8')), 'hex') $$;

-- the API joins translations to titles by hash; the expression index keeps that a lookup, not a scan
CREATE INDEX bill_title_sha_idx ON bill (title_sha(title_he));
CREATE INDEX vote_title_sha_idx ON vote (title_sha(title_he));
