# LiveLift

**Nền tảng Thí nghiệm Vận hành cho Livestream Thương mại** — dự thi AISC'26, bảng Data Driven Business.

LiveLift biến mỗi quyết định trong phiên livestream (ghim sản phẩm nào, lúc nào) thành một thí nghiệm đo được, bằng thiết kế luân phiên theo khối thời gian (switchback) hai tầng, với nhật ký can thiệp có ghi xác suất gán.

Tài liệu gốc: `../LiveLift-Mo-Ta-Du-An-Ban-Trien-Khai (1).md` (mô tả dự án) và `../LiveLift-Ke-Hoach-Trien-Khai.md` (kế hoạch).
Quy trình phát triển: xem [HARNESS.md](HARNESS.md).

## Khởi động nhanh

```bash
cp .env.example .env       # sửa POSTGRES_PASSWORD
docker compose up -d       # db + redis + migrate + api + web
# API:  http://localhost:8000/docs
# Web:  http://localhost:3000
```

Phát triển ngoài Docker (chỉ cần Python 3.11+):

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows — Linux/macOS: source .venv/bin/activate
pip install -e ".[dev,server,ml]"
pytest                            # toàn bộ kiểm thử lõi, không cần DB
pytest -m "not slow"              # nhanh (< 1 phút)
```

## Cấu trúc kho mã

```
livelift/
├── docker-compose.yml
├── PREREGISTRATION.md         # tiền đăng ký phân tích — KHÓA sau tuần 6
├── HARNESS.md                 # quy trình phát triển, quality gates
├── migrations/                # SQL migrations (up/down), chạy bằng livelift-migrate
├── src/livelift/
│   ├── config.py              # cấu hình (pydantic-settings, đọc từ env)
│   ├── ingest/
│   │   ├── events.py          # mô hình sự kiện chuẩn hóa chung cho mọi nguồn
│   │   ├── youtube.py         # YouTube Live Chat qua API chính thức
│   │   ├── facebook.py        # Facebook Graph API (Page của nhóm)
│   │   └── pii/               # BỘ LỌC PII — chạy TRƯỚC mọi lần ghi, không ngoại lệ
│   ├── core/
│   │   ├── assigner/          # bộ gán ngẫu nhiên hai tầng (outer switchback + inner)
│   │   ├── features.py        # chuẩn hóa sự kiện → khung 30 giây (session_tick)
│   │   └── quality.py         # bộ kiểm tra chất lượng dữ liệu sau phiên (mục 8.3)
│   ├── analysis/
│   │   ├── estimators.py      # ITT (kiểm định ngẫu nhiên hóa), LATE (IV), CUPED
│   │   └── power.py           # bảng MDE, hệ số thiết kế, pha loãng tuân thủ
│   ├── sim/                   # bộ mô phỏng phiên live — thẩm định ước lượng viên
│   ├── dbops/                 # migration runner, kết nối DB
│   └── api/                   # FastAPI: REST + WebSocket cho bàn trung control
├── collectors/tiktok_public/  # VLiveBench — CÁCH LY: không được import bởi src/
├── web/                       # Next.js — bàn trung control ba vùng
├── analysis/                  # notebook (calibration/, exploration/) — khóa theo tiền đăng ký
├── ops/                       # runbook phiên live, mẫu nhật ký, thư đối tác
└── tests/                     # pytest — xem HARNESS.md về quality gates
```

**Nguyên tắc cách ly:** `collectors/tiktok_public/` là dự án con độc lập (requirements riêng, process riêng). CI có kiểm tra tự động: bất kỳ `import` nào từ `src/livelift` sang `collectors/` là lỗi build. Nếu thư viện đọc phòng công khai hỏng, hệ thống lõi không bị ảnh hưởng.

**Nguyên tắc PII:** bình luận thô không bao giờ chạm đĩa. `ingest/pii/` chạy trong tiến trình ingest, trước lệnh ghi. Bộ kiểm thử PII (`tests/test_pii_filter.py` + `tests/data/pii_comments.jsonl`) là quality gate: recall < 95% → CI đỏ.

## Lệnh thường dùng

| Lệnh | Việc |
|---|---|
| `livelift-migrate up` / `down 1` / `status` | chạy / lùi / xem migration |
| `livelift-schedule --session-id S --duration 90 --block 10 --washout 2 --seed ...` | sinh lịch gán khối TRƯỚC phiên |
| `livelift-simulate --sessions 30 --effect 0.15` | mô phỏng chuỗi phiên, thẩm định ước lượng viên |
| `livelift-qc --session-id S` | kiểm tra chất lượng dữ liệu sau phiên |
| `pytest -m "not slow"` | kiểm thử nhanh |
| `ruff check src tests && ruff format --check src tests` | lint + format |
