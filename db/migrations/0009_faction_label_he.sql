-- Hebrew short names for factions whose official name is a long list name
-- ("התאחדות הספרדים שומרי תורה ..." -> "ש״ס"), for tables and charts in the Hebrew UI. The full official
-- name stays on faction.name_he; faction_label 'he' rows carry it as `name` and the short form as `short_name`.

ALTER TABLE faction_label DROP CONSTRAINT faction_label_language_check;
ALTER TABLE faction_label ADD CONSTRAINT faction_label_language_check CHECK (language IN ('ru', 'en', 'he', 'ar'));
