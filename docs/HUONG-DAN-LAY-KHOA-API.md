# Hướng dẫn lấy khoá API các nền tảng cho LiveLift

*Cập nhật 17/09/2026. Viết cho đội LiveLift: phần "Bấm gì" làm được mà không cần biết lập trình,
phần "Điền vào LiveLift" nhờ người giữ máy chủ làm. Mọi khẳng định về API có nguồn trong
`docs/research/2026-09-17-nen-tang-livestream-va-serpapi.md` và `docs/nen-tang-ho-tro.md`.*

---

## 0. Đọc trước

### 0.1 Nguyên tắc: chỉ đi đường chính thức

LiveLift chỉ đọc dữ liệu livestream qua **API chính thức của nền tảng**, và chỉ trên **tài khoản của
chính nhóm** hoặc của **đối tác có văn bản đồng ý**.

> **Quyết định 17/09/2026 — không làm cách "đọc như người xem".** LiveLift **không** thu bình luận
> bằng cách giả làm người xem buổi live: không tiện ích trình duyệt đọc khung bình luận, không
> Playwright/Selenium mở trang live, không WebSocket dịch ngược (kiểu TikTokLive, Euler Stream), không
> chụp màn hình rồi nhận dạng chữ, không dịch vụ cào dữ liệu trả phí. Bốn lý do:
>
> 1. **Điều khoản nền tảng.** TikTok và Meta đều cấm thu thập dữ liệu bằng công cụ tự động khi chưa
>    được phép. Người xem đọc bình luận rồi thôi; LiveLift chép, lưu và phân tích hàng nghìn bình luận
>    — đó là thu thập tự động.
> 2. **Dữ liệu cá nhân.** Bình luận gắn với tên và lời nói của người thật. Luật Bảo vệ dữ liệu cá nhân
>    91/2025/QH15 và Nghị định 356/2025/NĐ-CP đòi hỏi căn cứ để xử lý; buổi live của người lạ thì nhóm
>    không có căn cứ nào.
> 3. **Liêm chính.** Kho mã công khai, cuộc thi chấm tính trung thực của dữ liệu. Một nguồn cào không
>    chính thức là điểm phản biện yếu nhất có thể có.
> 4. **Độ bền.** Đường không chính thức hỏng khi nền tảng đổi giao diện hay giao thức; nhóm đã đo
>    TikTok bị chặn 10/10 lần.
>
> Các đường không chính thức cũ còn trong kho (bộ đo TikTok cách ly ở `collectors/tiktok_public/`,
> backend `INGEST_YOUTUBE_BACKEND=ytdlp`) **không dùng cho buổi live thật** và không đưa số liệu vào hồ
> sơ. Việc giữ hay gỡ chúng nằm trong `docs/VIEC-CAN-LAM.md`.

### 0.2 Nền tảng nào lấy được gì

| Nền tảng | Cần lấy | Thời gian | LiveLift đọc được | Trạng thái |
|---|---|---|---|---|
| **YouTube Live** | API key | ~10 phút | Bình luận, người xem đồng thời, của **mọi** buổi live công khai | Bộ nối có sẵn, **chưa chạy với key thật** |
| **Facebook Live** | Page access token | ~25 phút | Bình luận, người xem của **Fanpage mình quản trị** | Bộ nối có sẵn, **chưa chạy với token thật** |
| **Shopee Live** | Tài khoản Open Platform + ủy quyền | vài ngày duyệt | Bình luận, người xem, **GMV/đơn/thêm giỏ**, ghim sản phẩm qua API | Bộ nối có sẵn, **chưa có cuộc gọi thật**; vùng Việt Nam cần xác minh |
| **TikTok Shop** | Tài khoản Partner Center + app | vài ngày duyệt | Số liệu phiên LIVE **theo phút, sau khi kết thúc** (GMV, đơn, click, số bình luận) — **không** có nội dung bình luận | Bộ nối hậu kiểm **đã có** (`src/livelift/ingest/tiktok_shop.py`, chưa nối bộ thu, **chưa chạy với khoá thật**); hôm nay dùng được nhập đơn CSV |
| **TikTok LIVE thường** | — | — | Không có API chính thức | **Không làm** |
| **Live của người khác** (Facebook, TikTok) | — | — | Không đọc được nếu họ không cấp quyền | **Không làm** |
| **Lazada, Instagram** | — | — | Chưa xác minh / cần App Review | Để sau |

### 0.3 Khoá là mật khẩu

- Chỉ để khoá trong tệp **`.env`** ở thư mục `livelift/` — tệp này đã bị `.gitignore` chặn, **không bao
  giờ** lên GitHub.
- **Không** dán khoá vào chat nhóm, email, ảnh chụp màn hình, tài liệu, issue hay PR.
- Mỗi người giữ khoá ghi vào trình quản lý mật khẩu (Bitwarden, 1Password…), không ghi giấy.
- **Lộ khoá thì thu hồi ngay** theo mục "Nếu lộ" của từng nền tảng, rồi cấp khoá mới.

---

## 1. Điền khoá vào LiveLift và kiểm tra (dùng chung cho mọi nền tảng)

1. Mở tệp `livelift/.env`. Chưa có thì chép từ `.env.example` rồi đổi tên.
2. Điền đúng tên biến ở mục của từng nền tảng bên dưới. Không thêm dấu ngoặc kép, không để dấu cách
   hai bên dấu `=`.
3. Chạy máy cục bộ thì **để trống** `INGEST_TOKEN` — giao diện web hiện chưa gửi được token, đặt token
   thì nút "Bật bộ thu" và nhập đơn bị máy chủ từ chối.
4. **Khởi động lại máy chủ** (máy chủ chỉ đọc `.env` lúc khởi động):

   ```powershell
   .venv\Scripts\python scripts\chay_local.py
   ```

5. Kiểm tra trên giao diện: trang chủ → thẻ **01** → **"Trả lời 3 câu hỏi →"** → khối **"Máy chủ này thu
   được bình luận từ đâu"**. Nền tảng vừa điền phải ghi **Sẵn sàng**. Còn thiếu thì dòng đó ghi tên
   biến chưa có — máy chủ **không bao giờ** hiện giá trị khoá.
6. Hoặc kiểm tra bằng lệnh:

   ```powershell
   curl.exe -s http://localhost:8000/platforms
   ```

---

## 2. YouTube — API key (Data API v3)

