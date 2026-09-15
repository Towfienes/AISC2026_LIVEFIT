# 02 — KIỂM TOÁN ĐỐI KHÁNG THEO RUBRIC BẢNG C

*Thực hiện 14/09/2026 trên kho `D:\AISC2026\livelift` tại HEAD `dd66b38`.
Phạm vi: kiến trúc · chất lượng mã · bộ kiểm thử · **tính trung thực của con số công bố** ·
mức độ "làm chủ" · rủi ro vận hành demo. KHÔNG chấm phần NLP/mô hình và
hạ tầng Docker/Caddy (agent khác phụ trách) — chỉ nêu khi nó chạm tới con số công bố.*

> **Luật của tài liệu này:** không có câu nào được viết từ tài liệu. Mỗi khẳng
> định kèm **lệnh đã chạy thật** và **kết quả dán nguyên**. Chỗ nào chỉ suy luận
> được mà chưa chạy được, ghi thẳng "chưa kiểm chứng".

---

## 0. PHÁN QUYẾT NGẮN

| Câu hỏi | Trả lời |
|---|---|
| **Sản phẩm có thật không?** | **CÓ.** 19.398 dòng mã nguồn + 20.432 dòng test, 42 commit từ 24/08 đến 14/09 với author date == committer date (không backdate), 0 merge, lịch sử liên tục. Không có dấu hiệu giả mạo lịch sử. |
| **Chạy được không?** | **CÓ, nhưng HEAD đang đỏ.** Ở trạng thái đầu kiểm toán: `pytest -m "not slow"` → **993 pass / 0 fail / 0 skip / 109,8s**; `pytest -m slow` → **16 pass / 0 fail / 740,3s**; `ruff check src tests` sạch; `tsc --noEmit` exit 0. Chạy lại lúc 14:09 (sau khi các agent khác thêm tệp): **1.010 test, 1 FAIL** — xem P0-0 và P0-5. |
| **Điểm yếu sẽ bị bắt?** | **CÓ, ba điểm chết.** (1) Con số A/A đầu bảng — thứ được trích ở 12+ nơi kể cả **kịch bản video** — **không tái lập được** ở HEAD; (2) **0 phiên thí nghiệm thật**, toàn bộ bằng chứng nhân quả là mô phỏng; (3) **42/42 commit một tác giả**, không nhánh, không PR — trong khi HARNESS.md tự cam kết "người thứ hai duyệt". |

**Tổng chấm độc lập: 50/80** (bảng §3). Thấp hơn bản tự chấm ở
`01-CHIEN-LUOC.md` (52/80) vì kiểm toán này **làm mất hiệu lực hai bằng chứng**
mà bản ấy dùng để cho điểm (chi tiết §1.2 và §2c).

---

## 1. CHẠY THẬT — SỐ THẬT ĐỐI CHIẾU SỐ CÔNG BỐ

### 1.1 Nhật ký lệnh (máy `Lenovo`, Windows 11, Python 3.12.6, pytest 9.1.1)

```
.venv/Scripts/python -m pytest -m "not slow" -q --junitxml=fast.xml
  → <testsuite errors="0" failures="0" skipped="0" tests="993" time="109.836">
  → EXIT=0   (đo lại lần 2: WALL=112s)

.venv/Scripts/python -m pytest -m slow -q --junitxml=slow.xml
  → <testsuite errors="0" failures="0" skipped="0" tests="16" time="740.341">
  → EXIT=0   (12 phút 20 giây)

.venv/Scripts/ruff check src tests            → All checks passed!
.venv/Scripts/ruff format --check src tests   → 121 files already formatted
web/node_modules/.bin/tsc --noEmit            → EXIT=0 (0 lỗi)
.venv/Scripts/python scripts/dong_bo_so_test.py --xem-truoc
  → pytest đếm được: 993 test nhanh · 16 cổng chậm · tổng 1009
  → Mọi nơi đã ghi đúng con số — không phải sửa gì.

# CHẠY LẠI SAU KHI KIỂM TOÁN THÊM 17 TEST (§7.3), 14:09
.venv/Scripts/python -m pytest -m "not slow" -q
  → <testsuite errors="0" failures="1" skipped="1" tests="1010" time="114.392">
  → EXIT=1  🔴 BỘ TEST NHANH ĐANG ĐỎ — chi tiết P0-0 dưới đây

# XÁC NHẬN lỗi ấy KHÔNG do kiểm toán này, 14:17
.venv/Scripts/python -m pytest -m "not slow" -q    --deselect tests/test_web_design_tokens.py::test_every_focusable_element_shows_a_focus_ring
  → <testsuite errors="0" failures="0" skipped="1" tests="1043" time="111.723">
  → EXIT=0  ✅ mọi thứ còn lại xanh (1 skip là cổng mới của §7.3, skip đúng)

# Lưu ý: số test đang là mục tiêu di động (993 → 1.010 → 1.043 trong 35 phút)
# vì các agent khác đang thêm tệp song song. Trước khi nộp phải CHỐT một lần
# rồi chạy scripts/dong_bo_so_test.py --ghi.

grep -cE '^\| [0-9]{2}/[0-9]{2}/[0-9]{4} \|' docs/incident-log.md  → 41
git log --oneline | wc -l                                          → 42
git shortlog -sne --all  → 42  LiveLift Team <ngobinhminh2322006@gmail.com>
```

### 1.2 Bảng đối chiếu — số THẬT vs số ĐANG CÔNG BỐ

| Con số | FACT-SHEET công bố | **Đo thật 14/09** | Phán quyết |
|---|---|---|---|
| Test nhanh | 993 | **993** | ✅ KHỚP |
| Cổng chậm | 16 "Monte-Carlo" | **16** (nhưng **3 là cổng build CSS**, không phải Monte-Carlo; skip khi máy thiếu `node_modules`) | ⚠️ nhãn sai |
| Tổng | 1.009 | **1.009** | ✅ KHỚP |
| Sự cố | 41 | **41 hàng** | ✅ KHỚP |
| **Tỷ lệ bác bỏ A/A** | **4,5%** (9/200), p nhị thức 0,872 | **3,50% (7/200)**, p = **0,4168** | 🔴 **KHÔNG TÁI LẬP** |
| **Độ phủ KTC 95%** | **95,5%** | **96,50% (193/200)** | 🔴 **KHÔNG TÁI LẬP** |

