# VLiveBench — bộ thu thập phòng live TikTok công khai (CÁCH LY)

## Mục đích

Thu thập bình luận từ **20–30 phòng livestream bán hàng công khai** trên TikTok để xây
bộ dữ liệu VLiveBench, phục vụ **duy nhất một việc**: huấn luyện/đánh giá bộ phân loại
ý định bình luận tiếng Việt (intent classifier). Dữ liệu này **không** đi vào hệ thống
thí nghiệm, **không** vào DB của LiveLift, và các phiên thí nghiệm chính thức **không
phụ thuộc** vào bộ thu thập này — nếu nó hỏng, thí nghiệm không bị ảnh hưởng.

## Lưu ý pháp lý & rủi ro (đọc trước khi chạy)

- Thư viện `TikTokLive` là dự án **dịch ngược (reverse-engineered)** giao thức Webcast,
  **không phải API chính thức** — TikTok có thể làm nó ngừng hoạt động bất cứ lúc nào,
  và việc dùng có thể vi phạm điều khoản dịch vụ của TikTok. Nhóm chấp nhận rủi ro này
  CHỈ cho việc đọc phòng công khai, ẩn danh, không đăng nhập; **tuyệt đối không** gắn
  tài khoản shop/creator của nhóm vào công cụ này.
- **PII được lọc ngay tại thời điểm thu** (`livelift.ingest.pii.scrub` chạy trước lệnh
  ghi): số điện thoại, email, mã đơn, địa chỉ, tên bị thay bằng nhãn. Văn bản thô
  không bao giờ chạm đĩa. Không lưu định danh người bình luận.
- Dữ liệu thu được nằm trong `data/` (đã gitignore) — **không commit dữ liệu**.

## Cách ly kiến trúc

Đây là dự án con độc lập: **venv riêng, requirements riêng, process riêng**.
Quy tắc một chiều: `collectors/` được phép import `livelift` (để dùng bộ lọc PII);
`src/livelift/` **không bao giờ** được import từ `collectors/` — CI quét và chặn.

## Cài đặt

```bash
cd collectors/tiktok_public
python -m venv .venv
.venv\Scripts\activate            # Windows — Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
pip install -e ../..              # cài livelift (chỉ để dùng bộ lọc PII)
```

## Chạy

```bash
python collect.py --username ten_kenh_cong_khai --max-minutes 90
```

- Mỗi lần kết nối tạo một file JSONL mới trong `data/`:
  `data/<room>_<UTC timestamp>.jsonl`, mỗi dòng
  `{"ts": ..., "room": ..., "text_scrubbed": ..., "event_type": ..., "value": ...}`.
- Tự kết nối lại khi rớt (backoff lũy tiến); Ctrl+C dừng sạch.
- `--max-minutes` giới hạn tổng thời gian thu một phòng.
