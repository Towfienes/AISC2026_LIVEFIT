-- Comment idempotency + source provenance (ingest audit 06/09).
--
-- The ingest runner sends (platform, ext_id, ts_utc) with every comment; the
-- server used to drop all three, so a runner restart mid-session re-inserted
-- every comment it re-read. The partial unique index below turns a duplicate
-- delivery into ON CONFLICT DO NOTHING (see PostgresStore.add_comment).
-- Rows without ext_id (dashboard/manual posts) are exempt — they carry no
-- platform identity to dedup on.

ALTER TABLE comment_event ADD COLUMN platform text;
ALTER TABLE comment_event ADD COLUMN ext_id text;

CREATE UNIQUE INDEX idx_comment_platform_ext_id
    ON comment_event (session_id, platform, ext_id)
    WHERE ext_id IS NOT NULL;
