# Đóng góp cho LiveLift

Cảm ơn bạn tham gia! Toàn bộ quy trình làm việc nằm trong **[HARNESS.md](HARNESS.md)** —
tài liệu đó là luật. Trang này chỉ là bản đồ nhanh.

## Bắt đầu

> **Từ 16/09/2026 đội làm song song 3 người.** Đọc trước tiên
> **[docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md](docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md)**:
> ai sở hữu thư mục nào, việc nào trước 30/09, hợp đồng giữa các làn, và 48 giờ đầu.
> Mẫu PR ở `.github/pull_request_template.md` được GitHub điền sẵn khi mở PR.

1. Đi hết **lộ trình 90 phút cho thành viên mới** trong [README](README.md).
2. Nhận việc theo mã trong `09-PHAN-CONG.md` (ví dụ `K-06`, `T-01`).
3. Tạo nhánh `<ten>/<MA-VIEC>-mo-ta`, ví dụ `khanh/K-06-xuat-prompt-log`. Mở Draft PR ngay ngày đầu.

## Trước khi mở PR — checklist bắt buộc

```bash
pytest -m "not slow"                      # 100% pass
ruff check src tests && ruff format --check src tests
python scripts/check_isolation.py         # cách ly collectors/
```

- Đổi phần thống kê/thiết kế thí nghiệm? Chạy thêm `pytest -m slow` (gate hiệu chuẩn).
- Đổi client web hoặc route API? `pytest tests/test_web_api_contract.py` + `cd web && npm run build`.
- Sửa bug? **Root cause trước, vá sau** — viết test tái hiện (đỏ) → sửa (xanh) → thêm
  một dòng vào `docs/incident-log.md` (ngày · triệu chứng · root cause · commit · gate mới).

## Ranh giới không thương lượng

| Quy tắc | Vì sao |
|---|---|
| Bình luận thô không bao giờ chạm đĩa — `scrub()` trước mọi lệnh ghi | Luật 91/2025/QH15; quy tắc cứng của dự án |
| Số nguồn `forecast` không bao giờ mang khoảng tin cậy (E2-04) | chống overclaim ở cấp schema |
| Payload host không chứa gì về BẬT/TẮT/khối | làm mù thí nghiệm |
| Lịch gán sinh + lưu TRƯỚC phát sóng; dữ liệu thí nghiệm hỏng thì đánh dấu loại, không sửa tay | dấu vết kiểm chứng |
| Sau khi PREREGISTRATION.md khóa: mọi phân tích thêm phải dán nhãn "khám phá" | tiền đăng ký |

## Quy ước

- Commit: dòng đầu `<khu-vuc>: <mo ta khong dau>` ≤ 72 ký tự; thân có `Vi sao:` và `Kiem bang:`.
  Dùng AI thì thêm trailer đúng công cụ (xem `09-PHAN-CONG.md` §7). Không viết lại lịch sử đã push.
- `main` luôn chạy được `docker compose up` từ máy trắng.
- Số liệu mới trong docs/benchmarks phải kèm script sinh lại.
- Mọi công thức thống kê có docstring dẫn nguồn (tác giả, năm).
