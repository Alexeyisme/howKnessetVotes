-- MK portraits served from our own domain. Since 2026-10-05 fs.knesset.gov.il answers visitors outside Israel
-- (and iPhones on iCloud Private Relay) with a redirect to a geo-block page, so hotlinking the URL broke. The image
-- is fetched once, through HKV_KNESSET_PROXY, and kept here; `url` stays the source of record, and a new url clears
-- the copy so it is fetched again.

ALTER TABLE person_photo
    ADD COLUMN image            bytea,
    ADD COLUMN content_type     text CHECK (content_type ~ '^image/'),
    ADD COLUMN image_sha256     text CHECK (image_sha256 ~ '^[0-9a-f]{64}$'),
    ADD COLUMN image_fetched_at timestamptz,
    ADD CONSTRAINT person_photo_image_complete CHECK ((image IS NULL) = (content_type IS NULL) AND (image IS NULL) = (image_sha256 IS NULL));
