# Phân công và quy trình làm việc — đội LiveLift, từ 16/09/2026

*Lập 15/09/2026 từ một vòng đánh giá toàn bộ kho mã: 8 phân hệ đọc song song, 75 lỗ hổng
được phản biện độc lập, 3 phương án chia việc được soát xung đột trên chính lịch sử git rồi
chấm bởi 3 góc nhìn. Trạng thái xuất phát: `main` = `af0f00e`, cây làm việc sạch.*

**Đọc hết trong 15 phút trước khi viết dòng mã đầu tiên.** Mọi luật dưới đây đều có lý do,
và phần lớn lý do là một sự cố đã xảy ra thật trong dự án này.

---

## 0. Ba điều phải biết trước

1. **Hạn nộp hồ sơ 30/09/2026** (hạn nội bộ của trường có thể sớm hơn — đang hỏi).
   **Vòng Khu vực 10–11/10 là hackathon 2 ngày, chiếm 60% điểm.** Chung kết 20–22/11.
2. **Kho mã đang CÔNG KHAI.** Giám khảo có thể đọc mọi commit, mọi tài liệu, mọi lời kê khai.
   Không commit bất cứ thứ gì bạn không muốn hội đồng đọc.
3. **Dự án vừa phải đính chính công khai** (`af0f00e`): hồ sơ từng ghi 393 nhãn tập kiểm tra là
   "do người gán" và 320 câu mẫu là "nhóm tự viết" — transcript cho thấy **cả hai do Claude ghi**.
   Không ai cố ý, nhưng thể lệ Điều 5 cấm đúng loại khai sai này. Từ nay, **mọi câu về nguồn gốc
   dữ liệu, nhãn hay mã đều phải đối chiếu được với log hoặc mã**. Đây là luật quan trọng nhất
   của cả tài liệu.

---

## 1. Năm luật cứng

| # | Luật | Vì sao |
|---|---|---|
| 1 | **Hợp đồng giữa các làn là TỆP TEST do bên cung cấp giữ.** PR làm đỏ test của người khác tức là đang đổi hợp đồng — phải gắn nhãn `hop-dong` | Web và API từng lệch nhau vì xây song song; 4 đường dẫn không tồn tại làm bàn điều khiển đứng im |
| 2 | **README, FACT-SHEET, `incident-log.md`, hằng PROOF trong `web/src/app/page.tsx` chỉ Minh sửa**, trong cửa sổ tích hợp 22:00. Sửa lỗi thì ghi "Hàng sự cố đề xuất" trong mô tả PR | Hai PR cùng thêm dòng sự cố và cùng đổi số trong README sẽ merge trơn tru nhưng làm `main` đỏ |
| 3 | **Người gán nhãn mù không có dữ liệu thật trên máy, và không mở `results.json`/`results.md` cho tới khi đã đăng băm nhãn của mình** | Tệp kết quả công khai chứa đáp án; mở ra là độ đồng thuận κ mất giá trị |
| 4 | **Không bao giờ viết lại lịch sử git**: không amend/rebase commit đã push, không force-push, không `--author` người khác, không đổi ngày commit | Thể lệ chấm commit history thật; viết lại lịch sử mới là giả mạo |
| 5 | **Vai tạm tới 18/09.** Bài kiểm tra kỹ năng 60 phút; nếu lệch sở trường thì hoán **nguyên làn** Khánh ↔ Tiến | Chia theo đoán kỹ năng rồi mắc kẹt 2 tuần là rủi ro lớn hơn mất 2 ngày |

---

## 2. Ba làn — ai sở hữu gì

Mỗi tệp có **một người được sửa** và **ít nhất một người khác được duyệt**.

### Ngô Bình Minh — trưởng nhóm, lõi khoa học, API, tích hợp, hồ sơ

