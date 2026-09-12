# Kiểm chứng vận hành — hôm nay một người dùng thật làm được gì

*Đo ngày 11/09/2026, 13:13–13:35 giờ Việt Nam (ICT) · trên API đang chạy thật
tại `http://127.0.0.1:8000` (`store_backend: memory`) · không tắt, không reset,
không xoá gì.*

> **Mục đích:** thay vì mô tả năng lực bằng lời, đóng vai một chủ shop và bấm
> thật từng bước, rồi ghi lại đúng cái gì chạy được, cái gì vướng, mất bao lâu.

## Kết luận ba dòng

| Kịch bản | Kết luận | Thiếu gì |
|---|---|---|
| **1. "Live đã phát xong, tôi muốn xem phân tích"** | **LÀM ĐƯỢC** | — (đường đi trọn vẹn, 36,8 giây) |
| **2. "Tôi muốn chạy một phiên thí nghiệm thật"** | **LÀM ĐƯỢC MỘT PHẦN** | 1 lỗi HTTP 500 chặn đường; 2 bước bắt buộc mà giao diện không hề báo |
| **3. "Tôi live TikTok, tôi bật LiveLift lên"** | **LÀM ĐƯỢC MỘT PHẦN** | không có bình luận realtime; chỉ còn đường nhập tay, và phiên nhập tay không kết thúc được |

---

## 0. Phát hiện trước khi bắt đầu: dữ liệu 13 phiên đã mất

Việc đầu tiên là kiểm kê kho dữ liệu. Kết quả **không khớp** với giả định ban đầu
(«đang giữ 13 phiên live thật với 17.535 bình luận»):

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","store_backend":"memory","intent_backend":"tfidf_logreg"}

curl -s http://127.0.0.1:8000/sessions     # → 4 phiên
```

| Kiểm tra | Kết quả thật lúc 13:13 ICT |
|---|---|
| Số phiên trong kho | **4** (3 `sim` + 1 `replay`), không phải 13 |
| Tổng bình luận | **160** (59 + 47 + 32 + 22), không phải 17.535 |
| `created_at` của cả 4 phiên | `2026-09-11T06:09:1x` UTC — tức 13:09 ICT |
| Tiến trình phục vụ cổng 8000 | PID 29948, **khởi động lúc 13:05:53 ICT** |

Bốn phiên còn lại đều mang tiêu đề `Phiên mô phỏng seed=...` — đây là dữ liệu
`POST /demo/seed`, không phải phiên live thật.

> **13 phiên live thật và 17.535 bình luận đã mất trước khi gói kiểm chứng này
> bắt đầu**, khi tiến trình API khởi động lại lúc 13:05:53. Kho là `memory`, nên
> khởi động lại là mất sạch. Không có thao tác nào của gói này gây ra việc đó, và
> **không có cách nào khôi phục** — đây chính là rủi ro mà `store_backend: memory`
> mang lại, đã hiện thực hoá một lần trong ngày.

Toàn bộ số liệu dưới đây vì vậy được tạo mới trong phiên làm việc này.

---

## 1. Kịch bản 1 — "Tôi có một buổi live đã phát xong, tôi muốn xem phân tích"

### 1.1 Chọn một buổi live MỚI, ngành hàng chưa test

`docs/benchmarks/live-fire-da-nguon.md` đã phủ: tạp hoá/thực phẩm, quần áo, dược
liệu, đá quý, cây cảnh, gia dụng, sàn TMĐT. Nên lần này tìm ngành khác:

```bash
.venv/Scripts/yt-dlp.exe --flat-playlist --match-filter "was_live" \
  --print "%(id)s|%(duration)s|%(live_status)s|%(title).60s" \
  "ytsearch15:live bán nước hoa chính hãng"
```

**Bẫy gặp phải:** tìm bằng từ khoá thường (`ytsearch12:live bán mỹ phẩm chốt đơn`)
trả về **gần như toàn video dạy bán hàng**, không phải buổi live thật. Phải thêm
`--match-filter "was_live"` mới lọc ra được bản ghi live. Sau đó còn phải kiểm tra
buổi đó có lưu chat replay không:

```bash
.venv/Scripts/yt-dlp.exe --list-subs "https://www.youtube.com/watch?v=V0tvfOQ1_rQ" | grep '^live_chat'
# live_chat json          ← có chat replay
```

Chọn: **`V0tvfOQ1_rQ` — "Không Nói Nước Hoa, Nay Live Rồi Đi Lam | Kiên Fragrance"**,
78 phút, ngành **nước hoa** — chưa từng có trong 16 buổi đã đo.

### 1.2 Nạp qua API

```bash
curl -s -X POST http://127.0.0.1:8000/replays/youtube \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.youtube.com/watch?v=V0tvfOQ1_rQ"}'
# → 202 {"job_id":"acaab546-2162-40b9-b01a-b30761e1dff1"}   (20 mili-giây)

