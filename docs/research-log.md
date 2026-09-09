# Sổ nghiên cứu (research log)

*Theo HARNESS §4: phương pháp không được vào code từ trí nhớ. Mỗi mục: nguồn, tóm tắt
5 dòng, điều đã dùng, điều bác bỏ + lý do, ngày quyết định. Bản tổng hợp toàn bộ 6 báo
cáo: `docs/research/2026-08-24-bao-cao-tong-hop-nghien-cuu.md`.*

---

## 2026-08-24 — Báo cáo 1: Thiết kế switchback

**Nguồn:** `docs/research/2026-08-24-switchback-design.md` (Bojinov, Simchi-Levi & Zhao,
*Mgmt Sci* 2023; Hu & Wager, *JBES* 2022; Xiong, Chin & Taylor 2024; Wen et al. 2024;
Ni, Kalfountzou & Bojinov, HBS WP 26-012, 2025; Pankratev 2026).

**Tóm tắt:** Đơn vị lực thống kê là số lần ngẫu nhiên hóa, không phải số phút. Thiết kế
minimax-tối ưu: khối dài m (m = carryover), khối đầu/cuối nhân đôi 2m thay vì vứt bỏ.
Washout thiết-kế bị thay thế hoàn toàn bởi burn-in ở tầng phân tích (bỏ b phút đầu khối
trong ước lượng — không mất phút thí nghiệm nào, b audit được hậu nghiệm). Bernoulli(0.5)
i.i.d. mỗi khối + rerandomization giữ cân bằng; jitter ranh giới ±30–60s chống đồng bộ kịch bản.

**Đã dùng:** `DesignParams(washout_min=0, endpoint_double=True, jitter_s=30,
min_per_arm_per_phase=2)` trong `livelift.core.assigner`; burn-in `burn_in_s=60` trong
`block_frame`; PREREGISTRATION.md mục 2–3; runbook T−1h.

**Bác bỏ:** chốt cứng khối 5 phút ngay bây giờ — vì báo cáo 2 và 5 chỉ ra carryover có
thể dài (dwell 5–7 phút); tiền đăng ký QUY TRÌNH chọn X từ t_mix tuần 3, không chọn trước
kết quả. Cũng bác bỏ dải khối 5–15 phút tùy ý (mất tính so sánh, phải ngẫu nhiên hóa độ
dài nếu giữ).

**Quyết định (2026-08-24):** áp dụng 2m + burn-in + rerandomization + jitter; độ dài khối
để mở đến hết hiệu chỉnh tuần 3–4.

---

## 2026-08-24 — Báo cáo 2: Ước lượng & suy diễn mẫu nhỏ

**Nguồn:** `docs/research/2026-08-24-estimators.md` (Bojinov & Shephard, *JASA* 2019;
Lin, *AoAS* 2013; DoorDash Eng; arXiv:2606.27662; Londschien 2025; Pankratev 2026).

**Tóm tắt:** Đơn vị phân tích = khối, cụm = phiên (~30 phiên là cỡ mẫu thật, không phải
650 khối). Randomization inference phải vẽ lại phân bổ bằng chính hàm gán production
(không xáo outcome), thống kê studentized, CI bằng nghịch đảo kiểm định. OLS FE-phiên +
hiệp biến Lin (2013) demeaned-interacted giảm phương sai không hại tiệm cận; ~30 cụm →
wild cluster bootstrap. IV/LATE cần cờ compliance/override cấp khối trong schema từ đầu.
CUPED/CUPAC "tự tin sai" dưới carryover mạnh — phải chẩn đoán trước khi tin CI.

**Đã dùng:** `analyze_outer` (randomization test studentized + Fisher CI + HT),
`ols_fe_lin`, `late_wald`, `cuped_adjust`; cột `compliance_rate`, `override_count`,
`seconds_since_last_switch` trong schema; PREREGISTRATION.md mục 5; hiệu chỉnh MDE đầy đủ
(compliance, deff cụm-phiên, burn-in) trong `analysis/power.py`.

**Bác bỏ:** DML/doubly-robust làm ước lượng chính — suy thoái dưới ~50 cụm;
`scipy.stats.permutation_test` — không biểu diễn được sơ đồ phân-tầng-trong-phiên;
phân tích cấp click — thổi phồng false positive.

**Quyết định (2026-08-24):** primary = randomization test studentized với Fisher CI;
HT báo cáo cạnh; OLS-FE+Lin là secondary giảm phương sai; LATE cho suggest-mode/đối tác.

---

## 2026-08-24 — Báo cáo 3: NLP tiếng Việt (intent + PII)

**Nguồn:** `docs/research/2026-08-24-vietnamese-nlp.md` (ViSoBERT, EMNLP 2023; PhoBERT,
EMNLP-Findings 2020; UIT-ViOCD; ViLexNorm, EACL 2024; `vietnamadminunits`).

**Tóm tắt:** ViSoBERT thắng PhoBERT trên mọi benchmark social tiếng Việt và không cần
tách từ → bỏ Java/VnCoreNLP khỏi đường realtime. Serving CPU bằng ONNX INT8 (~10–30ms,
phải benchmark trên máy thật vì INT8 có thể chậm hơn trên CPU không-VNNI). PII:
rules-first — regex SĐT chuẩn hóa E.164 chống lách (tách chấm/cách, chữ số bằng chữ,
o→0), gazetteer địa chỉ nạp CẢ 63 tỉnh cũ lẫn 34 tỉnh mới (sáp nhập 07/2025); NER tên
người chỉ phụ trợ, recall ~0.7 khai báo trung thực. Mask chứ không xóa. Không có dataset
intent livestream tiếng Việt công khai → tự nhãn 2–3k bình luận, keyword baseline ship trước.

**Đã dùng:** kiến trúc rules-first trong `livelift.ingest.pii` (patterns + admin_units
hai thế hệ tỉnh, mask `[SĐT]`/`[ĐỊA CHỈ]`/...); kế hoạch keyword baseline trước
transformer; mục tiêu recall ≥95% từng loại làm quality gate CI.

**Bác bỏ:** DistilPhoBERT (không có bản chính thức, bản cộng đồng bỏ hoang); multilingual
mini (62–66% trên SMTCE); seq2seq normalize teencode trong realtime (ViLexNorm ERR chỉ
57.74%); PhoBERT-không-tách-từ (mất vài điểm F1 âm thầm).

**Quyết định (2026-08-24):** PII regex+gazetteer vào lõi ngay; ViSoBERT fine-tune khi đủ
nhãn; mọi bước NLP nặng nằm ngoài đường ghi dữ liệu thí nghiệm.

