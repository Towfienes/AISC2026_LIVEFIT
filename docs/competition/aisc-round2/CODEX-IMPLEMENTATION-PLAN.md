# Kế hoạch triển khai AISC Round 2

> Trạng thái: **CHỜ PHÊ DUYỆT** · lập ngày 21/09/2026 trên nhánh
> `tien/aisc-round2` (HEAD `08be6ae`).
>
> Đây là kế hoạch cho workspace AISC Round 2, không phải roadmap Sáng tạo trẻ.
> Chưa có mã ứng dụng, dữ liệu, cấu hình, branch, hay tài liệu ngoài tệp kế
> hoạch này được sửa trong Phase 1.

## Ranh giới đã kiểm tra

- `/ket-qua` mặc định gọi `GET /experiment/summary` với `env=real`; code đã
  tách phiên `is_demo` và có `?env=demo`/`?phien=<id>`. Thay đổi phải giữ mặc
  định này, không redirect sang demo và không làm demo thành dữ liệu thật.
- `scripts/kiem_tra_truoc_demo.py` là precheck hiện có nhưng phục vụ bối cảnh
  chung/Sáng tạo trẻ; nó chưa xác nhận đầy đủ session demo *fresh*, selection
  trên desk, route host/result, hay danh sách URL trình bày của AISC.
- `scripts/seed_demo_vang.py` và `POST /demo/seed-vang` đã có bộ sáu phiên
  `is_demo=true`. Một phiên đang phát mới là nhu cầu riêng, vì phiên cũ có thể
  rơi vào `NGOÀI KHỐI`.
- Mã hiện có đường nhập đơn (`POST /sessions/{id}/orders` và `/orders/import`),
  `IngestManager`, `SnapshotManager`, và autopilot nội bộ. Adapter Shopee có
  `update_show_item`, nhưng audit code/tài liệu cho thấy nó chưa là adapter
  production được scheduler gọi để ghim sản phẩm trên mọi nền tảng.
- Không lấy số công bố từ README/audit bằng cách chép tay. Hiện có mâu thuẫn:
  README nói 1.803 fast; `docs/VIEC-CAN-LAM.md` nói 1.555 fast + 17 slow + 10
  browser; audit cũng ghi nhiều tổng khác nhau. `scripts/dong_bo_so_test.py`
  xác định nguồn đếm là pytest `--collect-only`, nên kết quả thực thi của nó
  (kèm lệnh collect độc lập) mới là nguồn có thẩm quyền cho số test.
- `docs/benchmarks/so-hieu-chuan.json` hiện lưu phép đo 14/09/2026 (A/A
  7/200 = 3,50%; **statistical CI coverage** 193/200 = 96,50%; known-effect
  bias −0,84%). Đây là
  **candidate source**, chưa phải số được đóng gói AISC, cho đến khi
  `scripts/do_lai_so_hieu_chuan.py --kiem` chạy xanh trên revision triển khai.
- Tài liệu live-fire ghi 16 replay/VOD và 19.126 bình luận thật; đây là dữ liệu
  quan sát/replay, không phải phiên randomized. Fact sheet sẽ tiếp tục ghi rõ
  **0 phiên randomized thật** trừ khi bằng chứng executable của môi trường
  thật cho thấy khác (không có kế hoạch tạo hay ngụy tạo dữ liệu đó).

## BLOCKER

1. **Chưa có baseline executable cho các claim AISC.**

   Trước khi điền bất kỳ value nào vào FACT-SHEET, chạy và lưu nguyên output
   (ngày, commit, exit code) của các lệnh ở mục “Verification”. Nếu một lệnh
   không chạy được vì dependency/service thiếu, FACT-SHEET phải ghi `CHƯA XÁC
   MINH`, nguyên nhân, và lệnh còn thiếu; không ghi PASS hoặc suy số từ tài
   liệu cũ.

2. **Mọi conflict phải được giải bằng evidence, không bằng lựa chọn biên tập.**

   Ví dụ: pytest collect là authoritative cho test count; JSON chỉ là
   authoritative cho A/A/bias sau khi `--kiem` khớp; output benchmark/API là
   authoritative cho live-fire/real sessions. Nếu evidence vẫn mâu thuẫn, giữ
   cả hai giá trị kèm nguyên nhân, không chọn một giá trị “trông hợp lý”.

3. **Chưa có environment demo đang chạy được xác minh trong Phase 1.**

   Checker AISC chỉ có thể báo PASS sau khi người vận hành đã chủ động bật môi
   trường. Nó không được tự chạy `docker compose up`, kill tiến trình, reset
   DB, hay seed trong chế độ mặc định.

