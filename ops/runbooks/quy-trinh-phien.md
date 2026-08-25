# Runbook vận hành một phiên livestream

*Chuẩn hóa từ kế hoạch triển khai §6, cập nhật theo báo cáo tổng hợp nghiên cứu 24/08/2026
(`docs/research/2026-08-24-bao-cao-tong-hop-nghien-cuu.md`). Quy trình này lặp lại ~30 lần.
Phải chuẩn hóa đến mức người chưa từng làm cũng chạy được.*

---

## Nguyên tắc bất biến (đọc trước mỗi phiên)

1. **Lịch gán khối được sinh và lưu vào CSDL TRƯỚC khi phát sóng.** Không bao giờ sinh trong
   lúc đang phát. Phiên không có lịch gán đã lưu trong `experiment_block` thì **không được
   bấm "Go live"** — đây là điều bảo đảm tính ngẫu nhiên hóa không bị can thiệp, và là điều
   giám khảo sẽ hỏi.
2. **Host bị làm mù hoàn toàn với thiết kế thí nghiệm** (giao thức mục "Làm mù" bên dưới).
3. **Chỉ ba lý do được phép can thiệp thủ công:** `hết hàng`, `sai giá`, `sự cố kỹ thuật`.
   Hệ thống từ chối mọi lý do khác. Can thiệp ngoài ba lý do này làm hỏng tính tuân thủ
   của thí nghiệm.
4. **Click sản phẩm chỉ được đo qua redirect tự host** `/r/{code}` (shortlink UTM). Không có
   shortlink thì không có biến kết quả — bước T−24h bắt buộc.
5. Mọi timestamp ghi bằng đồng hồ server (UTC, `timestamptz`). Không tin đồng hồ máy khách.

---

## 1. Trước phiên

| Mốc | Việc | Người |
|---|---|---|
| T−24h | Chốt danh mục sản phẩm, kiểm tra tồn kho, nạp vào bảng `product` | SP |
| T−24h | **Tạo shortlink UTM cho từng sản phẩm của phiên** (xem 1.1) | KS |
| T−24h | Đặt quảng cáo phiên live, ngân sách theo kế hoạch | SP |
| T−2h | Kiểm tra pipeline: ingest chạy, CSDL ghi được, bộ lọc PII hoạt động (bơm 3 bình luận thử có SĐT giả → phải ra `[SĐT]`) | KS |
| T−1h | **Sinh lịch gán khối và lưu vào `experiment_block`** (xem 1.2) | TN |
| T−30' | Kiểm tra thiết bị: camera, âm thanh, ánh sáng, mạng dự phòng | SP |
| T−15' | Mở bàn trung control, xác nhận chế độ đúng (tự động cho Live Lab); **mở màn hình host ở route `/host`** và kiểm tra giao thức làm mù (xem 1.3) | SP |
| T−5' | Xác nhận thông báo xử lý dữ liệu hiển thị trong phòng | SP |

### 1.1 Tạo shortlink UTM (T−24h) — định nghĩa vận hành của "click"

Đây là lời giải cho lỗ hổng L5 (biến kết quả chính chưa đo được trên Facebook Live):
**một click = một request đến redirect tự host `/r/{code}`**, ghi vào `click_event` với
timestamp server và gán về khối đang chạy.

Với **mỗi sản phẩm** trong danh mục phiên, gọi API tạo shortlink:

```bash
curl -X POST http://localhost:8000/shortlinks \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "SKU-001",
    "session_id": "<session_id>",
    "target_url": "https://<trang-san-pham>?utm_source=livestream&utm_medium=<nen-tang>&utm_campaign=<session_id>&utm_content=SKU-001"
  }'
```

Kiểm tra từng link: mở `http://<host>/r/{code}` → phải chuyển hướng đúng trang sản phẩm
và sinh một dòng `click_event`. Link này là link **duy nhất** được ghim trong bình luận /
overlay trong phiên — tuyệt đối không dán link gốc (link gốc không đo được).

### 1.2 Sinh lịch gán khối (T−1h) — BẮT BUỘC trước phát sóng

```bash
# Ví dụ phiên 90 phút, khối 5 phút, KHÔNG washout thiết kế (burn-in xử lý ở phân tích),
# jitter ranh giới ±30 giây, khối đầu/cuối tự nhân đôi (quy tắc 2m):
livelift-schedule --duration 90 --block 5 --washout 0 --jitter 30 \
  --out schedule-<session_id>.json
```

