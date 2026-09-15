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
| T−2h | Kiểm tra pipeline: **khởi động runner ingest và xác nhận heartbeat** (xem 1.4), CSDL ghi được, bộ lọc PII hoạt động (bơm 3 bình luận thử có SĐT giả → phải ra `[SĐT]`) | KS |
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
# API đi qua Caddy với tiền tố /api; dev trên cùng máy: http://localhost/api/shortlinks
curl -X POST https://<DOMAIN>/api/shortlinks \
  -H "Content-Type: application/json" \
  -d '{
    "product_id": "SKU-001",
    "session_id": "<session_id>",
    "target_url": "https://<trang-san-pham>?utm_source=livestream&utm_medium=<nen-tang>&utm_campaign=<session_id>&utm_content=SKU-001"
  }'
```

Kiểm tra từng link: mở `https://<DOMAIN>/r/{code}` **từ mạng ngoài (4G trên điện thoại)**
→ phải chuyển hướng đúng trang sản phẩm và sinh một dòng `click_event`. Link này là link
**duy nhất** được ghim trong bình luận / overlay trong phiên — tuyệt đối không dán link
gốc (link gốc không đo được).

Dòng sinh ra khi kiểm tra mang cờ hợp lệ (tiền đăng ký §4.1): bấm lại cùng một link trong
vòng 10 giây sẽ được ghi với `is_valid=false, invalid_reason='refractory'` — **đúng như
thiết kế**, không phải lỗi. Kiểm tra bằng `curl` cũng bị gắn cờ (`givt_ua`): muốn xác nhận
đường redirect thì đọc mã 302, muốn xác nhận click hợp lệ thì bấm bằng trình duyệt thật.
Mọi dòng kiểm tra T−24h xảy ra trước `start` nên rơi ngoài mọi khối đo và KHÔNG vào biến
kết quả; chúng vẫn hiện trong tổng vận hành `raw_clicks`/`valid_clicks` — đúng tinh thần
flag-don't-drop, đừng xóa chúng đi.

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

### 1.4 Khởi động ingest (T−2h) — heartbeat và xử lý khi runner chết

Runner ingest chạy **một tiến trình cho mỗi phiên live** (trên máy vận hành hoặc VPS),
đọc bình luận + số người xem từ nền tảng, lọc PII ngay trong tiến trình rồi mới gửi về API:

```bash
# Env cần thiết (đọc từ .env tại thư mục chạy lệnh):
#   - YouTube:  YOUTUBE_API_KEY  (nếu chưa có key: xem "hai đường" ngay bên dưới)
#   - Facebook: FACEBOOK_PAGE_ACCESS_TOKEN (+ FACEBOOK_GRAPH_VERSION)
#   - INGEST_TOKEN: BẮT BUỘC khi API có địa chỉ công khai. Một token duy nhất bảo
#     vệ cả 15 endpoint ghi (gói VÁ-XÁC-THỰC 14/09/2026); để trống = tắt kiểm tra
#     hoàn toàn. Runner tự đính header Authorization: Bearer <token>.
#     Chi tiết: docs/competition/sang-tao-tre-2026/08-VA-XAC-THUC.md
python -m livelift.ingest.runner \
  --platform youtube \
  --source-id <VIDEO_ID> \
  --session-id <session_id> \
  --api-url https://<DOMAIN>/api
```

- `--platform`: `youtube` hoặc `facebook`; `--source-id` là YouTube video id /
  Facebook live-video id.
- `--api-url`: qua Caddy dùng `https://<DOMAIN>/api`; dev trên cùng máy dùng
  `http://localhost/api` (hoặc `http://localhost:8000` khi bật cổng dev DEV_PORTS).

#### YouTube — hai đường, chọn bằng `INGEST_YOUTUBE_BACKEND`

| | `api` (mặc định) | `ytdlp` |
|---|---|---|
| Cần gì | `YOUTUBE_API_KEY` | **không cần gì** |
| Độ trễ giao tin (đo thật) | 2–5 s | **~24 s (p50), 37 s (p90)** |
| Điều khoản dịch vụ | hợp lệ | **KHÔNG hợp lệ** — xem cảnh báo bên dưới |