**Bằng chứng cho hai dòng đỏ.** Chạy lại đúng tham số của cổng
`tests/test_sim_validation.py:44` (`n_reps=200, n_sessions_per_rep=6,
session_minutes=60, SimParams(treatment_effect=0.0), n_draws=300, master_seed=11`):

```
TY LE BAC BO A/A : 0.0350  (7/200)   -> cong bo 4,5%
  binomtest p    : 0.4168             -> cong bo 0,872
  SE Monte-Carlo : 0.0130  => KTC ~95% [0.010, 0.060]
DO PHU KTC 95%   : 0.9650  (193/200) -> cong bo 95,5%
```

Hàm là **tất định** (chạy 2 lần ở `n_reps=40` cho kết quả bit-identical:
`reject 0.075 / 0.075`, `cov 0.925 / 0.925`), nên đây không phải nhiễu chạy máy.

**Nguồn của con số cũ:** `docs/benchmarks/nhat-ky-test.md:21` —
*"30/08 | … sau sửa: **4,5%** (9/200, p=0,872), độ phủ 95,5%"*. Tức con số là
của **30/08**. Từ đó tới nay ước lượng viên và mô phỏng đã đổi nhiều lần
(Q1 đổi biến kết quả 08/09, cân bằng transition 08/09, knob ICC P1-K2 09/09,
hai nhánh độ nhạy P3+P4 09/09, tìm kiếm khả thi chính xác 12/09). **Không ai
đo lại.**

**Vì sao trôi mà không ai biết:** cổng A/A chỉ in con số **khi đỏ** — thông
điệp nằm trong `assert`. Xanh thì im lặng. Đúng lớp lỗi mà đội đã dựng gate
để chống, nhưng gate này lại không tự chống được chính nó.

