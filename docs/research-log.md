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
