# FACT SHEET — Một bộ số chuẩn duy nhất

*Tạo 06/09/2026 · cập nhật 14/09/2026 · Mọi tài liệu (thuyết minh, slide, kế hoạch, mô tả) TRỎ VỀ file này.
Sửa số ở đây trước, rồi đồng bộ ra các tài liệu khác — không bao giờ ngược lại.*

> **Lý do tồn tại:** kiểm toán 06/09 phát hiện các tài liệu gốc đang lệch nhau
> (ngân sách 17,2M vs 15,2M; 31 vs 30 phiên; hạn nộp 14 vs 15/09). Một giám khảo
> kỹ tính bắt được lệch số trong 5 phút và mất niềm tin vào mọi số còn lại.

## 1. Các số PHẢI CHỐT (đang lệch giữa tài liệu — cần quyết định của nhóm)

| Số | Kế-Hoạch-Triển-Khai | Mô-Tả-Dự-Án | ĐÃ CHỐT | Ghi chú |
|---|---|---|---|---|
| **Hạn nộp vòng 1** | 14/09 (dòng 229) | 15/09 (dòng 536) | ⬜ __/09 | **GỌI BTC XÁC MINH HÔM NAY** — "trễ 1 ngày = loại" |
| **Tổng ngân sách** | 17.200.000đ (§9.1) | 15.200.000đ (§8.2) | ⬜ | Khác nhau ở: quảng cáo 29 vs 30 phiên, bổ sung hàng 1,5M, poster 0,8M. Khuyến nghị: dùng bảng §9.1 chi tiết hơn làm gốc, cộng lại cho khớp |
| **Số phiên mục tiêu** | 31 (§8.4) | 30 (§8.2, §14) | ⬜ | Chọn MỘT số, dùng thống nhất |
| **Người xem đồng thời mục tiêu** | ≥ 80 (§8.4) | "vài trăm" giả định CV 0,5 (§8.2) | ⬜ | **Thực đo: 300k quảng cáo ≈ 5–15 đồng thời** (TONG-KET P0) — mục tiêu 80 hụt ~10 lần. Phải hạ mục tiêu hoặc đổi chiến lược (đối tác) và sửa MỌI bảng lực thống kê theo |

## 2. Các số đã đo được (nguồn: repo, sinh lại được bằng lệnh)

| Số | Giá trị | Nguồn kiểm chứng |
|---|---|---|
| Hiệu chuẩn A/A ước lượng viên | bác bỏ **3,50%** (7/200; danh nghĩa 5%), p nhị thức = **0,4168** | `scripts/do_lai_so_hieu_chuan.py` → `docs/benchmarks/so-hieu-chuan.json`, đo 14/09/2026. **Số cũ 4,5%/0,872 là đo 30/08, KHÔNG tái lập được** |
| Độ phủ KTC 95% (A/A) | **96,50%** (193/200), p nhị thức 0,4168 | cùng nguồn. Số cũ 95,5% đã thay |
| Thu hồi tác động biết trước | độ lệch tương đối **−0,84%**, phủ KTC 92,50% (37/40), lực 40/40 | cùng nguồn. **Số cũ −0,3% đã thay** |
| MDE đo được (điều kiện sim hiệu chỉnh) | 20,1% | sweep 4 mức tác động × 60 lặp, `analysis/power` |
| Intent classifier | macro-F1 0,870 — **trên 320 câu tự biên soạn, 5-fold CV** | `python -m livelift.nlp.train_intent` |
| ⚠️ Quy tắc quote số intent | **Cập nhật 14/09:** không còn "đang đo" — đã đo xong. Quote theo bộ ba **0,870 (bộ biên soạn) / 0,211 (chat thật, bản cũ) / 0,565 (chat thật, bản mới)**, luôn kèm cỡ mẫu và cách chia | `docs/benchmarks/intent-classifier.md` · `03-NLP-NANG-CAP.md` |
| Live-fire VOD thật | 262 phút, 14.903 bình luận qua API | phiên "quan sát" trong DB |
| Hiệu chỉnh KuaiLive | 1,16M phòng live shop thật (SIGIR 2026) | `docs/benchmarks/kuailive-calibration.md` |
| Bộ kiểm thử | **1.157 test nhanh xanh + 17 cổng Monte-Carlo = 1.174** (đếm 15/09/2026 bằng `scripts/dong_bo_so_test.py --xem-truoc`, sau khi gộp các đợt NLP / bảo mật / hạ tầng trong ngày) | `pytest -m "not slow"` và `pytest -m slow`; **chạy `scripts/dong_bo_so_test.py --xem-truoc` trước mỗi lần nộp** — nó lấy pytest làm nguồn duy nhất và tự báo chỗ lệch |
| Sổ sự cố | **46 sự cố có nguyên nhân gốc** (đếm 15/09/2026 — thêm sự cố số A/A không tái lập và sự cố bộ lọc lọt handle có dấu) | đếm số hàng bảng trong `docs/incident-log.md` |
| Bình luận thật đã chạy qua API | **19.126 bình luận · 16 buổi live · 7 ngành hàng** (lô đo 10/09/2026). ⚠️ **Không phải một tệp có sẵn** — store là in-memory, số này **sinh lại** từ 16 VOD YouTube công khai bằng `scripts/live_fire_da_nguon.py nap`. Kiểm kê đĩa 14/09: ảnh chụp store chỉ còn 757 bình luận của phiên **mô phỏng** | `docs/benchmarks/live-fire-da-nguon.md` §1 — con số 14.903 ghi ở bản 06/09 là lô CŨ, đã bị lô 10/09 thay thế |
| Bình luận thật **có nhãn** trên đĩa | **393** người gán (3 buổi, bộ test) + **1.800** LLM gán (1 buổi, chỉ train) + **320** câu tự biên soạn | `data/labeling/README.md`; kê khai LLM: `03-NLP-NANG-CAP.md` §7 |
| Bộ phân loại ý định trên CHAT THẬT | **macro-F1 0,271** (200 bình luận gán nhãn tay, 08/09) — thua baseline luôn đoán "khac". ⚠️ **Con số này KHÔNG tái lập được đến từng dòng** (file nhãn không được lưu) — từ 14/09 dùng số dưới đây | `docs/benchmarks/intent-classifier.md`; **luôn quote CẶP 0,870 / 0,271, không bao giờ quote riêng số đẹp** |
| **Bộ phân loại ý định — số TRƯỚC chính thức (14/09)** | **macro-F1 0,211 · KTC95 [0,172; 0,247]** · accuracy 0,338 · precision nhãn hành động 23,0% — đo trên **393 bình luận thật gán nhãn tay, 3 buổi live, leave-one-session-out** | `python -m livelift.nlp.eval_intent` → `docs/benchmarks/intent-eval/results.json` |
| **Bộ phân loại ý định — số SAU (14/09, `intent_clf_v2`)** | **macro-F1 0,565 · KTC95 [0,491; 0,649]** · accuracy 0,741 · precision nhãn hành động 66,7% · **11 lớp** · artifact 925 KB, không cần torch | cùng lệnh trên; phương pháp + ablation + hạn chế: `docs/competition/sang-tao-tre-2026/03-NLP-NANG-CAP.md` |
| ⚠️ Bất định thật của hai số trên | Nằm ở **cấp buổi live**, không ở KTC theo dòng: macro-F1 của bản mới đi từ **0,372** (buổi 0% ý định mua) đến **0,635** (buổi 48% ý định mua). n_session = **3** | `results.json` → `per_session`; §4 của `03-NLP-NANG-CAP.md` |
| Artifact ý định đang phục vụ mặc định | **v1** (`intent_clf.joblib`, 6 lớp). v2 bật bằng `LIVELIFT_INTENT_MODEL=v2` — **chưa phải mặc định**, quy trình thăng cấp ghi ở `03-NLP-NANG-CAP.md` §11 | `src/livelift/nlp/intent.py` |
| Độ phủ KTC dưới hiệu ứng lưu | bán rã 0 giây → **100%**; 120 giây → **84%**; 180 giây → **60%** (lệch −0,3% / −20,3% / −29,8%) | docstring `run_validation` trong `src/livelift/sim/validate.py`; đo 02/09 trên SimParams đã hiệu chỉnh KuaiLive. **Con số 76% cũ là TRƯỚC hiệu chỉnh, đã bị thay** |
| Điều kiện đo MDE 20,1% | mô phỏng ~45–62 người xem đồng thời | `src/livelift/sim/simulator.py`; **phải nói kèm: đo thật chỉ được 5–15 người xem đồng thời** |
| Số bản migration | 9 (0001–0009) | `ls src/livelift/migrations/*.up.sql` |
| Số phiên live THẬT đã chạy | **0** (tính đến 14/09/2026) | trung thực — không tuyên bố khác đi cho đến khi có |