### 2.1 Cần chuẩn bị

- Một tài khoản Google của nhóm (nên bật xác minh 2 bước).
- Không cần thẻ thanh toán: YouTube Data API v3 miễn phí trong hạn mức mặc định.

### 2.2 Bấm gì

1. Vào <https://console.cloud.google.com> và đăng nhập.
2. Thanh trên cùng → ô chọn dự án → **New project** → đặt tên `LiveLift` → **Create**. Chờ vài giây rồi
   chọn đúng dự án vừa tạo.
3. Menu trái → **APIs & Services → Library** → tìm **YouTube Data API v3** → **Enable**.
4. Menu trái → **APIs & Services → Credentials** → **Create credentials → API key**. Chép chuỗi bắt đầu
   bằng `AIza…`.
5. Bấm vào tên key vừa tạo để giới hạn nó:
   - **API restrictions → Restrict key** → chỉ tick **YouTube Data API v3**.
   - **Application restrictions**: để **None** khi chạy trên laptop; khi có máy chủ công khai thì chọn
     **IP addresses** và điền IP máy chủ.
   - **Save**.

### 2.3 Điền vào LiveLift

```dotenv
YOUTUBE_API_KEY=AIza...
INGEST_YOUTUBE_BACKEND=api
```

Khởi động lại máy chủ và kiểm tra theo mục 1. Dòng YouTube Live phải ghi **Sẵn sàng**.

Rồi chạy lệnh kiểm tra. Lệnh chỉ đọc, không in khoá và không in nội dung bình luận:

```powershell
# Ngay sau khi điền key: kiểm key hợp lệ và API đã bật (1 đơn vị quota)
.venv\Scripts\python scripts\kiem_tra_youtube.py

# Khi đang phát thử: kiểm thêm trạng thái live, người xem, đọc thử một trang chat (2–6 đơn vị)
.venv\Scripts\python scripts\kiem_tra_youtube.py --video https://www.youtube.com/live/<ID>
```

Đọc kết quả:

- Dòng cuối phải ghi `KẾT LUẬN: SẴN SÀNG` (mã thoát 0). `CHƯA SẴN SÀNG` (mã thoát 1) luôn kèm dòng
  **Cách sửa**.
- Mục 2 gọi tên đúng lỗi: key sai, dự án chưa bật API, key bị giới hạn, hết hạn mức.
- Mục 4 chỉ in **số lượng** và **loại** tin nhắn (`textMessageEvent`, `superChatEvent`…), không in chữ
  hay tên người xem.
- Mục 5 ước lượng hạn mức cho **thời gian chờ lên sóng** cộng **buổi live**. Mặc định bộ thu bật trước
  giờ phát 120 phút theo mốc T−2h (đổi bằng `--cho-truoc-phut`, `0` là bật đúng lúc phát) và buổi dài 90
  phút (đổi bằng `--thoi-luong-phut`). Mọi cảnh báo tính theo **trường hợp tốn nhất**: bộ thu đọc chat
  2 giây một lượt. Dòng "Nhịp lúc thử" in `pollingIntervalMillis` đo ở mục 4 **chỉ để tham khảo**. Đó là
  nhịp của một trang lúc phát thử, khi chat thường vắng. Google trả trường này ở từng trang và tài liệu
  không nói nó cố định, nên đừng dựa vào con số này để yên tâm về hạn mức (xem mục 2.4).

### 2.4 Hạn mức — đọc trước buổi live dài

- Mặc định **10.000 đơn vị/ngày** cho mỗi dự án. Hạn mức đặt lại lúc nửa đêm giờ Thái Bình Dương,
  tức 14:00 giờ Việt Nam khi bên đó dùng giờ mùa hè và 15:00 khi dùng giờ mùa đông. API không trả số
  còn lại; xem ở **APIs & Services → YouTube Data API v3 → Quotas**. Nguồn:
  <https://developers.google.com/youtube/v3/determine_quota_cost> (cập nhật 15/09/2026, truy cập
  17/09/2026).
- **Chưa chốt giá của một lượt đọc chat.** Bảng giá chính thức ghi `liveChatMessages.list` = **1 đơn
  vị** (cùng nguồn trên). Một dự án mã nguồn mở lại tính theo **5 đơn vị**. Log thật của họ cho thấy
  hạn mức cạn sau khoảng 47 phút khi đọc chat theo đúng `pollingIntervalMillis`; từ giá 5 đơn vị, họ suy
  ra nhịp đọc khoảng 1,41 giây (<https://github.com/clear-bg/NSS-Result-Tracker/pull/420>, gộp
  09/09/2026, truy cập 17/09/2026).
- Bộ thu đọc chat theo nhịp `pollingIntervalMillis` Google trả về, nhưng **không nhanh hơn 2 giây một
  lượt**, và đọc số người xem mỗi 30 giây. Tính hạn mức theo đúng 2 giây, không theo nhịp đo lúc phát
  thử. Trang `liveChatMessages.list` chỉ ghi `pollingIntervalMillis` là *"The amount of time, in
  milliseconds, that the client should wait before polling again for new live chat messages"*. Trang này
  không nói nhịp đó cố định
  (<https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list>, cập nhật 14/09/2026, truy
  cập 17/09/2026). Nhịp 1,41 giây ở dự án trên cũng nhanh hơn mức sàn 2 giây của bộ thu.
- **Bật bộ thu trước giờ phát cũng tốn hạn mức.** Khi trạng thái là *Chờ buổi live bắt đầu*, cứ 20 giây
  bộ thu dò lại một vòng. Mỗi vòng tốn tối đa 2 lượt `videos.list`: một lượt tìm phòng chat, một lượt đọc
  số người xem. Vậy là khoảng **6 đơn vị/phút**. Bật ở mốc T−2h thì tốn khoảng **720 đơn vị** trước khi
  lên sóng. Lượt dò nào cũng bị tính: *"Every API request, even if invalid, will cost at least one quota
  point"* (<https://developers.google.com/youtube/v3/determine_quota_cost>, cập nhật 15/09/2026, truy cập
  17/09/2026).
