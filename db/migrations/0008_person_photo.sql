-- Official MK portraits (docs/roadmap.md U5). The Knesset website gives each MK a photo URL on fs.knesset.gov.il;
-- we keep the URL, not the image, and show it with the source named.

CREATE TABLE person_photo (
    person_id         uuid PRIMARY KEY REFERENCES person (id) ON DELETE CASCADE,
    url               text NOT NULL CHECK (url ~ '^https://'),
    source            text NOT NULL DEFAULT 'knesset_site',
    fetched_at        timestamptz NOT NULL DEFAULT now()
);
