# Nền tảng nào test được, bằng cách nào — bảng khả năng THẬT

*Đo ngày 11/09/2026 · mọi ô trong bảng đều có bằng chứng: đã thử thật, tài liệu
chính thức, hoặc "không thể" kèm lý do. Không có ô nào đoán.*

> **Trả lời thẳng câu hỏi "tôi muốn test buổi live bất kỳ trên TikTok / Facebook
> / Shopee thì làm sao":**
>
> | Bạn có gì | Test được ngay hôm nay? |
> |---|---|
> | Link một buổi live **YouTube đã kết thúc** (còn chat replay) | ✅ **CÓ** — dán link vào `POST /replays/youtube`, 1–2 phút ra kết quả. Không cần tài khoản gì. |
> | Link một buổi live **YouTube đang phát** | ✅ CÓ (yt-dlp, **trái ToS YouTube** — chỉ kiểm thử) hoặc ⏳ xin `YOUTUBE_API_KEY` miễn phí ~10 phút thì hợp lệ |
> | Fanpage **của chính bạn** đang live trên Facebook | ⏳ CÓ sau ~25 phút lấy Page token. Không cần App Review. |
> | Link live **Facebook của người khác** | ❌ **KHÔNG** — không token thì 0 bình luận (đã thử thật, §3). Cần họ cấp quyền + App Review của Meta (4–6 tuần). |
> | Link live **TikTok** bất kỳ (đang phát hay đã kết thúc) | ❌ **KHÔNG, và cũng không có lộ trình** — §5. Đừng mất thời gian. |
> | Buổi live **Shopee của chính shop bạn** | ⏳ CÓ — API **chính thức**, có cả bình luận lẫn đơn hàng (§4). Cần tài khoản Open Platform. **Đây là đường đáng đầu tư nhất.** |
> | Link live **Shopee của shop khác** | ❌ KHÔNG — trang web công khai không có chat, API cần chủ shop ủy quyền (§4.2) |
>
> **Một câu cho hội đồng:** *"Chúng tôi đọc được buổi live của **chính mình**
> trên 3 nền tảng qua API chính thức, và buổi live **công khai đã kết thúc**
> của bất kỳ ai trên YouTube. Đọc buổi live của người khác trên Facebook/TikTok
> là việc các nền tảng cố ý không cho phép — và chúng tôi không lách."*

---

## 0. Cập nhật 17/09/2026 — sáu điều đã đổi so với bảng đo 11/09

*Chi tiết và URL nguồn của từng dòng: `docs/research/2026-09-17-nen-tang-livestream-va-serpapi.md`.
Phần từ §1 trở xuống giữ nguyên là bản đo 11/09 để còn đối chiếu.*

| # | Điều đã đổi | Hệ quả cho người dùng |
|---|---|---|
| 1 | **Bộ thu bình luận chạy NỀN trong API**, bật/tắt bằng nút trên Bàn trợ live và bước 4 của Chuẩn bị phiên (`POST /sessions/{id}/ingest`). Trên máy chủ **chưa đặt `INGEST_TOKEN`** không còn phải mở terminal chạy `python -m livelift.ingest.runner`. Bộ thu tự chờ buổi live bắt đầu, tự thử lại khi mất mạng, tự dừng khi phiên kết thúc, tự nối lại khi máy chủ khởi động lại | Người bán không kỹ thuật bật được nguồn bình luận **chỉ khi máy chủ chưa đặt `INGEST_TOKEN`** (chạy cục bộ / Wi-Fi nội bộ). Lệnh bật là đường ghi luôn đòi token, mà web chưa gửi token: bản công khai (bắt buộc đặt `INGEST_TOKEN`) trả **401** *"Thiếu hoặc sai token ingest…"* khi bấm nút, nên người kỹ thuật vẫn phải chạy runner CLI (tự đính token từ `.env`) cho tới khi web gửi được token — xem `docs/HUONG-DAN-SU-DUNG.md` giới hạn #10 và `docs/mo-hinh-van-hanh-kol.md` mục 6. Vẫn cần khoá của nền tảng trên máy chủ; `GET /platforms` và trang Bắt đầu nói rõ còn thiếu biến nào |
| 2 | **Shopee Live có ghi Việt Nam** trong tài liệu gốc của Shopee (mọi endpoint livestream: "For TW, ID, TH, PH, MY, SG, VN", cập nhật quyền 11/07/2025) — trái với README của một SDK cộng đồng ghi chỉ TW/ID/TH. Các endpoint này là loại **"User"**: ký bằng `user_id`, không phải `shop_id` | Adapter cũ ký bằng `shop_id` gần như chắc chắn bị từ chối khi chạy thật. Trạng thái sửa: xem `docs/incident-log.md` ngày 17/09. Chỉ một cuộc gọi thật bằng tài khoản VN mới chốt được vùng |
| 3 | **TikTok Shop có API chính thức cho số liệu phiên LIVE** theo PHÚT (GMV, đơn, click sản phẩm, số bình luận, người xem), mọi thị trường kể cả VN — nhưng chỉ có **sau khi phiên kết thúc**, không có nội dung bình luận, không ghim được, không webhook báo live bắt đầu | §5 "đóng lại" chỉ còn đúng cho **nội dung bình luận** TikTok. Biến kết quả của switchback trên TikTok Shop đo được **hậu kiểm** qua API chính thức; can thiệp (ghim) vẫn do người dẫn làm tay theo lịch |
| 4 | **Hạn mức YouTube:** bảng quota hiện hành ghi `liveChatMessages.list` = **1 đơn vị** (nhiều tích hợp cũ ghi 5); từ 01/06/2026 `search.list` có hạn mức riêng 100 lượt/ngày. Google khuyến nghị `liveChatMessages.streamList` (đẩy tin, nhận API key) thay cho poll | Con số "≈ 5.400 đơn vị/buổi 90 phút" ở §2.2 là trần xấu nhất; khoảng thật 1.080–5.400 đơn vị tuỳ giá mỗi lượt. Phải đo trên Cloud Console trước buổi live đầu tiên |
| 5 | **Facebook:** mặc định `live_filter=filter_low_quality` **âm thầm lọc bớt bình luận** — bộ thu phải gửi `live_filter=no_filter`. Page webhook `live_videos` báo được lúc live bắt đầu. Luồng SSE `live_comments` không còn tài liệu | Không dựa vào SSE. Điều kiện phát live qua phần mềm: tài khoản ≥ 60 ngày, Page ≥ 100 người theo dõi |
| 6 | **SerpAPI KHÔNG phải nguồn dữ liệu livestream.** Không engine nào đọc chat live, người xem đồng thời, quà hay đơn; không có engine TikTok/Shopee/Lazada. Giá trị thật duy nhất: Google Trends và Google Shopping để chọn hàng ghim và khung giờ phát, gói Free (250 lượt/tháng) là đủ | Không đưa SerpAPI vào đường nạp dữ liệu. Công cụ đọc chat TikTok trên thị trường (TikFinity, Apify, Euler Stream) đều dùng WebSocket không chính thức — rủi ro điều khoản cao, không dùng cho dữ liệu nghiên cứu |