## P0

Thứ tự thực thi đã duyệt:

1. **P0-A:** establish executable baseline/source of truth.
2. **P0-B:** tạo package AISC Round 2 từ evidence đã xác minh.
3. **P0-C:** CTA Demo Vàng trung thực trên `/ket-qua` + regression tests.
4. **P0-D:** chỉ sửa copy khối đối chứng, không đổi behavior.
5. **P0-E:** preflight `round2_demo_check.py` read-only + tests.
6. **P0-F:** chạy mandatory verification và ghi PASS/FAIL/NOT RUN.

### P0-1 — Tạo AISC Round 2 package độc lập

Tạo dưới `docs/competition/aisc-round2/`:

- `README.md`: giải thích đây là workspace AISC riêng; nêu entrypoints,
  ranh giới dữ liệu thật/demo, và link đến các tệp bên dưới.
- `FACT-SHEET.md`: bảng có đúng bốn cột bắt buộc: **value**, **nguồn**,
  **lệnh tái lập**, **ngày xác minh**. Có hàng cho fast/slow/browser, incidents,
  **statistical CI coverage**, A/A rejection, known-effect recovery/bias,
  live-fire comments/sessions và randomized real sessions. Nếu công bố
  **Python code coverage**, nó phải là một hàng riêng mang đúng tên đó; tuyệt
  đối không dùng nó thay cho statistical CI coverage. Mỗi hàng chưa chạy ghi
  rõ trạng thái chưa xác minh, không dùng số suy diễn.
- `ROADMAP.md`: mục tiêu, mốc và risk của AISC Round 2; không tham chiếu hoặc
  sao chép roadmap Sáng tạo trẻ.
- `DEMO-GATES.md`: checklist presenter và cách dùng checker mới, Caddy-vs-dev
  URL rõ ràng, nhãn DEMO/MÔ PHỎNG, cùng fallback trung thực.
- `PITCH.md`: **bản nháp factual/technical**, không tự quyết final storytelling
  hay business positioning; nói rõ 0 randomized sessions thật, phân biệt
  simulation/replay/real, mô tả thực tế của autopilot, và chỉ dùng numerical
  claim đã có trong FACT-SHEET.
- `QNA.md`: trả lời về methodology, demo, order ingest/background ingest/
  snapshot, autopilot, intent limitation, và live-fire; không nói v2 là mặc
  định hay tự ghim production trên mọi platform.
- `FREEZE.md`: danh sách claim đã chốt với revision/date/evidence và các claim
  bị cấm thay đổi trước demo. Nó không thay PREREGISTRATION và không sửa
  methodology.

### P0-2 — Establish source of truth trước khi viết claim

Chạy theo thứ tự, ghi output có cấu trúc vào artifact tạm dùng để soạn
FACT-SHEET (không commit raw logs/bí mật):

1. `python -m pytest -m "not slow" --collect-only -q` và
   `python -m pytest -m "slow and not browser" --collect-only -q`,
   `python -m pytest -m browser --collect-only -q`; đối chiếu với
   `python scripts/dong_bo_so_test.py --xem-truoc`.
2. `python -m pytest -m "not slow" --cov=src/livelift --cov-report=term-missing`;
   **Python code coverage** trong fact sheet lấy từ output lệnh này, với phạm
   vi chính xác được ghi kèm. Không có ngưỡng code coverage trong config hiện
   tại thì không tự đặt ngưỡng mới. Con số này độc lập với statistical CI
   coverage và không được dùng thay thế nó.
3. `python -m pytest -m slow`; sau đó
   `python scripts/do_lai_so_hieu_chuan.py --kiem`. Nếu `--kiem` lệch JSON,
   dừng cập nhật claim số liệu, tái hiện bằng script không `--kiem` chỉ sau khi
   được phép ghi benchmark, rồi cập nhật docs AISC từ output mới. **Statistical
   CI coverage** chỉ lấy từ calibration executable này (ví dụ 96,50% nếu lệnh
   xác nhận), không lấy từ pytest `--cov`.
4. Đếm incidents bằng parser minh bạch của bảng `docs/incident-log.md` (bỏ
   header/separator, kiểm một dòng = một incident); thêm test/script nhỏ chỉ
   nếu chưa có một lệnh tái lập được. Không dùng số 60/58/41 trong tài liệu cũ
   làm nguồn.
5. Xác minh live-fire bằng source `docs/benchmarks/live-fire-da-nguon.md` và
   command `python scripts/live_fire_da_nguon.py --api <API sạch> bang` khi
   environment/corpus hợp lệ; fact sheet ghi rõ đây là replay/VOD quan sát.
