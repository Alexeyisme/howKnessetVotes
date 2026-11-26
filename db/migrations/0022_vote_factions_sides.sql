-- Which factions were on each side of a vote, not only how many: "factions: 6 for, 4 against" does not say who.
-- Knesset faction ids, the faction with the most votes cast first. Written by hkv.coalition.refresh_blocs with the
-- rest of the row, so they are NULL until its next run (every `hkv update`).

ALTER TABLE vote_factions ADD COLUMN for_factions integer[], ADD COLUMN against_factions integer[];