- **Sở hữu:** `src/livelift/{api (trừ routes/replays.py), core, analysis, sim, dbops, migrations}`, `config.py` (trừ khối nền tảng), `analysis/`, `PREREGISTRATION.md`, `HARNESS.md`, `CONTRIBUTING.md`, `README.md`, `pyproject.toml` (trừ extras ml/nlp), `docker/`, `docker-compose*.yml` (đồng chủ khối environment với Khánh), `.github/`, `ops/runbooks/`, `docs/incident-log.md`, `docs/competition/` (trừ các tệp liệt kê ở hai làn kia), các test hợp đồng (`test_web_api_contract.py`, `test_bao_ve_ghi.py`, `test_so_cong_bo.py`, `test_so_hieu_chuan.py`, `test_infra_public.py`…).
- **Người giữ dữ liệu thật duy nhất tới 30/09:** `data/labeling/`, log AI, sinh lại tệp `.joblib`.
- **Tự bảo vệ trước hội đồng:** thiết kế switchback và vì sao demo dùng 90 phút; RI + Fisher CI; A/A 3,50%; khoá kết quả; xác thực 15 route ghi; lời đính chính nguồn gốc nhãn.

### Lê Xuân Khánh — tầng dữ liệu, AI, nạp nền tảng

- **Sở hữu:** `src/livelift/ingest/` (gồm `pii/`), `src/livelift/nlp/` (mã; mô hình chỉ sinh lại trên máy Minh trước 30/09), `src/livelift/api/routes/replays.py`, `collectors/`, khối nền tảng trong `config.py` và mục `# --- Platform APIs` của `.env.example`, extras ml/nlp trong `pyproject.toml`, `scripts/{xuat_prompt_log, gan_lai_nhan_11, live_fire_da_nguon, kiem_tra_facebook, kiem_tra_shopee}.py`, test `test_ingest_*`, `test_pii_filter`, `test_intent_classifier`, `test_nlp_eval_harness`, `docs/benchmarks/{intent-classifier.md, intent-eval/, live-fire-*.md}`, `docs/nen-tang-ho-tro.md`, `03-NLP-NANG-CAP.md`.
- **Chỉ đọc:** `api/` (trừ replays), `core/`, `analysis/`, `web/src/lib/types.ts`, tài liệu nộp (góp câu qua GitHub suggestion).
- **Vùng tự do:** kiến trúc bộ xuất Prompt Log, thiết kế script κ và bootstrap; **sau 30/09 toàn quyền** thiết kế client YouTube Data API, bộ đồ nghề hackathon, backend trợ lý LLM.
- **Tự bảo vệ trước hội đồng:** nguồn dữ liệu (yt-dlp, không phải API chính thức) và lộ trình sang YouTube Data API v3; cổng PII với handle có dấu; đánh giá NLP leave-one-session-out và vì sao 0,565 đo trên nhãn AI; κ người–người.

### Ngô Lâm Tiến — tầng giao diện, kiểm thử đầu-cuối, minh chứng nhìn thấy được

- **Sở hữu:** toàn bộ `web/` (trừ hằng PROOF), `web/e2e/` và Playwright, `.github/workflows/e2e.yml`, `scripts/gate_css_web.py`, `scripts/quet_so_cu.py` (mới), test `test_web_*` (trừ `test_web_api_contract.py`), `docs/HUONG-DAN-SU-DUNG.md`, `docs/img/v2/` (chỉ thêm, không ghi đè ảnh cũ), `dung_ho_so.py`, `07-KICH-BAN-2-VIDEO.md`, `thong_tin_doi.py` + tệp `.example` (Minh duyệt vì liên quan dữ liệu cá nhân).
- **Sau 01/10 nhận thêm:** vận hành máy chủ ≥48 giờ (`ops/deploy/`, `ops/monitoring/`, `docker/Caddyfile`, backup).
- **Chỉ đọc:** toàn bộ `src/livelift/` (muốn thêm trường thì mở issue `hop-dong`), các test hợp đồng, tài liệu nộp.
- **Vùng tự do:** kiến trúc E2E, cách trình bày lỗi và nhãn, dựng video; **sau 30/09 toàn quyền** thiết kế lại giao diện trong hệ token, chọn công cụ giám sát và đo tải.
- **Tự bảo vệ trước hội đồng:** vì sao màn hình không nói dối (nhãn DEMO/THẬT theo `is_demo`); vì sao test đọc mã xanh mà E2E vẫn bắt được lỗi; cổng quét số cũ; uptime và khôi phục sau 30/09.