6. Lấy số real randomized sessions từ API/store trên môi trường được kiểm tra,
   lọc `is_demo=false` và loại replay/quan sát theo semantic của API. Khi chưa
   có bằng chứng khác, value phải là `0` với nhãn “chưa có phiên randomized
   thật”, không dùng demo seed để thay thế.

Chỉ sau bước này cập nhật **các tệp AISC package**. Không dọn lịch sử Sáng tạo
trẻ, README toàn repo, thuyết minh, hay tài liệu cuộc thi khác trong scope này.

### P0-3 — Reliability tối thiểu cho demo

1. Sửa `web/src/app/ket-qua/page.tsx` để khi bản gộp **real** chưa có dữ liệu
   đủ điều kiện, CTA nổi bật xuất hiện trước verdict:

   > Chưa có kết quả thử nghiệm thật. Xem 3 kịch bản Demo Vàng: Dương rõ ·
   > Chưa kết luận · Chưa đủ dữ liệu.

   CTA phải mở/đi tới các session demo được resolve runtime, hoặc `env=demo`
   với nhãn rõ `DEMO/MÔ PHỎNG`. Nó không đổi request mặc định `env=real`, không
   che state 0 real sessions, và không hard-code UUID.
2. Thêm/điều chỉnh test ở `tests/test_web_ket_qua.py` (và API test chỉ khi
   cần một contract mới) để khóa các invariant: real default remains real; CTA
   chỉ hiện khi real chưa đủ; demo luôn nhãn; không UUID cố định; real-summary
   vẫn nêu 0/insufficient thật.
3. Sửa copy lock trong `web/src/components/ActionCard.tsx` hoặc nguồn
   `actionLockReason` ở `web/src/components/BlockClock.tsx`, tùy nơi render
   thực tế, thành ý nghĩa: “KHỐI ĐỐI CHỨNG — hệ thống cố ý không đưa gợi ý.
   Hãy vận hành như bình thường để đo mức nền.” Không redesign desk, không đổi
   assignment/action behavior. Cập nhật unit/source test UX thích hợp.

### P0-4 — Round 2 demo check không phá huỷ

Thêm `scripts/round2_demo_check.py` và test cho logic HTTP/selection (ví dụ
`tests/test_round2_demo_check.py`). Thiết kế:

- Mặc định chỉ GET/read: services reachable, API contracts, `/health`, database
  mode/durable/storage response, Demo Vàng tồn tại và có nhãn `is_demo`, phiên
  demo live fresh, current block hợp lệ, stale session không phải session được
  resolve, và URL presenter phải mở.
- Resolve session runtime từ API: chọn phiên `is_demo=true`, `status=live`, có
  `start_ts/end_ts` bao quanh thời gian hiện tại và block hiện tại hợp lệ; không
  hard-code UUID. Một session hết giờ/`NGOÀI KHỐI` là FAIL, không phải WARN.
- Script hoàn toàn read-only: không POST seed, không start/stop compose, không
  xoá session và không reset DB. Nếu thiếu Demo Vàng/phiên live fresh, bảng
  FAIL phải in lệnh chuẩn bị để người vận hành chủ động chạy riêng.
- Hỗ trợ `--base` qua Caddy (`http://localhost` => API `/api`) và `--api` /
  `--web` cho development (`:8000`/`:3000`); in chính các URL presenter nên
  mở, do đó không còn mâu thuẫn cổng trong package AISC.
- Kết thúc bằng bảng `CHECK | PASS/FAIL | evidence | presenter action`, exit
  non-zero khi một gate chặn fail. “Không đo được” không chuyển thành PASS.
- Đây là preflight HTTP/API, không phải browser E2E framework. HTTP 200 không
  được diễn đạt thành UI “usable”; UI correctness được xác minh bằng browser
  tests hiện có hoặc manual rehearsal. Không thêm browser framework mới.

### P0-5 — Claims AISC khớp code

Trong FACT-SHEET/PITCH/QNA/README AISC:

- Nói order ingestion **đã có** endpoint đơn lẻ và CSV, nhưng chưa có file
  đơn hàng thật/claim performance thật được xác minh.
- Nói background ingest manager và memory snapshot tồn tại; snapshot không
  được diễn đạt như Postgres durability.
- Nói autopilot nội bộ có thể quyết định/ghi exposure theo session auto; không
  nói đã ghim thành công lên mọi nền tảng. Shopee adapter chỉ được mô tả ở đúng
  mức adapter/credential/integration evidence hiện có.

### P0-6 — Mandatory production web build

Vì P0 sửa Next.js UI, `cd web && npm ci && npm run build` là gate P0 bắt buộc.
Không được gọi P0 hoàn thành nếu production build fail.