---

## 2026-08-24 — Báo cáo 4: API nền tảng & cạnh tranh

**Nguồn:** `docs/research/2026-08-24-apis-competition.md` (YouTube Live Streaming API docs;
Meta Live Video API; TikTokLive v6.x; khảo sát Chanmama/Feigua/Kalodata/FastMoss/EchoTik/
Bambuser/Firework/CommentSold; ISR 2025 field experiment).

**Tóm tắt:** YouTube: dùng `liveChatMessages.streamList` (push) — polling 5s/90' đốt quá
nửa quota 10k units/ngày; lấy `activeLiveChatId` qua `liveBroadcasts.list`, cấm
`search.list`. Facebook: SSE chết → polling `reverse_chronological` với `since`, TẮT
`live_filter`; app Development Mode đọc Page của mình KHÔNG cần App Review — Live Lab chạy
ngay; App Review chỉ cho Page đối tác (budget 4–6 tuần, nộp tháng 9). TikTok: TikTokLive
là reverse-engineering, best-effort, fallback ghi tay. Không đối thủ thương mại nào chạy
thí nghiệm ngẫu nhiên trong-phiên — tiền lệ duy nhất là ISR 2025 (phải cite ở related work).

**Đã dùng:** kiến trúc adapter YouTube streamList + fallback list; polling Facebook;
timestamp server-side mọi sự kiện; phân tầng rủi ro TikTok; cập nhật bảng kiểm tuần 1
(Development Mode trước, App Review song song); đoạn định vị cạnh tranh cho hồ sơ.

**Bác bỏ:** chờ App Review mới chạy Live Lab (sai — Development Mode đủ); polling YouTube
`list` làm đường chính (đốt quota); gắn automation vào tài khoản shop/creator TikTok
(rủi ro khóa tài khoản).

**Quyết định (2026-08-24):** thí nghiệm instrumented chỉ trên YouTube + Facebook; TikTok
xuống tầng best-effort; nộp App Review trong tháng 9 song song với Live Lab.

---

## 2026-08-24 — Báo cáo 5: Phản biện tài liệu dự án

**Nguồn:** `docs/research/2026-08-24-phan-bien-tai-lieu.md` (rà soát chéo kế hoạch +
mô tả dự án).

**Tóm tắt:** 8 lỗi/mâu thuẫn (L1–L8) + 5 rủi ro vận hành (R1–R5). Nặng nhất: L1 bảng MDE
mâu thuẫn quy tắc washout của chính nhóm (khối ≥2×washout với dwell 5–7' → MDE ≈28%);
L5 biến kết quả chính chưa có định nghĩa đo trên Facebook Live; L6 host không bị làm mù
và E2-08 chủ động phá mù; L8 ICC đo sai cấp cụm (cụm thật = phiên); L2 trộn dữ liệu hiệu
chỉnh vào mẫu khẳng định; R1 bài toán mua khán giả định giá thiếu ~10 lần. Đồng thời chỉ
ra các điểm xuất sắc phải giữ: E2-04, tiền đăng ký commit, ITT/LATE, thứ tự cắt phạm vi.

**Đã dùng:** toàn bộ L1/L5/L6/L8/L2 thành thay đổi cụ thể — washout=0 + burn-in; click =
redirect `/r/{code}` tự host; giao thức làm mù trong runbook + route `/host` tối giản +
quy tắc 3 lý do override; cụm = phiên trong mọi ước lượng; bảng lực hai kịch bản trong
PREREGISTRATION.md; pilot đo chi phí khán giả 2–3 phiên.

**Bác bỏ:** không bác bỏ mục nào của báo cáo — riêng đề xuất "làm mù operator hoàn toàn"
chỉ áp dụng được một phần (operator phải ghim shortlink) → hạ thành giao thức hành vi
(không đọc to, không xem trước lịch) và ghi nhận trung thực là "blinding không hoàn hảo"
trong slide giới hạn.

**Quyết định (2026-08-24):** cả ba việc thắng-thua (L5, R1, L1) vào danh sách P0 trước 14/09.

---

## 2026-08-24 — Báo cáo 6: Dataset & mô phỏng

**Nguồn:** `docs/research/2026-08-24-datasets-simulation.md` (KuaiLive, SIGIR 2026 /
Zenodo 16565801; LiveRec/Twitch, RecSys 2021; KuaiRec; KuaiRand; Taobao UserBehavior;
Credence, ICML 2022; Open Bandit Pipeline).

**Tóm tắt:** KuaiLive (858MB, tải tự do) có impression không-click → CTR cấp room đúng
hình dạng outcome của LiveLift; dùng làm calibration target + offline replay (chỉ
rates/timing, không text; coi license là NC). LiveRec calibrate arrival/dwell; KuaiRec
làm ground-truth preference; KuaiRand sanity-check IPS/DR. Simulator ~500 dòng: arrival
Poisson phi thuần nhất + Hawkes, departure hazard "boredom", click logistic, counterfactual
bằng common random numbers, 3 núm carryover; giao thức validation: 1.000 phiên A/A
(FPR ≈ α) + power curve δ × độ dài khối × carryover — nơi quyết định bất đồng 5-vs-15 phút.

**Đã dùng:** khung `livelift.sim.simulator` (SimParams có `carryover_halflife_s`,
treatment_effect biết trước); kế hoạch A/A + power curve làm gate `pytest -m slow`;
KuaiLive/LiveRec vào bảng kiểm tuần 1; simulator study làm mục headline hồ sơ.

**Bác bỏ:** LSEC (không timestamp tài liệu hóa, không license — vô dụng cho validation
theo khối thời gian); KuaiLive-M3 (hàng trăm GB đa phương thức không cần cho CTR khối);
tự viết IPS/DR tầng trong (dùng Open Bandit Pipeline).

**Quyết định (2026-08-24):** tải KuaiLive + LiveRec tuần 1; thẩm định mọi ước lượng viên
trên mô phỏng có tác động biết trước trước khi chạm dữ liệu thật (HARNESS gate E3-06/07).

## 2026-08-26 — S-O-R Model of Impulsive Purchase in TikTok Livestream Commerce (IMCOM 2026)

- **Nguồn:** Nguyễn T.H. Nhung et al., IMCOM 2026, doi:10.1109/IMCOM69009.2026.11360852.
  Khảo sát 212 người tiêu dùng Gen Z TP.HCM (mẫu thuận tiện), PLS-SEM theo khung
  Stimulus-Organism-Response: âm thanh + hình ảnh + ảnh hưởng xã hội → hưng phấn
  (arousal, biến trung gian) → mua hàng bốc đồng.
- **Dùng được:** (1) related work — bằng chứng Việt Nam/Gen Z rằng kích thích cảm quan-xã hội
  trong phiên live thúc đẩy mua bốc đồng qua kênh cảm xúc → củng cố luận điểm "thời điểm
  can thiệp trong phiên quan trọng"; (2) proxy hưng phấn từ log hành vi (nhịp thả tim,
  nhịp bình luận) làm hiệp biến tiền-khối (CUPED/CUPAC) và biến điều tiết cho phân tích
  tác động không đồng nhất (khám phá, ghi vào phụ lục tiền đăng ký).
