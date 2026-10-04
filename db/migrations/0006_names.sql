-- Names in he/en/ru for members and factions (docs/roadmap.md L1, L2).
--   origin: official = Knesset (OData or website API); wikidata; curated = hand-maintained list in the repo
--           (src/hkv/names/curated); human = approved by an editor; machine = generated, unreviewed.
--   alias_type 'variant': other spellings and nicknames used only for search.

ALTER TABLE person_alias DROP CONSTRAINT person_alias_alias_type_check;
ALTER TABLE person_alias ADD CONSTRAINT person_alias_alias_type_check
    CHECK (alias_type IN ('official', 'transliteration', 'former', 'source_variant', 'variant'));
ALTER TABLE person_alias DROP CONSTRAINT person_alias_origin_check;
ALTER TABLE person_alias ADD CONSTRAINT person_alias_origin_check
    CHECK (origin IN ('official', 'wikidata', 'curated', 'human', 'machine'));
CREATE INDEX person_alias_trgm_idx ON person_alias USING gin (lower(full_name) gin_trgm_ops);

ALTER TABLE faction_label DROP CONSTRAINT faction_label_origin_check;
ALTER TABLE faction_label ADD CONSTRAINT faction_label_origin_check
    CHECK (origin IN ('official', 'wikidata', 'curated', 'human', 'machine'));
CREATE INDEX faction_label_trgm_idx ON faction_label USING gin (lower(name) gin_trgm_ops);

-- IDs of the same person in other systems: the Knesset website (mk_individual_id, Wikidata P9770) and Wikidata.
CREATE TABLE person_external_id (
    person_id       uuid NOT NULL REFERENCES person (id) ON DELETE CASCADE,
    scheme          text NOT NULL CHECK (scheme IN ('knesset_site', 'wikidata')),
    value           text NOT NULL,
    method          text NOT NULL,            -- how the link was made: 'kns_mksitecode', 'site_current_list', 'wikidata_label', 'curated'
    PRIMARY KEY (person_id, scheme),
    UNIQUE (scheme, value)
);

-- Display name per person and language: the best available origin wins.
CREATE VIEW person_name AS
SELECT p.id AS person_id,
       p.first_name_he || ' ' || p.last_name_he AS he,
       (SELECT a.full_name FROM person_alias a WHERE a.person_id = p.id AND a.language = 'en' AND a.alias_type = 'official'
          ORDER BY array_position(ARRAY['human', 'official', 'curated', 'wikidata', 'machine'], a.origin) LIMIT 1) AS en,
       (SELECT a.full_name FROM person_alias a WHERE a.person_id = p.id AND a.language = 'ru' AND a.alias_type = 'official'
          ORDER BY array_position(ARRAY['human', 'official', 'curated', 'wikidata', 'machine'], a.origin) LIMIT 1) AS ru
FROM person p;
