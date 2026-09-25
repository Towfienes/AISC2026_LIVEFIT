# FACT SHEET — Một bộ số chuẩn duy nhất

*Tạo 06/09/2026 · cập nhật 14/09/2026 · rà lại toàn bộ 25/09/2026 (sau kiểm toán thử thật trên `main` 390027b) ·
Mọi tài liệu (thuyết minh, slide, kế hoạch, mô tả) TRỎ VỀ file này.
Sửa số ở đây trước, rồi đồng bộ ra các tài liệu khác — không bao giờ ngược lại.*

> **Lý do tồn tại:** kiểm toán 06/09 phát hiện các tài liệu gốc đang lệch nhau
> (ngân sách 17,2M vs 15,2M; 31 vs 30 phiên; hạn nộp 14 vs 15/09). Một giám khảo
> kỹ tính bắt được lệch số trong 5 phút và mất niềm tin vào mọi số còn lại.

## 1. Các số PHẢI CHỐT (đang lệch giữa tài liệu — cần quyết định của nhóm)

| Số | Kế-Hoạch-Triển-Khai | Mô-Tả-Dự-Án | ĐÃ CHỐT | Ghi chú |
|---|---|---|---|---|
| **Hạn nộp vòng 1 AISC'26** | 14/09 (dòng 229) | 15/09 (dòng 536) | **Đã nộp 14/09/2026** | Bản đã nộp còn số cũ (A/A 4,5%; 0,271 — không tái lập được; "gán nhãn tay"; "thực đo 5–15 người xem" — thật ra là ước tính CPM) — mang trang đính chính khi thuyết trình vòng 2 |
| **Tổng ngân sách** | 17.200.000đ (§9.1) | 15.200.000đ (§8.2) | **Chưa chốt** (25/09/2026) | Khác nhau ở: quảng cáo 29 vs 30 phiên, bổ sung hàng 1,5M, poster 0,8M. Khuyến nghị: dùng bảng §9.1 chi tiết hơn làm gốc, cộng lại cho khớp |
| **Số phiên mục tiêu** | 31 (§8.4) | 30 (§8.2, §14) | **Chưa chốt** (25/09/2026) | Chọn MỘT số, dùng thống nhất. Hiện đã chạy **0** phiên thí nghiệm thật |
| **Người xem đồng thời mục tiêu** | ≥ 80 (§8.4) | "vài trăm" giả định CV 0,5 (§8.2) | **Chưa chốt** (25/09/2026) | **ƯỚC TÍNH, CHƯA ĐO: 300.000đ quảng cáo ≈ 5–15 người xem đồng thời** — tính trên giấy ngày 24/08 từ CPM Facebook 25–60 nghìn và tỷ lệ vào phòng 1–2% (`docs/research/2026-08-24-phan-bien-tai-lieu.md` mục R1). Chưa chạy phiên quảng cáo nào (`docs/TONG-KET-DU-AN.md`: "Chạy 2–3 phiên thử + quảng cáo đo chi phí thật" vẫn là việc chưa làm). Nếu ước tính đúng, mục tiêu 80 hụt khoảng 10 lần: phải hạ mục tiêu hoặc đổi chiến lược (đối tác) và sửa MỌI bảng lực thống kê theo |

**Mốc đã biết (25/09/2026):** AISC'26 vòng 1 nộp 14/09/2026; vòng 2 ngày **15/10/2026 tại UIT**,
bắt buộc có poster (trang BTC). Cuộc thi Sáng tạo trẻ Quốc gia về AI 2026, Bảng C, đường trường cử:
hạn nộp **30/09/2026** (`sang-tao-tre-2026/BRIEF-THE-LE.md` §2).

## 2. Các số đã đo được (nguồn: repo, sinh lại được bằng lệnh)

