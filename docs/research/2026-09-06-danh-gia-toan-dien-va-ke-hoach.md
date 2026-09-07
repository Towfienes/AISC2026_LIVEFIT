# Đánh giá toàn diện & kế hoạch nâng cấp — 06/09/2026

*Phương pháp: 13 tác tử phân tích độc lập — 6 đọc sâu từng phân hệ mã, 5 khảo sát
SOTA 2024–2026 (papers + repos), 1 tổng hợp, 1 phản biện đối kháng vai giám khảo
trưởng. ~1 triệu token phân tích, 249 lượt đọc/tìm kiếm. Mọi phát hiện có file:line.*

## I. Điểm sẵn sàng (0–10)

| Trục | Điểm | Một dòng |
|---|---|---|
| Khoa học | **8,0** | Sát frontier 2026; chưa có công bố/platform nào làm switchback 2 tầng cho ghim livestream |
| Sản phẩm | **4,5** | Demo mượt; phiên THẬT thì ingest đứt, WS gãy, shortlink domain giả (đã fix 06/09) |
| Dữ liệu/NLP | **5,5** | 0,870 chỉ trên 320 câu tự soạn; PII leak 19/27 probe đối kháng (đã vá 06/09) |
| Vận hành | **4,0** | Chưa public HTTPS, không spool, token/quota lỗi chỉ warning lặp (đã fix 06/09) |
| Hồ sơ thi | **3,5** | Thuyết minh chưa có chữ nào; rubric BTC chưa nắm; 0 phỏng vấn khách hàng; số lệch giữa tài liệu |

**Chẩn đoán một câu:** dự án hai tốc độ — lõi khoa học đủ điểm ăn giải, nhưng thắng
thua vòng 1 nằm ở hồ sơ + phiên thật + business, đúng phần đang mỏng nhất.

## II. Phát hiện chặn (đã triển khai fix 06/09 — xem git log)

1. **Ingest live không hoạt động**: ApiSink gửi `text_scrubbed`, API đòi `text` →
   mọi comment 422 rồi drop; server bỏ `ext_id`/`ts_utc` → restart tạo trùng, sai khối.
2. **WebSocket gãy hợp đồng** `{type,data}` vs `msg.tick` → realtime chết lặng;
   desk live không hiển thị dải khối BẬT/TẮT; bấm thẻ A có thể ghim sản phẩm B;
   shortlink trỏ `shop.example` → outcome chính không đo được ở phiên thật.
3. **PII filter leak 19/27 probe** (phone đa separator/fullwidth/keycap, tên viết
   thường — mặc định chat live, thành phố ngoài gazetteer, link MXH/stk) trong khi
   hard rule 95% + viện dẫn Luật 91/2025.
4. **Peeking trái tiền đăng ký**: `/experiment/summary` trả τ̂/p/CI bất kỳ lúc nào,
   mâu thuẫn prereg §7; redraw dùng tham số mặc định thay vì DesignParams đã lưu;
   `estimate_ht ≡ estimate` từng bit tại p=0,5 nhưng prereg bán như 2 ước lượng viên.
5. **Không có mặt public**: API bind 127.0.0.1, không TLS — `/r/{code}` (định nghĩa
   outcome chính) người xem không bấm được; không spool → mất mạng = mất dữ liệu.

## III. Vị trí so với SOTA (khảo sát 06/09)

**Đi trước:** không platform OSS nào (GrowthBook/Unleash/Flagsmith) hỗ trợ switchback
native; không sản phẩm AI livestream nào (TikTok Live Studio AI, Taobao LiveThinking,
Syntopia) đo uplift nhân quả có propensity — câu chuyện "first" là thật, nói to.

**Khoảng trống chính (đường nâng cấp đã có văn liệu):**
- Giảm phương sai: CUPED/CUPAC đa biến cho switchback ("CUPED on Steroids",
  arXiv:2608.24038); doubly-robust giảm ~79% phương sai (arXiv:2606.27662).
- Kiểm định: CRT gộp khối hợp lệ mẫu hữu hạn dưới carryover bậc m (Liu–Zhong,
  arXiv:2602.23257) — dùng làm sensitivity, KHÔNG đổi kiểm định chính sau khóa prereg.
