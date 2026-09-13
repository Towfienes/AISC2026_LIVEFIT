-- Gỡ cờ dữ liệu mẫu (gói DEMO-THẬT). Sau khi gỡ, phiên demo không còn phân
-- biệt được với phiên thật ở tầng SQL — chỉ chạy down nếu chấp nhận mất ranh
-- giới đó (các gate ứng dụng sẽ coi mọi phiên là thật trở lại).
ALTER TABLE live_session DROP COLUMN IF EXISTS is_demo;
