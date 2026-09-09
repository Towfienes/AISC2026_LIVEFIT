# Đọc live chat YouTube **đang phát** bằng yt-dlp (không cần API key) — đo thật 09/09/2026

**Câu hỏi.** Nhóm chưa có `YOUTUBE_API_KEY` nên `src/livelift/ingest/youtube.py`
(Data API) **không chạy được dòng nào**. yt-dlp 2026.08.19 đã có sẵn trong venv.
Có lấy được chat của một phiên **đang phát** (không phải VOD) không, độ trễ bao
nhiêu, có lấy được số người xem đồng thời không?

**Kết luận ngắn.**

| | Kết quả |
|---|---|
| Chat phiên đang phát | **CÓ** — chạy thật, 104 bình luận qua toàn bộ pipeline |
| Số người xem đồng thời | **CÓ** — `concurrent_view_count`, số thật và biến thiên |
| Độ trễ giao tin | **~24 s (p50), ~37 s (p90)** — dấu thời gian sự kiện vẫn chính xác |
| Cần credential | **Không** |
| Hợp Điều khoản dịch vụ YouTube | **KHÔNG** — xem §6. Đây là điểm quyết định. |

Kết luận vận hành: **đường này chạy được ngay hôm nay, nhưng không phải đường
để công bố.** Việc đúng phải làm song song là xin API key (miễn phí, ~10 phút).

---

## 1. Cơ chế (đọc từ mã nguồn yt-dlp, không phải phỏng đoán)

`yt_dlp/extractor/youtube/_video.py:4401` gắn phụ đề giả `live_chat` với
`protocol = 'youtube_live_chat'` khi `live_status` là `is_live` hoặc
`is_upcoming` (VOD thì là `youtube_live_chat_replay`). Bộ tải
`yt_dlp/downloader/youtube_live_chat.py` (`YoutubeLiveChatFD`) poll liên tục
theo continuation token và **ghi thẳng vào file, flush sau mỗi fragment**
(`_append_fragment` → `dest_stream.write(...)` + `.flush()`), chạy cho tới khi
luồng kết thúc.

Với luồng đang phát, mỗi dòng ghi ra là một *pseudo-action* được cố ý làm
giống hệt định dạng replay:

```json
{"replayChatItemAction": {"actions": [<action thật>]},
 "videoOffsetTimeMsec": "-331725", "isLive": true}
```

Hai điểm quan trọng rút ra từ đây:

1. **`videoOffsetTimeMsec` KHÔNG dùng làm đồng hồ được.** Với luồng live nó là
   `timestamp - thời điểm yt-dlp khởi động`, nên **âm** với phần chat tồn đọng
   lúc kết nối (đo được `-331725` = 5,5 phút trước). Dấu thời gian đúng nằm ở
   `liveChatTextMessageRenderer.timestampUsec` (epoch micro giây, tuyệt đối).
   Adapter dùng `timestampUsec`; `parse_live_chat_actions` bỏ qua offset.
2. **Một parser dùng chung cho cả live và replay.** Kiểm tra 11 file
   `.live_chat.json` VOD thật: 100% bản ghi text đều có cả `id` và
   `timestampUsec`.

## 2. Số đo thật

Video kiểm chứng: `6ekwo7H_BJU` (tiếng Việt, ~860→1160 người xem đồng thời).
Máy Windows 11, yt-dlp 2026.08.19, mạng gia đình.

**(A) Thu chat thô — 151 giây**

```bash
yt-dlp --skip-download --write-subs --sub-langs live_chat \
       -o "%(id)s.%(ext)s" "https://www.youtube.com/watch?v=6ekwo7H_BJU"
```

| Chỉ số | Giá trị |
|---|---|
| Bản tin text | 100 (id **duy nhất 100/100**) |
| Trong đó tồn đọng lúc kết nối | 66 (cũ nhất **328,8 s** trước khi chạy) |
| Phát sinh trong lúc chạy | 34 → **13,5 tin/phút** |
| Loại bản ghi khác | `liveChatPlaceholderItemRenderer` ×5, `ViewerEngagementMessage` ×1 |
| Tiếng Việt có dấu | nguyên vẹn ("chốt đơn", "em xin link tai nghe với anh ơi") |

**(B) Độ trễ giao tin — 180 giây, chỉ tính tin sinh ra SAU khi kết nối**

