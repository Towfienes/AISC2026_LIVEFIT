# Nguồn các hình minh hoạ hồ sơ

*Sinh bằng* `python scripts/ve_hinh_ho_so.py` *— không sửa tay tệp này; chạy lại script.*

Mọi hình rộng đúng **16 cm** (bề rộng vùng chữ của hồ sơ: A4, lề 3 cm/2 cm), **300 dpi**,
chữ nhỏ nhất 8 pt. Chèn vào `noi-dung.md` bằng `![Hình N. ...](hinh/<tệp>.png){width=16cm}`
(chú thích phải bắt đầu bằng "Hình N." — quy ước của `dung_ho_so.py`); chèn hẹp hơn 16 cm thì chữ
in ra nhỏ hơn 8 pt. Mỗi hình có dòng nguồn ở chân hình.
Riêng `h6-nlp.png`: số trong ô ma trận 7,5 pt, hình cao 8,2 cm.

| Tệp | Mô tả một dòng | Nguồn chạy lại được |
|---|---|---|
| `h1-switchback.png` | Lịch khối của một phiên 90 phút sinh bằng chính hàm gán production (seed 42): 16 khối đo, 8 BẬT/8 TẮT, khối đầu 10,2 phút và khối cuối 10,4 phút (nhân đôi), burn-in 60 s đầu mỗi khối, mốc khoá lịch + `design_hash` `f5be4aa261de…` trước giờ phát, mốc lên sóng (409 nếu chưa có lịch) và kết thúc | `generate_schedule(90, DesignParams(), seed=42)`, `design_hash`, `BURN_IN_S` (`api/routes/reports.py`) |
| `h2-kien-truc.png` | Sơ đồ kiến trúc: nguồn (API chính thức · VOD quan sát qua yt-dlp · mô phỏng · link đo) → bộ thu → cổng lọc PII trước khi ghi → kho → lõi thống kê → /desk, /host làm mù, kết quả; tô 3 cổng chặn: PII, HTTP 409, `RESULTS_FREEZE_UNTIL` | Đọc từ mã (đường dẫn ở chân hình); nguồn HTML chỉnh được: `h2-kien-truc.html`, chụp bằng Playwright Chromium ở 300 dpi |
| `h3-hieu-chuan-aa.png` | Hiệu chuẩn A/A (mô phỏng): phân phối p-value 200 lần lặp; tỷ lệ bác bỏ 3,50% (KTC 95% [1,42%; 7,08%], p nhị thức 0,4168) so với 5%; độ phủ 96,50% (193/200) và 92,50% (37/40) so với 95% | `run_validation` với `NGHIEN_CUU` của `scripts/do_lai_so_hieu_chuan.py`; dữ liệu từng lần lặp: `du-lieu/hieu-chuan.json`; số tổng đối chiếu `docs/benchmarks/so-hieu-chuan.json` |
| `h4-mde.png` | MDE (sàn Poisson, cận dưới) của biến kết quả chính theo số người xem đồng thời × số phiên, trục log, hai giả định tỷ lệ nhấp; vùng 5–15 người xem là ƯỚC TÍNH từ CPM, chưa đo. Ở 18 phiên: 5–15 người xem cho MDE 21%–37% (tỷ lệ nhấp 1,00) hoặc 39%–67% (tỷ lệ nhấp 0,30). Điểm mô phỏng 8 phiên: CV trong phiên 0,263, MDE 16,4% ở ~59 người xem (40–114); sàn Poisson cùng chỗ đó là 16,0%, tức bộ mô phỏng gần như chỉ có nhiễu đếm | `livelift.analysis.power` (`analysis_window_seconds`, `poisson_cv`, `mde_relative`), `SimParams`, `analysis/power/bang_mde_don_hang.py` (`CLICK_RATE_ANCHOR`, `SESSIONS_GRID`) |
| `h5-luu-hieu-ung.png` | Độ phủ KTC 95% và độ lệch khi tác động kéo sang khối sau (mô phỏng), bán rã 0/120/180 s, 3 seed gộp — 0 s: 96% (72/75), lệch −1,5%; 120 s: 76% (57/75), lệch −21,5%; 180 s: 57% (43/75), lệch −31,6% | `run_validation` với tham số đọc bằng `ast` từ `tests/test_sim_validation.py::test_estimator_under_carryover_interference`; dữ liệu từng lần lặp: `du-lieu/hieu-ung-luu.json` |
| `h6-nlp.png` | Phân loại ý định trên 393 bình luận thật (3 buổi live, leave-one-session-out), nhãn tham chiếu do tác tử AI gán: (a) ma trận nhầm lẫn 11 lớp của C2 (v2) chuẩn hóa theo hàng, accuracy 0,730; lớp Hỏi mở đại lý không có dòng tham chiếu nào (n = 0); (b) macro-F1 kèm KTC 95% bootstrap — B0 0,056 [0,051; 0,063]; B1 0,146 [0,109; 0,180]; B2 0,211 [0,172; 0,247]; B3 0,199 [0,163; 0,234]; C1 0,563 [0,491; 0,621]; C2 0,542 [0,478; 0,625]; C3 0,493 [0,441; 0,562]; A4 0,362 [0,317; 0,423]. B2 (v1 đang chạy) 0,211 → C2 (v2) 0,542; bỏ bộ câu mẫu: 0,542 → 0,362 | `docs/benchmarks/intent-eval/chi-tiet-hinh.json` (sinh bằng `python -m livelift.nlp.eval_intent --ablation --coverage`, đo 25/09/2026); tên lớp: `livelift.nlp.labels.LABEL_DISPLAY` |
| `h7-giao-dien.png` | Giao diện thật — ảnh chụp tự động (Playwright, Chromium) bản build `fa64589` ngày 25/09/2026, lưới 2×2: (a) wizard bước 3, lịch 16 khối BẬT/TẮT bốc trước giờ phát của một phiên CHẠY THỬ; (b) feed bình luận trên bàn trợ live, câu có số điện thoại giả đã thành [SĐT]; (c) màn người dẫn cùng phiên — không có khối, không có nhánh; (d) kết quả một phiên Demo Vàng, nhãn DEMO | `python scripts/chup_giao_dien.py chup` (API + web production đang chạy) rồi `python scripts/chup_giao_dien.py ghep`; ảnh cắt và số đo: `docs/img/v2/` |

