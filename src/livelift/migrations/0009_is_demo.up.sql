-- Cờ DỮ LIỆU MẪU `is_demo` (gói DEMO-THẬT, 12/09/2026).
--
-- Yêu cầu từ hai vòng phản biện (ưu tiên #2–3 cả hai bản): người dùng phải
-- LUÔN biết mình đang nhìn dữ liệu mẫu hay dữ liệu thật, và dữ liệu demo
-- KHÔNG BAO GIỜ lọt vào kết quả thật. Trước gói này, phiên sinh từ
-- POST /demo/seed không được đánh dấu gì — chúng chỉ tình cờ nằm ngoài kết
-- quả thật khi kho còn trống, và sẽ trộn thẳng vào /experiment/summary ngay
-- khi kho chứa cả phiên thật lẫn phiên demo.
--
-- HAI CỜ, HAI CÂU HỎI KHÁC NHAU — không gộp vào một cột:
--
--   * `is_demo`  — "dữ liệu này có THẬT không?" Phiên MÁY SINH RA làm dữ liệu
--     mẫu để xem thử/tập demo (seed mô phỏng, replay mẫu). Không có buổi phát
--     nào từng diễn ra sau con số của nó. Chỉ các máy sinh demo phía server
--     (/demo/seed, scripts/seed_demo_vang.py) đặt được cờ này — POST /sessions
--     không nhận nó, nên không phiên thật nào bị dán nhầm nhãn demo.
--   * `dry_run` (migration 0008) — "phiên THẬT này có được TÍNH không?" Người
--     thật vận hành đường ống thật nhưng khai báo trước là chạy thử/tập dượt.
--     Dữ liệu thật về cơ chế sinh, chỉ không vào mẫu phân tích gộp.
--
-- Dùng lại `dry_run` cho phiên seed sẽ làm UI không phân biệt được nhãn
-- "DEMO — dữ liệu mẫu" với "chạy thử", và làm chip chế độ DEMO/THẬT cấp ứng
-- dụng đếm sai. Giao ước đầy đủ: PREREGISTRATION.md §8.2.
--
-- Như `dry_run`, cờ này BẤT BIẾN sau khi tạo (store._SESSION_WRITE_ONCE và
-- danh sách cột `allowed` của update_session không chứa nó): một cờ loại
-- phiên khỏi kết quả mà bật/tắt được sau khi thấy số liệu là cửa hậu chọn
-- lọc kết quả.

ALTER TABLE live_session
    ADD COLUMN IF NOT EXISTS is_demo boolean NOT NULL DEFAULT false;

COMMENT ON COLUMN live_session.is_demo IS
    'Dữ liệu MẪU máy sinh (demo/seed) — bị loại khỏi MỌI đầu ra khoa học thật '
    '(/experiment/summary mặc định, export nhãn, ...); xem được riêng, luôn kèm nhãn. '
    'Đặt lúc tạo bởi máy sinh demo phía server, bất biến sau đó. Khác dry_run: '
    'dry_run là phiên THẬT chạy thử; is_demo là dữ liệu KHÔNG thật. '
    'Xem PREREGISTRATION §8.2.';

-- BACKFILL các phiên seed SINH TRƯỚC cờ này — theo dấu vết KHÔNG THỂ là phiên
-- thật, không theo phỏng đoán:
--
--   * platform = 'sim' — giá trị enum này tồn tại DUY NHẤT cho simulator; mọi
--     đường tạo phiên thật (web, ingest, replay VOD) không bao giờ ghi 'sim'.
--     Kiểm chứng trên kho bền 12/09: 29 phiên 'sim' đều là seed cũ, và chúng
--     đang chiếm gần trọn "kết quả thật" của /experiment/summary — đúng lớp
--     sự cố mà gói DEMO-THẬT đóng lại.
--   * phiên replay CỦA máy seed — nhận diện bằng CẢ BA dấu vết mà
--     _seed_one_session để lại (platform 'replay' + host_id 'demo' + title
--     'Phiên mô phỏng seed=…'); phân tích VOD thật có host_id NULL và title
--     'Phân tích: …' nên không thể dính. Ba điều kiện AND là cố ý: đánh dấu
--     NHẦM một phiên thật thành demo sẽ làm nó biến mất âm thầm khỏi mẫu —
--     lỗi tệ hơn cái đang sửa (tinh thần §8.2: mặc định là TÍNH VÀO).
--
-- KHÔNG backfill gì khác: dry_run, phiên youtube/facebook/tiktok, phiên replay
-- phân tích thật đều giữ nguyên is_demo=false.
UPDATE live_session
SET is_demo = true
WHERE platform = 'sim'
   OR (platform = 'replay' AND host_id = 'demo' AND title LIKE 'Phiên mô phỏng seed=%');
