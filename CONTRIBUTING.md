# Đóng góp cho LiveLift

Cảm ơn bạn tham gia! Toàn bộ quy trình làm việc nằm trong **[HARNESS.md](HARNESS.md)** —
tài liệu đó là luật. Trang này chỉ là bản đồ nhanh.

## Bắt đầu

> **Từ 16/09/2026 đội làm song song 3 người.** Đọc trước tiên
> **[docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md](docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md)**:
> ai sở hữu thư mục nào, việc nào trước 30/09, hợp đồng giữa các làn, và 48 giờ đầu.
> Mẫu PR ở `.github/pull_request_template.md` được GitHub điền sẵn khi mở PR.

1. Đi hết **lộ trình 90 phút cho thành viên mới** ngay dưới đây.
2. Nhận việc theo mã trong `09-PHAN-CONG.md` (ví dụ `K-06`, `T-01`).
3. Tạo nhánh `<ten>/<MA-VIEC>-mo-ta`, ví dụ `khanh/K-06-xuat-prompt-log`. Mở Draft PR ngay ngày đầu.

## Lộ trình 90 phút cho thành viên mới

Mục tiêu: sau 90 phút bạn chạy được hệ thống, đi hết một phiên chạy thử và biết
việc đầu tiên của mình nằm ở đâu. Mỗi bước là một tệp có thật trong kho.

| Phút | Làm gì | Đọc / chạy |
|---|---|---|
| 0–15 | Bài toán và ranh giới trung thực: đo được gì, **chưa** có gì (0 phiên thí nghiệm ngẫu nhiên thật) | [README](README.md): khung *Tình trạng* ở đầu tệp và mục *Trạng thái dự án* · [docs/competition/FACT-SHEET.md](docs/competition/FACT-SHEET.md) |
| 15–30 | Luật làm việc: test trước, root cause, sổ sự cố | [HARNESS.md](HARNESS.md) · 5 dòng mới nhất của [docs/incident-log.md](docs/incident-log.md) |
| 30–45 | Cài môi trường, chạy bộ test nhanh (khoảng 4 phút), bật hệ thống | README mục *Bắt đầu nhanh*, cách 2 · `python scripts/chay_local.py` |
| 45–65 | Đi một vòng như người bán: Xem thử 30 giây → Chuẩn bị phiên (chọn **Chạy thử**) → Bàn trợ live → Màn người dẫn → Kết quả | [docs/HUONG-DAN-SU-DUNG.md](docs/HUONG-DAN-SU-DUNG.md) · [docs/demo-vang.md](docs/demo-vang.md) |
| 65–80 | Trái tim khoa học: lịch gán lưu trước giờ phát, kiểm định ngẫu nhiên hóa | [PREREGISTRATION.md](PREREGISTRATION.md) · `src/livelift/core/assigner/outer.py` · `src/livelift/analysis/estimators.py` |
| 80–90 | Nhận việc | [docs/VIEC-CAN-LAM.md](docs/VIEC-CAN-LAM.md) · [09-PHAN-CONG.md](docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md) |

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