**A. Có API key — đường chuẩn, dùng cho phiên thí nghiệm chính thức.**
Không phải đặt gì thêm (`api` là mặc định). Chỉ cần `YOUTUBE_API_KEY` trong `.env`.

**B. Chưa có API key — đường dự phòng bằng yt-dlp** (chạy được ngay, không
credential; yt-dlp đã có sẵn trong venv):

```bash
# Linux/macOS
INGEST_YOUTUBE_BACKEND=ytdlp python -m livelift.ingest.runner \
  --platform youtube --source-id <VIDEO_ID> --session-id <session_id> --api-url http://localhost:8000

# Windows PowerShell
$env:INGEST_YOUTUBE_BACKEND="ytdlp"; python -m livelift.ingest.runner `
  --platform youtube --source-id <VIDEO_ID> --session-id <session_id> --api-url http://localhost:8000
```

> ⚠️ **Cách truy cập này TRÁI Điều khoản dịch vụ của YouTube.** robots.txt của
> YouTube chặn đúng hai đường yt-dlp gọi (`/live_chat`, `/youtubei/`), và ToS chỉ
> miễn trừ truy cập tự động cho "công cụ tìm kiếm công khai theo robots.txt".
> Chỉ dùng cho **phiên của chính nhóm**, kiểm thử kỹ thuật, hoặc **dự phòng khi
> key chết giữa phiên**. Nếu dữ liệu này vào bài báo thì **phải khai báo phương
> pháp thu thập**, không được trình bày như dữ liệu API. Bằng chứng đầy đủ:
> [docs/research/2026-09-09-youtube-ytdlp-live.md](../../docs/research/2026-09-09-youtube-ytdlp-live.md).
> **Việc cần làm song song:** xin `YOUTUBE_API_KEY` (miễn phí, không cần thẻ,
> không cần app review, ~10 phút trong Google Cloud Console) rồi quay về `api`.

Kiểm tra nhanh trước khi chạy đường `ytdlp` (phải in `is_live|<số>|youtube_live_chat`):

```bash
yt-dlp --skip-download --print "%(live_status)s|%(concurrent_view_count)s|%(subtitles.live_chat.0.protocol)s" \
  "https://www.youtube.com/watch?v=<VIDEO_ID>"
