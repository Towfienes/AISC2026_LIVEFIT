# Bộ thu thập TikTok công khai — kiểm chứng trên phiên live THẬT

*Đo ngày 09/09/2026, 23:12–23:21 giờ Việt Nam (ICT) · vùng cách ly `collectors/tiktok_public/`*

> **Kết luận một dòng:** thư viện `TikTokLive` **vẫn cài được và vẫn tìm thấy
> phòng live thật** (phát hiện đúng `@quyenleo` đang phát, lấy được `room_id`),
> nhưng **bắt tay WebSocket bị từ chối HTTP 400** ở **10/10 lần thử** trong 6
> phút — **thu được 0 bình luận**. Đường đi này **không dùng được hôm nay**;
> hồ sơ thi **không được** phụ thuộc vào nó.

## Lệnh tái lập

```bash
# 0. venv RIÊNG — TUYỆT ĐỐI không cài vào .venv của repo
python -m venv <scratch>/tiktok_venv
<scratch>/tiktok_venv/Scripts/python -m pip install "TikTokLive>=6"

# 1. Bộ lọc PII lấy từ lõi qua PYTHONPATH (không pip install -e, tránh bẩn repo)
export PYTHONPATH="D:\AISC2026\livelift\src"
export PYTHONIOENCODING=utf-8      # bắt buộc: console cp1252 sẽ vỡ ở chữ "Đ"

# 2. Dò phòng nào đang LIVE (chỉ đọc metadata công khai)
<scratch>/tiktok_venv/Scripts/python probe_live.py quyenleo phamthoaiofficial ...

# 3. Chạy chính bộ thu thập của repo, 2 phút, ghi ra ngoài repo
<scratch>/tiktok_venv/Scripts/python collectors/tiktok_public/collect.py \
    --username quyenleo --max-minutes 2 --out-dir <scratch>/tiktok_out
```

## 1. Trạng thái thư viện — còn sống, nhưng đã nhảy major version

| | |
|---|---|
| `requirements.txt` ghim | `TikTokLive>=6` |
| Bản pip cài về hôm nay | **`TikTokLive 7.0.0`** — một **major version** mới so với lúc viết |
| Cài đặt | **Thành công**, không lỗi build |
| Phụ thuộc kéo theo | `TikTokLiveProto 0.2.2`, `EulerApiSdk 0.1.0`, `websockets 17.1`, `httpx 0.28.1`, `protobuf 7.36.1` |
| API mà `collect.py` dùng | **Còn nguyên** — `TikTokLiveClient(unique_id=...)`, `CommentEvent`, `ConnectEvent`, `GiftEvent`, `RoomUserSeqEvent` đều import được trên v7 |

Nói cách khác: **`collect.py` không hỏng vì đổi API.** Nó hỏng ở tầng mạng.

> ⚠️ `requirements.txt` để `>=6` nên đã âm thầm kéo v7.0.0 về. Dù hôm nay v7
> vẫn tương thích, việc để dải mở trên một thư viện dịch ngược là rủi ro — nên
> ghim cứng khi nào đường đi này thực sự được dùng.

## 2. Kết quả thử nghiệm THẬT hôm nay

Phòng mục tiêu: **`@quyenleo`** (Quyền Leo Daily — tài khoản livestream bán hàng
lớn của Việt Nam), **đang phát công khai** tại thời điểm đo.

| Bước | Kết quả THẬT |
|---|---|
| `is_live()` | ✅ **`True`** — phát hiện đúng phòng đang phát |
| Phân giải phòng | ✅ `GET tiktok.com/@quyenleo/live` → 200; `room_id=7683530480444001031` |
| `check_alive` của TikTok | ✅ HTTP 200 |
| Máy chủ ký (Euler Stream) | ✅ HTTP 200, trả về token JWT hợp lệ |
| URL WebSocket được cấp | ⚠️ `wss://ws-fallback.eulerstream.com/` kèm thông điệp *"Connected through Euler Stream fallback proxy"* — **không phải** socket TikTok trực tiếp |
| **Bắt tay WebSocket** | ❌ **`InvalidStatusCode: server rejected WebSocket connection: HTTP 400`** (Cloudflare, `CF-RAY ... -SIN`) |
| **Số lần thử** | **10/10 thất bại** trong 2 lần chạy, trải 23:14:02 → 23:20:09 ICT |
| **Bình luận thu được** | **0** |
| **Bình luận/phút** | **0,0** |
| Tệp đầu ra | 8 tệp JSONL, **tổng 0 dòng** |

Bộ thu thập tự kết nối lại đúng như thiết kế (backoff 5s → 10s → 20s → 40s →
80s) và dừng sạch khi hết `--max-minutes`. **Lỗi không nằm ở `collect.py`.**

### Chẩn đoán: hỏng ở đâu

