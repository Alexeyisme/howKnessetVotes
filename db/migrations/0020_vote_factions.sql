-- Factions on each side of a vote: how many factions' majorities voted for and how many against. Unlike vote_bloc
-- (coalition vs opposition), this needs no government, so it also shows the fights while a new government is being
-- formed. Rebuilt from ballots by hkv.coalition.refresh_blocs, next to vote_bloc. A faction is on a side when a
-- strict majority of its members who voted (for/against/abstain) chose it; opposed = factions on both sides.

CREATE TABLE vote_factions (
    vote_id           uuid PRIMARY KEY REFERENCES vote (id) ON DELETE CASCADE,
    factions_for      integer NOT NULL,
    factions_against  integer NOT NULL,
    opposed           boolean GENERATED ALWAYS AS (factions_for > 0 AND factions_against > 0) STORED
);
CREATE INDEX vote_factions_opposed_idx ON vote_factions (vote_id) WHERE opposed;