| p50 | p90 | min | max | Dữ liệu đầu tiên xuất hiện |
|---|---|---|---|---|
| **24,1 s** | 37,4 s | 12,3 s | 37,4 s | sau 14,7 s |

Nguyên nhân nằm trong `parse_actions_live`: nó `time.sleep(timeoutMs/1000)`
**trước** khi `_append_fragment`, nên một bản tin chờ khoảng hai nhịp poll. Đây
là đặc tính của công cụ, không phải lỗi cấu hình — không hạ xuống được nếu còn
dùng yt-dlp.

**Hệ quả đúng cách đọc:** độ trễ này **không làm lệch quy gán khối**, vì
`ts_utc` là `timestampUsec` của YouTube chứ không phải giờ nhận. Nhưng:
bảng điều khiển của operator chậm ~25 s, và **runner phải chạy quá khối cuối ít
nhất 1 phút** nếu không sẽ mất đuôi dữ liệu.

**(C) Số người xem đồng thời**

`extract_info(..., process=False)` → `concurrent_view_count`:
`863 → 892 → 890 → 908` (cách nhau 20 s) rồi `1008 → 1141` ở lần chạy sau. Số
thật, có biến thiên.

| | Thời gian |
|---|---|
| Lần gọi đầu của một tiến trình *lạnh* | **37,7 s** (nạp cache player JS) |
| Các lần sau | **1,7 s** |
| Tiến trình mới sau khi cache đã có | **1,76 s** (cache nằm trên đĩa, dùng lại được) |

**Cảnh báo cấu hình đã kiểm chứng:** thêm
`extractor_args={"youtube": {"player_skip": [...], "skip": [...]}}` để "cho
nhẹ" làm YouTube trả **"Sign in to confirm you're not a bot"** trong khi lệnh
mặc định chạy bình thường ở cùng thời điểm. **Không tối ưu kiểu đó.**

**(D) Chạy thật toàn tuyến** (`YouTubeYtdlpClient` thật → `ApiSink` thật →
`MockTransport`), 200 giây:

```
comments parsed+posted : 104
viewer ticks           : 7 -> [1008, 1018, 1058, 1062, 1101, 1092, 1141]
last_error             : None
payload keys           : ['ext_id', 'pii_kinds', 'platform', 'text', 'ts_utc', 'viewers']
```

Không có trường tác giả nào trong payload; văn bản đã qua `scrub()`.

**(E) Luồng bán hàng tiếng Việt vắng khách** (`3jVRnXtVvps`, 1 người xem):
0 bình luận/120 s nhưng vẫn có 4 tick người xem. Đường đi đúng, phòng chat rỗng
— kiểm chứng kỹ thuật phải dùng phòng đông.

**(F) Đúng câu lệnh trong runbook, qua CLI thật** (`python -m
livelift.ingest.runner` với `INGEST_YOUTUBE_BACKEND=ytdlp`, gửi HTTP thật vào
một sink tạm), 110 giây:

```
RESULT comments=73 ticks=4
comment payload keys: ['ext_id', 'pii_kinds', 'platform', 'text', 'ts_utc']
author leak: False
tick viewers: [1028.0, 1030.0, 1052.0, 1026.0]
```

Runner in đúng cảnh báo ToS tiếng Việt ở dòng đầu khi chọn backend này.

## 3. Cái bẫy Windows (đã đo, ảnh hưởng thiết kế)

yt-dlp ghi vào `<id>.live_chat.json.part` rồi **đổi tên** khi luồng kết thúc.
Nếu bộ đọc **giữ file mở**, đổi tên thất bại:

| Cách tail | Kết quả thật |
|---|---|
| Mở một lần rồi giữ | `ERROR: Unable to rename file: [WinError 32]`, thử lại 3 lần rồi **rc=1**, file `.part` ở lại |
| Mở → đọc → **đóng** mỗi vòng | **rc=0**, đổi tên thành công, đọc đủ 3596/3596 ký tự |

Vì vậy `_read_new_bytes` mở/đọc/đóng mỗi nhịp, theo dõi offset **byte** (nên
offset vẫn đúng sau khi đổi tên, và ký tự UTF-8 bị cắt giữa hai lần đọc vẫn an
toàn vì chỉ dòng trọn vẹn mới được giải mã). Và `classify_exit` coi
`"Unable to rename file"` là **kết thúc sạch**, không phải lỗi để chạy lại.

