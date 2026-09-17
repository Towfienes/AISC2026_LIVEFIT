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
| **TikTok Shop** | Tài khoản Partner Center + app | vài ngày duyệt | Số liệu phiên LIVE **theo phút, sau khi kết thúc** (GMV, đơn, click, số bình luận) — **không** có nội dung bình luận | **Chưa có bộ nối**; hôm nay dùng được nhập đơn CSV |
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

### 2.4 Hạn mức — đọc trước buổi live dài

- Mặc định **10.000 đơn vị/ngày** cho mỗi dự án, đặt lại lúc nửa đêm giờ Thái Bình Dương (khoảng
  14:00–15:00 giờ Việt Nam).
- Bảng giá hiện hành ghi `liveChatMessages.list` = 1 đơn vị/lượt, nhiều tài liệu cũ ghi 5. Một buổi 90
  phút poll mỗi 5 giây tốn khoảng **1.080–5.400 đơn vị**. **Đo thật** sau buổi phát thử: **APIs &
  Services → YouTube Data API v3 → Metrics/Quotas**.
- Chạy từ 2 buổi live dài trong cùng một ngày thì xin tăng hạn mức ở trang **Quotas**.

### 2.5 Điều kiện để kênh của nhóm phát live

- Xác minh kênh bằng số điện thoại tại <https://www.youtube.com/verify>.
- Lần đầu bật phát trực tiếp có thể phải **chờ tới 24 giờ**.
- Phát bằng **máy tính** (webcam hoặc OBS) không cần số người đăng ký tối thiểu; phát bằng **điện thoại**
  cần từ **50 người đăng ký**.
- Kênh không bị hạn chế phát trực tiếp trong 90 ngày gần nhất.

### 2.6 Lỗi thường gặp

| Bộ thu báo | Nghĩa là | Làm gì |
|---|---|---|
| *API key không hợp lệ hoặc quota trong ngày đã cạn* | Key sai, chưa bật API, hoặc hết hạn mức | Kiểm tra bước 3 và 5; xem Metrics xem đã hết hạn mức chưa |
| *Chờ buổi live bắt đầu* | Video chưa phát hoặc đã kết thúc | Bấm phát trên YouTube; bộ thu tự dò lại |
| *Không nhận ra video YouTube* | Dán link kênh thay vì link video | Dán link dạng `youtube.com/watch?v=…` hoặc `youtube.com/live/…` |

Video **Không công khai** chưa được kiểm chứng là đọc được bằng API key; nếu bộ thu không tìm thấy
video thì chuyển buổi phát thử sang **Công khai**.

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

## 5. TikTok Shop — Partner Center (chuẩn bị trước, chưa có bộ nối)

### 5.1 TikTok cho gì, không cho gì

- **Có** API chính thức cho số liệu phiên LIVE của shop, **theo từng phút**: GMV, đơn, click sản phẩm,
  số bình luận, người xem — áp dụng mọi thị trường kể cả Việt Nam. Số liệu chỉ có **sau khi phiên kết
  thúc**, và chỉ cho buổi live do **tài khoản chính thức hoặc tài khoản marketing của shop** phát.
- **Không** có API đọc nội dung bình luận live, **không** có API ghim sản phẩm trong live, **không** có
  thông báo khi live bắt đầu.
- **TikTok LIVE thường** (không phải shop) **không có đường chính thức nào**.

### 5.2 Bấm gì — để sẵn sàng khi LiveLift có bộ nối

1. Vào <https://partner.tiktokshop.com> (Partner Center ngoài Mỹ), đăng ký tài khoản đối tác loại
   **Seller in-house developer** và liên kết với **shop TikTok Shop Việt Nam đã kích hoạt**.
2. Tạo app riêng (private app) gắn với đúng một shop của mình; ghi lại **App Key** và **App Secret**.
3. Xin quyền cho các nhóm API số liệu LIVE (Analytics) và đơn hàng (Order).
4. Ủy quyền app cho shop để lấy access token.

LiveLift **chưa có biến `.env` cho TikTok Shop** — bộ nối hậu kiểm theo phút nằm trong danh sách việc
cần làm. Khi có bộ nối, tài liệu này sẽ bổ sung tên biến.

### 5.3 Dùng được ngay hôm nay với TikTok Shop

Xuất danh sách đơn từ **TikTok Shop Seller Center** ra tệp CSV sau buổi live, rồi nhập ở trang **Báo cáo
phiên** của LiveLift. LiveLift gán mỗi đơn vào khối BẬT/TẮT theo **giờ đặt đơn** và chỉ nhận đơn nằm
trong khung giờ của phiên. Cột bắt buộc: thời gian đặt đơn và tổng tiền; nên có mã đơn để nhập lại
không bị trùng. Xem mục 11 của `docs/HUONG-DAN-SU-DUNG.md`.

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
