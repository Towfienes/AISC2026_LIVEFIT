# Nghiên cứu tích hợp nền tảng livestream và đánh giá SerpAPI (17/09/2026)

> **Nguồn gốc tài liệu (khai thật):** do một tác tử nghiên cứu Claude soạn ngày 17/09/2026 trong phiên kiểm toán toàn diện, từ ~31 lượt tra web có URL và tài liệu API gốc tải về. Các tệp bằng chứng thô được nhắc là `scratchpad/...` (JSON tài liệu Shopee, bản lưu trang trợ giúp YouTube, tài liệu TikTok Shop) **chỉ nằm trên máy của phiên làm việc, không có trong kho** — mọi khẳng định có URL nguồn để kiểm lại. Những điểm ghi "chưa xác minh" phải được kiểm bằng cuộc gọi thật trước khi đưa vào hồ sơ.

*Người soạn: nhà nghiên cứu tích hợp nền tảng. Ngày truy cập mọi nguồn: **17/09/2026** trừ khi ghi khác.
Bổ sung cho `docs/nen-tang-ho-tro.md` (đo 11/09) — không lặp lại các phép đo đã có ở đó.*

Quy ước mức độ: **CT** = Chính thức (API công khai của nền tảng) · **NB** = Người-bán-tự-đọc
(dashboard/xuất file thủ công của chính chủ tài khoản) · **3P$** = Bên-thứ-ba-trả-phí / không chính thức ·
**KO** = Không có.

> Trạng thái: **hoàn tất 17/09/2026**. Mục 1 = bằng chứng chi tiết; A–D = kết luận. ~31 lượt tra web + tài liệu đã tải sẵn trong scratchpad.

---

## 1. Bằng chứng theo nền tảng (ghi dần)

### 1.1 Shopee Live — người bán Việt Nam

**Kết luận: VN CÓ trong phạm vi Livestream API chính thức — nhưng API là loại "User" (ký bằng `user_id`,
không phải `shop_id`). Adapter hiện tại của repo đang ký sai.**

Bằng chứng (JSON tài liệu API tải từ open.shopee.com, lưu ở `scratchpad/shopee/api_*.json`):

| Endpoint | `api_type` | Mô tả nguyên văn (trường `define`) | Nguồn |
|---|---|---|---|
| `v2.livestream.get_latest_comment_list` | **User** | "Get live stream room comments in the last 10 seconds, including user id, user name, comment id, comment content, and comment time. **(For TW, ID, TH, PH, MY, SG, VN)**" | https://open.shopee.com/documents/v2/v2.livestream.get_latest_comment_list?module=125&type=1 |
| `v2.livestream.get_session_metric` | User | "Get real-time indicator data of the live stream room, including the number of likes, comments, shares, views, etc. (For TW, ID, TH, PH, MY, SG, VN)" | …/v2.livestream.get_session_metric?module=125&type=1 |
| `v2.livestream.get_session_item_metric` | User | "Get real-time indicator data of live stream products, including product clicks, add-to-cart, etc. (For … VN)" | …/v2.livestream.get_session_item_metric?module=125&type=1 |
| `v2.livestream.update_show_item` | User | "Set the showing item. (For … VN)" — tham số `session_id`, `item_id`, `shop_id` | …/v2.livestream.update_show_item?module=125&type=1 |
| `v2.livestream.create_session` / `post_comment` / `get_session_detail` | User | cùng hậu tố (For TW, ID, TH, PH, MY, SG, VN) | module=125 |

- `perm_mtime` của các endpoint này = `1752231753…1752231792` → **11/07/2025**: đây là lần cập nhật quyền gần
  nhất, khớp với việc mở rộng từ 3 thị trường lên 7.
- **Mâu thuẫn nguồn:** README của SDK TypeScript cộng đồng (`scratchpad/sdk_livestream.md`) ghi
  *"LiveStream APIs are only available for TW (Taiwan), ID (Indonesia), and TH (Thailand) regions"*. SDK
  bên thứ ba, viết trước 07/2025 → **tin tài liệu gốc của Shopee**, nhưng vẫn phải có lỗi
  `"The API is not supported for current region"` trong danh sách lỗi của endpoint → **chỉ kiểm chứng dứt
  điểm bằng một cuộc gọi thật với tài khoản VN**.
