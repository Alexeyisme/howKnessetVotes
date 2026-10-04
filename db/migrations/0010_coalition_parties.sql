-- Governments, coalition membership and party lineage (docs/roadmap.md D2, D3).
--
-- Coalition membership is derived, not curated: KNS_PersonToPosition lists every minister and deputy minister with
-- the government number and dates. A faction is in the coalition on a date when one of its members holds a post in
-- that day's government; otherwise it is in the opposition. Known exceptions (a party that left the government but
-- not the coalition, outside support) are overrides in src/hkv/coalition/overrides.toml, stored with origin 'curated'.

CREATE TABLE gov_position (
    knesset_position_row_id integer PRIMARY KEY,     -- KNS_PersonToPosition.Id
    person_id         uuid REFERENCES person (id),   -- NULL: not an MK we know (e.g. a minister who never sat in the Knesset)
    knesset_person_id integer NOT NULL,
    government_number smallint NOT NULL,
    position_id       integer NOT NULL,              -- KNS_Position: 45 PM, 39/57 minister, 40/59/285079 deputy minister, ...
    ministry_he       text,
    duty_he           text,
    valid             daterange NOT NULL CHECK (NOT isempty(valid)),
    source_updated_at timestamptz,
    source_snapshot_id uuid REFERENCES source_snapshot (id)
);
CREATE INDEX gov_position_person_idx ON gov_position (person_id);
CREATE INDEX gov_position_valid_idx ON gov_position USING gist (valid);

-- government (0001) gets the prime minister; rows are derived from gov_position
ALTER TABLE government ADD COLUMN prime_minister_person_id uuid REFERENCES person (id);

ALTER TABLE faction_alignment ADD COLUMN origin text NOT NULL DEFAULT 'derived' CHECK (origin IN ('derived', 'curated'));

-- A party across Knessets: per-term factions linked to the party they belong to. A joint list belongs to every
-- member party (Likud Yisrael Beytenu -> likud and yisrael-beytenu). Curated: src/hkv/names/curated/parties.toml.
CREATE TABLE party (
    slug              text PRIMARY KEY CHECK (slug ~ '^[a-z0-9-]+$'),
    name_he           text NOT NULL,
    name_ru           text NOT NULL,
    name_en           text NOT NULL,
    sort              integer NOT NULL DEFAULT 0
);

CREATE TABLE party_faction (
    party_slug        text NOT NULL REFERENCES party (slug) ON DELETE CASCADE,
    faction_id        uuid NOT NULL REFERENCES faction (id) ON DELETE CASCADE,
    PRIMARY KEY (party_slug, faction_id)
);
CREATE INDEX party_faction_faction_idx ON party_faction (faction_id);