```

Ba khác biệt vận hành **phải biết** khi chạy `ytdlp`:

1. **Chạy runner quá khối cuối ít nhất 1 phút.** Bình luận về chậm ~25 s; dấu
   thời gian vẫn là giờ YouTube nên **không lệch khối**, nhưng tắt sớm thì mất đuôi.
2. **Bảng điều khiển chậm ~25 s** so với phòng chat — đừng tưởng hệ thống chết.
3. **Kênh ẩn số người xem** thì không có tick nào (hệ thống **không ghi số 0 giả**);
   heartbeat sẽ báo `Kênh này ẩn số người xem đồng thời…` và ma trận tín hiệu
   đánh dấu `ticks` THIẾU. Khi đó *không* kết luận được "nhịp phiên" hay CTR.
4. Nếu heartbeat báo *"YouTube yêu cầu xác minh không phải bot"*: đặt
   `YTDLP_COOKIES_FROM_BROWSER=chrome` (hoặc `edge`/`firefox`) trong `.env` rồi
   chạy lại runner.
5. **Dừng runner bằng Ctrl+C, đừng kill cứng.** Ctrl+C thì runner tự xóa file
   chat thô tạm (file này có **tên người bình luận**). Nếu bị kill cứng (mất
   điện, `kill -9`, container bị kill) thì file còn lại trong thư mục tạm của
   máy; lần chạy runner sau sẽ tự dọn (thư mục `livelift-ytchat-*` không được
   ghi quá 30 phút). Muốn dọn tay ngay:
   `python -c "from livelift.ingest.youtube_ytdlp import sweep_stale_temp_dirs as s; print(s())"`

**Facebook — bắt buộc chạy trước khi phát (30 giây):**

```bash
python scripts/kiem_tra_facebook.py     # phải in "KẾT LUẬN: SẴN SÀNG"
```

Script kiểm tra token còn hạn, đủ quyền (`pages_read_user_content` là quyền hay
thiếu nhất — thiếu nó thì **không đọc được bình luận nào**), Page đọc được, buổi live
đang phát và in luôn `Live video id` để dán vào `--source-id`. Cách lấy/gia hạn token:
[docs/huong-dan-facebook-token.md](../../docs/huong-dan-facebook-token.md).

**Kiểm tra heartbeat:** mỗi 60 giây runner in đúng một dòng dạng:

```
heartbeat: comments seen=12 posted=12 | ticks seen=4 posted=4 | failures=0 | tải API: 12% | lỗi gần nhất: không có
```

Điều kiện đạt ở T−2h (sau khi bơm 3 bình luận thử): có dòng heartbeat, `posted` bám sát
`seen`, `failures=0`, `lỗi gần nhất: không có`. Nếu `lỗi gần nhất` khác "không có"
(token hết hạn, cạn quota...) → xử lý xong mới được phát.

**Khi runner chết giữa phiên:**

1. **Khởi động lại ngay** bằng đúng lệnh trên. Server có khóa idempotency
   (comment theo `(platform, ext_id)`, tick theo `(session, ts_bucket)`) nên gửi trùng
   an toàn — không sinh bản ghi đôi.
2. **Backfill phần API không nhận được:** những bản ghi gửi hỏng đã nằm trong spool
   `data/spool/<session_id>.jsonl` (chỉ chứa dữ liệu đã lọc PII). Gửi lại bằng:

   ```bash
   python -m livelift.ingest.spool_replay data/spool/<session_id>.jsonl \
     --api-base https://<DOMAIN>/api
   ```

   Exit code 0 = mọi bản ghi đã vào API; exit code 1 = còn bản ghi lỗi — chạy lại
   lệnh sau khi API ổn định (gửi trùng vẫn an toàn nhờ idempotency).
3. **Ghi sự cố vào nhật ký phiên** (thời điểm chết / khởi động lại). QC T+30' sẽ soi
   khoảng trống dữ liệu; khối bị ảnh hưởng cân nhắc `excluded_reason` theo HARNESS §3
   — không bao giờ sửa tay số liệu.

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
| T+30' | Chạy bộ kiểm tra chất lượng dữ liệu **kèm đối soát click hợp lệ**: `livelift-qc --session-id <session_id> --recount-clicks` — mọi mục đỏ phải xử lý theo HARNESS §3 (root cause, không sửa số liệu) | KS |
| T+1h | Ghi nhật ký phiên theo mẫu `ops/templates/nhat-ky-phien.md` (kể cả mục sự cố burn-in và sự cố làm mù) | SP |
| T+24h | Cập nhật bảng theo dõi tích lũy (kế hoạch §8.4) | TN |

**Nhắc lại quy tắc dữ liệu thí nghiệm:** nếu QC phát hiện lỗi làm hỏng dữ liệu của khối/phiên
đã chạy → đánh dấu `excluded_reason`, KHÔNG sửa số liệu, ghi quyết định vào phụ lục phân tích
và `docs/incident-log.md`.

**Về `--recount-clicks` (click hợp lệ, tiền đăng ký §4.1):** bước này chạy lại các quy tắc
thời gian (refractory τ, trần số lượng) trên toàn bộ click của phiên và **chỉ cập nhật cờ**
`is_valid`/`invalid_reason` — không bao giờ xóa dòng nào (flag-don't-drop). Nó in kèm bảng
sensitivity τ ∈ {5, 30, 60} giây: chép cả ba con số vào nhật ký phiên. Số click bị gắn cờ
tăng đột biến so với các phiên trước là **tín hiệu vận hành** (bot/prefetch), không phải lý
do để sửa dữ liệu.