- Trường hợp tốn nhất cho buổi 90 phút là 2.700 lượt đọc chat, 181 lượt `videos.list` trong buổi, cộng
  lượt dò lúc chờ:

  | Giá một lượt đọc chat | Bật bộ thu đúng lúc phát | Bật ở T−2h (chờ 120 phút, +720) |
  |---|---|---|
  | 1 (bảng chính thức) | 2.881 đơn vị = 29% | 3.601 đơn vị = 36% |
  | 5 (quan sát cộng đồng) | 13.681 đơn vị — **vượt** | 14.401 đơn vị — **vượt** |

  Khi vượt, bộ thu gặp lỗi hết hạn mức giữa buổi. Muốn giảm phần chờ: dùng lệnh kiểm tra ở mục 2.3 để
  kiểm key từ sớm, rồi bật bộ thu gần giờ phát.
- **Rủi ro chưa đo.** Tài liệu `videos` ghi `activeLiveChatId` *"is filled only if the video is a
  currently live broadcast that has live chat"*
  (<https://developers.google.com/youtube/v3/docs/videos>, cập nhật 14/09/2026, truy cập 17/09/2026). Nếu
  thực tế YouTube cấp mã này sớm cho buổi đã lên lịch, bộ thu sẽ đọc chat suốt thời gian chờ, nhanh nhất
  2 giây một lượt. Chờ 120 phút như vậy tốn thêm tới 3.600 lượt đọc chat. Để kiểm, chạy lệnh ở mục 2.3 với
  `--video` khi buổi còn *Sắp phát*. Mục 3 ghi `activeLiveChatId: có` thì lệnh sẽ cảnh báo. Ghi kết quả
  vào nhật ký buổi thử.
- Sau buổi phát thử, **đọc số thật** ở **Metrics/Quotas** để chốt giá 1 hay 5. Nếu là 5: rút ngắn buổi,
  dùng một dự án Google Cloud riêng cho buổi live, hoặc xin tăng hạn mức ở trang **Quotas**.
- Chạy từ 2 buổi live dài trong cùng một ngày thì xin tăng hạn mức ở trang **Quotas**.

### 2.5 Điều kiện để kênh của nhóm phát live

- Xác minh kênh bằng số điện thoại tại <https://www.youtube.com/verify>.
- Lần đầu bật phát trực tiếp có thể phải **chờ tới 24 giờ**.
- Phát bằng **máy tính** (webcam hoặc OBS) không cần số người đăng ký tối thiểu; phát bằng **điện thoại**
  cần từ **50 người đăng ký**.
- Kênh không bị hạn chế phát trực tiếp trong 90 ngày gần nhất.

### 2.6 Lỗi thường gặp

Gặp lỗi nào thì chạy `scripts\kiem_tra_youtube.py` trước: lệnh đọc lý do cụ thể Google gửi kèm, còn
thông báo của bộ thu thì gộp nhiều lỗi làm một.

| Bộ thu báo | Nghĩa là | Làm gì |
|---|---|---|
| *API key không hợp lệ hoặc quota trong ngày đã cạn* | Google từ chối với mã 401/403: chưa bật API, key bị giới hạn, hết hạn mức, hoặc chat đã đóng | Chạy lệnh kiểm tra để biết đúng lý do |
| *Không lấy được activeLiveChatId … (lỗi mạng/API tạm thời)* | Mạng chập chờn, **hoặc key sai**: key sai hiện trả mã 400 nên bộ thu tưởng là lỗi tạm thời | Chạy lệnh kiểm tra; mục 2 ghi `API_KEY_INVALID` thì chép lại key |
| *Chờ buổi live bắt đầu* | Video chưa phát hoặc đã kết thúc | Bấm phát trên YouTube; bộ thu tự dò lại. Mỗi phút chờ tốn khoảng 6 đơn vị quota (mục 2.4) |
| *Không nhận ra video YouTube* | Dán link kênh thay vì link video | Dán link dạng `youtube.com/watch?v=…` hoặc `youtube.com/live/…` |

Tên lỗi Google trả về: <https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list>
(mục Errors, cập nhật 14/09/2026) và <https://developers.google.com/youtube/v3/docs/core_errors>
(cập nhật 20/08/2025), truy cập 17/09/2026. Với key sai, Google hiện trả `badRequest` kèm
`API_KEY_INVALID`, không phải `keyInvalid` như bảng core_errors. Nhóm đo điều này ngày 17/09/2026 bằng
một key giả.

### 2.7 Video "Không công khai" có đọc được bằng API key không?

**Chưa có câu trả lời chính thức, nên phải đo trong buổi phát thử.** Tra cứu ngày 17/09/2026 cho kết quả
như sau:

- **Thông tin video:** tài liệu `videos` (mục `snippet.publishedAt`) ghi về video tải lên ở chế độ
  không công khai: *"anyone who knows the video's unique video ID can retrieve the video metadata"*.
  Câu này nói về video tải lên, chưa chắc áp dụng cho buổi live. Nguồn:
  <https://developers.google.com/youtube/v3/docs/videos> (cập nhật 14/09/2026).
- **Chat:** không trang nào của Google nói API key đọc được hay không đọc được chat của video không công
  khai. Trang `liveChatMessages.list` không có mục yêu cầu đăng nhập. Hướng dẫn Streaming Live Chat
  ghi *"You can use an OAuth 2.0 access token or an API key"*. Hai điều này nghiêng về "đọc được" nhưng
  chưa phải bằng chứng. Nguồn: <https://developers.google.com/youtube/v3/live/docs/liveChatMessages/list>,
  <https://developers.google.com/youtube/v3/live/streaming-live-chat> (cập nhật 14/09/2026).
- **Video Riêng tư:** đừng dùng. Tài liệu `videos` chỉ nói **chủ kênh** đọc được thông tin video riêng
  tư, còn LiveLift đọc bằng API key.
- **Video chưa phát:** tài liệu ghi `activeLiveChatId` *"is filled only if the video is a currently
  live broadcast that has live chat"*, nên chỉ đọc thử chat được **sau khi đã bấm phát** (cùng nguồn
  `videos`).

Cách đo, khoảng 5 phút trong buổi phát thử:

1. Phát live ở chế độ **Không công khai** và tự gửi một bình luận.
2. Chạy `.venv\Scripts\python scripts\kiem_tra_youtube.py --video <link buổi live>`.
3. **Đạt** khi dòng "Kết quả" ở mục 4 ghi **OK**. Nếu mục 3 ghi chế độ **Không công khai (unlisted)**,
   lệnh in thêm dòng **"ĐÃ ĐO: API key đọc được chat của video Không công khai"**. Nếu mục 3 ghi
   **Google không trả**, tự đối chiếu chế độ trong YouTube Studio.
