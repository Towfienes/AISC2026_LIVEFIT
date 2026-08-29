# Sổ sự cố (incident log)

*Theo HARNESS §3: mỗi lỗi (test đỏ, số liệu bất thường, sự cố trong phiên) ghi MỘT dòng
sau khi đã tìm root cause — không ghi triệu chứng suông. Lỗi trong phiên live ghi thêm
vào nhật ký phiên (`ops/templates/nhat-ky-phien.md`). Cột "gate mới" trả lời câu hỏi
bắt buộc: lỗi này lọt qua gate nào, có cần gate mới không (ghi "không" nếu gate hiện có
đủ). Nhớ: dữ liệu khối/phiên hỏng thì đánh dấu `excluded_reason`, KHÔNG sửa số liệu.*

| Ngày | Triệu chứng | Root cause | Commit fix | Gate mới |
|---|---|---|---|---|
| 25/08/2026 | Scrub lần 2 sinh `[[ĐỊA CHỈ]` lồng nhau (test idempotency đỏ) | Token thay thế `[ĐỊA CHỈ]` chứa chính trigger "địa chỉ" của `ADDR_ANNOUNCE_RE`; trigger ngắn `đc` không yêu cầu dấu `:` nên khớp cả "đc" ≈ "được" | lookbehind `(?<!\[)` + tail loại ngoặc + `đc` bắt buộc có `:` (commit 5111e48) | không — test idempotency đã có sẵn và giữ vĩnh viễn |
| 25/08/2026 | API trong Docker báo `store_backend=memory` dù có DATABASE_URL | docker-compose chỉ đặt `DATABASE_URL`; store chọn backend qua biến `STORE_BACKEND` (mặc định memory) — hai cấu hình tách rời, thiếu một | thêm `STORE_BACKEND: postgres` vào app_env | cân nhắc: smoke-test compose trong CI (job tùy chọn, cần Docker runner) |
| 27/08/2026 | Nút "Xem thử ngay" trên trang chủ lỗi; `/demo/seed` trả HTTP 500 từ lần gọi thứ hai | Hai store phân kỳ hợp đồng: `InMemoryStore.create_shortlink` ghi đè âm thầm nên test (chỉ chạy memory) luôn xanh, còn `PostgresStore` ném UniqueViolation trên mã cố định `demo0/1/2` → 500. Seed lại là thao tác bình thường của người dùng | mã shortlink duy nhất mỗi lần seed + cả hai store cùng ném `ShortlinkCodeTakenError` + route trả 409 kèm retry | CÓ — `tests/test_store_contract.py` (kiểm hợp đồng trên mọi backend, phần postgres chạy khi có DATABASE_URL) và test hồi quy seed hai lần trong `tests/test_api_flow.py` |