- **KHÔNG dùng được:** hệ số đường dẫn PLS-SEM không nhập được vào mô hình LiveLift
  (đo self-report cắt ngang, tương quan, khác tầng khái niệm); không phải bằng chứng
  nhân quả — LiveLift chính là phần bù thực nghiệm cho dòng nghiên cứu khảo sát này,
  và nên trình bày đúng như vậy trong hồ sơ.
- **Đã áp dụng:** thêm `pre_like_rate` (nhịp thả tim/phút cửa sổ tiền-khối) vào
  BlockRecord làm hiệp biến — commit cùng ngày.

## 2026-09-06 — LLM-as-annotator: đồng thuận 2 model + người duyệt bất đồng (gói F)

- **Nguồn:** ACL 2024 Workshop NLP+CSS (LLM annotation cho dữ liệu xã hội — hai LLM
  gán độc lập, giữ nhãn đồng thuận, người duyệt xử lý bất đồng); ViGoEmotions (2026,
  áp dụng quy trình này cho văn bản mạng xã hội tiếng Việt).
- **Dùng được:** quy trình 2-model-consensus giảm chi phí gán nhãn nhiều lần so với
  gán tay toàn bộ mà chất lượng gần chuyên gia; bất đồng giữa 2 model khác họ là bộ
  lọc tự nhiên cho "câu khó" cần người duyệt; kết hợp uncertain-first (active learning
  theo `intent_confidence`) để mỗi nhãn mua được nhiều thông tin nhất.
- **KHÔNG dùng được:** nhãn LLM không thay được người duyệt ở lớp mở `khac` và các
  câu mỉa mai/đa ý định — vì vậy consensus không tự động thành ground truth: trường
  `source` (`llm-consensus`/`human`) đi theo từng mẫu train để benchmark truy được
  nguồn gốc.
- **Quyết định (2026-09-06):** hiện thực `livelift.nlp.label_llm` (export/merge/finalize,
  không gọi API từ code); đủ 2–3k nhãn duyệt → fine-tune 5CD-AI/visobert-14gb-corpus,
  xuất ONNX INT8 (docs/benchmarks/llm-labeling.md).

## 2026-09-08 — Ràng buộc cân bằng transition trong acceptance của bộ gán (gói Q2)

- **Nguồn:** Zeng et al., *Sequentially-Rerandomized Switchback Experiments* (SRSB),
  arXiv:2604.02489 (2026); Ni, Kalfountzou & Bojinov, HBS WP 26-012 (HT cặp liền kề);
  Liu & Zhong, arXiv:2602.23257 (CRT gộp khối); tổng hợp trong
  `docs/research/data/2026-09-07-reading-notes.json` (đề xuất 5).
- **Dùng được:** blocked-SRSB cần N đơn vị song song — với 1 stream, dạng khả thi duy
  nhất là ràng buộc ĐẾM transition trong acceptance rule: #(BẬT,BẬT) ≥ 3 VÀ
  #(TẮT,TẮT) ≥ 3 VÀ |hiệu| ≤ 1 trên chuỗi khối đo được. Đối xứng BẬT↔TẮT nên marginal
  propensity giữ đúng 0,5; RI redraw dùng chính hàm production nên suy diễn tự đúng.
- **KHÔNG dùng được:** Mahalanobis acceptance trên biến tiên lượng (SRSB Alg 1) — để
  đợt chung kết; blocked-SRSB Alg 3 nguyên bản — không có đơn vị song song.
- **Đo được (08/09):** tỷ lệ chấp nhận lịch 90′ mặc định ≈ 9,6% → trung bình ≈ 9,4
  redraw/lịch (kỳ vọng < 5 của agenda KHÔNG đạt với đúng công thức — ghi trung thực);
  60′ ≈ 0,4% (~245 redraw, vẫn xa trần 10.000); 30′ suy giảm còn 1 cặp/loại + cờ
  `realized_transition_pairs` + cảnh báo API trước phát sóng.
- **Quyết định (2026-09-08):** vào `draw_assignments`/`generate_schedule` +
  `DesignParams.min_transition_pairs=3` (tắt được bằng 0 cho phiên cũ); cập nhật
  PREREGISTRATION.md mục 2 TRƯỚC khóa tuần 6; trần khả thi của chuỗi ngắn theo
  `_transition_requirement` (cận cần, không phải chứng minh đủ — RuntimeError
  `max_redraws` giữ nguyên làm lưới an toàn).

## 2026-09-08 — Click hợp lệ kiểu IAB (GIVT-lite), flag-don't-drop (gói Q1)

- **Nguồn:** IAB Click Measurement Guidelines (2009) — chuẩn đo click ngành quảng cáo:
  lọc "invalid traffic" bằng danh sách robot/spider đã biết + quy tắc phi-người
  (dedup, cap khối lượng), đếm phía server; Fabijan et al., KDD 2019 — traffic bot
  làm méo metric thí nghiệm trực tuyến, phải lọc bằng quy tắc tiền đăng ký.
- **Dùng được:** 5 quy tắc GIVT-lite tự host được từ thuộc tính request thuần: UA regex,
  header prefetch/prerender, chỉ-GET, refractory τ=10s theo dedup_hash+shortlink,
  volume cap M=5/hash/shortlink/khối. Gắn cờ chứ không xóa row → raw là secondary
  bắt buộc, recount lại được cho sensitivity τ∈{5,30,60} và đối soát T+30′.
- **KHÔNG dùng được:** SIVT (invalid tinh vi — fingerprint hành vi, danh sách IP thương
  mại) — cần dữ liệu/nhà cung cấp ngoài scope pilot; danh sách robots IAB/ABC đầy đủ
  có phí — thay bằng regex tự quản, kiểm toán được trong repo.
