# BÁO CÁO TỔNG HỢP LIVELIFT — Hợp nhất 6 báo cáo nghiên cứu & phản biện

*Người tổng hợp: Lead Synthesizer · 24/08/2026 · Dành cho toàn đội AISC'26*

---

## 1. Đánh giá tổng quan

**Kết luận chung: nền tảng phương pháp thuộc nhóm 1% đội thi sinh viên — nhưng chưa phải "competition-winning" ở trạng thái hiện tại.** Ba lỗ hổng có thể đánh sập toàn bộ hồ sơ nếu không sửa trước 14/09: (1) biến kết quả chính (product CTR) **chưa có định nghĩa đo lường trên Facebook Live** (L5); (2) bài toán mua khán giả bị **định giá thiếu ~10 lần** (R1); (3) bảng lực thống kê **tự mâu thuẫn với quy tắc washout của chính nhóm** (L1). Cả ba đều sửa được, và lời giải cho (1) và (3) đã có sẵn trong tài liệu nghiên cứu.

**Những điểm xuất sắc phải giữ nguyên** (theo báo cáo phản biện): quy tắc hiển thị nguồn con số E2-04 (phân biệt "ước lượng dự báo" với "tác động đo được, KTC 95%"); tiền đăng ký bằng commit khóa tuần 6; nguyên tắc chốt độ dài khối theo dữ liệu pilot; holdback ngẫu nhiên trùng cơ chế định giá; phân tích ITT/LATE; demo cho giám khảo đổi tham số tại chỗ.