# rồi hỏi trạng thái đến khi xong:
curl -s http://127.0.0.1:8000/replays/jobs/acaab546-2162-40b9-b01a-b30761e1dff1
```

| Bước | Thời gian thật |
|---|---|
| `POST /replays/youtube` trả `job_id` | **0,02 s** |
| Tải chat replay + nạp xong (`status: done`) | **36,8 s** |
| Kết quả | **274 bình luận**, 156 điểm đo |

### 1.3 Lấy đầy đủ dữ liệu

Tất cả bảy đường đều trả `HTTP 200`, gần như tức thì:

| Đường | HTTP | Thời gian | Nội dung |
|---|---|---|---|
| `GET /sessions/{id}/comments` | 200 | 20 ms | 274 bình luận, đã gắn nhãn ý định + lọc PII |
| `GET /sessions/{id}/signals` | 200 | 14 ms | 6 tín hiệu, 5 năng lực |
| `GET /sessions/{id}/ticks` | 200 | 4 ms | 156 điểm |
| `GET /sessions/{id}/reactions` | 200 | 3 ms | 0 |
| `GET /sessions/{id}/bao-cao` | 200 | 4 ms | **báo cáo tiếng Việt đầy đủ** |
| `GET /sessions/{id}/report` | 200 | 5 ms | rỗng đúng cách (phiên quan sát) |
| `GET /sessions/{id}/state` | 200 | 14 ms | xem mục 1.5 |

**`GET /sessions/{id}/bao-cao` đã có sẵn và chạy tốt.**

### 1.4 Báo cáo nói gì

Bản báo cáo trung thực đúng mức — đây là điểm mạnh rõ nhất quan sát được:

- `loai_phien: "quan_sat"`, kèm nhãn: *"phiên QUAN SÁT: chỉ số mô tả, KHÔNG có số
  nhân quả (không có lịch gán ngẫu nhiên để suy diễn)"*.
- Ô trống được ghi rõ là **thiếu nguồn**, không phải đo bằng 0:
  > *"156 điểm đo chỉ có NHỊP BÌNH LUẬN, không điểm nào có số người xem — video đã
  > kết thúc không còn lộ số người xem đồng thời; số 0 trong cột người xem là chỗ
  > trống, KHÔNG phải phép đo"*
- Phân bổ ý định: `khác 239 · chốt_đơn 17 · chê_đắt 9 · vận_chuyển 4 · hỏi_size 3 · hỏi_giá 2`
  — kèm cảnh báo bắt buộc rằng nhãn là tự động và precision phụ thuộc tỷ lệ nền.
- PII đã che: `address 9 · name 5 · social 5`.
- Ba khoảnh khắc đỉnh (phút 8, 55, 71), mỗi cái đều đóng dấu *"quan sát, chưa kiểm
  chứng nhân quả"*.

### 1.5 Chỗ vướng: thẻ gợi ý sai ngữ cảnh

`GET /sessions/{id}/state` trên phiên nước hoa **đã kết thúc** và gắn cờ
`analysis_only: true` vẫn trả về ba thẻ hành động mời **ghim hàng**:

```
card-0-P-BINH | Ghim Bình giữ nhiệt 500ml        | source=forecast
card-1-P-KHAN | Ghim Set 5 khăn lau đa năng      | source=forecast
card-2-P-SAP  | Ghim Sáp thơm để xe hương cà phê | source=forecast
```

Đây là ba sản phẩm demo trong kho, **không liên quan gì đến buổi live nước hoa**,
trên một phiên **đã phát xong từ lâu** nên không thể ghim gì được nữa. Báo cáo thì
rất cẩn trọng, nhưng bảng điều khiển lại mời thao tác vô nghĩa.

> **Kết luận kịch bản 1: LÀM ĐƯỢC.** Từ lúc bắt đầu tìm video đến lúc cầm báo cáo:
> **2 phút 32 giây** (tìm + thẩm định 114 s, nạp 36,8 s, đọc < 1 s).
> `session_id` để chủ dự án tự mở xem: **`6a44dd9c-33d6-4298-be22-0b99028b69b7`**

---

## 2. Kịch bản 2 — "Tôi muốn chạy một phiên thí nghiệm thật"

Đóng vai chủ shop thao tác qua API đúng như giao diện sẽ gọi.

### 2.1 Lần chạy thứ nhất — chặn ngay ở bước sinh lịch (HTTP 500)

```bash
POST /products    {"product_id":"KC-SON-131827", ...}        → 200  (22 ms)
POST /sessions    {"platform":"youtube","planned_duration_min":5, ...} → 200 (35 ms)
POST /sessions/{id}/start                                     → 409  ✅ đúng
POST /sessions/{id}/schedule {"block_min":1,"washout_min":0,"jitter_s":0,"seed":4242}
                                                              → 500  ❌ LỖI
```

Cái 409 là **đúng và tốt** — hệ thống chặn phát sóng khi chưa có lịch gán:

> *"Chưa có lịch gán khối — phiên không được phép phát sóng khi chưa sinh và lưu
> lịch gán (quy tắc bất biến, kế hoạch §6.1)."*

Nhưng bước sinh lịch thì **đổ 500 với thông báo rỗng** (`Internal Server Error`).
Truy vết trong log máy chủ:

```
File "src/livelift/core/assigner/outer.py", line 337, in draw_assignments
    raise RuntimeError(f"rerandomization failed to satisfy constraints in {max_redraws} draws")
