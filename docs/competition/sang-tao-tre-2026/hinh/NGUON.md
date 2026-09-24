# Nguồn các hình minh hoạ hồ sơ

*Sinh bằng* `python scripts/ve_hinh_ho_so.py` *— không sửa tay tệp này; chạy lại script.*

Mọi hình rộng đúng **16 cm** (bề rộng vùng chữ của hồ sơ: A4, lề 3 cm/2 cm), **300 dpi**,
chữ nhỏ nhất 8 pt. Chèn vào `noi-dung.md` bằng `![Hình N. ...](hinh/<tệp>.png){width=16cm}`
(chú thích phải bắt đầu bằng "Hình N." — quy ước của `dung_ho_so.py`); chèn hẹp hơn 16 cm thì chữ
in ra nhỏ hơn 8 pt. Mỗi hình có dòng nguồn ở chân hình.

| Tệp | Mô tả một dòng | Nguồn chạy lại được |
|---|---|---|
| `h1-switchback.png` | Lịch khối của một phiên 90 phút sinh bằng chính hàm gán production (seed 42): 16 khối đo, 8 BẬT/8 TẮT, khối đầu 10,2 phút và khối cuối 10,4 phút (nhân đôi), burn-in 60 s đầu mỗi khối, mốc khoá lịch + `design_hash` `f5be4aa261de…` trước giờ phát, mốc lên sóng (409 nếu chưa có lịch) và kết thúc | `generate_schedule(90, DesignParams(), seed=42)`, `design_hash`, `BURN_IN_S` (`api/routes/reports.py`) |
| `h2-kien-truc.png` | Sơ đồ kiến trúc: nguồn (API chính thức · VOD quan sát qua yt-dlp · mô phỏng · link đo) → bộ thu → cổng lọc PII trước khi ghi → kho → lõi thống kê → /desk, /host làm mù, kết quả; tô 3 cổng chặn: PII, HTTP 409, `RESULTS_FREEZE_UNTIL` | Đọc từ mã (đường dẫn ở chân hình); nguồn HTML chỉnh được: `h2-kien-truc.html`, chụp bằng Playwright Chromium ở 300 dpi |
| `h3-hieu-chuan-aa.png` | Hiệu chuẩn A/A (mô phỏng): phân phối p-value 200 lần lặp; tỷ lệ bác bỏ 3,50% (KTC 95% [1,42%; 7,08%], p nhị thức 0,4168) so với 5%; độ phủ 96,50% (193/200) và 92,50% (37/40) so với 95% | `run_validation` với `NGHIEN_CUU` của `scripts/do_lai_so_hieu_chuan.py`; dữ liệu từng lần lặp: `du-lieu/hieu-chuan.json`; số tổng đối chiếu `docs/benchmarks/so-hieu-chuan.json` |
| `h4-mde.png` | MDE (sàn Poisson, cận dưới) của biến kết quả chính theo số người xem đồng thời × số phiên, trục log, hai giả định tỷ lệ nhấp; vùng 5–15 người xem là ƯỚC TÍNH từ CPM, chưa đo. Ở 18 phiên: 5–15 người xem cho MDE 21%–37% (tỷ lệ nhấp 1,00) hoặc 39%–67% (tỷ lệ nhấp 0,30). Điểm mô phỏng 8 phiên: CV trong phiên 0,263, MDE 16,4% ở ~59 người xem (40–114); sàn Poisson cùng chỗ đó là 16,0%, tức bộ mô phỏng gần như chỉ có nhiễu đếm | `livelift.analysis.power` (`analysis_window_seconds`, `poisson_cv`, `mde_relative`), `SimParams`, `analysis/power/bang_mde_don_hang.py` (`CLICK_RATE_ANCHOR`, `SESSIONS_GRID`) |
| `h5-luu-hieu-ung.png` | Độ phủ KTC 95% và độ lệch khi tác động kéo sang khối sau (mô phỏng), bán rã 0/120/180 s, 3 seed gộp — 0 s: 96% (72/75), lệch −1,5%; 120 s: 76% (57/75), lệch −21,5%; 180 s: 57% (43/75), lệch −31,6% | `run_validation` với tham số đọc bằng `ast` từ `tests/test_sim_validation.py::test_estimator_under_carryover_interference`; dữ liệu từng lần lặp: `du-lieu/hieu-ung-luu.json` |

## Lưu ý trung thực khi trích hình

- Hình 3 và 5 là **mô phỏng Monte-Carlo**; dự án có **0 phiên thí nghiệm ngẫu nhiên thật**.
- Hình 5 **thay** bảng hiệu ứng lưu cũ (100% / 84% / 60%, docstring `sim/validate.py`, đo 02/09): bảng đó không tái lập được ở mã hiện tại. Trích số từ hình này kèm cỡ mẫu (n = 75 mỗi mức).
- Hình 4 là **sàn Poisson** — với CÙNG tỷ lệ nhấp và số người xem, MDE thật chỉ có thể lớn hơn. Tỷ lệ nhấp chưa đo được (cả hai panel là giả định); vùng 5–15 người xem là ước tính từ chi phí quảng cáo (CPM), **chưa đo**.
- Hình 2: nguồn VOD là dữ liệu quan sát lấy bằng yt-dlp, **không** qua API chính thức; các bộ nối API chính thức đã viết nhưng chưa chạy với khoá thật. `RESULTS_FREEZE_UNTIL` hiện để trống (tắt) trong `.env.example`; khi đặt, `/ket-qua` và `/bao-cao` bị khoá nhưng `GET /sessions/{id}/report` vẫn trả chênh lệch trung bình (đường lọt đã biết, kiểm toán 25/09) — hộp CỔNG 3 ghi rõ; vá xong thì sửa `html_h2()` và chạy lại `--chi h2`.

## Chạy lại

```
python scripts/ve_hinh_ho_so.py               # vẽ lại từ du-lieu/*.json (~1 phút)
python scripts/ve_hinh_ho_so.py --kiem        # chạy lại Monte-Carlo, đối chiếu TỪNG lần lặp với du-lieu/ (~9 phút)
python scripts/ve_hinh_ho_so.py --tinh-lai    # chạy lại Monte-Carlo và ghi đè du-lieu/ (khi mã đã đổi có chủ ý)
```

Cần `matplotlib` (không nằm trong pyproject) và Playwright + Chromium cho hình 2.
