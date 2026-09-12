-- Vòng đời phiên + cờ CHẠY THỬ (gói C-NHẤT-QUÁN, 12/09/2026).
--
-- Hai vấn đề vận hành ĐÃ XẢY RA THẬT, ghi trong docs/benchmarks/kiem-chung-van-hanh.md:
--
-- (1) §3.3 — phiên QUAN SÁT chưa từng phát sóng không đóng lại được. `POST /end`
--     đòi trạng thái 'live', nên một phiên gõ tay (chế độ quan sát, hợp lệ và hữu
--     ích) kẹt ở 'planned' VĨNH VIỄN. Đường vòng duy nhất là bắt chủ shop sinh lịch
--     gán rồi bấm phát sóng — tức dựng một bộ máy thí nghiệm họ không định chạy,
--     chỉ để đóng được một dòng trong danh sách. Thêm trạng thái cuối 'cancelled':
--     "đã đóng mà KHÔNG phát sóng". Không dùng 'ended' cho việc này — 'ended' có
--     nghĩa buổi phát đã diễn ra và đã kết thúc; nói dối trạng thái để tiện code
--     là cách nhanh nhất làm bẩn mẫu phân tích.
--
-- (2) §2.4c — không có cách nào loại phiên CHẠY THỬ khỏi kết quả gộp. Hai phiên dò
--     lỗi sống đúng 1 giây, không một cú nhấp, đã lọt vĩnh viễn vào
--     /experiment/summary. Chủ shop bấm thử cho quen tay một lần là làm bẩn kết quả
--     của chính mình, không có nút gỡ. `dry_run` khai báo TRƯỚC khi phiên chạy
--     (POST /sessions) và KHÔNG có đường sửa sau — đó là điều kiện để nó là quy tắc
--     nạp mẫu tiền đăng ký (PREREGISTRATION §8.2) chứ không phải cái nút loại bỏ
--     dữ liệu xấu sau khi đã nhìn thấy kết quả.

ALTER TABLE live_session DROP CONSTRAINT IF EXISTS live_session_status_check;
ALTER TABLE live_session
    ADD CONSTRAINT live_session_status_check
    CHECK (status IN ('planned','scheduled','live','ended','cancelled'));

ALTER TABLE live_session
    ADD COLUMN IF NOT EXISTS dry_run boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN live_session.dry_run IS
    'Phiên chạy thử/tập dượt. Khai báo lúc tạo phiên, bất biến sau đó; phiên TRUE bị '
    'loại khỏi mẫu phân tích gộp (PREREGISTRATION §8.2) nhưng vẫn xem được riêng.';

-- Một phiên đã huỷ không bao giờ có mốc bắt đầu phát sóng: nếu nó có start_ts thì
-- nó đã lên sóng, và khi đó trạng thái cuối phải là 'ended'. Ràng buộc này giữ cho
-- bộ lọc mẫu phân tích ('ended' + có lịch) không bao giờ phải đoán.
ALTER TABLE live_session
    ADD CONSTRAINT live_session_cancelled_never_aired
    CHECK (status <> 'cancelled' OR start_ts IS NULL);