- **Phát hiện quan trọng cho mã:** `common_params` của các endpoint livestream gồm `partner_id, timestamp,
  access_token, user_id, sign` và mô tả `sign` = *"partner_id, api path, timestamp, access_token, **user_id**
  and partner_key via HMAC-SHA256"*. `v2.public.get_access_token` trả `user_id_list` bên cạnh
  `shop_id_list`; `refresh_access_token` nhận **hoặc** `shop_id` **hoặc** `user_id` ("must be refreshed
  separately"); `refresh_token` sống 30 ngày, dùng một lần. Nguồn:
  https://open.shopee.com/documents/v2/v2.public.get_access_token?module=104&type=1 ,
  https://open.shopee.com/documents/v2/v2.public.refresh_access_token?module=104&type=1
  → `src/livelift/ingest/shopee.py` hiện ký `partner_id+path+timestamp+access_token+shop_id` (dòng 163–169)
  và gửi `shop_id` → **gần như chắc chắn sẽ nhận `error_sign`/`error_auth` khi chạy thật**.
- Cửa sổ bình luận 10 giây, không có con trỏ `since` (đã biết từ 11/09) — giữ nguyên ràng buộc poll ≤ 8 s.
- `update_show_item` = **ghim sản phẩm qua API chính thức** (Shopee gọi là "showing item") → Shopee là nền
  tảng duy nhất vừa có đọc bình luận vừa có điều khiển can thiệp qua API.
- **Đường thay thế nếu tài khoản VN bị từ chối vùng:** (a) Seller Centre → Kênh Marketing → Shopee Live →
  dữ liệu phiên (xem/xuất thủ công, mức NB); (b) Shopee Affiliate (link tiếp thị liên kết + báo cáo chuyển
  đổi) cho đo click/đơn theo link — xem §1.8.

### 1.2 TikTok Shop Open Platform (partner.tiktokshop.com)

**Kết luận: CÓ API chính thức cho số liệu phiên LIVE của shop — gồm chuỗi theo PHÚT (GMV, đơn, click sản
phẩm, số bình luận, người xem) — áp dụng mọi thị trường kể cả VN. KHÔNG có API đọc NỘI DUNG bình luận,
KHÔNG có API ghim sản phẩm trong live, KHÔNG có webhook "live bắt đầu".**

Bằng chứng (tài liệu tải từ cây docv2, lưu `scratchpad/ttsdocs/*.md`, `tts_tree_list.txt`):

| Endpoint | Trả về | Ghi chú nguyên văn | Nguồn |
|---|---|---|---|
| `GET /analytics/202510/shop_lives/{live_id}/performance_per_minutes` | `intervals[]` theo phút: `sales.gmv`, `items_sold`, `sku_orders`, `main_orders`, `traffic.viewers`, `views`, `product_clicks`, `product_impressions`, `interactions.comments`, `likes`, `shares`, `new_followers` | "Returns minute-level performance for a LIVE session **after the session is finished**. This API only returns data for live streams hosted by the **shop official account or marketing account**." | https://partner.tiktokshop.com/docv2/page/get-shop-live-minute-performance-202510 (cập nhật 14/07/2026) |
| `GET /analytics/202509/shop_lives/performance` | danh sách phiên + GMV, sku_orders, items_sold, customers | "Sellers can only query room ID data for their own official creator accounts." | https://partner.tiktokshop.com/docv2/page/get-shop-live-performance-list-202509 |
| `GET /analytics/202509/shop_lives/overview_performance` | tổng hợp; tham số `today=true` | "The response will contain **real-time metrics of today** (local time)" | https://partner.tiktokshop.com/docv2/page/get-shop-live-performance-overview-202509 (10/09/2026) |
| `GET /analytics/202512/shop/{live_id}/products_performance` | GMV/đơn theo từng sản phẩm trong phiên | official account hoặc marketing accounts | https://partner.tiktokshop.com/docv2/page/get-shop-live-products-performance-list-202512 |
| `GET /analytics/202502/live_rooms/{live_room_id}/core_stats` | `current_visitor_count`, `peak_concurrent_user_count`, `created_order_count`, `paid_order_count`, `product_reach_count`, `accumulated_comment_count`, `local_gmv` | lỗi `66009315 No permission for the action` | https://partner.tiktokshop.com/docv2/page/get-live-room-core-stats-202502 (20/07/2026) |
| `GET /analytics/202502/live_rooms/{id}/interactive_trend_performances`, `…/gmv_trend_performances`, `…/view_trend_performances` | chuỗi `data_points[{value,timestamp}]` cho WATCH_PV/COMMENT_PV/SHARE_PV, TREND_GMV/TREND_CREATED_ORDER, TREND_ONLINE_VIEWER | có `current_visitor_count` → có khả năng dùng trong lúc phát (chưa kiểm chứng) | …/get-live-room-interactive-trends-202502 · …/get-live-room-gmv-trend-202502 · …/get-live-room-view-trends-202502 |

- Phạm vi thị trường: changelog "New APIs for TikTok LIVE" — *"Impacted market(s): All markets - local and
  cross-border"* (https://partner.tiktokshop.com/docv2/page/68af6771eb3a300486d0e157, 27/08/2025); changelog
  "Analytics APIs now available globally" — *"Endpoints that were previously exclusive to the US, UK, and SEA
  can now be used … regardless of market"* (https://partner.tiktokshop.com/docv2/page/68d6ce2d8e2c770495cced8c).
- Đơn hàng: `GET Order Details` có `auto_combine_order_id` "to identify orders assigned from the same customer
  during a LIVE session" (https://partner.tiktokshop.com/docv2/page/67c8ed2e2b63a404b7ad64ce, "all markets") —
  nhưng changelog **không** nói có trường `live_id` gắn đơn với phiên (chưa đọc trang Get Order Detail đầy đủ — cần kiểm tra trước khi dựa vào).
- Webhook: danh sách topic chỉ gồm đơn/gói/sản phẩm/hoàn trả/tin nhắn CSKH/ủy quyền — **không có topic live**
  (https://partner.tiktokshop.com/docv2/page/64f1997e93f5dc028e357341).
- Hạn mức: "dynamic QPS allocation … does not expose a single fixed QPS"; gợi ý khởi điểm cho analytics nặng
  **0,2–1 request/giây**; lỗi `429` / `36009002` (https://partner.tiktokshop.com/docv2/page/64f1991d64ed2e0295f3d2c0).
- Đăng ký: Partner Center non-US `partner.tiktokshop.com`; đối tác "local" chọn đúng thị trường của mình;
  loại "Seller inhouse developer / TikTok Shop Seller" liên kết shop đã kích hoạt; app private chỉ gắn **1 shop
  của chính mình** (https://partner.tiktokshop.com/docv2/page/6789f73f18828103147a8ca1 ,
  https://partner.tiktokshop.com/docv2/page/686394877cac2a04980aa7a6).
- Partner Center có "LIVE Dashboard" cho TSP/CAP xem live đang phát, **đọc bình luận và sản phẩm đang ghim trên
  giao diện** — nhưng đây là UI, không phải API (https://partner.tiktokshop.com/docv2/page/671754d18559ca030797dea5).

**Ý nghĩa cho switchback:** biến kết quả (GMV/đơn/click theo phút) **có chính thức** → khối switchback
10–15 phút đo được **hậu kiểm** sau phiên. Biến can thiệp (ghim sản phẩm) phải do người dẫn làm thủ công trên
app/LIVE Manager theo lịch LiveLift phát; bình luận realtime **không có đường chính thức**.

### 1.3 YouTube

**Kết luận: bình luận + quà (giftEvent/Super Chat) + người xem đồng thời + phát hiện live = CHÍNH THỨC,
dùng API key được (không cần OAuth) cho kênh công khai. Ghim tin nhắn / ghim sản phẩm qua API = KHÔNG CÓ.
Đơn hàng = KHÔNG CÓ.**

| Câu hỏi | Trả lời | Nguồn (truy cập 17/09/2026) |
|---|---|---|
| Giá `liveChatMessages.list` | Bảng Quota Calculator hiện hành ghi **1 đơn vị** (trang "Last updated 2026-09-15"). Nhiều tích hợp cũ (vd. SAMMI) vẫn ghi **5 đơn vị/lần** → **lập kế hoạch theo 5, đo thật trên Cloud Console**. | https://developers.google.com/youtube/v3/determine_quota_cost · https://sammi.solutions/docs/integrations/youtube |
| Quota mặc định | 10.000 đv/ngày cho mọi method "thường"; **từ 01/06/2026 `search.list` và `videos.insert` có bucket riêng: 100 lượt/ngày, 1 đv/lượt**; reset nửa đêm giờ Thái Bình Dương (14:00–15:00 giờ VN) | determine_quota_cost · https://developers.google.com/youtube/v3/revision_history (mục June 1, 2026) |
| 90 phút live, poll | Poll 5 s = 1.080 lượt → **1.080 đv (nếu 1 đv)** hoặc **5.400 đv (nếu 5 đv)**. Nên tôn trọng `pollingIntervalMillis` do server trả. | tính từ hai dòng trên |
| `liveChatMessages.streamList` (server-streaming, gRPC `youtube.googleapis.com:443` hoặc HTTP) | Tài liệu khuyến nghị dùng thay cho poll: *"This is the most efficient way to consume live chat messages, as it pushes new messages…"*; ghi chú trên trang `list`: *"…helps to avoid exceeding your quota"*. **Nhận API key** (`x-goog-api-key`) hoặc OAuth. `maxResults` 200–2000. Mất kết nối thì nối lại bằng `pageToken`. **Bảng quota KHÔNG liệt kê `streamList`** → giá mỗi kết nối chưa công bố; phải đo. Lỗi `LIVE_CHAT_ENDED` → không đọc được chat sau khi kết thúc. | https://developers.google.com/youtube/v3/live/docs/liveChatMessages/streamList · https://developers.google.com/youtube/v3/live/streaming-live-chat · https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list |
| Quyền cho `list`/`streamList` | Trang tài liệu **không có mục Authorization** (khác với `liveBroadcasts.list`, `liveChatMessages.insert`, `transition`) → API key đủ cho chat công khai. | 3 trang trên |
| `liveBroadcasts.list` | **Bắt buộc OAuth** (scope `youtube.readonly`/`youtube`/`youtube.force-ssl`); `mine=true` chỉ trả broadcast của người ủy quyền → chỉ dùng cho kênh **của nhóm**. | https://developers.google.com/youtube/v3/live/docs/liveBroadcasts/list |
| Phát hiện kênh đang live rẻ nhất | (1) RSS `https://www.youtube.com/feeds/videos.xml?channel_id=UC…` (0 đv) hoặc PubSubHubbub push (0 đv — *"receive notifications when a channel uploads a video…"*) để lấy videoId mới → (2) `videos.list?part=liveStreamingDetails,snippet&id=…` (**1 đv**, tối đa 50 id/lượt) đọc `snippet.liveBroadcastContent`, `liveStreamingDetails.actualStartTime`, **`concurrentViewers`**, **`activeLiveChatId`**. `search.list?eventType=live` giờ chỉ 1 đv nhưng **trần 100 lượt/ngày** → chỉ dùng để khám phá, không dùng để canh. | https://developers.google.com/youtube/v3/guides/push_notifications · https://developers.google.com/youtube/v3/docs/videos · https://developers.google.com/youtube/v3/docs/search/list |
| Quà/tiền | `superChatEvent`, `superStickerEvent`, `newSponsorEvent`, `membershipGiftingEvent`; **mới 26/03/2026: `giftEvent` + `giftEventDetails.jewelsAmount`** (người xem đổi Jewels lấy quà; cùng ID có thể lặp để cập nhật combo). | https://developers.google.com/youtube/v3/live/revision_history · https://developers.google.com/youtube/v3/live/docs/liveChatMessages |
| Ghim tin nhắn qua API | **Không có.** Các method của `liveChatMessages`: `list`, `streamList`, `insert` (chỉ `textMessageEvent` hoặc `pollEvent`), `delete`, `transition` (chỉ đóng poll: *"You can only transition to closed"*). Không có method/trường "pin". Ghim chỉ làm trong YouTube Studio/app. | https://developers.google.com/youtube/v3/live/docs/liveChatMessages/insert · …/transition |
| Can thiệp thay thế qua API | Chủ kênh (OAuth `youtube.force-ssl`) có thể **gửi tin nhắn** (50 đv) hoặc **tạo poll** (50 đv) — dùng làm "CTA có lịch" cho switchback. Ghim sản phẩm YouTube Shopping chỉ trong Studio; YouTube Shopping Affiliate có ở **Việt Nam** (cùng US, KR, ID, IN, TH, MY, PH, SG, BR, TW, JP). | yt_lcm_insert · YouTube Help — trang điều kiện YouTube Shopping (support.google.com/youtube, bản lưu `pages/yt_help_shopping_eligibility.txt`, 17/09/2026) |

### 1.4 Facebook (Graph API v26.0)

**Kết luận: Page của mình — bình luận (poll), người xem (`live_views`), phát hiện live bắt đầu (webhook
`live_videos`) đều CHÍNH THỨC. Luồng SSE `streaming-graph.facebook.com/{id}/live_comments` KHÔNG còn được
tài liệu hóa → đừng xây phụ thuộc vào nó. Không có quà/đơn hàng/ghim sản phẩm qua API.**

| Câu hỏi | Trả lời | Nguồn (17/09/2026) |
|---|---|---|
| Phiên bản hiện hành | Trang tham chiếu hiển thị **v26.0** (repo đang gọi v25.0 — vẫn chạy nhưng nên nâng) | https://developers.facebook.com/docs/graph-api/reference/live-video/comments/ |
| Đọc bình luận live | `GET /{live-video-id}/comments` với `live_filter=no_filter` (mặc định `filter_low_quality` — **lọc mất bình luận "chất lượng thấp"**, nguy hiểm cho biến kết quả), `order=chronological|reverse_chronological`, `since=<datetime>`, `filter=stream|toplevel`; `summary.total_count`. *"This endpoint is supported for New Page Experience."* | cùng trang |
| SSE `live_comments` | URL tài liệu cũ `…/server-sent-events/endpoints/live-comments/` nay **chuyển về trang tổng quan Live Video API**, không còn mô tả endpoint, tham số `comment_rate`. → xem là **không được bảo đảm**; nếu thử thì chỉ để so sánh độ trễ, fallback bắt buộc về poll `/comments?since=`. | https://developers.facebook.com/docs/graph-api/server-sent-events/endpoints/live-comments/ |
| Webhook phát hiện live | Page Webhooks có field **`live_videos`**: *"Describes changes to a page's live video status."* — payload `id`, `status` (enum). Đăng ký qua `POST /{page-id}/subscribed_apps?subscribed_fields=live_videos` (cần Page token có `pages_manage_metadata`). | https://developers.facebook.com/docs/graph-api/webhooks/reference/page/ |
| Người xem | Trường `live_views` trên node LiveVideo (repo đã dùng `?fields=live_views`; phép thử 11/09 xác nhận là *trường*, không phải edge). | `docs/nen-tang-ho-tro.md` §3.1 · https://developers.facebook.com/docs/graph-api/reference/live-video/ |
| Quyền | Live Video API: Page cần `pages_manage_posts` + `pages_read_engagement` (để tạo/quản lý live); đọc bình luận người xem cần thêm `pages_read_user_content` (đã đo 11/09). App ở Development Mode đủ cho Page do chính admin app quản lý. | https://developers.facebook.com/docs/live-video-api/ (overview) |
| Điều kiện phát live | *"The Facebook account must be at least 60 days old"* và *"The Facebook Page or professional mode profile must have at least 100 followers"* (từ 10/06/2024) | cùng trang overview |

### 1.5 SerpAPI — đã tra (chi tiết kết luận ở mục B)

- Danh mục engine trên trang chủ (17/09/2026, https://serpapi.com/): nhóm Google (Search, Shopping, Shopping Light,
  **Immersive Product**, Trends, Trends Autocomplete, **Trends Trending Now**, Maps, Maps Reviews, Lens, Videos,
  **Short Videos**, News, Autocomplete, Ads Transparency…), **YouTube Search / YouTube Channel / YouTube Video /
  YouTube Video Transcript**, Amazon/eBay/Walmart/Home Depot (Search/Product), **Facebook Profile API, Instagram
  Profile API**, Bing/Yahoo/Yandex/Baidu/Naver/DuckDuckGo, App Store/Play Store… **Không có engine TikTok, Shopee,
  Lazada, Tiki; không có engine chat/live nào.**
- YouTube Search API: tham số `search_query`, `sp` (*"can be used for pagination"* và *"to filter the search results"*),
  `gl`, `hl`. **Tài liệu không nêu bộ lọc live**; ví dụ chỉ có upload date / 4K; ví dụ phản hồi không có trường
  người xem live (https://serpapi.com/youtube-search-api).
- YouTube Video API: tiêu đề, mô tả, `views`, `likes`, chapters, video liên quan, **token phân trang bình luận VOD**;
  **không** có `is_live`, người xem đồng thời, live chat (https://serpapi.com/youtube-video-api).
- Giá (https://serpapi.com/pricing): Free **0 $/250 lượt/tháng (50/giờ)** · Starter **25 $/1.000** · Developer
  **75 $/5.000** · Production **150 $/15.000** · Big Data **275 $/30.000** · Searcher 725 $/100.000 · Volume
  1.475 $/250.000 … *"Only successful searches are counted… Cached, errored, and failed searches are not."*
- "U.S. Legal Shield": *"covers the scraping and parsing of search engine data, as long as your use of the data or
  service is not illegal"* — áp dụng tại Mỹ, **không phải giấy phép của YouTube/Google** cho người dùng cuối.

### 1.6 Công cụ đọc chat TikTok LIVE trên thực tế (TikFinity / Streamer.bot / Apify / Euler Stream)

**Kết luận: mọi công cụ phổ biến đều đi cùng MỘT đường — WebSocket "webcast" không chính thức của TikTok, URL
được ký bởi sign server của Euler Stream. Không có API chính thức nào cho chat TikTok LIVE.**

| Công cụ | Cách đọc chat | Nguồn (17/09/2026) |
|---|---|---|
| **TikTok-Live-Connector** (Node.js, Zerody) | *"This is not a production-ready API. It is a reverse engineering project."* Ký URL WebSocket qua **Euler Stream sign server** (`@eulerstream/euler-api-sdk`, `signApiKey`); hạn mức cộng đồng miễn phí, có key thì cao hơn; lỗi `SignatureRateLimitError`, `UserOfflineError`, captcha khi tải nặng; muốn gửi chat phải đưa cookie `sessionid` của tài khoản (rủi ro lộ phiên đăng nhập). | https://github.com/zerodytrash/TikTok-Live-Connector |
| **TikTokLive** (Python, isaackogan) | cùng giao thức; tài liệu nay đặt dưới tên miền Euler Stream | https://github.com/isaackogan/TikTokLive · https://tiktoklive.eulerstream.com/ |
| **TikFinity** (Zerody) | dùng TikTok-Live-Connector + Socket.IO; mở WebSocket cục bộ cho widget; tích hợp Streamer.bot | https://tikfinity.zerody.one/ · https://tikfinity.zerody.one/streamerbot-integration |
| **Streamer.bot** | **không** có tích hợp TikTok gốc — FAQ: sẽ cân nhắc *"if/when they release a usable public API"*; dùng TikFinity làm cầu nối | https://docs.streamer.bot/faq/platform-support |
| **Apify** actor "TikTok Live Scraper" (khadinakbar) | *"the public TikTok webcast WebSocket (no cookies) via `tiktok-live-connector`"*; **0,0002 $/sự kiện chat/quà**, 0,005 $/kết quả is-live/room; nghe tối đa **1.800 s/lần chạy**; **12 người dùng, 4 MAU, chưa có đánh giá** | https://apify.com/khadinakbar/tiktok-live-scraper |
| **Restream** | chính thức *phát* lên TikTok; nhưng TikTok yêu cầu **≥ 50% nội dung gaming** với luồng qua phần mềm bên thứ ba từ 07/07/2025; bài viết không nói Restream Chat đọc được chat TikTok | https://support.restream.io/en/articles/6721574-stream-to-tiktok (cập nhật 09/07/2026) |

**Euler Stream — có gói trả phí** (https://www.eulerstream.com/pricing): **Community 0 $** — 2.500 request/ngày,
25 Cloud WebSockets · **Business 50 $/tháng** — 10.000 request/ngày, 100 Cloud WebSockets · **Enterprise** —
liên hệ, 250.000+ request/ngày, 1.500+ Cloud WebSockets. Có route `/webcast/websockets` (WebSocket được host sẵn).
Trang giá **không** nêu SLA hay tuyên bố về ToS TikTok.

**Độ tin cậy & rủi ro:** (1) giao thức có thể đổi bất kỳ lúc nào (chính README thừa nhận); (2) phụ thuộc một
nhà cung cấp ký duy nhất; (3) trái Điều khoản TikTok (truy cập tự động không được phép) → **không dùng cho dữ
liệu vào bài báo**; (4) ghi chú cho repo: lỗi *HTTP 400, 10/10 lần* đo ngày 09/09 **có thể** do gọi thiếu
`signApiKey`/phiên bản thư viện cũ — nếu muốn thử lại chỉ nên thử trên live **của chính nhóm**, coi là quan sát kỹ thuật.

### 1.7 Dịch vụ scraping trả phí để so sánh với SerpAPI

| Dịch vụ | Giá (17/09/2026) | Có gì cho live | Tuyên bố pháp lý | Nguồn |
|---|---|---|---|---|
| **ScrapeCreators** | Free 100 credit (+ tới 7.000 credit thưởng) · **47 $ = 25.000 credit (1,88 $/1k)** · 497 $ = 500.000 (0,99 $/1k); *"No subscriptions. No expiring credits."* | TikTok `GET /v1/tiktok/user/live` và `GET /v1/tiktok/live` (trạng thái/thông tin phòng live), bình luận **video** TikTok/IG/FB/YT; **không thấy** endpoint chat live | chỉ nói lấy *"publicly available data"* | https://scrapecreators.com/ |
| **EnsembleData** | Free 50 unit/ngày · Wood **100 $/tháng (1.500 unit/ngày)** · Bronze 200 $ (5.000) · Silver 400 $ · Gold 800 $ · Platinum 1.400 $; request đơn giản 1–2 unit | bảng endpoint **không liệt kê** TikTok LIVE (info/comment/gift) | *"…compliant to GDPR and the social media ToS"* (tự tuyên bố, không phải giấy phép của nền tảng) | https://ensembledata.com/pricing |
| **Apify** (actor cộng đồng) | xem §1.6: 0,0002 $/sự kiện chat, tối đa 30 phút/lần chạy; actor bình luận video TikTok 0,23–1,00 $/1k | chat + quà TikTok LIVE qua webcast không chính thức | trách nhiệm tuân thủ thuộc người chạy actor | https://apify.com/khadinakbar/tiktok-live-scraper · https://apify.com/scraptivo/tiktok-comment-scraper |
| **Euler Stream** | 0 $ / **50 $/tháng** / Enterprise | sign server + Cloud WebSocket cho TikTok LIVE | trang giá không nêu | https://www.eulerstream.com/pricing |

### 1.8 Đường thay thế đo click/đơn trên Shopee: Shopee Affiliate Open API (VN)

- Cổng: https://affiliate.shopee.vn/open_api (danh mục: https://affiliate.shopee.vn/open_api/list), explorer
  https://open-api.affiliate.shopee.vn/explorer/v2 — GraphQL, ký HMAC-SHA256, App ID + API Key lấy trong trang
  Affiliate. Có `generateShortLink` **kèm `subIds`** và `conversionReport` (báo cáo chuyển đổi/hoa hồng).
  (Mô tả tổng hợp từ kết quả tìm kiếm 17/09/2026; chưa đọc trang tài liệu đầy đủ vì cần đăng nhập.)
- Ý nghĩa: **mỗi khối switchback = một `subId`** → click/đơn quy về khối **qua kênh chính thức**, không cần
  Livestream API. Nhược điểm: chỉ đo đơn đi qua link affiliate, trễ báo cáo, cần tài khoản Affiliate được duyệt.
- Seller Centre: Học viện Shopee có bài "Theo dõi hiệu suất Shopee Live"
  (https://banhang.shopee.vn/edu/article/9602/hieu-suat-livestream-tai-shopee-live) — trang render bằng JS,
  **chưa trích được** danh sách chỉ số / có nút xuất file hay không → phải mở bằng tài khoản shop để xác minh.
- Đăng ký Open Platform cho người bán VN: https://banhang.shopee.vn/edu/article/8450 ("Hướng Dẫn Đăng Ký Tài
  Khoản Open API").

### 1.9 Bổ sung: Instagram, Lazada, điều kiện được phát live

- **Instagram:** webhook field **`live_comments`** — *"Notifications for Comments on Live media are only sent during
  the live broadcast."* Quyền (Instagram Login): `instagram_business_basic` + `instagram_business_manage_comments`;
  (Facebook Login): `instagram_basic`, `instagram_manage_comments`, `pages_manage_metadata`, `pages_read_engagement`,
  `pages_show_list`. **"Advanced Access is mandatory"**; tài khoản chuyên nghiệp phải công khai
  (https://developers.facebook.com/docs/instagram-platform/webhooks). → khác Facebook Page: **không làm được ở Dev
  Mode**, phải App Review.
- **Lazada:** kết quả tìm kiếm cho thấy danh mục Open Platform có nhóm **"LazLive API"** (https://open.lazada.com/apps/doc/api),
  nhưng trang tài liệu render JS và cổng API kiểm `app_key` trước khi định tuyến (đo 11/09) → **chưa xác minh nội
  dung** (bình luận? chỉ số?). Seller Center app có mục Livestream/"Schedule Live" (https://blog.splitdragon.com/lazlive/).
- **TikTok Shop – "ghim":** chỉ có `POST /affiliate_creator/202409/showcases/products/top` — *"move products to the
  top in a creator's showcase"* (tủ trưng bày hồ sơ creator), **không phải** sản phẩm ghim trong LIVE
  (https://partner.tiktokshop.com/docv2/page/top-showcase-products-202409).
- **YouTube Super Chat/Super Stickers** có ở **Việt Nam** (danh sách quốc gia trên trang điều kiện Super Chat,
  bản lưu `pages/yt_help_livechat_mod.txt`) — nhưng cần kênh đủ điều kiện fan funding (YPP) → nhóm sinh viên
  gần như không có tín hiệu quà trên kênh test.

**Điều kiện để TỰ phát live thử (quan trọng cho kịch bản kiểm thử):**

| Nền tảng | Điều kiện | Nguồn |
|---|---|---|
| YouTube (máy tính / OBS / webcam) | *"no live streaming restrictions in the past 90 days and you need to verify your channel"* (xác minh = SĐT); lần đầu bật live có thể chờ tới 24 giờ | https://support.google.com/youtube/answer/2474026 (bản lưu `pages/yt_help_live_eligibility.txt`) |
| YouTube (điện thoại) | *"At least 50 subscribers"*, không bị hạn chế 90 ngày, xác minh kênh, *"You may need to wait 24 hours before you can start your first live stream"*; người 13–17 tuổi mặc định unlisted | https://support.google.com/youtube/answer/9228390 (bản lưu `pages/yt_help_mobile_live.txt`) |
| Facebook Page / hồ sơ chuyên nghiệp | Từ 10/06/2024: tài khoản Facebook **≥ 60 ngày tuổi**, Page **≥ 100 người theo dõi** — áp dụng chắc chắn cho phát qua Live Video API / phần mềm bên thứ ba (OBS, StreamYard, Ecamm); với app điện thoại chưa xác minh | https://developers.facebook.com/docs/live-video-api/ · https://support.streamyard.com/hc/en-us/articles/21951924137492 · https://ecamm.com/blog/new-facebook-live-streaming-requirements-2024/ |
| TikTok LIVE thường | ≥ 18 tuổi; *1.000 follower (có thể khác theo khu vực)*; luồng qua phần mềm bên thứ ba cần ≥ 50% nội dung gaming (từ 07/07/2025) | https://support.tiktok.com/en/live-gifts-wallet/tiktok-live · https://support.tiktok.com/en/safety-hc/account-and-user-safety/age-requirements-for-tiktok-live · https://support.restream.io/en/articles/6721574-stream-to-tiktok |
| TikTok Shop VN (tài khoản chính thức của shop) | Nguồn thứ cấp VN: live bán hàng qua Seller Center **không cần 1.000 follower**; người bán cá nhân phải là công dân VN ≥ 18 tuổi — **chưa có nguồn chính thức, phải thử bằng shop thật** | https://ghtk.vn/blog/dieu-kien-tiktok-live/ · https://gochek.vn/blogs/news/dieu-kien-live-tiktok |
| Shopee Live (API) | `create_session` có tham số **`is_test`** ("Indicate whether the livestream session is for testing purpose only.") → có chế độ phiên thử chính thức | `scratchpad/shopee/api_create_session.json` · https://open.shopee.com/documents/v2/v2.livestream.create_session?module=125&type=1 |

---

## A. MA TRẬN nền tảng × tín hiệu (17/09/2026)

**CT** Chính thức · **NB** Người-bán-tự-đọc (dashboard/app) · **3P$** Bên-thứ-ba/không chính thức · **KO** Không có ·
**?** chưa xác minh. Mọi ô "CT" chỉ áp dụng cho **tài khoản/shop của chính mình hoặc đã ủy quyền**, trừ khi ghi khác.

| Nền tảng | Bình luận | Người xem | Quà / tim | Đơn hàng | Ghim qua API | Phát hiện live bắt đầu |
|---|---|---|---|---|---|---|
| **YouTube** | **CT** — `liveChatMessages.streamList` / `list`, **API key đủ, cả kênh người khác** (§1.3) | **CT** — `videos.list` `liveStreamingDetails.concurrentViewers` (1 đv) | **CT** — `superChatEvent`, `superStickerEvent`, `giftEvent` (Jewels, từ 26/03/2026), membership; lượt thích qua `statistics.likeCount` | **KO** (YouTube Shopping: chỉ **NB** trong Studio) | **KO** — chỉ `insert` tin nhắn/poll (OAuth, 50 đv) | **CT** — PubSubHubbub/RSS (0 đv) + `videos.list` (1 đv); `liveBroadcasts.list` (OAuth, kênh mình) |
| **Facebook** (Page mình) | **CT** — `GET /{live-video-id}/comments?live_filter=no_filter` (v26.0); SSE `live_comments`: **?** (không còn tài liệu) · Page người khác: CT sau App Review | **CT** — trường `live_views` | reactions: **CT** (edge của video); Stars: **?** | **KO** | **KO** (không thấy trong tài liệu) | **CT** — Page webhook `live_videos` |
| **TikTok** (LIVE thường) | **KO** chính thức · **3P$** — webcast WebSocket + Euler Stream (0–50 $/tháng), Apify 0,0002 $/sự kiện | **NB** (LIVE Center trong app) · **3P$** | **3P$** (sự kiện gift/like qua webcast) | KO | **KO** | **3P$** — ScrapeCreators `/v1/tiktok/user/live`, Apify is-live |
| **TikTok Shop** (tài khoản chính thức/marketing của shop) | **Nội dung: KO** · **Số đếm: CT** (`accumulated_comment_count`, `COMMENT_PV`, `comments`/phút) · xem nội dung: **NB** (LIVE Dashboard Partner Center) | **CT** — `core_stats.current_visitor_count`, `view_trend_performances`, `viewers`/phút | likes/shares theo phút: **CT**; quà: **KO** | **CT** — GMV, `sku_orders`, `main_orders`, `product_clicks` **theo phút, sau khi phiên kết thúc** (`performance_per_minutes`); `core_stats` created/paid orders | **KO** (chỉ "top showcase" hồ sơ creator — không phải ghim LIVE) | **KO** realtime (không có webhook live) · **CT gián tiếp**: `shop_lives/performance`, `overview_performance?today=true` |
| **Shopee Live** (VN, user/shop đã ủy quyền) | **CT** — `get_latest_comment_list` (cửa sổ 10 s; tài liệu ghi có VN, **cần gọi thật để chốt**) | **CT** — `get_session_metric.ccu`, `peak_ccu` | likes: **CT**; quà: **KO** | **CT** — `gmv`, `orders`, `atc` (cộng dồn), `get_session_item_metric` (click/ATC theo sản phẩm); đường phụ **CT**: Shopee Affiliate `conversionReport` theo `subId` | **CT** — `update_show_item` / `delete_show_item` | **CT (poll)** — `get_session_detail.status`; không webhook |
| **Lazada** (LazLive) | **?** (có nhóm "LazLive API" trong danh mục, chưa đọc được) | **?** / NB | **?** | NB (Seller Center) | **?** | **?** |
| **Instagram** (tài khoản chuyên nghiệp mình) | **CT nhưng bắt buộc Advanced Access (App Review)** — webhook `live_comments`, chỉ gửi trong lúc phát | **?** | **KO** | KO | KO | **CT** — edge `/{ig-user-id}/live_media` (tồn tại, đo 11/09) |

**Đọc ma trận trong 3 câu:** (1) Chỉ **Shopee** có đủ vòng khép kín *đọc bình luận + đo đơn + ghim sản phẩm* qua API
chính thức. (2) **TikTok Shop** có **biến kết quả tốt nhất** (GMV/đơn/click **theo phút**) nhưng chỉ hậu kiểm, không có
nội dung bình luận và không ghim được qua API. (3) **YouTube** là đường chính thức duy nhất đọc chat của **người khác**
— nhưng không có tín hiệu thương mại.

---

## B. SerpAPI — kết luận dứt khoát

**SerpAPI KHÔNG phải nguồn dữ liệu livestream và không được đưa vào đường ingest của LiveLift.** Nó là dịch vụ cào
*trang kết quả tìm kiếm* (Google, YouTube Search, Amazon…): không engine nào đọc live chat, người xem đồng thời theo
thời gian thực, quà hay đơn hàng, và **không có engine TikTok/Shopee/Lazada** (danh mục https://serpapi.com/,
17/09/2026). Với YouTube, SerpAPI còn **thua API chính thức**: `search.list?eventType=live` giờ chỉ 1 đơn vị trong
bucket riêng 100 lượt/ngày **miễn phí**, còn SerpAPI Free chỉ 250 lượt/**tháng**. Giá trị thật duy nhất là **Google
Trends** và **Google Shopping/Immersive Product** — hai thứ Google không có API công khai tương đương — để chọn *hàng
ghim* và *khung giờ phát*; gói **Free (250 lượt/tháng)** là đủ, **không nên trả 25–75 $/tháng**. "U.S. Legal Shield"
chỉ bảo vệ việc cào tại Mỹ, không phải giấy phép của Google/YouTube.

| Việc | SerpAPI làm được? | Ghi chú |
|---|:--:|---|
| Đọc bình luận live (YouTube/TikTok/FB/Shopee) | ❌ | không có engine chat; dùng `liveChatMessages.streamList` |
| Người xem đồng thời theo thời gian thực | ❌ | cùng lắm là ảnh chụp trong kết quả tìm kiếm (chưa xác minh trường này); dùng `videos.list` 1 đv |
| Quà / tim / đơn hàng | ❌ | — |
| Tìm video YouTube **đang live** theo từ khóa | ⚠️ được, nhưng **đắt hơn API chính thức** | `engine=youtube&search_query=…&sp=EgJAAQ%3D%3D` — tài liệu chỉ nói "copy `sp` từ URL YouTube" (https://serpapi.com/blog/youtube-sp-filters-paginating-sorting-and-filtering-with-the-youtube-api/); bộ lọc live **chưa thử** |
| Tìm phiên live **TikTok / Shopee** của đối thủ | ❌ | không có engine |
| Bình luận / transcript **VOD** YouTube | ✅ | YouTube Video API (token phân trang bình luận), YouTube Video Transcript — hữu ích để gán nhãn lời người dẫn trong replay |
| Xu hướng từ khóa theo vùng VN | ✅ | Google Trends / Trends Trending Now (`geo=VN`) — chọn sản phẩm & giờ phát |
| Giá thị trường sản phẩm để chọn hàng ghim | ✅ (độ phủ VN **chưa đo**) | Google Shopping / Shopping Light / Immersive Product — cần 1 lượt Free với `gl=vn` để xem có phủ Shopee/Lazada/Tiki không |
| Hồ sơ trang FB/IG đối thủ | ⚠️ chỉ metadata | Facebook Profile API, Instagram Profile API — không có bình luận live |

**So nhanh với các dịch vụ khác** (chi tiết §1.6–1.7):

| | Giá khởi điểm | Chat TikTok LIVE | Rủi ro ToS | Dùng cho LiveLift? |
|---|---|:--:|---|---|
| SerpAPI | 0 $ (250/tháng) · 25 $/1.000 lượt | ❌ | cào Google/YouTube; Legal Shield chỉ ở Mỹ | chỉ Trends + Shopping, gói Free |
| Apify (actor TikTok Live) | 0,0002 $/sự kiện, ≤ 30 phút/lần chạy | ✅ (webcast không chính thức) | **cao** — actor 12 người dùng, dựa trên tiktok-live-connector | ❌ không vào dữ liệu nghiên cứu |
| Euler Stream | 0 $ / 50 $/tháng | ✅ (sign server + Cloud WebSocket) | **cao** — dịch ngược, không nêu SLA | ❌ (chỉ quan sát kỹ thuật trên live của nhóm) |
| ScrapeCreators | 47 $ = 25.000 credit, không hết hạn | trạng thái live ✅, chat ❌ | trung bình–cao | ❌ |
| EnsembleData | 100 $/tháng (1.500 unit/ngày) | ❌ (không liệt kê) | tự tuyên bố tuân thủ | ❌ |

---

## C. Kịch bản kiểm thử 3 tầng cho đội sinh viên

**Nguyên tắc:** chỉ leo tầng khi tầng dưới đạt tiêu chí; mọi phiên có **file "sự thật nền"** (ground truth) viết
trước để so; chat thô xóa sau khi đếm (quy tắc hiện hành).

### Tầng 1 — Không phát live, không khán giả (0 rủi ro, làm ngay)

| Bước | Việc | Tiêu chí đạt |
|---|---|---|
| 1.1 | **Contract test** từ mẫu phản hồi trong tài liệu: Shopee (`shopee/api_*.json`), TikTok Shop (`ttsdocs/*.md` — response sample), YouTube (`liveChatMessage` resource, có `giftEvent`) | parser đọc đúng 100% trường; username/user_id bị bỏ |
| 1.2 | Kiểm **chữ ký Shopee loại User** bằng vector tự tính (`partner_id+path+timestamp+access_token+user_id`); gọi thật với `partner_id` giả để thấy lỗi dừng ở tầng xác thực (cách đo 11/09) | lỗi đúng tầng; token không lộ trong log |
| 1.3 | YouTube API key: `search.list?eventType=live&type=video&regionCode=VN&q=live bán hàng` (1 lượt/100) → `videos.list` ≤ 50 id (1 đv) → `streamList` 10 phút trên **một live công khai của người khác** (API chính thức, chỉ đếm, không lưu tên) | nhận bản tin liên tục; đo **quota thật** của `list` (1 hay 5 đv) và của `streamList` trên Cloud Console |
| 1.4 | Replay VOD (đường `/replays/youtube` sẵn có) — chỉ `analysis_only` | pipeline chạy hết, không sinh số nhân quả |

### Tầng 2 — Live THẬT của nhóm, không khán giả ngoài (rủi ro thấp)

Chuẩn bị: 1 máy phát (OBS) + 3 "khán giả kịch bản" dùng tài khoản riêng, gửi bình luận theo file lịch `(t, mã_tin)`
với mã duy nhất (vd. `T2-A-017`), nhịp tăng dần 0,2 → 1 → 3 bình luận/giây; một người ghim/đổi sản phẩm theo lịch
LiveLift và ghi tay thời điểm.

| Nền tảng | Cách phát an toàn | Điều kiện tài khoản | Đo gì |
|---|---|---|---|
| YouTube | Studio/OBS, **Unlisted**, 30 phút | kênh đã xác minh SĐT, chờ ≤ 24 h lần đầu; điện thoại cần ≥ 50 subscriber → **dùng OBS trên máy tính** | recall bình luận (≥ 98%), độ trễ p50/p90 (`streamList` mục tiêu p90 ≤ 5 s), quota/30 phút, nối lại bằng `pageToken` sau khi rút mạng 30 s, xử lý `LIVE_CHAT_ENDED` |
| Facebook | Page của nhóm qua Live Producer/OBS, tiêu đề "TEST", 15 phút | tài khoản ≥ 60 ngày, Page ≥ 100 follower (thiếu thì mượn Page CLB/Đoàn trường đủ điều kiện, có văn bản đồng ý) | webhook `live_videos` đến sau bao lâu; recall `/comments` với `live_filter=no_filter` so với mặc định; `live_views`; 5 phút sau khi kết thúc gọi lại `/comments` (chốt câu hỏi §3.5 tài liệu cũ) |
| Shopee | `create_session` với **`is_test=true`**, đẩy RTMP 20 phút | tài khoản Open Platform + ủy quyền **user** của người phát | có lỗi *"not supported for current region"* không (chốt VN); recall ở 3 bình luận/giây (phân trang `offset` trong cửa sổ 10 s); `update_show_item` hiện trên app sau bao nhiêu giây; ép hết hạn token để thử refresh (`refresh_token` dùng một lần) |
| TikTok Shop | Tài khoản chính thức của shop, live 15 phút, 2–3 sản phẩm | shop VN đã kích hoạt; app Seller in-house gắn 1 shop | `core_stats` có số trong lúc phát không; `performance_per_minutes` có dữ liệu sau bao lâu kể từ khi kết thúc; `comments`/phút có khớp số bình luận kịch bản không |

Tiêu chí qua tầng: recall ≥ 98% (Shopee ≥ 95% ở 3 bình luận/giây); không lộ token trong log; lệch giữa lịch
switchback và thời điểm ghim thực ≤ 5 s; quota YouTube dự phóng cho 90 phút ≤ 30% hạn mức ngày.

### Tầng 3 — Pilot với khán giả thật (rủi ro trung bình, cần đồng ý)

1. **Đối tác**: 1 shop (Shopee hoặc TikTok Shop) có **văn bản đồng ý** và tự ủy quyền token; phiên 60–90 phút; khối
   10–15 phút; lịch gán ngẫu nhiên sinh trước và niêm phong (hash) trước giờ phát.
2. **Hai nguồn sự thật song song**: quay màn hình app người xem + nhật ký tay thời điểm ghim; LiveLift *gợi ý*, người
   dẫn *thực hiện* (với Shopee có thể để `update_show_item` thực hiện từ phiên thứ 2).
3. **Điều kiện dừng/hạ cấp**: quota > 70%; token còn < 20 phút mà refresh lỗi; tỷ lệ lỗi API > 5% trong 5 phút →
   chuyển sang "chỉ ghi nhật ký tay", đánh dấu khối bị ảnh hưởng để loại khỏi phân tích.
4. **Sau phiên**: kéo `performance_per_minutes` (TikTok Shop) hoặc hiệu `get_session_metric` đầu/cuối khối (Shopee)
   + `conversionReport` theo `subId` (Shopee Affiliate); khai báo trong phương pháp: biến kết quả là sai phân bộ đếm
   cộng dồn (Shopee) hoặc chuỗi phút do nền tảng tính (TikTok Shop).
5. **Không** dùng công cụ webcast/scraper nào ở tầng này.

---

## D. 5 khuyến nghị kỹ thuật ưu tiên cho mã LiveLift

1. **Sửa `src/livelift/ingest/shopee.py` sang xác thực loại "User" — trước mọi việc khác.** Livestream API ký
   `partner_id + path + timestamp + access_token + user_id` và gửi `user_id` trong query (không phải `shop_id`); luồng
   OAuth lấy `user_id_list` từ `v2.public.get_access_token`; `v2.public.refresh_access_token` gọi **theo `user_id`** và
   lưu ngay `refresh_token` mới (dùng một lần, sống 30 ngày); refresh chủ động ở mốc ~3 h 30 (token sống 4 h). Thêm lớp
   lỗi riêng cho `"The API is not supported for current region"` và `"The session … is not ongoing"`. Bổ sung actuator
   `POST /api/v2/livestream/update_show_item` (`session_id`, `item_id`, `shop_id`) và poll `get_session_item_metric`
   (click/ATC theo sản phẩm) 60 s/lần. Các test hiện khẳng định chữ ký bằng `shop_id` → phải sửa theo tài liệu.
2. **YouTube: chuyển ingest sang `liveChatMessages.streamList` bằng API key**, fallback `list` tôn trọng
   `pollingIntervalMillis`; phát hiện live bằng PubSubHubbub/RSS + `videos.list?part=liveStreamingDetails&id=<≤50 id>`
   (1 đv) thay cho `search.list`; đọc `concurrentViewers` 60 s/lần (≈ 90 đv/phiên). Thêm bộ đếm quota trong tiến trình
   (giả định **5 đv/lượt `list`** cho tới khi bước 1.3 đo được) và hạ nhịp ở 70%. Parser nhận thêm `giftEvent`
   (`giftEventDetails.jewelsAmount`; ID lặp = cập nhật combo → giữ bản mới nhất). Không có API ghim: actuator YouTube =
   `liveChatMessages.insert` (OAuth `youtube.force-ssl`, 50 đv/lần, ≤ 1 lần/khối) hoặc checklist ghim tay. Sửa con số
   "≈ 5.400 đv" trong `docs/nen-tang-ho-tro.md` thành khoảng 1.080–5.400 đv kèm nguồn.
3. **Viết adapter TikTok Shop "hậu kiểm theo phút"** (biến kết quả tốt nhất cho nền tảng #1 VN): lấy `live_id` từ
   `GET /analytics/202509/shop_lives/performance?start_date_ge=…&end_date_lt=…`, rồi
   `GET /analytics/202510/shop_lives/{live_id}/performance_per_minutes?currency=LOCAL` (phân trang `page_token`) và
   `GET /analytics/202512/shop/{live_id}/products_performance`; trong lúc phát thử
   `GET /analytics/202502/live_rooms/{id}/core_stats` 60 s/lần. Bộ giới hạn 0,5 req/s theo (app, shop, endpoint), backoff
   khi HTTP 429 hoặc `code=36009002`; xử lý `66009315 No permission` (tài khoản không phải official/marketing). Gộp
   `intervals[]` vào khối switchback theo `start_time` (UTC). App loại *Seller in-house developer* gắn 1 shop.
4. **Facebook: nâng Graph lên v26.0 và khóa cấu hình đọc bình luận** —
   `GET /{live-video-id}/comments?live_filter=no_filter&order=chronological&since=<ts>&fields=id,message,created_time`,
   khử trùng lặp theo `id`; mặc định `filter_low_quality` sẽ **âm thầm làm mất dữ liệu biến kết quả**. Đăng ký webhook
   `live_videos` (`POST /{page-id}/subscribed_apps?subscribed_fields=live_videos`, Page token có `pages_manage_metadata`)
   để tự mở phiên khi trạng thái chuyển sang live; `live_views` 30–60 s/lần. SSE `live_comments` chỉ đặt sau feature
   flag. `scripts/kiem_tra_facebook.py` nên kiểm thêm điều kiện Page ≥ 100 follower trước ngày test.
5. **Tách tầng nguồn trong schema và dùng shortlink chính thức cho click.** Thêm trường `source_tier ∈ {official,
   seller_export, unofficial}` cho mọi sự kiện ingest; pipeline phân tích nhân quả **từ chối** `unofficial` (TikTok
   webcast, yt-dlp). Để đo click: ngoài redirect server của LiveLift, sinh link qua **Shopee Affiliate Open API
   `generateShortLink` với `subIds=[session_id, block_id]`** rồi đối soát `conversionReport` — click/đơn quy về khối qua
   kênh chính thức ngay cả khi Livestream API bị từ chối vùng. SerpAPI **không** vào ingest; nếu dùng thì chỉ một job
   ngoại tuyến Google Trends/Shopping (gói Free) để chọn sản phẩm ghim.

---

### Giới hạn của báo cáo này (nói thẳng)

- Shopee VN: tài liệu gốc ghi có VN nhưng **chưa có cuộc gọi thật**, và mâu thuẫn với SDK cộng đồng → chốt ở Tầng 2.
- Giá quota `liveChatMessages.list` (1 hay 5 đv) và `streamList` **chưa đo**; bảng chính thức hiện ghi 1.
- TikTok Shop `live_rooms/*` dùng được **trong lúc phát** và với **token shop VN** hay chỉ creator/đối tác: chưa kiểm
  chứng (tài liệu không nói rõ loại token).
- Lazada LazLive API, số người xem Instagram Live, Facebook Stars, endpoint SSE `live_comments`: chưa đọc được tài liệu.
- Điều kiện live TikTok Shop VN "0 follower" chỉ có nguồn thứ cấp.
- Shopee Affiliate Open API: mới dựa trên kết quả tìm kiếm, chưa đọc trang tài liệu (cần đăng nhập).
- SerpAPI: bộ lọc live `sp=EgJAAQ%3D%3D` và độ phủ Google Shopping `gl=vn` chưa thử (tốn 2 lượt gói Free).
