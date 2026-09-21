# LiveLift — workspace AISC 2026 Round 2

Thư mục này là workspace **riêng cho AISC Round 2 — Data-Driven Business**.
Nó không dùng roadmap, deadline hay tiêu chí hackathon của hồ sơ Sáng tạo trẻ.

## Đọc theo thứ tự

1. [FACT-SHEET.md](FACT-SHEET.md) — mọi con số, nguồn và lệnh tái lập.
2. [DEMO-GATES.md](DEMO-GATES.md) — preflight và diễn tập trước khi trình bày.
3. [PITCH.md](PITCH.md) — bản nháp factual/technical, chưa phải storytelling cuối.
4. [QNA.md](QNA.md) — câu trả lời kỹ thuật, giới hạn và chống overclaim.
5. [ROADMAP.md](ROADMAP.md) — việc riêng của AISC Round 2.
6. [FREEZE.md](FREEZE.md) — claim nào đã khóa, gate nào PASS/FAIL/NOT RUN.

## Ranh giới dữ liệu

- **THẬT + RANDOMIZED:** hiện ghi nhận **0 phiên**. Không dùng demo để thay số này.
- **THẬT + QUAN SÁT:** benchmark replay/VOD có bình luận thật, nhưng không có
  lịch gán ngẫu nhiên nên không tạo bằng chứng nhân quả.
- **DEMO/MÔ PHỎNG:** dùng seed cố định để trình bày ba trạng thái kết quả.
  Mọi phiên mang `is_demo=true` và bị loại khỏi kết quả real mặc định.

`/ket-qua` tiếp tục mở kết quả real theo mặc định. Khi chưa đủ evidence thật,
trang nói thẳng điều đó và chỉ cung cấp CTA sang Demo Vàng có nhãn rõ.

## Điều workspace này không làm

Không đổi statistical core, estimator, switchback hay preregistration; không
đổi Intent v2 thành mặc định; không train NLP; không TikTok scraping; không
OAuth/multi-tenant; không sửa tài liệu lịch sử của cuộc thi khác.