---

## 3. Việc trước 30/09

Mỗi việc có **tiêu chí nghiệm thu kiểm được bằng lệnh**. Việc chưa có lệnh nghiệm thu thì chưa xong.

### Minh (≈52 giờ, gồm 9 giờ tích hợp và duyệt)

| Mã | Việc | Hạn | Nghiệm thu chính |
|---|---|---|---|
| M-01 | Chặn mất log AI, liên hệ trường (hạn nội bộ, người giữ tài khoản nộp), thư BTC gộp câu hỏi, giấy xác nhận SV | 15–16/09 | `cleanupPeriodDays` = 365; bản sao log + manifest SHA-256 lên Drive riêng tư; ảnh thư đã gửi |
| M-02 | Hoàn tất đính chính (đã làm một phần ở `af0f00e`) ở các tệp còn lại; gỡ yêu cầu 0,271 trong `test_so_cong_bo.py` | 17/09 | `git grep` các cụm "người gán / gán mù / tự viết / API chính chủ" chỉ còn trong đoạn đính chính |
| M-03 | Quy trình GitHub: ruleset `main`, mời Khánh/Tiến, tag `moc-truoc-phan-cong`, nhãn, issue ghim, gỡ khoá Actions | 16/09 | Có ≥1 lần CI chạy có bước thật, hoặc ghi phương án B |
| M-04 | Bài kiểm tra kỹ năng; sinh bảng gán mù (uid ngẫu nhiên, xáo trộn); quyết định public/private | 17–18/09 | Băm bảng + key được commit **trước** khi phát bảng |
| M-05 | Lọc lại PII dữ liệu thật; huấn luyện và đo lại; công bố key; đo trên nhãn người | 17–22/09 | 0 handle có dấu trong `data/labeling`; `results.json` sinh lại, công bố cả khi lệch 0,565 |
| M-06 | `/health` thêm khoá quyền ghi và mô hình; token sai trả 401 | 19–21/09 | `pytest tests/test_health_su_that.py tests/test_bao_ve_ghi.py` xanh |
| M-07 | Sửa lỗi hoà số p-value; `/demo/seed` mặc định 90 phút | 23/09 | Test tái hiện lỗi hoà số; A/A 1 phiên 60' không còn p < 0,05 giả |
| M-08 | `noi-dung.md` khớp mã; khoá kết quả trên `/sessions/{id}/report` | 22/09 | Không còn câu nói mạnh hơn mã; PDF ≤ 20 trang |
| M-09 | Viết lại bản kê khai 05, có chữ ký 3 người | 25/09 | Bảng "đội tự làm / AI tạo / kế thừa" sinh từ dữ liệu của K-07 |
| M-10 | Xuất Prompt Log lần 1 và bản cuối | 22/09, 29/09 | Quét PII trên bản xuất = 0 |
| M-11 | Cửa sổ tích hợp 22:00 hằng ngày | 16–30/09 | `dong_bo_so_test.py --xem-truoc` báo khớp sau mỗi cửa sổ |

### Khánh (≈49 giờ)

