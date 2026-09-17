# YouTube: kiểm thử bằng API chính thức và công nghệ live mới (17/09/2026)

> **Nguồn gốc tài liệu (khai thật).** Tác tử Claude (vai tổng biên tập) soạn tài liệu này ngày 17/09/2026. Đầu vào là
> một đợt nghiên cứu nhiều tác tử: một tác tử viết báo cáo, một tác tử khác **kiểm chứng độc lập** 14 phát hiện
> (9 xác nhận, 5 đúng một phần, 0 sai). Người kiểm chứng mở lại các trang Google, tự tải lại Discovery Document
> (revision `20260914`) và gọi lại endpoint bằng **key giả** (không đọc dữ liệu người dùng, không tốn quota của ai).
> Sau đó một tác tử triển khai viết `scripts/kiem_tra_youtube.py`, fixture và test, và một tác tử phản biện kiểm lại
> phần đó. Báo cáo thô và bản tải trang nằm trong scratchpad của phiên làm việc, **không có trong kho**, nên mọi khẳng
> định dưới đây kèm URL để kiểm lại. Tổng biên tập chạy lại test ngày 17/09/2026 (mục 8).
>
> **Phạm vi:** chỉ API chính thức (quyết định của chủ dự án ngày 17/09/2026). Backend `INGEST_YOUTUBE_BACKEND=ytdlp`
> và phân tích VOD qua yt-dlp **vẫn giữ nguyên trong kho** theo quyết định đó; tài liệu này không đề xuất phát triển
> thêm chúng.
>
> **Ngày truy cập:** mọi URL truy cập ngày **17/09/2026**, trừ khi ghi khác. "Cập nhật" là dòng *Last updated* của
> trang Google.
>
> **Mức chắc chắn:** **[Đã kiểm]** · **[Một phần]** (phần sai/thiếu ghi bên cạnh) · **[Đã đo]** = gọi thật ngày 17/09
> bằng key giả · **[Chưa kiểm lại]** · **[Suy luận]** · **[Thứ cấp]**.

Bổ sung và **đính chính** cho `docs/research/2026-09-17-nen-tang-livestream-va-serpapi.md` §1.3 và mục D.2. Thao tác
lấy khoá nằm ở `docs/HUONG-DAN-LAY-KHOA-API.md` mục 2.

---

## 0. Tóm tắt dứt khoát

1. **Chuỗi gọi:** `videos.list` (1 đơn vị) → `activeLiveChatId` → đọc chat bằng `liveChatMessages.list` (đang dùng)
   hoặc `streamList` (khuyến nghị, chưa cài). `streamList` có **endpoint REST thật** trả **mảng JSON đẩy dần**. **[Đã đo]**
2. **Quota chưa chốt:** bảng chính thức ghi `list` = **1** đơn vị; log thật của một dự án mã nguồn mở tháng 9/2026 khớp
   với giá **5**. Với sàn đọc 2 giây của bộ thu hiện tại, buổi 90 phút tốn **2.881** đơn vị (giá 1) hoặc **13.681**
   (giá 5, **vượt** hạn mức 10.000/ngày). **[Đã kiểm]** phần nguồn; con số tính theo mã
3. **Video không công khai + API key:** **chưa có câu chính thức nào trả lời.** Căn cứ gián tiếp nghiêng về "đọc được"
   nhưng yếu. Hồ sơ **không được** khẳng định điều này trước khi đo T2. **[Một phần]**
4. **Video sắp phát:** tài liệu nói `activeLiveChatId` *"is filled only if the video is a currently live broadcast"*.
   **[Đã kiểm]**
5. **Key sai hiện trả HTTP 400** kèm `details[].reason = API_KEY_INVALID`, không phải `keyInvalid` như bảng lỗi cũ.
   **[Đã đo]**
6. **Webcam và điện thoại không chỉnh được độ trễ**; chỉ bộ mã hoá (OBS) mới chọn Low/Ultra-low. **[Đã kiểm]**
7. **Link trong chat không bấm được ở luồng dọc**, và phát kép ngang + dọc là **mặc định** khi phát từ Live Control
   Room. Chỉ người xem vào từ Shorts feed trên điện thoại mới thấy luồng dọc. **[Đã kiểm]**
8. **Không có API ghim** tin nhắn hay sản phẩm. Ghim sản phẩm làm tay (một sản phẩm ghim được cả trên app Android);
   chỉ chủ kênh ghim được **tin nhắn**. **[Một phần]** / **[Đã kiểm]**
9. **Đã có công cụ** `scripts/kiem_tra_youtube.py` (chỉ đọc, mã thoát 0/1) và 144 test không mạng; parser đã sửa lỗi
   biến sự kiện trả phí thành bình luận. **Chưa sửa** vòng đọc chat (mục 8.3).
10. **Đính chính tài liệu cũ:** đường dẫn `giftEventDetails.jewelsAmount` không khớp nguồn nào (mục 5).

---

## 1. Chuỗi gọi chính thức cho một buổi live

```
(0) videoId      ← người vận hành dán link (hoặc RSS kênh / PubSubHubbub, 0 đơn vị)
(1) GET https://www.googleapis.com/youtube/v3/videos?part=snippet,liveStreamingDetails&id=<id>        [1 đơn vị]
      → snippet.liveBroadcastContent ∈ {live, upcoming, none}
      → liveStreamingDetails.activeLiveChatId   (chỉ có khi ĐANG live và có chat)
      → liveStreamingDetails.concurrentViewers  (chuỗi số; vắng khi 0 người xem hoặc chủ kênh ẩn)
(2a) Khuyến nghị: GET https://youtube.googleapis.com/youtube/v3/liveChat/messages/stream?liveChatId=…&part=id,snippet
      (hoặc gRPC youtube.googleapis.com:443, StreamList)                                                 [giá chưa công bố]
(2b) Đang dùng:   GET https://www.googleapis.com/youtube/v3/liveChat/messages?liveChatId=…&part=id,snippet&pageToken=…
      → chờ pollingIntervalMillis rồi gọi lại với nextPageToken                                        [1 hoặc 5 đơn vị/lượt]
(3) Dừng khi: có offlineAt | item chatEndedEvent | lỗi 403 liveChatEnded (gRPC: FAILED_PRECONDITION)
(4) Song song: videos.list part=liveStreamingDetails định kỳ → concurrentViewers
```

