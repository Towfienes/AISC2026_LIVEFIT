# BÁO CÁO ĐÁNH GIÁ SAU TRIỂN KHAI (POST-IMPLEMENTATION REVIEW) — AISC 2026 VÒNG 2

> **Mã tài liệu:** `AISC-R2-PIR-20260921`
> **Thời điểm review:** 21/09/2026
> **Nhánh kiểm toán:** `tien/aisc-round2` (Base commit `08be6ae`)
> **Chế độ kiểm toán:** REVIEW ONLY — Không sửa mã nguồn dự án, không `git add`, không commit, không push, không đổi nhánh, không chạy lệnh phá hủy.
> **Đối tượng review:** Toàn bộ working-tree diff và các file untracked do Codex triển khai theo kế hoạch `docs/competition/aisc-round2/CODEX-IMPLEMENTATION-PLAN.md`.

---

## MỤC LỤC

1. [TỔNG QUAN VÀ PHẠM VI REVIEW](#1-tổng-quan-và-phạm-vi-review)
2. [KIỂM TOÁN CHI TIẾT THEO 8 TRỌNG TÂM](#2-kiểm-toán-chi-tiết-theo-8-trọng-tâm)
   - 2.1. Gói tài liệu AISC Round 2 Package
   - 2.2. Giao diện trang `/ket-qua`
   - 2.3. Khối đối chứng (Control Block UX)
   - 2.4. Công cụ kiểm tra trước demo (`round2_demo_check.py`)
   - 2.5. Hệ thống kiểm thử mới và sửa đổi (Tests)
   - 2.6. Kỷ luật ranh giới và phạm vi (Scope Enforcement)
   - 2.7. Đánh giá 5 lỗi Fast Test NLP (Baseline vs Regression)
   - 2.8. An toàn bảo mật và phát hành (Security / Release)
3. [MA TRẬN KẾT QUẢ THỰC THI KIỂM CHỨNG (VERIFICATION MATRIX)](#3-ma-trận-kết-quả-thực-thi-kiểm-chứng-verification-matrix)
4. [BẢNG PHÂN LOẠI PHÁT HIỆN (FINDINGS CLASSIFICATION)](#4-bảng-phân-loại-phát-hiện-findings-classification)
   - BLOCKER
   - P0 FIX
   - P1
   - SAFE / APPROVED
   - NEEDS BASELINE COMPARISON / PRE-EXISTING BASELINE
5. [KẾT LUẬN VÀ VERDICT](#5-kết-luận-và-verdict)

---

## 1. TỔNG QUAN VÀ PHẠM VI REVIEW

Kiểm toán độc lập tiến hành rà soát toàn diện các thay đổi trong working-tree của Codex trên nhánh `tien/aisc-round2`.

### Hiện trạng Working Tree:
- **Files modified / tracked (6 files):**
  - `docs/competition/aisc-round2/CODEX-IMPLEMENTATION-PLAN.md` (Kế hoạch triển khai)
  - `web/src/app/ket-qua/page.tsx` (CTA Demo Vàng trung thực cho state chưa đủ điều kiện)
  - `web/src/components/BlockClock.tsx` (Copy giải thích khối đối chứng)
  - `tests/test_web_ket_qua.py` (Regression test cho `/ket-qua`)
  - `tests/test_web_desk_layout.py` (Cập nhật copy assertion cho layout desk)
  - `tests/test_web_desk_v3.py` (Cập nhật assertion cho `actionLockReason`)
- **Files untracked (9 files):**
  - `docs/competition/aisc-round2/README.md`
  - `docs/competition/aisc-round2/FACT-SHEET.md`
  - `docs/competition/aisc-round2/ROADMAP.md`
  - `docs/competition/aisc-round2/DEMO-GATES.md`
  - `docs/competition/aisc-round2/PITCH.md`
  - `docs/competition/aisc-round2/QNA.md`
  - `docs/competition/aisc-round2/FREEZE.md`
  - `scripts/round2_demo_check.py`
  - `tests/test_round2_demo_check.py`

---

## 2. KIỂM TOÁN CHI TIẾT THEO 8 TRỌNG TÂM

### 2.1. Gói tài liệu AISC Round 2 Package

Rà soát toàn bộ 7 file tài liệu độc lập trong `docs/competition/aisc-round2/`:

1. **Tính xác thực của các chỉ số số liệu (Numerical Claims):**
   - Mọi số liệu trong `FACT-SHEET.md` đều có cột **Nguồn**, **Lệnh tái lập** và **Ngày xác minh**.
   - Con số `1.811 test nhanh`, `17 cổng Monte-Carlo`, `10 test trình duyệt` đã được xác minh bằng chính các lệnh collect của pytest và `scripts/dong_bo_so_test.py --xem-truoc`.
   - Số lượng `60 sự cố` khớp chính xác với lệnh đếm dòng dữ liệu trên `docs/incident-log.md` (`awk` filter chuẩn).
   - Tỷ lệ A/A `3,50%`, KTC độ phủ `96,50%`, bias `-0,84%` lấy từ `docs/benchmarks/so-hieu-chuan.json`, bảo đảm tính nhất quán với đính chính khoa học ngày 14/09/2026.
2. **Tách biệt tuyệt đối AISC vs Sáng tạo trẻ:**
   - Không xuất hiện bất kỳ từ khóa hay nội dung nào liên quan đến Hackathon 48h, Bảng C, ĐH Tôn Đức Thắng, nộp Prompt Log, hay Mẫu 3 TW Đoàn.
   - `README.md` và `ROADMAP.md` tuyên bố tường minh ranh giới: workspace này dành riêng cho AISC Round 2 (Data-Driven Business), không kế thừa lộ trình Sáng tạo trẻ.
3. **Phân biệt Statistical CI Coverage vs Python Code Coverage:**
   - `FACT-SHEET.md` (dòng 5–11), `QNA.md` (dòng 14–18), và `FREEZE.md` (dòng 40) đã phân định rạch ròi:
     - **Statistical CI coverage** (96,50% / 92,50%): đo tỷ lệ khoảng tin cậy chứa hiệu ứng thật trong mô phỏng Monte-Carlo (nguồn: calibration).
     - **Python code coverage** (88% observed; gate FAIL): đo tỷ lệ dòng mã được test đi qua (nguồn: `pytest-cov`). Tuyệt đối không dùng code coverage để thay thế hay chứng minh CI coverage.
4. **Phân định minh bạch Simulation / Replay / Demo / Real:**
   - `README.md` (dòng 15–21) phân định 3 tầng dữ liệu:
     - **Thật + Randomized:** 0 phiên (không có dữ liệu can thiệp ngẫu nhiên trên shop thật).
     - **Thật + Quan sát:** 19.126 bình luận từ 16 VOD YouTube hồi cứu (không có lịch can thiệp, không chứng minh quan hệ nhân quả).
     - **Demo / Mô phỏng:** 6 phiên Demo Vàng sinh bằng seed cố định, luôn mang cờ `is_demo=true`.
5. **Khai báo trung thực 0 phiên ngẫu nhiên thật:**
   - Toàn bộ các file tài liệu (`README`, `FACT-SHEET`, `ROADMAP`, `PITCH`, `QNA`, `FREEZE`) đều thừa nhận thẳng thắn: **0 phiên randomized thật**. Không dùng phiên mô phỏng để khỏa lấp điểm khuyết này.
6. **Kiểm soát Overclaim trong PITCH.md:**
   - `PITCH.md` mở đầu bằng disclaimer: Đây chỉ là bản nháp factual/technical, không tự ý bịa đặt vị thế kinh doanh; mọi số liệu phải lấy từ `FACT-SHEET.md`.
   - Phần giới hạn sản phẩm nêu rõ: API nhập đơn hàng đã có nhưng chưa có file dữ liệu đơn thật; Autopilot nội bộ có scheduler nhưng chưa chứng minh ghim thành công trên mọi nền tảng; mô hình NLP giữ nguyên giới hạn, không nâng cấp ngầm.

---

### 2.2. Giao diện trang `/ket-qua` (`web/src/app/ket-qua/page.tsx`)

1. **Mặc định giữ nguyên `env=real`:**
   - Trạng thái khởi tạo `const [env, setEnv] = useState<"real" | "demo">("real")` (dòng 712) được bảo toàn.
   - Endpoint gọi dữ liệu mặc định vẫn là `/experiment/summary?env=real`.
2. **Không redirect âm thầm sang demo:**
   - Tuyệt đối không có lệnh chuyển hướng tự động (`router.push`, `router.replace`, hay `window.location.href`).
3. **Hiển thị trung thực trạng thái 0 phiên thật:**
   - Khối `DemoVangCta` (dòng 664–691) chỉ là một Callout cảnh báo đặt phía trên khối Verdict.
   - Ngay bên dưới CTA, component `VerdictChuaDu` (dòng 866) vẫn hiển thị đầy đủ thông tin: "CHƯA ĐỦ ĐIỀU KIỆN — Cần ít nhất 1 phiên đã hoàn thành, hiện có 0 phiên". Trạng thái thật không hề bị che giấu.
4. **Nhãn Demo rõ ràng:**
   - Các nút bấm trong CTA đều mang nhãn rõ: `<span className="text-warn-ink">· DEMO/MÔ PHỎNG</span>`.
5. **Không hard-code UUID:**
   - Hàm `hrefFor(needle)` (dòng 665–670) tìm kiếm phiên runtime qua `sessions.find(...)` kết hợp kiểm tra `s.is_demo` và tiêu đề chứa chuỗi tương ứng (`"DƯƠNG RÕ"`, `"NULL"`, `"CHƯA ĐỦ"`).
   - Nếu danh sách phiên chưa nạp hoặc không khớp, URL an toàn rơi về `/ket-qua?env=demo`. Không chứa bất kỳ chuỗi UUID tĩnh nào.
6. **Không gây hồi quy (regression) các trạng thái khác:**
   - Điều kiện render (dòng 837): `!loading && !err && !phien && env === "real" && verdict?.state === "chuadu"`.
   - Khi đang xem phiên cụ thể (`phien`), hoặc khi `env === "demo"`, hoặc khi có lỗi tải mạng (`err`), hoặc khi thí nghiệm đã có kết quả (`duong`, `null`), Callout này hoàn toàn ẩn.

---

### 2.3. Khối Đối Chứng (`web/src/components/BlockClock.tsx`)

1. **Chỉ thay đổi nội dung văn bản (Copy):**
   - Hằng số giải thích trạng thái khối TẮT:
     ```typescript
     // Trước:
     off: "Vận hành như thường lệ — nhánh đối chứng để so sánh",
     // Sau:
     off: "Khối đối chứng — hệ thống cố ý không đưa gợi ý; hãy vận hành như bình thường để đo mức nền",
     ```
   - Hàm `actionLockReason` khi `view.assignment === "OFF"`:
     ```typescript
     // Trước:
     text: "Khối TẮT — vận hành như thường lệ"
     // Sau:
     text: "KHỐI ĐỐI CHỨNG — hệ thống cố ý không đưa gợi ý. Hãy vận hành như bình thường để đo mức nền."
     ```
2. **Bảo toàn hành vi gán khối và điều khiển:**
   - Không can thiệp vào logic tính toán khối, washout, hay thời gian đếm ngược.
   - Giá trị trả về `shape: "off"` được giữ nguyên vẹn.
3. **Hiệu quả UX:**
   - Giải quyết triệt để sự hoang mang của người vận hành: làm rõ việc hệ thống im lặng trong khối TẮT là chủ đích khoa học (đo lường mức nền đối chứng), loại bỏ hiểu lầm rằng phần mềm bị treo hay mất kết nối.

---

### 2.4. Công cụ kiểm tra trước demo (`scripts/round2_demo_check.py` & `tests/test_round2_demo_check.py`)

1. **Mặc định hoàn toàn chỉ đọc (Read-only):**
   - Chỉ sử dụng hàm `http_get` thông qua `urllib.request.urlopen` (không truyền tham số `data`, mặc định phương thức GET).
   - Không có bất kỳ request `POST`, `PUT`, `DELETE` nào trong script.
2. **Không can thiệp hạ tầng:**
   - Không gọi `subprocess`, `docker compose`, không khởi động/tắt tiến trình, không reset database, không xóa session.
3. **Phát hiện chính xác phiên quá hạn (Stale Session):**
   - Hàm `select_fresh_demo_session(sessions, now)` kiểm tra chặt chẽ `start <= now < start + timedelta(minutes=duration)`.
   - Phiên mang cờ `status=live` nhưng thời gian hiện tại đã vượt quá thời lượng kế hoạch sẽ bị tăng bộ đếm `stale` và bị loại khỏi danh sách chọn.
   - Nếu không có phiên nào hợp lệ, script lập tức trả về `FAIL` cho các cổng phụ thuộc (`Valid current block`, `Blinded host API contract`, `Presenter web routes reachable`).
4. **Hỗ trợ đầy đủ cả 2 topology mạng (Caddy vs Split Ports):**
   - Hỗ trợ cờ `--base` (cho Caddy: `http://localhost`, API trỏ vào `/api`).
   - Hỗ trợ cờ `--api` và `--web` (cho Split ports: `:8000` và `:3000`).
5. **Không đồng nhất HTTP 200 với "UI Usable":**
   - Header và output của script ghi rõ: *"HTTP reachability is not a UI usability claim"*.
   - Thông điệp hành động hướng dẫn presenter phải kiểm tra giao diện bằng browser test hoặc diễn tập thực tế.
6. **Cơ chế Fail-closed và Exit Code:**
   - `main()` trả về mã thoát `1` nếu có bất kỳ kiểm tra nào thất bại hoặc khi service chưa khởi động (`0 PASS · 2 FAIL`).
7. **Bảo mật thông tin:**
   - Không in biến môi trường, secret key, hay token ra màn hình console.

---

### 2.5. Hệ thống kiểm thử (Tests)

1. **`tests/test_round2_demo_check.py` (Mới — 6 tests):**
   - Bao phủ: logic chọn phiên runtime, loại bỏ phiên quá hạn, phát hiện thiếu Demo Vàng, kiểm tra rò rỉ thông tin gán khối tại màn hình Host (`HOST_ALLOWED_KEYS`), kiểm tra chế độ kho bền vững (`--allow-memory`), và xác nhận URL không hard-code UUID.
   - Mocking sạch: chỉ mock network getter `_getter`, không mock logic nội tại của checker.
2. **`tests/test_web_ket_qua.py` (Cập nhật — thêm 1 test):**
   - Test `test_real_chua_du_co_cta_demo_vang_nhung_khong_redirect_mac_dinh`: kiểm tra sự tồn tại của `DemoVangCta`, các nhãn cảnh báo, regex chống hard-code UUID.
   - *Nhận xét kỹ thuật:* Test này sử dụng kỹ thuật kiểm tra chuỗi mã nguồn (`_read(KET_QUA)`). Mặc dù tuân theo phong cách hiện có của repo, đây là dạng test tĩnh trên source code (xem chi tiết tại Mục P1).
3. **`tests/test_web_desk_layout.py` & `tests/test_web_desk_v3.py` (Cập nhật copy):**
   - Khóa đúng chuỗi thông báo mới của khối đối chứng.
   - Test `test_c2_khoa_nut_theo_lich_that` trong `test_web_desk_v3.py` thực thi trực tiếp hàm `actionLockReason` qua Node.js để kiểm tra hợp đồng trả về `{shape: "off", text: ...}`.

---

### 2.6. Kỷ luật ranh giới và phạm vi (Scope Enforcement)

Xác nhận Codex **TUÂN THỦ TUYỆT ĐỐI** các ranh giới cấm can thiệp:
- [x] Không can thiệp lõi thống kê (`src/livelift/stats/`).
- [x] Không sửa công thức ước lượng (`estimators.py`).
- [x] Không sửa phương pháp switchback hay tham số bốc thăm ngẫu nhiên.
- [x] Không sửa `PREREGISTRATION.md`.
- [x] Không thay đổi/huấn luyện lại mô hình NLP ý định (`src/livelift/nlp/`).
- [x] Không sửa scraper cào dữ liệu TikTok.
- [x] Không tạo hoặc sửa database migration (`src/livelift/storage/migrations/`).
- [x] Không thay đổi kiến trúc xác thực (auth/OAuth).
- [x] Không sửa đổi tài liệu lịch sử của cuộc thi Sáng tạo trẻ (`docs/competition/sang-tao-tre-2026/`, `docs/VIEC-CAN-LAM.md`, `README.md` gốc).

---

### 2.7. Đánh giá 5 lỗi Fast Test NLP (Baseline vs Regression)

Khi chạy toàn bộ bộ kiểm thử nhanh (`python -m pytest -m "not slow"`), hệ thống ghi nhận **5 lỗi thất bại** tại module NLP:

```text
FAILED tests/test_intent_classifier.py::test_trained_model_beats_keyword_baseline_by_a_margin
FAILED tests/test_intent_classifier.py::test_classify_with_confidence_matches_classify_and_bounds
FAILED tests/test_intent_classifier.py::test_model_meta_records_sklearn_version
FAILED tests/test_nlp_eval_harness.py::test_v2_meta_declares_provenance_and_matches_the_artifact
FAILED tests/test_nlp_eval_harness.py::test_env_var_switches_the_served_artifact_to_v2
```

#### Phân tích nguyên nhân gốc (Root Cause):
- **Bản chất lỗi:** Metadata của các artifact đã đóng gói sẵn (`intent_clf.joblib` và `intent_clf_v2.joblib`) ghi nhận được xuất từ `scikit-learn==1.9.0`.
- **Môi trường thực thi hiện tại:** Cài đặt `scikit-learn==1.7.2` (hoàn toàn hợp lệ theo ràng buộc của dự án tại `pyproject.toml: "scikit-learn>=1.5,<1.8"`).
- Khi nạp artifact, scikit-learn phát cảnh báo `InconsistentVersionWarning`. Đồng thời, các test kiểm tra phiên bản bắt buộc:
  `assert meta["sklearn_version"] == sklearn.__version__`
  `assert '1.9.0' == '1.7.2'` $\rightarrow$ **FAIL**.
- Khi model gặp sự cố phiên bản, hệ thống kích hoạt fallback an toàn về `keyword baseline`, khiến các bài test yêu cầu độ chính xác vượt trội của ML bị trượt.

#### Đánh giá tương quan với thay đổi của Codex:
- Lịch sử git cho thấy thư mục `src/livelift/nlp/` và các file test NLP được chỉnh sửa lần cuối tại commit `f4723bd` (ngày 17/09/2026).
- Working tree diff của Codex hoàn toàn **KHÔNG CHẠM** vào thư mục NLP, pyproject.toml hay bất kỳ cấu hình scikit-learn nào.
- Codex đã chủ động ghi nhận sự tồn tại của 5 lỗi này trong `FACT-SHEET.md`, `FREEZE.md`, `ROADMAP.md` và `QNA.md`.
- **KẾT LUẬN:** Đây là **PRE-EXISTING BASELINE FAILURE** tồn tại từ trước trên nhánh/môi trường, hoàn toàn **KHÔNG PHẢI REGRESSION** do Codex gây ra. Quyết định không tự ý retrain model trong phạm vi Round 2 là hoàn toàn chính xác.

---

### 2.8. An toàn bảo mật và phát hành (Security / Release)

1. **Rò rỉ bí mật:** Không phát hiện bất kỳ API key, token, mật khẩu hay credential nào bị commit nhầm trong code hoặc tài liệu.
2. **Rủi ro Command Injection & File Operation:** `round2_demo_check.py` chỉ sử dụng các hàm chuẩn của thư viện Python (`urllib.parse`, `urllib.request`), kiểm tra scheme hợp lệ (`http`, `https`), không thực thi subshell hay ghi file bất kỳ.
3. **Kiểm tra lỗ hổng phụ thuộc npm:**
   - Lệnh `npm audit` trong thư mục `web/` báo cáo 2 lỗ hổng (1 high trên `postcss`, 1 critical trên `next`).
   - Codex **KHÔNG** tự ý chạy `npm audit fix --force` (vì việc nâng cấp lên `next@16` sẽ làm gãy giao diện). Build production của Next.js 14 vẫn biên dịch thành công 100% (`Compiled successfully`).

---

## 3. MA TRẬN KẾT QUẢ THỰC THI KIỂM CHỨNG (VERIFICATION MATRIX)

Tất cả các lệnh dưới đây đã được thực thi trực tiếp và ghi nhận kết quả:

| Lệnh kiểm chứng | Kết quả | Chi tiết / Evidence thực tế |
|---|:---:|---|
| `.venv/bin/python -m pytest tests/test_round2_demo_check.py tests/test_web_ket_qua.py tests/test_web_desk_layout.py tests/test_web_desk_v3.py` | **PASS** | 75 passed trong 2.30s. |
| `.venv/bin/python -m pytest -m "not slow" --tb=short` | **FAIL** *(Dự kiến)* | 1.803 passed, 5 failed (đúng 5 lỗi NLP scikit-learn baseline), 3 skipped trong 86.27s. |
| `.venv/bin/python -m pytest -m slow` | **PASS** | 26 passed, 1 skipped, 1.811 deselected trong 466.83s. |
| `.venv/bin/python -m pytest -m browser` | **PASS** | 10 passed trong 9.06s. |
| `.venv/bin/python scripts/dong_bo_so_test.py --xem-truoc` | **PASS** *(Evidence)* | Đếm chính xác: 1.811 nhanh · 17 Monte-Carlo · 10 trình duyệt (tổng 1838). |
| `awk ... docs/incident-log.md` | **PASS** | Khớp chính xác 60 sự cố có root-cause. |
| `.venv/bin/ruff check src tests scripts/round2_demo_check.py` | **PASS** | All checks passed. |
| `.venv/bin/ruff format --check src tests scripts/round2_demo_check.py` | **PASS** | 157 files already formatted. |
| `npm run build` (trong thư mục `web/`) | **PASS** | Next.js 14.2.32 tạo optimized production build thành công (11/11 pages static/dynamic). |
| `python scripts/round2_demo_check.py --base http://localhost` | **FAIL-CLOSED** | Báo lỗi kết nối chuẩn xác khi chưa bật service (0 PASS · 2 FAIL, exit code 1). |
| `pytest -m db tests/test_store_contract.py` | **NOT RUN** | 13 deselected (không có Postgres, marker hoạt động đúng kỳ vọng). |
| `docker compose config` | **NOT RUN** | `docker: command not found` (môi trường máy tính review không cài docker client). |

---

## 4. BẢNG PHÂN LOẠI PHÁT HIỆN (FINDINGS CLASSIFICATION)

### BLOCKER
*Không có phát hiện nào thuộc mức độ BLOCKER trong mã nguồn triển khai của Codex.*

---

### P0 FIX
*Không có lỗi P0 nào bắt buộc phải sửa trước khi tiến hành runtime verification.*

---

### P1 (Cải tiến chất lượng & Độ bền vững)

#### [P1.1] Phòng vệ kiểu dữ liệu trong `round2_demo_check.py`
- **File:** `scripts/round2_demo_check.py`
- **Vị trí:** Dòng 295 và dòng 393
- **Evidence:**
  ```python
  # Dòng 295:
  and block.get("seconds_remaining", 0) > 0
  ```
  Nếu một API response bất thường trả về `{"current_block": {"seconds_remaining": None, ...}}`, biểu thức `None > 0` trong Python 3 sẽ gây ra ngoại lệ `TypeError: '>' not supported between instances of 'NoneType' and 'int'`.
  Tại dòng 393, khối `try...except` chỉ bắt `(OSError, ValueError)`, không bắt `TypeError`, khiến checker có thể bị crash đột ngột thay vì xuất báo cáo FAIL lịch sự.
- **Tác động:** Rủi ro checker bị crash nếu mock hoặc API thật trả về trường `seconds_remaining` mang giá trị `None`.
- **Đề xuất fix tối thiểu:**
  Sửa điều kiện kiểm tra thành:
  ```python
  and isinstance(block.get("seconds_remaining"), (int, float))
  and block["seconds_remaining"] > 0
  ```
  và tại `main()`, bổ sung bắt `Exception` chung để luôn in báo cáo bảng preflight.

#### [P1.2] Tính giòn (Brittle) của test tĩnh trong `test_web_ket_qua.py`
- **File:** `tests/test_web_ket_qua.py`
- **Vị trí:** Hàm `test_real_chua_du_co_cta_demo_vang_nhung_khong_redirect_mac_dinh` (dòng 275–293)
- **Evidence:**
  Test kiểm tra trực tiếp mã nguồn dạng chuỗi:
  ```python
  src = _read(KET_QUA)
  assert "function DemoVangCta" in src
  ```
- **Tác động:** Nếu sau này lập trình viên chuyển hàm thành `const DemoVangCta = ...` hoặc tách component ra file riêng, test sẽ bị đỏ dù giao diện và chức năng hoàn toàn đúng. Ngược lại, test chuỗi không phát hiện được lỗi render JSX runtime.
- **Đề xuất fix tối thiểu:** Giữ nguyên test hiện tại để khóa quy chuẩn ngắn hạn, nhưng ghi chú trong tài liệu test rằng tính toàn vẹn của giao diện Next.js được bảo đảm bởi gate `npm run build`.

---

### SAFE / APPROVED (Đã kiểm tra và phê duyệt)

1. **`web/src/app/ket-qua/page.tsx`:** Cơ chế hiển thị Callout Demo Vàng trung thực, giải quyết xuất sắc vấn đề "màn hình mặc định gây thất vọng" mà vẫn bảo vệ tính liêm chính khoa học (giữ nguyên verdict thật 0 phiên ở bên dưới, fallback link an toàn, nhãn Demo Vàng rõ ràng).
2. **`web/src/components/BlockClock.tsx`:** Thay đổi copy khối đối chứng chính xác, ngắn gọn, trấn an người vận hành mà không làm biến đổi bất kỳ hành vi gán khối nào.
3. **`scripts/round2_demo_check.py`:** Công cụ preflight mẫu mực — tuân thủ triệt để nguyên tắc Read-Only, hỗ trợ linh hoạt cả 2 cấu hình cổng, xử lý stale session chặt chẽ, từ chối khẳng định sai lệch về tính khả dụng của UI.
4. **Bộ tài liệu `docs/competition/aisc-round2/*`:** Tài liệu độc lập, sạch sẽ, phân định rõ ràng giữa code coverage và statistical CI coverage, minh bạch về 0 phiên thật, loại bỏ hoàn toàn các yếu tố gây nhiễu của cuộc thi Sáng tạo trẻ.

---

### NEEDS BASELINE COMPARISON / PRE-EXISTING BASELINE

- **5 lỗi test NLP:**
  - `tests/test_intent_classifier.py::test_trained_model_beats_keyword_baseline_by_a_margin`
  - `tests/test_intent_classifier.py::test_classify_with_confidence_matches_classify_and_bounds`
  - `tests/test_intent_classifier.py::test_model_meta_records_sklearn_version`
  - `tests/test_nlp_eval_harness.py::test_v2_meta_declares_provenance_and_matches_the_artifact`
  - `tests/test_nlp_eval_harness.py::test_env_var_switches_the_served_artifact_to_v2`
- **Kết luận thẩm định:** Đây là **PRE-EXISTING BASELINE ISSUE** bắt nguồn từ việc đóng gói artifact với metadata scikit-learn 1.9.0 trên một môi trường khác trước ngày 17/09/2026. Thay đổi hiện tại của Codex không liên quan và không gây ra hồi quy này. Giữ nguyên trạng thái để Tech Lead xử lý trong một đợt cập nhật model riêng biệt.

---

## 5. KẾT LUẬN VÀ VERDICT

Triển khai của Codex trên nhánh `tien/aisc-round2` đạt mức độ kỷ luật kỹ thuật rất cao:
- Đáp ứng đầy đủ các yêu cầu cốt lõi của bài thi AISC Vòng 2.
- Bảo vệ tuyệt đối tính liêm chính khoa học của LiveLift (không ngụy tạo dữ liệu thật, minh bạch về trạng thái 0 phiên, làm rõ ranh giới giữa mô phỏng và thực tế).
- Giao diện web được hoàn thiện tinh tế, Next.js build xanh 100%.
- Công cụ preflight hoạt động đúng thiết kế chỉ đọc an toàn.
- Không có bất kỳ vi phạm nào về ranh giới phạm vi hay hồi quy chức năng.

### VERDICT:

# **READY FOR RUNTIME VERIFICATION**

*(Sẵn sàng để đội ngũ vận hành tiến hành khởi động môi trường máy chủ và chạy quy trình kiểm chứng runtime preflight).*
