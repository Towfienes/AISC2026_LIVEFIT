# LiveLift

**Nền tảng thí nghiệm vận hành cho livestream thương mại**
*Causal experimentation infrastructure for live commerce operations*

> Một phiên livestream tạo ra hàng nghìn tín hiệu, nhưng đội vận hành vẫn không biết
> chiến thuật nào thực sự hiệu quả. LiveLift biến mỗi quyết định trong phiên thành một
> thí nghiệm đo được — phân biệt một hành động **tạo ra giá trị** với một **sự trùng
> hợp thời điểm**.

Dự thi **AISC'26 — bảng Data Driven Business** · Việt Nam · Chung kết 11/2026

`157 test pass` · `Python 3.11 + FastAPI + PostgreSQL/TimescaleDB + Next.js 14` · `Docker Compose một lệnh`

---

## Abstract (English)

LiveLift is a control-desk platform that turns in-session live-commerce decisions
(*which product to pin, when*) into valid randomized experiments. It implements a
**two-tier switchback design**: the outer tier randomizes 5-minute time blocks between
"system strategy" and "operator default" (i.i.d. Bernoulli(0.5) with rerandomization,
endpoint-doubled blocks per Bojinov–Simchi-Levi–Zhao 2023, analysis-time burn-in per
Hu–Wager 2022); the inner tier randomizes only among candidate products whose posterior
intervals overlap, logging exact propensities. Primary inference is a studentized
randomization test whose reference distribution is redrawn with the **production
assignment mechanism**, with Fisher confidence intervals by test inversion. The full
pipeline — assignment → event capture → outcome construction → estimation — is
validated end-to-end on a simulator calibrated against **KuaiLive** (SIGIR 2026; 1.16M
real shop-livestream rooms): under a true null the system rejects at 4.5% (nominal 5%,
exact binomial p = 0.87) with 95.5% CI coverage. Every displayed number carries its
provenance (forecast vs. experiment), Vietnamese PII is scrubbed at ingest before any
write, and the host screen is structurally blinded to treatment assignment.

---

## Mục lục

