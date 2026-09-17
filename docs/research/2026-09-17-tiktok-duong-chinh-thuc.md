# TikTok: đường API chính thức cho LiveLift (17/09/2026)

> **Nguồn gốc tài liệu (khai thật).** Tác tử Claude (vai tổng biên tập) soạn tài liệu này ngày 17/09/2026. Đầu vào là
> một đợt nghiên cứu nhiều tác tử: một tác tử viết báo cáo, một tác tử khác **kiểm chứng độc lập từng phát hiện**
> (14 phát hiện: 13 xác nhận, 1 đúng một phần, 0 sai). Người kiểm chứng tự tải lại tài liệu TikTok Shop Partner
> Center qua API tài liệu công khai và chạy lại ví dụ ký. Báo cáo thô, bản tải trang và kịch bản kiểm chứng nằm
> trong thư mục scratchpad của phiên làm việc, **không có trong kho**. Vì vậy mọi khẳng định dưới đây đều kèm URL để
> kiểm lại. Tổng biên tập đọc thêm mã trong kho và chạy lại test ngày 17/09/2026 (mục 10).
>
> **Phạm vi:** chỉ đường **chính thức**, trên tài khoản của nhóm hoặc của đối tác đồng ý (quyết định của chủ dự án
> ngày 17/09/2026). Bộ đo không chính thức cũ `collectors/tiktok_public/` **vẫn giữ nguyên trong kho** theo quyết định
> đó; tài liệu này không đề xuất dùng hay phát triển thêm nó.
>
> **Ngày truy cập:** mọi URL truy cập ngày **17/09/2026**, trừ khi ghi khác. Ngày trong ngoặc sau tên trang
> TikTok là trường `update_time` của trang đó.
>
> **Mức chắc chắn:** **[Đã kiểm]** = người kiểm chứng tự đọc lại nguồn và xác nhận · **[Một phần]** = đúng một phần,
> phần sai hoặc thiếu ghi ngay bên cạnh · **[Chưa kiểm lại]** = chỉ có trong báo cáo gốc · **[Suy luận]** = nhóm tự
> suy ra, phải đo · **[Thứ cấp]** = báo, blog, diễn đàn.

Bổ sung và **đính chính** cho `docs/research/2026-09-17-nen-tang-livestream-va-serpapi.md` §1.2 và mục D.3. Hướng
dẫn thao tác lấy khoá nằm ở `docs/HUONG-DAN-LAY-KHOA-API.md` mục 5; tài liệu này không lặp lại các bước bấm.

---

## 0. Trả lời dứt khoát

**TikTok lấy được API chính thức không?** **Có**, qua TikTok Shop Open Platform (Partner Center). Nhưng đội 3 sinh
viên **chưa có shop** thì trước 30/09/2026 **không lấy được số liệu LIVE thật**. Trước hạn đó nhóm chỉ làm được đến
bước ký yêu cầu, ủy quyền và gọi API trên **shop thử (sandbox) Việt Nam**.

**Đường nào?** Chỉ có **đường người bán**: token người bán (`user_type = 0`), gói quyền "TikTok Shop Analytics"
(`data.shop_analytics.public.read`), bốn endpoint `shop_lives/*` và `shop/{live_id}/products_performance`. Nhóm
`live_rooms/*` (`core_stats`…) cần **token creator** (`user_type = 1`), nên **không** dùng được bằng token shop.

**Mất bao lâu?**

| Mục tiêu | Thời gian | Căn cứ |
|---|---|---|
| Minh chứng ký + OAuth trên shop thử VN | 1–2 ngày | Không cần giấy tờ doanh nghiệp để tạo app (mục 2) |
| Số liệu LIVE thật qua shop của chính nhóm | **Không xác định**, có thể không bao giờ | Cần Account Manager; TikTok không cam kết gán (mục 2.2) |
| Số liệu LIVE thật qua shop đối tác đã có app | 2–3 ngày kỹ thuật, cộng thời gian đàm phán | Mã bộ nối đã có trong kho (mục 10) |

**Cho LiveLift được gì?** **Hậu kiểm theo phút sau khi phiên kết thúc**: GMV, `sku_orders`, `product_clicks`,
`viewers`, **số** bình luận… cho từng phút. Dữ liệu này ghép được vào khối switchback, nhưng chỉ dùng làm **biến
phụ để đối chiếu chéo**. Biến kết quả chính vẫn là lượt bấm `/r/{code}` do LiveLift tự đo.

**Không có:** nội dung bình luận LIVE, API ghim sản phẩm trong LIVE cho người bán, webhook "live bắt đầu", số liệu
theo phiên trong lúc đang phát, Research API cho Việt Nam.

---

## 1. Đính chính tài liệu 17/09 (làm trước khi dùng lại tài liệu cũ)