| Mã | Việc | Hạn | Nghiệm thu chính |
|---|---|---|---|
| K-00 | Việc cá nhân: sao lưu log AI (hoặc biên bản "không có"), kê khai công cụ AI, danh tính git, giấy xác nhận SV | 17/09 | `git log -1 --format='%an <%ae>'` ra tên thật + email noreply |
| K-01 | Cổng recall PII có handle tiếng Việt (regex đã sửa ở `b1cd9fa`, còn thiếu dữ liệu cổng); bộ xuất Prompt Log dùng chung regex sản phẩm | 17/09 | ≥20 dòng handle bịa trong fixture; đối chứng âm: đổi regex về ASCII thì cổng đỏ |
| K-02 | Script lọc lại PII cho `data/labeling`, viết trên dữ liệu tổng hợp để Minh chạy | 19/09 | Chạy lần 2 không đổi gì; chỉ in số đếm |
| K-03 | Mã đánh giá NLP trung thực: nguồn nhãn là tham số, bỏ chữ "gán tay" | 19/09 | `grep -nE 'gán nhãn TAY\|người gán' src/livelift/nlp/eval_intent.py` = 0 |
| K-04 | Chốt scikit-learn khớp artifact (`>=1.9,<1.10`); `classifier_info` báo `predict_ok` | 19/09 | Venv Python 3.11 sạch chạy xanh `test_intent_classifier.py` |
| K-05 | Script κ viết **trước** khi nhận bảng; gán mù 393 dòng | 17/09 → 22/09 | Băm nhãn đăng trong issue trước 20/09 23:59; `kappa.json` công bố dù số tăng hay giảm |
| K-06 | Sửa bộ xuất Prompt Log: không cắt ngầm đầu vào công cụ, phân vai đúng, kèm log tác tử con | 20/09 | Mọi chỗ cắt có dấu "(cắt bớt N ký tự)"; test trên dữ liệu tổng hợp |
| K-07 | Script phân định đóng góp (đội / AI / kế thừa) từ log + `git blame` | 23/09 | Minh chạy ≤ 10 phút ra `phan-dinh.json` |
| K-08 | Tạo `YOUTUBE_API_KEY`, bật live kênh đội, token Fanpage | 19/09 | `videos.list` trả 200; không thu bình luận nào trước 30/09 |
| K-09 | Phỏng vấn 1 nhà bán + tổng hợp 3 biên bản | 24–25/09 | Biên bản ẩn danh + phiếu đồng ý trên Drive riêng |
| K-10 | Đưa `INGEST_TOKEN`, `PUBLIC_DEMO_WRITES`, `CORS_ORIGINS`, `RESULTS_FREEZE_UNTIL`, `LIVELIFT_INTENT_MODEL` vào container `api` | 22/09 | `tests/test_compose_env.py` đỏ trước khi sửa, xanh sau khi sửa |
| K-11 | Hậu cần 2 vòng thi: kinh phí, lịch học, giấy tờ | 30/09 | Đơn kinh phí đã gửi trường |

### Tiến (≈50 giờ)

| Mã | Việc | Hạn | Nghiệm thu chính |
|---|---|---|---|
| T-00 | Việc cá nhân (như K-00) | 17/09 | Tên thật trên commit |
| T-01 | Dựng Playwright; sửa `/replay`: đọc `?session=`, nhãn theo `is_demo` | 20/09 | `npx playwright test e2e/replay.spec.ts` xanh; bỏ đoạn đọc query thì đỏ |
| T-02 | Gọi `/demo/seed` với `duration_min` tường minh; hiển thị đúng 401/403/429 | 21/09, 24/09 | Web phân nhánh theo mã trạng thái, không so chuỗi tiếng Việt |
| T-03 | Web chịu được 11 nhãn và nhãn lạ; radar ghi "chưa dùng cho quyết định" | 22/09 | Test hợp đồng nhãn; 0 lỗi console với nhãn không tồn tại |
| T-04 | Cổng quét số cũ **chỉ trên tệp nộp** | 23/09, chạy lại 29/09 | Xoá một dòng ngoại lệ thì test đỏ; ngày 29/09 tệp ngoại lệ rỗng |
| T-05 | Sửa bộ dựng PDF: tích ô "3 người", hết dấu backtick, chặn xuất khi còn ô ⬜ | 21/09 | Còn ⬜ thì thoát mã 1 và PDF không bị ghi đè |
| T-06 | Kịch bản, ảnh v2 tái lập, quay và dựng 2 video ≤ 5 phút có đủ 3 người | 23–27/09 | `ffprobe` ≤ 300 giây mỗi video; không ghi đè ảnh cũ |
| T-07 | Gán mù 393 dòng (bản của Tiến) | 20/09 | Không dùng AI, không trao đổi với Khánh, đăng băm trước 20/09 23:59 |
| T-08 | Phỏng vấn 2 nhà bán | 24/09 | Giữ nguyên câu trả lời bất lợi |
| T-09 | Gói Drive minh chứng: tiến trình theo commit, đọc tay ≥ 5 tệp Prompt Log, mở quyền | 26/09 | Link mở được bằng cửa sổ ẩn danh |