RuntimeError: rerandomization failed to satisfy constraints in 10000 draws
```

#### Quy luật của lỗi — tất định, không phải xác suất

Dò trực tiếp hàm thuần `generate_schedule` (không đụng máy chủ):

| thời lượng \ `block_min` | 1 | 2 | 3 | 5 | 10 |
|---|---|---|---|---|---|
| 5 phút | **HỎNG** | OK | OK | OK | `ValueError` |
| 10 phút | OK | **HỎNG** | OK | OK | OK |
| 15 phút | OK | OK | **HỎNG** | OK | OK |
| 20 phút | OK | OK | OK | OK | OK |
| 30–120 phút | OK | OK | OK | OK | OK |

Thử 20 seed khác nhau cho (5 phút, `block_min=1`): **20/20 đều hỏng** → lỗi **tất
định**, không phải xui seed.

Quy luật chính xác, đã kiểm chứng trên 13 tổ hợp:

> **Hễ `planned_duration_min / block_min == 5` thì luôn trả HTTP 500.**
> Đã xác nhận hỏng ở: 5/1, 10/2, 15/3, 20/4, 25/5, 30/6, 35/7, 40/8, 50/10.
> Các tỷ lệ 6,0 và 10,0 (12/2, 18/3, 24/4, 20/2) đều bình thường.

Đây không phải tổ hợp kỳ quặc: **"phiên 50 phút, đổi khối mỗi 10 phút"** là lựa
chọn rất tự nhiên của một chủ shop — và nó đổ 500 câm.

### 2.2 Lần chạy thứ hai — đường đi thông, nhưng kết quả rỗng ruột

Đổi sang 10 phút / `block_min=1` (tỷ lệ 10,0). Toàn bộ chuỗi chạy trơn:

```bash
POST /products × 2                → 200   (20 ms, 14 ms)
POST /sessions                    → 200   (15 ms)
POST /sessions/{id}/schedule      → 200   (21 ms)  4 khối BẬT / 4 khối TẮT
POST /sessions/{id}/start         → 200   (41 ms)
POST /shortlinks × 2              → 200   (47 ms, 31 ms)   code=RDaZEYIM, ZocRXRLv
# mô phỏng 191 giây: 93 lượt GET /r/{code}, 62 bình luận, 31 tick
POST /sessions/{id}/end           → 200   (46 ms)
```

Mọi thứ `200`. Nhưng báo cáo ra **số không**:

```json
"blocks": [
 {"block_index":0,"assignment":"OFF","clicks":0,"clicks_raw":30,"y":0.0},
 {"block_index":1,"assignment":"ON", "clicks":0,"clicks_raw":15,"y":0.0}],
"diff_in_means": null,
"compliance": {"on_blocks":4,"on_blocks_with_pin":0,"compliance_rate":0.0}
```

Hai nguyên nhân, cả hai đều đáng ghi:

**(a) 93 lượt nhấp → 0 hợp lệ.** Bộ lọc GIVT trong `core/click_validity.py` bắt
đúng `python-urllib` trong User-Agent và loại toàn bộ. **Đây là hệ thống làm
đúng** — lỗi thuộc về kịch bản mô phỏng, không phải sản phẩm. Nhưng nó phơi ra một
mâu thuẫn thật ở tầng hiển thị (mục 2.4).

**(b) compliance = 0%.** Lịch gán có 4 khối BẬT, nhưng **không khối nào được ghim
hàng**. Phiên đặt `mode: "auto"`, chủ shop tự nhiên sẽ nghĩ hệ thống tự ghim.
**Hệ thống không tự làm.** Phải có ai đó gọi `POST /sessions/{id}/actions/execute`
trong từng khối BẬT, nếu không thì nhánh BẬT chưa hề được can thiệp và thí nghiệm
rỗng ruột — trong khi mọi endpoint vẫn trả `200` và không có cảnh báo nào.

### 2.3 Lần chạy thứ ba — làm đúng cách, ra số nhân quả

Sửa hai điểm trên: mô phỏng **14 người xem, mỗi người một User-Agent trình duyệt
thật**, giãn cách > 14 giây (tôn trọng `REFRACTORY_TAU_S = 10`), và **bấm hành
động khi vào khối BẬT**.

Lịch gán sinh ra (seed 2026, 28 lần vẽ lại):

```
khối 0  early ON    0-120s     khối 4  mid  ON  300-360s
khối 1  early OFF 120-180s     khối 5  mid  ON  360-420s
khối 2  mid   OFF 180-240s     khối 6  late ON  420-480s
khối 3  mid   OFF 240-300s     khối 7  late OFF 480-600s
```

Gửi vào: **212 lượt nhấp, 86 bình luận, 44 tick, 2 lần bấm hành động.**

Kết quả:

```
n_blocks=5  n_on=2  n_off=3   diff_in_means = -0,4197
compliance = {on_blocks: 4, on_blocks_with_pin: 1, compliance_rate: 0,25}

 khối 0  ON  clicks= 31  raw= 33   y=3,77
 khối 1 OFF  clicks= 11  raw= 11   y=2,68
 khối 2 OFF  clicks= 19  raw= 19   y=3,84
 khối 3 OFF  clicks= 20  raw= 20   y=5,46
 khối 4  ON  clicks= 16  raw= 16   y=3,38
```

Lần này `/signals` xanh hết (`schedule ok · ticks ok phủ 99% · comments ok 86 ·
clicks ok 212`), `luot_nhap_hop_le: 210`, và `bao-cao` chuyển sang
`loai_phien: "thi_nghiem"` với khối `ket_qua_thi_nghiem` thật:

```json
{"estimable": true, "n_blocks": 5, "estimate": -0.4197,
 "ci_low": null, "ci_high": 5.152, "p_value": 0.4755, "n_draws": 1000}