| # | Tài liệu cũ viết | Đúng là | Mức | Nguồn |
|---|---|---|---|---|
| Đ1 | D.3: *"trong lúc phát thử `GET /analytics/202502/live_rooms/{id}/core_stats` 60 s/lần"*, trong bối cảnh app Seller in-house gắn 1 shop | `live_rooms/*` đòi **token creator**. Header ghi nguyên văn *"The creator access_token value … when user_type = 1"*, scope `creator.data.live.read.public`, gói "Live Data", `is_shop_chiper_exist = False`. Cả 7 endpoint của nhóm (`core_stats`, `product_stats`, ba `*_trend_performances`, `traffic_performances`, `user_portraits`) đều ghi như vậy | [Đã kiểm] | https://partner.tiktokshop.com/api/v1/document/api_meta?src_document_id=69b0389520af8e048fcadff7 (trang get-live-room-core-stats-202502, 20/07/2026) · https://partner.tiktokshop.com/docv2/page/creator-authorization-guide |
| Đ2 | Mục "Giới hạn": `live_rooms/*` dùng được với token shop hay không thì *"chưa kiểm chứng (tài liệu không nói rõ loại token)"* | Tài liệu **có** nói rõ loại token (xem Đ1) | [Đã kiểm] | như trên |
| Đ3 | §1.2 và bảng A coi `core_stats.current_visitor_count` là số "trong lúc phát" của shop | Chỉ đúng khi có **creator TikTok Shop ủy quyền** cho app. Tài khoản creator thử chỉ cấp cho *"members of our beta phase"* | [Đã kiểm] | https://partner.tiktokshop.com/docv2/page/creator-authorization-guide |
| Đ4 | Ngầm coi cả ba endpoint `shop_lives/*` áp dụng mọi thị trường | Chưa trang nào xác nhận phạm vi thị trường cho **đúng các phiên bản** LiveLift gọi (202509, 202510, 202512). Thông báo "All markets" viết cho bản **202508**; thông báo "available in all markets" chỉ liệt kê endpoint 202405–202409 | [Chưa kiểm lại] — đã ghi ở `HUONG-DAN-LAY-KHOA-API.md` §5.1 | https://partner.tiktokshop.com/docv2/page/68af6771eb3a300486d0e157 · https://partner.tiktokshop.com/docv2/page/68d6ce2d8e2c770495cced8c |

Việc sửa trực tiếp tài liệu cũ được đưa vào `docs/VIEC-CAN-LAM.md` (việc 28).

---

## 2. Bảng đường truy cập

### 2.1 Đường nào, lấy được không, mất bao lâu, cho gì

| # | Đường | Đội VN lấy được không | Mất bao lâu | Cho LiveLift được gì | Nguồn | Mức |
|---|---|---|---|---|---|---|
| 1 | **App developer (ISV) + custom app + shop thử VN** | **Có, ngay.** Không cần giấy chứng nhận doanh nghiệp để tạo app. *Chưa rõ* tài khoản chưa duyệt chứng nhận có vào được Sandbox không | 1–2 ngày | Kiểm chứng ký, OAuth, token, `shop_cipher`, xử lý lỗi. **Không** có dữ liệu LIVE thật | developer-onboarding (11/08/2026) · app-development-overview (06/07/2026) · seller-center-development-shops (21/08/2026) | [Đã kiểm] |
| 2 | **Seller developer**: shop VN của thành viên, đã KYC/KYB, **có Account Manager** → `shop_lives/*` | **Có điều kiện.** Account Manager không đăng ký thẳng được | Shop cá nhân 1–2 ngày [Thứ cấp]; AM **không xác định** | Chuỗi theo phút sau phiên + số theo sản phẩm; `overview_performance?today=true` trong ngày | developer-onboarding · seller-developer-onboarding-onepager (11/08/2026, FAQ 13) | [Đã kiểm] |
| 3 | **ISV publish app** → shop đối tác bất kỳ ủy quyền | **Chỉ khi có pháp nhân** (chứng nhận doanh nghiệp) | Registration review *"several business days"* + thời gian lấy chứng nhận | Như #2, cho nhiều shop | publish-custom-app · app-review-process | [Chưa kiểm lại] |
| 4 | **Đối tác doanh nghiệp đã có app seller-developer**, chạy mô-đun LiveLift như công cụ nội bộ | **Khả thi nhất** cho dữ liệu thật | 2–3 ngày kỹ thuật + đàm phán | Như #2; shop giữ khoá (hợp điều khoản license, xem mục 8) | Developer Terms of Service | [Một phần] — xem mục 8 về giới hạn công bố |
| 5 | **Creator authorization** → `live_rooms/*` | **Rủi ro cao.** Creator TikTok Shop VN cần ≥ 1.000 follower + CCCD gắn chip; tài khoản creator thử chỉ cho beta | Không xác định | Số trong lúc phát (`current_visitor_count`, click/đơn theo sản phẩm, `is_live`) | creator-authorization-guide · https://seller-vn.tiktok.com/university/essay?knowledge_id=6837838528808705&role=2&course_type=1&from=search&identity=1 | [Đã kiểm] phần token; điều kiện creator VN [Chưa kiểm lại] |
| 6 | **Seller Center / Phân tích LIVE** (giao diện, chủ shop tự xuất) | **Có** cho mọi shop bán qua LIVE | Ngay sau phiên; chẩn đoán 1–2 ngày | File số liệu theo sản phẩm, **dòng thời gian sản phẩm được ghim** (tab Nội dung) để đối chiếu lịch switchback | https://seller-vn.tiktok.com/university/essay?knowledge_id=6837840206563073&lang=vi-VN · https://seller-us.tiktok.com/university/essay?knowledge_id=6394088836597518&lang=en | [Chưa kiểm lại] |
| 7 | **TikTok API for Business — báo cáo LIVE GMV Max** (`gmv_max/report/get`, lọc `room_ids`) | Có, nếu shop chạy quảng cáo LIVE GMV Max | 1–3 ngày thiết lập | Chi phí/doanh thu quảng cáo theo phòng live, **chỉ làm biến kiểm soát** | https://github.com/tiktok/tiktok-business-api-sdk/blob/main/js_sdk/docs/ReportingApi.md | [Chưa kiểm lại] |
| 8 | Research API · Commercial Content API · Data Portability · Display API · Login/Share Kit · Content Posting | **Không** (VN không đủ điều kiện, hoặc API không có dữ liệu LIVE) | — | Không gì | mục 6 | [Đã kiểm] |
| 9 | API nội dung bình luận LIVE, ghim sản phẩm trong LIVE, webhook live bắt đầu | **Không tồn tại** | — | Ghim làm tay theo lịch; bình luận TikTok không có đường chính thức | mục 6.1 | [Chưa kiểm lại] phần tìm trong cây tài liệu |

