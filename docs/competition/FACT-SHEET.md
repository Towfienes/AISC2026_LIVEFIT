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
| **Hạn nộp vòng 1 AISC'26** | 14/09 (dòng 229) | 15/09 (dòng 536) | **Đã nộp 14/09/2026** | Bản đã nộp còn số cũ (A/A 4,5%; 0,271; "gán nhãn tay"; "thực đo 5–15 người xem") — mang trang đính chính khi thuyết trình vòng 2 |
| **Tổng ngân sách** | 17.200.000đ (§9.1) | 15.200.000đ (§8.2) | **Chưa chốt** (25/09/2026) | Khác nhau ở: quảng cáo 29 vs 30 phiên, bổ sung hàng 1,5M, poster 0,8M. Khuyến nghị: dùng bảng §9.1 chi tiết hơn làm gốc, cộng lại cho khớp |
| **Số phiên mục tiêu** | 31 (§8.4) | 30 (§8.2, §14) | **Chưa chốt** (25/09/2026) | Chọn MỘT số, dùng thống nhất. Hiện đã chạy **0** phiên thí nghiệm thật |
| **Người xem đồng thời mục tiêu** | ≥ 80 (§8.4) | "vài trăm" giả định CV 0,5 (§8.2) | **Chưa chốt** (25/09/2026) | **ƯỚC TÍNH, CHƯA ĐO: 300.000đ quảng cáo ≈ 5–15 người xem đồng thời** — tính trên giấy ngày 24/08 từ CPM Facebook 25–60 nghìn và tỷ lệ vào phòng 1–2% (`docs/research/2026-08-24-phan-bien-tai-lieu.md` mục R1). Chưa chạy phiên quảng cáo nào (`docs/TONG-KET-DU-AN.md`: "Chạy 2–3 phiên thử + quảng cáo đo chi phí thật" vẫn là việc chưa làm). Nếu ước tính đúng, mục tiêu 80 hụt khoảng 10 lần: phải hạ mục tiêu hoặc đổi chiến lược (đối tác) và sửa MỌI bảng lực thống kê theo |

**Mốc đã biết (25/09/2026):** AISC'26 vòng 1 nộp 14/09/2026; vòng 2 ngày **15/10/2026 tại UIT**,
bắt buộc có poster (trang BTC). Cuộc thi Sáng tạo trẻ Quốc gia về AI 2026, Bảng C, đường trường cử:
hạn nộp **30/09/2026** (`sang-tao-tre-2026/BRIEF-THE-LE.md` §2).

## 2. Các số đã đo được (nguồn: repo, sinh lại được bằng lệnh)

