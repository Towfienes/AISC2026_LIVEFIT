# Pitch AISC Round 2 — factual/technical draft

> Đây chưa phải storytelling hay business positioning cuối. Tech lead quyết
> định bản trình bày cuối; mọi numerical claim dưới đây phải tồn tại trong
> `FACT-SHEET.md`.

## Vấn đề kỹ thuật

Trong một livestream, mọi người xem nhìn cùng một màn hình. LiveLift chia thời
gian thành các khối BẬT/TẮT được gán trước để đo tác động của chiến lược vận
hành thay vì đọc tương quan sau phiên.

## Demo

1. Mở desk của phiên demo live fresh do preflight resolve. Chỉ ra lịch đã gán.
2. Ở khối đối chứng, giải thích hệ thống cố ý không đưa gợi ý và đội vận hành
   tiếp tục như bình thường để đo mức nền.
3. Mở host view để cho thấy payload làm mù không chứa assignment/block timing.
4. Mở `/ket-qua`: real result vẫn nói chưa đủ. CTA dẫn tới ba trạng thái Demo
   Vàng — Dương rõ, Chưa kết luận, Chưa đủ dữ liệu — đều dán nhãn mô phỏng.

## Evidence được phép nói

- Bộ kiểm thử hiện thu thập 1.811 fast, 17 slow/Monte-Carlo và 10 browser test.
  Không nói tất cả xanh khi fast gate còn FAIL.
- Calibration executable xác nhận A/A rejection 3,50%, statistical CI coverage
  A/A 96,50% và known-effect bias −0,84%.
- Live-fire đã ghi nhận 19.126 bình luận ở 16 replay/VOD thật. Đây là dữ liệu
  quan sát, không phải randomized evidence.
- Hiện có 0 phiên randomized thật. Demo không thay đổi sự thật đó.

## Giới hạn sản phẩm

Order ingestion và background ingest tồn tại; snapshot giúp memory mode hồi
phục cục bộ nhưng không tương đương Postgres durability. Autopilot nội bộ ghi
quyết định/exposure; chưa được mô tả như production pinning thành công trên mọi
nền tảng. Intent model không được nâng cấp hay đổi mặc định trong phase này.