- Nếu không truyền `--seed`, seed được rút từ nguồn entropy hệ điều hành và **in ra — phải
  ghi lại**. Seed lưu cùng lịch trong cột `design` của `live_session`.
- Nạp JSON vào CSDL (`experiment_block` + `live_session.design`) qua API hoặc script nạp.
- **Xác nhận trước khi phát:** `SELECT count(*) FROM experiment_block WHERE session_id = ...`
  phải bằng số khối trong file JSON, và `live_session.design` khác NULL.
- Sau khi lưu, **không ai xem trước chuỗi BẬT/TẮT** ngoài hệ thống thực thi. Operator không
  in lịch ra giấy, không mở JSON trong phiên.

### 1.3 Giao thức làm mù (nghiên cứu L6 — ghi trong tiền đăng ký)

Host hào hứng hơn trong khối BẬT là kênh nhiễu trực tiếp lên tỷ lệ nhấp; khi đó ta đo
"hệ thống + tâm lý host" chứ không phải hệ thống. Vì vậy:

- **Màn hình host = route `/host` DUY NHẤT.** Màn hình này chỉ hiện: sản phẩm đang ghim,
  giá, tồn kho, tổng thời gian đã trôi của phiên. **Không** hiện: ranh giới khối, nhánh
  BẬT/TẮT, thời-gian-còn-lại-của-khối, đếm ngược, hay bất kỳ thứ gì suy ra được trạng thái khối.
- Host **không được nhìn** màn hình operator/bàn trung control. Bố trí máy operator ngoài
  tầm nhìn host (quay lưng hoặc phòng khác).
- Operator **không đọc to** trạng thái khối, không đếm ngược chuyển khối, không thay đổi
  cử chỉ/giọng nói giữa khối BẬT và TẮT. Trong khối TẮT, operator không bình luận gì về hệ thống.
- Mọi vi phạm làm mù (host nhìn thấy màn hình operator, ai đó nói "sắp đổi khối"...) phải
  ghi vào nhật ký phiên, mục **"Sự cố làm mù"** — trung thực, không giấu; khối liên quan
  sẽ được cân nhắc `excluded_reason` khi phân tích.

## 2. Trong phiên

| Việc | Người |
|---|---|
| Host dẫn phiên theo run sheet, chỉ nhìn màn hình `/host` | SP hoặc NC |
| Hệ thống tự thực thi hành động (ghim) trong khối BẬT | Tự động |
| Người trực kỹ thuật theo dõi log, **không can thiệp trừ lỗi** | KS |
| Ghim shortlink `/r/{code}` của sản phẩm đang lên sóng vào bình luận | Operator |
| Mọi can thiệp thủ công ghi lý do vào `override_reason` | Người can thiệp |

**Chỉ ba lý do được phép can thiệp thủ công** (validation ở tầng API — giá trị khác bị từ chối):

1. `hết hàng`
2. `sai giá`
3. `sự cố kỹ thuật`

Mỗi can thiệp tự động ghi: `block_id`, timestamp server, `source='human'`,
`override_reason`, `seconds_since_last_switch`. Không cần (và không được) sửa tay.

## 3. Sau phiên

| Mốc | Việc | Người |
|---|---|---|
| T+15' | Chạy tác vụ tổng hợp: sinh `session_tick`, đối soát đơn hàng với báo cáo nền tảng | KS |
| T+30' | Chạy bộ kiểm tra chất lượng dữ liệu: `livelift-qc --session-id <session_id>` — mọi mục đỏ phải xử lý theo HARNESS §3 (root cause, không sửa số liệu) | KS |
| T+1h | Ghi nhật ký phiên theo mẫu `ops/templates/nhat-ky-phien.md` (kể cả mục sự cố burn-in và sự cố làm mù) | SP |
| T+24h | Cập nhật bảng theo dõi tích lũy (kế hoạch §8.4) | TN |

**Nhắc lại quy tắc dữ liệu thí nghiệm:** nếu QC phát hiện lỗi làm hỏng dữ liệu của khối/phiên
đã chạy → đánh dấu `excluded_reason`, KHÔNG sửa số liệu, ghi quyết định vào phụ lục phân tích
và `docs/incident-log.md`.