URL đầy đủ của các trang TikTok Shop trong bảng (tiền tố `https://partner.tiktokshop.com/docv2/page/`):
`developer-onboarding`, `seller-developer-onboarding-onepager`, `app-development-overview`,
`seller-center-development-shops`, `publish-custom-app`, `app-review-process`, `creator-authorization-guide`,
`6506bc942f024f02be400315` (Developer Terms of Service).

### 2.2 Vai trò đăng ký và điều kiện (nguyên văn)

- **Seller developer:** *"You must have an activated TikTok Shop account and bound an Account Manager before
  registering as a developer."* Onepager, mục Prerequisites: *"You already have a TikTok Shop seller account that has
  passed KYB or KYC verification"* và *"The seller account has an assigned Account Manager."*
  (developer-onboarding và seller-developer-onboarding-onepager, cùng 11/08/2026) **[Đã kiểm]**
- **Account Manager:** *"TikTok Shop Account Managers (AMs) are not a service sellers can directly apply for in the
  backend"*. Cùng FAQ 13 có đường chính thức: gửi ticket qua Help Center để xin *"Account Manager eligibility review"*,
  nhưng nói rõ đây là *"not officially published guarantees"*. Vậy: **không tự đăng ký được, xin xét được, không có
  cam kết**. **[Đã kiểm]**
- **Private app:** *"Private App can only be authorized and bind to one shop ONLY (seller's own shop)"* (onepager
  FAQ 7). **[Đã kiểm]**
- **ISV:** bước 5 đòi *"Upload your company's business certificate and registration information"*, nhưng có **Save for
  later**: *"(If you create an app now, you can't publish it until certification is complete.)"* (developer-onboarding).
  App chưa publish chỉ thử được với shop thử: *"You can only use test seller accounts created in Development Shop
  (sandbox) to test an unpublished app"* (app-development-overview, 06/07/2026). Seller authorization guide: *"While
  your app is in development, online sellers can't authorize it."* **[Đã kiểm]**
- **Email:** *"If you have already registered for a TikTok Shop Seller account, you are not eligible to apply for ISV
  registration."* (onepager FAQ) → đăng ký ISV bằng **email nhóm, không dùng email shop**. **[Chưa kiểm lại]**
- **Kiểm duyệt bảo mật — hai trang mâu thuẫn:** onepager FAQ 3 ghi *"For seller: Security review is mandatory"*; trang
  App review process ghi custom app của seller truy cập dữ liệu shop mình *"usually do not need app review … Partner
  Center may still require onboarding, compliance, or security checks"*. Chỉ biết chắc khi mở tài khoản, nên đưa vào
  ticket (mục 13). **[Đã kiểm]** phần onepager; https://partner.tiktokshop.com/docv2/page/app-review-process

### 2.3 Shop thử (sandbox) — có Việt Nam

Nguồn: https://partner.tiktokshop.com/docv2/page/seller-center-development-shops (21/08/2026) ·
https://partner.tiktokshop.com/docv2/page/create-test-seller-account (29/06/2026)

- Bảng thị trường: `Vietnam | VN (704) | Yes | Yes` (cross-border và local). Lưu ý đi kèm: với Full Function thì
  *"cross-border seller support is currently unavailable"*. **[Đã kiểm]**
- **Core Function:** *"does not require real business information, TikTok account setup, or credit card
  information"*; chọn *"Onboarding type … individual"* (câu này ở trang create-test-seller-account). **[Đã kiểm]**
- Tối đa **10** tài khoản shop thử (gộp hai loại), hết hạn sau **180 ngày**, kích hoạt lại được. **[Đã kiểm]**
- Cảnh báo: *"Binding a test Seller account to your developer account is permanent and cannot be undone"*. **[Đã kiểm]**
- Trang **không** nhắc LIVE hay livestream: **không biết shop thử có số liệu LIVE**. **[Đã kiểm]**
- Hạn mức gọi của shop thử: một thông báo ghi **1000** lượt/giờ, thông báo khác ghi **100** → lập kế hoạch theo 100.
  https://partner.tiktokshop.com/docv2/page/6a2fcefe4dcf9be6fd930820 ·
  https://partner.tiktokshop.com/docv2/page/6a0ffdce1c4e66e01e6f2362 **[Chưa kiểm lại]**

---

## 3. Ủy quyền và token

| Bước | Chi tiết nguyên văn | Nguồn | Mức |
|---|---|---|---|
| Mã ủy quyền | *"The `auth_code` expires in 30 minutes and can be used only once"* | https://partner.tiktokshop.com/docv2/page/authorization-overview-202407 (26/06/2026) | [Đã kiểm] |
| Đổi token | `GET https://auth.tiktok-shops.com/api/v2/token/get?…&grant_type=authorized_code`; *"Only `authorized_code` is accepted"*; *"Do not 'fix' it to `authorization_code`"* | như trên | [Đã kiểm] |
| Thời hạn | `access_token` *"default validity: 7 days"*; `refresh_token_expire_in` *"equals the authorization duration the user granted"* | như trên | [Đã kiểm] |
| Sắp hết hạn | *"30 days before an authorization expires, an Upcoming authorization expiration webhook is triggered"* | https://partner.tiktokshop.com/docv2/page/seller-authorization-guide (29/06/2026) | [Đã kiểm] |
| `shop_cipher` | Lấy qua `GET /authorization/202309/shops`; bắt buộc với `shop_lives/*`; **không gửi** cho endpoint không cần (lỗi `36009004` *"Unexpected identifier"*) | https://partner.tiktokshop.com/docv2/page/common-errors (06/07/2026) | [Đã kiểm] |

