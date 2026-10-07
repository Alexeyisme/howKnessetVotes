-- Small copies of MK portraits (2026-10-07). The originals are 420x630 JPEGs of ~100 KB, shown at 40x50 in member
-- chips and 120x150 on the member page: a members list of 150 chips loaded ~15 MB. Each size is made once from the
-- stored image (hkv.names.cache_photos) and served as /api/v1/members/{id}/photo-{width}.jpg; the .jpg extension lets
-- Cloudflare cache it, which it does not for the extensionless /photo.

CREATE TABLE person_photo_size (
    person_id       uuid NOT NULL REFERENCES person_photo (person_id) ON DELETE CASCADE,
    width           smallint NOT NULL CHECK (width > 0),
    image           bytea NOT NULL,
    source_sha256   text NOT NULL CHECK (source_sha256 ~ '^[0-9a-f]{64}$'),   -- the stored image it was made from
    PRIMARY KEY (person_id, width)
);