| Số | Giá trị | Nguồn kiểm chứng |
|---|---|---|
| Hiệu chuẩn A/A ước lượng viên | bác bỏ **3,50%** (7/200; danh nghĩa 5%), p nhị thức = **0,4168** | `scripts/do_lai_so_hieu_chuan.py` → `docs/benchmarks/so-hieu-chuan.json`, đo lại 25/09/2026 trên cây sạch 17c3ee1 (V3), `--kiem` khớp từng chữ số và trùng lần đo 14/09/2026; `--kiem` chạy lại 25/09/2026 trên `816ed60`: khớp. **Số cũ 4,5%/0,872 là đo 30/08, KHÔNG tái lập được** |
| Độ phủ KTC 95% (A/A) | **96,50%** (193/200) — mặt kia của dòng trên (193 = 200 − 7): `sim/validate.py` tính bác bỏ và độ phủ từ CÙNG một KTC, nên đây không độc lập, không trích như bằng chứng thứ hai. Bằng chứng riêng về độ phủ là dòng thu hồi (37/40) | cùng nguồn. Số cũ 95,5% đã thay. Hội đồng thử 25/09/2026 bắt lỗi trình bày; hồ sơ Bảng 4 ghi "đối ngẫu với dòng trên, không độc lập" |
| Thu hồi tác động biết trước | độ lệch tương đối **−0,84%**, phủ KTC 92,50% (37/40), lực 40/40 | cùng nguồn. **Số cũ −0,3% đã thay**. Chỉ 40 lần lặp: KTC nhị thức của độ phủ 37/40 khá rộng |
| MDE lượt nhấp, lực 80% (mô phỏng) | **16,4%** ở ~59 người xem đồng thời (40–114): MDE giải tích từ CV trong phiên **0,263** đo trên 8 phiên mô phỏng (tuân thủ 0,95, biên ×1,2); sàn Poisson cùng chỗ 16,0%. Số **20,1%** (quét lực 4 mức × 60 lặp ngày 30/08) là một đại lượng khác và **chưa đo lại** — kiểm 25/09/2026, không lệnh nào trong kho sinh lại được, không trích như số hiện hành | `python scripts/ve_hinh_ho_so.py` → `docs/competition/sang-tao-tre-2026/hinh/du-lieu/tom-tat.json` (khoá `h4.mo_phong`), Hình 4 hồ sơ; hàm `livelift.analysis.power` |
| Intent classifier — bộ câu mẫu | macro-F1 0,870 — **trên 320 câu mẫu do AI (Claude) soạn ngày 01/09, 5-fold CV**. Không bao giờ quote một mình | `python -m livelift.nlp.train_intent` |
| ⚠️ Quy tắc quote số intent | Quote theo bộ ba **0,870 (bộ câu do AI soạn) / 0,211 (chat thật, bản cũ v1) / 0,542 (chat thật, bản mới v2, đo lại 25/09)**, luôn kèm cỡ mẫu, cách chia, và câu "nhãn tham chiếu do tác tử AI gán". 0,211 → 0,542 là thang **11 lớp** (v1 chỉ có 6 lớp, lại chấm với ngưỡng 0,45; v2 chấm chưa áp ngưỡng) — nói mức tăng thì kèm cặp **cùng thang 6 lớp 0,370 → 0,572** (dòng "cùng thang 6 lớp" bên dưới). v2 chưa phải mặc định: bật bằng `LIVELIFT_INTENT_MODEL=v2` | `docs/benchmarks/intent-classifier.md` · `03-NLP-NANG-CAP.md` |
| Live-fire lô CŨ 06/09 (đã thay) | 262 phút, 14.903 bình luận | bị lô 10/09 thay thế — dùng dòng "Bình luận VOD công khai" bên dưới |
| Hiệu chỉnh KuaiLive | 1,16M phòng live shop thật (SIGIR 2026) | `docs/benchmarks/kuailive-calibration.md` |
| Bộ kiểm thử | **2.066 test nhanh + 17 cổng chậm (13 mô phỏng/thống kê · 1 đánh giá NLP · 3 cổng build CSS) + 10 test trình duyệt = 2.093 test thu thập được** (thu thập ngày 25/09/2026 bằng `scripts/dong_bo_so_test.py --xem-truoc`). Đây là số test pytest **thu thập**, không phải số đã chạy. Kết quả chạy gần nhất trên nhánh hoàn thiện (25/09/2026 22:43–23:06, cây sạch tại `816ed60`, sau các sửa của hội đồng thử): 2.064 test nhanh đạt · 2 bỏ qua, 17/17 cổng chậm, 10/10 test trình duyệt — **2.091 đạt, 0 lỗi** (lần tích hợp trước, sau 14266d2, cùng kết quả), với scikit-learn 1.9.0 (ghim trong `pyproject` từ ba96b73); lần trước (V3, 17c3ee1): 2.030 đạt. Trên main 390027b, cài theo ràng buộc cũ `scikit-learn>=1.5,<1.8` (ra 1.7.2) thì 5 test NLP đỏ, vì hai artifact ý định được huấn luyện bằng 1.9.0. Lịch sử: 1.555 + 17 + 10 = 1.582 (17/09), 1.157 + 17 = 1.174 (15/09). Nhóm chậm từng bị gọi chung là Monte-Carlo — sai, chỉ 13 trong 17 là mô phỏng/thống kê | `pytest -m "not slow"` · `pytest -m "slow and not browser"` · `pytest -m browser`; **chạy `scripts/dong_bo_so_test.py --xem-truoc` trước mỗi lần nộp** — nó lấy pytest làm nguồn duy nhất, quét README, trang chủ và chính dòng này, báo lỗi nếu một mẫu không còn khớp |
| Sổ sự cố | **121 sự cố có nguyên nhân gốc** (đếm lại 25/09/2026: 121 hàng, trong đó 61 hàng ngày 25/09 — đợt hoàn thiện hồ sơ trên nhánh `hoan-thien/ho-so-2509`) | đếm số hàng bảng bắt đầu bằng ngày trong `docs/incident-log.md` |
| Bình luận VOD công khai (QUAN SÁT) | **19.126 bình luận · 16 buổi live · 7 ngành hàng** (lô đo 10/09/2026). Chat của 16 VOD YouTube **công khai**, tải bằng **yt-dlp** (không phải API chính thức của YouTube), nạp qua `POST /replays/youtube` của LiveLift. **Chỉ phân tích quan sát**: không buổi nào có can thiệp hay bốc thăm. ⚠️ **Không phải một tệp có sẵn** — store là in-memory, số này **sinh lại** bằng `scripts/live_fire_da_nguon.py nap`. Kiểm kê đĩa 14/09: ảnh chụp store chỉ còn 757 bình luận của phiên **mô phỏng** | `docs/benchmarks/live-fire-da-nguon.md` §1 |
| Bình luận thật **có nhãn** trên đĩa | **393** do tác tử AI gán ngày 09/09 (3 buổi, bộ test — **chưa có nhãn người**) + **1.800** LLM gán (1 buổi, chỉ train) + **320** câu mẫu do AI soạn. ⚠️ Đính chính 15/09: các bản trước ghi "393 người gán, gán mù" và "320 câu nhóm tự viết" — **sai**, transcript cho thấy cả hai do Claude ghi. Tệp nhãn nằm ngoài git (chính sách PII) | `data/labeling/README.md`; kê khai LLM: `03-NLP-NANG-CAP.md` §7 |
| ⚠️ Số 0,271 (08/09) — **KHÔNG DÙNG** | Từng công bố là "macro-F1 0,271 trên 200 bình luận gán nhãn tay". **Không tái lập được** (tệp nhãn 08/09 không được lưu); nguồn nhãn chưa kiểm chứng được — tệp nhãn không được lưu. Từ 14/09 số "trước cải tiến" chính thức là 0,211 (dòng dưới) | `docs/benchmarks/intent-classifier.md` |
| **Bộ phân loại ý định — số TRƯỚC chính thức (14/09)** | **macro-F1 0,211 · KTC95 [0,172; 0,247]** · accuracy 0,338 · precision nhãn hành động 23,0% — đo trên **393 bình luận thật với nhãn tham chiếu do tác tử AI gán, 3 buổi live, leave-one-session-out**. Nghĩa là số đo mức đồng thuận với nhãn AI, chưa phải độ chính xác so với con người | `python -m livelift.nlp.eval_intent` → `docs/benchmarks/intent-eval/results.json` |
| **Bộ phân loại ý định — số SAU (cấu hình v2, đo lại 25/09/2026)** | **macro-F1 0,542 · KTC95 [0,478; 0,625]** · accuracy 0,730 · precision nhãn hành động 65,5% (38/58) · recall nhãn hành động 55,1% (38/69; bản cũ 78,3%) · **11 lớp** · artifact 942.653 byte (≈ 921 KiB), không cần torch. Đo lại trên dữ liệu đã lọc lại tên tài khoản (PII) ngày 25/09. Số 14/09 **0,565 [0,491; 0,649]** đo trên dữ liệu TRƯỚC khi lọc — thay bằng số này, hai KTC chồng lấn gần hết | cùng lệnh trên (`--ablation --coverage`) → `docs/benchmarks/intent-eval/results.json` (dòng C2); phương pháp + ablation + hạn chế: `docs/competition/sang-tao-tre-2026/03-NLP-NANG-CAP.md` |
| ⚠️ Bất định thật của hai số trên | Nằm ở **cấp buổi live**, không ở KTC theo dòng: macro-F1 của bản mới đi từ **0,368** (buổi 0% ý định mua) đến **0,599** (buổi 48% ý định mua) — số 14/09 là 0,372 đến 0,635. n_session = **3** | `results.json` → dòng C2 → `per_session`; §4 của `03-NLP-NANG-CAP.md` |
| **Bộ phân loại ý định — cùng thang 6 lớp (A9 → A8, đo 25/09/2026)** | v1 đang chạy (B2) chấm trên thang 6 lớp gộp: **macro-F1 0,370 · KTC95 [0,306; 0,432]** → v2 (11 lớp, gộp về 6 khi chấm): **0,572 · KTC95 [0,471; 0,667]**. Cùng 393 bình luận, cùng nhãn do tác tử AI gán, cùng leave-one-session-out. Theo buổi: ở buổi `47o…` hai bản gần bằng nhau (0,683 / 0,729) — mức tăng đến chủ yếu từ hai buổi còn lại. Không so dòng này với thang 11 lớp | cùng lệnh (`--ablation --coverage`) → `docs/benchmarks/intent-eval/results.md` (dòng A8, A9), `results.json`; dòng A9 thêm ở `cd5190b` (hội đồng thử 25/09/2026) |
| Artifact ý định đang phục vụ mặc định | **v1** (`intent_clf.joblib`, 6 lớp). v2 bật bằng `LIVELIFT_INTENT_MODEL=v2` — **chưa phải mặc định**, quy trình thăng cấp ghi ở `03-NLP-NANG-CAP.md` §11 | `src/livelift/nlp/intent.py` |
| Độ phủ KTC 95% dưới hiệu ứng lưu (mô phỏng) | bán rã 0 giây → **96%** (72/75); 120 giây → **76%** (57/75); 180 giây → **57%** (43/75); lệch tương đối −1,5% / −21,5% / −31,6%. n = 75 mỗi mức (3 seed × 25 lần lặp × 6 phiên 90 phút) | `python scripts/ve_hinh_ho_so.py --kiem` → `docs/competition/sang-tao-tre-2026/hinh/du-lieu/hieu-ung-luu.json`, Hình 5 hồ sơ, `hinh/NGUON.md`; tham số bóc từ `tests/test_sim_validation.py::test_estimator_under_carryover_interference`. **Bảng cũ trong docstring `sim/validate.py` (đo 02/09) không tái lập được ở mã hiện tại — không trích** |
| Điều kiện của điểm MDE mô phỏng | ~59 người xem đồng thời (40–114), 8 phiên mô phỏng (Hình 4). Số 20,1% của phép quét 30/08 từng ghi ~45–62 người xem — chưa đo lại | `hinh/du-lieu/tom-tat.json`; `src/livelift/sim/simulator.py`; **phải nói kèm: theo ƯỚC TÍNH (chưa đo) 300.000đ quảng cáo chỉ kéo được 5–15 người xem đồng thời**; ở 15 người xem, MDE theo đơn hàng là 179–327% với 18 phiên (`docs/benchmarks/order-mde.md`) |
| Làm mù người dẫn | **MỘT PHẦN.** `/host` chỉ nhận 4 trường (thời gian đã phát, sản phẩm đang ghim, giá, tồn kho), không có lịch, khối hay nhánh. Nhưng người dẫn vẫn thấy sản phẩm đang ghim — chính là can thiệp — và ở chế độ Tự ghim lệnh ghim chỉ đến trong khối BẬT (khối TẮT hiện "Chưa ghim sản phẩm"), nên đoán được nhánh. Không viết "người dẫn bị làm mù" trọn vẹn; phép so là chiến lược ghim của LiveLift với cách làm thường lệ, tính cả phản ứng của người dẫn | `src/livelift/api/schemas.py` (`HostState`, `extra="forbid"`), `tests/test_case_nguoi_dung_that.py::test_case_8…`; `PREREGISTRATION.md` §1, §9; hồ sơ mục 5.3 |
| Số bản migration | 9 (0001–0009) | `ls src/livelift/migrations/*.up.sql` |
| Số phiên thí nghiệm ngẫu nhiên THẬT đã chạy | **0** (kiểm lại 25/09/2026). Phiên CHẠY THỬ (tập dượt) không tính | trung thực — không tuyên bố khác đi cho đến khi có |