```

Khoảng tin cậy một phía và p = 0,48 — đúng như kỳ vọng với 5 khối. Hệ thống
**không** tô vẽ con số này thành kết luận.

### 2.4 Bốn chỗ vướng đáng sửa

**(a) `/signals` đếm nhấp THÔ, `/report` đếm nhấp HỢP LỆ — hai con số đá nhau.**
Ở lần chạy thứ hai, `/signals` báo *"clicks ok — 93 lượt nhấp qua link đo"* và
*"thí nghiệm nhân quả (BẬT/TẮT): ok — đủ tín hiệu"*, trong khi `/report` cùng phiên
cho `clicks: 0` ở mọi khối và `diff_in_means: null`. Chủ shop được bảo "đủ tín
hiệu" rồi nhận về số rỗng, không một lời giải thích.

**(b) Ghim đúng sản phẩm của mình thì bị từ chối, kèm thông báo sai sự thật.**
Kho có **11 sản phẩm**, nhưng hệ thống chỉ gợi ý **3 thẻ**. Thử ghim một sản phẩm
vừa tạo (`KC3-NEW-133246`, `stock = 50`):

| Cách bấm | Kết quả |
|---|---|
| A. `{"product_id": "KC3-NEW-133246"}` — sản phẩm của tôi | **409** |
| B. `{"card_id": "card-0-KC-MASK-131827"}` — thẻ hệ thống gợi ý | **200** |
| C. `{}` — để hệ thống tự chọn | **200** |

Thông báo lỗi ở (A):

> *"Thẻ không còn hợp lệ — sản phẩm đã hết hàng hoặc danh sách gợi ý vừa thay đổi.
> Chờ thẻ mới rồi thử lại."*

**Cả hai lý do đều sai.** Sản phẩm còn 50 cái trong kho, và danh sách gợi ý không
hề thay đổi. Lý do thật là: *sản phẩm này không nằm trong 3 thẻ hệ thống đang gợi
ý*. Lời khuyên "chờ thẻ mới rồi thử lại" sẽ khiến chủ shop chờ vô ích — thẻ không
bao giờ đổi thành sản phẩm đó. (Chính cái 409 này làm compliance ở mục 2.3 chỉ đạt
25% thay vì 50%.)

**(b-phụ) Lý do ghi đè bị giới hạn trong đúng ba lựa chọn.**
`POST /actions/override` với lý do tự gõ bị từ chối:

```
POST /sessions/{id}/actions/override {"reason":"khách hỏi dồn sản phẩm này, tôi ghim tay"}
→ 422  "Input should be 'hết hàng', 'sai giá' or 'sự cố kỹ thuật'"
```

Ràng buộc này **hợp lý** cho việc truy vết (lý do tự do sẽ không phân tích được),
và thông báo lỗi liệt kê đủ ba giá trị hợp lệ. Nhưng giao diện **bắt buộc** phải
hiện sẵn ba lựa chọn này dưới dạng nút bấm — chủ shop không có cách nào đoán ra.

**(c) Không có cách loại phiên chạy thử khỏi kết quả tổng.**
`experiment_summary` gộp **mọi phiên đã kết thúc có lịch gán**, không phân biệt
thật hay thử:

```python
ended = [s for s in store.list_sessions()
         if s.get("status") == "ended" and not _is_analysis_only(s)]
```

Hai phiên dò lỗi của gói này (`probe409`, `probe-pin`) — mỗi phiên sống 1 giây,
không có nhấp nào — đã lọt vĩnh viễn vào `/experiment/summary`. Chủ shop chạy thử
một lần là **làm bẩn kết quả của chính mình**, không có nút gỡ.

> **Kết luận kịch bản 2: LÀM ĐƯỢC MỘT PHẦN.** Đường đi trọn vẹn và ra được số nhân
> quả thật, nhưng chỉ khi né đúng một lỗi 500 tất định và tự biết hai bước mà không
> giao diện nào chỉ. Thời gian: lần hỏng ~2 phút; lần thông **3 phút 14 giây**; lần
> làm đúng **6 phút 5 giây** (trong đó thao tác thật chỉ ~0,2 giây, còn lại là chờ
> phiên chạy).
> `session_id` có số nhân quả: **`2c8e60db-2796-4891-866b-07a6b769452a`**

---

## 3. Kịch bản 3 — "Tôi live trên TikTok, tôi bật LiveLift lên"

### 3.1 Đường realtime: vẫn không có, đã xác nhận lại hôm nay

`docs/benchmarks/tiktok-collector-2026-09.md` (đo 09/09) kết luận bắt tay WebSocket
bị từ chối HTTP 400, 10/10 lần, 0 bình luận. Chạy lại **một lượt ngắn hôm nay** để
xem tình hình có đổi không:

```bash
PYTHONPATH="D:\AISC2026\livelift\src" \
  <scratch>/tiktok_venv/Scripts/python.exe collectors/tiktok_public/collect.py \
  --username quyenleo --max-minutes 1 --out-dir <scratch>/tiktok_out_kc
```

Kết quả lúc 13:33–13:34 ICT ngày 11/09/2026:

| Khâu | Kết quả |
|---|---|
| Phát hiện phòng live `@quyenleo` | ✅ 200, `room_id = 7684114186393193223` |
| `check_alive` của TikTok | ✅ HTTP 200 |
| Máy chủ ký Euler Stream | ✅ HTTP 200 |
| **Bắt tay WebSocket** | ❌ `InvalidStatusCode` — **3/3 lần hỏng** |
| **Bình luận thu được** | **0** |

Backoff 5s → 10s → 20s rồi dừng sạch khi hết giờ. **Tình hình không đổi so với
09/09: không có đường lấy bình luận TikTok realtime.**

### 3.2 Đường thay thế: phiên quan sát, dữ liệu nhập tay

Câu hỏi thật: chủ shop đang live TikTok có dùng được gì không? Thử nạp tay.

```bash
POST /sessions {"platform":"tiktok","mode":"suggest","planned_duration_min":15} → 200
POST /sessions/{id}/comments {"text":"chị ơi cái áo khoác này còn size M không",
                              "platform":"tiktok"}                              → 200
