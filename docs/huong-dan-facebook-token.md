# Hướng dẫn lấy token Facebook cho LiveLift (làm được kể cả khi không rành kỹ thuật)

> **Mục tiêu:** để LiveLift đọc **bình luận** và **số người xem** của buổi live trên
> **Fanpage của chính nhóm mình**, phục vụ thí nghiệm switchback.
> **Thời gian:** khoảng 20–30 phút cho lần đầu.
> **Cần App Review của Facebook không?** **KHÔNG** — nếu chỉ đọc Page của chính nhóm
> (xem mục 11 để biết khi nào thì cần).
>
> Đã đối chiếu tài liệu Graph API ngày **09/09/2026**. Bản Graph API dùng mặc định
> trong repo: **v25.0**.

---

## 0. Cần chuẩn bị sẵn

| Thứ cần có | Ghi chú |
|---|---|
| 1 tài khoản Facebook cá nhân (đã bật xác thực 2 lớp) | Người này sẽ là **quản trị viên app** |
| 1 **Fanpage** (Trang) do chính người đó làm **quản trị viên** | Không dùng trang cá nhân — API live chỉ đọc được Page |
| Máy đã cài repo LiveLift và chạy được `python` trong `.venv` | Bước 9 cần chạy 1 lệnh |

> **Trang cá nhân (profile) KHÔNG dùng được.** Facebook chỉ cho đọc bình luận live
> qua **Page access token**. Nếu nhóm mới, hãy tạo một Fanpage đặt tên kiểu
> "Live Lab — <tên nhóm>" ở <https://facebook.com/pages/create>.

---

## 1. Tạo ứng dụng (app) trên Meta for Developers

1. Vào <https://developers.facebook.com/apps> → **Tạo ứng dụng** (Create App).
2. Chọn trường hợp sử dụng: **Khác** (Other) → loại ứng dụng: **Doanh nghiệp**
   (Business).
3. Đặt tên: `LiveLift Live Lab` (tên gì cũng được, không hiện với người xem).
4. Bấm **Tạo ứng dụng**. Nhập lại mật khẩu Facebook nếu được hỏi.

Sau bước này app đang ở **chế độ Phát triển (Development Mode)**. **Cứ để nguyên như
vậy** — đó chính là chế độ cho phép đọc Page của mình mà **không cần App Review**.

## 2. Ghi lại App ID và App Secret

1. Trong app: **Cài đặt ứng dụng → Cơ bản** (App settings → Basic).
2. Chép **ID ứng dụng** (App ID) và bấm **Hiện** (Show) để chép **Khóa bí mật**
   (App Secret).
3. Dán tạm vào một chỗ an toàn — **App Secret là mật khẩu, không gửi qua chat nhóm,
   không chụp màn hình đăng lên đâu cả.**

## 3. Thêm các thành viên khác vào app (nếu cần)

Trong **Vai trò ứng dụng → Vai trò** (App roles → Roles): thêm thành viên với vai trò
**Quản trị viên / Nhà phát triển / Người kiểm thử**. Người đó **cũng phải là quản trị
viên của Fanpage** thì mới lấy được Page token.

> Đây là lý do không cần App Review: ở Development Mode, mọi quyền đều dùng được
> **cho những người có vai trò trong app** và trên **tài sản (Page) mà họ quản trị**.

## 4. Lấy token người dùng (User token) kèm đủ quyền

1. Mở **Graph API Explorer**: <https://developers.facebook.com/tools/explorer/>.
2. Góc phải: **Ứng dụng Meta** → chọn đúng app vừa tạo.
3. **Loại token của người dùng** (User or Page) → chọn **Mã truy cập của người dùng**
   (User Token).
4. Bấm **Thêm quyền** (Add a Permission) và tick đủ **3 quyền** sau:

   | Quyền | Dùng để làm gì | Bắt buộc? |
   |---|---|---|
   | `pages_show_list` | Liệt kê các Page mình quản trị (bước 6) | Nên có |
   | `pages_read_engagement` | Đọc video live + **số người xem** của Page | **Bắt buộc** |
   | `pages_read_user_content` | Đọc **bình luận của người xem** | **Bắt buộc** |

   > ⚠️ **Cái bẫy kinh điển:** `pages_read_engagement` chỉ cho đọc nội dung **do Page
   > tự đăng**. Bình luận là nội dung **của người xem**, nên **thiếu
   > `pages_read_user_content` thì không đọc được một bình luận nào** — mà biến kết
   > quả chính của LiveLift lại nằm ở bình luận.

