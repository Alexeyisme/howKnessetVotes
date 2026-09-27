-- Legacy names differ in plene spelling (סידה / סיידה, לזמי / לזימי) and compound surnames (הילה וזאן / הילה שי וזאן).
SET LOCAL lock_timeout = '60s';
ALTER TABLE legacy_person_map DROP CONSTRAINT legacy_person_map_method_check;
ALTER TABLE legacy_person_map ADD CONSTRAINT legacy_person_map_method_check
    CHECK (method IN ('id_and_name', 'full_name', 'last_name', 'spelling_variant', 'manual'));