So với Shopee (token 4 giờ), token TikTok Shop sống 7 ngày, nên bộ làm mới chỉ cần chạy hằng ngày. **[Suy luận]**

---

## 4. Ký yêu cầu (API 202309 trở về sau)

Nguồn: https://partner.tiktokshop.com/docv2/page/sign-your-api-request (06/07/2026) ·
https://partner.tiktokshop.com/docv2/page/common-parameters (15/09/2026)

1. Lấy mọi tham số query trừ `sign` và `access_token`, sắp khoá theo thứ tự chữ cái (có `shop_cipher` nếu endpoint cần).
2. Nối thành `{key}{value}`, rồi **đặt đường dẫn lên trước**.
3. Nếu `content-type` không phải `multipart/form-data`, nối **đúng từng byte** thân yêu cầu: *"Use the exact body bytes
   that are sent in the HTTP request. Do not parse and re-serialize"*.
4. Bọc `app_secret` ở hai đầu, băm HMAC-SHA256 với khoá `app_secret`, xuất hex.
5. Token đi ở header `x-tts-access-token`: *"The access token is not included when generating the signature."*
6. `timestamp` là *"A 10-digit Unix timestamp in seconds… Valid range: [current time - 5 mins, current time + 30
   secs]"*; sai thì có thể gặp `36009004 Invalid timestamp` (trang common-parameters).

**[Đã kiểm]** Người kiểm chứng chạy lại ví dụ chính thức (`app_secret = e59af819cc`) và ra đúng
`b596b73e0cc6de07ac26f036364178ab16b0a907af13d43f0a0cd2345f582dc8`.

Hai lưu ý:

- Mẫu Node.js chính thức lại dùng `JSON.stringify(body)`, tức serialize lại thân, trái với ghi chú của chính trang.
  Mã Python phải ký trên đúng chuỗi byte sẽ gửi. **[Đã kiểm]**
