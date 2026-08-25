# Sổ sự cố (incident log)

*Theo HARNESS §3: mỗi lỗi (test đỏ, số liệu bất thường, sự cố trong phiên) ghi MỘT dòng
sau khi đã tìm root cause — không ghi triệu chứng suông. Lỗi trong phiên live ghi thêm
vào nhật ký phiên (`ops/templates/nhat-ky-phien.md`). Cột "gate mới" trả lời câu hỏi
bắt buộc: lỗi này lọt qua gate nào, có cần gate mới không (ghi "không" nếu gate hiện có
đủ). Nhớ: dữ liệu khối/phiên hỏng thì đánh dấu `excluded_reason`, KHÔNG sửa số liệu.*

| Ngày | Triệu chứng | Root cause | Commit fix | Gate mới |
|---|---|---|---|---|
| | | | | |
