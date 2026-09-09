-- Index for the valid-click classification on the redirect hot path (gói Q1).
--
-- Every /r/{code} request classifies the click before logging it, and the
-- refractory (τ) + volume-cap rules need the history of THIS fingerprint on
-- THIS shortlink only (store.list_clicks_for_fingerprint). Without this index
-- that lookup falls back to idx_click_session_ts and scans the whole session,
-- so each redirect costs O(clicks-so-far) — degrading precisely during the bot
-- bursts the rules exist to catch. The redirect must never be slowed down
-- (PREREGISTRATION §4.1: the 302 goes out regardless).

CREATE INDEX idx_click_fingerprint
    ON click_event (session_id, dedup_hash, shortlink_code, ts);