**Thoát tải:** check-in 20/09 mà M-02/M-04/M-05 chưa xong thì M-07 chuyển sang Khánh.
**Cắt dự phòng ngày 22/09 nếu trễ hơn 1 ngày:** (a) bỏ T-03, kịch bản ghi "desk chạy v1";
(b) dời T-02b sau 30/09; (c) chỉ 2 phỏng vấn; (d) K-07 chỉ tính theo tệp.

## 4. Sau 30/09 (tóm tắt)

| Người | Việc chính |
|---|---|
| Minh | Bảo mật còn lại (proxy tin cậy cho click, WebSocket kiểm origin, Postgres trong CI) · chỉ huy diễn tập hackathon · chương trình phiên thật và khoá tiền đăng ký |
| Khánh | YouTube Data API v3 chính thức (quota, xoá dữ liệu ≤ 30 ngày) · **bộ đồ nghề đánh giá cho hackathon** (repo riêng có tag) · chặn tín hiệu ý định theo tỷ lệ nền · backend trợ lý LLM |
| Tiến | Web công khai cùng origin + E2E trên URL thật · **vận hành máy chủ ≥ 48 giờ** (HTTPS, giám sát, khôi phục, rollback) · thiết kế lại responsive · đo tải và fuzz |

Mốc: **diễn tập hackathon trọn 2 ngày 03–04/10**; mỗi người tự trình bày phần mình, không nhìn tài liệu, 06–08/10.

---

## 5. Hợp đồng giữa các làn

| Mã | Hợp đồng | Giữa | Tệp canh | Luật đổi |
|---|---|---|---|---|
| C-1 | REST/WS API ↔ web | Minh ↔ Tiến | `tests/test_web_api_contract.py` (chỉ Minh sửa) | Thêm route/trường tuỳ chọn: PR `hop-dong`; phá vỡ: cấm trước 30/09 |
| C-2 | Sự kiện nạp | Khánh ↔ Minh | `tests/test_ingest_api_integration.py`, `schemas.py` | Khánh không sửa `schemas.py`, store, migrations; cần trường mới thì viết test đỏ trước |
| C-3 | Bộ nhãn ý định | Khánh ↔ Tiến ↔ Minh | `nlp/labels.py`, `web/src/lib/types.ts`, `test_hop_dong_nhan_y_dinh.py` | Web có nhánh dự phòng trước; thêm nhãn: merge Tiến trước, Khánh sau |
| C-4 | `/health` | Minh ↔ Khánh ↔ Tiến | `tests/test_health_su_that.py` | Chỉ **thêm** khoá, không đổi tên hay xoá trước 22/11 |
| C-5 | Lỗi quyền và tần suất | Minh ↔ Tiến | `tests/test_bao_ve_ghi.py` | Web phân nhánh theo **mã trạng thái**, không so chuỗi — Minh được sửa câu chữ tự do |
| C-6 | Dữ liệu mẫu cho test/E2E/ảnh | Minh ↔ Tiến ↔ Khánh | `POST /demo/seed`, `/demo/seed-vang` | Luôn truyền tham số tường minh; mọi fixture là dữ liệu **tổng hợp** |
| C-7 | Token giao diện | Tiến ↔ Minh | `tailwind.config.ts`, `globals.css`, `test_web_design_tokens.py` | Không đổi tên token trước 30/09; màu mới qua cổng WCAG |
| C-8 | Số công bố | Minh ↔ Khánh ↔ Tiến | `so-hieu-chuan.json`, `results.json`, `kappa.json`, `dong_bo_so_test.py` | **Không ai gõ tay số vào tài liệu nộp** |
| C-9 | Gán nhãn mù | Minh ↔ Khánh, Tiến | `docs/benchmarks/intent-eval/gan-mu/*.sha256` (mỗi tệp một chủ) | Băm bảng/key commit trước khi phát; băm nhãn đăng trước khi key công bố |
| C-10 | Biến môi trường container | Minh ↔ Khánh | `.env.example`, 2 tệp compose, `test_compose_env.py` | Biến production mới phải có trong **cùng PR** ở cả 4 chỗ |
| C-11 | Lọc PII dùng chung | Khánh ↔ Minh ↔ Tiến | `ingest/pii/patterns.py`, `tests/test_pii_filter.py` | Ngưỡng recall **chỉ được nâng**; placeholder (`[MXH]`, `[SĐT]`…) giữ ổn định |
| C-12 | JSONL trung gian của log AI | Khánh ↔ Minh | Bộ xuất Prompt Log | Thêm trường tự do; đổi quy tắc phân vai cần Minh duyệt |