- Thiết kế: rerandomization tuần tự cân bằng biến tiên lượng (SRSB, arXiv:2604.02489;
  P&G production — HBS WP 26-012) — thiết kế cho đợt thí nghiệm MỚI ở chung kết.
- Bandit inner: Mixture Adaptive Design (Liang–Bojinov, arXiv:2311.05794) — cùng dòng
  tác giả, anytime-valid CI — roadmap chung kết, không làm trước vòng 1.
- Vận hành platform: SRM check chặn-hiển-thị kiểu Eppo; tách assignment/exposure kiểu
  Statsig; báo cáo quyết định 5 trạng thái không hiện p-value mặc định.
- NLP: ViSoBERT (checkpoint `5CD-AI/visobert-14gb-corpus`) khi đủ 2–3k nhãn duyệt;
  BamiBERT 2026 làm backbone so sánh; SetFit làm cầu nối ít nhãn.

## IV. Phán quyết dữ liệu & training

- **0,870 không được quote trần**: 5-fold CV trên 320 câu tự biên soạn, cân bằng lớp
  nhân tạo, sai số ~±0,04 — chưa có số nào trên chat thật.
- **KHÔNG fine-tune transformer bây giờ**: dưới 1k nhãn, ViSoBERT ≈ TF-IDF (mốc văn
  liệu UIT: 2–3k nhãn cho macro-F1 0,80–0,88). Không thuê gán nhãn nhiều tuần.
- **Con đường nhanh nhất (văn liệu đã hợp thức hóa** — ACL 2024 NLP+CSS; ViGoEmotions
  2026; 5CD-AI re-label 120k bằng Gemini**):** nguyên liệu có sẵn 14.903 bình luận VOD
  đã lọc PII → 2 LLM gán nhãn 3–5k câu qua batch API (vài USD) → giữ phần đồng thuận
  (~85–90%) → người chỉ duyệt phần bất đồng → retrain. Pipeline code đã dựng 06/09
  (`python -m livelift.nlp.label_llm`), chạy NỀN không chặn việc khác.
- **Chung kết:** đủ 2–3k nhãn duyệt → fine-tune visobert-14gb-corpus, ONNX INT8, giữ
  TF-IDF làm ablation; công bố **dataset intent chat livestream Việt đầu tiên**
  (khảo sát xác nhận chưa tồn tại) — từ "người dùng SOTA" thành "người đóng góp SOTA".

## V. Kế hoạch đã qua phản biện đối kháng

Phản biện chính: *kế hoạch 12 việc = 25–35 ngày công cho ~8 ngày; giám khảo vòng 1
chấm qua thuyết minh + video demo, không clone repo — cắt còn 5, phần khoa học dời
sau 14/09.*

### Trước 14/09 (thứ tự ưu tiên)

1. **Hồ sơ là sản phẩm được chấm**: xác minh hạn + rubric BTC hôm nay → FACT-SHEET
   một bộ số → E6-01 + pitch deck + video demo 2–3 phút. 1 người chuyên trách, không
   kiêm code. *(khung đã dựng: `docs/competition/`)*
2. **Chuỗi fix tối thiểu để phiên thật sống** *(code — đã triển khai 06/09)*: ingest
   contract + idempotency + spool; WS envelope + dải khối live; target_url thật +
   HTTPS public qua Caddy; product_id đúng thẻ. **MODE TAY** — auto-executor,
   rehydrate, override UI dời sau 14/09.
3. **1 phiên nội bộ end-to-end + 1 phiên 10–20 khán giả thật trước 12/09** — screenshot
   + chi phí/người xem đo được vào FACT-SHEET và E6-01. Một phiên thật đánh bại mọi
   mô phỏng trong mắt giám khảo vòng 1.
4. **Bằng chứng business song song từ ngày đầu**: 5 phỏng vấn nhà bán (trích dẫn
   nguyên văn; phỏng vấn quyết định pricing) + 10 thư đối tác + 1 trang funnel
   "kịch bản" + 3 câu trả lời sẵn (`phan-bien-du-kien.md`).