**Nguồn mô phỏng để kiểm thử đầu-cuối (17/09/2026).** Khi chưa có khoá nền tảng nào, bộ thu có
thêm nguồn `mo_phong`: phát lại một kịch bản bình luận **tổng hợp** như một buổi live thật, đi hết
đường ống lọc PII → phân loại ý định → WebSocket → Bàn trợ live. Máy chủ chỉ cho dùng nguồn này trên
phiên **chạy thử** hoặc **phiên mẫu**, không bao giờ trộn vào dữ liệu thật.

---

## 1. Bảng tổng hợp

Cột "Hôm nay" = trạng thái ngày 11/09/2026 với đúng những gì repo đang có
(`.env` **trống** cả `YOUTUBE_API_KEY` lẫn `FACEBOOK_PAGE_ACCESS_TOKEN`).

| Nền tảng | Khả năng | Hôm nay | Cần gì | Hợp ToS? | Bằng chứng |
|---|---|:--:|---|:--:|---|
| **YouTube** | VOD đã kết thúc (chat replay) | ✅ **CHẠY** | không cần gì | ⚠️ yt-dlp trái ToS | §2.1 — chạy lại hôm nay: 6.963 bản tin chat |
| YouTube | Live đang phát — Data API | ❌ | `YOUTUBE_API_KEY` (miễn phí, ~10 phút) | ✅ **hợp lệ** | §2.2 — `.env` trống |
| YouTube | Live đang phát — yt-dlp | ✅ CHẠY | không cần gì | ❌ **trái ToS** | §2.2 — hôm nay tìm được 6 luồng đang phát |
| YouTube | Tín hiệu chuyển đổi (đơn/doanh thu) | ❌ | — | — | **không tồn tại** trên YouTube |
| **Facebook** | Live Page **của mình** — bình luận + người xem | ⏳ | Page token + 2 quyền (~25 phút) | ✅ **hợp lệ** | §3.4 · `docs/huong-dan-facebook-token.md` |
| Facebook | Video **đã kết thúc** của Page mình — bình luận | ⏳ chưa kiểm chứng | cùng token trên | ✅ hợp lệ | §3.5 — edge `/comments` có thật, chưa chạy được |
| Facebook | Page **của người khác** | ❌ | Advanced Access + Business Verification (4–6 tuần) | ✅ nếu được duyệt | §3.6 |
| Facebook | **Không token** — bình luận | ❌ **0 bình luận** | — | — | §3.1–3.3 — đã thử 3 đường, thật |
| Facebook | **Không token** — metadata + lượt xem gộp | ✅ có (làm tròn) | — | ⚠️ xám | §3.2 — `og:title` cho "2,8 triệu lượt xem · 1,2K cảm xúc" |
| **TikTok** | Live đang phát | ❌ | — | ❌ | `tiktok-collector-2026-09.md`: WebSocket 400, **10/10 lần**, 0 bình luận |
| TikTok | Video/live **đã kết thúc** — bình luận | ❌ | — | ❌ | §5.1 — WAF chặn; **yt-dlp không có** bộ đọc bình luận TikTok |
| TikTok | Research API (có endpoint bình luận) | ❌ **Việt Nam không đủ điều kiện** | quốc tịch tổ chức US/EEA/UK/CA/CH/BR | ✅ | §5.2 — trích nguyên văn điều kiện |
| **Shopee Live** | Live của **shop mình** — bình luận | ⏳ | tài khoản Open Platform + ủy quyền shop | ✅ **hợp lệ** | §4.1 — endpoint **đã kiểm chứng tồn tại** |
| Shopee Live | Live của shop mình — **GMV / đơn / ATC / CCU** | ⏳ | như trên | ✅ hợp lệ | §4.1 — `get_session_metric` |
| Shopee Live | Live **shop khác** / không tài khoản | ❌ | — | — | §4.2 — web công khai **không có chat** |
| **Lazada (LazLive)** | bất kỳ | ❓ **không xác định được** | `app_key` ISV mới dò được | — | §6.1 — cổng API từ chối trước khi định tuyến |
| **Instagram Live** | bình luận live | ❌ | cùng cổng Meta như Facebook | — | §6.2 |
| **Zalo** | live bán hàng | ❌ **không áp dụng** | — | — | §6.3 — Zalo OA API không có module live |
| **TikTok Shop Partner** | live của shop mình | ❓ chưa xác định | tài khoản Partner Center | — | §6.4 — chưa dò được, **không kết luận vội** |

**Đọc bảng này trong một câu:** hôm nay **YouTube VOD** là đường duy nhất chạy
được ngay lập tức trên buổi live của *người khác*; **Shopee** là đường duy nhất
có thể cho cả bình luận **lẫn đơn hàng** qua API chính thức; **TikTok là ngõ
cụt** và nên bị đóng lại trong kế hoạch.

---

## 2. YouTube

### 2.1 VOD đã kết thúc — CHẠY ĐƯỢC, và đã chạy lại hôm nay

Đây là đường đang gánh toàn bộ live-fire của dự án: 16 buổi (10/09) + 8 buổi
(11/09) đi qua `POST /replays/youtube`.

**Kiểm chứng lại hôm nay 11/09/2026** (yt-dlp 2026.08.19, mạng gia đình):

```bash
yt-dlp --skip-download --write-subs --sub-langs live_chat \
       -o "vod.%(ext)s" "https://www.youtube.com/watch?v=ZU_0QJzsR6w"
```

| | Kết quả THẬT |
|---|---|
| Tệp `vod.live_chat.json` | **10.210.279 byte** |
| Số dòng | **6.965** |
| Bản tin chat (`addChatItemAction`) | **6.963** |
| Kết luận | Đường VOD **vẫn sống nguyên** ngày 11/09/2026 |

> Tệp chat thô **chứa tên người bình luận** — đã **xóa ngay** sau khi đếm, đúng
> quy tắc "chat thô không bao giờ nằm lại trên đĩa".

**Cách dùng (dán link là xong):**

```bash
curl -X POST http://127.0.0.1:8000/replays/youtube \
     -H "Content-Type: application/json" \
     -d '{"url":"https://www.youtube.com/watch?v=<VIDEO_ID>"}'
curl http://127.0.0.1:8000/replays/jobs/<job_id>   # queued→downloading→ingesting→done
```

**Ràng buộc thật, không phải chi tiết kỹ thuật:** *có* track `live_chat` **không**
có nghĩa là *có* chat. Đo 10/09: trong 17 video thử, 16 vào được nhưng chỉ **7
buổi đạt ≥ 100 bình luận**, 1 buổi 715 phút có **0 bình luận**. Tìm được buổi
live bán hàng tiếng Việt chat đủ dày là việc khó — hãy tính thời gian tìm nguồn
vào kế hoạch.

