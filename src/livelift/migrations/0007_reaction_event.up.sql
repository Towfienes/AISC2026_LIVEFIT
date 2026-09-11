-- Sự kiện tương tác trả tiền / phản ứng công khai của khán giả (gói BACKEND-SIGNALS, 11/09).
--
-- Nguồn hiện có (đo trên 11 chat replay YouTube của live-fire đa nguồn, đếm ở
-- mức addChatItemAction — grep chuỗi thô đếm trùng vì ticker nhúng lại renderer):
--   * superchat  — liveChatPaidMessageRenderer, kèm purchaseAmountText (0 sự kiện
--                  trong toàn bộ corpus: shop VN gần như không dùng Super Chat);
--   * sticker    — liveChatPaidStickerRenderer, kèm purchaseAmountText (0 sự kiện);
--   * membership — liveChatMembershipItemRenderer (7 sự kiện / 3 buổi);
--   * gift       — liveChatSponsorshipsGiftPurchaseAnnouncementRenderer (4 sự kiện / 2 buổi).
--   * like       — CHƯA có nguồn nào cung cấp (YouTube không lưu tim/like vào chat
--                  replay; TikTok có gift/like nhưng nguồn đang không hoạt động).
--                  Giá trị kind vẫn được khai sẵn để schema dùng chung khi nguồn về —
--                  KHÔNG nghĩa là hệ thống đang đo được like.
--
-- amount/currency là SỐ TIỀN CÔNG KHAI YouTube in trong khung chat (ví dụ "50.000 ₫")
-- — không phải PII. Không cột nào mang tên/kênh người tặng: parser không bao giờ đọc
-- trường tác giả (hard rule 1).
--
-- Idempotency: (session_id, platform, ext_id) như comment_event (migration 0002) —
-- gửi lại cùng sự kiện (runner restart, replay lại) không nhân đôi row.

CREATE TABLE reaction_event (
    reaction_id uuid PRIMARY KEY,
    session_id  uuid NOT NULL REFERENCES live_session(session_id) ON DELETE CASCADE,
    ts_utc      timestamptz NOT NULL,
    kind        text NOT NULL CHECK (kind IN ('superchat','gift','sticker','membership','like')),
    -- NULL = sự kiện không mang số tiền (membership/gift/like), hoặc chuỗi tiền
    -- không đọc được — khi đó currency cũng NULL, KHÔNG ghi 0 giả.
    amount      numeric,
    currency    text,
    platform    text,
    ext_id      text,
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX idx_reaction_event_session_ts ON reaction_event (session_id, ts_utc);
CREATE UNIQUE INDEX idx_reaction_platform_ext_id
    ON reaction_event (session_id, platform, ext_id)
    WHERE ext_id IS NOT NULL;