### 1.1 `videos.list` và trường live

Nguồn: https://developers.google.com/youtube/v3/docs/videos (cập nhật 2026-09-16) ·
https://developers.google.com/youtube/v3/docs/videos/list

- *"A call to this method has a quota cost of 1 unit."* **[Chưa kiểm lại]**
- `activeLiveChatId`: *"This field is filled only if the video is a currently live broadcast that has live chat. Once the
  broadcast transitions to complete this field will be removed and the live chat closed down."* **[Đã kiểm]**
- `concurrentViewers`: *"will be present if the broadcast has current viewers and the broadcast owner has not hidden the
  viewcount"*. Trong Discovery Document, trường này có kiểu **chuỗi** `uint64`. **[Chưa kiểm lại]**
- `videos.batchGetStats` (mới 03/06/2026, bucket quota riêng) **không có** `concurrentViewers`, nên không thay được
  `videos.list` (https://developers.google.com/youtube/v3/revision_history). **[Chưa kiểm lại]**

### 1.2 `liveChatMessages.list`

Nguồn: https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list (cập nhật 2026-09-14)

- Đầu trang khuyến nghị: *"To poll for live chat messages, use the liveChatMessages.streamList method … helps to avoid
  exceeding your quota."* **[Chưa kiểm lại]**
- `maxResults` từ 200 đến 2000, mặc định 500. Lượt gọi đầu (không có token) chỉ trả tin **gần nhất**: không lấy lại được
  lịch sử, **bắt đầu đọc trễ là mất tin**. **[Chưa kiểm lại]**
- Lỗi trong bảng của trang: `forbidden`, `liveChatDisabled`, `liveChatEnded` (403); `liveChatNotFound` (404);
  `rateLimitExceeded`. `quotaExceeded` **không** nằm trong bảng này mà ở trang lỗi chung. **[Đã kiểm]**
- Trang **không có mục Authorization**. **[Đã kiểm]**

### 1.3 `liveChatMessages.streamList`

Nguồn: https://developers.google.com/youtube/v3/live/docs/liveChatMessages/streamList (cập nhật 2026-09-14) ·
https://developers.google.com/youtube/v3/live/streaming-live-chat ·
https://youtube.googleapis.com/$discovery/rest?version=v3 (revision `20260914`)

- Trang tham chiếu **không có** dòng HTTP request, **không có** Quota impact, **không có** mục Authorization. **[Đã kiểm]**
- **Endpoint REST chỉ thấy trong Discovery Document:** id `youtube.youtube.v3.liveChat.messages.stream`, `GET`, đường
  dẫn `youtube/v3/liveChat/messages/stream`; `maxResults` ghi *"Not used in the streaming RPC."* **[Đã kiểm]**
- **Đo 17/09/2026 (15:34 GMT) bằng key giả:** cả `www.googleapis.com` và `youtube.googleapis.com` đều trả 400,
  `Transfer-Encoding: chunked`, thân **bọc trong mảng JSON** `[{"error":{…API_KEY_INVALID…}}]`. Thêm `alt=sse` thì bị
  từ chối: *"Invalid value \"sse\" for query parameter 'alt'"*. Đối chứng: đường dẫn bịa trả 404 text/html, nên
  endpoint là thật. **[Đã đo]**
- Giới hạn của phép đo: mới thấy lớp bọc mảng **khi server trả lỗi**; chưa thấy dữ liệu thật. Nguồn độc lập thứ hai cho
  định dạng "mảng JSON đẩy dần" là bộ phân tích REST streaming của Google
  (https://github.com/googleapis/google-cloud-python/blob/main/packages/google-api-core/google/api_core/_rest_streaming_base.py),
  vốn báo *"Can only parse array of JSON objects"*. **[Đã kiểm]**
- Hệ quả cho mã: client HTTP phải đọc **tăng dần theo độ sâu ngoặc**, không `json.loads` cả thân (sẽ treo tới khi server
  đóng kết nối). **[Suy luận]**
- **gRPC:** kênh `dns:///youtube.googleapis.com:443`, `V3DataLiveChatMessageService/StreamList`, xác thực bằng metadata
  `x-goog-api-key` hoặc `authorization: Bearer`; hướng dẫn ghi *"You can use an OAuth 2.0 access token or an API key to run
  the demo."* **[Đã kiểm]**
- Hai câu nằm ở **trang tham chiếu streamList** (không phải trang hướng dẫn): nối lại bằng `nextPageToken` cuối cùng; và
  *"Due to a gRPC limitation, it is not possible to distinguish based on the error code between a LIVE_CHAT_DISABLED case
  and a LIVE_CHAT_ENDED case."* **[Đã kiểm]**

---

## 2. Quota

### 2.1 Bảng chính thức

Nguồn: https://developers.google.com/youtube/v3/determine_quota_cost (cập nhật 2026-09-15)

| Method | Giá | Mức |
|---|---|---|
| `videos.list` | 1 | [Đã kiểm] |
| `liveChatMessages.list` | **1** | [Đã kiểm] |
| `liveChatMessages.insert` / `delete` / `transition` | 50 | [Đã kiểm] |
| `liveChatMessages.streamList` | **không có trong bảng** (chữ "streamList" không xuất hiện trên trang) | [Đã kiểm] |
| `search.list`, `videos.insert` | bucket riêng 100 lượt/ngày từ 01/06/2026 (tài liệu dự án 17/09) | [Chưa kiểm lại] |

Câu chung trên trang: *"Every API request, even if invalid, will cost at least one quota point"*; mặc định **10.000
đơn vị/ngày**; đặt lại lúc nửa đêm giờ Thái Bình Dương (14:00 giờ VN mùa hè bên đó, 15:00 mùa đông). **[Chưa kiểm lại]**

### 2.2 Bằng chứng giá thực tế có thể là 5

PR #420 của kho `clear-bg/NSS-Result-Tracker`, gộp **09/09/2026**: https://github.com/clear-bg/NSS-Result-Tracker/pull/420
**[Đã kiểm]**, và **mạnh hơn** báo cáo gốc ghi:

- Nguyên văn (tiếng Nhật): 「`liveChatMessages.list` は1回5ユニット」 (list tốn 5 đơn vị/lượt).
- **47 phút là số đo từ log** của 4 buổi thật: từ lúc phát hiện live tới lỗi 403 `quotaExceeded` đầu tiên
  (48:09, 47:03, 48:44, 47:02).
- Cloud Console của họ ghi **20.511 lượt `list` trong 30 ngày**, ngày nào phát live cũng chạm trần; con số này khớp với
  giá 5 đơn vị/lượt.
- Nhịp 1,41 giây là **suy ngược từ giả định giá 5**: 「2,822秒 ÷ 2,000回 = 約1.41秒」. PR **không** nói chat của họ đông.
- Họ sửa bằng sàn đọc 10 giây.

Kết luận: **lập ngân sách theo giá 5**, chốt bằng Cloud Console sau buổi đo (phép thử T10).

### 2.3 Hạn mức theo đúng cách bộ thu LiveLift chạy

Nguồn: `docs/HUONG-DAN-LAY-KHOA-API.md` §2.4 và mã `src/livelift/ingest/youtube.py`, `src/livelift/api/ingest_jobs.py`
(tổng biên tập đọc ngày 17/09/2026).

- Bộ thu đọc chat theo `pollingIntervalMillis` nhưng **không nhanh hơn 2 giây/lượt** (`DEFAULT_POLL_FLOOR_MS = 2000`),
  đọc số người xem mỗi 30 giây.
- Khi chờ lên sóng, cứ 20 giây (`WAIT_FOR_LIVE_S`) bộ thu dò lại, mỗi vòng tối đa 2 lượt `videos.list` → khoảng
  **6 đơn vị/phút**. Người phản biện đã mô phỏng `IngestManager` thật để xác nhận con số 2 lượt/vòng.

| Buổi 90 phút, trường hợp tốn nhất | Bật bộ thu đúng lúc phát | Bật ở T−2h (+720) |
|---|---|---|
| Giá `list` = 1 | 2.881 đơn vị (29%) | 3.601 đơn vị (36%) |
| Giá `list` = 5 | **13.681 — vượt hạn mức ngày** | **14.401 — vượt** |

Rủi ro **chưa đo**: nếu thực tế YouTube cấp `activeLiveChatId` sớm cho buổi đã lên lịch, bộ thu sẽ đọc chat suốt thời
gian chờ; chờ 120 phút tốn thêm tới 3.600 lượt `list` (3.600–18.000 đơn vị). Công cụ kiểm tra tự cảnh báo khi gặp
trường hợp này (mục 8.1).

Quy tắc đề xuất: nhịp đọc thực = `max(pollingIntervalMillis, sàn_ngân_sách)`, với
`sàn_ngân_sách = thời_lượng_giây × giá_mỗi_lượt / ngân_sách_đơn_vị`. Ví dụ giữ một buổi 90 phút trong 30% hạn mức
(3.000 đơn vị) với giá 5: sàn = 5.400 × 5 / 3.000 = **9 giây**. Công cụ kiểm tra tính thêm lượt đọc số người xem và
lượt dò lúc chờ, nên theo bản sửa sau phản biện nó in khoảng **10 giây** khi bật bộ thu đúng lúc phát và **13 giây** khi
bật ở T−2h. Chậm hơn vài giây nhưng **không mất tin**, vì `nextPageToken` nối tiếp. **[Suy luận]**

---

## 3. Dạng lỗi thật và cách phân loại

Đo ngày 17/09/2026 bằng key giả trên `videos.list` và `liveChat/messages`. **[Đã đo]**, người kiểm chứng gọi lại lúc
15:34 GMT và ra cùng kết quả.

| Trường hợp | HTTP | `errors[].reason` | `details[]` | Thông điệp |
|---|---|---|---|---|
| Không có key | 403 | `forbidden` | — (`status: PERMISSION_DENIED`) | *"Method doesn't allow unregistered callers (callers without established identity)…"* |
| Key sai (trong query hoặc header `X-Goog-Api-Key`) | 400 | **`badRequest`** | ErrorInfo `reason: API_KEY_INVALID`, `domain: googleapis.com` | *"API key not valid. Please pass a valid API key."* |

Trang lỗi chung (https://developers.google.com/youtube/v3/docs/core_errors, cập nhật 2025-08-20) vẫn ghi `keyInvalid`
dưới mã 400 và không nhắc `details[]`. Mã HTTP khớp tài liệu, chỉ có `reason` là khác. **[Đã kiểm]**

**Thứ tự phân loại:** `error.details[].reason` → `error.errors[].reason` → mã HTTP. Lý do: cùng một mã 403 có thể là
`quotaExceeded` (dừng tới giờ đặt lại), `liveChatEnded` (dừng hẳn), `forbidden` (đổi video hoặc quyền) hay
`accessNotConfigured` (bật API). PR #420 cũng viết 「同じ403でも取るべき対処が正反対」 (cùng là 403 nhưng cách xử lý ngược
nhau).

Mẫu `quotaExceeded` và `accessNotConfigured` lấy từ diễn đàn và issue, chưa tự gây được:
https://forum.bubble.io/t/youtube-api-quotaexceeded-error/304619 · https://github.com/youtube/api-samples/issues/129
**[Thứ cấp]**

---

## 4. Video không công khai và video sắp phát

### 4.1 API key có đọc được chat của video Không công khai?

**Trả lời: chưa ai biết chắc; phải đo (phép thử T2).** **[Một phần]**

| Căn cứ | Nội dung | Sức nặng |
|---|---|---|
| Trang `liveChatMessages.list` và `streamList` | Không có mục Authorization; không có chữ unlisted/private/public nào | [Đã kiểm] — không trả lời trực tiếp |
| Hướng dẫn Streaming Live Chat | *"You can use an OAuth 2.0 access token or an API key to run the demo."* https://developers.google.com/youtube/v3/live/streaming-live-chat | [Đã kiểm] — gián tiếp |
| Tài liệu `videos`, mục `snippet.publishedAt` | Với video tải lên ở chế độ không công khai: *"anyone who knows the video's unique video ID can retrieve the video metadata"* — nói về video tải lên, chưa chắc áp dụng cho buổi live | [Chưa kiểm lại] (trích ở `HUONG-DAN-LAY-KHOA-API.md` §2.7) |
| Issue googleapis/google-api-python-client #2648 (30/08/2025) | Báo cáo gốc dùng làm căn cứ, nhưng issue nói về video **members-only**, không nhắc unlisted, live chat hay API key | **Yếu** — người kiểm chứng xác nhận lệch chủ đề |
| Bài Medium của J. Kalambay về chatbot | Không mở được | Chưa kiểm chứng, **bỏ** |

**Video Riêng tư:** không dùng. Tài liệu `videos` chỉ cho **chủ kênh** đọc thông tin video riêng tư, còn bộ thu dùng API
key. **Đường dự phòng chính thức nếu T2 thất bại:** chuyển buổi live sang **Công khai**, hoặc dùng OAuth
`youtube.readonly` của chính kênh nhóm với `liveBroadcasts.list?mine=true` để lấy `snippet.liveChatId`
(https://developers.google.com/youtube/v3/live/docs/liveBroadcasts). **[Suy luận]**

### 4.2 Video sắp phát

- Tài liệu `videos` và Discovery Document: `activeLiveChatId` chỉ có khi **đang** live. **[Đã kiểm]**
- Mẫu chính thức `youtube/youtubechatbot` ghi *"Set videoId to the ID of an upcoming or active live event"*, nhưng dùng
  OAuth, nhiều khả năng lấy `liveChatId` qua `liveBroadcasts`, và kho đã lưu trữ từ 19/04/2026
  (https://github.com/youtube/youtubechatbot). Không mâu thuẫn trực tiếp. **[Đã kiểm]**
- Kết luận: **không dựa vào `activeLiveChatId` trước giờ phát**; đo thật ở phép thử T3.

### 4.3 Sau khi kết thúc

- *"After the event ends, live chat is no longer available for that event."*
  (https://developers.google.com/youtube/v3/live/docs/liveChatMessages). **[Chưa kiểm lại]**
- `chatEndedEvent` *"is not sent for live chats on a channel's default broadcast"*, nên không được coi là tín hiệu kết
  thúc duy nhất; phải kết hợp `offlineAt`, lỗi `liveChatEnded` và `actualEndTime`. **[Chưa kiểm lại]**
- Không có API chính thức đọc **chat replay**: LiveLift phải thu **trong lúc live**. **[Chưa kiểm lại]**

---

## 5. Cấu trúc JSON và mâu thuẫn giữa các nguồn Google

**Trường quà Jewels (`giftEvent`, thêm ngày 26/03/2026) — ba nguồn chính thức không khớp nhau.** **[Đã kiểm]**

| Nguồn | Đường dẫn trường | `giftDuration` |
|---|---|---|
| Trang HTML `liveChatMessages` (cập nhật 2026-09-14) và Live API revision history (mục March 26, 2026: *"new snippet.giftEventDetails property"*) | `snippet.giftEventDetails.giftMetadata.{jewelsAmount, giftName, giftUrl, giftDuration, hasVisualEffect, comboCount, altText, language}` | object `{seconds, nanos}` |
| Discovery Document rev `20260914` | `snippet.giftDetails` (`$ref LiveChatGiftDetails`), trường **phẳng**; toàn tệp không có chữ `giftEventDetails` hay `giftMetadata` | chuỗi, `format: google-duration` (ví dụ `"5s"`) |
| `stream_list.proto` (hướng dẫn gRPC) | `LiveChatGiftDetails gift_details = 34` | `google.protobuf.Duration` (thành chuỗi `"5s"` khi chuyển sang JSON) |

Nguồn: https://developers.google.com/youtube/v3/live/docs/liveChatMessages ·
https://developers.google.com/youtube/v3/live/revision_history · https://youtube.googleapis.com/$discovery/rest?version=v3 ·
https://developers.google.com/youtube/v3/live/streaming-live-chat

- **Đính chính:** tài liệu `2026-09-17-nen-tang-livestream-va-serpapi.md` (dòng 110 và 345) ghi
  `giftEventDetails.jewelsAmount`, thiếu lớp `giftMetadata`, nên **không khớp nguồn nào**.
- Ghi chú cho parser: *"For giftEvents, the same ID may be reused to update the combo count."* → ghi đè bản cũ theo `id`,
  không cộng dồn. **[Đã kiểm]**
- Một số mâu thuẫn khác (báo cáo gốc, **[Chưa kiểm lại]**): sticker `language` (HTML) và `altTextLanguage` (Discovery);
  `amountMicros` là chuỗi `uint64` trong Discovery; trang HTML liệt kê loại `pollDetails` còn Discovery dùng `pollEvent`;
  `tally` của poll chỉ trả khi *"the API request is authorized by the channel owner"*; revision 23/06/2026 bỏ
  `messageDeletedEvent`, `messageRetractedEvent`.

---

## 6. Cài đặt kênh ảnh hưởng trực tiếp tới chỉ số LiveLift

| Cài đặt | Nguyên văn | Tác động và việc cần làm | Nguồn | Mức |
|---|---|---|---|---|
| **Độ trễ** | *"Webcam and mobile streaming are always set up for interactivity. You cannot set a live stream latency for them."* Chỉ bộ mã hoá mới chọn Low (*"less than 10 seconds"*) hay Ultra-low (*"less than 5 seconds"*, dễ giật) | Giả định "Webcam + độ trễ thấp" trước đây là **sai**. Muốn chọn độ trễ thì dùng OBS | https://support.google.com/youtube/answer/7444635 | [Đã kiểm] |
| **Link trong chat ở luồng dọc** | Bảng so sánh: *"Clickable links in chat and channel description"* — Horizontal **Yes**, Vertical live feed **No** | Người xem luồng dọc không bấm được `/r/{code}` → làm loãng biến kết quả chính | https://support.google.com/youtube/answer/2474026 | [Đã kiểm] |
| **Phát kép (mặc định)** | *"By default, your live streams will go live in both horizontal … and vertical … formats at the same time when you stream from the Live Control Room"*; tắt: *"turn off Dual stream"*; *"You can't add the vertical format once the stream has started."* Phạm vi: *"Viewers watching your stream in the Shorts feed on mobile will see the vertical version. All other viewers will see the horizontal stream."* | **Tắt Dual stream** trong phiên thí nghiệm. Đánh đổi: mất khả năng được phát hiện qua Shorts feed. Không đổi giữa chừng | như trên | [Đã kiểm] |
| **Chặn link** | *"Comments with links aren't blocked if they're posted by you, moderators, or approved users."* và *"Live chat messages with URLs are also blocked."* | Câu miễn trừ nói về **bình luận video**; áp cho **live chat** là suy luận. Phải đo ở T8 trước khi dựa vào việc chủ kênh gửi được link khi bật chặn | https://support.google.com/youtube/answer/9483359 | [Một phần] |
| **Giữ tin để duyệt** | None / Basic / Strict | Tin bị giữ có thể không tới API → recall giảm giả tạo; đặt None/Basic khi đo; đo ở T9 | https://support.google.com/youtube/answer/9826490 | [Chưa kiểm lại] |
| **Ghim tin nhắn** | *"Only you, not your moderators or viewers, can pin messages."*; *"You can only pin one message at a time."* | Người ghim **tin nhắn** phải đăng nhập tài khoản chủ kênh | https://support.google.com/youtube/answer/2524549 | [Đã kiểm] |
| **Ghim sản phẩm Shopping** | Bản máy tính: tab Shopping, biểu tượng ghim; *"The feature to pin multiple products is only available on desktop"*; tự xoay vòng *"rotate in every 60 seconds"*. Bản Android: *"Tap Shopping … Tap Pin next to the product you want to pin"* | Ghim **một** sản phẩm làm được cả trên app Android; ghim nhiều và xoay vòng cần máy tính. **Tắt xoay vòng 60 giây** trong phiên switchback, nếu không khối TẮT vẫn có ghim. Trang không nói ai (chủ kênh hay kiểm duyệt) được ghim sản phẩm | https://support.google.com/youtube/answer/12299016 · https://support.google.com/youtube/answer/12299016?hl=en&co=GENIE.Platform%3DAndroid | [Một phần] — "chỉ trong Studio" là sai |
| **Không có API ghim** | Discovery rev `20260914`: 0 lần xuất hiện "shopping", "productTag", "pinned" | Ghim tay; LiveLift ghi thời điểm | https://youtube.googleapis.com/$discovery/rest?version=v3 | [Đã kiểm] |

Điều kiện kênh thử (báo cáo gốc, **[Chưa kiểm lại]**): *"To live stream, you need to have no live streaming restrictions in
the past 90 days and you need to verify your channel"* (answer/2474026); *"You may need to wait 24 hours before you can
start your first live stream"* (https://support.google.com/youtube/answer/9228390); phát bằng điện thoại cần *"At least 50
subscribers"* (cùng trang).

---

## 7. Kịch bản kiểm thử (T0–T10)

**Chuẩn bị:** kênh thử của nhóm đã xác minh số điện thoại ít nhất 24 giờ trước; **hai dự án Google Cloud riêng**
(P-list chỉ gọi `list`, P-stream chỉ gọi `streamList`) để tách số quota; 2–3 tài khoản người xem là thành viên nhóm; đồng
bộ giờ máy (Windows: `w32tm /resync`). Cấu hình buổi đo: **Dual stream TẮT**, giữ tin = None/Basic, slow mode tắt, tự
xoay vòng sản phẩm tắt.

| Mã | Mục tiêu | Cách làm | Đạt khi | Trước |
|---|---|---|---|---|
| T0 | Key và API | `kiem_tra_youtube.py` không có `--video`; thử cố ý key sai | Mã thoát 0 với key đúng; nhãn `KEY_SAI` với key sai | 30/09 |
| T1 | Chuỗi gọi cơ bản | Live **công khai** bằng Webcam 10 phút; `--video` | Có `activeLiveChatId`; `concurrentViewers` là số hoặc vắng khi 0 người | 30/09 |
| T2 | **Không công khai + API key** | Lặp T1 với video **Không công khai** | Mục 4 của công cụ ghi OK và in dòng "ĐÃ ĐO"; nếu `forbidden` → chuyển sang Công khai | 30/09 |
| T3 | Video sắp phát | Lên lịch trước 15 phút; chạy `--video` ở T−10, T−1, T+0, T+1 phút | Bảng có/không `activeLiveChatId` theo mốc | 30/09 |
| T4 | Recall | 3 người gửi tin đánh số `LL-<người>-<stt>` (1 tin/5 giây trong 10 phút + một đợt dồn 20 tin/30 giây) | Số tin khớp / số tin gửi ≥ **99%** (loại tin bị giữ hoặc chặn) | 30/09 cho `list` |
| T5 | Độ trễ | `trễ_API = giờ nhận − publishedAt` (hiệu chỉnh lệch đồng hồ) | Báo p50/p90/p99 riêng `list` và `streamList` | 10/10 |
| T6 | Nối lại | Rút mạng 30 giây giữa buổi | 0 tin mất; tin trùng khử theo `id` | 10/10 |
| T7 | Kết thúc | Bấm End; ghi thời điểm `offlineAt`, `chatEndedEvent`, lỗi `liveChatEnded`, `actualEndTime` | Có bảng thời gian thật; bộ thu dừng sạch | 30/09 |
| T8 | Chặn link | Bật/tắt *Block links*; người xem thường và chủ kênh gửi `https://…/r/TEST` | Ghi tin nào hiện, tin nào tới API | 10/10 |
| T9 | Tin bị giữ | Đặt Strict, gửi tin "nghi vấn" giả | Ghi tin bị giữ có tới API không | 10/10 |
| T10 | Giá quota thật | Mỗi dự án chạy một phương thức 30 phút; đọc Cloud Console → YouTube Data API v3 → Metrics/Quotas trước và sau | Chốt giá `list` (1 hay 5); giá `streamList` theo kết nối hay theo phản hồi | 30/09 cho `list` |

**Bốn con số đưa vào hồ sơ** sau buổi đo trước 30/09: recall của `list`, độ trễ p50/p90 của `list`, giá quota thật của
`list`, kết quả T2. Hồ sơ viết dạng: *"bảng Google ghi 1 đơn vị/lượt `list`, một dự án cộng đồng 09/2026 quan sát tương
đương 5 — nhóm đo được X"*.

**An toàn dữ liệu:** chỉ thành viên nhóm chat; không lưu `displayName`/`channelId` thô; xoá chat thô trong vòng 30 ngày
theo chính sách nhà phát triển: *"not longer than 30 calendar days"*
(https://developers.google.com/youtube/terms/developer-policies). **[Chưa kiểm lại]**

---

## 8. Công cụ `scripts/kiem_tra_youtube.py` (đã triển khai 17/09/2026, chưa commit)

### 8.1 Công cụ làm gì

Chạy: `.venv/Scripts/python scripts/kiem_tra_youtube.py [--video <link|id>] [--thoi-luong-phut 90] [--cho-truoc-phut 120]
[--ngan-sach-phan-tram 30] [--timeout 20]`. **Chỉ đọc**, gọi qua chính `YouTubeLiveChatClient` của bộ thu.
**Mã thoát 0 = SẴN SÀNG, 1 = CHƯA SẴN SÀNG.**

1. Có `YOUTUBE_API_KEY` không; chỉ in độ dài, không in khoá.
2. Một lượt `videos.list` (1 đơn vị). Phân loại lỗi theo `details[].reason` → `errors[].reason` → mã HTTP, ra các nhãn
   `KEY_SAI`, `KEY_HET_HAN`, `CHUA_BAT_API` (in link bật API nếu Google gửi), `KEY_BI_GIOI_HAN`, `HET_QUOTA`, `QUA_NHANH`,
   `CHAT_DA_KET_THUC`, `CHAT_BI_TAT`, `KHONG_THAY_CHAT`, `KHONG_CO_QUYEN`, `THIEU_KEY`, `LOI_MAY_CHU`, `LOI_MANG`,
   `PHAN_HOI_HONG`, `KHONG_RO`; mỗi nhãn có câu tiếng Việt và cách sửa.
3. Với `--video`: trạng thái live, chế độ riêng tư, các mốc giờ, `activeLiveChatId`, `concurrentViewers`. Video sắp phát
   chỉ **cảnh báo**; nếu Google đã trả `activeLiveChatId` cho buổi sắp phát thì in "ĐÃ ĐO" kèm cảnh báo quota lúc chờ.
   Đã kết thúc, không phải video live, không tìm thấy, hoặc đang live mà không có chat → **chặn**.
4. Đọc **một** trang chat với đúng tham số của bộ thu (`part=id,snippet`, `maxResults=500`). Chỉ in số đếm theo loại sự
   kiện, `pollingIntervalMillis`, có/không `nextPageToken`/`offlineAt`/`activePollItem`, dạng trường quà gặp được, và cảnh
   báo loại sự kiện lạ. **Không in nội dung tin, tên hay mã kênh người xem.** Video Không công khai đọc được chat thì in
   "ĐÃ ĐO: API key đọc được chat của video Không công khai".
5. Ước lượng quota theo **trường hợp tốn nhất** (sàn 2 giây của bộ thu), cộng chi phí chờ lên sóng, in riêng giả định
   giá 1 và giá 5, in nhịp đọc tối thiểu để giá 5 vừa ngân sách. Nhịp đo được lúc thử chỉ in "để tham khảo".
6. Kết luận kèm mã thoát.

Bảo vệ khoá: không bao giờ in chuỗi ngoại lệ của httpx (chuỗi đó chứa URL có `key=`), che khoá lần cuối trước khi in.

### 8.2 Test và sửa lỗi parser

- **Lỗi thật đã sửa trong `src/livelift/ingest/youtube.py`:** `parse_live_chat_message` trước đây lấy `displayMessage` của
  **mọi** loại tin. Chạy bản cũ trên fixture thì 13 sự kiện không phải văn bản (Super Chat, Super Sticker, `giftEvent`,
  hội viên, poll, `userBannedEvent`, loại lạ) bị biến thành bình luận; riêng `userBannedEvent` mang tên người bị cấm.
  Sửa: thêm `COMMENT_TYPES = {"textMessageEvent"}`, loại khác trả `None` có chủ đích; item không có `type` giữ hành vi cũ.
- `tests/data/youtube/`: **23 fixture JSON**, toàn dữ liệu giả, mỗi tệp có trường `_nguon` ghi URL, ngày truy cập và phần
  nào là giả định; có cả hai dạng quà mâu thuẫn và hai thân lỗi đo thật bằng key giả.
- `tests/test_kiem_tra_youtube.py` (69 test) và `tests/test_youtube_hop_dong.py` (75 test): **144 test đạt** khi tổng biên
  tập chạy lại ngày 17/09/2026, không cần mạng hay key.
- Phản biện độc lập: không có lỗi P0/P1; hai lỗi P2 về ước lượng quota (dựa vào **một** mẫu `pollingIntervalMillis` lúc
  chat vắng; quên chi phí chờ lên sóng) **đã sửa kèm test**.
- `docs/HUONG-DAN-LAY-KHOA-API.md` mục 2.3, 2.4, 2.6 đã cập nhật; mục 2.7 mới trả lời câu hỏi video Không công khai.

### 8.3 Chưa làm (việc cho làn của Khánh)

| Việc | Hệ quả nếu không làm | Căn cứ |
|---|---|---|
| Vòng đọc chat coi mọi 401/403 là "key sai hoặc hết quota", ngủ 60 giây rồi thử lại | Khi 403 `liveChatEnded` tới trước `offlineAt`, bộ thu lặp tới khi phiên đóng với thông báo sai. PR #420 xác nhận ca này có xảy ra: 「同じ死んだチャットIDへ投げ続けていた」. Tầng job hủy tác vụ khi phiên đóng, nên vòng lặp **không vĩnh viễn** | [Một phần] — `src/livelift/ingest/base.py` `AUTH_STATUSES={401,403}` |
| Key sai trả 400 | Lúc khởi động, `get_active_live_chat_id` thử 4 lần rồi báo "lỗi mạng/API tạm thời", sai nhãn | [Đã kiểm] |
| Sàn đọc 2 giây | Nếu giá thật là 5 đơn vị, hạn mức cạn quanh phút 67 của buổi 90 phút | mục 2.3 |
| Khoá API nằm trong query `key=` | Bộ lọc log đang che, nhưng đưa khoá vào header `X-Goog-Api-Key` an toàn hơn (header đã được Google nhận, mới thử với key giả) | [Đã đo] |
| `stream_comments` (HTTP stream) | Vẫn `NotImplementedError` | mục 1.3 |
| Parser sự kiện trả phí thành bản ghi riêng | `giftEvent`/`superChatEvent` đang bị bỏ có chủ đích, chưa vào chỉ số phụ | mục 10 |

---

## 9. Công nghệ live commerce mới của YouTube 2025–2026

| Mục | Nội dung | Nguồn | Mức |
|---|---|---|---|
| YouTube Shopping Affiliate ở VN | Ra mắt **03/11/2024**, đối tác đầu tiên Shopee; nhà sáng tạo gắn thẻ và ghim sản phẩm trong livestream | https://kenh14.vn/youtube-ra-mat-shopping-affiliate-tai-viet-nam-215241103211212334.chn | [Thứ cấp], [Chưa kiểm lại] |
| Điều kiện Shopping Affiliate | Kênh trong YouTube Partner Program; danh sách nước có Vietnam; không phải kênh nhạc, không "Made for Kids" | https://support.google.com/youtube/answer/13376398 | [Chưa kiểm lại] |
| YouTube Festival Vietnam 2026 (16/09/2026) | Mua qua YouTube từ Shopee, Lazada, CellphoneS; *"hơn 50% nhà sáng tạo đủ điều kiện ở Đông Nam Á tham gia"*; lần đầu có Affiliate Partnerships Boost ở ĐNÁ | https://kenh14.vn/93-nguoi-dung-internet-viet-nam-xem-youtube-moi-ngay-215260917133602668.chn | [Thứ cấp], [Chưa kiểm lại] |
| Quà Jewels | VN có trong danh sách nước bật quà; API có `giftEvent` từ 26/03/2026 | https://support.google.com/youtube/answer/15534883 · https://developers.google.com/youtube/v3/live/revision_history | [Đã kiểm] phần API |
| Merchant API Reports v1alpha | Số liệu affiliate YouTube **theo ngày** × video × sản phẩm (`gross_sales`, `orders`, `clicks`, `views`…); chỉ cho Merchant Center trong YouTube Affiliate Program; *"in public alpha"* | https://developers.google.com/merchant/api/guides/reports/analyze-youtube-affiliate-performance | [Chưa kiểm lại] |
| Made on YouTube 16/09/2025 | Tự tạo Shorts từ khoảnh khắc live bằng AI; phát ngang + dọc cùng lúc với một phòng chat; Practice mode; không kèm API mới | https://blog.youtube/news-and-events/live-updates/ | [Chưa kiểm lại] |
| Made On YouTube 2026 | *"will be taking place on September 23 in New York City"* — sau ngày soạn tài liệu; xem lại trước hackathon | https://blog.youtube/madeonyoutube/ | [Chưa kiểm lại] |
| Thay đổi Live API 2026 | `giftEvent` 26/03; `availabilityConfig` 01/06; `snippet.categoryId` 17/08; midroll tự động 12/01 | https://developers.google.com/youtube/v3/live/revision_history | [Chưa kiểm lại] |
| Poll | Tạo/đóng qua API bằng OAuth chủ kênh, 50 đơn vị/lượt; *"You can only transition to closed"* | https://developers.google.com/youtube/v3/live/docs/liveChatMessages/insert · …/transition | [Chưa kiểm lại] |
| Live Q&A | Không có loại `type` tương ứng trong Discovery → không có API | Discovery Document | [Chưa kiểm lại] |
| Hype | Tin 27/08/2025 nói triển khai toàn cầu, danh sách 39 nước của RouteNote không có VN → chưa rõ | https://www.mediapost.com/publications/article/408490/youtubes-creator-hype-feature-rolls-out-globall.html · https://routenote.com/blog/youtube-hype-in-39-countries/ | [Thứ cấp] |
| Gắn thẻ sản phẩm Amazon | Cho nhà sáng tạo **Mỹ**, cuối 08/2026; không liên quan VN | https://techmymoney.com/2026/08/28/youtube-amazon-product-tags-now-work-in-videos-shorts-and-livestreams/ | [Thứ cấp] |
| Resource `thirdPartyLinks` trong Discovery | Liên kết kênh với cửa hàng/chương trình affiliate; không có trang tài liệu công khai, không khai báo scope; không ghim được sản phẩm vào live | Discovery Document | [Chưa kiểm lại] |

**Ý nghĩa cho LiveLift:** trên YouTube, "BẬT ghim" = ghim sản phẩm hoặc ghim tin nhắn, **đều làm tay**; LiveLift ra lịch,
đồng hồ đếm và ghi thời điểm người vận hành xác nhận. Merchant API chỉ cho số **theo ngày**, không đo được hiệu ứng theo
khối 10–15 phút.

---

## 10. Khuyến nghị theo mốc

**Trước 30/09/2026**

1. Hôm nay: tạo kênh thử và **xác minh số điện thoại ngay** (lần phát đầu có thể phải chờ 24 giờ); tạo 2 dự án Google
   Cloud (P-list, P-stream), bật YouTube Data API v3, giới hạn key chỉ cho API này.
2. Một buổi đo 60–90 phút bằng Webcam: T0, T1, T2, T3, T4-list, T7, T10-list, cấu hình ở mục 7. Chạy
   `kiem_tra_youtube.py --video` trước khi bật bộ thu.
3. Hồ sơ chỉ ghi điều đã đo hoặc có nguồn; không viết "API key đọc được video không công khai" trước khi T2 đạt; không
   hứa ghim tự động trên YouTube.
4. Sửa tài liệu cũ: đường dẫn trường quà; thêm "Webcam/điện thoại không chọn được độ trễ"; thêm "link trong chat không
   bấm được ở luồng dọc, phát kép là mặc định".

**Trước hackathon 10–11/10**

5. Sửa vòng đọc chat trong `youtube.py` theo bảng 8.3: phân loại theo `details[].reason` rồi `errors[].reason`
   (`liveChatEnded` → dừng hẳn; `API_KEY_INVALID`/`accessNotConfigured` → dừng; `quotaExceeded` → dừng tới 14–15 giờ VN);
   sàn đọc theo ngân sách, mặc định 10 giây; khoá vào header.
6. Cài `stream_comments` bằng HTTP (parser mảng JSON tăng dần, nối lại bằng `nextPageToken`, khử trùng theo `id`) sau
   feature flag, giữ `list` làm dự phòng; chạy T5, T6, T8, T9, T10-stream. Chỉ chuyển sang gRPC nếu HTTP stream không ổn.
7. Cố định kịch bản demo: kênh nhóm; video Không công khai nếu T2 đạt; OBS Ultra-low hoặc Webcam; Dual stream TẮT; tự xoay
   vòng TẮT; người ghim đăng nhập tài khoản chủ kênh; *Block links* chỉ bật nếu T8 xác nhận chủ kênh vẫn gửi được link.
8. Xem Made On YouTube 23/09/2026; cập nhật mục 9 nếu có API Shopping hoặc live mới.

**Trước chung kết 20–22/11**

9. Đưa `giftEvent`/`superChatEvent` vào **chỉ số phụ**, phân tích riêng, không trộn vào NLP bình luận; parser nhận cả
   `giftDetails` lẫn `giftEventDetails.giftMetadata` và ghi log dạng đã gặp.
10. Chỉ thử Merchant API Reports v1alpha nếu có đối tác merchant trong YouTube Affiliate Program; chỉ để đối chiếu tổng
    phiên theo ngày.

## 11. Câu hỏi còn mở

1. Giá thật của `liveChatMessages.list` là 1 hay 5 đơn vị? `streamList` tính theo kết nối, theo phản hồi hay miễn phí? (T10)
2. Qua REST, trường quà thật là `giftDetails` hay `giftEventDetails.giftMetadata`? `giftDuration` là chuỗi hay object?
3. API key có đọc được chat của video Không công khai không? (T2)
4. Video sắp phát có `activeLiveChatId` trước giờ phát không, từ lúc nào? (T3)
5. Tin bị giữ (Basic/Strict) hoặc bị chặn vì có link có tới API không? Chủ kênh có được miễn chặn link trong **live chat**
   không? (T8, T9)
6. `displayMessage` của `superChatEvent`, `giftEvent`, `newSponsorEvent` có chứa tên người gửi không?
7. Kết nối `streamList` qua HTTP giữ bao lâu thì server đóng? Mỗi phần tử có kèm `pollingIntervalMillis`/`offlineAt` không?
8. Gọi `videos.list` bằng API key có nhận được `status.privacyStatus` không?
9. `concurrentViewers` cập nhật theo nhịp nào, lệch bao nhiêu so với YouTube Studio?
10. Merchant API Reports (view affiliate YouTube) có áp dụng cho merchant bán tại Việt Nam không, trễ bao lâu?
11. Made On YouTube 23/09/2026 có công bố API cho Shopping, ghim sản phẩm hay chat live không?
