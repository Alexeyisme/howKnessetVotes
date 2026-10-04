-- Coalition vs opposition per vote (docs/roadmap.md U11, "contested votes"). Rebuilt from ballots and
-- faction_alignment by hkv.coalition.refresh_blocs after every derivation. Counts are cast votes of members whose
-- faction had that role on the vote date; contested = both blocs had a strict majority and they differed.

CREATE TABLE vote_bloc (
    vote_id             uuid PRIMARY KEY REFERENCES vote (id) ON DELETE CASCADE,
    coalition_for       integer NOT NULL,
    coalition_against   integer NOT NULL,
    coalition_abstain   integer NOT NULL,
    opposition_for      integer NOT NULL,
    opposition_against  integer NOT NULL,
    opposition_abstain  integer NOT NULL,
    contested           boolean NOT NULL
);
CREATE INDEX vote_bloc_contested_idx ON vote_bloc (vote_id) WHERE contested;