```

**Nạp được bình luận ngay khi phiên còn ở trạng thái `planned`** — không cần sinh
lịch gán, không cần bấm bắt đầu phát sóng. Đây là điểm cộng thật: chế độ quan sát
không bắt chủ shop phải dựng bộ máy ngẫu nhiên hoá.

| Thao tác | HTTP | Ghi chú |
|---|---|---|
| Nạp 12 bình luận tay | 200 ×12 | **0,1 giây tổng** (~12 ms/bình luận) |
| Nạp quà (`kind: gift`, 10 VND) | 200 | nhận |
| Nạp số người xem (`viewers: 340`) | 200 | gõ tay từ màn hình TikTok |

Phân loại ý định chạy đúng trên tiếng Việt kiểu TikTok:
`chốt_đơn 4 · khác 5 · hỏi_size 2 · hỏi_giá 1 · vận_chuyển 1`, PII che `address 1`.

Báo cáo trả về `loai_phien: "quan_sat"` với nhãn trung thực *"chỉ số mô tả, KHÔNG
có số nhân quả"*, và bảng năng lực nói thẳng cái gì bật được:

```
radar ý định bình luận                 ok        đủ tín hiệu
nhịp phiên (người xem theo thời gian)  degraded  tín hiệu suy giảm: ticks
tỷ lệ nhấp sản phẩm                    missing   thiếu clicks
thí nghiệm nhân quả (BẬT/TẮT)          missing   thiếu schedule, clicks
đối soát doanh thu                     missing   thiếu orders
```

### 3.3 Chỗ vướng: phiên quan sát không bao giờ kết thúc được

```bash
POST /sessions/{id}/end
# → 409 {"detail":"Phiên không ở trạng thái đang phát"}
```

Phiên chưa từng `start` thì không `end` được. Nó **kẹt vĩnh viễn ở `planned`**
(`start_ts: null`, `end_ts: null`), đã thử lại và vẫn 409. Hệ quả:

- Danh sách phiên của chủ shop tích tụ những phiên "đang chờ" không bao giờ đóng.
- Vì `experiment_summary` chỉ gộp phiên `ended`, phiên quan sát nằm ngoài — điều
  này đúng về mặt thống kê, nhưng là do tình cờ chứ không phải do thiết kế.
- `ticks` bị chấm `degraded — telemetry chỉ phủ 0% thời gian phát`, vì phiên không
  có `start_ts` nên phép tính độ phủ vô nghĩa.

Đường vòng duy nhất: sinh lịch gán + bấm bắt đầu rồi mới kết thúc — tức là **bắt
chủ shop dựng một bộ máy thí nghiệm mà họ không định dùng**, chỉ để đóng được phiên.

> **Kết luận kịch bản 3: LÀM ĐƯỢC MỘT PHẦN.** Không có bình luận TikTok realtime
> (đã xác nhận lại hôm nay, 3/3 lần hỏng). Đường nhập tay **chạy được và cho ra
> radar ý định + báo cáo quan sát**, nhưng nhập tay không mở rộng nổi cho một buổi
> live thật hàng nghìn bình luận, và phiên nhập tay **không kết thúc được**.
> Thời gian: script nạp tay **1,3 giây**; probe TikTok **1 phút**.
> `session_id`: **`6a5e16fe-a13c-4566-ba63-6e842f761dbe`**

---

## 4. Bảng thời gian thật

| Kịch bản | Từ đầu đến khi có kết quả | Trong đó máy làm | Trong đó người/chờ |
|---|---|---|---|
| 1. Phân tích live đã phát xong | **2 ph 32 s** | 36,8 s nạp | 114 s tìm & thẩm định video |
| 2. Phiên thí nghiệm (lần hỏng) | ~2 ph | — | chết ở HTTP 500 |
| 2. Phiên thí nghiệm (lần thông) | **3 ph 14 s** | 0,2 s thao tác | 191 s chờ phiên chạy |
| 2. Phiên thí nghiệm (làm đúng) | **6 ph 5 s** | 0,2 s thao tác | 360 s chờ phiên chạy |
| 3. TikTok nhập tay | **1,3 s** | 1,3 s | — |
| 3. Xác nhận lại TikTok realtime | **1 ph** | 1 ph | — |

Đọc bảng này: **phần mềm không phải chỗ nghẽn.** Mọi thao tác dựng phiên cộng lại
là 0,2 giây. Thời gian thật đổ vào ba chỗ: tìm video (kịch bản 1), chờ buổi live
trôi qua (kịch bản 2 — không rút ngắn được, đó là bản chất switchback), và **né
lỗi** (kịch bản 2 lần đầu).

## 5. Phát hiện xếp theo mức độ đáng sửa

1. **Kho `memory` đã làm mất 13 phiên / 17.535 bình luận lúc 13:05:53 hôm nay.**
   Không khôi phục được. (mục 0)
2. **`planned_duration_min / block_min == 5` → HTTP 500 tất định, thông báo rỗng.**
   Nên trả 422 kèm gợi ý chọn `block_min` khác. (mục 2.1)
3. **Chế độ `auto` không tự ghim hàng trong khối BẬT.** Không gọi
   `/actions/execute` thì compliance = 0 và thí nghiệm rỗng ruột, nhưng không có
   cảnh báo nào. (mục 2.2b)
4. **Thông báo 409 khi ghim sản phẩm ngoài thẻ gợi ý nói sai lý do** ("hết hàng /
   danh sách vừa đổi") và khuyên chờ vô ích. (mục 2.4b)
5. **`/signals` đếm nhấp thô, `/report` đếm nhấp hợp lệ** → báo "đủ tín hiệu"
   trong khi kết quả rỗng. (mục 2.4a)
6. **Phiên quan sát không kết thúc được**, kẹt `planned` vĩnh viễn. (mục 3.3)
7. **Không có cờ loại phiên chạy thử khỏi `/experiment/summary`.** (mục 2.4c)
8. **Thẻ "Ghim hàng" hiện trên phiên replay đã kết thúc**, gợi ý sản phẩm không
   liên quan đến video. (mục 1.5)

## 6. Điểm mạnh quan sát được

- **Chốt chặn bất biến hoạt động — đã thử tay, không chỉ đọc code:**
  - Không có lịch gán thì không phát sóng được:
    `POST /start` → **409** *"Chưa có lịch gán khối… (quy tắc bất biến, kế hoạch §6.1)"*
  - Ghim hàng trong khối TẮT bị chặn:
    `POST /actions/execute` trong khối TẮT → **409** *"Khối TẮT: đội vận hành làm
    theo cách thường lệ — hệ thống không can thiệp để bảo toàn nhánh đối chứng"*
    (kiểm chứng trên phiên `b522d4ae-b493-4d62-b9a0-210bde968bc6`)
- **Bộ lọc nhấp không hợp lệ bắt đúng bot** ngay lần đầu (93/93), theo GIVT-lite.
- **Báo cáo tiếng Việt phân biệt rạch ròi "thiếu nguồn" với "đo được 0"** — hiếm
  thấy, và đúng chỗ quan trọng nhất.
- **Ngẫu nhiên hoá gán theo sản phẩm được ghi lại** (`inner_propensity`,
  `overlap_set`), không chỉ gán BẬT/TẮT ngoài.
- **Nạp replay nhanh:** 78 phút live → 274 bình luận đã gắn nhãn trong 36,8 giây.

---

## 7. Sau khi sửa (12/09) — đóng vai người dùng lại từ đầu

*Đo ngày **12/09/2026, 14:45–15:00 ICT**. Tám lỗi ở mục 5 đã được vá trong ba gói
A/B/C; mục này **không đọc lại mã nguồn**, mà bấm lại đúng những thao tác đã làm
hỏng hôm 11/09 rồi ghi cái nhận được.*

> **Chạy ở đâu:** trên một tiến trình API **mới** (kho `memory` rỗng, cùng mã
> nguồn của cây làm việc), chứ không phải tiến trình cổng 8000. Lý do và hệ quả:
> mục 7.3.

### 7.1 Bảng đối chiếu từng lỗi

| # | Thao tác của người dùng | Trước (11/09) | Sau (12/09) |
|---|---|---|---|
| **a** | `POST /sessions/{id}/schedule` cho **phiên 50 phút, khối 10 phút** | **HTTP 500**, thân rỗng, tất định | **HTTP 200**, 5 khối đo, **50/50 seed đều thành công** |
| **b** | Quét dải cấu hình thời lượng × độ dài khối | 36/1.080 tổ hợp ném `RuntimeError` → 500; thêm 30 tổ hợp `ValueError` trần → 500 | Hàm thuần: **1.061 sinh được lịch, 19 báo `ScheduleInfeasibleError` tiếng Việt, 0 cạn lượt vẽ, 0 ngoại lệ khác**. Qua HTTP (176 thời lượng × 6 độ dài khối = 1.056 lượt): **1.051 × 200, 5 × 400, 0 × 5xx** |
| **c** | Phiên `mode:"auto"` chạy trọn 5 phút qua 4 biên khối | `compliance_rate = 0,0`; không khối BẬT nào được can thiệp; không cảnh báo | `actions_taken = 2`, `on_blocks_done = 2/2`, `missed_on_blocks = []`, **`compliance_rate = 1,0`**, `n_interventions = 2` |
| **d** | Ghi dữ liệu → **giết cứng** tiến trình → bật lại | Mất sạch (13 phiên + 17.535 bình luận, 11/09) | `postgres`: **phiên CÒN, 25 bình luận, 1 tick**. `memory` + ảnh chụp 3 s: **phiên CÒN, 25 bình luận, 1 tick**. Đối chứng âm `--no-snapshot`: **mất đúng như dự đoán** (phép thử có răng) |
| **e** | `/signals` và `/bao-cao` trên **cùng một phiên** | `/signals`: *"clicks ok — 93 lượt nhấp"* + *"thí nghiệm nhân quả: ok"*; `/report`: `clicks = 0` mọi khối, `diff_in_means = null` | Tái hiện đúng 93 cú nhấp bot: `/signals` → **`missing`** *"0 lượt nhấp HỢP LỆ trên 93 lượt đã ghi…"*, năng lực nhân quả → **`missing`**, `bao-cao` → `luot_nhap_hop_le = 0`, `luot_nhap_tho = 93`, `report.diff_in_means = null`. Phiên pha trộn: **12 hợp lệ / 37 thô**, cả ba màn hình cùng một cặp số |
| **f** | Ghim một sản phẩm **còn hàng** nằm ngoài 3 thẻ gợi ý | 409 *"sản phẩm đã hết hàng hoặc danh sách gợi ý vừa thay đổi. Chờ thẻ mới rồi thử lại."* — cả hai lý do đều sai | 409 nói **đúng chỗ đứng và đúng đường ra**: *"«Áo khoác gió» còn 80 trong kho và vẫn đủ điều kiện lên thẻ, nhưng bàn chỉ gợi ý 3 sản phẩm xếp đầu…; sản phẩm này đang đứng thứ 6/6 … Muốn ghim ĐÚNG sản phẩm này: bấm `POST /actions/override` kèm một trong ba lý do…"*. Ba tình huống khác nhau, ba câu trả lời khác nhau: không có trong kho → **404**; hết hàng → **409 "đang HẾT HÀNG (tồn kho 0)"**; bấm thẻ hệ thống gợi ý → **200** |
| **g** | Phiên quan sát chưa từng `start` → `POST /end` | **409** *"Phiên không ở trạng thái đang phát"*, kẹt `planned` vĩnh viễn | **200 → `status = cancelled`**, `start_ts` vẫn `null`, `end_ts` có thật. `POST /cancel` tường minh và **idempotent** (200 hai lần); phát lại sau khi huỷ → **409** *"Phiên đã huỷ — không phát lại được"* |
| **h** | Chạy thử một phiên cho quen tay | Lọt **vĩnh viễn** vào `/experiment/summary`, không có nút gỡ | Hai phiên **giống hệt nhau**, chỉ khác cờ `dry_run`: phiên chạy thử **không thêm một cú nhấp nào** vào tổng gộp (`raw_clicks` 0 → 0), phiên thật thì có (0 → 6). `sessions_excluded` công bố: *"phiên CHẠY THỬ, khai báo lúc tạo phiên (tiền đăng ký §8.2)": 1*. Báo cáo **riêng** của phiên chạy thử vẫn mở được (200) — bị loại khỏi mẫu gộp, không bị xoá |
| **i** | Mở bàn điều khiển của phiên replay đã kết thúc | 3 thẻ mời ghim sản phẩm demo không liên quan | **`cards: []`** kèm `cards_note`: *"phiên PHÂN TÍCH video của người khác — buổi live đã phát xong và không thuộc quyền vận hành của bạn, nên không có gì để ghim"*. `POST /actions/execute` từ chối bằng **đúng câu đó** (409) — bàn điều khiển và lớp từ chối không còn kể hai câu chuyện |

Chín trên chín đạt. Không điểm nào phải nới tiêu chí để đạt.

### 7.2 Lệnh tái lập

```bash
cd d:/AISC2026/livelift

