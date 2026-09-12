-- Quay lui gói C-NHẤT-QUÁN. Phiên đang ở trạng thái 'cancelled' không có chỗ trong
-- lược đồ cũ: đưa chúng về 'planned' (đúng trạng thái chúng bị kẹt trước bản vá)
-- thay vì để CHECK cũ từ chối và làm hỏng cả lần quay lui.
ALTER TABLE live_session DROP CONSTRAINT IF EXISTS live_session_cancelled_never_aired;
UPDATE live_session SET status = 'planned' WHERE status = 'cancelled';

ALTER TABLE live_session DROP CONSTRAINT IF EXISTS live_session_status_check;
ALTER TABLE live_session
    ADD CONSTRAINT live_session_status_check
    CHECK (status IN ('planned','scheduled','live','ended'));

ALTER TABLE live_session DROP COLUMN IF EXISTS dry_run;
