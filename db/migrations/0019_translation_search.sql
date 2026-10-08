-- Search bills by their translated titles in any word form: "налоги" finds "налог", "налоговый", "налогообложение"
-- (stemmed prefix match, hkv.api.topics.search). One index per language, each with its own stemmer; the query must use
-- the same expression to use it.
CREATE INDEX text_translation_fts_ru ON text_translation USING gin (to_tsvector('russian'::regconfig, text)) WHERE language = 'ru';
CREATE INDEX text_translation_fts_en ON text_translation USING gin (to_tsvector('english'::regconfig, text)) WHERE language = 'en';
CREATE INDEX text_translation_fts_ar ON text_translation USING gin (to_tsvector('arabic'::regconfig, text)) WHERE language = 'ar';