5. Bấm **Tạo mã truy cập** (Generate Access Token) → đăng nhập → chọn **Fanpage của
   nhóm** ở màn hình cấp quyền → **Tiếp tục**.
6. Chép chuỗi token vừa hiện ra (rất dài). Token này **chỉ sống 1–2 giờ** — bước 5 và 6
   sẽ đổi nó thành token dài hạn.

## 5. Đổi sang token dài hạn (long-lived, 60 ngày)

Mở một tab trình duyệt mới, dán URL sau (thay 3 chỗ trong ngoặc nhọn, bỏ luôn dấu
ngoặc):

```
https://graph.facebook.com/v25.0/oauth/access_token?grant_type=fb_exchange_token&client_id=<APP_ID>&client_secret=<APP_SECRET>&fb_exchange_token=<TOKEN_NGAN_HAN_O_BUOC_4>
```

Kết quả trả về dạng:

```json
{"access_token":"EAAG...","token_type":"bearer","expires_in":5183944}
```

`access_token` này là **User token dài hạn (~60 ngày)**. Chép lại.

> Cách khác không cần dán App Secret vào trình duyệt: vào
> <https://developers.facebook.com/tools/debug/accesstoken>, dán token ngắn hạn, bấm
> **Gỡ lỗi** (Debug) rồi bấm **Gia hạn mã truy cập** (Extend Access Token).

## 6. Lấy **Page token** dài hạn (loại token LiveLift cần)

Dán URL sau (thay token dài hạn ở bước 5):

```
https://graph.facebook.com/v25.0/me/accounts?fields=id,name,access_token&access_token=<USER_TOKEN_DAI_HAN>
```

Kết quả liệt kê các Page bạn quản trị:

```json
{"data":[{"id":"1234567890","name":"Live Lab — Nhóm A","access_token":"EAAG...."}]}
```

- `id` của Page → điền vào `FACEBOOK_PAGE_ID`
- `access_token` của **đúng Page đó** → điền vào `FACEBOOK_PAGE_ACCESS_TOKEN`

> **Page token lấy từ User token dài hạn thì KHÔNG có ngày hết hạn.** Nó chỉ mất hiệu
> lực khi: đổi mật khẩu Facebook, gỡ app, mất quyền quản trị Page, hoặc app không dùng
> dữ liệu suốt ~90 ngày (mục 12).

## 7. Dán vào `.env`

Mở file `.env` ở thư mục gốc repo (nếu chưa có thì chép từ `.env.example`), điền:

```dotenv
FACEBOOK_PAGE_ID=1234567890
FACEBOOK_PAGE_ACCESS_TOKEN=EAAG...            # Page token ở bước 6
FACEBOOK_GRAPH_VERSION=v25.0
# Hai dòng dưới KHÔNG bắt buộc — chỉ để script kiểm tra đọc được hạn/quyền của token:
FACEBOOK_APP_ID=...
FACEBOOK_APP_SECRET=...
```

> **KHÔNG commit file `.env` lên git** (repo đã bỏ qua file này). Token = mật khẩu của
> Page. Nếu lỡ lộ: vào **Cài đặt ứng dụng → Cơ bản → Đặt lại khóa bí mật**, rồi làm lại
> từ bước 4.
> Máy chạy ingest **chỉ cần** `FACEBOOK_PAGE_ACCESS_TOKEN`; **đừng** đưa
> `FACEBOOK_APP_SECRET` lên VPS.

## 8. Chạy script kiểm tra

```bash
# Windows
.venv/Scripts/python scripts/kiem_tra_facebook.py
# macOS / Linux
python scripts/kiem_tra_facebook.py
```

Script **chỉ đọc**, không đăng/sửa/xóa gì trên Facebook, và **không in nội dung bình
luận** (quy tắc PII của dự án). Kết quả mẫu khi mọi thứ đã sẵn sàng:

```
==================================================================
 KIỂM TRA ĐƯỜNG FACEBOOK LIVE — LiveLift
 Thời điểm: 09/09/2026 08:15 UTC · Graph API v25.0
==================================================================

1) TOKEN
   Độ dài token   : 212 ký tự (không in ra token)
   Trạng thái     : HỢP LỆ
   Loại token     : PAGE
   Hạn token      : KHÔNG hết hạn (token dài hạn)
   Hạn truy cập DL: còn 89 ngày (07/12/2026 08:15 UTC)

2) QUYỀN
   [x] pages_read_engagement      BẮT BUỘC — đọc video live + số người xem của Page
   [x] pages_read_user_content    BẮT BUỘC — đọc BÌNH LUẬN của người xem
   [x] pages_show_list            nên có — liệt kê Page mình quản trị

3) PAGE ĐỌC ĐƯỢC
   Tên            : Live Lab — Nhóm A
   Id             : 1234567890

4) BUỔI LIVE & ĐỌC THỬ BÌNH LUẬN
   ĐANG PHÁT      : có (1 buổi)
   Live video id  : 100200300
   Người xem hiện : 42
   Đọc bình luận  : OK — lấy được 3 bình luận (không in nội dung: quy tắc PII)

5) HẠN MỨC GỌI API
   Đã dùng        : 3% (Facebook chặn khi chạm 100%)
------------------------------------------------------------------
KẾT LUẬN: SẴN SÀNG
==================================================================
```

Mỗi dòng `[CHẶN]` đều kèm cách sửa. Mã thoát: `0` = sẵn sàng, `1` = chưa.

## 9. Thử thật một lần trước ngày chạy phiên

1. Trên Fanpage, bấm **Phát trực tiếp** (có thể đặt đối tượng **Chỉ mình tôi** để không
   ai thấy) — phát khoảng 2 phút.
2. Nhờ 1 người (hoặc chính mình) bình luận vài câu.
3. Chạy lại `scripts/kiem_tra_facebook.py` → phải thấy `ĐANG PHÁT : có` và
   `Đọc bình luận : OK`.
4. Chép `Live video id` ở mục 4 rồi chạy thử runner:

```bash
python -m livelift.ingest.runner --platform facebook \
  --source-id <LIVE_VIDEO_ID> --session-id <session_id> --api-url http://localhost:8000
```

Mỗi 60 giây phải có 1 dòng `heartbeat: ... | tải API: 3% | lỗi gần nhất: không có`.

> **Chỉ bước 9 mới chứng minh được đường dữ liệu chạy.** Token hợp lệ mà chưa từng đọc
> bình luận thật thì vẫn còn rủi ro.

## 10. Trước mỗi phiên live thật (checklist 2 phút)

- [ ] `python scripts/kiem_tra_facebook.py` → `KẾT LUẬN: SẴN SÀNG`
- [ ] Không có dòng `[CẢNH BÁO]` về hạn token / hạn truy cập dữ liệu
- [ ] Mục 5 `Đã dùng` < 50%
- [ ] Đã chép đúng `Live video id` của buổi live **hôm nay** (id đổi theo từng buổi)

---

## 11. Khi nào **cần** App Review, khi nào **không**

| Tình huống | App Review? | Ghi chú |
|---|---|---|
| Đọc live của **Fanpage nhóm mình**, người chạy có vai trò trong app | **KHÔNG** | Development Mode / Standard Access — chạy được ngay hôm nay |
| Đọc live của **Page đối tác** (nhà bán khác) | **CÓ** | Cần **Advanced Access** cho `pages_read_engagement` + `pages_read_user_content`, và **Business Verification** trước |
| Tự **phát/điều khiển** buổi live bằng API (`publish_video`) | **CÓ** | LiveLift **không** làm việc này — chỉ đọc |

**Nếu đi tiếp đường Page đối tác:** làm Business Verification trước (có thể mất 10+
ngày), mỗi quyền cần 1 video quay màn hình mô tả luồng thật, chính sách quyền riêng tư
nêu rõ loại dữ liệu và cách xóa; thực tế 2–7 ngày nếu hồ sơ sạch, tới ~20 ngày nếu bị
trả lại, và **mỗi lần bị từ chối là đếm lại từ đầu** — dự trù 4–6 tuần.

**Giới hạn pháp lý/đạo đức của dự án (không được lách):**

- Chỉ thu thập nội dung **công khai** trên Page **mình sở hữu**, hoặc Page đối tác **đã
  có văn bản đồng ý + Advanced Access**. Dùng token của người khác để đọc Page họ không
  đồng ý là **vi phạm Điều khoản Nền tảng của Meta**.