## 3. Số thị trường dùng trong hồ sơ (kèm nguồn, cập nhật 09/2026)

| Số | Giá trị | Nguồn |
|---|---|---|
| Phiên live bán hàng VN/tháng | ~2,5 triệu; >50.000 nhà bán | Truy tới gốc 25/09/2026: vneconomy.vn, bài 18/11/2024, dẫn số của AccessTrade Việt Nam — số thứ cấp, năm 2024. Tài liệu 17/09 khuyên không dùng; nếu dùng phải ghi nguồn và năm |
| TikTok Shop VN | 42% GMV e-commerce, +148% YoY (H1/2025) | khảo sát SOTA 06/09 |
| Tỷ lệ chuyển đổi livestream vs feed | ~7,8% vs 2,1% (3,7×) | khảo sát SOTA 06/09 |
| Live commerce SEA | ~14% GMV sàn (~17,6 tỷ USD) | khảo sát SOTA 06/09 |
| Bằng chứng bình duyệt bài toán ghim | Xie–Sharma–Mehra, *POM* 34(12), 2025, DOI 10.1177/10591478251314455: trình bày sản phẩm **lâu hơn → doanh thu sản phẩm cao hơn**, nhưng thời lượng trình bày **trung bình tăng → doanh thu cả phiên giảm** (một đánh đổi, dữ liệu hồi cứu 2 nền tảng Trung Quốc). ⚠️ Đính chính 15/09: các bản trước ghi "chữ U ngược" — **sai**, tóm tắt bài báo mô tả hai quan hệ đơn điệu | tóm tắt trên Crossref |

