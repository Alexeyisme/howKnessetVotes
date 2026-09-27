-- Adjustments found by loading real data.

-- Term 0 exists: the Provisional State Council (מועצת המדינה הזמנית, 1948-1949).
ALTER TABLE knesset_term DROP CONSTRAINT knesset_term_number_check;
ALTER TABLE knesset_term ADD CONSTRAINT knesset_term_number_check CHECK (number >= 0);

-- Some KNS_Status rows have no description (e.g. 6015).
ALTER TABLE bill_status ALTER COLUMN label_he DROP NOT NULL;

-- Revisions record source facts only. Columns derived by the pipeline (faction/mandate at vote time)
-- are recomputable from faction_membership/mandate history, so their changes are not revisions.
-- Trigger arguments = columns to ignore in addition to source_snapshot_id.
CREATE OR REPLACE FUNCTION capture_revision() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    ignored text[] := array_append(TG_ARGV::text[], 'source_snapshot_id');
BEGIN
    IF (to_jsonb(OLD) - ignored) IS DISTINCT FROM (to_jsonb(NEW) - ignored) THEN
        INSERT INTO row_revision (table_name, row_id, old_row) VALUES (TG_TABLE_NAME, OLD.id, to_jsonb(OLD));
    END IF;
    RETURN NEW;
END $$;

DROP TRIGGER ballot_revision ON ballot;
CREATE TRIGGER ballot_revision BEFORE UPDATE ON ballot FOR EACH ROW
    EXECUTE FUNCTION capture_revision('faction_id', 'faction_method', 'faction_ambiguous', 'mandate_id');