---

## 6. Tệp dùng chung — ai được ghi

- **Commit bằng `git add <đường dẫn cụ thể>` rồi `git diff --cached --stat`. KHÔNG dùng `git add -A`.**
- `docs/incident-log.md`, `README.md`, `FACT-SHEET.md`, hằng PROOF: chỉ Minh, trong cửa sổ tích hợp.
- `noi-dung.md` (hồ sơ): chỉ Minh viết; nhận góp theo lô 18, 20, 22, 25/09; **khoá nội dung 26/09**.
- `web/src/lib/api.ts`, `types.ts`: Tiến; hàm mới thêm cuối nhóm, không định dạng lại cả tệp.
- `config.py`, `.env.example`: Minh; Khánh chỉ thêm ở cuối khối nền tảng.
- `pyproject.toml`: Minh; mỗi PR chỉ **một** thay đổi phụ thuộc, tiêu đề `deps:`.
- `web/package.json`, lock: Tiến; xung đột lock thì lấy lock của `main` rồi `npm install` lại.
- `web/tsconfig.json`: `next dev` tự chèn dòng `.next-*` — chỉ Tiến commit; lỡ đổi thì `git restore web/tsconfig.json`.
- `src/livelift/migrations/`: **đóng băng tới 30/09.**
- Tệp sinh hoặc nhị phân (`results.json`, `*.joblib`, `so-hieu-chuan.json`): không merge tay — xung đột thì chạy lại lệnh sinh trên `main`.

**KHÔNG BAO GIỜ COMMIT:** `.env` · `docs/competition/thong-tin-doi.local.json` · `data/labeling/*` (trừ README) · `data/snapshot/` · `backups/` · bản sao log AI · phiếu đồng ý · giấy xác nhận SV · mô hình mới chưa kiểm từ vựng.

---

## 7. Git: nhánh, commit, PR, duyệt

**Nhánh:** `<ten>/<MA-TASK>-mo-ta` — ví dụ `khanh/K-06-xuat-prompt-log`, `tien/T-01-replay-session`.
Một việc một nhánh, sống ≤ 3 ngày, **mở Draft PR ngay ngày đầu**. Việc > 6 giờ tách 2 PR.

**Cỡ PR:** ≤ 400 dòng (không tính tệp sinh, lock, ảnh). Mỗi PR chạm tối đa **một** hợp đồng.

**Commit:** dòng đầu `<khu-vuc>: <mo ta khong dau ≤72 ky tu>`, khu vực ∈ {api, core, sim, nlp, pii, ingest, web, e2e, infra, ci, docs, ho-so, so-lieu, lien-chinh, deps, tich-hop}. Thân có `Vi sao:` và `Kiem bang:` (lệnh + kết quả). Trailer:
- Dùng Claude Code: `Co-Authored-By: <đúng tên mô hình của phiên> <noreply@anthropic.com>`
- Dùng công cụ AI khác: `AI-Assisted: <công cụ, ngày>`
- Làm cặp với người thật: `Co-authored-by: <Tên thật> <email noreply>`

**Cập nhật nhánh:** `git merge origin/main` (không rebase nhánh đã push).

**Merge:** chỉ "Create a merge commit"; xoá nhánh sau khi merge.

**Duyệt:**
- PR thuần làn Khánh → Tiến duyệt, và ngược lại. Có approval là merge được bất cứ lúc nào.
- PR chạm hợp đồng (`hop-dong`), config, compose, `pyproject.toml`, `.github/`, hoặc tệp của Minh → Minh duyệt trong cửa sổ 12:00 hoặc 22:00.
- **Người duyệt phải tự chạy lệnh nghiệm thu chính của việc đó.** Quá 24 giờ chưa duyệt thì nhắc; quá 48 giờ thì người thứ ba duyệt.

