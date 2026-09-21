# Demo gates — AISC Round 2

## 1. Chọn đúng topology

- Docker/Caddy: web `http://localhost`, API `http://localhost/api`.
- Development split ports: web `http://127.0.0.1:3000`, API
  `http://127.0.0.1:8000`.

Không trộn URL của hai topology trong cùng một lần diễn tập.

## 2. Chuẩn bị do người vận hành chủ động

Chế độ mặc định không seed. Khi chủ động cho phép ghi **chỉ dữ liệu mô phỏng**,
dùng cùng checker với opt-in rõ ràng:

```bash
python scripts/round2_demo_check.py --base http://localhost --prepare-demo
```

Với split ports, truyền thêm `--prepare-demo` vào lệnh `--api`/`--web` ở dưới.
Tuỳ chọn này chỉ gọi `POST /demo/seed-vang` (idempotent theo API) và
`POST /demo/seed` để tạo phiên demo live mới, rồi chạy nguyên bộ preflight.
Nó không reset kho, xoá/kết thúc phiên, hay chạm dữ liệu randomized thật.

## 3. Chạy read-only preflight

```bash
python scripts/round2_demo_check.py --base http://localhost
```

Hoặc split ports:

```bash
python scripts/round2_demo_check.py \
  --api http://127.0.0.1:8000 \
  --web http://127.0.0.1:3000
```

Checker xác nhận services/API contracts, health/storage, Demo Vàng, phiên demo
live còn trong duration, current block hợp lệ và URL runtime. Nó không tuyên bố
UI usable chỉ vì HTTP 200. `--allow-memory` chỉ dành cho rehearsal có chủ ý;
lần kiểm chính thức yêu cầu durable Postgres.

## 4. UI/browser gate riêng

```bash
.venv/bin/python -m pytest -m browser
cd web && npm ci && npm run build
```

Sau đó diễn tập thủ công: desk không `NGOÀI KHỐI`; copy OFF dễ hiểu; host không
lộ assignment; `/ket-qua` vẫn cho thấy real chưa đủ và ba link đều có nhãn
DEMO/MÔ PHỎNG. Ghi PASS chỉ khi chính bước đó đã chạy.

## 5. Presenter URLs

Không lưu UUID trong tài liệu. Dùng đúng URL mà preflight in ra cho `/desk`,
`/host` và ba phiên Demo Vàng. Nếu refresh/restart làm UUID đổi, chạy lại
preflight.