**Mức sát thương:** con số ấy đang nằm ở **12+ vị trí**, gồm
`README.md:47,191,192` · `docs/competition/FACT-SHEET.md:23,24` ·
`docs/competition/sang-tao-tre-2026/05-BAN-KE-KHAI.md:528` ·
`docs/competition/sang-tao-tre-2026/noi-dung.md:48,182,183` ·
`docs/competition/kich-ban-demo-7-phut.md:268` · và
**`07-KICH-BAN-2-VIDEO.md:24` — lời thoại video nộp thi**.
Hồ sơ nói "mọi con số sinh lại được bằng lệnh trong repo" (README:190). Một
giám khảo làm đúng câu đó sẽ ra số khác. Đây là trọng tâm 5 ("khả năng kiểm
chứng") bị đánh trúng bằng chính lời hứa của đội.

> **Lưu ý công bằng:** cả hai bộ số đều *hợp lệ về thống kê* (3,5% và 4,5% đều
> tương thích với mức danh nghĩa 5%; 96,5% và 95,5% đều tương thích 95%).
> Vấn đề **không phải khoa học sai** — mà là **số công bố không phải số mã
> nguồn sinh ra**. Sửa rất rẻ (chạy lại + thay số); để nguyên thì rất đắt.

### 1.3 Các con số lệch khác đã tìm thấy (đã sửa — xem §7)

| Chỗ | Trước kiểm toán | Nguồn thật |
|---|---|---|
| `README.md:203, 239` | "**18** sự cố" (2 nơi) | 41 hàng trong `docs/incident-log.md` |
| `README.md:50, 202` | "**14.903** bình luận" | lô 10/09 đã thay: **19.126** bình luận / 16 buổi / 7 ngành (`docs/benchmarks/live-fire-da-nguon.md:3`) |
| `README.md:199` | macro-F1 **0.870** nêu **một mình** | `docs/benchmarks/intent-classifier.md:9` in đậm: *"**Không được nêu 0.870 một mình**"* — trên chat thật là **0,271**, precision gộp 11% |
| `README.md:49` | lọc PII "recall **≥95%**" (hàm ý mọi loại) | `tests/test_pii_filter.py:53` — ngưỡng cho `name` chỉ là **≥70%** |
| `docs/TONG-KET-DU-AN.md:59` | "**611** test", "**24** sự cố" | 993 / 41 — **vẫn chưa sửa, xem P0-3** |
| `docs/HUONG-DAN-TEST.md:6` | "**119** test tự động pass" (27/08) | 993 — **vẫn chưa sửa, xem P0-3** |

→ Trong kho mã hiện có **5 câu trả lời khác nhau** cho câu hỏi "đội có bao
nhiêu test": 993 · 838 (`docs/benchmarks/kiem-chung-van-hanh.md:515`) ·
719/689 (`nhat-ky-test.md`) · 611 (`TONG-KET-DU-AN.md`) · 119
(`HUONG-DAN-TEST.md`). Với một đề tài lấy **kỷ luật bằng chứng** làm bản sắc,
đây là vết thương tự gây.

---

## 2. KIỂM CHỨNG BỐN TUYÊN BỐ THEN CHỐT (đọc mã + chạy, không đọc tài liệu)

### (a) Hàm gán ngẫu nhiên có tất định và tái tạo được không? — **ĐẠT**

Chạy độc lập ngoài bộ test:

```
seed42 == seed42 (assignment)     : True
seed42 == seed42 (jitter offsets) : True
seed42 != seed43                  : True
n_blocks: 16  n_on: 8  n_off: 8  n_redraws: 3  constraint_met: True
propensities distinct: [0.5]
design_hash(42) = f5be4aa261de4d5e (lặp lại y hệt) ; design_hash(43) = 73c74149874edc38
vector seed42: 0011100110100110
```

- `generate_schedule` (`src/livelift/core/assigner/outer.py:501`) là hàm thuần
  của `(DesignParams, seed)`; jitter cũng đi từ cùng RNG nên tái lập cả biên khối.
- `design_hash` (`outer.py:204`) băm **JSON chuẩn hoá** (`sort_keys=True`,
  separators cố định) → thứ tự khoá không đổi được hash. Cam kết thiết kế
  trước phát sóng là **có thật**, không phải lời hứa.
- Lập luận quan trọng nhất và **đúng**: `draw_assignments` (`outer.py:417`) giữ
  propensity biên = 0,5 **chỉ vì** rerandomization đối xứng dưới hoán vị ON↔OFF
  ở p=0,5; mã **cảnh báo tường minh** khi p≠0,5 (`outer.py:462-470`) thay vì
  im lặng ghi sai propensity. Đây là mức tự giác hiếm gặp.
- Cùng hàm ấy được dùng lại để vẽ phân bố tham chiếu
  (`analysis/estimators.py:201 _redraw_matrix`, nhận `design_params` **theo
  từng phiên**). Tuyên bố "vẽ lại bằng chính hàm gán production" **kiểm chứng được**.

**Rủi ro còn lại:** `random.Random(seed)` (Mersenne Twister) ổn định giữa các
bản CPython, nhưng tái lập **giữa máy** chưa được cố định bằng một test
vector nào. Đề xuất: thêm 1 test giữ cứng chuỗi `0011100110100110` cho
`(DesignParams(), seed=42, 90 phút)` — 3 dòng, chặn mọi thay đổi vô ý làm
lệch lịch gán của các phiên đã chạy.

### (b) Khoá kết quả theo tiền đăng ký có fail-closed thật không? — **ĐẠT** (nhưng đang TẮT)

Quét đối kháng độc lập: dựng app với `RESULTS_FREEZE_UNTIL=2999-01-01`, gieo
**4 phiên THẬT** (`is_demo=False`), gọi **toàn bộ 15 route GET** trong
`/openapi.json`, dò mọi khoá số có tên gợi suy diễn:

```
freeze = 2999-01-01 | real sessions: 4
GET routes: 15   (2 route có tham số → bỏ)
checked=13 leaks=0
summary: estimable=False ; estimate=None ci_low=None ci_high=None p_value=None
```

- `_results_freeze_reason` (`api/routes/reports.py:73`): chuỗi rỗng → không
  khoá; **sai định dạng → KHOÁ** (`reports.py:85-92`). Fail-closed đúng nghĩa.
- Áp ở **2 điểm**: `/experiment/summary` (`reports.py:501`) và
  `/sessions/{id}/bao-cao` (`reports.py:897`) — và kiểm **TRƯỚC khi tính**
  ước lượng, không phải lọc sau.
- Đường lách `is_demo` đã bị bịt và **có test**: `POST /sessions` ghim
  `is_demo=False` (`api/routes/sessions.py:97`), schema `SessionCreate` không
  có trường ấy, `tests/test_demo_that.py:68` khẳng định client gửi vào bị lờ.

**Nhưng:** `.env` đang chạy **không có** khoá `RESULTS_FREEZE_UNTIL` (thiếu
24/37 khoá so với `.env.example`), và `PREREGISTRATION.md:3` vẫn ghi
**"TRẠNG THÁI: BẢN MẪU — CHƯA KHOÁ"** với `<hash>` để trống. Cơ chế có thật
nhưng **chưa từng được bật**. Câu trả lời đúng trước hội đồng là: *"cơ chế
xong và có test; khoá vào 29/09–05/10 khi có số hiệu chỉnh tuần 3"*.

### (c) Lọc PII có đạt recall ≥95% không? — **ĐẠT TRÊN GIẤY, KHÔNG ĐỦ SỨC CHỊU PHẢN BIỆN**

Tính lại recall trực tiếp trên `tests/data/pii_comments.jsonl`:

| loại | nhãn | bắt | recall |
|---|---:|---:|---:|
| phone | 24 | 24 | 100,0% |
| email | **4** | 4 | 100,0% |
| order | **6** | 6 | 100,0% |
| address | 24 | 24 | 100,0% |
| social | **6** | 6 | 100,0% |
| bank | **4** | 4 | 100,0% |
| name | 12 | 12 | 100,0% |

Ba vấn đề, xếp theo sát thương:

1. **Cỡ mẫu.** Tổng **95 câu**. Với `email`/`bank` chỉ **n=4**, recall 100%
   có khoảng tin cậy Wilson 95% khoảng **[51%, 100%]**. Con số "≥95%" ở
   `email`, `bank`, `order`, `social` **không có ý nghĩa thống kê**.
2. **Train-on-test.** Docstring `tests/test_pii_filter.py:10` tự khai bộ dữ
   liệu *"bao gồm bộ thăm dò đối kháng từ đợt red-team 09/2026"* — tức
   ca lọt bị phát hiện được **thêm vào bộ test rồi mới sửa luật**. Recall
   trên văn bản **chưa từng thấy** là chưa biết. Đã có **19.126 bình luận
   thật** trong kho mà **không đo recall trên đó** (dù chỉ lấy mẫu 300 câu
   gán nhãn tay) — đây là khoảng trống lớn nhất của trọng tâm 3 và 8.
3. **Ngưỡng `name` là 70%, không phải 95%** (`tests/test_pii_filter.py:53`),
   trong khi README (trước khi sửa) nói "recall ≥95%". Đã sửa; nhưng nếu
   giám khảo đã đọc bản cũ thì đây là một câu hỏi khó.

**Điểm mạnh cần nói ra:** `scrub` trả về `PIIMatch` **chỉ có `kind/start/end`**,
không giữ `snippet` — và có test khẳng định điều đó
(`tests/test_pii_filter.py:97-98`). Tức bản thân kết quả lọc **không tái tạo
được** dữ liệu cá nhân. Đó là thiết kế đúng.

### (d) A/A 200 lặp có chạy lại ra đúng số không? — **KHÔNG** (xem §1.2)

Cổng **xanh** (`pytest -m slow` 16/16 pass, 740s) nhưng **giá trị đã trôi**:
3,50% thay vì 4,5%; 96,50% thay vì 95,5%. Chi tiết và bằng chứng ở §1.2.

---

## 3. BẢNG CHẤM 8 TRỌNG TÂM (độc lập, 1–10)

| # | Trọng tâm | Điểm | Bằng chứng (file:dòng / lệnh) | Giám khảo sẽ hỏi | Đội trả lời được? |
|---|---|---:|---|---|---|
| 1 | Cấp thiết, giá trị thực tiễn, tác động | **4** | Bài toán có bằng chứng bình duyệt (Xie–Sharma–Mehra POM 2025, chữ U ngược); `docs/competition/FACT-SHEET.md:41-46` có nguồn thị trường. Nhưng `FACT-SHEET.md:37`: **"Số phiên live THẬT đã chạy: 0"** | *"Đã có nhà bán nào dùng chưa?"* | ❌ **CHƯA** — 0 người dùng ngoài đội, 0 thư xác nhận, 0 phỏng vấn WTP (`FACT-SHEET.md:49-53` tự khai giá là "giả thuyết") |
| 2 | Khoa học, logic, phù hợp phương pháp | **9** | `core/assigner/outer.py:1-56` trích dẫn đúng và **nói rõ điều KHÔNG áp dụng được**; `outer.py:417` giữ propensity đúng và cảnh báo khi p≠0,5; `analysis/estimators.py:118,578` từ chối ước lượng khi một nhánh <2 khối; `docs/benchmarks/sim-validation-report.md:9` tự dán nhãn **"SKELETON"** | *"Vì sao không washout?"* · *"Vì sao redraw chứ không permute?"* | ✅ **ĐƯỢC** — có trong docstring + `docs/research/`. Trừ 1 điểm: **chưa có bản 1 trang cho giám khảo không chuyên thống kê** |
| 3 | Chất lượng & tính hợp lệ dữ liệu | **6** | Lọc PII chạy **trước khi ghi đĩa**; `PIIMatch` không giữ snippet (`tests/test_pii_filter.py:97`); 19.126 bình luận qua API chính thức; cách ly `collectors/` có cổng CI (`scripts/check_isolation.py`, chạy OK: *64 files scanned, 0 collectors imports*) | *"Recall 95% đo trên bộ nào? Ai gán nhãn?"* | ⚠️ **YẾU** — 95 câu do chính đội soạn, email/bank n=4; **chưa đo trên 19.126 câu thật** |
| 4 | **Mức độ LÀM CHỦ** | **5** | Mã thật, kiến trúc hàm-thuần đúng như HARNESS §1 tuyên bố (lõi không chạm DB/đồng hồ). **Nhưng:** `git log` → **42 commit, 1 author, 0 nhánh, 0 merge, 0 PR**; HARNESS.md §1 bước 7 hứa *"người thứ hai duyệt"* và §7 DoD hứa *"người thứ hai xác nhận"*; `mypy src` **crash** với chính cấu hình của repo | *"Ai viết phần nào? Hai bạn kia làm gì?"* · *"Chỗ này do AI sinh hay đội viết?"* | ❌ **CHƯA** — xem §5 |
| 5 | Kết quả thử nghiệm & **khả năng kiểm chứng** | **5** | 993+16 test xanh (đo thật); lưới SBC 4/4 xanh và **có răng** (`tests/test_sim_report.py:462` tiêm lỗi → ô đỏ); `estimable=False` có lý do tiếng Việt | *"Chạy lại lệnh của các bạn, số ra khác — giải thích?"* | ❌ **CHƯA** — **A/A 4,5% không tái lập (§1.2)**; 0 phiên ngẫu nhiên thật. Đây là điểm bị trừ nặng nhất |
| 6 | Phân tích, so sánh, tối ưu, xử lý rủi ro | **8** | **41 sự cố** có root cause + cột "gate mới" (`docs/incident-log.md`); tự tìm và sửa lỗi FATAL "NaN → significance" (52% phiên null bị tuyên có ý nghĩa); tự sửa công thức MDE 30,1%→20,1%; ánh xạ knob→ICC 400 phiên tách được hai cơ chế | *"Lỗi nào nghiêm trọng nhất các bạn từng mắc?"* | ✅ **ĐƯỢC, RẤT MẠNH** — sổ sự cố là tài sản lớn nhất của hồ sơ |
| 7 | Khả thi, triển khai, mở rộng, duy trì | **5** | Docker compose đủ 7 service + Caddy + 9 migration + backup; CI 5 job; `scripts/chay_local.py` một lệnh dọn cổng/build/kho; cổng CSS thật (`tests/test_web_css_gate.py`) | *"Cho chúng tôi link để tự mở"* | ❌ **CHƯA** — grep toàn hồ sơ: **không có URL triển khai công khai nào**. Thể lệ Vòng Chung kết §8: không truy cập được → **điểm vận hành có thể tính 0** |
| 8 | An toàn, bảo mật, đạo đức AI, trách nhiệm | **8** | Làm mù ở **cấp kiểu dữ liệu**: `HostState` đúng **4 trường** `['pinned_product','price','stock','elapsed_s']` (`api/schemas.py:259`) — kiểm chứng bằng introspect, không phải đọc docs; validator chặn "số dự báo + KTC" (`api/schemas.py:421`, thử lách 5 tổ hợp: **forecast+2CI / +ci_low / +ci_high đều bị TỪ CHỐI**, chỉ `experiment` mới được); `.env` **không** bị track trong git | *"Kiểm soát đầu ra thế nào?"* · *"Dữ liệu người xem lấy theo căn cứ gì?"* | ⚠️ **MỘT NỬA** — cơ chế kỹ thuật rất mạnh; nhưng thiếu **bảng nguồn × giấy phép × căn cứ pháp lý** và chưa xử lý dứt `collectors/tiktok_public` |

**Tổng: 50/80.**

> Chênh so với bản tự chấm `01-CHIEN-LUOC.md` (52/80): kiểm toán này hạ
> **trọng tâm 5 từ 7 → 5** (số A/A không tái lập, tức chính "khả năng kiểm
> chứng" bị thủng) và **trọng tâm 3 từ 7 → 6** (recall PII không đủ cỡ mẫu và
> là train-on-test), bù lại nâng **trọng tâm 8 từ 7 → 8** vì hai cơ chế liêm
> chính cấp kiến trúc đã được kiểm chứng bằng probe đối kháng chứ không phải
> bằng lời.

---

## 4. MƯỜI LĂM CÂU HỎI HIỂM NHẤT (xếp theo sát thương)

| # | Câu hỏi | Câu trả lời trung thực hiện có |
|---:|---|---|
| 1 | *"Tôi vừa chạy lại cổng A/A của các bạn. Ra 3,5% chứ không phải 4,5%. Số nào đúng?"* | 🔴 **CHƯA CÓ CÂU TRẢ LỜI.** Phải chạy lại và thay số ở 12+ nơi **trước khi nộp**. Câu trả lời đúng sau khi sửa: *"3,50% (7/200), p nhị thức 0,417 — 4,5% là số đo ngày 30/08, mã đã đổi 5 lần sau đó, chúng em đã cập nhật."* |
| 2 | *"Các bạn đã chạy được bao nhiêu phiên thí nghiệm ngẫu nhiên thật?"* | ✅ **CÓ** — **0**, và `FACT-SHEET.md:37` ghi thẳng "không tuyên bố khác đi cho đến khi có". Trả lời: hạ tầng đo đã xong + kiểm chứng trên mô phỏng hiệu chỉnh; 16 buổi live thật đã chạy qua API ở chế độ **quan sát**. Nhưng phải **chủ động nói trước**, không đợi bị hỏi. |
| 3 | *"42 commit, một tác giả 'LiveLift Team'. Hai bạn kia đóng góp gì?"* | 🔴 **CHƯA CÓ CÂU TRẢ LỜI.** Không có `CONTRIBUTORS.md`, không có bảng phân công, không có nhánh/PR. Xem §5. |
| 4 | *"Phần nào do AI sinh, phần nào đội tự viết?"* (Điều 5 §4–6 — điều khoản loại đội) | 🔴 **CHƯA CÓ CÂU TRẢ LỜI.** Bản kê khai AI chưa hoàn tất; Prompt Log mới có script xuất (`scripts/xuat_prompt_log.py`, chưa chạy ra bản nộp). |
| 5 | *"Recall PII 95% đo trên bộ nào? Ai gán nhãn? Bao nhiêu mẫu?"* | ⚠️ **NỬA VỜI.** Trả lời đúng: *"95 câu do đội soạn, gồm cả ca đối kháng đội tự tìm; email/bank chỉ n=4 nên con số ấy không có sức thống kê; chưa đo trên chat thật — đây là việc P0 tuần này."* Nói trước thì thành điểm trung thực. |
| 6 | *"Mô hình ý định của các bạn tốt không?"* | ✅ **CÓ, VÀ RẤT MẠNH** — 0,870 trên bộ biên soạn nhưng **0,271 trên chat thật**, precision gộp 11%, precision theo buổi dao động **1,3%→67,9%** theo tỷ lệ nền (`docs/benchmarks/live-fire-da-nguon.md`). Đội **tự đo, tự công bố số xấu**. Đây là câu trả lời ăn điểm nếu nói chủ động. |
| 7 | *"Cho chúng tôi link sản phẩm đang chạy để tự mở."* | 🔴 **CHƯA CÓ CÂU TRẢ LỜI.** Không có URL công khai. Vòng Chung kết yêu cầu chạy ổn định ≥48h trước kiểm tra. |
| 8 | *"MDE 20,1% đo ở điều kiện nào? Điều kiện đó có giống thực tế không?"* | ✅ **CÓ, nhưng đau** — `FACT-SHEET.md:34-35`: đo ở mô phỏng **45–62 người xem đồng thời**, trong khi đo thật chỉ **5–15**. Tức MDE thật sẽ tệ hơn nhiều. Đội đã tự ghi; phải nói kèm, đừng để giám khảo tự phát hiện. |
| 9 | *"HARNESS.md nói mỗi PR có người thứ hai duyệt. `git log` không có PR nào."* | 🔴 **CHƯA CÓ CÂU TRẢ LỜI.** Hoặc sửa HARNESS.md cho khớp thực tế, hoặc bắt đầu làm PR từ hôm nay. Để lệch là tự tố cáo quy trình. |
| 10 | *"Tiền đăng ký đã khoá chưa? Cho xem commit khoá."* | ✅ **CÓ** — `PREREGISTRATION.md:3` ghi rõ "BẢN MẪU — CHƯA KHOÁ", dự kiến 29/09–05/10. Trung thực. Nhưng phải nói kèm: cơ chế cưỡng chế `RESULTS_FREEZE_UNTIL` **đã có và có 3 test** (`tests/test_api_flow.py:374,400,411`). |
| 11 | *"Switchback trong một phiên thì đơn vị độc lập ở đâu? Hiệu ứng lưu xử lý sao?"* | ✅ **ĐƯỢC** — burn-in lúc phân tích thay washout (Hu–Wager 2022), độ nhạy b∈{0..3} phút; và **đo được cái giá**: bán rã 120s → coverage 84%, 180s → 60% (`FACT-SHEET.md:36`). Trung thực hơn mức trung bình rất nhiều. |
| 12 | *"Vì sao propensity ghi 0,5 khi đã rerandomization? Điều kiện hoá làm lệch chứ?"* | ✅ **ĐƯỢC** — `outer.py:14-24` + `417-446`: ở p=0,5 quy tắc chấp nhận đối xứng dưới hoán vị ON↔OFF nên biên giữ đúng 0,5; ở p≠0,5 mã **cảnh báo** và cấm dùng p làm propensity IPW. Câu trả lời tốt nhất trong toàn bộ hồ sơ. |
| 13 | *"Bộ test 993 có bao nhiêu là test thật, bao nhiêu là test tài liệu/giao diện?"* | ⚠️ **CHƯA ĐẾM.** Có ít nhất 5 tệp gate tài liệu/CSS/design-token (`test_docs_huong_dan.py`, `test_web_css_gate.py`, `test_web_design_tokens.py`, `test_web_desk_*`). Nên chuẩn bị bảng phân nhóm test theo mục đích. |
| 14 | *"`collectors/tiktok_public` là gì? Có vi phạm ToS không?"* | ⚠️ **NỬA VỜI** — có cổng CI cách ly (đã chạy: 0 import ngược) và `docs/benchmarks/tiktok-collector-2026-09.md`. Nhưng chưa có quyết định dứt khoát "gỡ khỏi bản nộp hay giữ kèm tuyên bố không dùng". |
| 15 | *"Bộ ước lượng của các bạn hơn baseline nào? Ablation đâu?"* | 🔴 **CHƯA CÓ CÂU TRẢ LỜI** cho đúng MẪU 3 mục 9. Vật liệu có sẵn (Hájek IPW / OLS-Lin / RI+Fisher, bảng so sánh ở `noi-dung.md:264`) nhưng chưa dựng thành một mục **so sánh baseline + ablation** độc lập. |

---

## 5. ĐỐI CHIẾU "LÀM CHỦ" (Điều 5 §4–6)

Thể lệ đòi đội chứng minh **hiểu · kiểm chứng · chỉnh sửa · vận hành · chịu
trách nhiệm** với mã do AI hỗ trợ sinh. Bằng chứng hiện có, chấm thẳng:

| Yêu cầu | Bằng chứng có | Thiếu |
|---|---|---|
| **Hiểu** | Docstring lõi thống kê trích dẫn nguồn **và nêu điều KHÔNG áp dụng được** — dấu hiệu đọc thật, không chép (`outer.py:9-13,25-42`) | Không có bảng "ai hiểu phân hệ nào" |
| **Kiểm chứng** | 41 sự cố có root cause; cổng SBC **có răng**; A/A có phân tích **lực của chính cổng** (`test_sim_validation.py:53-59`) | Chính con số A/A đã trôi mà cổng không phát hiện |
| **Chỉnh sửa** | Nhiều lần tự sửa tận gốc: NaN→significance, MDE 30,1%→20,1%, `_transition_requirement` đổi từ chặn xấp xỉ sang tìm kiếm chính xác (`outer.py:386-411`) | — |
| **Vận hành** | `scripts/chay_local.py`, sổ tay sự cố, cổng CSS, kịch bản demo 7 phút | Chưa deploy công khai |
| **Chịu trách nhiệm** | Công bố số xấu của chính mình (0,271; coverage 60%; 5–15 người xem) | **42/42 commit một danh tính**; không PR; chưa kê khai AI |

### Vùng mã đội KHÓ giải thích nếu bị hỏi

| Vùng | Vì sao khó | Đề xuất |
|---|---|---|
| `api/routes/reports.py:384 experiment_summary()` — **263 dòng, độ phức tạp nhánh ~35** | Hàm **đông nhất kho mã** lại đúng là hàm phục vụ con số đầu bảng. Một câu "giải thích luồng của hàm này" là đủ để lộ chỗ nào không nắm | **Tách 3 hàm thuần**: `_chon_phien()` · `_kiem_khoa()` · `_dung_bang_luc()`. Không đổi hành vi, có test bao sẵn |
| `core/assigner/outer.py:285 _acceptance_set_nonempty()` — tìm kiếm trạng thái có ngân sách | Toán tổ hợp, không trực giác. Nhưng **có test đối chiếu vét cạn** (`test_schedule_config_matrix.py`, 31,5s) | Giữ nguyên. Thêm **5 dòng giải thích bằng ví dụ 5 khối** vào docstring — ví dụ đã có ở `outer.py:397-404`, chỉ cần đưa lên đầu |
| `api/store.py` — **1.943 dòng**, tệp lớn nhất | Không ai nắm hết một tệp 2k dòng | Tách theo bảng (`sessions` / `events` / `shortlinks`) — **hoãn sau vòng thi**, rủi ro hồi quy cao |
| `ingest/pii/filter.py:102 _find_spans()` — không docstring, 24 lượt regex | Đây là hàm có **hệ quả pháp lý**. Thực tế mã **rất dễ đọc** (danh sách phẳng), độ phức tạp ~26 là ảo | Thêm docstring 6 dòng nói **thứ tự ưu tiên** và **vì sao `p5` cần ngữ cảnh còn `q7` thì không** — câu hỏi chắc chắn bị hỏi |
| `nlp/eval_intent.py` — **941 dòng, mới, 4 lỗi ruff đang đỏ** | Không nằm trong cây thư mục README; đang **làm hỏng cổng lint CI** | Agent NLP xử lý; nhưng **phải sửa trước khi nộp** (xem P0-5) |

### Khoảng cách giữa harness TUYÊN BỐ và harness THỰC THI

| HARNESS.md nói | CI thực tế (`.github/workflows/ci.yml`) | Thực tế kho mã |
|---|---|---|
| §1.6 "tự soát ruff **+ mypy**" | **Không có job mypy** | `mypy src` **crash** với `python_version=3.11` trong `pyproject.toml` (numpy stub đòi 3.12). Ép `--python-version 3.12` → **22 lỗi** (đa số là narrowing giả, nhưng gate coi như chưa từng chạy) |
| §1.7 "PR — người thứ hai duyệt" | — | 0 nhánh, 0 merge, 0 PR |
| §2 "ruff check" | `ruff check src tests` | **`scripts/` và `analysis/` không được lint** — có 3 lỗi E501 + 1 RET504 đang tồn tại ngoài tầm cổng |
| §2 "Migration up→down→up trên DB sạch" | **Không có job DB** | Marker `db` tồn tại nhưng **0 test dùng nó**; lần chạy 993 test có **0 skipped** → đường Postgres chưa bao giờ được CI xác nhận |

---

## 6. RỦI RO VẬN HÀNH DEMO (thể lệ: hỏng do lỗi chủ quan → **điểm vận hành có thể tính 0**)

| # | Rủi ro | Bằng chứng | Xử lý |
|---:|---|---|---|
| **1** | **Web gọi sai địa chỉ API nếu demo bằng Docker.** `.env` đang có `NEXT_PUBLIC_API_URL=http://localhost:8000`, nhưng `docker-compose.yml:62-66` **không publish cổng 8000** (mọi thứ qua Caddy). Docker Compose tự nạp `.env` nên biến này **đè** mặc định `http://localhost/api` ở `docker-compose.yml:83,87`. Giao diện sẽ mở được nhưng **mọi lời gọi API hỏng**, im lặng | `.env` (dòng 13) vs `.env.example:68` | Sửa `.env` thành `http://localhost/api` rồi **`docker compose build web`** (biến `NEXT_PUBLIC_*` nhúng lúc build). Hoặc demo bằng `scripts/chay_local.py` như kịch bản 7 phút đang làm |
| **2** | **`.env` thiếu 24/37 khoá** so với `.env.example`, trong đó có `STORE_BACKEND` — đúng nguyên nhân gốc của sự cố 25/08 ("API báo `store_backend=memory` dù có `DATABASE_URL`") | `comm` giữa hai tệp | Copy lại từ `.env.example`, điền secret, giữ nguyên phần còn lại |
| **3** | ✅ **ĐÃ SỬA** — bước (2) của checklist 15 phút trước hội đồng (`kich-ban-demo-7-phut.md:23`) **crash**: `scripts/dong_bo_so_test.py` ném `UnicodeEncodeError` trên console cp1252 trước khi in được con số | Tái hiện được; nay chạy ra `993 test nhanh · 16 cổng chậm · tổng 1009` | Xem §7 |
| **4** | ✅ **ĐÃ SỬA** — 3 script khác cùng lỗi: `don_phien_demo_trung.py` (`--help` chết hẳn), `kiem_tra_facebook.py`, **`xuat_prompt_log.py`** (script xuất Prompt Log — hạng mục nộp **bắt buộc** theo MẪU 3 mục 13) | `--help` của cả 3 nay exit 0 | Xem §7 |
| **5** | **Không có môi trường trực tuyến.** Demo hiện chỉ chạy `127.0.0.1`. Thể lệ Vòng Chung kết §8 đòi chạy ổn định ≥48h trước kiểm tra | grep toàn hồ sơ: 0 URL triển khai | Deploy HTTPS + `/health` + uptime monitor (ước 4 giờ, đã nằm ở đòn bẩy #2 của `01-CHIEN-LUOC.md`) |
| **6** | **3 cổng chậm cần `npm install`**; thiếu `node_modules` thì **skip** chứ không đỏ (`tests/test_web_css_gate.py:57-61`) — tốt về thiết kế, nhưng nghĩa là trên máy giám khảo `pytest -m slow` báo **13 passed, 3 skipped**, không phải "16 cổng Monte-Carlo" | đọc mã | Sửa nhãn badge/FACT-SHEET: "13 cổng thống kê + 3 cổng build web" |
| 7 | Job phân tích VOD **chạy in-process** — quá 3–4 job song song là nghẽn | `TONG-KET-DU-AN.md:101` (đội tự khai) | Chỉ chạy 1 job trong demo; đã có trong kịch bản |
| 8 | Đã có sẵn lớp chống: dọn cổng, dọn `.next` thừa, đo kho sống/chết, cổng CSS thật — **39 test** trong `tests/test_khoi_dong_sach.py` | đọc mã | Không cần làm gì; **nên khoe** |

---

## 7. NHỮNG GÌ KIỂM TOÁN NÀY ĐÃ SỬA

Tất cả đều nhỏ, an toàn, và có test chứng minh. **Không** đụng mã NLP,
Docker, Caddy, hay bất kỳ tệp hồ sơ nào của agent khác.

### 7.1 Sửa crash thật (4 tệp)

Sự cố 27/08 đã có cách sửa chốt trong kho (`livelift.console.configure`, dùng
ở 15 tệp) nhưng **4 script quên gọi** → chết bằng `UnicodeEncodeError` trên
console Windows cp1252:

| Tệp | Triệu chứng tái hiện được | Sửa |
|---|---|---|
| `scripts/dong_bo_so_test.py` | **bước (2) checklist demo trước hội đồng** — chết trước khi in con số | `configure()` ở dòng đầu `main()`, **trước `parse_args`** (đúng quy ước `chay_local.py:625`) |
| `scripts/don_phien_demo_trung.py` | `--help` chết hẳn (`\u1ecd` position 121) | như trên |
| `scripts/kiem_tra_facebook.py` | `print(ket_qua.van_ban())` — báo cáo tiếng Việt | như trên |
| `scripts/xuat_prompt_log.py` | script xuất **Prompt Log** (MẪU 3 mục 13, bắt buộc) | như trên |

Kiểm chứng: `--help` của cả 4 nay **exit 0**;
`dong_bo_so_test.py --xem-truoc` → `993 test nhanh · 16 cổng chậm · tổng 1009`.

### 7.2 Sửa số công bố sai trong `README.md` (5 chỗ)

| Dòng | Trước | Sau |
|---|---|---|
| 49 | "recall ≥95%" · "F1 0.87" | nói rõ **95 câu**, `name` ngưỡng **≥70%**, và **cặp 0,870/0,271** |
| 50 | "14.903 bình luận" | **19.126 · 16 buổi · 7 ngành** (lô 10/09) |
| 199 | "macro-F1 **0.870** vs baseline 0.653" | thêm **"NHƯNG 0,271 trên chat thật, precision gộp 11%"** |
| 202 | "262 phút, 14.903 bình luận" | **19.126 · 16 buổi · 7 ngành**, ghi rõ lô cũ đã bị thay |
| 203, 239 | "**18** sự cố" (2 nơi) | **41** |

### 7.3 Thêm cổng chặn tái diễn — `tests/test_so_cong_bo.py` (mới, 17 test)

Nguyên tắc: **không hằng số chép tay**; mỗi test so README với **nguồn** của
con số, nên lô đo mới về là gate tự đòi sửa README.

1. Số sự cố trong README == số hàng bảng trong `docs/incident-log.md`
2. Số bình luận live-fire == số ở đầu `docs/benchmarks/live-fire-da-nguon.md`
   (số lô cũ chỉ được xuất hiện kèm chữ "cũ")
3. README **không bao giờ** nêu 0,870 mà thiếu 0,271 trên cùng dòng — nâng
   chính quy tắc in đậm của `intent-classifier.md` thành cổng tự động
4. (parametrize 14 script) mọi script có chuỗi tiếng Việt phải đặt lại
   encoding stdout — chặn lớp lỗi §7.1 tái diễn

Kết quả: `17 tests, 0 failures, 1 skipped` (skip đúng: `check_isolation.py`
chỉ in tiếng Anh). `ruff check` + `ruff format` sạch.

---

## 8. P0 — PHẢI SỬA TRƯỚC KHI NỘP (xếp theo thứ tự làm)

| # | Việc | Vì sao P0 | Công | Ai |
|---:|---|---|---|---|
| **P0-0** | **Bộ test nhanh đang ĐỎ ngay lúc này.** `tests/test_web_design_tokens.py::test_every_focusable_element_shows_a_focus_ring` đỏ vì **3 tệp mới chưa track** — `web/src/app/error.tsx:70` `<button>`, `global-error.tsx:104` `<button>`, `not-found.tsx:37` `<Link>` — thiếu token `focus-ring` (WCAG 2.4.7). Không phải do kiểm toán này (các tệp do agent triển khai thêm song song, `git status` → `??`) | Badge CI đỏ + `pytest` đỏ là hai thứ giám khảo kiểm đầu tiên. Sửa = thêm `focus-ring` vào 3 thẻ | 10 phút | agent triển khai |
| **P0-1** | **Chạy lại cổng A/A rồi thay số ở MỌI nơi.** Số đúng ở HEAD: **bác bỏ 3,50% (7/200), p nhị thức 0,4168, độ phủ 96,50% (193/200)**. Sửa: `README.md:47,191,192` · `FACT-SHEET.md:23,24` · `05-BAN-KE-KHAI.md:528` · `noi-dung.md:48,182,183` · `kich-ban-demo-7-phut.md:268` · `01-CHIEN-LUOC.md:179,327,344,614` · **`07-KICH-BAN-2-VIDEO.md:24` (lời thoại video!)** · `E6-01-thuyet-minh-khung.md:38` · `intent-classifier.md:43` | Hồ sơ tự hứa "sinh lại được bằng lệnh". Giám khảo làm đúng câu đó ra số khác → **thủng trọng tâm 5**, và là đúng thứ Điều 5 gọi là "dữ liệu thử nghiệm không đúng" | 30 phút (đã có lệnh + số ở §1.2) | TN |
| **P0-2** | **Bắt cổng A/A IN con số ra**, không chỉ assert. Ghi vào `docs/benchmarks/` một dòng "đo lại ngày … = …". Không có bước này thì số sẽ trôi lại sau lần sửa mã tới | Root cause của P0-1: gate xanh thì im lặng | 30 phút | TN |
| **P0-3** | **Đồng bộ nốt 2 tài liệu còn lệch**: `TONG-KET-DU-AN.md:59` (611 test, 24 sự cố → 993, 41) và `HUONG-DAN-TEST.md:6` (119 test → 993). Mở rộng `scripts/dong_bo_so_test.py` ghi vào cả hai | Kho mã đang có **5 câu trả lời** cho "bao nhiêu test" | 30 phút | BM |
| **P0-4** | **Gói liêm chính tác giả.** Từ hôm nay commit bằng `user.name/email` thật của từng người; thêm `CONTRIBUTORS.md` + `docs/phan-cong.md` (ai làm phân hệ nào); xuất **Prompt Log** bằng `scripts/xuat_prompt_log.py` (nay chạy được); hoàn tất **bản kê khai AI** có cột *đội tự xây / AI sinh / kế thừa nguồn mở*. **KHÔNG viết lại lịch sử git cũ** | Điều 5 §4–6 là **điều khoản loại đội**. 42/42 commit một danh tính là câu hỏi số 3 và số 4 ở §4 | 1 ngày | Cả 3 |
| **P0-5** | **Sửa 4 lỗi ruff đang đỏ trong `src/livelift/nlp/eval_intent.py`** (UP035 + 3×E501). Hiện `ruff check src tests` **thất bại** → job `lint` của CI đỏ → badge CI trên README đỏ khi giám khảo mở | Badge đỏ ở dòng 12 README là ấn tượng đầu tiên | 10 phút | agent NLP |
| **P0-6** | **Sửa `.env`**: `NEXT_PUBLIC_API_URL=http://localhost/api`, bổ sung 24 khoá thiếu từ `.env.example` (đặc biệt `STORE_BACKEND`, `RESULTS_FREEZE_UNTIL`) | Demo bằng Docker sẽ hỏng im lặng (§6.1) | 15 phút | KS |
| **P0-7** | **Đo recall PII trên chat THẬT**: lấy mẫu 300 câu từ 19.126 bình luận đã có, gán nhãn tay, báo recall kèm khoảng tin cậy. Dù số xấu vẫn công bố | Câu hỏi số 5 ở §4; và là bằng chứng duy nhất cho trọng tâm 3 & 8 trên dữ liệu chưa từng thấy | nửa ngày | NC |
| **P0-8** | **Sửa nhãn "16 cổng Monte-Carlo"** → "13 cổng thống kê + 3 cổng build web (skip nếu thiếu node)" | Giám khảo chạy ra "13 passed, 3 skipped" | 10 phút | TN |
| **P0-9** | **Đồng bộ HARNESS.md với thực tế**: hoặc bỏ câu "PR — người thứ hai duyệt" / "mypy", hoặc bật chúng từ hôm nay. Thêm job `mypy` vào CI (và sửa `python_version` → `3.12` trong `pyproject.toml`, vì `mypy src` đang crash) | Câu hỏi số 9 ở §4 — quy trình tuyên bố mà không thực thi là tự tố cáo | 1 giờ | KS |

### P1 (nên có, không chặn nộp)

- Thêm **test vector cố định** cho lịch gán (`seed=42` → `0011100110100110`) — chặn lệch tái lập giữa máy.
- Tách `experiment_summary()` (263 dòng) thành 3 hàm thuần — giảm rủi ro "không giải thích được".
- Thêm docstring cho `_find_spans()` (thứ tự ưu tiên + vì sao `p5` cần ngữ cảnh).
- Mở rộng `ruff check` sang `scripts/` và `analysis/` (đang có 4 lỗi ngoài tầm cổng).
- Viết MẪU 3 **mục 9 (baseline + ablation)** thành mục độc lập.

---

## 9. NHỮNG GÌ KIỂM TOÁN NÀY XÁC NHẬN LÀ THẬT (nên khoe, đừng khiêm tốn)

Kiểm chứng bằng chạy/probe, không bằng đọc tài liệu:

- **Lịch gán tất định + cam kết SHA-256 trước phát sóng** — tái lập bit-identical, `design_hash` đổi theo seed.
- **Propensity 0,5 đúng về mặt toán** dưới rerandomization, **và mã cảnh báo khi lập luận ấy hỏng** (p≠0,5). Đây là mức tự giác vượt chuẩn sinh viên.
- **Khoá tiền đăng ký fail-closed** — quét 13 route GET với 4 phiên thật: **0 rò rỉ**; `estimable=False`, mọi trường suy diễn `None`.
- **Làm mù host ở cấp kiểu dữ liệu** — `HostState` đúng 4 trường, xác nhận bằng introspect.
- **Validator chặn "số dự báo + khoảng tin cậy"** — thử lách 3 tổ hợp, **cả 3 bị từ chối** kèm thông điệp tiếng Việt nêu đúng quy tắc E2-04.
- **Cách ly `src/` ↔ `collectors/`** — cổng CI chạy thật: 64 tệp quét, 0 import ngược.
- **Sổ sự cố 41 mục có root cause + cột "gate mới"** — tài sản mạnh nhất của hồ sơ cho trọng tâm 6.
- **Cổng SBC có răng** — tiêm lỗi vào thì ô chuyển ĐỎ (`tests/test_sim_report.py:462`), tức cổng không phải trang trí.
- **Tự công bố số xấu**: 0,271 trên chat thật · coverage 60% dưới hiệu ứng lưu dài · 5–15 người xem thay vì 80 · **0 phiên thật**. Một đội tự nêu giới hạn bằng số được tin hơn một đội khẳng định mọi thứ đều tốt.