- **Bất biến:** quy tắc hợp lệ MÙ với nhánh gán (chỉ thuộc tính request) — quy tắc nhìn
  thấy assignment có thể tự chế ra hiệu ứng; test khẳng định chữ ký hàm sạch.
- **Quyết định (2026-09-08):** migration 0004 (is_valid/invalid_reason/ua_class trên
  click_event), `core/click_validity.py` (classify_click + recount_click_validity),
  phân loại lúc ghi ở `/r/{code}` (302 luôn trả bất kể), outcome chính đếm CHỈ click
  hợp lệ (`block_frame`, `include_invalid=True` cho raw), PREREGISTRATION §4.1 cập
  nhật TRƯỚC khóa tuần 6; gate sim: bot tiêm vào không làm lệch estimator trên valid.
- **Bổ sung khi soát lại (08/09):** phân loại lúc ghi cần lịch sử của ĐÚNG fingerprint,
  nên thêm `store.list_clicks_for_fingerprint` (2 backend) + migration 0005 (index
  `session_id, dedup_hash, shortlink_code, ts`). Đọc cả phiên khiến mỗi redirect tốn
  O(số click đã có) — chậm nhất đúng lúc bot đang bắn, tức là quy tắc chống bot tự
  biến mình thành đòn bẩy cho bot. Hook `livelift-qc --recount-clicks` vào runbook
  mốc T+30′.


## 2026-09-08 — Tách assignment / exposure + cam kết design_hash (gói Q3)

**Nguồn:** Bakshy, Eckles & Bernstein, *"Designing and Deploying Online Field
Experiments"* (PlanOut), WWW 2014 — thiết kế được mô tả bằng script tất định,
"gán" là một sự kiện ghi lại được và tách khỏi "phơi nhiễm". Fabijan et al.,
*"Diagnosing Sample Ratio Mismatch in Online Controlled Experiments"* / kinh
nghiệm hạ tầng thí nghiệm (KDD 2019) — log phơi nhiễm bất biến là điều kiện cần
để chẩn đoán và để tin dữ liệu thí nghiệm.

- **Dùng được:** tách hai bảng chỉ-ghi-thêm. `assignment_event` = TOÀN BỘ lịch
  materialize một lần lúc sinh schedule (ý định thí nghiệm); `exposure_event` =
  điều bàn điều khiển thực sự làm (thực tế vận hành). Tuân thủ trở thành một
  VIEW dẫn xuất (`derive_compliance`), không còn là con số được ghi đè.
- **Dùng được:** cam kết thiết kế `design_hash = SHA256(canonical JSON của
  DesignParams ∪ seed)`, công bố ở phản hồi `POST /schedule` và hiện rút gọn (8
  ký tự) trên thanh trạng thái bàn. Lịch là hàm tất định của (tham số, seed),
  nên hash đúng cặp đó là vân tay của toàn bộ ngẫu nhiên hóa: ai giữ design json
  cũng tính lại và đối chiếu được.
- **KHÔNG dùng được:** namespace/segment của PlanOut (nhiều thí nghiệm song song
  trên cùng người dùng) — LiveLift chỉ có MỘT stream và một thí nghiệm mỗi phiên;
  bê nguyên sẽ là hạ tầng thừa. Cưỡng chế bất biến bằng quyền DB (REVOKE
  UPDATE/DELETE) cũng chưa làm: đó là việc của deploy, không phải migration.
- **Bất biến:** ITT KHÔNG đổi — estimand vẫn theo `assignment`. Hai bảng mới chỉ
  phục vụ first-stage/LATE (§5(d)) và dấu vết kiểm chứng; không bao giờ dùng để
  sửa dữ liệu khối đã chạy (HARNESS §3). Store hai backend cố tình KHÔNG có
  method update/delete cho hai bảng — có test khẳng định.
- **Quyết định (2026-09-08):** migration 0006 (`assignment_event`,
  `exposure_event`), `design_hash` trong `core/assigner/outer.py` (hàm thuần),
  ghi sự kiện ở `service.schedule_session` (gán) và `routes/actions.py` (phơi
  nhiễm), `derive_compliance` trong `core/quality.py`, báo cáo dùng hai bảng khi
  có dữ liệu và rơi về `intervention_log` cho phiên tiền-Q3 (toàn-bộ-hoặc-không
  mỗi phiên, không trộn nguồn). PREREGISTRATION §2 cập nhật TRƯỚC khóa tuần 6.
- **Bổ sung khi soát lại:** lịch được phép sinh lại khi phiên chưa phát, mà bảng
  chỉ-ghi-thêm thì không xóa lượt rút cũ → thêm cột `design_hash` vào
  `assignment_event` để mỗi dòng gắn đúng lượt rút của nó. Thiếu cột này, hai
  lượt rút trộn lẫn và mẫu số tuân thủ bị thổi lên gấp đôi — đúng kiểu lỗi âm
  thầm mà bảng audit sinh ra để chặn.
- **Chưa làm (theo dõi):** biên khối (`block_start`/`block_end`) chưa có nơi xử
  lý trong engine hiện tại nên chưa ghi sự kiện; auto-executor (sau 14/09) sẽ
  ghi. `ack_latency_ms` để NULL vì bàn chưa gửi `client_ts` — NULL trung thực
  hơn 0.
## 2026-09-08 — Phễu click→đơn và MDE biến kết quả đơn hàng (gói Q4)

**Nguồn:** Taobao **UserBehavior** (Alibaba Tianchi bộ #649; ~100 triệu tương tác
pv/cart/fav/buy của gần 1 triệu người dùng, 25/11–03/12/2017) cho hai bậc phễu
pv→giỏ và giỏ→mua. Nhánh đối tác: nghiên cứu thương mại điện tử qua livestream
(LSEC), arXiv:2106.03415, cho hệ số khán giả ×4,9 giữa phiên có người bán/KOL
đã có tệp và phiên tự vận hành.

- **Dùng được:** hai tỷ lệ phễu làm PRIOR chuyển click→đơn: pv→giỏ 9,33% ×
  giỏ→mua 24,33% ≈ 2,27%. Bậc giỏ→mua (q2) được QUÉT {0,15; 0,25; 0,35; 0,50}
  vì đây là bậc mà livestream lệch khỏi thương mại điện tử tĩnh nhiều nhất
  (mua bốc đồng, khuyến mãi trong phiên); prior 0,2433 nằm giữa hai mốc đầu.