### HUMAN-DEPENDENT P0

Các việc dưới đây là P0 vận hành cần con người/credential, không phải DEFER.
Codex không tự tạo, giả lập hay ghi PASS cho evidence này:

- lấy official platform credential;
- chạy official ingest smoke test;
- chạy bền vững trên Postgres;
- nếu khả thi trước Round 2, thử ít nhất một real end-to-end randomized pilot.

Khi chưa có evidence, FACT-SHEET tiếp tục ghi **0 real randomized sessions** và
trạng thái BLOCKED/NOT RUN thích hợp.

## P1

- Nếu P0 baseline pass, bổ sung test contract cho checker ở Caddy và split-port
  URL. Không thêm browser framework hay test mới chỉ để nâng “số test”.
- Nếu có dev server được chủ động bật để kiểm tra, dùng existing browser tests
  hoặc manual rehearsal cho `/desk`, `/host`, `/ket-qua` theo session runtime.
  Không tự khởi động server trong checker và không thêm browser framework.
- Chạy `docker compose config`, và nếu Postgres sẵn có `pytest -m db
  tests/test_store_contract.py`. Mỗi kết quả được ghi Pass/Fail/Not run trong
  FREEZE/FACT-SHEET với command và ngày; không ghi PASS cho command chưa chạy.

## DEFER

- Production Shopee pinning, reconciliation đơn hàng thật, OAuth/multi-tenant,
  queue/scale, và các cải tiến screenshot/hướng dẫn ngoài AISC package. Việc
  xin credential, official ingest smoke test, Postgres durable run và cố gắng
  chạy real pilot nằm ở HUMAN-DEPENDENT P0 phía trên, không phải DEFER.
- Thay đổi methodology, estimator, switchback, block length/burn-in, hoặc
  preregistration: chỉ xử lý nếu có bug tái hiện được và theo HARNESS; không
  nằm trong triển khai Round 2 này.

## REJECTED

- Không đổi branch, merge main, push/force-push.
- Không TikTok scraping hay mở rộng collector không chính thức.
- Không train/nâng NLP, không đổi Intent v2 thành mặc định.
- Không redirect `/ket-qua` mặc định sang demo, không biến DEMO/MÔ PHỎNG thành
  real data, và không che giấu 0 randomized real sessions.
- Không dashboard/rework UI/refactor ngoài CTA và copy lock cần thiết.

## Verification bắt buộc sau implementation

Chỉ ghi trạng thái sau khi chạy thật trên đúng revision:

```bash
python -m pytest -m "not slow" --collect-only -q
python -m pytest -m "slow and not browser" --collect-only -q
python -m pytest -m browser --collect-only -q
python scripts/dong_bo_so_test.py --xem-truoc
python -m pytest -m "not slow" --cov=src/livelift --cov-report=term-missing
python -m pytest -m slow
python scripts/do_lai_so_hieu_chuan.py --kiem
ruff check src tests
ruff format --check src tests
ruff check scripts/round2_demo_check.py
ruff format --check scripts/round2_demo_check.py
(cd web && npm ci && npm run build)
docker compose config
pytest -m db tests/test_store_contract.py  # chỉ khi Postgres đã sẵn có
python scripts/round2_demo_check.py --base http://localhost
```

Nếu dùng development split ports, thay lệnh cuối bằng:

```bash
python scripts/round2_demo_check.py --api http://127.0.0.1:8000 --web http://127.0.0.1:3000
```

## File dự kiến sửa/tạo

| File | Thay đổi tối thiểu |
|---|---|
| `docs/competition/aisc-round2/{README,FACT-SHEET,ROADMAP,DEMO-GATES,PITCH,QNA,FREEZE}.md` | Tạo package AISC độc lập và claims có evidence. |
| `web/src/app/ket-qua/page.tsx` | CTA Demo Vàng có nhãn, chỉ khi real chưa đủ; giữ default real. |
| `web/src/components/ActionCard.tsx` **hoặc** `web/src/components/BlockClock.tsx` | Copy khối đối chứng ở đúng render point. |
| `scripts/round2_demo_check.py` | Preflight/check AISC read-only mặc định, resolution session runtime. |
| `tests/test_web_ket_qua.py` | Regression cho honesty/default/CTA demo. |
| `tests/test_round2_demo_check.py` | Regression checker/URL/session selection; tạo mới. |
| Test copy lock hiện hữu gần component được chọn | Cập nhật assertion hẹp nếu đã có. |

Không có file statistical core, intent model, scraper, migration, compose config,
hay tài liệu lịch sử khác trong danh sách dự kiến.