## Lưu ý trung thực khi trích hình

- Hình 3 và 5 là **mô phỏng Monte-Carlo**; dự án có **0 phiên thí nghiệm ngẫu nhiên thật**.
- Hình 5 **thay** bảng hiệu ứng lưu cũ (100% / 84% / 60%, docstring `sim/validate.py`, đo 02/09): bảng đó không tái lập được ở mã hiện tại. Trích số từ hình này kèm cỡ mẫu (n = 75 mỗi mức).
- Hình 4 là **sàn Poisson** — với CÙNG tỷ lệ nhấp và số người xem, MDE thật chỉ có thể lớn hơn. Tỷ lệ nhấp chưa đo được (cả hai panel là giả định); vùng 5–15 người xem là ước tính từ chi phí quảng cáo (CPM), **chưa đo**.
- Hình 2: nguồn VOD là dữ liệu quan sát lấy bằng yt-dlp, **không** qua API chính thức; các bộ nối API chính thức đã viết nhưng chưa chạy với khoá thật. `RESULTS_FREEZE_UNTIL` hiện để trống (tắt) trong `.env.example`; khi đặt, `/ket-qua` và `/bao-cao` bị khoá nhưng `GET /sessions/{id}/report` vẫn trả chênh lệch trung bình (đường lọt đã biết, kiểm toán 25/09) — hộp CỔNG 3 ghi rõ; vá xong thì sửa `html_h2()` và chạy lại `--chi h2`.
- `h6-nlp.png` đo **mức đồng thuận với nhãn tham chiếu do tác tử AI gán**, chưa phải độ chính xác so với người: chưa có nhãn người (bảng gán mù cho hai thành viên đã chuẩn bị nhưng chưa gán — `docs/benchmarks/intent-eval/gan-mu/README.md`). Dữ liệu là bình luận công khai của VOD lấy qua yt-dlp (quan sát, không qua API chính thức). Ma trận là của C2 vì đó là cấu hình đóng gói `intent_clf_v2.joblib`, chọn trước chứ không chọn theo điểm trên tập test.
- Trên `h6-nlp.png`, C1 (0,563) cao hơn C2 (0,542) về macro-F1, KTC chồng lấn — trích đủ cả hai, không gọi C2 là “tốt nhất”.
- `h7-giao-dien.png` là ảnh chụp giao diện: bình luận là dữ liệu mô phỏng tổng hợp của một phiên chạy thử (không phải khách thật); ô (d) là dữ liệu MẪU — không phải kết quả thí nghiệm (dự án có 0 phiên thí nghiệm ngẫu nhiên thật).

## Chạy lại

```
python scripts/ve_hinh_ho_so.py               # vẽ lại từ du-lieu/*.json (~1 phút)
python scripts/ve_hinh_ho_so.py --kiem        # chạy lại Monte-Carlo, đối chiếu TỪNG lần lặp với du-lieu/ (~9 phút)
python scripts/ve_hinh_ho_so.py --tinh-lai    # chạy lại Monte-Carlo và ghi đè du-lieu/ (khi mã đã đổi có chủ ý)
python -m livelift.nlp.eval_intent --ablation --coverage   # đo lại bộ phân loại ý định → chi-tiet-hinh.json
python scripts/ve_hinh_ho_so.py --chi h6      # rồi vẽ lại hình 6 từ chi-tiet-hinh.json (vài giây)
```

Cần `matplotlib`, Pillow, và Playwright + Chromium cho hình 2: cài bằng `pip install -e ".[hinh]"` rồi `playwright install chromium`.