## 4. Lỗi thật đã gặp và cách xử lý trong adapter

| Hiện tượng | Phân loại | Hành vi |
|---|---|---|
| rc=0 | `ended` | dừng vòng, `last_error=None` |
| "Unable to rename file" | `ended` | như trên (dữ liệu đã trên đĩa) |
| "Sign in to confirm you're not a bot" | `blocked` | ngủ 60 s, giữ tiến trình sống, báo `YTDLP_COOKIES_FROM_BROWSER` trong mọi heartbeat |
| "Video unavailable" / "Private video" | `fatal` | raise ngay, không quay vòng vô ích |
| "This live event will begin in…" | `wait` | chạy lại có backoff → **khởi động runner từ T−2h vẫn đúng**, nó tự bắt được khi luồng lên sóng |
| 503/429/mạng đứt | `retry` | backoff mũ 5→60 s, chạy lại |

Khi chạy lại, YouTube phát lại phần chat tồn đọng → adapter khử trùng lặp theo
`ext_id` (hàng đợi 5000 id) *và* server vẫn idempotent theo `(platform, ext_id)`,
nên **khởi động lại tự vá luôn khoảng trống dữ liệu**.

## 5. Riêng tư — điểm phải canh

File của yt-dlp **chứa `authorName` và `authorExternalChannelId`**, tức bình
luận thô có danh tính. Xử lý:

- file nằm trong thư mục tạm riêng, **không bao giờ dưới `data/`**;
- parser chỉ đọc `id`, `timestampUsec`, `message.runs` — không chạm trường tác giả;
- `ApiSink` scrub trước khi truyền, đúng như đường API.

**Một lỗi thật đã phát hiện nhờ chạy live và đã sửa:** khi runner hủy tác vụ
bơm bình luận, `CancelledError` nổ ở phía *tiêu thụ*, async generator chỉ bị
treo lơ lửng nên `finally` của nó **không chạy** — kết quả đo được: một tiến
trình yt-dlp vẫn tải tiếp và **182 KB chat thô còn nguyên trên đĩa** sau khi
chạy xong. `aclose()` bây giờ tự giết tiến trình đang theo dõi rồi mới xóa thư
mục (có retry, vì Windows còn khóa file một nhịp sau khi tiến trình chết), và
log đỏ nếu vẫn xóa không được. Chạy lại sau khi sửa: **0 thư mục sót**.
Có test hồi quy: `test_aclose_kills_an_abandoned_download_and_deletes_raw_chat`.

**Lỗi thật thứ hai, phát hiện khi chạy CLI:** nếu tiến trình runner bị **giết
cứng** (`timeout`, `kill -9`, container bị kill) thì Python không chạy được
dòng dọn dẹp nào — đo được **121 KB chat thô kèm tên người bình luận nằm lại
trong thư mục tạm**. Ctrl+C thì không sao (có `finally` → `aclose()`), nhưng
kill cứng thì không cứu được từ bên trong. Xử lý: `sweep_stale_temp_dirs()`
chạy khi khởi tạo client, xóa mọi thư mục `livelift-ytchat-*` **không được ghi
trong 30 phút** — ngưỡng này đủ để **không bao giờ** đụng vào phiên đang chạy
song song (phiên sống ghi file mỗi ~10 s). Đã kiểm chứng trên đúng thư mục sót
thật: gọi với đồng hồ hiện tại → không xóa (0); gọi như thể 40 phút sau → xóa
(1). Test: `test_startup_sweeps_raw_chat_left_by_a_hard_killed_run`.

## 6. Điều khoản dịch vụ — nói thẳng

Đây là lý do đường này **không được** trở thành mặc định.

- **ToS YouTube** (https://www.youtube.com/t/terms, tra ngày 09/09/2026) cấm
  "truy cập Dịch vụ bằng bất kỳ phương thức tự động nào (như rô bốt, mạng
  botnet hoặc chương trình tự động thu thập dữ liệu)", chỉ trừ "(a) trong
  trường hợp công cụ tìm kiếm công khai, **theo tệp robot.txt của YouTube**;
  hoặc (b) được YouTube cho phép trước bằng văn bản".