- **Không tải video** — chỉ lấy bình luận và số liệu.
- Bình luận thô **không bao giờ được ghi xuống đĩa**: bộ lọc PII chạy ngay trong tiến
  trình ingest trước khi gửi đi; id người bình luận bị **loại bỏ** ngay khi phân tích
  dữ liệu (không lưu chuỗi hành vi theo từng người).

## 12. Vì sao token đang tốt lại chết — và cách phòng

| Nguyên nhân | Dấu hiệu | Cách xử lý |
|---|---|---|
| Đổi mật khẩu Facebook | code 190, subcode 460 | Làm lại bước 4→6 |
| Gỡ app khỏi tài khoản | code 190, subcode 458 | Cấp quyền lại rồi làm lại bước 4→6 |
| Mất quyền quản trị Page | code 190, subcode 492 | Xin lại quyền quản trị Page |
| **Hết hạn truy cập dữ liệu (~90 ngày không dùng)** | Gọi được nhưng dữ liệu rỗng / code 190 | Vào Graph API Explorer cấp quyền lại (bấm lại bước 4) |
| Token là **User token**, không phải **Page token** | Script báo `Đây là USER token` | Làm bước 6 |

**Đặt lịch:** chạy `scripts/kiem_tra_facebook.py` **mỗi tuần một lần** và trước mỗi
phiên. Dòng `Hạn truy cập DL` cho biết còn bao nhiêu ngày.

## 13. Hạn mức gọi API (đừng để bị chặn giữa phiên)

- Hạn mức cấp Page ≈ **4800 × số người tương tác với Page / 24 giờ** (cửa sổ trượt 24h),
  **dùng chung cho mọi app** gọi bằng token của Page đó.
- LiveLift poll bình luận mỗi 5 giây ≈ **17.000 lượt gọi/24 giờ** + đếm người xem mỗi
  30 giây ≈ 2.900 lượt. Fanpage mới, ít người tương tác ⇒ **hạn mức thấp** ⇒ dễ chạm
  trần.
- Runner đọc header `X-App-Usage` / `X-Page-Usage` của Facebook và in phần trăm trong
  mỗi heartbeat (`tải API: 62%`), kèm cảnh báo khi vượt 75%.
- Khi bị chặn, Facebook trả **code 4 / 17 / 32 / 613**. Runner sẽ báo
  *"GIỚI HẠN nhịp gọi Facebook … token VẪN TỐT, không cần đổi token"* và tự nghỉ 5 phút.
  **Đừng đi tạo token mới lúc đó** — vô ích, và làm mất thêm thời gian giữa phiên.
- Cách giảm tải: chỉ chạy **một** tiến trình ingest cho mỗi Page, và tăng khoảng poll
  nếu phiên dài.

## 14. Bảng lỗi thường gặp

| Thông báo của Facebook | Nghĩa là gì | Làm gì |
|---|---|---|
| `code 190` (OAuthException) | Token hỏng/hết hạn | Làm lại bước 4→6 |
| `code 200` hoặc `code 10` | Thiếu quyền | Thiếu `pages_read_user_content` là phổ biến nhất — bước 4 |
| `code 4 / 17 / 32 / 613` | Chạm hạn mức | Chờ, giảm nhịp poll (mục 13) — **không** đổi token |
| `code 100` (Unsupported get request) | Sai id, hoặc Page token không có quyền với vật thể đó | Kiểm tra lại `Live video id` (id đổi theo từng buổi live) |
| `(#803) Some of the aliases…` | Dùng tên Page thay vì id số | Lấy id số ở bước 6 |

---

## Nguồn đã đối chiếu (09/09/2026)

- Live Video Comments — <https://developers.facebook.com/docs/graph-api/reference/live-video/comments/>
  (`live_filter`, `filter`, `order`, `since`)
- Live Video API, "Interacting with Viewers" — <https://developers.facebook.com/documentation/live-video-api/interact-with-viewers>
- Page Live Videos — <https://developers.facebook.com/docs/graph-api/reference/page/live_videos/>
- Token dài hạn — <https://developers.facebook.com/docs/facebook-login/guides/access-tokens/get-long-lived>
- Rate limits (`X-App-Usage`, mã lỗi 4/17/32/613) — <https://developers.facebook.com/docs/graph-api/overview/rate-limiting>
- Phiên bản & vòng đời API (v25.0 phát hành 18/02/2026, ngừng 29/07/2028) —
  <https://developers.facebook.com/docs/graph-api/changelog/versions/>