5. **Gói liêm chính 1–2 ngày** *(code — đã triển khai 06/09)*: vá PII + probe vào test
   hồi quy; cờ `RESULTS_FREEZE_UNTIL` khóa kết quả trước đóng băng (trình bày như
   TÍNH NĂNG); DesignParams vào redraw; kích hoạt pipeline nhãn LLM chạy nền.

### 15/09 → khóa prereg (tuần 6)

- Trả nợ tiền đăng ký: sweep burn-in b∈{0..3} + sensitivity khối loại E_min∈{0,60,120}
  + wild cluster bootstrap (CR1 anti-conservative với 18–30 cụm) + AR CI cho LATE.
- Đổi thống kê RI sang khử-FE-phiên + trọng số exposure (miễn phí về validity dưới
  sharp null; lấy lại lực trên phiên thật dị biệt) → đo lại RANDOMIZATION_TEST_MARGIN.
- Bịt 4 lỗ sim: analyzed_mask trong validate.py; sweep khán giả thưa 0,5–6/phút;
  non-compliance cho LATE; shock cấp phiên + thang phút.
- Hiệu chỉnh tuần 3 trên kênh thật → chốt độ dài khối, khóa PREREGISTRATION bằng commit.

### Trước chung kết (11/2026)

- Counterfactual replay bằng Open Bandit Pipeline trên log propensity (demo giám khảo
  bấm được, zero rủi ro production) · Live Co-pilot PhoWhisper INT8 (trễ 2–3s, không
  phá làm mù) · ViSoBERT + công bố dataset · SRM check + trang "Báo cáo quyết định"
  5 trạng thái tiếng Việt business · video 90s cho vòng bình chọn 01/10 (làm NGAY sau
  14/09) · diễn tập phản biện gồm kịch bản null.

### KHÔNG làm (nghe hay nhưng sai thời điểm)

| Việc | Vì sao không |
|---|---|
| Contextual bandit đầy đủ trước vòng 1 | ~30 phiên → overfit, phá câu chuyện suy diễn sạch; Gamma-Poisson hiện tại đã là Thompson-style có propensity |
| Fine-tune ViSoBERT ngay | <1k nhãn → ngang TF-IDF, đốt 8 ngày quý nhất |
| Đổi thiết kế/kiểm định chính sang SRSB/CRT giữa chừng | Tự phá cơ chế tiền đăng ký — tài sản quý nhất; chỉ dùng làm sensitivity/đợt mới |
| Always-valid CI để "hợp pháp hóa" peeking | Giải sai bài — prereg cam kết KHÔNG nhìn; giải đúng là cờ khóa (đã làm); confidence sequences là tính năng chung kết |
| Pin-at-highlight đa phương thức / đua latency <1s | Hàng tuần GPU cho việc ngoài đường găng; định vị đúng là "gợi ý KÈM bằng chứng nhân quả" |

## VI. Nguồn chính (chọn lọc, đầy đủ trong khảo sát)

Bojinov–Simchi-Levi–Zhao 2023 (Mgmt Sci) · Hu–Wager arXiv:2209.00197 · Liu–Zhong
arXiv:2602.23257 · SRSB arXiv:2604.02489 · P&G HBS WP 26-012 · CUPED-on-Steroids
arXiv:2608.24038 · DR-for-switchback arXiv:2606.27662 · EB block length arXiv:2406.06768
· MAD arXiv:2311.05794 · Xie–Sharma–Mehra POM 2025 (U ngược pin) · KuaiLive SIGIR 2026
+ KuaiLive-M3 · LSEC KDD 2021 (3,06M giao dịch mua — calibrate funnel) · ViSoBERT
EMNLP 2023 + 5CD-AI/visobert-14gb-corpus · BamiBERT arXiv:2607.02259 · LLM-annotation
ACL 2024 NLP+CSS · ViGoEmotions arXiv:2602.08371 · PhoWhisper · Open Bandit Pipeline ·
gbstats (GrowthBook) · Spotify confidence · PlanOut · Eppo/Statsig engineering blogs.