- **Dùng được:** hệ số ×4,9 chỉ nhân KHÁN GIẢ của nhánh đối tác. Nguồn không
  nói gì về phễu hay tỷ lệ nhấp nên hai đại lượng đó giữ nguyên — nhân cả ba sẽ
  là bịa thêm hai hiệu ứng không có trong tài liệu.
- **KHÔNG dùng được — ghi thẳng vào docstring `order_mde_table`:** KuaiLive
  TUYỆT ĐỐI không map được vào phễu này. 'Click' của KuaiLive là *vào phòng
  live*, không phải nhấp sản phẩm ghim; trùng tên, khác hành vi. Ràng buộc này
  mạnh hơn ghi chú đã có cho `base_click_prob_per_min` vì một tỷ lệ chuyển đổi
  sai ngữ nghĩa đi thẳng vào con số đơn hàng công bố.
- **KHÔNG dùng được:** mức tuyệt đối của phễu Taobao như một số đo của dự án —
  khác nền tảng, khác năm, khác quốc gia. Bảng dán nhãn KỊCH BẢN toàn phần.
- **Bất biến:** MDE đơn hàng dùng ĐÚNG machinery `mde_relative` hiện có, không
  công thức riêng. Đơn là biến đếm hiếm nên CV nạp vào là **CV Poisson**
  `√(trung bình_k 1/λ_k)` — cùng đại lượng `poisson_floor()` đo trên dữ liệu
  thật (có test khẳng định hai đường cho cùng số). Vì thế con số in ra là SÀN:
  phiên thật còn phương sai hệ thống, MDE thật chỉ có thể lớn hơn.
- **Quyết định (2026-09-08):** `analysis/power.py` thêm `order_mde_table`,
  `expected_orders`, `poisson_cv`, `analysis_window_seconds` + hằng số phễu;
  script `analysis/power/bang_mde_don_hang.py` sinh lại
  `docs/benchmarks/order-mde.md` bằng một lệnh. Kết quả đọc được ngay: ở quy mô
  ≤ 50 người xem đồng thời, MDE đơn hàng tốt nhất trong lưới vẫn ~79% — đơn
  hàng KHÔNG thể là biến kết quả khẳng định, nó ở lại đúng chỗ thứ cấp/mô tả
  (PREREGISTRATION §4.2, cập nhật kèm).
- **Bổ sung khi soát lại:** mốc tỉnh táo của agenda (15 người xem × 90 phút →
  0,3–0,6 đơn/phiên) ứng với tỷ lệ nhấp 0,20–0,40 click/1000 giây·người xem,
  trong khi tham số mô phỏng hiện tại (`base_click_prob_per_min = 0,06`) suy ra
  1,00 — cao hơn 2,5–5 lần. CÙNG BẬC nhưng KHÔNG trùng; ghi cả hai vào báo cáo
  và vào test thay vì chỉnh một bên cho khớp. Tham số mô phỏng đó vốn đã được
  đánh dấu là giả định và chỉ phiên thăm dò mới chốt được.


## 2026-09-08 — SRM đợt 1: toàn vẹn gán + giao nhận telemetry (gói Q5)

**Nguồn:** Fabijan, Dmitriev, McFarland, Vermeer, Holmström Olsson & Bosch,
*"Diagnosing Sample Ratio Mismatch in Online Controlled Experiments"* (KDD 2019)
— SRM là kiểm định tỷ lệ ĐƠN VỊ vào từng nhánh so với tỷ lệ thiết kế quy định;
lệch ⇒ lỗi hạ tầng, và mọi kết luận sau đó không đáng tin cho tới khi tìm ra
nguyên nhân. PlanOut (Bakshy, Eckles & Bernstein, WWW 2014) cho phần tách "gán"
khỏi "phơi nhiễm" mà gói Q3 đã dựng.

- **Dùng được:** ý tưởng SRM áp cho **nhịp `session_tick`** — đơn vị đo do ĐỒNG
  HỒ sinh (30 giây một nhịp), nên số nhịp trong một khối do độ dài khối và
  đường ống ingest quyết định, không do nhánh. Kiểm định nhị thức CHÍNH XÁC
  (`scipy.stats.binomtest`, hai phía) thay vì xấp xỉ chuẩn: vài trăm nhịp một
  phiên thì đuôi α = 0,005 không tin được bằng xấp xỉ.
- **Dùng được:** kỳ vọng của kiểm định là **TỶ LỆ THỜI GIAN BẬT/TẮT của lịch đã
  persist**, KHÔNG phải 0,5. Khối biên nhân đôi (quy tắc 2m, Bojinov et al.
  2023) cộng jitter ranh giới khiến thời gian BẬT lệch khỏi một nửa khá xa ở
  nhiều lịch hợp lệ; lấy 0,5 sẽ biến lịch sạch thành báo động đỏ (có test đo
  đúng điều này trên 40 lịch).
- **KHÔNG dùng được — quy tắc bất di bất dịch, ghi cả trong mã lẫn test:**
  KHÔNG BAO GIỜ chạy SRM trên **người xem / bình luận / click**. Ba đại lượng
  đó là HẬU CAN THIỆP: nếu chiến lược ghim có tác dụng thì chúng PHẢI lệch giữa
  hai nhánh — đó chính là thứ thí nghiệm đi đo. Một "SRM" trên chúng sẽ gắn cờ
  đỏ đúng lúc thí nghiệm thành công và cám dỗ loại khối theo kết quả.
- **KHÔNG dùng được:** cơ chế "auto-invalidate thí nghiệm khi SRM đỏ" của các
  nền tảng lớn. Ở đây kết quả chỉ là **CỜ** kèm thông điệp điều tra; không sửa,
  không loại dữ liệu tự động (HARNESS §3).
- **Bất biến:** `assignment_integrity` so lịch đã persist (ưu tiên
  `assignment_event` chỉ-ghi-thêm, rơi về `design['blocks']`) với **khung phân
  tích thật sự đi vào ước lượng viên** (`block_frame`), không với một bản sao
  viết tay — bản sao sẽ mù đúng chỗ cần nhìn (lỗi trong `block_frame` /
  `rebuild_schedule`). Hai nguồn persist mâu thuẫn nhau là một lỗi RIÊNG.