# Cổng chất lượng (nền: 838 test nhanh + 13 gate chậm)
.venv/Scripts/python -m pytest -m "not slow"      # 838 passed, 13 deselected
.venv/Scripts/python -m pytest -m slow            # 13 passed
.venv/Scripts/python -m ruff check src tests scripts
.venv/Scripts/python -m ruff format --check src tests
.venv/Scripts/python scripts/check_isolation.py
cd web && npx tsc --noEmit

# (a)(b) lỗi 500 khi sinh lịch — gate chặn tái diễn
.venv/Scripts/python -m pytest tests/test_schedule_config_matrix.py
.venv/Scripts/python -m pytest tests/test_case_nguoi_dung_that.py -k case_3

# (c) chế độ auto tự ghim hàng
.venv/Scripts/python -m pytest tests/test_autopilot.py
.venv/Scripts/python -m pytest tests/test_case_nguoi_dung_that.py -k case_7

# (d) dữ liệu sống sót qua một lần tiến trình CHẾT CỨNG (mở cổng 8099 riêng,
#     không đụng API 8000)
.venv/Scripts/python scripts/bat_postgres.py
.venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend postgres \
  --database-url 'postgresql://livelift:<mật khẩu>@127.0.0.1:5432/livelift'
.venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend memory --interval 3
.venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend memory --no-snapshot  # đối chứng ÂM