## 3. Số thị trường dùng trong hồ sơ (kèm nguồn, cập nhật 09/2026)

| Số | Giá trị | Nguồn |
|---|---|---|
| Phiên live bán hàng VN/tháng | ~2,5 triệu; >50.000 nhà bán | Mô-Tả §2 (giữ nguồn gốc khi trích) |
| TikTok Shop VN | 42% GMV e-commerce, +148% YoY (H1/2025) | khảo sát SOTA 06/09 |
| Tỷ lệ chuyển đổi livestream vs feed | ~7,8% vs 2,1% (3,7×) | khảo sát SOTA 06/09 |
| Live commerce SEA | ~14% GMV sàn (~17,6 tỷ USD) | khảo sát SOTA 06/09 |
| Bằng chứng bình duyệt bài toán ghim | Xie–Sharma–Mehra, POM 2025: thời lượng pin vs doanh thu phiên có dạng **chữ U ngược** | slide động cơ |

## 4. Giá gói (TRẠNG THÁI: giả thuyết — chưa phỏng vấn WTP nào)

Free (báo cáo sau phiên) → Pro 990k/tháng → Agency 3,9M/tháng → Performance (% giá trị
tăng thêm, đo bằng holdback 10% khối). **Không trình bày như giá đã kiểm chứng** —
ghi "định giá dự kiến, sẽ hiệu chỉnh sau 5 phỏng vấn nhà bán (kế hoạch tuần này)".
Chuẩn ngành tham chiếu: experimentation platform bán usage-based freemium; lift đo được
là công cụ chứng minh ROI, không phải đơn vị tính tiền.

## 5. Quy tắc dùng file này

1. Trước khi viết bất kỳ số nào vào thuyết minh/slide: tra ở đây. Không có → thêm vào đây trước.
0. **Luật thêm ngày 14/09/2026:** hồ sơ thuyết minh có câu trỏ thẳng vào file này
   ("Mọi số của hồ sơ chốt ở docs/competition/FACT-SHEET.md"). Chấm lại hồ sơ hôm ấy
   phát hiện file này KHÔNG chứa hai con số mà hồ sơ nói nó chốt, và bản thân nó còn
   dừng ở lô đo 06/09. Một giám khảo mở file ra kiểm mất 30 giây là bắt được. Từ nay:
   **sửa hồ sơ mà không sửa file này là chưa xong việc.**
2. Ô ⬜ nào còn trống sau 08/09 là việc P0 chưa xong.
3. Người review chéo hồ sơ đối chiếu từng số trong bản nộp với file này trước khi nộp ≥24h.