- **Quyết định (2026-09-08):** `core/quality.py` thêm `check_assignment_integrity`
  và `check_telemetry_delivery` (+ `telemetry_counts` / `TelemetryCounts` /
  `check_telemetry_counts` cho đường gộp chuỗi phiên); bộ QC sau phiên lên
  **8 mục**; α = 0,005 mỗi kiểm định, họ ~10 kiểm tra ⇒ ≤ 5%. `livelift-qc` dựng
  khung phân tích bằng chính `block_frame` và nạp `assignment_event` lọc theo
  `design_hash`. Không có thay đổi schema — hai kiểm tra đọc bảng đã có.
  PREREGISTRATION §8.1 cập nhật TRƯỚC khóa tuần 6.
- **Bổ sung khi soát lại (đo được, không phải phỏng đoán):** ở mức MỘT phiên 90
  phút (~180 nhịp), kiểm định chỉ bắt được sự cố THÔ — mất ~50% nhịp một nhánh;
  mất 10% thì vô hình (đo: 0/20 phiên). Muốn nhạy tới vài phần trăm phải GỘP cả
  chuỗi: cộng `TelemetryCounts` rồi kiểm định một lần (đo: công suất 100% trên
  50 lần lặp × 30 phiên khi mất 10% nhịp khối TẮT, FPR 0/50 trên dữ liệu sạch).
  Tính bảo thủ này là cố ý: nhịp telemetry gần như tất định trong khi phương
  sai nhị thức rộng hơn thế nhiều — thà bỏ sót còn hơn kêu oan mỗi phiên.
- **Chưa làm (theo dõi):** kết luận "nhịp tick độc lập với nhánh" chỉ đúng
  chừng nào bộ ghi tick còn là nhịp đồng hồ. Nếu có ngày tick chỉ được ghi khi
  có người xem, nó thành đại lượng hậu can thiệp và kiểm tra này phải xét lại —
  cảnh báo đã ghi trong docstring.

---

## 2026-09-08 — Tách `analysis/estimators.py` thành adjust / robust / carryover (gói P5a)

**Nguồn:** không có nguồn học thuật — đây là ghi chú CẤU TRÚC MÃ, không phải
phương pháp mới. Ghi vào sổ vì phản biện kỹ thuật đặt nó làm điều kiện tiên
quyết cho chương trình 2026-09-07.

- **Lý do tách:** ba đề xuất sắp tới (P3 CUPED-mv/linearization, P4 wild
  cluster bootstrap + ICS, C2/C3 carryover lag-1) đều sửa cùng một file
  `estimators.py` trong cùng một tuần, ngay trước mốc khóa PREREGISTRATION
  (tuần 6). Va chạm merge trên file chứa kiểm định CHÍNH là con đường ngắn
  nhất để một thay đổi "cơ học" lặng lẽ đụng vào `randomization_test` /
  `randomization_ci` / `analyze_outer`.
- **Đã làm:** `cuped_adjust` → `analysis/adjust.py`; `ols_fe_lin` + `OLSResult`
  → `analysis/robust.py`; `analysis/carryover.py` mới CHỈ có docstring nêu API
  dự kiến (`ht_lag1`, `carryover_gate`, `impulse_response`), chưa cài đặt gì.
  `estimators.py` re-export toàn bộ tên cũ ⇒ **0 import site phải đổi**.
- **KHÔNG làm (cố ý):** không dời `randomization_test`, Fisher CI,
  `analyze_outer`, `late_wald`. Kiểm định chính ở nguyên chỗ cho tới sau khi
  khóa prereg. Không đổi một dòng thân hàm nào — refactor thuần cơ học.
- **Gác bằng test:** `tests/test_estimators.py` thêm 6 test — cùng-một-object
  qua hai đường import (`is`, bắt kiểu tách nhầm thành hai bản song song), tập
  `__all__` khớp API cũ, `__module__` xác nhận đúng thứ được dời, kết quả
  CUPED/OLS trùng khít qua cả hai đường gọi, `carryover` vẫn rỗng (một hàm
  carryover xuất hiện phải kèm nghiên cứu + test riêng theo HARNESS §4), và
  cạnh phụ thuộc chỉ đi một chiều — quét `ast` cấm ba module mới import ngược
  về `estimators`, vì import vòng sẽ xóa đúng tính cách ly mà P5a mua được.
  (Đính chính 09/09: bản ghi 08/09 viết "6 test" khi mới có 5 — test thứ sáu,
  chính là guard một chiều nói trên, được bổ sung ngày 09/09 để con số khớp
  thực tế thay vì sửa con số xuống.)
- **Quyết định:** mọi bổ sung về hiệu chỉnh hiệp biến vào `adjust.py`, về
  phương sai robust vào `robust.py`, về carryover vào `carryover.py` — không
  quay lại `estimators.py`.

---

## 2026-09-09 — Mẫu số nội sinh + CUPED đa biến (gói P3+P4)

**Nguồn:** Deng, Knoblich & Lu, *Applying the Delta Method in Metric Analytics*,
KDD 2018 / arXiv:1803.06336; arXiv:2510.01127 (ICS); arXiv:2608.24038 (CUPED-mv);
arXiv:2606.27662 (bản đồ chế độ — vùng số cụm nhỏ).