1. [Tầm nhìn & mục tiêu](#1-tầm-nhìn--mục-tiêu)
2. [Bài toán](#2-bài-toán)
3. [Phương pháp khoa học](#3-phương-pháp-khoa-học)
4. [Kiến trúc hệ thống](#4-kiến-trúc-hệ-thống)
5. [Kết quả đã kiểm chứng](#5-kết-quả-đã-kiểm-chứng)
6. [Khởi động trong 5 phút](#6-khởi-động-trong-5-phút)
7. [Cấu trúc kho mã](#7-cấu-trúc-kho-mã)
8. [Quy trình phát triển (harness)](#8-quy-trình-phát-triển-harness)
9. [Trạng thái & lộ trình](#9-trạng-thái--lộ-trình)
10. [Dành cho thành viên mới](#10-dành-cho-thành-viên-mới)
11. [Pháp lý, quyền riêng tư & đạo đức](#11-pháp-lý-quyền-riêng-tư--đạo-đức)
12. [Tài liệu tham khảo](#12-tài-liệu-tham-khảo)

---

## 1. Tầm nhìn & mục tiêu

### Tầm nhìn khi hoàn thành

Một nhà bán livestream cỡ vừa ở Việt Nam mở LiveLift lên như mở một bảng điều khiển
thứ hai cạnh OBS. Sau mỗi phiên, họ không nhận về một mớ "kinh nghiệm cảm tính" mà nhận
một **báo cáo tác động**: *chiến thuật ghim sản phẩm tuần này tạo thêm X% lượt nhấp,
khoảng tin cậy [a, b], đo bằng thí nghiệm ngẫu nhiên hóa trên chính phòng live của bạn.*
Sau mười phiên, tri thức vận hành của cửa hàng không còn nằm trong trí nhớ của một
người — nó nằm trong dữ liệu có bảo chứng thống kê, và **cơ chế đo lường đó cũng chính
là cơ chế định giá**: gói Performance thu phí theo giá trị tăng thêm đo bằng holdback
ngẫu nhiên mà nhà bán tự kiểm chứng được trong tài khoản của mình.

### Mục tiêu mùa thi (đến 11/2026)

| # | Mục tiêu | Thước đo |
|---|---|---|
| 1 | Hạ tầng thí nghiệm hợp lệ, tự chứng minh được | Ước lượng viên hiệu chỉnh đúng trên mô phỏng (A/A ≈ 5%, coverage ≈ 95%) — **đã đạt** |
| 2 | Chuỗi thí nghiệm thật trên Live Lab | ≥ 18 phiên × 90 phút, ≥ 250 khối/nhánh, tuân thủ ≥ 90% |
| 3 | Kết quả chính có bảo chứng | ITT + LATE với KTC 95%, MDE thực tế báo cáo trung thực |
| 4 | Sản phẩm dùng được bởi người ngoài nhóm | Toàn bộ vòng đời phiên chạy được từ giao diện — **đã đạt** |
| 5 | Bằng chứng thị trường | ≥ 3 thư quan tâm, ≥ 1 đối tác dữ liệu gắn bàn trung control |

**Nguyên tắc bất di bất dịch:** không để nghiên cứu phụ nuốt sản phẩm lõi; một con số
sai được nói chắc chắn tệ hơn không có con số.

## 2. Bài toán

Phút 30, tổ vận hành ghim sản phẩm B. Phút 35, doanh thu tăng 40%. Do ghim sản phẩm?
Do thuật toán vừa đẩy 500 người xem vào phòng? Do host kể chuyện hay? Không ai biết —
nên "kinh nghiệm" cả ngành tích lũy phần lớn là **tương quan giả**.

Các công cụ hiện có (Chanmama, Feigua, Kalodata, EchoTik…) hoặc *quan sát hồi cứu*,
hoặc *cảnh báo theo ngưỡng cố định* ("CTR < 5% thì đổi sản phẩm"). Theo khảo sát của
nhóm, **không công cụ thương mại nào chạy thí nghiệm ngẫu nhiên trong phiên hay ghi
xác suất gán** — tiền lệ duy nhất là một nghiên cứu học thuật (ISR 2025). Đó là khoảng
trống LiveLift nhắm vào: không phải một dashboard đẹp hơn, mà một **moat phương pháp**.

## 3. Phương pháp khoa học

### 3.1 Thiết kế hai tầng

```
PHIÊN LIVE (90 phút)
│
├── TẦNG NGOÀI — switchback theo khối thời gian
│   Khối 5 phút, khối đầu/cuối nhân đôi (Bojinov et al. 2023)
│   Gán i.i.d. Bernoulli(0.5) + rerandomization (≥2 khối/nhánh/giai đoạn)
│   Jitter ranh giới ±30s · KHÔNG washout thiết kế — burn-in lúc phân tích
│   (Hu & Wager 2022, sensitivity b ∈ {0..3} phút)
│   → BẬT: hệ thống điều khiển ghim · TẮT: đội vận hành như thường lệ
│   → Trả lời: HỆ THỐNG có tạo giá trị không? (kết quả CHÍNH)
│
└── TẦNG TRONG — khám phá có kiểm soát
    Chỉ trong khối BẬT, chỉ khi các ứng viên có khoảng hậu nghiệm CHỒNG LẤN
    (Gamma-Poisson, cùng đơn vị với biến kết quả) → chọn đều, ghi propensity 1/k
    → Trả lời: hành động nào tốt hơn ở trạng thái nào? (dữ liệu off-policy)
```

**Biến kết quả chính:** lượt nhấp sản phẩm / 1000 giây·người xem theo khối, đo qua
link chuyển hướng tự phục vụ (`GET /r/{code}`) — định nghĩa vận hành do nhóm kiểm soát
hoàn toàn, không phụ thuộc nền tảng.

### 3.2 Suy diễn

- **Kiểm định ngẫu nhiên hóa studentized** (Bojinov & Shephard 2019): phân bố tham
  chiếu vẽ lại bằng *chính hàm gán production* trên **toàn bộ lịch đã chạy** rồi áp
  mặt nạ loại trừ — không phải một phép xáo trộn tùy tiện.
- **KTC Fisher** bằng nghịch đảo kiểm định; sàn p-value 1/(draws+1) hiển thị trung thực.
- **Hájek IPW**, **OLS FE-phiên + tương tác Lin (2013)** (SE cụm theo phiên), **LATE**
  qua biến công cụ cho chế độ đề xuất/đối tác.
- **Từ chối có kỷ luật:** thiết kế không kiểm định được (một nhánh < 2 khối) trả
  `estimable=False` kèm lý do tiếng Việt — không bao giờ trả một con số đẹp vô nghĩa.

### 3.3 Ba lớp phòng thủ liêm chính (đặc sản của dự án)

1. **E2-04 — nguồn con số ở cấp schema:** số từ mô hình dự báo *không thể* mang khoảng
   tin cậy (validator Pydantic từ chối construct); chỉ số từ thí nghiệm mới được.
2. **Làm mù ở cấp kiểu dữ liệu:** màn hình host là model riêng chỉ có 4 trường — rò rỉ
   nhánh thí nghiệm qua endpoint host là *lỗi kiểu*, không phải lỗi review.
3. **Dấu vết kiểm chứng:** lịch gán sinh và lưu **trước khi phát sóng** (seed tái lập
   được); QC sau phiên đối chiếu khối đã chạy với lịch đã lưu; tiền đăng ký khóa bằng
   commit trước chuỗi khẳng định.

### 3.4 Thẩm định bằng mô phỏng đã hiệu chỉnh

Bằng chứng "ước lượng viên đúng" không phải lời hứa: bộ mô phỏng phiên live (đến/đi
của người xem, nhiễu AR(1), sốc cấp phiên, **núm hiệu ứng lưu**) được hiệu chỉnh theo
**KuaiLive** — 1.157.314 phòng livestream *bán hàng* thật của Kuaishou — rồi toàn
pipeline được chạy Monte-Carlo với tác động biết trước (counterfactual bằng common
random numbers). Kết quả ở [§5](#5-kết-quả-đã-kiểm-chứng).

## 4. Kiến trúc hệ thống

```
THU THẬP                          XỬ LÝ                       PHỤC VỤ
YouTube Live API ─┐                                            ┌─ Web desk (Next.js)
Facebook Graph ───┼─► Lọc PII ─► Chuẩn hóa 30s ─► PostgreSQL ─┼─ /desk /host /replay
VOD chat replay ──┤   (TRƯỚC     tick → khối      Timescale   ├─ /chay-phien /ket-qua
Link đo /r/{code}─┘    mọi ghi)                      │         └─ REST + WebSocket
TikTok (cách ly) ─── collectors/ (không import ngược vào lõi)
                                                     │
                            PHÂN TÍCH: bộ gán 2 tầng · randomization inference
                            · Fisher CI · LATE · power/MDE · mô phỏng thẩm định
```

- **Cách ly rủi ro:** `collectors/tiktok_public` (thư viện reverse-engineered) là dự án
  con độc lập; CI chặn mọi import từ lõi sang — thư viện chết không kéo lõi chết.
- **Hai store tương đương:** InMemory (test/demo) và Postgres (production) chịu chung
  contract test — bài học từ một sự cố phân kỳ đã ghi sổ.

## 5. Kết quả đã kiểm chứng

*Mọi con số dưới đây sinh lại được bằng lệnh trong repo; nguồn: `docs/benchmarks/`,
`tests/` (gate tự động), `docs/incident-log.md`.*

| Hạng mục | Kết quả | Cách kiểm chứng |
|---|---|---|
| **Hiệu chỉnh ước lượng viên (A/A)** | Tỷ lệ bác bỏ **4.5%** (danh nghĩa 5%), nhị thức chính xác p = 0.872 | 200 lần lặp Monte-Carlo, gate `test_aa_false_positive_rate_near_alpha` |
| **Độ phủ KTC 95%** | **95.5%** | cùng gate |
| **Thu hồi tác động biết trước** | sai lệch **−0.3%** (không hiệu ứng lưu) | `livelift-simulate` |
| **Dưới hiệu ứng lưu** (bán rã 2ph / 3ph) | lệch −20% / −30% *về phía 0* (bảo thủ), coverage 84% / 60% | đã ghi trung thực — lý do tuần 3 phải đo t_mix |
| **MDE hiệu chỉnh theo lực thật** | 20.1% (18 phiên, CV đo được) — công thức cũ sai 30.1% | sweep 4 mức tác động × 60 lặp; `RANDOMIZATION_TEST_MARGIN = 1.2` đo được |
| **Phân loại ý định tiếng Việt** | macro-F1 **0.870** (5-fold CV) vs baseline từ khóa 0.653 | `python -m livelift.nlp.train_intent` |
| **Lọc PII** | recall ≥ 95% từng loại (SĐT/email/mã đơn/địa chỉ) trên bộ nhãn | gate `test_pii_filter.py` |
| **Hiệu chỉnh KuaiLive** | 1.16M phòng shop; dwell gắn bó trung vị 3.6ph; đơn vị ms **chứng minh bằng ràng buộc vật lý** | `analysis/calibration/kuailive_calibration.py` |
| **Live-fire video thật** | VOD 262 phút, **14.903 bình luận chat replay** chạy trọn qua API sản phẩm | phiên phân tích trong DB, nhãn "quan sát" |
| **Kiểm toán đối kháng** | 16/16 phát hiện xử lý (2 FATAL: NaN→significance; khối chưa phát bịa exposure) | `docs/incident-log.md` — 13 sự cố, đủ root cause + gate |

## 6. Khởi động trong 5 phút

Yêu cầu: Docker Desktop. (Phát triển: thêm Python 3.11+, Node 20+.)

```bash
git clone https://github.com/bminhnemhoi/AISC2026_LIVEFIT.git && cd AISC2026_LIVEFIT
cp .env.example .env        # sửa POSTGRES_PASSWORD
docker compose up -d        # db + redis + migrate + api + web + backup
```

| Địa chỉ | Là gì |
|---|---|
| http://localhost:3000 | Trang chính — bấm **"Xem thử ngay (30 giây)"** |
| http://localhost:3000/chay-phien | Chạy một phiên thí nghiệm thật, 4 bước, không cần lệnh |
| http://localhost:3000/ket-qua | Kết quả gộp: tác động, KTC 95%, p, bảng MDE |
| http://localhost:8000/docs | Toàn bộ API (OpenAPI) |

Phát triển ngoài Docker & kiểm thử:

```bash
python -m venv .venv && .venv\Scripts\activate      # Windows
pip install -e ".[dev,server,ml]"
pytest -m "not slow"     # 157 test, < 10 giây
pytest -m slow           # gate thống kê Monte-Carlo (vài phút)
```

**Hướng dẫn kiểm thử từng khả năng** (mọi lệnh đã chạy thật):
[docs/HUONG-DAN-TEST.md](docs/HUONG-DAN-TEST.md)

## 7. Cấu trúc kho mã

```
├── src/livelift/
│   ├── core/
│   │   ├── assigner/        # bộ gán 2 tầng — TRÁI TIM KHOA HỌC (outer.py, inner.py)
│   │   ├── features.py      # sự kiện → tick 30s → outcome theo khối (+ đo lường được)
│   │   ├── quality.py       # QC sau phiên (6 kiểm tra, thông điệp tiếng Việt)
│   │   └── signals.py       # ma trận tín hiệu → năng lực ("đo được gì, thiếu gì")
│   ├── analysis/
│   │   ├── estimators.py    # randomization test · Fisher CI · Hájek · OLS-Lin · LATE
│   │   └── power.py         # MDE + hiệu chỉnh ĐO ĐƯỢC · within_session_cv · poisson_floor
│   ├── sim/                 # mô phỏng hiệu chỉnh KuaiLive + harness bias/coverage/A-A
│   ├── ingest/              # YouTube/Facebook chính thức · VOD replay · pii/ (BẮT BUỘC)
│   ├── nlp/                 # phân loại ý định (TF-IDF+LogReg đã train, fallback keyword)
│   ├── api/                 # FastAPI: sessions/schedule/actions/reports/replays/signals
│   └── migrations/          # SQL up/down, chạy bằng livelift-migrate
├── web/                     # Next.js 14: desk 3 vùng, host làm mù, replay, kết quả
├── collectors/tiktok_public # CÁCH LY — VLiveBench, không import ngược vào lõi
├── analysis/                # notebook + script hiệu chỉnh (calibration/, power/)
├── ops/                     # runbook phiên live, mẫu nhật ký, thư đối tác
├── docs/
│   ├── HUONG-DAN-TEST.md    # kiểm thử từng khả năng
│   ├── TONG-KET-DU-AN.md    # ĐÃ ĐẠT GÌ · CẦN LÀM GÌ · TẦM NHÌN  ← đọc thứ hai
│   ├── benchmarks/          # intent, KuaiLive — số sinh lại được
│   ├── research/            # 7 báo cáo nghiên cứu đa nguồn (trích dẫn đầy đủ)
│   └── incident-log.md      # 13 sự cố: root cause + gate chặn tái diễn
├── PREREGISTRATION.md       # tiền đăng ký — KHÓA trước chuỗi khẳng định (tuần 6)
├── HARNESS.md               # quy trình phát triển & quality gates  ← đọc thứ ba
└── docker-compose.yml
```

## 8. Quy trình phát triển (harness)

Chi tiết: [HARNESS.md](HARNESS.md). Tóm tắt triết lý:

- **Logic quyết định là hàm thuần** (gán, lọc, ước lượng) — test được không cần hạ tầng;
  I/O nằm ở rìa. Mọi RNG nhận seed tường minh; seed lịch gán lưu vào DB.
- **Quality gates CI đỏ = không merge:** 157 test nhanh · gate thống kê chậm (A/A,
  coverage, MDE-khớp-lực-thật) · recall PII ≥ 95% · cân bằng gán 1000 lịch ·
  **contract test web↔API** (trích mọi đường dẫn client gọi, đối chiếu OpenAPI — sinh
  ra từ một sự cố thật) · cách ly collectors · ruff.
- **Lỗi → root cause → test → sổ sự cố:** không vá triệu chứng. 13 sự cố trong
  `docs/incident-log.md` là *tài sản* của dự án — mỗi dòng có cơ chế, commit fix, và
  gate chặn tái diễn. Dữ liệu thí nghiệm hỏng thì **đánh dấu loại, không bao giờ sửa tay**.
- **Nghiên cứu → mã có trích dẫn:** mọi công thức trong `analysis/` dẫn nguồn (tác giả,
  năm); quyết định phương pháp đi qua phản biện đối kháng trước khi vào code.

## 9. Trạng thái & lộ trình

**Đọc bản đầy đủ — thành tựu, việc còn lại theo P0/P1/P2, tầm nhìn:**
[docs/TONG-KET-DU-AN.md](docs/TONG-KET-DU-AN.md)

Tóm tắt một dòng: *phần mềm ~85% cho mùa thi và đã tự chứng minh bằng số; đường găng
bây giờ là VẬN HÀNH (Page + App Review Meta, chốt hàng, đo giá quảng cáo thật, đối tác
dữ liệu) — những việc chỉ con người làm được, hạn chót gần nhất 14/09.*

## 10. Dành cho thành viên mới

Lộ trình 90 phút để nắm dự án:

1. **Chạy hệ thống** (§6) và bấm qua 6 trang — 15 phút.
2. Đọc [docs/TONG-KET-DU-AN.md](docs/TONG-KET-DU-AN.md) — bức tranh toàn cảnh — 15 phút.
3. Đọc §3 README này + `src/livelift/core/assigner/outer.py` (file được chú thích như
   một bài giảng nhỏ) — 20 phút.
4. Đọc [docs/incident-log.md](docs/incident-log.md) — hiểu *cách dự án này đối xử với
   lỗi*, đó là văn hóa làm việc — 15 phút.
5. Chạy `pytest -m "not slow"` rồi mở `tests/test_user_journey.py` — 4 hành trình
   người dùng là đặc tả hành vi sống — 15 phút.
6. Chọn việc trong TONG-KET §"Cần làm thêm", tạo nhánh `<mã-việc>-mô-tả`, làm theo
   HARNESS §1 — bắt đầu đóng góp.

Quy ước: commit tiếng Việt không dấu hoặc tiếng Anh, nhất quán trong một PR; `main`
luôn chạy được `docker compose up`; số liệu mới phải kèm cách sinh lại.

## 11. Pháp lý, quyền riêng tư & đạo đức

- **Luật 91/2025/QH15 + Nghị định 356/2025/NĐ-CP:** dữ liệu hành vi trên không gian
  mạng là dữ liệu nhạy cảm. LiveLift **khử nhận dạng tại ingest**: bình luận thô không
  bao giờ chạm đĩa; SĐT/email/mã đơn/địa chỉ/tên bị thay thế trước lệnh ghi; không lưu
  chuỗi hành vi theo cá nhân; salt xoay theo phiên cho mọi hash khử trùng lặp.
- **Ba nguồn dữ liệu hợp lệ:** API chính thức có ủy quyền · dữ liệu công khai ai xem
  cũng thấy (chat replay VOD — chỉ phân tích *quan sát*, không bao giờ gắn nhãn thí
  nghiệm) · dữ liệu nhóm tự tạo. TikTokLive (reverse-engineered) được cách ly, rủi ro
  ToS được thừa nhận công khai, tuyệt đối không gắn vào tài khoản shop.
- **Không thao túng:** không bình luận giả, không khan hiếm giả, không thổi người xem.

## 12. Tài liệu tham khảo

Thiết kế thí nghiệm: Bojinov, Simchi-Levi & Zhao (2023) *Design and Analysis of
Switchback Experiments*, Mgmt Sci 69(7) · Hu & Wager (2022) *Switchback Experiments
under Geometric Mixing*, arXiv:2209.00197 · Ni, Kalfountzou & Bojinov (2025), HBS WP
26-012 · Xiong, Chin & Taylor (2024), arXiv:2406.06768.
Suy diễn: Bojinov & Shephard (2019), JASA · Lin (2013), Ann. Appl. Stat. · Zhao & Ding
(2021), J. Econometrics · Chung & Romano (2013).
Dữ liệu & NLP: KuaiLive (SIGIR 2026), Zenodo 10.5281/zenodo.16565801 · ViSoBERT
(EMNLP 2023) · Nguyễn et al. (2026) S-O-R Impulsive Purchase, IMCOM.
Danh mục đầy đủ kèm ghi chú áp dụng/loại bỏ: `docs/research/` và `docs/research-log.md`.

---

*LiveLift — AISC'26. Một đội tự nêu giới hạn của mình bằng số được tin hơn một đội
khẳng định mọi thứ đều tốt.*