# (e) hai màn hình một sự thật
.venv/Scripts/python -m pytest tests/test_signals.py
.venv/Scripts/python -m pytest tests/test_case_nguoi_dung_that.py -k case_2

# (f)(g)(h)(i) vòng đời phiên, thẻ ghim, mẫu phân tích
.venv/Scripts/python -m pytest tests/test_vong_doi_phien.py
.venv/Scripts/python -m pytest tests/test_case_nguoi_dung_that.py -k "case_1 or case_4 or case_5 or case_9"
```

Kiểm tra nhanh bằng tay, đúng thao tác đã làm hỏng hôm 11/09:

```bash
# bật một API sạch trên cổng RIÊNG (đừng dùng 8000 — xem 7.3)
.venv/Scripts/python -m uvicorn livelift.api.main:app --port 8098

curl -s http://127.0.0.1:8098/health
# → có thêm storage_mode / durable / storage_warning: hệ thống tự nói ra
#   "chết bây giờ thì mất gì"

SID=$(curl -s -X POST http://127.0.0.1:8098/sessions -H 'Content-Type: application/json' \
  -d '{"platform":"youtube","title":"Phiên 50 phút","mode":"auto","planned_duration_min":50}' \
  | python -c "import sys,json;print(json.load(sys.stdin)['session_id'])")
curl -s -o /dev/null -w '%{http_code}\n' -X POST "http://127.0.0.1:8098/sessions/$SID/schedule" \
  -H 'Content-Type: application/json' -d '{"block_min":10,"washout_min":0,"jitter_s":0,"seed":4242}'
# → 200   (11/09: 500)