- **robots.txt của YouTube** (tra cùng ngày) `Disallow:` cả **`/live_chat`** và
  **`/youtubei/`** — đúng hai đường mà `YoutubeLiveChatFD` gọi
  (`https://www.youtube.com/live_chat?continuation=…` và
  `https://www.youtube.com/youtubei/v1/live_chat/get_live_chat`, xem mã nguồn
  dòng 161–166). Nên ngoại lệ robots.txt **không che được chúng ta**.

Nói cho đúng mức: ta **không** tải video, **không** đọc dữ liệu riêng tư,
**không** phát tán chat, và dữ liệu đều là nội dung công khai. Nhưng *phương
thức truy cập* thì không được YouTube cho phép. Vậy nên:

1. **Đường chuẩn là xin `YOUTUBE_API_KEY`** — miễn phí, không cần thẻ, không
   cần app review, ~10 phút trong Google Cloud Console. Rào cản hiện tại chỉ là
   chưa ai tạo project, không phải tiền hay xét duyệt.
2. Dùng yt-dlp cho: **phiên của chính nhóm**, kiểm thử kỹ thuật, và **dự phòng
   khi key chết giữa phiên**. Không dùng để quét hàng loạt phiên của người khác.
3. Nếu dữ liệu thu bằng đường này đi vào bài báo, **phải khai báo phương pháp
   thu thập** trong mục phương pháp/đạo đức. Không được trình bày như dữ liệu API.

Runner đã in cảnh báo tiếng Việt đúng nội dung này mỗi lần chọn backend `ytdlp`.

## 7. So sánh hai đường

| Tiêu chí | `INGEST_YOUTUBE_BACKEND=api` | `=ytdlp` |
|---|---|---|
| Credential | Cần `YOUTUBE_API_KEY` | Không cần |
| Quota | 10.000 đơn vị/ngày; `liveChatMessages.list` ~5 đv/lần → phiên 90 phút poll 5 s ≈ 5.400 đv (**quá nửa ngày**) | Không có quota |
| Độ trễ giao tin | Theo `pollingIntervalMillis`, thường **2–5 s** | **~24 s (p50), 37 s (p90)** |
| Số người xem | `concurrentViewers` (cùng lệnh `videos.list`, 1 đv) | `concurrent_view_count`, ~1,7 s/lần |
| Chat tồn đọng lúc nối | Không | ~5 phút, có dấu thời gian đúng (khử trùng lặp được) |
| Ổn định | Lỗi HTTP rõ ràng, xử lý theo mã | Phụ thuộc tiến trình con + đổi tên file; phải chạy lại khi rớt |
| Chống bot | Không | Có thể dính, cần `YTDLP_COOKIES_FROM_BROWSER` |
| ToS | **Hợp lệ** | **Không hợp lệ** (§6) |
| Chạy được hôm nay | Không (chưa có key) | Có |

**Khuyến nghị:** xin key ngay; chạy phiên thí nghiệm chính thức trên `api`.
Giữ `ytdlp` làm đường dự phòng và để kiểm thử kỹ thuật trong lúc chờ key —
và ghi rõ đã dùng đường nào cho từng phiên trong nhật ký phiên.

## 8. Tái lập

```bash
# tìm luồng đang phát (bộ lọc "Trực tiếp" của YouTube)
yt-dlp --flat-playlist --print "%(id)s|%(title).50s|%(concurrent_view_count)s" \
  "https://www.youtube.com/results?search_query=<từ+khóa>&sp=EgJAAQ%253D%253D" --playlist-end 10

# xác nhận đang live + có chat trực tiếp
yt-dlp --skip-download --print "%(live_status)s|%(concurrent_view_count)s|%(subtitles.live_chat.0.protocol)s" \
  "https://www.youtube.com/watch?v=<VIDEO_ID>"     # kỳ vọng: is_live|<số>|youtube_live_chat

# chạy ingest thật, không cần key
INGEST_YOUTUBE_BACKEND=ytdlp python -m livelift.ingest.runner \
  --platform youtube --source-id <VIDEO_ID> --session-id <session_id> --api-url http://localhost:8000
```

Mã: `src/livelift/ingest/youtube_ytdlp.py` · Test:
`tests/test_ingest_youtube_ytdlp.py` (44 test, chạy không cần mạng) · Fixture
`tests/data/live_chat_live_fixture.jsonl` là dòng chat **thật** đã thay danh
tính bằng placeholder và cho văn bản qua `scrub()` trước khi đưa vào repo.