| Số | Giá trị | Nguồn kiểm chứng |
|---|---|---|
| Hiệu chuẩn A/A ước lượng viên | bác bỏ **3,50%** (7/200; danh nghĩa 5%), p nhị thức = **0,4168** | `scripts/do_lai_so_hieu_chuan.py` → `docs/benchmarks/so-hieu-chuan.json`, đo 14/09/2026; `--kiem` chạy lại 25/09/2026 trên 390027b khớp từng chữ số. **Số cũ 4,5%/0,872 là đo 30/08, KHÔNG tái lập được** |
| Độ phủ KTC 95% (A/A) | **96,50%** (193/200), p nhị thức 0,4168 | cùng nguồn. Số cũ 95,5% đã thay |
| Thu hồi tác động biết trước | độ lệch tương đối **−0,84%**, phủ KTC 92,50% (37/40), lực 40/40 | cùng nguồn. **Số cũ −0,3% đã thay**. Chỉ 40 lần lặp: KTC nhị thức của độ phủ 37/40 khá rộng |
| MDE đo được (điều kiện sim hiệu chỉnh) | 20,1% | sweep 4 mức tác động × 60 lặp, `analysis/power` |
| Intent classifier — bộ câu mẫu | macro-F1 0,870 — **trên 320 câu mẫu do AI (Claude) soạn ngày 01/09, 5-fold CV**. Không bao giờ quote một mình | `python -m livelift.nlp.train_intent` |
| ⚠️ Quy tắc quote số intent | Quote theo bộ ba **0,870 (bộ câu do AI soạn) / 0,211 (chat thật, bản cũ v1) / 0,542 (chat thật, bản mới v2, đo lại 25/09)**, luôn kèm cỡ mẫu, cách chia, và câu "nhãn tham chiếu do tác tử AI gán". v2 chưa phải mặc định: bật bằng `LIVELIFT_INTENT_MODEL=v2` | `docs/benchmarks/intent-classifier.md` · `03-NLP-NANG-CAP.md` |
| Live-fire lô CŨ 06/09 (đã thay) | 262 phút, 14.903 bình luận | bị lô 10/09 thay thế — dùng dòng "Bình luận VOD công khai" bên dưới |
| Hiệu chỉnh KuaiLive | 1,16M phòng live shop thật (SIGIR 2026) | `docs/benchmarks/kuailive-calibration.md` |
| Bộ kiểm thử | **1.892 test nhanh + 17 cổng chậm (13 mô phỏng/thống kê · 1 đánh giá NLP · 3 cổng build CSS) + 10 test trình duyệt = 1.919 test thu thập được** (thu thập ngày 25/09/2026 bằng `scripts/dong_bo_so_test.py --xem-truoc`). Đây là số test pytest **thu thập**, không phải số đã chạy. Kết quả chạy gần nhất (25/09/2026, đều trên main 390027b — chưa chạy trên nhánh hoàn thiện): 17/17 cổng chậm đạt; 10/10 test trình duyệt đạt; bộ nhanh của main 390027b (1.803 test) 1.800 đạt · 3 bỏ qua · 0 lỗi trên clone sạch với scikit-learn 1.9.0 — **trên main 390027b, cài theo ràng buộc cũ `scikit-learn>=1.5,<1.8` (ra 1.7.2) thì 5 test NLP đỏ**, vì hai artifact ý định được huấn luyện bằng 1.9.0. Sau khi sửa ghim phiên bản phải chạy lại bộ nhanh rồi mới ghi "xanh". Lịch sử: 1.555 + 17 + 10 = 1.582 (17/09), 1.157 + 17 = 1.174 (15/09). Nhóm chậm từng bị gọi chung là Monte-Carlo — sai, chỉ 13 trong 17 là mô phỏng/thống kê | `pytest -m "not slow"` · `pytest -m "slow and not browser"` · `pytest -m browser`; **chạy `scripts/dong_bo_so_test.py --xem-truoc` trước mỗi lần nộp** — nó lấy pytest làm nguồn duy nhất, quét README, trang chủ và chính dòng này, báo lỗi nếu một mẫu không còn khớp |
| Sổ sự cố | **60 sự cố có nguyên nhân gốc** (đếm lại 25/09/2026: 60 hàng, không có hàng nào sau 18/09) | đếm số hàng bảng bắt đầu bằng ngày trong `docs/incident-log.md` |
| Bình luận VOD công khai (QUAN SÁT) | **19.126 bình luận · 16 buổi live · 7 ngành hàng** (lô đo 10/09/2026). Chat của 16 VOD YouTube **công khai**, tải bằng **yt-dlp** (không phải API chính thức của YouTube), nạp qua `POST /replays/youtube` của LiveLift. **Chỉ phân tích quan sát**: không buổi nào có can thiệp hay bốc thăm. ⚠️ **Không phải một tệp có sẵn** — store là in-memory, số này **sinh lại** bằng `scripts/live_fire_da_nguon.py nap`. Kiểm kê đĩa 14/09: ảnh chụp store chỉ còn 757 bình luận của phiên **mô phỏng** | `docs/benchmarks/live-fire-da-nguon.md` §1 |
| Bình luận thật **có nhãn** trên đĩa | **393** do tác tử AI gán ngày 09/09 (3 buổi, bộ test — **chưa có nhãn người**) + **1.800** LLM gán (1 buổi, chỉ train) + **320** câu mẫu do AI soạn. ⚠️ Đính chính 15/09: các bản trước ghi "393 người gán, gán mù" và "320 câu nhóm tự viết" — **sai**, transcript cho thấy cả hai do Claude ghi. Tệp nhãn nằm ngoài git (chính sách PII) | `data/labeling/README.md`; kê khai LLM: `03-NLP-NANG-CAP.md` §7 |
| ⚠️ Số 0,271 (08/09) — **KHÔNG DÙNG** | Từng công bố là "macro-F1 0,271 trên 200 bình luận gán nhãn tay". **Không tái lập được** (tệp nhãn 08/09 không được lưu) và nguồn nhãn ghi sai. Từ 14/09 số "trước cải tiến" chính thức là 0,211 (dòng dưới) | `docs/benchmarks/intent-classifier.md` |
| **Bộ phân loại ý định — số TRƯỚC chính thức (14/09)** | **macro-F1 0,211 · KTC95 [0,172; 0,247]** · accuracy 0,338 · precision nhãn hành động 23,0% — đo trên **393 bình luận thật với nhãn tham chiếu do tác tử AI gán, 3 buổi live, leave-one-session-out**. Nghĩa là số đo mức đồng thuận với nhãn AI, chưa phải độ chính xác so với con người | `python -m livelift.nlp.eval_intent` → `docs/benchmarks/intent-eval/results.json` |
| **Bộ phân loại ý định — số SAU (cấu hình v2, đo lại 25/09/2026)** | **macro-F1 0,542 · KTC95 [0,478; 0,625]** · accuracy 0,730 · precision nhãn hành động 65,5% (38/58) · recall nhãn hành động 55,1% (38/69; bản cũ 78,3%) · **11 lớp** · artifact 925 KB, không cần torch. Đo lại trên dữ liệu đã lọc lại tên tài khoản (PII) ngày 25/09. Số 14/09 **0,565 [0,491; 0,649]** đo trên dữ liệu TRƯỚC khi lọc — thay bằng số này, hai KTC chồng lấn gần hết | cùng lệnh trên (`--ablation --coverage`) → `docs/benchmarks/intent-eval/results.json` (dòng C2); phương pháp + ablation + hạn chế: `docs/competition/sang-tao-tre-2026/03-NLP-NANG-CAP.md` |
| ⚠️ Bất định thật của hai số trên | Nằm ở **cấp buổi live**, không ở KTC theo dòng: macro-F1 của bản mới đi từ **0,368** (buổi 0% ý định mua) đến **0,599** (buổi 48% ý định mua) — số 14/09 là 0,372 đến 0,635. n_session = **3** | `results.json` → dòng C2 → `per_session`; §4 của `03-NLP-NANG-CAP.md` |
| Artifact ý định đang phục vụ mặc định | **v1** (`intent_clf.joblib`, 6 lớp). v2 bật bằng `LIVELIFT_INTENT_MODEL=v2` — **chưa phải mặc định**, quy trình thăng cấp ghi ở `03-NLP-NANG-CAP.md` §11 | `src/livelift/nlp/intent.py` |
| Độ phủ KTC dưới hiệu ứng lưu | bán rã 0 giây → **100%**; 120 giây → **84%**; 180 giây → **60%** (lệch −0,3% / −20,3% / −29,8%) | docstring `run_validation` trong `src/livelift/sim/validate.py`; đo 02/09 trên SimParams đã hiệu chỉnh KuaiLive. **Con số 76% cũ là TRƯỚC hiệu chỉnh, đã bị thay** |
| Điều kiện đo MDE 20,1% | mô phỏng ~45–62 người xem đồng thời | `src/livelift/sim/simulator.py`; **phải nói kèm: theo ƯỚC TÍNH (chưa đo) 300.000đ quảng cáo chỉ kéo được 5–15 người xem đồng thời**; ở 15 người xem, MDE theo đơn hàng là 179–327% với 18 phiên (`docs/benchmarks/order-mde.md`) |
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