curl -s -X POST "http://127.0.0.1:8098/sessions/$SID/end"
# → 200, status=cancelled   (11/09: 409, kẹt 'planned')
```

### 7.3 Một điều phải nói thẳng: tiến trình cổng 8000 vẫn chạy mã CŨ

Bản vá nằm trong cây làm việc, **chưa được nạp vào tiến trình đang phục vụ cổng
8000** — tiến trình ấy khởi động từ trước khi sửa. Đo lúc 14:51 ICT ngày
12/09, trên chính API 8000 (chỉ THÊM một phiên, không xoá gì):

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","store_backend":"memory","intent_backend":"tfidf_logreg"}
#  ↑ không có storage_mode/durable → đây là mã trước 12/09

# phiên 272e9c8f-c281-4042-bd24-3f18b79afb0e, 50 phút, khối 10 phút:
# POST /sessions/{id}/schedule → HTTP 500
```

Đây **không phải** một lỗi còn sót: đúng cái cấu hình ấy trả 200 trên tiến trình
chạy mã mới (mục 7.1a). Nó là một sự thật vận hành, và nó kẹt đúng vào cái bẫy mà
gói B vừa vá:

- tiến trình 8000 đang giữ **23 phiên trong RAM** với `store_backend: memory`;
- khởi động lại để nạp mã mới là **mất sạch 23 phiên đó** — đúng kịch bản
  13:05:53 ngày 11/09;
- mã cũ đang chạy nên **không có ảnh chụp nào** để khôi phục.

Cách thoát an toàn, và là việc nên làm trước buổi live thật kế tiếp:

```bash
.venv/Scripts/python scripts/bat_postgres.py      # đã chạy 12/09: db healthy, migrate up-to-date
$env:STORE_BACKEND = "postgres"
$env:DATABASE_URL  = "postgresql://livelift:<mật khẩu>@127.0.0.1:5432/livelift"
.venv/Scripts/python -m uvicorn livelift.api.main:app --port 8000
curl -s http://127.0.0.1:8000/health   # phải thấy storage_mode=postgres, durable=true
```

Lần khởi động lại đó vẫn mất 23 phiên RAM hiện có (không có đường nào khác trên
mã cũ) — nhưng là **lần cuối cùng** mất dữ liệu vì lý do này. Quyết định thời
điểm là của chủ dự án, nên gói thẩm định này **không tự khởi động lại cổng
8000**.

### 7.4 Bẫy cấu hình im lặng: đã có tiếng nói

Đặt `DATABASE_URL` mà quên `STORE_BACKEND` (vector của sự cố 25/08/2026) nay ghi
một dòng cảnh báo tiếng Việt lúc dựng kho, và `/health` nói thẳng dữ liệu đang
nằm trong RAM:

```
WARNING livelift.store: Đã cấu hình DATABASE_URL nhưng CHƯA đặt STORE_BACKEND —
API chạy kho 'memory', dữ liệu nằm trong RAM và mất khi khởi động lại.
Muốn dùng cơ sở dữ liệu thì đặt STORE_BACKEND=postgres (xem docs/luu-tru-du-lieu.md).
```

---

## Phụ lục — session_id để tự mở xem

| Kịch bản | `session_id` | Trạng thái |
|---|---|---|
| 1 — replay nước hoa | `6a44dd9c-33d6-4298-be22-0b99028b69b7` | `ended` |
| 2 — lần hỏng ở sinh lịch | `897e617f-36b8-4619-8dc5-5a38f924bf7d` | `planned` (kẹt) |
| 2 — lần thông, kết quả rỗng | `a95a2ff6-54ce-44f6-a864-124662a8feb5` | `ended` |
| 2 — làm đúng, có số nhân quả | `2c8e60db-2796-4891-866b-07a6b769452a` | `ended` |
| 3 — TikTok nhập tay | `6a5e16fe-a13c-4566-ba63-6e842f761dbe` | `planned` (kẹt) |

**Lưu ý khi đọc `/experiment/summary`:** lúc 13:35 nó báo `n_sessions = 6`,
`raw_clicks = 861`, `valid_clicks = 766`, `estimate = -0,1836`, `p = 0,4955`.
Con số này **không phải của riêng gói kiểm chứng** — kho đang được nhiều tác tử ghi
song song, và tổng đó gộp cả phiên của gói khác (`Phiên live tối thứ Sáu`,
`Phiên thử nghiệm tối thứ Sáu`) lẫn hai phiên dò lỗi 1 giây của gói này. Không nên
trích dẫn như một kết quả thí nghiệm.

*Script tái lập nằm ngoài repo, trong thư mục scratchpad của phiên làm việc:
`kc_kb1.py`, `kc_poll1.py`, `kc_kb2.py`, `kc_kb2b.py`, `kc_kb3.py`,
`kc_probe_schedule.py`, `kc_probe409.py`, `kc_probe_pin.py`.*

**Phiên của gói thẩm định 12/09 (mục 7) KHÔNG mở xem lại được**, và đó là chủ ý:
chúng sinh ra trong một tiến trình API dùng một lần với kho `memory` rỗng, đã tắt
sau khi đo xong. Cái đáng giữ lại không phải `session_id` mà là **lệnh** ở mục
7.2 — chạy lại là có phiên mới với cùng kết luận. Riêng phiên dò trên API 8000
(`272e9c8f-c281-4042-bd24-3f18b79afb0e`, 50 phút, kẹt `planned` vì mã cũ vẫn trả
500) thì còn đó, và là bằng chứng sống của mục 7.3.