### 2.2 Live đang phát — hai đường, chọn đường nào

Tìm luồng đang phát vẫn chạy tốt hôm nay:

```bash
yt-dlp --flat-playlist --playlist-end 6 \
  --print "%(id)s|%(live_status)s|%(concurrent_view_count)s|%(title).40s" \
  "https://www.youtube.com/results?search_query=live+bán+hàng&sp=EgJAAQ%253D%253D"
```

Kết quả THẬT lúc 12:5x ngày 11/09: **6/6 luồng `is_live`**, có số người xem thật
(`4SddnVIBntc` 29 · `oFpVZ91wbkA` 50 · `q-BvtDrTnxc` 9 · `eAlqLqahw6U` 68 ·
`ufwLk92fA9k` 259), gồm cả live bán hàng tiếng Việt (mai vàng, đồ ăn vặt).

| | `INGEST_YOUTUBE_BACKEND=api` | `=ytdlp` |
|---|---|---|
| **(a) Hôm nay chạy được?** | ❌ — `.env` để `YOUTUBE_API_KEY=` trống | ✅ chạy được ngay |
| **(b) Cần gì** | Tạo project Google Cloud, bật YouTube Data API v3, lấy key. **Miễn phí, không cần thẻ, không cần app review, ~10 phút.** | Không cần gì |
| **(c) Hợp ToS?** | ✅ **HỢP LỆ** | ❌ **KHÔNG** — robots.txt của YouTube `Disallow: /live_chat` và `/youtubei/`, đúng hai đường yt-dlp gọi |
| Độ trễ giao tin | 2–5 s | **~24 s (p50), 37 s (p90)** — đo thật |
| Quota | 10.000 đv/ngày; phiên 90 phút poll 5 s ≈ 5.400 đv (**quá nửa ngày**) | không có |

**Việc phải làm, thứ tự đúng:** xin key trước (rào cản chỉ là *chưa ai tạo
project*, không phải tiền hay xét duyệt); chạy phiên chính thức trên `api`; giữ
`ytdlp` cho kiểm thử kỹ thuật và phiên của chính nhóm. Nếu dữ liệu thu bằng
yt-dlp vào bài báo thì **phải khai báo phương pháp thu thập** trong mục đạo đức.

Chi tiết đầy đủ: [`research/2026-09-09-youtube-ytdlp-live.md`](research/2026-09-09-youtube-ytdlp-live.md).

---

## 3. Facebook — kết quả THẬT của 5 đường thử không token

Câu hỏi được đặt ra là: *"có đường nào không cần token không?"* Đã thử thật cả 5.
**Câu trả lời: không, đối với bình luận.** Dưới đây là mã lỗi nguyên văn.

### 3.1 Graph API không token — 400/403, không lách được

```
GET https://graph.facebook.com/v25.0/me
  -> HTTP 400 {"error":{"message":"An active access token must be used to query
     information about the current user.","type":"OAuthException","code":2500,...}}

GET https://graph.facebook.com/v25.0/<id>/comments
  -> HTTP 400 {"error":{"message":"An access token is required to request this
     resource.","type":"OAuthException","code":104,...}}

GET https://graph.facebook.com/v25.0/shopeevn/live_videos
  -> HTTP 403 {"error":{"message":"(#200) Provide valid app ID",
     "type":"OAuthException","code":200,...}}
```

Ba lỗi khác nhau cho ba kiểu truy vấn, nhưng cùng một kết luận: **không có
token thì không có gì.**