Chuỗi phát hiện phòng (HTTP) **hoạt động hoàn hảo**. Chỉ khâu cuối — nâng cấp
lên WebSocket — bị từ chối:

```
is_live: True
EXC TYPE : websockets.legacy.exceptions.InvalidStatusCode
EXC STR  : server rejected WebSocket connection: HTTP 400
  .status_code = 400
  .headers = Date: Wed, 09 Sep 2026 16:17:16 GMT / CF-RAY: a387808f682cce3a-SIN
```

Điểm mấu chốt: máy chủ ký **không** cấp socket TikTok trực tiếp mà đẩy sang
**proxy dự phòng** của chính Euler Stream, rồi **proxy đó** trả 400. Đây là dấu
hiệu điển hình của **tầng miễn phí/ẩn danh đang bị giới hạn hoặc đã chặn**, chứ
không phải TikTok đổi giao thức. Tài liệu TikTokLive nói khoá API chỉ để "nâng
giới hạn", nhưng **thực đo hôm nay: không có khoá thì không kết nối được.**

> `collect.py` chỉ ghi log **tên loại** ngoại lệ (`type(exc).__name__`), nên
> nhật ký vận hành chỉ hiện `InvalidStatusCode` — phải chạy chẩn đoán riêng mới
> ra mã 400. Xem đề xuất ở mục 6.

## 3. Bộ lọc PII và lược đồ bản ghi

Vì không có sự kiện thật, phần này kiểm trực tiếp hàm `_record()` mà bộ thu
thập sẽ dùng, với bình luận bán hàng tiếng Việt mô phỏng. **Đây là kiểm ngoại
tuyến, không phải dữ liệu thật** — nói rõ để không nhầm.

```json
{"ts":"2026-09-09T16:21:05+00:00","room":"quyenleo","text_scrubbed":"Shop ơi cho mình đặt 2 cái size L nhé, sđt [SĐT]","event_type":"comment"}
{"ts":"...","room":"quyenleo","text_scrubbed":"Chốt đơn! Giao về 25 [TÊN], Thanh Xuân, [TÊN] giúp mình","event_type":"comment"}
{"ts":"...","room":"quyenleo","text_scrubbed":"Mail mình là [EMAIL] nha shop, gửi hoá đơn","event_type":"comment"}
{"ts":"...","room":"quyenleo","text_scrubbed":"","event_type":"viewer_count","value":15230.0}
```

- Trường: `ts`, `room`, `text_scrubbed`, `event_type` (+ `value` khi có).
- **Không có trường định danh người bình luận** — đúng cam kết quyền riêng tư.
- Số điện thoại → `[SĐT]`, email → `[EMAIL]`, tên/địa chỉ → `[TÊN]`: **che đúng**.

### 🐞 Lỗi thật phát hiện được: mã đơn bắt đầu bằng "Đ" KHÔNG bị che

```
'Mã đơn DH20260909123 ...' -> 'Mã đơn [MÃ ĐƠN] ...'      ✅ che đúng
'Mã đơn ĐH20260909123 ...' -> 'Mã đơn ĐH20260909123 ...'  ❌ LỌT
```

Nguyên nhân: `ORDER_CONTEXT_RE` trong `src/livelift/ingest/pii/patterns.py:60`
bắt mã bằng `(?P<code>[A-Za-z0-9][A-Za-z0-9\-]{4,24})` — **chỉ ASCII**, nên mã
mở đầu bằng chữ **`Đ`** (tiền tố `ĐH` = "Đơn Hàng", cực phổ biến ở Việt Nam)
không khớp. Đây là **lỗ lọt PII thật, ảnh hưởng toàn hệ thống**, không riêng
TikTok. **Chưa sửa trong gói này** (nằm ngoài ranh giới cách ly của gói B, cần
test riêng) — xem mục 6.

## 4. Giới hạn của TikTok với tư cách nguồn dữ liệu

Kể cả khi kết nối lại được, đường đi này **vẫn** thiếu những thứ mà một thí
nghiệm nhân quả cần:

| Thứ cần | TikTok qua `TikTokLive` |
|---|---|
| Gán ngẫu nhiên / can thiệp | ❌ **Không thể** — ta chỉ đọc phòng của người khác, không điều khiển được nội dung, thời điểm hay thứ tự |
| Chuyển đổi (click, đơn, doanh thu) | ❌ **Không có** — không có tín hiệu thương mại nào |
| Số người xem đáng tin | ⚠️ Chỉ có `RoomUserSeqEvent` (đồng thời, do TikTok tự báo); **không** phải người xem duy nhất, không kiểm chứng được, và hôm nay **chưa nhận được mẫu nào** |
| Định danh người xem / dedup | ❌ **Cố tình không thu** (quyền riêng tư) → không đo được người bình luận duy nhất |
| Độ trễ / dấu thời gian sự kiện | ⚠️ `ts` là **giờ nhận của máy thu**, không phải giờ TikTok đóng dấu |
| Ổn định | ❌ Dịch ngược + phụ thuộc bên thứ ba; **hôm nay đã hỏng** |