- **Dùng được (Deng KDD'18):** biến kết quả chính của dự án là một TỶ LỆ của hai
  tổng (click hợp lệ / viewer-giây), không phải trung bình cấp đơn vị. Tuyến tính
  hóa `L_b = click_b − r0·exposure_b` biến nó thành metric cộng tính chạy được
  bằng đúng ước lượng viên cấp khối đang có; phương sai delta theo cụm cho một
  phân rã "bao nhiêu phần bất định là giữa các phiên".
- **KHÔNG áp dụng được:** phương sai delta ở trên là xấp xỉ CHUẨN dựa vào CLT
  theo cụm. Mẫu tiền đăng ký K = 18–31 phiên nằm trong vùng arXiv:2606.27662 chỉ
  ra là coverage lệch, nên nó **không được làm KTC chính** — KTC chính vẫn là
  Fisher CI (không cần CLT theo cụm). Docstring `delta_var_ratio` ghi thẳng điều
  này để không ai vô tình nâng nó lên.
- **Dùng được (ICS):** giả định "mẫu số ngoại sinh" kiểm tra được bằng chính kiểm
  định ngẫu nhiên hóa đã tiền đăng ký, chỉ đổi biến kết quả sang viewer-giây.
- **Điểm phải cẩn thận (tự soát, không có trong nguồn):** cổng này chạy trên một
  đại lượng HẬU CAN THIỆP, đúng thứ PREREGISTRATION §8.1 cấm đưa vào bộ SRM. Nó
  không mâu thuẫn §8.1 vì Ý NGHĨA của cờ khác hẳn (SRM = dữ liệu hỏng; ICS =
  estimand cần chú thích), nhưng vì cùng lý do "hậu can thiệp", nó **phải nằm
  trong phạm vi khóa §7** — đọc sớm vẫn là nhìn trộm tác động. Quyết định: khóa.
- **Quy ước r0 (tiền đăng ký, §5e):** r0 = tỷ lệ gộp của MẪU QUAN SÁT, cố định
  qua mọi redraw. Tính lại r0 trong từng redraw sẽ làm outcome động theo vector
  gán đang kiểm định — mọi test khác vẫn xanh, chỉ p-value sai. Có test khẳng
  định bất biến này trực tiếp trên ma trận redraw production.
- **Dùng được (CUPED-mv):** nhiều hiệp biến cùng lúc + co ridge + chọn siêu tham
  số ngoài mẫu. **Sửa cho bối cảnh:** fold phải là PHIÊN, không phải khối — khối
  cùng phiên chia chung cú sốc phiên nên K-fold ngẫu nhiên sẽ rò rỉ và báo mức
  giảm phương sai không sống sót sang phiên sau. Ridge chuẩn hóa cột và chia Gram
  cho n (λ trên thang tương quan), vì cột thô trải từ phút tới phút² thì phạt
  không chuẩn hóa sẽ dập gần hết số hạng bậc hai bất kể λ.
- **KHÔNG áp dụng được:** mọi hiệp biến lag trong-phiên (§5c). Chúng giảm phương
  sai đẹp hơn hẳn và không làm test nào khác đỏ — chỉ hiện ra ở FPR trôi lên
  trong vòng A/A. Ma trận hiệp biến vì vậy chỉ gồm giờ-trong-ngày (sin/cos, giờ
  địa phương) và spline bậc 2 của phút-vào-phiên; nút 45 phút là hằng số lịch,
  không khớp từ dữ liệu.
- **Đo được (không phỏng đoán):** FPR của RI trên L khi mẫu số lệch +20% mà tỷ lệ
  click không đổi: 3/60 ở α = 0,05. Công suất cổng ICS trước mẫu số lệch 20%:
  40/40; FPR cổng khi không có hiệu ứng: 3/40 ở α = 0,10. `delta_var_ratio` so
  bootstrap theo cụm (40 cụm): lệch 0,3%. CUPED-mv trên thế giới có hiệu ứng
  giờ-trong-ngày nhân tạo: `se_ratio` ≈ 0,46 (SE giảm ~54%), R² ngoài-phiên 0,76;
  trên thế giới KHÔNG có tín hiệu: λ chọn = 10 (co nhiều nhất), `se_ratio` 0,998,
  R² ngoài-phiên **âm** — đúng hành vi trung thực. A/A với CUPED-mv: 2/60.
- **Quyết định:** cả hai đường vào `analyze_outer` dưới dạng THAM SỐ TẮT MẶC ĐỊNH
  (`outcome_mode='ratio'`, `adjust='none'`); đường mặc định có test khẳng định
  kết quả trùng khít với trước gói này. Bật đường nào cho kết quả khẳng định là
  quyết định tiền đăng ký của nhóm. PREREGISTRATION §5c/§5e/§7/§10 cập nhật
  TRƯỚC khóa tuần 6.
- **Chưa làm (theo dõi):** `analyze_outer(adjust='cuped_mv')` chưa được nối vào
  `/experiment/summary` — nối vào là bật một đường phân tích, phải có quyết định
  nhóm trước. `blocks_to_dicts` chưa xuất `start_ts`/`start_offset_s`, nên khi
  nối sẽ phải bổ sung đường dữ liệu đó.

---

## 2026-09-09 — ICC ở biến kết quả + bộ khung SBC (gói P1-K2 + P2)

**Nguồn:** KuaiLive (arXiv:2508.05633 — 1,16 triệu phòng shop, làm nền cho hiệu chỉnh
dwell/comment/like đã dùng từ 02/09); Talts, Betancourt, Simpson, Vehtari & Gelman,
*Validating Bayesian Inference Algorithms with Simulation-Based Calibration*
(arXiv:1804.06788); Modrák và cộng sự, *Simulation-Based Calibration Checking for
Bayesian Computation* (arXiv:2211.02383); Massart 1990 (hằng số chặt của bất đẳng thức
DKW); Aldor-Noiman và cộng sự 2013 (băng đồng thời cho ECDF); Shrout & Fleiss 1979
(ICC(1) theo ANOVA một chiều).

**Tóm tắt:** SBC kiểm *tính đúng của cả quy trình suy diễn* bằng cách mô phỏng từ chính
mô hình rồi hỏi một đại lượng có phân phối đã biết hay không — với Bayes là hạng của
tham số thật trong mẫu hậu nghiệm (đều U). Modrák tổng quát hoá: chọn đại lượng nào cũng
được, miễn phân phối dưới giả thuyết là biết trước, và luôn cần một **kiểm chứng nghịch
đảo** (tiêm lỗi biết trước) để chứng minh cổng có răng. Chuyển sang khung tần suất của dự
án này, ba đại lượng có phân phối biết trước là: p-value dưới H0 sắc (U(0,1)), cờ phủ KTC
(Bernoulli 0,95), và sai số điểm so chân trị CRN (kỳ vọng 0).

**Đã dùng:** `livelift.sim.report` — `sbc_cell()` (KS + độ lệch ECDF lớn nhất so băng
DKW/Massart, Wilson cho độ phủ, lệch tương đối kèm sai số Monte-Carlo), `render_report()`,
`session_icc()` (ANOVA một chiều, Shrout & Fleiss); `livelift.sim.validate.run_grid` +
`GridSpec`; `python -m livelift.sim.cli --grid` sinh `docs/benchmarks/sim-validation-report.md`.
Hai knob mới `SimParams.click_frailty_cv` và `SimParams.session_click_sigma` (mặc định
TẮT, luồng RNG riêng, có test bất biến từng-bit theo seed cũ).

**Bác bỏ / KHÔNG áp dụng được:**
- *Băng Aldor-Noiman* — chặt hơn DKW ở n nhỏ nhưng độ rộng đến từ hằng số hiệu chuẩn bằng
  mô phỏng. Bịa hằng số đó ra là đúng thứ dự án cấm, nên dùng băng DKW/Massart và **ghi rõ
  là bảo thủ**; KS mới là công cụ sắc, băng là thứ vẽ được lên đồ thị ECDF.
- *Hạng SBC kiểu Bayes* — không có mẫu hậu nghiệm để xếp hạng; đường tần suất tương đương
  là tính đồng đều của p-value, và nó **chỉ có nghĩa ở ô A/A**. Ô có tác động thì p-value
  dồn về 0 theo thiết kế, nên `check_uniformity` mặc định tắt ở đó.
- *Tiêm lỗi "tắt studentization ở cả hai phía"* — thử và **bác bỏ**: kiểm định ngẫu nhiên
  hoá là CHÍNH XÁC dưới giả thuyết không sắc với bất kỳ thống kê nào, nên ô A/A vẫn đồng
  đều và phép tiêm không chứng minh được gì. Lỗi thực sự phát hiện được là **lệch pha giữa
  thống kê quan sát và thống kê tham chiếu** (một phía mất studentization) — đó là dạng bug
  có thật và nó làm p-value dồn về 1. Test nghịch đảo dùng dạng này.

**Đo được (không phỏng đoán):**
- Ánh xạ σ → ICC(y) (400 phiên × 90 phút, ± là SE bootstrap theo cụm): σ=0 → **+0,008 ±
  0,005**; 0,03 → 0,018; 0,06 → **0,048**; 0,095 → 0,101; 0,1 → 0,110; 0,2 → 0,333;
  0,3 → 0,535. Tức "σ=0" đọc là ICC≈0,01 chứ không phải 0 (ICC(1) lệch lên khi phương sai
  trong-cụm không đều, mà `session_shock_sd` làm đúng thế).
- **Docstring cũ sai:** `session_shock_sd` được ghi là "generates session ICC". Không phải:
  biến kết quả chính là TỶ LỆ (click / 1000 giây·người xem), cú sốc lượt vào nhân cả tử lẫn
  mẫu nên đổi *độ nhiễu* của y chứ không đổi E[y]. Đã sửa.
- **Frailty theo người xem cũng tạo ICC** — trái với dự đoán ban đầu của gói này. Khán giả
  hữu hạn (~500 lượt vào/phiên) nên trung bình frailty của phiên tự nó là một nhân tử cấp
  phiên với CV ≈ cv/√N: ICC 0,008 (cv=0) → 0,022 (0,5) → 0,038 (1,0) → 0,059 (1,5) →
  0,083 (2,0). Dấu hiệu phân biệt hai knob là **phương sai TRONG-phiên**: frailty làm nó
  tăng (0,0853 → 0,1536), knob phiên thì không (σ=0,06 → 0,0855). Mức trung bình y giữ
  1,00 ở mọi hàng — cả hai knob đều mean-1.
- **Cổng ở ICC≈0,05 XANH với NGUYÊN ngưỡng cũ** (200 lặp A/A; 40 lặp bias/coverage). Đúng
  dự đoán cơ học: redraw ngẫu nhiên hoá diễn ra **trong từng phiên**, nên mức nền cấp phiên
  chung cho cả hai nhánh của tương phản và triệt tiêu khỏi cả ước lượng lẫn phân phối tham
  chiếu. Thiết kế giữa-phiên sẽ phải trả giá cho ICC; switchback thì không.
- Lưới SBC bộ khung (4 ô × 100 lặp): 4/4 XANH, lệch tương đối +0,7% và +1,5% ở hai ô có
  tác động, độ phủ 95–97%.

**Quyết định (2026-09-09):** hai knob vào `SimParams` **mặc định TẮT**; `session_click_sigma`
là knob ICC chính thức, `click_frailty_cv` là knob phân tán (có tác dụng phụ ICC đã đo và
ghi bảng). PREREGISTRATION §3 bước 2–3 thêm trục ICC vào lưới hiệu chỉnh — trước 09/09 bước
1(d) đo ICC rồi bước 2 không có chỗ nạp vào, đó là một lỗ hổng của quy trình đã đăng ký chứ
không phải của mã. Lưới SBC đầy đủ (~20 ô × 1000 lặp) là việc tuần khóa; bản trong repo tự
dán nhãn SKELETON và **không** được trích như bằng chứng hiệu chuẩn đầy đủ.

**Bổ sung cùng ngày (09/09) — bảng SỐ ĐO phải có lệnh sinh lại.** Ánh xạ σ → ICC ở trên
được đo thật nhưng chỉ tồn tại dưới dạng bảng chép trong docstring và trong báo cáo lưới:
ba bản sao của cùng một phép đo, không bản nào chạy lại được. Đã đóng lỗ hổng đó:
`analysis/calibration/bang_icc_mo_phong.py` sinh `docs/benchmarks/sim-icc-map.md` bằng
một lệnh, dùng `livelift.sim.validate.measure_icc_map` (mọi hàng CHUNG `master_seed` nên
chung lượt vào/thời gian ở lại/nhiễu AR(1) — hai hàng chỉ khác nhau ở knob) và
`livelift.sim.report.session_icc_bootstrap_se` (bootstrap theo **cụm phiên**, không theo
khối: khối trong cùng phiên phụ thuộc nhau, đó đúng là đại lượng đang đo; bootstrap theo
khối sẽ báo SE nhỏ hơn sự thật). Chạy lại ở 400 phiên × 90 phút cho **đúng** các con số đã
ghi (0,008 / 0,018 / 0,048 / 0,101 / 0,110 / 0,333 / 0,535); chỉ hai SE lệch ở chữ số thứ
ba (0,022→0,021; 0,024→0,023) do seed bootstrap khác — đã sửa docstring theo bản sinh lại
được. Bảng chép tay trong `sim/cli.py` bị **xóa**, thay bằng liên kết tới file chuẩn: một
bảng số đo chép sang file thứ hai là chỗ để hai con số lặng lẽ lệch nhau.

Bảng frailty (tác dụng phụ ICC của `click_frailty_cv`) cũng chạy trong cùng lệnh đó và
**tái tạo đúng từng con số** đã ghi: ICC 0,008 / 0,022 / 0,038 / 0,059 / 0,083 và phương
sai trong-phiên 0,0853 / 0,0883 / 0,0992 / 0,1229 / 0,1536, trung bình y ≈ 1,00 ở cả hai
bảng. Tức toàn bộ phần "đo được" của gói P1-K2 đã được kiểm chứng độc lập, không còn chỗ
nào phải tin. File đầu ra mang sẵn một phép TỰ KIỂM: hàng knob = 0 xuất hiện ở cả hai bảng
và phải trùng nhau (trùng: +0,008 ± 0,005, 0,0853) — nếu lệch thì hai bảng đã không chạy
trên cùng một thế giới và mọi so sánh giữa hai knob mất nghĩa.