**Vị thế cạnh tranh đã được xác minh (báo cáo 4):** không một công cụ thương mại nào — Chanmama, Feigua, Kalodata, FastMoss, EchoTik, Bambuser, Firework, CommentSold — chạy thí nghiệm ngẫu nhiên trong-phiên hay ghi propensity; tất cả đều quan sát hồi cứu. Tiền lệ duy nhất là một nghiên cứu học thuật: *"AI Assistant in Online Shopping: A Randomized Field Experiment on a Livestream Selling Platform"*, [ISR 2025](https://pubsonline.informs.org/doi/10.1287/isre.2023.0103) — **phải trích dẫn trong related work** vì nó hợp thức hóa hướng tiếp cận. Dùng nguyên văn đoạn định vị trong báo cáo 4: LiveLift trả lời *"điều gì đã xảy ra nếu ghim khác đi?"* — một "moat phương pháp", không phải tính năng dashboard.

---

## 2. Lỗi và mâu thuẫn phải sửa

| # | Lỗi | Cách sửa |
|---|---|---|
| **L1** | **Bảng MDE mâu thuẫn với quy tắc washout.** Dòng "5+1 phút" chỉ hợp lệ nếu trung vị dwell ≤1 phút; với dwell 5–7 phút thực tế, quy tắc `khối ≥ 2×washout` ép chu kỳ ≥15 phút → MDE ≈28%, phá vỡ mục tiêu "MDE ≤20%" và "≥500 khối". | **Bỏ washout thiết-kế, thay bằng burn-in phân-tích** (Hu–Wager, mục 3) — vòng luẩn quẩn biến mất *nếu* carryover đo được ngắn. Đo t_mix ở tuần 1–2 pilot trước khi cam kết. **Lưu ý bất đồng chưa giải quyết ở mục 3.** |
| **L2** | **3.900 phút trộn dữ liệu hiệu chỉnh với dữ liệu khẳng định.** Tuần 3–5 dùng để *chọn* thiết kế thì không được đếm vào mẫu khẳng định; chuỗi chính thức chỉ còn 18 phiên (1.620 phút) + 1.200 phút đối tác **chưa ký** — mâu thuẫn với tuyên bố "hoàn thành không cần ai" (8.3). | Viết lại bảng lực thành **hai kịch bản trung thực**: "không đối tác, chỉ tuần 6–11" và "có đối tác". Chủ động đưa con số xấu ra trước. |
| **L3** | **Ngân sách hai tài liệu lệch nhau:** 17,2M (kế hoạch) vs 15,2M (mô tả); số phiên lệch 8/9, 18/21, 29/30/31. | Chốt một bộ số duy nhất (đề xuất: 17,2M; thống nhất số phiên) trước khi nộp. |
| **L4** | **Hạn nộp lệch:** 14/09 vs 15/09; khung 12 tuần vs 14 tuần. | Xác minh với BTC; hợp nhất một lịch duy nhất. |
| **L5** | **"Product CTR" chưa đo được trên Facebook Live** — không có thẻ sản phẩm gốc; bán qua bình luận chốt đơn. Biến chính không tồn tại nếu không trả lời. | Định nghĩa vận hành từng nền tảng: **link rút gọn có UTM ghim trong bình luận, đo click qua redirect tự host**. Viết thành mục riêng trong hồ sơ. |
| **L6** | **Host không bị làm mù; E2-08 chủ động phá mù** (hiện thời gian còn lại của khối → host suy ra BẬT/TẮT → nhiễu "hệ thống + tâm lý host"). | Bỏ hiển thị ranh giới khối khỏi màn hình host; host chỉ thấy sản phẩm đang ghim. Ghi vào tiền đăng ký như biện pháp chống nhiễu — biến điểm yếu thành điểm cộng. Liên quan: **làm mù cả operator trong khối OFF** (báo cáo 1). |
| **L7** | **"Đồng ý" pháp lý bị đánh tráo bằng "thông báo"** — mâu thuẫn với chính trích dẫn Nghị định "cấm mặc định đồng ý" (Luật 91/2025). | Thay bằng lập luận **khử nhận dạng tại ingest + lợi ích chính đáng**, không tự nhận có consent. Thừa nhận rủi ro ToS của TikTokLive trong một câu thay vì gộp vào "nguồn hợp lệ". |
| **L8** | **ICC đo sai cấp cụm** — "tương quan khối liền kề" là tự tương quan, không phải ICC theo phiên. Cụm thật là *phiên* (~30), không phải 650 khối; design effect 1+(m−1)ρ có thể nuốt phần lớn lực thống kê. | Đo ICC cấp phiên; đưa design effect cụm-phiên vào bảng MDE; hoán vị randomization test theo đúng sơ đồ phân-tầng-trong-phiên. |
| **R1** | **80 người xem đồng thời với 300k/phiên thiếu 5–10 lần** (CPM VN 25–60k → chỉ ~5–15 đồng thời từ ads); dự phòng 500k không lấp nổi khoảng cách 10× và vượt quỹ. | Chạy thử 2–3 phiên đo chi phí thật/lượt vào; hạ ngưỡng tiên quyết (40–50 đồng thời) hoặc tuyên bố đối tác dữ liệu là đường sống chính. |
| **R2–R5** | SP quá tải (không ai đóng gói/giao ≥8 đơn/phiên); TN là single point of failure; "giai đoạn ít thay đổi mã" mâu thuẫn với lịch tích hợp tuần 8–10; giá vốn ~19k/đơn khiến GMV thành nhiễu. | Phân công đóng gói–giao hàng; NC học backup notebook E3; đóng băng assigner/ingest tuần 6 bằng nhánh riêng + kiểm thử hồi quy; xem lại danh mục hàng. |

---

## 3. Nâng cấp phương pháp từ nghiên cứu

### 3.1 Thiết kế switchback (báo cáo 1)

1. **Chuẩn hóa khối ~5 phút, khối đầu/cuối phiên nhân đôi thành ~10 phút** (quy tắc 2m của [Bojinov, Simchi-Levi & Zhao, *Management Science* 69(7), 2023](https://pubsonline.informs.org/doi/10.1287/mnsc.2022.4583) / [arXiv:2009.00148](https://arxiv.org/abs/2009.00148)). Bỏ dải 5–15 phút tùy ý — số lần ngẫu nhiên hóa, không phải số phút, mới là đơn vị lực thống kê. Nếu giữ nhiều độ dài, phải ngẫu nhiên hóa cả độ dài theo lịch tiền đăng ký.
2. **Bỏ washout thiết-kế → burn-in phân-tích** ([Hu & Wager, *JBES*, arXiv:2209.00197](https://arxiv.org/abs/2209.00197)): ghi log tất cả, ước lượng bỏ 1–2 phút đầu mỗi khối, sensitivity analysis trên b ∈ {0,1,2,3} phút. Không mất phút thí nghiệm nào; quyết định không-thể-hoàn-tác thành quyết định audit được. **Đây là lời giải trực tiếp cho L1.**
3. **Giữ i.i.d. Bernoulli(0.5) mỗi khối + rerandomization**: vẽ lại chuỗi đến khi mỗi 1/3 phiên có ≥2 khối mỗi nhánh ([Ni, Kalfountzou & Bojinov, HBS WP 26-012, 2025](https://www.hbs.edu/ris/Publication%20Files/26-012_e60b131f-aa68-4422-97e8-a478d6ed4baa.pdf)); jitter ranh giới ±30–60s để không đồng bộ với kịch bản show ([Xiong, Chin & Taylor, arXiv:2406.06768](https://arxiv.org/abs/2406.06768)).
4. **Tuần 1–2 pilot: đo t_mix** (impulse response CTR sau khi bỏ ghim) — mọi công thức thiết kế tối ưu phụ thuộc con số này.

**⚠️ BẤT ĐỒNG PHẢI GIẢI QUYẾT BẰNG DỮ LIỆU PILOT:** Báo cáo 1 (dựa [Wen et al., arXiv:2403.17285](https://arxiv.org/abs/2403.17285)) lập luận CTR livestream tự tương quan dương mạnh + carryover ngắn → **khối 5 phút ngắn nhất là tối ưu**. Báo cáo 2 (mục hiệu chỉnh #3) lưu ý **khối 15 phút giảm tự tương quan dư** sau FE; báo cáo 5 (L1) chỉ ra dwell 5–7 phút gợi ý carryover có thể *dài*, ép khối dài. Nếu t_mix đo được >3 phút, khuyến nghị "5 phút + burn-in" của báo cáo 1 yếu đi đáng kể (Wen et al.: carryover mạnh → switch hiếm). **Không chốt độ dài khối trước khi có số đo tuần 1–2; tiền đăng ký quy trình chọn, không chọn trước kết quả.**

### 3.2 Ước lượng & suy diễn (báo cáo 2, có đối chiếu báo cáo 1)

- **Đơn vị phân tích = khối; cụm = phiên.** Không bao giờ phân tích cấp click ([DoorDash: cluster-robust SEs](https://careersatdoordash.com/blog/cluster-robust-standard-error-in-switchback-experiments/)). 30 phiên mới là cỡ mẫu ràng buộc, không phải 650 khối — sốc cấp phiên (host, traffic, thuật toán) chi phối ([Pankratev, arXiv:2606.03012](https://arxiv.org/html/2606.03012)).
- **⚠️ BẤT ĐỒNG về ước lượng chính:** Báo cáo 1 đề xuất **Horvitz–Thompson** design-based với burn-in làm primary (thống nhất với propensity log tầng trong), OLS làm secondary. Báo cáo 2 đề xuất **OLS FE-phiên + hiệp biến kiểu Lin (2013)** làm primary. Đề xuất dung hòa: pre-register **cả hai**, HT là primary về mặt học thuật (ít giả định nhất), OLS-CUPAC là primary về lực thống kê; kiểm định chính là **randomization inference studentized** — cả hai báo cáo đồng ý điểm này.
- **Randomization inference đúng chuẩn:** vẽ lại phân bổ bằng chính hàm assignment production (không "xáo outcome"), trong-phiên đúng sơ đồ phân tầng, thống kê studentized, 2.000–10.000 draws ([Bojinov & Shephard, *JASA* 2019](https://arxiv.org/abs/1706.07840); [arXiv:1702.04851](https://arxiv.org/pdf/1702.04851)). Với 30 cụm: **wild cluster bootstrap** (`wildboottest`, 9.999 reps).
- **IV/LATE:** 2SLS với Z làm instrument cho "sản phẩm đề xuất thực sự được ghim ≥x% khối"; báo cáo first-stage F + **Anderson–Rubin CI** ([Londschien, arXiv:2508.12474](https://arxiv.org/pdf/2508.12474); `ivmodels`). **Phải thêm ngay vào schema log: cờ compliance/override cấp khối** — thiếu là IV bất khả thi.
- **Giảm phương sai: CUPAC, không DML-DR.** DR/DML suy thoái dưới ~50 cụm; CUPAC (GBM dự đoán CTR khối từ đặc trưng tiền-khối, train trên dữ liệu OFF/tiền-thí-nghiệm, cross-fit theo phiên) ổn định và cho SE ratio ~0.50 ở R²≈0.5 ([arXiv:2606.27662](https://arxiv.org/html/2606.27662v1); [DoorDash CUPAC](https://opendatascience.com/improving-experimental-power-through-cupac/)). Kỳ vọng thực tế: giảm 20–40% phương sai. **Cảnh báo:** dưới carryover mạnh, ước lượng giảm-phương-sai "tự tin sai" (38% bác bỏ sai dấu) — chạy chẩn đoán carryover (hồi quy lag-augmented, plot τ theo burn-in) **trước** khi tin CI của CUPAC.
- **Công thức MDE ≈ 4·CV/√n đúng làm base case** ([J-PAL](https://www.povertyactionlab.org/resource/power-calculations)) nhưng phải nhân hiệu chỉnh: **÷ tỷ lệ compliance** (60% → ×1,67 — lớn nhất), ×√deff (FE-phiên trung hòa phần lớn nếu dùng CV *trong-phiên*), ×√((1+ρ_r)/(1−ρ_r)) cho tự tương quan dư, ~10% mất n do burn-in, ÷√(1−R²_CUPAC). CUPAC có thể triệt tiêu gần đúng phạt compliance.
- **Xây dựng outcome:** CTR khối = click/impression *quy về pin của khối đó*, có trọng số impression (không trung bình thô tỷ lệ từng khối); quy tắc impression tối thiểu tiền đăng ký.
- **Stack Python:** `statsmodels` (cluster + HAC sensitivity), `linearmodels.IV2SLS`, `wildboottest`, `ivmodels`, `lightgbm`; randomization inference tự viết ~30 dòng numpy (không dùng `scipy.stats.permutation_test` — không biểu diễn được thiết kế phân tầng).

### 3.3 NLP tiếng Việt (báo cáo 3)

- **Intent: ViSoBERT thay PhoBERT** ([EMNLP 2023](https://arxiv.org/abs/2310.11166)) — pre-train đúng trên bình luận FB/TikTok/YouTube tiếng Việt (teencode, mất dấu), thắng PhoBERT mọi benchmark social, **và không cần tách từ** → bỏ Java/VnCoreNLP khỏi đường realtime. Nếu vẫn dùng PhoBERT: bắt buộc RDRSegmenter ([PhoBERT, EMNLP-Findings 2020](https://aclanthology.org/2020.findings-emnlp.92.pdf)).
- **Serving CPU: ONNX INT8**, không có DistilPhoBERT chính thức; kỳ vọng ~10–30ms/comment, benchmark FP32 vs INT8 trên server thật (INT8 có thể chậm hơn trên CPU không-VNNI, [onnxruntime #12854](https://github.com/microsoft/onnxruntime/issues/12854)). Bỏ multilingual mini (chỉ 62–66% trên SMTCE).
- **PII: rules-first, NER phụ trợ.** Regex SĐT chuẩn hóa E.164 với hardening chống lách (tách dấu chấm/cách, "không/một/hai", "o→0") — mục tiêu recall ≥0.98 đo được trên log Live Lab. Gazetteer địa chỉ từ [`vietnamadminunits`](https://github.com/tranngocminhhieu/vietnamadminunits) — **bắt buộc nạp cả 63 tỉnh cũ lẫn 34 tỉnh mới** (sáp nhập 01/07/2025, bỏ cấp quận/huyện — người xem vẫn gõ "quận 7" nhiều năm nữa; [2025 admin reforms](https://en.wikipedia.org/wiki/2025_Vietnamese_administrative_reforms)); cờ PII = tên đơn vị + cue đường phố ("số", "đường", "ngõ"…). Tên người: underthesea NER + heuristic kính ngữ ("chị Lan"), recall ~0.7, khai báo trung thực. **Mask, không xóa:** `[SĐT]`, `[ĐỊA CHỈ]`, `[TÊN]`.
- **Dữ liệu train:** không tồn tại dataset purchase-intent livestream tiếng Việt công khai. Pre-finetune trên [UIT-ViOCD](https://arxiv.org/pdf/2104.11969) + UIT-ViSFD; **tự nhãn 2–3k bình luận Live Lab** (2 annotator + adjudication, báo cáo κ — ViOCD đạt 0.87). Teencode: từ điển ~300 mục + underthesea `text_normalize`; **không** đưa seq2seq normalizer vào realtime (ViLexNorm best chỉ 57.74% ERR, [EACL 2024](https://aclanthology.org/2024.eacl-long.85/)).
- **Ship keyword baseline trước** ("chốt", "bn tiền", "sz M"…): radar ngày-một, nguồn weak-label, baseline ablation (~0.55–0.65 macro-F1 vs ~0.85 transformer), graceful degradation. Mục tiêu cam kết: intent macro-F1 0.80–0.88; latency <50ms/comment CPU.

---

## 4. Thực tế API/nền tảng 2026 (đã xác minh)

- **YouTube: dùng `liveChatMessages.streamList`** (push, khuyến nghị chính thức từ 07/2025), không polling `list` — polling 5s/90 phút ≈ 5.400 units, **quá nửa quota 10.000 units/ngày** cho một phiên ([docs](https://developers.google.com/youtube/v3/live/docs/liveChatMessages/streamList); [quota](https://developers.google.com/youtube/v3/determine_quota_cost)). Auto-reconnect bằng `pageToken`; fallback `list` tôn trọng `pollingIntervalMillis`; lấy `activeLiveChatId` qua `liveBroadcasts.list`, **không** dùng `search.list` (cap 100 call/ngày). Timestamp server-side mọi message để attribution khối không phụ thuộc latency.
- **Facebook: SSE stream đã chết — thiết kế polling** `/{live-video-id}/comments?order=reverse_chronological` với `since` cursor; **tắt `live_filter`** (mặc định lọc "low quality" — mất dữ liệu intent). Quyền đọc bình luận người xem cần `pages_read_user_content` (gotcha kinh điển). **Điểm mấu chốt cho L4/R2 (hai báo cáo độc lập cùng xác nhận):** app ở **Development Mode đọc được Page của chính nhóm không cần App Review** → Live Lab chạy được ngay hôm nay; App Review chỉ chặn tích hợp Page đối tác (tuần 8). Nếu cần Advanced Access: Business Verification trước (có thể treo 10+ ngày), timeline thực tế 2–7 ngày sạch đến ~20 ngày, mỗi lần reject reset đồng hồ — **budget 4–6 tuần, nộp trong tháng 9** ([Meta Live Video API](https://developers.facebook.com/docs/live-video-api/); [bundle.social 2026](https://bundle.social/blog/meta-app-review-20-days)).
- **TikTok: [TikTokLive](https://github.com/isaackogan/TikTokLive) còn sống (v6.x, 07/2026)** nhưng là reverse-engineering, phụ thuộc sign server Euler Stream, TikTok phá được bất kỳ lúc nào; không có API chính thức đọc bình luận live ([TikTok Shop docs](https://partner.tiktokshop.com/docv2/page/developer)). **Chiến lược phân tầng rủi ro:** thí nghiệm instrumented trên **YouTube + Facebook**; TikTok adapter "best-effort" sau cùng interface sự kiện, fallback ghi tay (tablet operator) — adapter chết chỉ mất intent bình luận, không mất switchback. **Không gắn automation vào tài khoản shop/creator.** Khai báo tầng rủi ro này trong hồ sơ — giám khảo thưởng cho realism. (Nhất quán với L7: thừa nhận rủi ro ToS.)

---

## 5. Dataset & mô phỏng

**Đã xác minh (báo cáo 6):**
- **KuaiLive — TẢI NGAY** (858,2 MB, [Zenodo 16565801](https://zenodo.org/records/16565801), không cần đăng ký; SIGIR 2026, [arXiv:2508.05633](https://arxiv.org/abs/2508.05633)): 23.772 users, 11,6M live rooms, 5,36M tương tác/21 ngày, **có impression không-click → tính được CTR cấp room** — đúng hình dạng outcome của LiveLift. Dùng: (1) calibration target cho simulator (CTR room, dwell, cường độ arrival, tỷ lệ comment/click); (2) offline replay cho estimator; (3) chỉ dùng rates/timing, không dùng text (tiếng Trung). **Lưu ý license:** trang dự án ghi CC BY-NC-SA 4.0, Zenodo ghi CC BY 4.0 — **coi là NC** (ổn cho thi, không ship vào bản thương mại).
- **LiveRec/Twitch** ([repo](https://github.com/JRappaz/liverec)): nguồn công khai tốt nhất về arrival/departure/dwell theo kênh live → calibrate cường độ đến và survival curve.
- **KuaiRec** ([kuairec.com](https://kuairec.com/)): ma trận sở thích ~100% density → ground-truth preference trong simulator. **KuaiRand** ([arXiv:2208.08696](https://arxiv.org/pdf/2208.08696)): sanity-check IPS/DR với propensity đều đã biết. **Taobao UserBehavior** ([Tianchi 649](https://tianchi.aliyun.com/dataset/649?lang=en-us)): base rate funnel, Zipf sản phẩm.
- **BỎ: LSEC** (không timestamp tài liệu hóa, không license — vô dụng cho validation theo khối thời gian) và **KuaiLive-M3** (hàng trăm GB phức tạp không cần cho CTR khối).

**Simulator (~500 dòng Python, clock 1 giây, phiên 90 phút)** — nguyên tắc "calibrated simulation" ([Credence, ICML 2022](https://proceedings.mlr.press/v162/parikh22a.html)); **tái dùng [Open Bandit Pipeline](https://github.com/st-tech/zr-obp) cho IPS/DR/SNIPS tầng trong thay vì tự viết**:
1. **Arrival:** Poisson phi thuần nhất (shape từ LiveRec, scale từ pilot) + **Hawkes self-excitation** khi đổi pin/flash deal ([arXiv:1602.06033](https://arxiv.org/pdf/1602.06033)).
2. **Departure:** hazard mũ theo "boredom" phản ứng với affinity pin — kênh interference thực tế.
3. **Click:** σ(α + u·pⱼ + β_pin + s(t)), u từ cụm KuaiRec, α calibrate theo CTR KuaiLive + pilot.
4. **Ground truth:** mô phỏng cả hai nhánh counterfactual bằng **common random numbers** → hiệu ứng thật từng-khối chính xác, test được cả CATE.
5. **Carryover 3 cơ chế có núm vặn:** audience persistence (geometric φ_a), demand cannibalization (κ, m phút), hype decay xuyên ranh giới khối; sweep từ 0 lên, kiểm chứng kết quả Bojinov et al. rằng đặt p hơi cao là an toàn.
6. **Giao thức validation:** 1.000 phiên A/A → false-positive rate ≈ α cho *mọi* estimator; power curve trên δ × độ dài khối {5,10,15} × carryover on/off ở n=650 → **chính đây là nơi quyết định bất đồng độ-dài-khối ở mục 3.1** và cho ra MDE báo cáo cuối. Replay tầng trong qua OBP-DR trước khi Live Lab bắt đầu.

**Simulator study phải là một mục headline của bài nộp** — nó biến "chúng tôi mở một shop" thành "estimator của chúng tôi được chứng minh đã hiệu chỉnh".

---

## 6. Danh sách hành động ưu tiên

**P0 — trước 14/09:**
1. Định nghĩa vận hành "click sản phẩm" từng nền tảng (UTM + redirect tự host), viết thành mục riêng — **Backend + Trưởng phân tích**.
2. Hợp nhất hai tài liệu: một ngân sách (17,2M), một số phiên, một hạn nộp (xác minh BTC 14/15-09), một khung tuần — **PM/hồ sơ**.
3. Viết lại bảng MDE hai kịch bản (không/có đối tác) với đầy đủ hiệu chỉnh compliance, deff cụm-phiên, burn-in, CUPAC — **Trưởng phân tích (TN)**.
4. Bật Live Lab ngay ở Facebook Development Mode (không đợi App Review); nộp App Review song song với app demo + screencast — **Backend + PM**.
5. Thêm vào schema log: cờ compliance/override, propensity, "giây kể từ lần switch cuối", timestamp server-side — **Backend**.
6. Tải KuaiLive + LiveRec, dựng khung simulator, chạy pilot toán quảng cáo 2–3 phiên đo chi phí thật/lượt vào — **Trưởng phân tích + Vận hành (SP)**.

**P1 — trước tuần 6 (khóa tiền đăng ký):**
7. Đo t_mix/carryover tuần 1–2 → chốt độ dài khối + burn-in qua power curve simulator (giải quyết bất đồng 5 vs 15 phút bằng dữ liệu) — **TN**.
8. Tiền đăng ký: thiết kế Bojinov 2m + rerandomization + jitter; HT & OLS-CUPAC; randomization test studentized phân-tầng; sensitivity b ∈ {0..3} — **TN**.
9. Làm mù host (sửa E2-08) + làm mù operator khối OFF, ghi vào tiền đăng ký — **Frontend + Vận hành**.
10. Sửa mục pháp lý: khử nhận dạng tại nguồn thay "consent = thông báo"; một câu thừa nhận ToS TikTokLive — **PM/pháp lý**.
11. Đo ICC cấp phiên từ pilot, cập nhật deff — **TN**.
12. Ship keyword baseline intent + regex SĐT + gazetteer 2 thế hệ tỉnh; fine-tune ViSoBERT khi đủ 2–3k nhãn; benchmark ONNX INT8 trên VPS thật — **NLP lead**.
13. YouTube adapter chuyển sang `streamList`; Facebook polling tắt `live_filter`; TikTok xuống tầng best-effort + fallback tay — **Backend**.

**P2 — trước chung kết:**
14. Phân công đóng gói–giao hàng; NC học backup notebook E3-06/07 cho TN — **Vận hành + NC**.
15. Đóng băng assigner/ingest tuần 6 (nhánh riêng, regression test); tính năng mới merge sau kiểm thử — **Backend**.
16. Chạy A/A 1.000 phiên + power study đầy đủ; đưa simulator study thành mục headline bài nộp — **TN**.
17. Slide "giới hạn tự khai": MDE thật, blinding không hoàn hảo, một can thiệp, một cửa hàng; trích ISR 2025 vào related work + đoạn định vị cạnh tranh mục 1 — **PM/hồ sơ**.

**Ba việc quyết định thắng thua: L5 (đo được click), R1 (toán khán giả), L1→burn-in (bảng lực tự nhất quán). Sửa xong trước 14/09 thì hồ sơ gần như không còn điểm chết.**