## 4. Giá gói (TRẠNG THÁI: giả thuyết — 0 phỏng vấn WTP, kiểm lại 25/09/2026)

Free (báo cáo sau phiên) → Pro 990k/tháng → Agency 3,9M/tháng → Performance (% giá trị
tăng thêm, đo bằng holdback 10% khối). **Không trình bày như giá đã kiểm chứng** —
ghi "định giá dự kiến, chưa phỏng vấn nhà bán nào; sẽ hiệu chỉnh sau các phỏng vấn đầu tiên".
Chuẩn ngành tham chiếu: experimentation platform bán usage-based freemium; lift đo được
là công cụ chứng minh ROI, không phải đơn vị tính tiền.

## 5. Quy tắc dùng file này

1. Trước khi viết bất kỳ số nào vào thuyết minh/slide: tra ở đây. Không có → thêm vào đây trước.
0. **Luật thêm ngày 14/09/2026:** hồ sơ thuyết minh có câu trỏ thẳng vào file này
   ("Mọi số của hồ sơ chốt ở docs/competition/FACT-SHEET.md"). Chấm lại hồ sơ hôm ấy
   phát hiện file này KHÔNG chứa hai con số mà hồ sơ nói nó chốt, và bản thân nó còn
   dừng ở lô đo 06/09. Một giám khảo mở file ra kiểm mất 30 giây là bắt được. Từ nay:
   **sửa hồ sơ mà không sửa file này là chưa xong việc.**
2. Ô nào còn ghi "Chưa chốt" là việc P0 chưa xong — không bịa số cho đủ ô.
3. Người review chéo hồ sơ đối chiếu từng số trong bản nộp với file này trước khi nộp ≥24h.
4. **Luật thêm ngày 25/09/2026:** "ước tính" và "đo được" là hai cột khác nhau. Con số
   5–15 người xem từng bị ghi "thực đo" ở đây và lan sang hồ sơ vòng 1 — nó là phép tính
   trên giấy. Số nào chưa có lệnh chạy lại được thì ghi rõ là ước tính.