4. **Không đạt** khi mục 3 ghi **Tìm thấy: KHÔNG** hoặc mục 4 báo lỗi `forbidden`. Khi đó chuyển các buổi
   live sang **Công khai**.
5. Ghi kết quả vào `ops/templates/nhat-ky-phien.md`. Chưa đo xong thì hồ sơ **không** được viết "API key
   đọc được video không công khai".

**Nếu lộ key:** Credentials → bấm key → **Delete** (hoặc **Regenerate key**) → điền key mới vào `.env`.

---

## 3. Facebook — Page access token

Hướng dẫn chi tiết từng màn hình, kèm cách đọc kết quả kiểm tra: **[huong-dan-facebook-token.md](huong-dan-facebook-token.md)**.
Tóm tắt các bước:

### 3.1 Cần chuẩn bị

- Một **Fanpage** mà chính bạn là **quản trị viên**. Trang cá nhân **không** dùng được.
- Tài khoản Facebook cá nhân của quản trị viên, đã bật xác thực 2 lớp.

### 3.2 Bấm gì

1. Vào <https://developers.facebook.com/apps> → **Tạo ứng dụng** → trường hợp sử dụng **Khác** → loại
   **Doanh nghiệp** → đặt tên `LiveLift Live Lab`.
2. Để nguyên **chế độ Phát triển**. Đọc Page của chính mình **không cần App Review**.
3. Mở **Graph API Explorer** (<https://developers.facebook.com/tools/explorer/>) → chọn app vừa tạo →
   **User Token** → **Thêm quyền** đủ ba quyền:
   - `pages_show_list`
   - `pages_read_engagement` — **bắt buộc**, đọc video live và số người xem
   - `pages_read_user_content` — **bắt buộc**, đọc bình luận của người xem. Thiếu quyền này, bộ thu đọc
     được **0 bình luận mà không báo lỗi**.
4. Bấm **Generate Access Token** → đăng nhập → chọn đúng Fanpage của nhóm.
5. Đổi sang token dài hạn: mở <https://developers.facebook.com/tools/debug/accesstoken>, dán token →
   **Debug** → **Extend Access Token**.
6. Lấy Page token: mở trên trình duyệt (thay token dài hạn vào cuối):

   ```
   https://graph.facebook.com/v25.0/me/accounts?fields=id,name,access_token&access_token=<TOKEN_DAI_HAN>
   ```

   Lấy `id` và `access_token` của **đúng Fanpage**.

### 3.3 Điền vào LiveLift

```dotenv
FACEBOOK_PAGE_ID=1234567890
FACEBOOK_PAGE_ACCESS_TOKEN=EAAG...
FACEBOOK_GRAPH_VERSION=v25.0
```

Khởi động lại máy chủ, rồi chạy lệnh kiểm tra — kết quả phải là `KẾT LUẬN: SẴN SÀNG`:

```powershell
.venv\Scripts\python scripts\kiem_tra_facebook.py
```

Trên web, bộ thu Facebook **để trống ô nguồn**: LiveLift tự tìm buổi đang phát trên Page, và tự dò lại
nếu host tắt rồi phát lại.

### 3.4 Điều kiện và giới hạn

- Phát live qua OBS hay phần mềm khác: tài khoản Facebook **từ 60 ngày tuổi** và Page **từ 100 người
  theo dõi**.
- Hạn mức gọi API tính theo số người tương tác với Page trong 24 giờ; Page mới, ít tương tác dễ chạm
  trần trong buổi live dài. `kiem_tra_facebook.py` mục 5 phải dưới 50% trước buổi live.
- Page token hết hiệu lực khi đổi mật khẩu Facebook, gỡ app, mất quyền quản trị Page, hoặc khoảng 90
  ngày không dùng. Chạy lệnh kiểm tra **mỗi tuần một lần**.
- Đọc Page của **đối tác** cần họ cấp quyền, **Business Verification** và **App Review** cho hai quyền
  đọc — dự trù **4–6 tuần**.

**Nếu lộ token:** đổi mật khẩu Facebook của quản trị viên (token cũ chết ngay), vào app → **Cài đặt →
Cơ bản → Đặt lại khoá bí mật**, rồi làm lại từ bước 3.

---

## 4. Shopee Live — Shopee Open Platform

> Đường **sạch nhất và giàu tín hiệu nhất**: bình luận, người xem, GMV, đơn, thêm giỏ và ghim sản phẩm
> đều qua API chính thức. Nhưng **chưa có cuộc gọi thật nào**, và tài liệu Shopee ghi có Việt Nam trong
> khi một SDK cộng đồng ghi không — chỉ tài khoản thật mới chốt được.

### 4.1 Cần chuẩn bị

- Một **shop Shopee Việt Nam** đang hoạt động, và tài khoản **người phát live** của shop.
- Giấy tờ đăng ký tài khoản nhà phát triển theo yêu cầu của Shopee (cá nhân hoặc doanh nghiệp).

### 4.2 Bấm gì

1. Đọc hướng dẫn đăng ký chính thức của Shopee cho người bán Việt Nam:
   <https://banhang.shopee.vn/edu/article/8450>.
2. Đăng ký tài khoản nhà phát triển tại <https://open.shopee.com>, chờ Shopee duyệt.
3. Trong Console của Open Platform, tạo app. Ghi lại **Partner ID** và **Partner Key**. Nếu Console cấp
   riêng một cặp cho môi trường thử nghiệm (sandbox), LiveLift dùng cặp của môi trường **thật**.
4. Xin quyền cho app dùng nhóm API **Livestream** (module livestream). Các API này là loại **"User"**:
   ký bằng mã **người phát**, không phải mã shop.
5. Chạy luồng **ủy quyền**: chủ tài khoản người phát đăng nhập và đồng ý cấp quyền cho app, Shopee trả
   về một `code`. Đổi `code` lấy token theo tài liệu
   <https://open.shopee.com/documents/v2/v2.public.get_access_token?module=104&type=1>. Phản hồi có:
   - `access_token` — chỉ sống **4 giờ**;
   - `refresh_token` — sống 30 ngày, **mỗi lần làm mới chỉ dùng được một lần**;
   - `user_id_list` — mã người phát, điền vào `SHOPEE_USER_ID`;
   - `shop_id_list` — mã shop, chỉ cần khi ghim sản phẩm.

   LiveLift **chưa có** trang tự làm luồng ủy quyền này; người kỹ thuật làm theo tài liệu Shopee.

### 4.3 Điền vào LiveLift

```dotenv
SHOPEE_PARTNER_ID=2001234
SHOPEE_PARTNER_KEY=...
SHOPEE_USER_ID=880011
SHOPEE_ACCESS_TOKEN=...
SHOPEE_REFRESH_TOKEN=...
SHOPEE_SHOP_ID=77001
SHOPEE_REGION=global
```

Bốn biến **bắt buộc** để đọc bình luận: `SHOPEE_PARTNER_ID`, `SHOPEE_PARTNER_KEY`, `SHOPEE_USER_ID`,
`SHOPEE_ACCESS_TOKEN`. Việt Nam dùng cổng `global`.

Kiểm tra với một buổi live có `session_id` thật:

```powershell
.venv\Scripts\python scripts\kiem_tra_shopee.py --session-id <SESSION_ID>
```

Shopee có chế độ **phiên thử** chính thức (`is_test` khi tạo phiên) — dùng nó cho buổi phát thử đầu tiên.

### 4.4 Giới hạn

- **Token 4 giờ** và LiveLift **chưa tự làm mới**: buổi live dài hơn thì người kỹ thuật cấp token mới
  giữa chừng rồi khởi động lại máy chủ.
- Bình luận chỉ lấy được trong **cửa sổ 10 giây gần nhất**; bộ thu poll mỗi 5 giây, máy chủ bận quá lâu
  là mất bình luận.
- Chỉ số GMV/đơn là **số cộng dồn**; số theo từng khối thí nghiệm là hiệu giữa hai mốc.
- Nếu tài khoản bị báo *"not supported for current region"*, vùng Việt Nam chưa được cấp API livestream;
  khi đó dùng xuất đơn CSV từ Seller Centre (mục 5.3).

**Nếu lộ Partner Key:** vào Console của app → đặt lại Partner Key → cấp lại token.

---

## 5. TikTok Shop — Partner Center (hậu kiểm LIVE theo phút)

> **Trạng thái 17/09/2026.** Bộ nối chính thức `src/livelift/ingest/tiktok_shop.py` đã có: ký yêu cầu,
> phân trang, báo lỗi tiếng Việt, gộp số liệu theo khối. Nó **chưa được nối vào bộ thu nền hay giao diện
> web**, và **chưa chạy với app/shop thật** vì nhóm chưa có tài khoản. Hôm đó nhóm gọi thử cả ba endpoint
> bằng khoá GIẢ. Cả ba đều bị chặn ở bước kiểm `app_key` (HTTP 400, mã `36009004`), còn một đường dẫn bịa
> bị chặn ở bước đường dẫn (HTTP 404, mã `36009009`). Vậy **endpoint có thật**. Nhưng TikTok chặn `app_key`
> trước khi kiểm chữ ký, nên phần ký chỉ dựa vào ví dụ chính thức mà nhóm đã tính lại khớp.
> Mọi nguồn trong mục này truy cập ngày **17/09/2026**.

### 5.1 TikTok cho gì, không cho gì

Cả ba API dưới đây dùng **token người bán** (`user_type = 0`) và gói quyền **"TikTok Shop Analytics"**
(`data.shop_analytics.public.read`).

**Phạm vi thị trường: chưa trang nào xác nhận cho cả ba.**

- Thông báo *New APIs for TikTok LIVE* (cập nhật 27/08/2025,
  <https://partner.tiktokshop.com/docv2/page/68af6771eb3a300486d0e157>) ghi *"All markets - local and
  cross-border"*, nhưng cho bản **202508** của Live Performance Overview/List. LiveLift gọi bản **202509**
  của danh sách phiên.
- Thông báo *Analytics APIs now available globally* (cập nhật 26/09/2025,
  <https://partner.tiktokshop.com/docv2/page/68d6ce2d8e2c770495cced8c>) ghi *"All existing Analytics APIs
  are now available in all markets"*, nhưng chỉ liệt kê các endpoint 202405–202409 và không nhắc
  endpoint LIVE nào. Ngày cập nhật của trang (09/2025) còn sớm hơn tên phiên bản 202510 (theo phút) và
  202512 (theo sản phẩm).

Vậy việc danh sách phiên dùng được ở Việt Nam chỉ là **suy luận** của nhóm. Với hai endpoint theo phút và
theo sản phẩm, **chưa trang nào nêu phạm vi thị trường**. Phải xác nhận bằng lời gọi thật trên một shop
Việt Nam.

| Có | Tài liệu |
|---|---|
| Danh sách phiên LIVE của shop trong một khoảng ngày | <https://partner.tiktokshop.com/docv2/page/get-shop-live-performance-list-202509> |
| Số liệu **từng phút** của một phiên: GMV, đơn, lượt bấm sản phẩm, lượt hiển thị, **số** bình luận, lượt thích, người xem. Nguyên văn: *"after the session is finished"* và *"only returns data for live streams hosted by the shop official account or marketing account"* | <https://partner.tiktokshop.com/docv2/page/get-shop-live-minute-performance-202510> |
| Số liệu theo **từng sản phẩm** của một phiên | <https://partner.tiktokshop.com/docv2/page/get-shop-live-products-performance-list-202512> |

**Không có:**

- nội dung bình luận live (chỉ có **số** bình luận mỗi phút);
- API ghim sản phẩm trong live, nên việc ghim theo lịch switchback vẫn **làm tay**;
- số liệu theo phiên **trong lúc đang phát**. Tài liệu cũng **không nói** số theo phút có sau bao lâu;
- nhóm API `live_rooms/*` (`core_stats`…): nhóm này cần token **creator** (`user_type = 1`), không phải
  token shop, nên LiveLift không dùng
  (<https://partner.tiktokshop.com/docv2/page/get-live-room-core-stats-202502>);
- đường chính thức nào cho **TikTok LIVE thường** (không phải shop).

GMV và đơn theo phút là số **quy đổi** (attributed) do TikTok tính, và GMV gồm cả hàng trả/hoàn
(<https://partner.tiktokshop.com/docv2/page/698d74de3a0ca3049812e044>). Vì vậy chúng chỉ dùng để
**đối chiếu**. Chỉ số chính của thí nghiệm vẫn là lượt bấm link đo `/r/{code}`.

### 5.2 Điều kiện và bấm gì

**Điều kiện.** Đây là chỗ khó nhất với đội sinh viên, nên đọc trước:

| Cách | Điều kiện (theo tài liệu) | Được gì |
|---|---|---|
| **A. Seller in-house developer**: app riêng của một shop | Shop TikTok Shop **đã kích hoạt, đã qua KYC/KYB và đã được gán Account Manager**. Account Manager **không đăng ký thẳng được**: *"TikTok Shop Account Managers (AMs) are not a service sellers can directly apply for in the backend"*, mà TikTok tự gán theo thị trường, ngành hàng, quy mô, hiệu quả shop. Nhưng cùng FAQ (mục 13) có đường chính thức: chủ shop vào **Help Center trong Seller Center**, chat với hỗ trợ hoặc gửi ticket, ghi rõ đang xin *"Account Manager eligibility review"*, kèm Shop ID, thị trường, ngành hàng chính, GMV và số đơn 30/90 ngày, điểm shop. Tài liệu **không hứa** sẽ được gán: giữ shop hoạt động, điểm SPS và giao hàng tốt chỉ *"generally increases your chances of being identified as a priority merchant"*, và *"these are not officially published guarantees for AM assignment"*. Phải dùng **tài khoản chủ** shop (tài khoản phụ bị từ chối). App riêng chỉ gắn được với **một** shop. | Dữ liệu thật của shop đó |
| **B. App developer (ISV)**: tài khoản đối tác của nhóm | Đăng ký đòi giấy chứng nhận doanh nghiệp, nhưng có nút **Save for later**: *"If you create an app now, you can't publish it until certification is complete."* App chưa publish thì *"You can only use test seller accounts created in Development Shop (sandbox)"*. Email/tài khoản **đã đăng ký shop** TikTok Shop thì **không** được đăng ký ISV. | Kiểm chứng ký + ủy quyền trên **shop thử**, **không** có dữ liệu LIVE thật |
| **C. Đối tác doanh nghiệp đã làm được cách A** | Shop đối tác **tự giữ** App Key/App Secret và chạy LiveLift như công cụ nội bộ của họ, kèm **thư đồng ý** ghi rõ mục đích nghiên cứu | Dữ liệu thật, đúng điều khoản |

Nguồn: <https://partner.tiktokshop.com/docv2/page/developer-onboarding> ·
<https://partner.tiktokshop.com/docv2/page/seller-developer-onboarding-onepager> (FAQ 13 về Account
Manager) ·
<https://partner.tiktokshop.com/docv2/page/64f198e74830a5028854bf8f>.

- **Shop thử (sandbox) có Việt Nam**: bảng thị trường ghi `VN (704)`, "Local: Yes". Nếu không có thông tin
  doanh nghiệp/KYC, tài liệu bảo bắt đầu bằng tài khoản **Core Function**, loại onboarding chọn được
  **Individual**. Tạo được tối đa **10** tài khoản shop thử (gộp cả hai loại Core Function và Full
  Function). Shop thử **hết hạn sau 180 ngày** nhưng kích hoạt lại được. Tài liệu **không nói** shop thử
  có phát LIVE hay có số liệu LIVE không
  (<https://partner.tiktokshop.com/docv2/page/seller-center-development-shops>).
- **Điều khoản nhà phát triển** (<https://partner.tiktokshop.com/docv2/page/6506bc942f024f02be400315>):
  giấy phép là *"personal, non-exclusive, non-transferable, non-sublicensable"*; phải có *"express
  permission"* trước khi chia sẻ dữ liệu cho bên thứ ba; cấm *"aggregate or otherwise utilize End User
  data for your own purposes"*. Hệ quả: shop đối tác **không đưa khoá cho nhóm**, và muốn đưa số liệu
  vào hồ sơ thi hay bài báo thì cần thư đồng ý.
- Trước **30/09/2026** nhóm thực tế chỉ làm được **cách B trên shop thử**, tức minh chứng kỹ thuật, không
  có số liệu thật. Hồ sơ **không được** viết là đã có dữ liệu LIVE TikTok thật.

**Bấm gì (cách A/C do người giữ shop làm; cách B do nhóm làm trên shop thử):**

1. Vào <https://partner.tiktokshop.com>. Cách A: đăng ký developer loại **Seller inhouse developer /
   TikTok Shop Seller**, liên kết shop đã kích hoạt bằng tài khoản chủ. Cách B: đăng ký **App developer**,
   chọn **Save for later** ở bước chứng nhận.
2. **App & Service** → tạo **Custom app** → bật **Enable API**. Ghi lại **App Key** và **App Secret**.
3. **App & Service → Manage API**: kiểm tra app có gói **TikTok Shop Analytics**. Đây là gói loại
   *Public*, và trang Access scope ghi app mới tạo mặc định có mọi gói Public. Nếu thiếu thì bật, rồi mới
   cho shop ủy quyền (bật sau thì shop phải ủy quyền lại)
   (<https://partner.tiktokshop.com/docv2/page/64f19916cb677b0286e76d9d>).
4. **Ủy quyền.**
   - Shop thật: chủ shop mở `https://services.tiktokshop.com/open/authorize?service_id=<service_id>` (ngoài
     Mỹ), đồng ý, và TikTok chuyển về địa chỉ redirect của app kèm `code`.
   - Shop thử: **Development Kits → Development Shops → Authorize App**.

   `code` chỉ sống **30 phút** và **dùng được một lần**
   (<https://partner.tiktokshop.com/docv2/page/authorization-overview-202407>).
5. **Đổi `code` lấy token** (người kỹ thuật làm, trên máy của mình; không dán lệnh có khoá vào chat):

   ```text
   GET https://auth.tiktok-shops.com/api/v2/token/get?app_key=<APP_KEY>&app_secret=<APP_SECRET>&auth_code=<code>&grant_type=authorized_code
   ```

   `grant_type` đúng là **`authorized_code`**, không phải `authorization_code`. Phản hồi có:
   - `access_token`, mặc định sống **7 ngày**;
   - `refresh_token`, để làm mới qua `/api/v2/token/refresh`;
   - `granted_scopes`, phải có `data.shop_analytics.public.read`.
6. **Lấy `shop_cipher`**: gọi `GET /authorization/202309/shops` (Get Authorized Shops,
   <https://partner.tiktokshop.com/docv2/page/6507ead7b99d5302be949ba9>) bằng token vừa lấy, rồi chép
   trường `cipher` của shop.

LiveLift **chưa có** lệnh làm bước 5–6; người kỹ thuật làm theo hai trang tài liệu trên.

### 5.3 Dùng được ngay hôm nay với TikTok Shop

Xuất danh sách đơn từ **TikTok Shop Seller Center** ra tệp CSV sau buổi live, rồi nhập ở trang **Báo cáo
phiên** của LiveLift. LiveLift gán mỗi đơn vào khối BẬT/TẮT theo **giờ đặt đơn** và chỉ nhận đơn nằm
trong khung giờ của phiên. Cột bắt buộc: thời gian đặt đơn và tổng tiền; nên có mã đơn để nhập lại
không bị trùng. Xem mục 11 của `docs/HUONG-DAN-SU-DUNG.md`.

### 5.4 Điền vào LiveLift và kiểm tra

```dotenv
TIKTOK_SHOP_APP_KEY=...
TIKTOK_SHOP_APP_SECRET=...
TIKTOK_SHOP_ACCESS_TOKEN=...
TIKTOK_SHOP_SHOP_CIPHER=...
```

Cả **bốn biến đều bắt buộc**. Không có biến vùng: mọi mẫu yêu cầu trong các trang tài liệu TikTok mà nhóm
đã đọc đều dùng một tên miền duy nhất là `https://open-api.tiktokglobalshop.com`. App Secret chỉ dùng để ký, không bao giờ bị gửi
đi. Token đi trong header `x-tts-access-token`, không nằm trong URL.

Kiểm tra (**chỉ đọc**):

```powershell
.venv\Scripts\python scripts\kiem_tra_tiktok_shop.py
```

Script làm bốn việc:

1. In độ dài của bốn biến (**không in giá trị**).
2. Gọi danh sách phiên LIVE **7 ngày gần nhất** (ngày theo giờ Việt Nam) của tài khoản chính thức và tài
   khoản marketing, rồi in số phiên.
3. Nếu có phiên, gọi số liệu theo phút của phiên mới nhất và in **số phút dữ liệu**.
4. Kết luận **một trong ba** trạng thái, kèm cách sửa:
   - **DÙNG ĐƯỢC** (mã thoát 0): đã đọc được **ít nhất một phút** dữ liệu theo phút.
   - **CHƯA DÙNG ĐƯỢC** (mã thoát 1): có lỗi chặn, như thiếu biến, sai khoá hay thiếu quyền.
   - **CHƯA KIỂM ĐƯỢC THEO PHÚT** (mã thoát 2): khoá và danh sách phiên đã qua, nhưng không có phiên nào,
     hoặc phiên mới nhất chưa có phút dữ liệu nào. Trạng thái này **không** chứng minh đường theo phút
     chạy được, nên **không** được ghi vào hồ sơ là đã chạy được. Shop thử rất dễ rơi vào trường hợp này,
     vì tài liệu không nói shop thử có số liệu LIVE.

Script không in tiêu đề phiên, tên tài khoản hay thông tin khách. Muốn tìm phiên cũ hơn thì thêm
`--so-ngay 14`.

| Mã lỗi TikTok | Nghĩa | Cách sửa |
|---|---|---|
| `105005` | App hoặc token chưa có gói **TikTok Shop Analytics** | Bật gói ở **Manage API**, cho shop **ủy quyền lại** |
| `105002` | Token hết hạn (7 ngày) | Làm mới bằng `refresh_token`, dán token mới vào `.env` |
| `36009004` + chữ `timestamp` | Đồng hồ máy lệch (quá 5 phút về trước hoặc 30 giây về sau) | Bật đồng bộ giờ tự động của hệ điều hành |
| `36009004` + chữ `app_key`, hoặc `106001` | Sai App Key hoặc App Secret | Chép lại từ trang chi tiết app trong Partner Center |
| `36009004` + chữ `access_token` | Token không hợp lệ | Lấy token mới theo bước 5 của mục 5.2 |
| `101000` | Token không phải của người bán, hoặc không khớp `shop_cipher` | Lấy lại `shop_cipher` bằng Get Authorized Shops |
| `106013` | Thiếu hoặc sai `shop_cipher` | Như trên |
| `66009315` | Không có quyền với phiên này | Phiên phải do tài khoản chính thức/marketing **của chính shop** phát |
| HTTP `429` / `36009002` | Bị giới hạn nhịp gọi, **token vẫn tốt** | Bộ nối tự chờ rồi thử lại; nếu vẫn lỗi, đợi vài phút |
| `36009043` / `36009044` | Shop hoặc tài khoản người bán bị vô hiệu hóa | Chủ shop xử lý trong Seller Center; thử lại không sửa được |
| `36009003` | Lỗi nội bộ phía TikTok | Bộ nối tự thử lại. Nếu vẫn lỗi nhiều lần, gửi ticket ở <https://partner.tiktokshop.com/ticket/center> kèm `request_id` |

Nguồn mã lỗi: <https://partner.tiktokshop.com/docv2/page/common-errors> ·
<https://partner.tiktokshop.com/docv2/page/6a2fcefe4dcf9be6fd930820>. Mã `66009315` được tài liệu ghi cho
nhóm `live_rooms/*`. Mã `36009003` (*"Internal error. Please try again"*) có trong bảng lỗi của Get Shop
LIVE Performance Overview (<https://partner.tiktokshop.com/docv2/page/6960bc30ea9d0304fa4027f7>) và Get
Authorized Shops. Địa chỉ ticket cho shop ngoài Mỹ lấy từ
<https://partner.tiktokshop.com/docv2/page/seller-developer-onboarding-onepager>.

### 5.5 Giới hạn

- **Chỉ hậu kiểm.** Số theo phút có **sau** khi phiên kết thúc, và TikTok **không công bố** độ trễ. Sau mỗi
  phiên thật, chạy lại lệnh kiểm tra (ví dụ mỗi 15 phút) và **ghi lại độ trễ đo được**.
- **Không có bình luận** (chỉ có số đếm) và **không ghim được** qua API.
- **Phút vắt qua ranh giới hai khối bị loại và đếm riêng** khi gộp theo khối (hàm `gop_theo_khoi`), chứ
  không chia tỷ lệ. Lý do: chia tỷ lệ sẽ bịa ra "nửa lượt bấm". Ranh giới khối lệch theo giây, nên thường
  mất khoảng một phút ở mỗi ranh giới. Ghi con số này vào phần phương pháp. Tài liệu không nói `end_time`
  của một phút là mốc mở hay đóng, và mẫu phản hồi chính thức còn để `start_time` **bằng** `end_time`.
  Vì vậy khi xét ranh giới, LiveLift coi mỗi phút phủ **ít nhất 60 giây kể từ `start_time`**, và đếm số
  phút dựa vào giả định này (`so_phut_gia_dinh_60s`). Nếu chỉ so `end_time`, phút bắt đầu 30 giây trước
  ranh giới sẽ bị cộng trọn vào khối trước.
- **Token sống 7 ngày**, và LiveLift **chưa tự làm mới**.
- **Nhịp gọi.** TikTok cấp hạn mức động. Bộ nối giữ **0,2 yêu cầu/giây**, là mức thấp nhất mà trang Rate
  limits gợi ý bắt đầu, và tự chờ khi gặp `429`
  (<https://partner.tiktokshop.com/docv2/page/64f1991d64ed2e0295f3d2c0>). Shop thử bị giới hạn số lượt
  gọi mỗi giờ, nhưng hai thông báo chính thức ghi hai con số khác nhau: **100** và **1000**.
- **Chưa nối** vào bộ thu nền, khối "Máy chủ này thu được bình luận từ đâu" hay báo cáo phiên. Hiện chỉ
  dùng được qua script kiểm tra và mã Python.

**Nếu lộ token hoặc App Secret:** chủ shop vào **Seller Center → App Store → My apps and incidents**, hủy
ủy quyền cho app, rồi ủy quyền lại để lấy token mới
(<https://partner.tiktokshop.com/docv2/page/seller-authorization-guide>). Tài liệu nhóm đã đọc **không
mô tả** cách đổi App Secret. Hãy hỏi hỗ trợ TikTok qua ticket trong Partner Center, và cho tới lúc đó coi
app là đã lộ.

---

## 6. Địa chỉ công khai cho link đo

Chỉ số chính của thí nghiệm là **lượt bấm link đo** `/r/{code}`. Khách xem live bấm link trên điện
thoại của họ, nên link phải trỏ tới một **địa chỉ công khai** — chạy trên laptop thì link trỏ về
`localhost` và **không ai ngoài máy đó bấm được**.

- **Đường đúng cho thí nghiệm thật:** máy chủ công khai + tên miền + HTTPS bằng Caddy, theo
  `docs/competition/sang-tao-tre-2026/04-TRIEN-KHAI.md`. Điền `DOMAIN` và
  `NEXT_PUBLIC_PUBLIC_API_BASE=https://<tên-miền>` trong `.env`.
- **Không** mở máy chủ trên laptop ra Internet bằng đường hầm (tunnel) khi `INGEST_TOKEN` để trống:
  mọi đường ghi sẽ mở cho người lạ. Bản công khai phải đặt `INGEST_TOKEN`, và việc giao diện web chưa
  gửi được token là một việc còn mở trong `docs/VIEC-CAN-LAM.md`.

---

## 7. Buổi phát thử 30 phút đầu tiên

**Mục tiêu:** chứng minh đường thu bình luận chạy thật với khoá thật, trước khi mời đối tác. Làm trên
**YouTube** và **Fanpage** của nhóm, chọn chế độ **chạy thử** để số liệu không lẫn vào kết quả thí
nghiệm.

**Trước một ngày**

1. Xong mục 2 và 3; trang Bắt đầu ghi **Sẵn sàng** cho YouTube và Facebook.
2. Kênh YouTube đã xác minh (mục 2.5); Fanpage đủ điều kiện phát (mục 3.4).
3. Chia vai 4 người: **người phát**, **người vận hành Bàn trợ live**, **hai người bình luận**.
4. Soạn khoảng 60 bình luận kịch bản, mỗi câu có mã riêng (`T2-001 giá bao nhiêu shop`,
   `T2-002 còn size M không`…). Thêm **một** câu chứa số điện thoại giả `0900 000 000`.

**Ngày phát**

1. Chạy máy chủ: `.venv\Scripts\python scripts\chay_local.py`, mở <http://localhost:3000>.
2. **Chuẩn bị phiên**:
   - bước 1: thêm 2–3 sản phẩm;
   - bước 2: chọn nền tảng, thời lượng **30 phút**, chọn **"Chạy thử (không tính vào kết quả)"**;
   - bước 3: bốc lịch.
3. Bấm phát trên nền tảng:
   - **YouTube:** YouTube Studio → **Tạo** → **Phát trực tiếp** → **Webcam** → chép link video;
   - **Facebook:** Fanpage → **Video trực tiếp**.
4. Bước 4 của wizard, mục **Nguồn bình luận**: YouTube **dán link video**; Facebook **để trống**. Bấm
   **"Bật bộ thu"**, chờ dòng **"● Đang thu bình luận"**.
5. Mở màn người dẫn bằng link ở bước 4 (link có `?session=`), rồi bấm **"Bắt đầu phát sóng"**.
6. Trong 30 phút: hai người bình luận theo kịch bản, nhịp tăng dần tới khoảng 1 câu mỗi giây. Người vận
   hành bấm ghim trên Bàn trợ live trong khối BẬT, ghim tay trên nền tảng và ghi lại giờ ghim.
7. Hết giờ: tắt phát trên nền tảng → **"Kết thúc phiên"** → **"Kết thúc ngay"** → **"Xem báo cáo
   phiên"**.

**Buổi thử đạt khi**

| Kiểm tra | Đạt khi |
|---|---|
| Thu đủ bình luận | ≥ 98% câu kịch bản có trong LiveLift |
| Lọc dữ liệu cá nhân | Số điện thoại giả hiện thành `[SĐT]` |
| Hạn mức YouTube | Dự phóng cho buổi 90 phút ≤ 30% hạn mức ngày (mục 2.4) |
| Hạn mức Facebook | `kiem_tra_facebook.py` mục 5 dưới 50% |

Ghi kết quả vào mẫu `ops/templates/nhat-ky-phien.md`. Buổi này **chưa** kiểm được lượt bấm từ điện
thoại khách — việc đó cần địa chỉ công khai (mục 6).