- **Không có SDK Python chính thức.** SDK chính thức chỉ có Java, Go, Node.js (*"The SDKs currently support Java, Go,
  and Node.js"*), tải trong Partner Center khi đã có app. Tổ chức GitHub `tiktok` (26 repo, tra qua
  https://api.github.com/orgs/tiktok/repos) không có SDK TikTok Shop; các SDK tìm thấy đều do cộng đồng làm và tự ghi
  "Unofficial". https://partner.tiktokshop.com/docv2/page/tts-api-sdk-overview (06/07/2026) **[Đã kiểm]**
- Mã `36009004` bị dùng lại cho nhiều lỗi: *"Do not use the numeric code alone for programmatic branching. Combine it
  with the response message keyword"*. Các mã khác: `105005` thiếu scope, `105002` token hết hạn, `101000` token sai
  `user_type`, `106013` thiếu `shop_cipher` (common-errors). **[Đã kiểm]**

---

## 5. Endpoint LIVE analytics

### 5.1 Token và scope theo metadata chính thức

Metadata tải qua `https://partner.tiktokshop.com/api/v1/document/api_meta?src_document_id=<id>`.

| Endpoint | Token | Scope · gói | Trả gì | Trang | Mức |
|---|---|---|---|---|---|
| `GET /analytics/202509/shop_lives/performance` | người bán, `user_type = 0` | `data.shop_analytics.public.read` · "TikTok Shop Analytics" | Danh sách phiên theo khoảng ngày; lọc `account_type` | get-shop-live-performance-list-202509 | [Đã kiểm] |
| `GET /analytics/202509/shop_lives/overview_performance` | người bán | như trên | Tổng mọi phiên của shop; `today=true` → số thời gian thực trong ngày | get-shop-live-performance-overview-202509 | [Đã kiểm] |
| `GET /analytics/202510/shop_lives/{live_id}/performance_per_minutes` | người bán | như trên | `intervals[]` theo phút (xem 5.2) | get-shop-live-minute-performance-202510 (14/07/2026) | [Đã kiểm] |
| `GET /analytics/202512/shop/{live_id}/products_performance` | người bán | như trên | Số liệu theo sản phẩm của phiên | get-shop-live-products-performance-list-202512 (26/08/2026) | [Đã kiểm] |
| `GET /analytics/202502/live_rooms/{id}/core_stats` và 6 endpoint cùng nhóm | **creator**, `user_type = 1` | `creator.data.live.read.public` · "Live Data" (gói ra mắt 02/07/2026) | `current_visitor_count`, `peak_concurrent_user_count`, đơn, bình luận tích lũy… | get-live-room-core-stats-202502 (20/07/2026) | [Đã kiểm] |

Cả bốn endpoint người bán đều có query `shop_cipher` bắt buộc (`is_shop_chiper_exist = True`). Tiền tố URL trang:
`https://partner.tiktokshop.com/docv2/page/`.

Chi tiết nhỏ: gói "Live Data", và gói "TikTok Shop Analytics" của `performance`/`overview_performance`, được liệt kê cả
loại Private lẫn Public; `performance_per_minutes` và `products_performance` chỉ ghi Public. **[Đã kiểm]**

Ngày 02/07/2026 là `launch_time` của **gói scope** "Live Data". Mã `api_basic_id` giải theo kiểu snowflake ra khoảng
09/2023, nên có thể API đã tồn tại nội bộ từ trước. **[Suy luận]**

### 5.2 `performance_per_minutes` — nguồn chính cho hậu kiểm

Nguyên văn phần mô tả (14/07/2026): *"Returns minute-level performance for a LIVE session after the session is
finished. This API only returns data for live streams hosted by the shop official account or marketing account."*
**[Đã kiểm]**

- Trường có trong tài liệu: `intervals[].start_time`/`end_time` (*"unix timestamp GMT (UTC+00:00)"*); `sales{gmv,
  items_sold, customers, sku_orders, main_orders}`; `traffic{viewers, views, product_impressions, ctr, enter_room_rate,
  product_clicks, impressions}`; `interactions{new_followers, shares, comments, likes, …}`;
  `conversion{created_sku_orders, …}`; `overall`, `next_page_token`, `total_count`. **[Đã kiểm]**
- `gmv` theo phút *"including returns and refunds"*. **[Đã kiểm]**
- GMV và đơn là số **quy đổi (attributed)** theo thông báo "Analytics Open API Metric Consistency Adjustment"
  (https://partner.tiktokshop.com/docv2/page/698d74de3a0ca3049812e044). **[Chưa kiểm lại]**
- **Độ trễ không được công bố.** Người kiểm chứng tìm các từ delay, latency, hour, T+1 trong trang và không thấy câu
  nào. **[Đã kiểm]** Tham khảo gián tiếp phía giao diện: trang LIVE Performance của Seller Center Mỹ ghi *"Diagnosis
  data is typically available within 1-2 days after the live session"*
  (https://seller-us.tiktok.com/university/essay?knowledge_id=6394088836597518&lang=en). **[Chưa kiểm lại]**

### 5.3 Trong lúc phát thì có gì?

| Endpoint | Trong lúc phát | Mức |
|---|---|---|
| `performance_per_minutes` | **Không**, chỉ sau khi phiên kết thúc | [Đã kiểm] |
| `overview_performance?today=true` | Có số *"real-time metrics of today (local time)"*, nhưng là **tổng mọi phiên của shop trong ngày** (granularity chỉ `ALL`/`1D`), không tách theo phiên và **không có số click hay lượt xem tuyệt đối**. Có `account_type` để loại live của affiliate | [Đã kiểm] |
| Lấy hiệu hai lần gọi đầu/cuối khối để ước lượng số của khối | Chỉ làm được với trường **cộng dồn** (`gmv`, `sku_orders`, `items_sold`); không làm được với `customers` hay các tỷ lệ; tài liệu không nói số "real-time" được làm mới bao lâu một lần | [Suy luận] — phải đo |
| `live_rooms/*/core_stats` | Có vẻ có (`current_visitor_count`), nhưng cần token creator | [Đã kiểm] phần token |
| `shop_lives/performance` có liệt kê phiên đang phát không | Tài liệu không nói | câu hỏi mở |

### 5.4 Nhịp gọi

- Hạn mức cấp động: *"The TTS Open Platform uses a dynamic QPS allocation mechanism"*; điểm khởi đầu gợi ý cho
  *"complex analytics: 0.2-1 request/second"*; `429` hoặc `36009002` thì backoff mũ + jitter, tôn trọng `Retry-After`
  (https://partner.tiktokshop.com/docv2/page/64f1991d64ed2e0295f3d2c0). **[Chưa kiểm lại]**
- Nhu cầu của LiveLift rất nhỏ: một phiên 90 phút cần vài trang `performance_per_minutes`, một lượt
  `products_performance`, một lượt `shop_lives/performance`. **[Suy luận]**

### 5.5 Ghép vào khối switchback

Khả thi, với các điều kiện:

1. Phiên phát từ **tài khoản chính thức hoặc tài khoản marketing của shop**; live của creator affiliate không có số theo
   phút. **[Đã kiểm]**
2. Lấy `live_id` qua `shop_lives/performance` với `account_type = OFFICIAL_ACCOUNTS`. **[Đã kiểm]** phần tham số
3. Gán mỗi phút vào khối theo `start_time` (UTC). Bộ nối trong kho **loại và đếm riêng** phút vắt qua ranh giới hai
   khối thay vì chia tỷ lệ; nó coi mỗi phút phủ ít nhất 60 giây kể từ `start_time`, vì mẫu phản hồi chính thức còn để
   `start_time == end_time` (`src/livelift/ingest/tiktok_shop.py`, hàm `gop_theo_khoi`). **[Đã kiểm]** bằng đọc mã
4. Ghi `source_tier = official`, phiên bản API, thời điểm kéo dữ liệu; kết luận nhân quả chỉ dùng số đã chốt. **[Suy luận]**
5. Can thiệp (ghim/bỏ ghim) vẫn **làm tay** theo lịch LiveLift.

---

## 6. Các chương trình khác của TikTok

| Chương trình | Có dữ liệu LIVE chính thức? | VN dùng được? | Nguồn | Mức |
|---|---|---|---|---|
| **Research API** | Không nhắc LIVE; mở cho *"Academic institutions in the U.S., EEA, UK, Canada, or Switzerland"*, tổ chức phi lợi nhuận ở EU, và Brazil **chỉ cho nghiên cứu an toàn trẻ em** | **Không** | https://developers.tiktok.com/products/research-api/ | [Đã kiểm] |
| **TikTok for Developers** (Login Kit, Share Kit, Content Posting, Embed, Display, Data Portability, Green Screen, Commercial Content, Mini Games, Mini Dramas) | Không có sản phẩm LIVE trên trang chủ và footer | — | https://developers.tiktok.com/ | [Đã kiểm], nhưng chỉ trong phạm vi trang chủ và footer (các trang con trả 302/401) |
| **Commercial Content API** | Không (nội dung quảng cáo) | Không (EU, EEA, UK, CH) | https://developers.tiktok.com/docs/en/commercial-content-api-supported-countries | [Chưa kiểm lại] |
| **Data Portability API** | Không | Không (chỉ người dùng EEA/UK) | https://developers.tiktok.com/products/data-portability-api/ | [Chưa kiểm lại] |
| **TikTok API for Business — LIVE GMV Max** | Một phần: báo cáo quảng cáo theo `room_ids`, chỉ khi phiên chạy quảng cáo | Có | https://github.com/tiktok/tiktok-business-api-sdk/blob/main/js_sdk/docs/ReportingApi.md | [Chưa kiểm lại] |
| **Partner Center LIVE Analytics/LIVE Dashboard** (đối tác TSP/CAP) | Giao diện, có *"read comments and view the pinned product"*; không phải API | Chỉ qua đối tác có pháp nhân | https://partner.tiktokshop.com/docv2/page/671754d18559ca030797dea5 | [Chưa kiểm lại] |
| **Agency Access to Live Manager** | Giao diện thay mặt creator; *"currently in beta and available only to allowlisted partners"* | Không cho đội | https://partner.tiktokshop.com/docv2/page/6864797b75134204a1f760cf | [Chưa kiểm lại] |
| **"TikTok LIVE API" trên mạng** (TikTokLive, Euler Stream…) | Không phải chương trình chính thức; là WebSocket dịch ngược | **Ngoài phạm vi** theo quyết định 17/09 | — | — |

### 6.1 Ghim sản phẩm qua API

Mô tả gói `creator.showcase.write` có câu *"manage the creator's products within the livestream such as adding,
removing, pinning, and unpinning"*, nhưng các API trong gói chỉ là `showcases/products/add|remove|top` (tủ trưng bày
hồ sơ creator). Báo cáo gốc tìm theo `pin` và `live` trong cây 956 trang và không thấy endpoint ghim trong LIVE.
Kết luận: **không ghim LIVE qua API**; nên theo dõi changelog vì mô tả gói gợi ý TikTok có thể mở sau.
https://partner.tiktokshop.com/docv2/page/top-showcase-products-202409 **[Chưa kiểm lại]**

---

## 7. Cộng đồng đã dùng thật chưa?

| Bằng chứng | Nội dung | Nguồn | Mức |
|---|---|---|---|
| PR dự án Laravel (tiền tệ MYR, Malaysia), 12/05/2026 | Đồng bộ `shop_lives/performance` bản 202509 hằng đêm; trước đó nhập tay CSV "Live Analysis" | https://github.com/aminpamelo/mudeerbedaie/pull/11 | [Thứ cấp], [Chưa kiểm lại] |
| ETL Python (múi giờ Asia/Jakarta, Indonesia), cập nhật 08/09/2026 | Tự ký như mẫu chính thức, gọi `shop_lives/performance` 7 ngày gần nhất | https://github.com/michaelAngelo1/shop-live-performance | [Thứ cấp], [Chưa kiểm lại] |
| Blog EchoTik, 06/08/2026 | *"Some LIVE analytics require creator authorization."* | https://www.echotik.live/blog/echotik-tiktok-shop-data-api/ | [Thứ cấp], người kiểm chứng đã đọc |
| Tìm trên GitHub | 0 kết quả liên quan cho `performance_per_minutes`, `live_rooms core_stats`, mã lỗi `66009315` | https://api.github.com/search/issues | [Chưa kiểm lại] |

Nếu LiveLift chạy được `performance_per_minutes` trên shop thật, nhóm sẽ thuộc số ít người công bố dùng endpoint này,
và **độ trễ phải tự đo**.

---

## 8. Điều khoản nhà phát triển — rủi ro lớn hơn báo cáo gốc đánh giá

Nguồn: Developer Terms of Service, *"Last Updated: May 22, 2025"*,
https://partner.tiktokshop.com/docv2/page/6506bc942f024f02be400315. **[Một phần]**: các câu trích đều đúng, nhưng báo
cáo gốc kết luận "chỉ cần thư đồng ý của shop" là **quá nhẹ**.

| Mục | Nguyên văn | Hệ quả cho LiveLift |
|---|---|---|
| 2.1 | *"a personal, non-exclusive, non-transferable, non-sublicensable, limited, revocable license"*; mục đích license là *"assisting Sellers to integrate their enterprise resource planning systems… and assisting Creators to authorize third parties to manage Creators' data"* | Shop đối tác **không được đưa khoá** cho nhóm. Nghiên cứu hay công bố **không nằm** trong các mục đích được liệt kê |
| 2.7(f) | *"You must obtain express permission from each End User before you share their data with any third parties."* | Cần đồng ý rõ ràng trước khi chia sẻ |
| 2.7(g) | *"You agree not to aggregate or otherwise utilize End User data for your own purposes."* | **Không có ngoại lệ "nếu được đồng ý"** như 2.7(f), nên thư đồng ý của shop **chưa chắc đủ** để nhóm dùng số liệu cho hồ sơ hay bài báo của chính nhóm |
| 3.5(b) | cấm *"sublicense to any third-party or permit any third-party, without TikTok's express written authorization, to browse, access or use the TTSPC"* | Củng cố: không mượn tài khoản hay khoá |
| 4 | *"All authentication procedures, information and data to which you gain access… is the Confidential Information of TikTok"*; không chia sẻ *"other than as required by a court, a regulator or otherwise under applicable laws"* | Công bố số liệu **kéo qua API** có thể vướng điều khoản bảo mật |

**Phương án an toàn hơn** (thứ tự ưu tiên):

1. Chủ shop **tự xuất** số liệu từ Seller Center rồi chia sẻ cho nhóm, kèm thư đồng ý mục đích nghiên cứu. Lưu ý:
   nhóm **chưa đọc điều khoản dành cho người bán** về việc chia sẻ file xuất từ Seller Center, nên đây vẫn là việc phải
   kiểm. **[Suy luận]**
2. Xin **văn bản cho phép của TikTok** qua ticket Partner Center trước khi công bố bất kỳ số nào kéo qua API.
3. Chỉ công bố số tổng hợp/ẩn danh; nhờ giảng viên hướng dẫn hoặc tư vấn pháp lý của trường xem thư đồng ý.

Trong hồ sơ 30/09, **không** hứa sẽ công bố số liệu TikTok của shop đối tác; chỉ nêu "đã tích hợp và kiểm chứng kỹ
thuật".

---

## 9. Điều kiện phía Việt Nam (chưa kiểm lại)

| Việc | Điều kiện | Nguồn | Mức |
|---|---|---|---|
| Mở shop cá nhân VN | Công dân VN ≥ 18 tuổi, CCCD; duyệt *"1 - 2 ngày"* khi hồ sơ hợp lệ | https://ghn.vn/blogs/tip-ban-hang/dang-ky-tiktok-shop | [Thứ cấp] |
| Tài khoản chính thức của shop | Một tài khoản chính thức cho mỗi cửa hàng; *"sẽ được cấp quyền đăng video và phát LIVE liên quan đến thương mại điện tử"* | https://ads.tiktok.com/help/article/about-official-accounts-in-seller-center?lang=vi | [Chưa kiểm lại] |
| Creator TikTok Shop VN | ≥ 18 tuổi, ≥ 1.000 follower, CCCD 12 số gắn chip, mã số thuế trùng số CCCD | https://seller-vn.tiktok.com/university/essay?knowledge_id=6837838528808705&role=2&course_type=1&from=search&identity=1 | [Chưa kiểm lại] |
| Phát LIVE bằng tài khoản chính thức của shop mới mà không cần 1.000 follower | Chỉ có nguồn thứ cấp | — | câu hỏi mở |
| Người livestream bán hàng phải cung cấp thông tin để nền tảng xác thực danh tính (Luật Thương mại điện tử 2025, hiệu lực 01/07/2026) | Áp dụng cho người dẫn trong mọi phiên thật | https://nghiencuu.tapchikinhtetaichinh.vn/luat-thuong-mai-dien-tu-2025-khung-phap-ly-moi-cho-livestream-ban-hang-va-tiep-thi-lien-ket-157230.html (đăng 26/05/2026) | [Thứ cấp], tổng biên tập đọc 17/09; nên đối chiếu văn bản luật gốc |

---

## 10. Hiện trạng trong kho (tổng biên tập kiểm ngày 17/09/2026)

- `src/livelift/ingest/tiktok_shop.py` (**chưa commit**): ký yêu cầu, gọi ba endpoint người bán, phân trang, phân loại lỗi
  tiếng Việt (tách `36009004` theo từ khoá trong `message`), giữ nhịp 0,2 yêu cầu/giây, che bí mật trong log, gộp số
  theo khối (`gop_theo_khoi`). Vector ký chính thức được khoá trong test. **Chưa nối** vào bộ thu nền, giao diện hay
  báo cáo phiên.
- `scripts/kiem_tra_tiktok_shop.py` (**chưa commit**): chỉ đọc; mã thoát 0 = đọc được ít nhất một phút dữ liệu,
  1 = lỗi chặn, 2 = chưa kiểm được theo phút (không có phiên hoặc phiên chưa có phút dữ liệu). Mã 2 **không** được ghi
  vào hồ sơ như đã chạy được.
- `tests/test_ingest_tiktok_shop.py`: **100 test đạt** khi tổng biên tập chạy lại ngày 17/09/2026.
- `tests/data/tiktok_shop/loi_tham_do_that_17092026.json`: phản hồi **thật** của cổng API khi gọi bằng danh tính giả.
  Ba đường dẫn thật trả HTTP 400 `36009004` *"Invalid credentials. Invalid 'app_key' query parameter"*; một đường dẫn bịa
  trả HTTP 404 `36009009 Invalid path`. Phép thử này chứng minh **endpoint tồn tại**, nhưng **không** chứng minh thuật
  toán ký, vì cổng chặn `app_key` trước khi kiểm chữ ký.
- **Chưa có:** lệnh đổi `code` lấy token và lấy `shop_cipher` (bước 5–6 ở `HUONG-DAN-LAY-KHOA-API.md` §5.2), bộ tự làm
  mới token 7 ngày.
- `collectors/tiktok_public/` (TikTokLive + Euler Stream) **giữ nguyên** theo quyết định chủ dự án; không dùng cho live
  thật.

---

## 11. Lộ trình 2 tuần (18/09 → 01/10/2026)

Người phụ trách theo làn ở `docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md`: Khánh sở hữu `src/livelift/ingest/`,
Minh lo hồ sơ và đối tác, Tiến lo minh chứng nhìn thấy được.

| Ngày | Minh (tài khoản đối tác, hồ sơ) | Khánh (Partner Center, mã) | Tiến (minh chứng) |
|---|---|---|---|
| **18–19/09** | Soạn danh sách 3–5 shop VN để liên hệ (mục 12, khuyến nghị 8) | Tạo tài khoản Partner Center bằng **email nhóm, không dùng email shop**; đăng ký App developer, thị trường VN local, **Save for later** phần chứng nhận; tạo custom app; kiểm tra gói TikTok Shop Analytics và Shop Authorized Information | Lập mẫu nhật ký minh chứng (ảnh chụp màn hình, `request_id`, giờ) |
| **22–23/09** | Gửi **ticket Partner Center** với 4 câu hỏi đầu ở mục 13 | Development Kits → tạo **shop thử VN Core Function (individual)** → Authorize App → đổi token (`grant_type=authorized_code`) → Get Authorized Shops lấy `shop_cipher` | Ghi nhật ký từng bước; không chụp khoá |
| **24–25/09** | Soạn thư đồng ý mẫu cho shop đối tác, theo mục 8 | Chạy `scripts/kiem_tra_tiktok_shop.py` trên shop thử; gọi thử `live_rooms/{id}/core_stats` bằng token người bán để **ghi lại mã lỗi thật** (dự kiến `101000`); lưu `request_id` | Chụp kết quả lệnh kiểm tra (mã thoát, không khoá) |
| **26–29/09** | Liên hệ shop theo tiêu chí ở khuyến nghị 8 | Viết lệnh đổi token + lấy `shop_cipher` (còn thiếu), test không mạng | Soạn đoạn minh chứng cho hồ sơ |
| **30/09** | Nộp hồ sơ với câu: *"đã tích hợp và kiểm chứng ký + ủy quyền với TikTok Shop Analytics API trên shop thử Việt Nam; dữ liệu LIVE thật triển khai cùng shop đối tác từ 10/2026"* — chỉ viết câu này nếu bước 22–25/09 **đã chạy xong** | — | — |

**Sau 30/09 đến chung kết:** nếu có đối tác (đường #4), chạy phiên thử 30 phút bằng tài khoản chính thức; sau phiên gọi
`performance_per_minutes` **mỗi 15 phút tới khi có dữ liệu, tối đa 48 giờ** để đo độ trễ; đối chiếu với file "Phân tích
LIVE" và dòng thời gian ghim do shop tự xuất. Mục tiêu 2–3 phiên switchback thật trước 20/11.

---

## 12. Khuyến nghị

1. **Sửa tài liệu cũ** theo mục 1 (D.3, mục Giới hạn, bảng A). Đường người bán chỉ có `shop_lives/*` và
   `products_performance`.
2. **Không chờ SDK.** Bộ ký Python trong kho đã khoá bằng vector chính thức; giữ quy tắc ký đúng byte thân, `timestamp`
   10 chữ số, không gửi `shop_cipher` cho endpoint không cần.
3. **Làm xong phần ủy quyền trên shop thử trước 25/09**, lưu `request_id` làm minh chứng.
4. **Adapter "hậu kiểm theo phút"**: `shop_lives/performance(account_type=OFFICIAL_ACCOUNTS)` →
   `performance_per_minutes` (phân trang) → `products_performance`; sau phiên poll 15 phút/lần tới 48 giờ để đo độ trễ;
   lưu `source_tier = official`, phiên bản API, `pulled_at`.
5. **Biến kết quả chính vẫn là click `/r/{code}`.** `product_clicks`, `sku_orders`, `comments` theo phút chỉ để đối
   chiếu chéo. Ghi trong phương pháp rằng GMV/đơn là số quy đổi và `gmv` theo phút gồm cả hàng hoàn.
6. **Hồ sơ 30/09 chỉ khẳng định điều đã kiểm.** Không tuyên bố có dữ liệu LIVE TikTok thật.
7. **Đường thủ công hợp lệ từ phiên thật đầu tiên:** chủ shop tự tải "Phân tích LIVE" và dòng thời gian sản phẩm được
   ghim (tab Nội dung) để kiểm độ lệch giữa lịch switchback và thời điểm ghim thật.
8. **Tìm 3–5 shop đối tác** theo tiêu chí: shop local VN đang ACTIVE, phát LIVE bằng tài khoản chính thức, đã có
   Account Manager hoặc là doanh nghiệp. Shop giữ app key/secret. Thư đồng ý nêu mục đích nghiên cứu, chỉ công bố số tổng
   hợp, và **ưu tiên để shop tự xuất dữ liệu** (mục 8).
9. **Không chạy quảng cáo LIVE GMV Max trong phiên thí nghiệm.** Nếu đối tác buộc phải chạy, kéo `gmv_max/report/get`
   lọc `room_ids` làm biến kiểm soát.
10. **Không đầu tư** vào đường creator (`live_rooms/*`) trước chung kết, cũng không vào Research API, Commercial Content
    API, Data Portability, Display/Login Kit.

## 13. Câu hỏi còn mở (đưa vào ticket tuần 22/09)

Bốn câu đầu gửi ticket Partner Center (https://partner.tiktokshop.com/ticket/center):

1. Tài khoản App developer **chưa duyệt chứng nhận doanh nghiệp** có vào được Development Kits → Development Shops để
   tạo shop thử VN không? Tài liệu chỉ nói *"complete enough to access Sandbox"*.
2. Shop thử (Full Function) VN có phát LIVE được không, và `shop_lives/*` có trả dữ liệu cho phiên thử không?
3. `performance_per_minutes` có dữ liệu sau bao lâu kể từ khi phiên kết thúc: vài phút, vài giờ hay T+1?
4. Custom app của seller developer ở VN có phải qua security review/DSPR không (onepager nói "mandatory", trang App
   review nói "usually not required")?
5. Ba endpoint người bán (202509, 202510, 202512) có chính thức áp dụng cho shop Việt Nam không?
6. `shop_lives/performance` có liệt kê phiên **đang phát** không?
7. Hạn mức của shop thử là 100 hay 1000 lượt/giờ?
8. Shop nhỏ mới mở có được gán Account Manager không, sau bao lâu? Chưa có nguồn chính thức.
9. `live_rooms/*` có thật sự thời gian thực không; `66009315` xảy ra khi nào; app VN có được mở scope creator không?
10. Mô tả gói `creator.showcase.write` nhắc ghim/bỏ ghim trong livestream: TikTok có sắp mở API ghim LIVE không?
11. Điều khoản dành cho người bán có cho phép chủ shop chia sẻ file xuất từ Seller Center cho nhóm nghiên cứu không?