**CI:** GitHub Actions hiện **chưa chạy được** — mọi job dừng trước bước đầu tiên, rất có thể do khoá thanh toán tài khoản. Cho tới khi gỡ được (hạn 20/09), dùng **phương án B**: PR dán dòng tổng kết `pytest -m "not slow" --junitxml`, `ruff check`, `ruff format --check`, `npx tsc --noEmit` và `git rev-parse HEAD`.

---

## 8. Nhịp đồng bộ — không họp vô ích

**Hằng ngày:**
- **21:30** — mỗi người ≤ 3 dòng vào issue ghim "Check-in": *Xong* (link PR) · *Mai* (mã việc) · *Vướng*. Kết luận trao đổi trên Zalo phải dán lại đây để có vết.
- **12:00** (15') — Minh duyệt PR `hop-dong`.
- **22:00–22:30** — cửa sổ tích hợp của Minh: merge, gộp hàng sự cố, đồng bộ số, báo "main xanh tại `<hash>`".
- Khánh và Tiến `git merge origin/main` đầu mỗi buổi làm.

**Cuộc gọi trước 30/09:** 16/09 20:00 (90', chốt phạm vi) · 18/09 21:00 (30', kết quả kỹ năng, giữ hay hoán làn) · 20/09 21:30 (15') · 22/09 20:00 (30', kích hoạt cắt nếu trễ) · 26/09 21:00 (30', khoá hồ sơ) · 29/09 20:00 (45', kiểm tra cuối).

**Lịch đóng băng:** 17/09 phát bảng mù · 20/09 nộp băm nhãn · 22/09 xuất Prompt Log lần 1 · **23/09 23:59 đóng băng giao diện và hợp đồng cho ảnh/video** · 26/09 khoá nội dung hồ sơ · 28/09 dựng PDF · 29/09 xuất lại Prompt Log.

---

## 9. 48 giờ đầu của Khánh và Tiến

1. Nếu có dùng Claude Code cho LiveLift: thêm `"cleanupPeriodDays": 365` vào `~/.claude/settings.json` và sao lưu `~/.claude/projects/` + manifest SHA-256 lên Drive riêng. Không dùng thì ghi biên bản "không có log AI".
2. Bật "Keep my email private" trên GitHub, nhận lời mời Collaborator.
3. Clone và cấu hình danh tính **tên thật**:
   ```bash
   git clone https://github.com/bminhnemhoi/AISC2026_LIVEFIT.git
   cd AISC2026_LIVEFIT
   git config --local user.name "Họ Tên Thật"
   git config --local user.email "<id>+<user>@users.noreply.github.com"
   ```
4. Môi trường và phép thử đầu tiên (bản clone mới phải ra **1.157 test, 0 lỗi, 3 bỏ qua**):
   ```bash
   py -3.11 -m venv .venv
   .venv/Scripts/pip install -e ".[dev,server,ml]"
   PYTHONIOENCODING=utf-8 .venv/Scripts/python -m pytest -m "not slow" -q
   ```
   Tiến chạy thêm: `cd web && npm ci && npx tsc --noEmit`.
   Dán dòng tổng kết + `git rev-parse HEAD` vào issue Check-in.
5. Đọc tài liệu này, `CONTRIBUTING.md`, và các hợp đồng liên quan làn mình (mục 5).
6. **PR nhỏ đầu tiên để thử trọn quy trình:** nhánh `<ten>/K-00-cong-cu-ai` (hoặc `T-00`), chỉ tạo `docs/research/cong-cu-ai/<ten>.md` kê khai công cụ AI đã dùng và khoảng ngày. Mở PR theo mẫu, nhờ người kia duyệt, merge bằng merge commit.
7. Gửi **riêng cho Minh** (không qua repo): số điện thoại, nơi ở, lớp hành chính — để điền vào tệp thông tin đội cục bộ. Nộp đơn xin giấy xác nhận sinh viên.

---

## 10. Rủi ro phối hợp và cách giảm

| Rủi ro | Cách giảm |
|---|---|
| Gán mù bị nhiễm (người gán mở kết quả hoặc có dữ liệu thật) | Dữ liệu thật chỉ trên máy Minh; cấm mở `results.*` tới khi đăng băm; uid ngẫu nhiên xáo lẫn các buổi |
| Hai PR cùng đổi số sự cố và README → `main` đỏ mà CI không chạy nên không ai thấy | Chỉ Minh ghi sổ sự cố; chạy `test_so_cong_bo.py` sau mỗi cửa sổ; phương án B bắt dán kết quả test |
| CODEOWNERS sai cú pháp hoặc một chủ duy nhất khoá merge | Mỗi mẫu ≥ 2 chủ; chỉ bật "Require review from Code Owners" khi cả hai đã nhận lời mời và API báo 0 lỗi |
| Minh là điểm nghẽn (~52 giờ) | Phần bắt buộc của Minh làm tối 15/09; luật thoát tải M-07 → Khánh; cắt dự phòng ngày 22/09 |
| Mất log AI do Claude Code tự dọn sau 30 ngày | `cleanupPeriodDays` 365 trên cả 3 máy trước 17/09; sao lưu lại 12/10 và 15/11 |
| scikit-learn trong CI/Docker lệch bản đã đóng gói mô hình → dự đoán âm thầm rơi về từ khoá | K-04 chốt phiên bản + `predict_ok`; Minh chỉ huấn luyện lại sau K-04 |
| Hạn nội bộ của trường sớm hơn 30/09 | Hỏi ngày 16/09; không có trả lời tới 18/09 thì coi hạn là 26/09 và dời mọi mốc |
| Sau 30/09 thiếu người trực máy chủ ≥ 48 giờ → điểm vận hành bằng 0 | T-11 giao Tiến từ 01/10, URL 12/10, chạy liên tục từ 01/11 |

---

## Phụ lục — trạng thái đã kiểm ngày 15/09/2026

- `main` = `af0f00e`, 49 commit (tất cả dưới danh tính chung "LiveLift Team"), cây sạch; bản clone mới: 1.157 test, 0 lỗi, 3 bỏ qua (2 test NLP tự bỏ qua vì dữ liệu gán nhãn bị gitignore).
- `ruff check` sạch, `ruff format` sạch, `tsc --noEmit` sạch, `next build` thành công. Web **chưa có ESLint**.
- GitHub Actions: chưa chạy được (job dừng trước bước đầu tiên).
- Kho mã **công khai**. Lịch sử git cũ còn thông tin cá nhân của đội trong `dung_thuyet_minh.py` (đã gỡ khỏi HEAD) và 2 bản dump cơ sở dữ liệu (30/08, 02/09) — kiểm sơ bộ không thấy số điện thoại hay tên tài khoản, cần xác nhận bằng `pg_restore`.
- Log AI trên máy Minh đã sao lưu cục bộ: 2.811 tệp, 355 transcript, có manifest SHA-256. Chưa đặt `cleanupPeriodDays`, chưa đưa lên Drive.
- Đã sửa trong ngày: xác thực 15 route ghi; regex PII handle có dấu; khung đánh giá NLP; làm cứng hạ tầng; số hiệu chuẩn tái lập được; đính chính nguồn gốc nhãn.
- **Còn mở, đã xác nhận bằng phản biện:** compose không đưa `INGEST_TOKEN` vào container (bản triển khai tắt xác thực) · sau Caddy, chống trùng click lấy IP của Caddy nên gộp người xem · mô hình v2 chỉ bật bằng biến môi trường, web chưa hiển thị được 5 nhãn mới · thiết kế gán suy biến ở phiên dưới ~85 phút (phiên 60' chỉ còn 4 chuỗi gán khả dĩ) · lỗi hoà số trong p-value · `/replay` ghi "DỮ LIỆU THẬT" trên phiên DEMO · số MDE 20,1% và hiệu ứng lưu chưa có lệnh sinh lại · 0 phiên thí nghiệm ngẫu nhiên thật.
