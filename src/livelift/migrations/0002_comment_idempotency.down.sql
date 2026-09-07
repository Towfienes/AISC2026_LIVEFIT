DROP INDEX IF EXISTS idx_comment_platform_ext_id;
ALTER TABLE comment_event DROP COLUMN IF EXISTS ext_id;
ALTER TABLE comment_event DROP COLUMN IF EXISTS platform;