**Mẹo dò có ích (không cần token):** Graph phân biệt *edge có thật* với *edge
bịa* ngay cả khi ẩn danh — edge thật trả `code 100` ("Unsupported get request.
Object with ID '1' does not exist"), edge bịa trả `code 2500` ("Unknown path
components"). Đã dùng để xác nhận:

| Đường | Mã | Kết luận |
|---|---|---|
| `/1/comments` · `/1/live_videos` · `/1/videos` · `/1/video_insights` · `/1/live_media` | 100 | **edge CÓ THẬT** |
| `/1/live_views` | 2500 | là **trường**, không phải edge (khớp `facebook.py` đang dùng `?fields=live_views`) |
| `/1/live_comments` | 2500 | **không** nằm trên `graph.facebook.com` — đúng như docstring của repo: luồng SSE nằm ở host `streaming-graph.facebook.com` |
| `/1/khong_co_edge_nay` (đối chứng) | 2500 | không tồn tại ✔ phép thử có răng |

### 3.2 Trang video công khai (không đăng nhập) — có metadata, **0 bình luận**

Thử trên video công khai thật của chính Meta
(`facebook.com/facebook/videos/10153231379946729/`):

| | Kết quả THẬT |
|---|---|
| HTTP | **200**, **≈450 KB** (456.173 byte lúc 12:47; 443.431 byte lúc 13:12 — trang động, kích thước đổi mỗi lần tải) |
| `<title>` | `How to share with just friends.` ✅ đọc được |
| `og:title` | `2,8 triệu lượt xem · 1,2K cảm xúc \| How to share…` ✅ **có lượt xem + cảm xúc** (đã làm tròn, tiếng Việt) |
| `"comment_count"` trong HTML | **0 lần xuất hiện** |
| `"body":{"text"` (thân bình luận) | **0 lần** |
| `top_level_comments` · `"total_count"` · `"feedback"` | **0 lần** mỗi cái |
| `CometUFI` | **45 lần** — nhưng **chỉ là tên component React**, không kèm dữ liệu |
| chuỗi con `comment` (mọi dạng) | 18 lần — toàn là tên biến/tham số URL (`focuscommentid`, `comment_id`), **không có một nội dung bình luận nào** |

Nói cho chính xác: **HTML công khai cho biết video tên gì và bao nhiêu lượt xem
(làm tròn), nhưng không chứa một chữ nào của bình luận.** Facebook render bình
luận sau, bằng truy vấn có xác thực.

### 3.3 Hai đường vòng cổ điển — **đều đã chết**

| Đường | Kết quả THẬT |
|---|---|
| `mbasic.facebook.com/...` (bản không JS, cách scrape kinh điển) | **HTTP 400**, `<title>Error Facebook</title>` — với *mọi* URL đã thử |
| `m.facebook.com/...` | 301 → `www.facebook.com/...?_rdr`, y hệt bản desktop |
| `facebook.com/<page>/videos` khi chưa đăng nhập | **HTTP 400**, *"Sorry, something went wrong."* |
| `oembed_video` (không token) | HTTP **200** nhưng chỉ trả **thẻ nhúng**; trả 200 kể cả với video id **bịa** → không phải nguồn dữ liệu |
| `yt-dlp` trên video FB công khai | rc=**0**, lấy được `id\|title\|duration`; `comment_count` = **NA**; `--write-comments` → **NA** |

Kiểm tra mã nguồn cho chắc: `yt_dlp/extractor/facebook.py` **không có
`_get_comments`** — yt-dlp *chưa bao giờ* đọc bình luận Facebook, nên đây không
phải chuyện "hỏng hôm nay, mai sửa".

### 3.4 Live của Page **mình** — đường đúng, cần ~25 phút

- **(a) Hôm nay?** Chưa — `.env` có `FACEBOOK_PAGE_ACCESS_TOKEN=` **trống**.
- **(b) Cần gì:** 1 Fanpage do nhóm quản trị + 1 app Meta ở **Development Mode**
  + Page token dài hạn với **`pages_read_engagement`** *và* **`pages_read_user_content`**.
  **KHÔNG cần App Review.** Từng bước: [`huong-dan-facebook-token.md`](huong-dan-facebook-token.md).
  Kiểm tra: `python scripts/kiem_tra_facebook.py`.
- **(c) ToS:** ✅ hợp lệ — đọc nội dung công khai trên tài sản mình sở hữu.

> **Cái bẫy đắt nhất:** `pages_read_engagement` chỉ cho đọc nội dung **Page tự
> đăng**. Bình luận là nội dung **người xem**. Thiếu `pages_read_user_content`
> thì đọc được **0 bình luận** — mà đó chính là biến kết quả của LiveLift.

### 3.5 Video **đã kết thúc** của Page mình — có đọc được bình luận không?

**Trả lời trung thực: gần như chắc chắn CÓ, nhưng nhóm CHƯA kiểm chứng được.**

Cái đã xác nhận hôm nay:
- Edge `/{video-id}/comments` **có thật** (phép thử code-100 ở §3.1).
- Tài liệu lỗi của Meta cho edge này ghi mã 283: *"That action requires the
  extended permission **pages_read_engagement and/or pages_read_user_content**
  and/or pages_manage_ads and/or pages_manage_metadata"* — tức đúng bộ quyền
  đã dùng cho live.
- Buổi live kết thúc sẽ đi LIVE → LIVE_STOPPED → PROCESSING → **VOD**; ở trạng
  thái VOD nó là một video của Page và bình luận vẫn nằm đó.

Cái **chưa** xác nhận: tài liệu `live-video/comments` **không nói một chữ nào**
về việc edge còn dùng được sau khi phát xong (đã đọc, mục "Live vs. Ended" trống).
Không có token nên không thử được. **Đừng ghi vào hồ sơ như việc đã chạy.**
Việc cần làm: sau khi có token, phát live thử 2 phút, kết thúc, rồi gọi
`/{video-id}/comments` — 5 phút là biết.

### 3.6 Page của **người khác** — cần App Review, tính bằng tuần

| Tình huống | App Review? | Thời gian thực tế |
|---|---|---|
| Page **của nhóm mình** | **KHÔNG** | ~25 phút |
| Page **đối tác** (nhà bán khác) | **CÓ** — Advanced Access cho `pages_read_engagement` + `pages_read_user_content`, **kèm Business Verification trước** | Verification 10+ ngày; mỗi quyền cần 1 video quay màn hình; 2–7 ngày nếu hồ sơ sạch, ~20 ngày nếu bị trả lại, **mỗi lần bị từ chối là đếm lại** → **dự trù 4–6 tuần** |

Và ranh giới không được lách: chỉ thu thập trên Page **mình sở hữu**, hoặc Page
đối tác **đã có văn bản đồng ý + Advanced Access**. Dùng token của người khác
để đọc Page họ không đồng ý là **vi phạm Điều khoản Nền tảng của Meta**.

---

## 4. Shopee Live — **phát hiện lớn nhất của đợt khảo sát này**

### 4.1 Có API chính thức cho bình luận live. Và có cả đơn hàng.

Shopee Open Platform v2 có hẳn module `livestream`. Đây **không** phải suy đoán —
phép thử có đối chứng, chạy thật hôm nay:

```
GET https://partner.shopeemobile.com/api/v2/livestream/get_latest_comment_list
  -> HTTP 200 {"error":"error_param","message":"There is no partner_id in query.",
               "request_id":"e3e3e7f35b2e74147c7e63bc3f885900"}        ← ENDPOINT CÓ THẬT

GET https://partner.shopeemobile.com/api/v2/livestream/khong_ton_tai_abc
  -> HTTP 404 {"error":"error_not_found"}                              ← ĐỐI CHỨNG: bịa thì 404

GET https://partner.shopeemobile.com/api/v2/livestream/get_session_list
  -> HTTP 404 {"error":"error_not_found"}                              ← endpoint này KHÔNG có
```

Ký thử đúng lược đồ với `partner_id`/`partner_key` **giả**:

```
-> HTTP 403 {"error":"invalid_partner_id","message":"Invalid partner_id, please have a check."}
```

Tức là **cổng API chấp nhận dạng yêu cầu của chúng ta** và chỉ từ chối vì danh
tính giả. Chỉ còn thiếu đúng một thứ: tài khoản thật.

**Ba endpoint đáng giá** (mô tả lấy từ tài liệu Shopee; mọi dòng đều ghi
`(For TW, ID, TH, PH, MY, SG, VN)` — **có Việt Nam**):

| Endpoint | Trả về |
|---|---|
| `/livestream/get_latest_comment_list` | `comment_id`, `content`, `timestamp`, *(user_id, username — ta **bỏ**)*; phân trang `offset`/`next_offset`. **Chỉ 10 giây gần nhất.** |
| `/livestream/get_session_metric` | `gmv` · `orders` · `atc` · `ctr` · `co` · **`ccu`** · `engage_ccu_1m` · `peak_ccu` · `likes` · `comments` · `shares` · `views` · `avg_viewing_duration` |
| `/livestream/get_session_detail` | `title`, `status` (0 chưa bắt đầu / 1 đang phát / 2 kết thúc), `start_time`, `end_time`, `share_url` |

> **Vì sao đây là phát hiện lớn:** YouTube cho bình luận **nhưng không có một
> tín hiệu thương mại nào**. TikTok không cho gì. Shopee cho **cả bình luận lẫn
> GMV/đơn/ATC** — tức là lần đầu tiên có một nền tảng vừa cho *biến can thiệp*
> (shop tự chạy phiên của mình nên **gán ngẫu nhiên được**) vừa cho *biến kết
> quả thật*. Đó chính xác là thứ một thí nghiệm switchback cần và là thứ 24 buổi
> live-fire YouTube **không bao giờ** cung cấp được.

### 4.2 Không có tài khoản thì sao? — Web công khai KHÔNG có chat

Đã thử thật, và câu trả lời dứt khoát:

| Đường thử | Kết quả THẬT |
|---|---|
| `live.shopee.vn/share?from=live&session=…` | HTTP 200 nhưng `__NEXT_DATA__` chỉ có `setupStore` **rỗng** (`"sessionid": null`) — trang này là **màn hình đẩy sang app**, không phải trình phát |
| `live.shopee.vn/api/v1/session/1` | **HTTP 403** `{"is_login": false, "error": 90309999, "redirect_to_error_page": true}` |
| `live.shopee.vn/api/v1/session/list` | **HTTP 403** `{"err_code": 7913016, "err_msg": "ErrorSVFailed"}` |
| Grep **12.971.905 byte** bundle JS của `live.shopee.vn/pc/live` | Tìm thấy ~50 đường `/api/v2`–`/api/v4` của sàn (tìm kiếm, sản phẩm, shop) và hàng chục đường `/session/${id}/…` **phía người phát** (thêm hàng, ghim, kết thúc phiên); **KHÔNG có** endpoint bình luận phía người xem, **KHÔNG có** một URL `wss://` nào |
| Đối chứng mạng: `shopee.vn/api/v4/pages/get_homepage_category_list` | **HTTP 200 + dữ liệu thật** → mạng **không** bị chặn; 403 ở trên là **chính sách**, không phải sự cố |

**Kết luận:** Shopee Live trên web là "xem thì mở app". Không có đường công khai
nào lấy được bình luận, kể cả một bình luận. Đừng tìm nữa.

### 4.3 Ba câu trả lời cho Shopee

- **(a) Hôm nay?** ❌ Chưa — `.env` chưa có `SHOPEE_PARTNER_ID`. **Adapter đã
  viết xong và có bộ test không chạm mạng** (số test đếm theo ngày ở bảng §4.4),
  nhưng **chưa có một cuộc gọi thật nào**: khi có danh tính, chạy
  `scripts/kiem_tra_shopee.py` trước (§4.4) rồi mới bật bộ thu.
- **(b) Cần gì** (bảng *Danh tính cần có trong `.env`* ở §4.4 là bản đầy đủ):
  1. Tài khoản **Shopee Open Platform** (`open.shopee.com`) → `partner_id` + `partner_key`.
  2. Chủ shop (chính nhóm, hoặc đối tác **có văn bản đồng ý**) chạy luồng **ủy
     quyền OAuth** → `user_id` của tài khoản người phát (`user_id_list` trong
     phản hồi `v2.public.get_access_token`, điền vào `SHOPEE_USER_ID` — **bắt
     buộc**, API livestream là loại "User" và ký bằng `user_id`) + `access_token`
     + `refresh_token`. `shop_id` **chỉ** cần để ghim sản phẩm
     (`update_show_item`); đọc bình luận, người xem, chỉ số không cần nó. Thiếu
     `SHOPEE_USER_ID` thì trang Bắt đầu báo Shopee thiếu khoá và bộ thu dừng với
     *"Thiếu danh tính Shopee trong .env: SHOPEE_USER_ID"*.
  3. ⚠️ **`access_token` của Shopee chỉ sống 4 GIỜ** — phiên live dài **phải**
     làm mới bằng `refresh_token` (theo `user_id`) giữa chừng. LiveLift **chưa
     tự làm mới** (17/09/2026): hết hạn thì người kỹ thuật cấp token mới, dán vào
     `.env` rồi khởi động lại máy chủ. Đây là khác biệt lớn so với Page token
     Facebook (không hết hạn).
  4. Chưa xác minh được: thời gian duyệt tài khoản Open Platform, và hạn mức gọi
     API. **Không bịa số** — phải đọc trong Partner Portal sau khi đăng ký.
- **(c) ToS:** ✅ **Hợp lệ** — API chính thức, token do chủ shop tự cấp. Đây là
  đường **sạch nhất** trong toàn bộ tài liệu này. Ranh giới: chỉ đọc shop đã ủy
  quyền; đọc shop chưa đồng ý là vi phạm.

### 4.4 Đã viết sẵn trong repo (gói này)

*Cập nhật 17/09/2026: danh tính loại "User", bộ thu trên web, số test. Vẫn **chưa
có một cuộc gọi thật nào** bằng tài khoản Shopee.*

| Tệp | Nội dung |
|---|---|
| `src/livelift/ingest/shopee.py` | `ShopeeLiveClient`: ký HMAC-SHA256 trên `partner_id + đường dẫn đầy đủ /api/v2/livestream/… + timestamp + access_token + user_id` (API livestream là loại **"User"**, sửa 17/09 — trước đó ký bằng `shop_id` trên phần đuôi đường dẫn), `iter_comments`, `iter_viewers`, `get_session_metric`, `update_show_item`, phân loại lỗi auth / rate-limit / chưa phát / transient |
| `tests/test_ingest_shopee.py` | **57 test** (đếm 17/09/2026 tại commit `abbbeb1`), không chạm mạng. Số này là ảnh chụp theo commit, sẽ tăng khi thêm test; số hiện tại: `pytest tests/test_ingest_shopee.py --collect-only -q` |
| `scripts/kiem_tra_shopee.py` | `--session-id <ID>` → bảng tiếng Việt "SẴN SÀNG / CHƯA SẴN SÀNG", mã thoát 0/1. Chỉ đọc |
| `.env.example` | khối `SHOPEE_*` kèm giải thích |
| `runner.py` | `--platform shopee` (đường CLI) |
| `src/livelift/api/ingest_jobs.py` | Bộ thu **chạy nền trong API** — bật bằng nút *Bật bộ thu* trên web, chọn *Shopee Live (shop của bạn)*, dán `session_id` |

**Danh tính cần có trong `.env`:**

| Biến | Bắt buộc? | Ghi chú |
|---|---|---|
| `SHOPEE_PARTNER_ID`, `SHOPEE_PARTNER_KEY` | **Bắt buộc** | Từ Shopee Open Platform |
| `SHOPEE_USER_ID` | **Bắt buộc** | Mã **tài khoản người phát** đã ủy quyền cho app (`user_id_list` trong phản hồi `v2.public.get_access_token`) — **không phải** mã shop, và không liên quan `user_id` của người bình luận. Là dãy số |
| `SHOPEE_ACCESS_TOKEN` | **Bắt buộc** | Cấp cho đúng `SHOPEE_USER_ID`; chỉ sống **4 giờ** |
| `SHOPEE_SHOP_ID` | Chỉ để **ghim sản phẩm** | Tham số thân của `update_show_item`. Đọc bình luận, người xem, chỉ số **không** cần — thiếu thì `kiem_tra_shopee.py` chỉ cảnh báo, không chặn |
| `SHOPEE_REFRESH_TOKEN` | Nên có | Thiếu thì script cảnh báo |
| `SHOPEE_REGION` | Mặc định `global` | Việt Nam dùng cổng global |

Trang Bắt đầu (`GET /platforms`) coi Shopee là *Sẵn sàng* khi đủ bốn biến bắt buộc
ở trên.

**Ba quyết định thiết kế đến từ đặc tính thật của API — đọc trước khi sửa:**

1. **Cửa sổ 10 giây → nhịp poll bị ép cứng.** `get_latest_comment_list` chỉ trả
   bình luận *10 giây gần nhất* và **không có con trỏ `since`**: poll chậm hơn
   là **mất vĩnh viễn**. Nên `iter_comments` **ném `ValueError` ngay** nếu
   `poll_s > 8.0`, chứ không chạy rồi âm thầm bỏ sót bình luận trong một thí
   nghiệm nhân quả. Mặc định 5 s → mỗi bình luận về ~2 lần, khử trùng lặp theo
   `comment_id`.
2. **Token bắt buộc nằm trong query string → lỗi phải giấu URL.** Lược đồ ký của
   Shopee đưa `access_token` và `user_id` vào chuỗi HMAC nên chúng **phải** là
   tham số query (không đẩy sang header như Facebook được). `httpx` nhét URL đầy
   đủ vào mọi `HTTPStatusError`, nên mọi lỗi được gói thành `ShopeeApiError` chỉ
   mang mã lỗi + `request_id`. Có test khẳng định token **không** xuất hiện
   trong thông điệp lỗi, kể cả lỗi mạng.
3. **`username` bị bỏ ngay tại parser.** Phản hồi Shopee có `user_id` và
   `username`; `parse_comment` chỉ đọc `comment_id`/`content`/`timestamp`. Có
   test khẳng định cả hai không lọt ra (hard rule 1 + §11.2).

**Cảnh báo về biến kết quả:** `get_session_metric` trả **số cộng dồn từ đầu
phiên**, không phải sự kiện có dấu thời gian. Muốn số theo khối switchback thì
phải lấy **hiệu** giữa hai mốc đầu/cuối khối — và **phải khai báo trong phương
pháp** rằng biến kết quả là sai phân của một bộ đếm cộng dồn. Đây là điểm phản
biện chắc chắn bị hỏi.

**Chạy thử khi có danh tính** (đủ `SHOPEE_PARTNER_ID`, `SHOPEE_PARTNER_KEY`,
`SHOPEE_USER_ID`, `SHOPEE_ACCESS_TOKEN`):

```bash
# 1) Kiểm tra danh tính + phiên (chỉ đọc). Chạy lúc buổi live ĐANG PHÁT thì mới
#    thử được đường đọc bình luận; chạy trước giờ phát thì chỉ nhận cảnh báo.
python scripts/kiem_tra_shopee.py --session-id <SESSION_ID>

# 2a) Cách khuyên dùng — bật từ web: Bàn trợ live (hoặc bước 4 Chuẩn bị phiên)
#     → Nền tảng "Shopee Live (shop của bạn)" → dán <SESSION_ID> → "Bật bộ thu".
#     Bật TRƯỚC giờ phát được: bộ thu hiện "Chờ buổi live bắt đầu" và tự thu khi lên sóng.
#     Chỉ dùng được khi máy chủ CHƯA đặt INGEST_TOKEN (web chưa gửi token → 401, §0 dòng 1);
#     máy chủ công khai thì dùng 2b.

# 2b) Đường CLI — chỉ chạy SAU KHI đã bấm phát trên app Shopee. Chạy trước giờ phát
#     thì lệnh dừng ngay với "Bộ thu dừng: … KHÔNG có buổi live nào đang phát" (mã thoát 1),
#     vì client Shopee không tự chờ; runner tự đính INGEST_TOKEN từ .env.
python -m livelift.ingest.runner --platform shopee \
    --source-id <SESSION_ID> --session-id <uuid> --api-url http://localhost:8000
```

---

## 5. TikTok — đóng lại, và nói thẳng lý do

### 5.1 Đã kết thúc hay đang phát: đều không

Live đang phát đã có kết luận từ 09/09: bắt tay WebSocket bị từ chối **HTTP 400,
10/10 lần**, **0 bình luận** ([`benchmarks/tiktok-collector-2026-09.md`](benchmarks/tiktok-collector-2026-09.md)).

Hôm nay thử tiếp **video/live đã kết thúc** — cũng không:

| Đường | Kết quả THẬT |
|---|---|
| `tiktok.com/@quyenleo` (trang hồ sơ) | HTTP 200 nhưng chỉ **1.462 byte**: trang thử thách WAF (`"slardarClient": "SlardarWAF"`, `class="_wafchallengeid"`), không có nội dung |
| `tiktok.com/@quyenleo/live` | HTTP 200, **1.155 byte** — cùng trang WAF |
| `tiktok.com/api/comment/list/` (không chữ ký) | HTTP 200 `{"log_pb":{...},"status_code":5,"status_msg":""}` — **status_code 5 = từ chối**; thêm tham số web chuẩn → **thân phản hồi 0 byte** |
| `tiktok.com/api/live/detail/?roomID=…` | HTTP 400 `{"statusCode":10201,"statusMsg":"missing required fields..."}` |
| `yt-dlp` trên video TikTok | `ERROR: [TikTok] …: Unexpected response from webpage request` |

Và điều quyết định: `yt_dlp/extractor/tiktok.py` **không có `_get_comments`**.
Kể cả nếu WAF mở ra ngày mai, yt-dlp **vẫn không đọc bình luận TikTok** — đây
không phải sự cố tạm thời mà là **tính năng chưa từng tồn tại**.

### 5.2 Research API có endpoint bình luận — nhưng Việt Nam không đủ điều kiện

TikTok **có** `POST https://open.tiktokapis.com/v2/research/video/comment/list/`.
Điều kiện, **nguyên văn từ trang sản phẩm Research API**:

> *"Academic institutions in the U.S., EEA, UK, Canada, or Switzerland; or
> Not-for-profit and/or independent research institution, organization,
> association, or body in the EU"* — cộng thêm Brazil cho nghiên cứu an toàn
> trẻ vị thành niên; bản beta đang chạy ở U.S., UK, Switzerland, Norway,
> Iceland, Liechtenstein.

**Việt Nam không nằm trong danh sách.** FAQ chỉ nói *"we hope to expand
eligibility to additional regions soon"* — tức là một lời hứa, không phải một
lộ trình có ngày.

### 5.3 Ba câu trả lời cho TikTok

- **(a) Hôm nay?** ❌ Không, bằng mọi đường đã thử.
- **(b) Cần gì:** một tư cách pháp nhân mà nhóm **không thể có** (tổ chức học
  thuật Mỹ/EU/UK/Canada/Thụy Sĩ), hoặc **TikTok Live/Partner API chính thức**
  qua quan hệ đối tác thương mại.
- **(c) ToS:** thư viện `TikTokLive` là **dịch ngược giao thức Webcast** — dùng
  nó **có thể vi phạm ToS TikTok**, và còn đẩy lưu lượng qua proxy bên thứ ba.

**Cách trình bày đúng trong hồ sơ thi** — biến thất bại kỹ thuật thành luận
điểm về tính chính trực:

> *"TikTok là kênh live-commerce lớn nhất Việt Nam nhưng không có API công khai
> cho bình luận live. Chúng tôi đã hiện thực và kiểm chứng một bộ thu thập cách
> ly; tính đến 11/09/2026 đường không chính thức bị chặn ở tầng WebSocket
> (HTTP 400, 10/10 lần) và ở tầng WAF với nội dung đã kết thúc, còn Research API
> chính thức không mở cho tổ chức Việt Nam. Kết quả của chúng tôi vì vậy dựa
> trên các nền tảng có API chính thức."*

---

## 6. Các nền tảng khác — đánh giá nhanh, có đo

### 6.1 Lazada (LazLive) — **không kết luận được**, và nói rõ là không kết luận được

```
GET https://api.lazada.vn/rest/livestream/comment/get?app_key=123456&…
  -> HTTP 200 {"type":"ISV","code":"InvalidAppKey","message":"The specified App Key is invalid"}
GET https://api.lazada.vn/rest/khong_ton_tai/abc?app_key=123456&…          (ĐỐI CHỨNG)
  -> HTTP 200 {"type":"ISV","code":"InvalidAppKey","message":"The specified App Key is invalid"}
```

Đường thật và đường bịa cho **y hệt** một lỗi: cổng Lazada kiểm `app_key`
**trước khi** định tuyến. Nên **không thể dò** xem có API livestream hay không
nếu chưa là ISV đã đăng ký.

- **(a) Hôm nay?** ❌ · **(b) Cần:** tài khoản ISV Lazada Open Platform (thời
  gian duyệt: chưa biết) · **(c) ToS:** sẽ hợp lệ nếu đi qua API chính thức.
- Ghi chú nghiệp vụ: một buổi `[LAZLIVE]` **đã** vào hệ thống qua YouTube VOD
  (`jUMO3oUfVnE`, 5 bình luận/136 phút) — tức các shop Lazada có phát song song
  lên YouTube, và đó là đường vòng rẻ tiền để quan sát mà **không** cần API.

### 6.2 Instagram Live — cùng cổng Meta, không thêm gì mới

- `/1/live_media` là **edge có thật** (code 100); `graph.instagram.com/me` trả
  `{"error":{"message":"Invalid OAuth 2.0 Access Token","type":"IGApiException","code":190}}`.
- Cùng một cánh cổng với Facebook: tài khoản IG Business liên kết Page + App
  Review cho tài khoản người khác. **Không mở thêm khả năng nào** so với §3, mà
  thị phần live-commerce ở Việt Nam lại nhỏ hơn hẳn.
- **Khuyến nghị: bỏ qua.** Nếu đã phải làm App Review của Meta thì làm cho
  Facebook — nơi có người bán thật.

### 6.3 Zalo — **không áp dụng**

```
GET https://openapi.zalo.me/v2.0/oa/getprofile   -> {"error":-216,"message":"Access token is invalid"}
GET https://openapi.zalo.me/v2.0/oa/khongtontai  -> {"error":404,"message":"You are accessing an
                                                     empty or invalid API..."}
```

Cổng Zalo **có** phân biệt endpoint thật/bịa, nên phép dò đáng tin. Sản phẩm
Official Account xoay quanh **tin nhắn**, không có module livestream. Zalo không
phải nền tảng live-commerce ở quy mô đáng đo. **Bỏ qua.**

### 6.4 TikTok Shop Partner API — chưa dò được, **đừng kết luận vội**

```
GET https://open-api.tiktokglobalshop.com/authorization/202309/shops
  -> HTTP 400 {"code":36009004,"message":"Invalid credentials. Invalid 'app_key' query parameter."}   ← có thật
GET https://open-api.tiktokglobalshop.com/live/202309/comments   -> HTTP 404
GET https://open-api.tiktokglobalshop.com/khong_ton_tai/abc      -> HTTP 404   ← ĐỐI CHỨNG cũng 404
```

Đường `live/...` là **do tôi đoán tên**, và đối chứng cũng 404 — nên **404 ở đây
chỉ có nghĩa "đoán sai tên", không có nghĩa "không tồn tại"**. Phải đăng nhập
Partner Center đọc danh mục v2 mới biết.

**Vì sao đáng bỏ 30 phút kiểm tra:** TikTok Shop là kênh live-commerce **lớn
nhất Việt Nam**. Nếu API bán hàng của họ có module live giống Shopee, nó sẽ là
nguồn dữ liệu giá trị nhất trong cả đề tài — và hoàn toàn **hợp ToS** vì là API
chính thức cho shop của chính mình. **Đây là việc số 1 trong lộ trình.**

---

## 7. Tóm tắt (a) / (b) / (c) — một chỗ nhìn

| Nền tảng | (a) Hôm nay test được? | (b) Cần gì | (c) Hợp ToS? |
|---|---|---|---|
| YouTube VOD | ✅ **có, ngay** | không gì | ⚠️ yt-dlp trái ToS — khai báo phương pháp |
| YouTube live (API) | ❌ | `YOUTUBE_API_KEY`, **miễn phí ~10 phút** | ✅ hợp lệ |
| YouTube live (yt-dlp) | ✅ có | không gì | ❌ trái ToS |
| Facebook — Page mình | ⏳ | Page token + 2 quyền, **~25 phút, không cần App Review** | ✅ hợp lệ |
| Facebook — Page khác | ❌ | Advanced Access + Business Verification, **4–6 tuần** + văn bản đồng ý | ✅ nếu được duyệt |
| Facebook — không token | ❌ **0 bình luận** | — | — |
| Shopee — shop mình | ⏳ | Open Platform + ủy quyền shop; **token sống 4 giờ** | ✅ **hợp lệ (sạch nhất)** |
| Shopee — shop khác | ❌ | — | — |
| TikTok — mọi đường | ❌ | pháp nhân US/EU/UK/CA/CH | ❌ (đường không chính thức) |
| Lazada | ❓ | tài khoản ISV mới dò được | — |
| Instagram | ❌ | như Facebook, ít giá trị hơn | — |
| Zalo | ❌ **không áp dụng** | — | — |
| TikTok Shop | ❓ **cần kiểm tra** | tài khoản Partner Center | có thể ✅ |

---

## 8. Lộ trình mở thêm nền tảng — xếp theo (giá trị ÷ công sức)

| # | Việc | Công | Được gì |
|---|---|---|---|
| **1** | **Xin `YOUTUBE_API_KEY`** | **10 phút** | Biến toàn bộ đường YouTube từ "trái ToS" thành **hợp lệ**. Rẻ nhất, giá trị cao nhất, chặn được câu phản biện nặng nhất. |
| **2** | **Dò danh mục API TikTok Shop Partner** (§6.4) | 30 phút | Nếu có module live → nguồn dữ liệu **giá trị nhất cả đề tài** (nền tảng #1 VN, hợp ToS). Nếu không → đóng dứt điểm, hết bàn. |
| **3** | **Lấy Facebook Page token** + phát live thử 2 phút | 25 phút + 5 phút | Live-fire **ĐANG PHÁT** trên nền tảng hợp ToS đầu tiên; đồng thời trả lời dứt điểm câu "video đã kết thúc có đọc được bình luận không" (§3.5) |
| **4** | **Đăng ký Shopee Open Platform** + ủy quyền shop | vài ngày (chờ duyệt) | Nền tảng duy nhất cho **bình luận + GMV/đơn/ATC** ⇒ mở đường cho switchback **thật** có biến kết quả thương mại. Adapter đã sẵn sàng. |
| 5 | Cân nhắc Lazada ISV | chưa rõ | Chỉ làm sau khi #2 và #4 có kết luận |
| — | ~~TikTok không chính thức~~ | — | **Đóng lại.** Không đầu tư thêm một giờ nào. |
| — | ~~Instagram / Zalo~~ | — | **Bỏ qua.** Không mở thêm khả năng nào. |

**Nguyên tắc xuyên suốt, phải giữ:** dữ liệu vào bài báo chỉ đến từ **API chính
thức** trên **tài sản mình sở hữu hoặc đã được đồng ý bằng văn bản**. Mọi thứ
khác là quan sát kỹ thuật, phải **ghi rõ phương thức thu thập**, và không bao giờ
được trình bày như dữ liệu API.

---

## 9. Cách tái lập toàn bộ phép đo trong tài liệu này

Các script dò nằm **ngoài repo** (thư mục tạm) vì chỉ dùng một lần. Toàn bộ phép
đo mạng trong tài liệu này chạy lại được bằng đúng đoạn dưới (chỉ cần `httpx` và
`yt-dlp` có sẵn trong `.venv`). Đã chạy thử đoạn này để chắc nó không hỏng:

```bash
cd d:/AISC2026/livelift
.venv/Scripts/python - <<'PY'
import httpx
UA = {"User-Agent": "Mozilla/5.0"}

# 1) Facebook — phép thử edge có thật / edge bịa (KHÔNG cần token)
for edge in ("comments", "live_videos", "live_comments", "khong_co_edge_nay"):
    r = httpx.get(f"https://graph.facebook.com/v25.0/1/{edge}", headers=UA, timeout=30)
    code = r.json().get("error", {}).get("code")
    print(f"FB /1/{edge:20s} code={code}  {'EDGE THẬT' if code != 2500 else 'KHÔNG TỒN TẠI'}")

# 2) Facebook — trang video công khai: có metadata, KHÔNG có bình luận
t = httpx.get("https://www.facebook.com/facebook/videos/10153231379946729/",
              headers=UA, follow_redirects=True, timeout=60).text
print("FB HTML:", len(t), 'byte | "comment_count":', t.count('"comment_count"'),
      '| thân bình luận:', t.count('"body":{"text"'))

# 3) Shopee — phép thử CÓ ĐỐI CHỨNG (đường thật vs đường bịa)
for p in ("/api/v2/livestream/get_latest_comment_list",
          "/api/v2/livestream/khong_ton_tai_abc"):
    r = httpx.get("https://partner.shopeemobile.com" + p, headers=UA, timeout=30)
    print("Shopee", p, "->", r.status_code, r.text[:90])

# 4) TikTok — API bình luận web không chữ ký + tường WAF
r = httpx.get("https://www.tiktok.com/api/comment/list/",
              params={"aweme_id": "7000000000000000000", "count": 20},
              headers=UA, timeout=40)
print("TikTok comment/list ->", r.status_code, r.text[:120])
r = httpx.get("https://www.tiktok.com/@quyenleo", headers=UA,
              follow_redirects=True, timeout=40)
print("TikTok hồ sơ ->", r.status_code, len(r.text), "byte",
      "| WAF" if "wafchallengeid" in r.text else "")
PY
```

```bash
# 5) YouTube — VOD còn tải được chat replay không
.venv/Scripts/python -m yt_dlp --skip-download --write-subs --sub-langs live_chat \
       -o "vod.%(ext)s" "https://www.youtube.com/watch?v=ZU_0QJzsR6w"
wc -l vod.live_chat.json && rm -f vod.live_chat.json   # XÓA NGAY: tệp chứa tên người bình luận

# 6) Cổng chất lượng sau khi thêm adapter Shopee
.venv/Scripts/python -m pytest tests/test_ingest_shopee.py -q     # 26 passed lúc thêm adapter; 57 passed tại commit abbbeb1 (17/09/2026)
.venv/Scripts/python -m pytest -m "not slow" -q                   # 689 passed
.venv/Scripts/python -m ruff check src tests scripts              # All checks passed!
```

---

## 10. Ba điều PHẢI nói thẳng, không được che

1. **Không nền tảng nào cho phép đọc buổi live của người lạ mà không xin phép.**
   Đó là *thiết kế*, không phải trở ngại kỹ thuật, và nó đúng. Mọi tài liệu bán
   "API TikTok/Facebook comment" trôi nổi đều là scraping có rủi ro pháp lý.
2. **Bình luận không phải là chuyển đổi.** YouTube cho bình luận nhưng **không**
   cho đơn hàng. Đã đo trên 24 buổi live thật: precision của radar ý định dao
   động **1,3% → 67,9%** giữa các buổi — nó đi theo *tỷ lệ nền của ý định mua
   trong buổi đó*, không phải theo model. Nói "bình luận là biến kết quả" mà
   không nói khoảng dao động này là không trung thực. Chỉ **Shopee** (và có thể
   TikTok Shop) cho biến kết quả thương mại thật.
3. **Phiên replay là QUAN SÁT.** Mọi buổi nạp qua `/replays/youtube` đều
   `analysis_only=true`: buổi phát gốc **không có lịch gán ngẫu nhiên**, nên
   không có gì để bốc thăm và **không sinh được một con số nhân quả nào**. Thí
   nghiệm switchback thật chỉ chạy được trên phiên **do chính nhóm điều khiển**
   — tức trên Page Facebook của nhóm, hoặc shop Shopee của nhóm.

---

*Tài liệu liên quan:*
[`huong-dan-facebook-token.md`](huong-dan-facebook-token.md) ·
[`benchmarks/tiktok-collector-2026-09.md`](benchmarks/tiktok-collector-2026-09.md) ·
[`research/2026-09-09-youtube-ytdlp-live.md`](research/2026-09-09-youtube-ytdlp-live.md) ·
[`benchmarks/live-fire-da-nguon.md`](benchmarks/live-fire-da-nguon.md) ·
[`benchmarks/nhat-ky-test.md`](benchmarks/nhat-ky-test.md)