## 5. Rủi ro pháp lý & điều khoản dịch vụ — nói thẳng

- `TikTokLive` là **dịch ngược giao thức Webcast, không phải API chính thức**.
  Dùng nó **có thể vi phạm Điều khoản dịch vụ của TikTok**. Chính tài liệu của
  dự án thượng nguồn cũng nói nó **không sẵn sàng cho production**.
- Đường đi hiện tại còn **đẩy lưu lượng qua proxy bên thứ ba** (Euler Stream) —
  tức là thêm một bên nữa vào chuỗi dữ liệu, kèm điều khoản riêng của họ. Nâng
  giới hạn thường đồng nghĩa **mở tài khoản/trả phí** cho bên thứ ba đó.
- Chỉ đọc **phòng công khai, ẩn danh, không đăng nhập**; **không** gắn tài khoản
  shop/creator của nhóm. **Không tải video** — chỉ chat/metadata.
- PII bị che **trước khi ghi đĩa**; văn bản thô không bao giờ chạm đĩa.

> Vì rủi ro ToS là **thật và không thể loại bỏ**, kết quả từ đường đi này chỉ
> nên dùng ở mức **quan sát/mô tả**, và phải **ghi rõ nguồn gốc** trong hồ sơ.

## 6. Khuyến nghị cho hồ sơ thi

**DÙNG TikTok cho:**
- **Không gì cả ở trạng thái hiện tại** — hôm nay nó thu được 0 dòng.
- Nếu sau này kết nối lại được: **chỉ** làm **kho văn bản quan sát** để
  huấn luyện/đánh giá bộ phân loại ý định tiếng Việt (đúng mục đích VLiveBench),
  và **chỉ** khi có nhãn "dữ liệu quan sát, thu thập không chính thức".

**KHÔNG DÙNG TikTok cho:**
- ❌ Bất kỳ **con số nhân quả** nào (uplift, MDE, switchback) — **không có gán
  ngẫu nhiên, không có chuyển đổi**. Đây là giới hạn *thiết kế*, không phải lỗi
  kỹ thuật, nên **kể cả khi sửa được kết nối vẫn không dùng được**.
- ❌ Bất kỳ đường đi nào mà **thí nghiệm chính phụ thuộc vào** — nó vừa chứng
  minh có thể chết bất cứ lúc nào.
- ❌ Số liệu người xem/engagement trình bày như đo lường đáng tin.

**Cách trình bày trong hồ sơ (đề xuất):** đặt TikTok vào phần **lộ trình**, nói
trung thực: *"TikTok là kênh live-commerce lớn nhất Việt Nam, nhưng không có API
công khai cho bình luận live. Chúng tôi đã hiện thực và kiểm chứng một bộ thu
thập cách ly; tính đến 09/09/2026 đường đi không chính thức bị chặn ở tầng
WebSocket (HTTP 400, 10/10 lần). Việc mở rộng sang TikTok do đó cần **TikTok
Partner/Live API chính thức**. Kết quả nhân quả của chúng tôi dựa trên các nền
tảng có API chính thức."* — Điều này biến một thất bại kỹ thuật thành **luận
điểm về tính chính trực của phương pháp**, và đó là cách trình bày đúng.

### Việc nên làm tiếp

1. **Sửa lỗ lọt PII `ĐH`** ở `patterns.py:60` (cho phép ký tự tiếng Việt ở đầu
   mã) + test hồi quy — **ưu tiên cao, ảnh hưởng mọi nguồn**, không riêng TikTok.
2. Ghim cứng `TikTokLive==7.0.0` thay cho `>=6` nếu còn giữ đường đi này.
3. Cho `collect.py` log thêm **mã trạng thái** khi lỗi là `InvalidStatusCode`
   (hiện chỉ log tên loại) — nếu không, sự cố kiểu này rất khó chẩn đoán.
4. `collect.py` tạo **một tệp JSONL rỗng mới cho mỗi lần thử lại** (hôm nay: 8
   tệp rỗng). Nên chỉ tạo tệp khi có dòng đầu tiên.
5. Không đầu tư thêm cho đến khi có quyết định về **API chính thức**.

## 7. Kiểm tra cách ly vẫn xanh

```
OK: import isolation holds — 58 files scanned under src/ (0 collectors imports);
1 files scanned under collectors/ (0 disallowed livelift imports;
allowed exception: livelift.ingest.pii).
```

Toàn bộ thử nghiệm chạy trong **venv riêng ngoài repo**; `.venv` của repo
**không** hề có `TikTokLive`/`EulerApiSdk`; không sinh `.egg-info`; không tạo
`collectors/tiktok_public/data/`. Dữ liệu đầu ra nằm ngoài repo.
