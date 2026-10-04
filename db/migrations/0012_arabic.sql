-- Arabic (docs/roadmap.md L10). person_alias, faction_label, topic_label and topic_alias already allow 'ar';
-- this adds the Arabic display name to person_name, an Arabic party name and a normalisation for Arabic search.

-- Arabic normalisation for search (same rules as hkv.topics.ar_norm): drop harakat, superscript alef and tatweel;
-- hamza forms of alef become a bare alef, ta marbuta becomes ha, alef maqsura becomes ya, hamza on waw/ya becomes
-- the bare letter. People type "احمد الطيبي" for "أحمد الطيبي" and "عوده" for "عودة".
CREATE FUNCTION ar_norm(t text) RETURNS text LANGUAGE sql IMMUTABLE PARALLEL SAFE AS $$
    SELECT btrim(lower(regexp_replace(
               translate(regexp_replace(coalesce(t, ''), '[ً-ٰٟـ]', '', 'g'),
                         U&'\0623\0625\0622\0671\0629\0649\0624\0626', U&'\0627\0627\0627\0627\0647\064A\0648\064A'),
               '\s+', ' ', 'g')))
$$;

ALTER TABLE party ADD COLUMN name_ar text;

CREATE OR REPLACE VIEW person_name AS
SELECT p.id AS person_id,
       p.first_name_he || ' ' || p.last_name_he AS he,
       (SELECT a.full_name FROM person_alias a WHERE a.person_id = p.id AND a.language = 'en' AND a.alias_type = 'official'
          ORDER BY array_position(ARRAY['human', 'official', 'curated', 'wikidata', 'machine'], a.origin) LIMIT 1) AS en,
       (SELECT a.full_name FROM person_alias a WHERE a.person_id = p.id AND a.language = 'ru' AND a.alias_type = 'official'
          ORDER BY array_position(ARRAY['human', 'official', 'curated', 'wikidata', 'machine'], a.origin) LIMIT 1) AS ru,
       (SELECT a.full_name FROM person_alias a WHERE a.person_id = p.id AND a.language = 'ar' AND a.alias_type = 'official'
          ORDER BY array_position(ARRAY['human', 'official', 'curated', 'wikidata', 'machine'], a.origin) LIMIT 1) AS ar
FROM person p;
