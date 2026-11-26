-- How many factions took part in a vote, and how many there were. "44 for, 0 against" reads as agreement; when six of
-- eleven factions cast no vote at all it was one side voting alone (26th Knesset, 2026-11-18, votes 46728 and 46732).
-- factions_voted = factions with at least one for/against/abstain record; factions_total = factions of the vote's
-- Knesset with at least one member on the vote date. Written by hkv.coalition.refresh_blocs with the rest of the row,
-- so they are NULL until its next run (every `hkv update`).

ALTER TABLE vote_factions ADD COLUMN factions_voted integer, ADD COLUMN factions_total integer;
