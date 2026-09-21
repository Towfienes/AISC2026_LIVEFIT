# Roadmap AISC Round 2

Roadmap này chỉ phục vụ AISC Round 2. Nó không kế thừa roadmap Sáng tạo trẻ.

## BLOCKER

- Giữ source of truth executable cho fact sheet; conflict không được giải bằng
  chép số từ README.
- Production Next.js build phải PASS sau thay đổi UI.
- Fast suite đang bị chặn bởi mismatch artifact NLP/scikit-learn. Không train
  hoặc đổi model trong scope này; ghi rõ blocker để tech lead xử lý riêng.

## P0 kỹ thuật

- Package AISC độc lập và claim có provenance.
- `/ket-qua` giữ real mặc định, nêu chưa có kết quả thật và dẫn rõ sang ba Demo
  Vàng có nhãn.
- Copy khối đối chứng giải thích hệ thống cố ý không đưa gợi ý.
- Preflight read-only resolve phiên demo mới, current block và presenter URLs.
- Chạy fast/slow/browser, Ruff, production web build và compose/DB gate khi hạ
  tầng tồn tại; FAIL/NOT RUN được giữ nguyên.

## HUMAN-DEPENDENT P0

- Lấy official platform credential.
- Chạy official ingest smoke test.
- Chạy hệ thống với durable Postgres.
- Nếu khả thi trước Round 2, thử ít nhất một real end-to-end randomized pilot.

Codex không tự tạo evidence cho các mục này. Cho tới khi có bằng chứng, fact
sheet tiếp tục ghi 0 real randomized sessions.

## P1 sau P0

- Diễn tập thủ công toàn luồng presenter ở đúng màn hình và mạng ngày thi.
- Đóng băng slide/storytelling cuối bởi tech lead dựa trên fact sheet.
- Xử lý blocker dependency NLP ở một scope riêng, không retrain ngầm trong gói
  Round 2.

## DEFER/REJECTED

Production pinning đa nền tảng, order reconciliation thật, OAuth/multi-tenant,
queue/scale và redesign nằm ngoài Round 2 package. TikTok scraping, đổi
methodology, estimator, switchback, preregistration hoặc Intent v2 mặc định bị
từ chối trong scope này.
