# Đánh giá toàn diện LiveLift ngày 17/09/2026 — hạn chế, vấn đề, kiểm thử với live thật, lộ trình tự động hoá

> **Nguồn gốc tài liệu (khai thật):** do Claude (tác tử điều phối) soạn ngày 17/09/2026 từ một đợt kiểm
> toán nhiều tác tử: đọc mã nguồn, phép thử tái hiện lỗi chạy thật, ảnh chụp giao diện bằng Playwright,
> và nghiên cứu web có URL nguồn (`docs/research/2026-09-17-nen-tang-livestream-va-serpapi.md`). Mọi lỗi
> ghi "đã kiểm chứng" đều có phép thử tái hiện hoặc test hồi quy; mọi khẳng định về API nền tảng có URL.
> Viết cho: đội LiveLift và giảng viên hướng dẫn.

---

## 1. Kết luận ngắn

1. **LiveLift mạnh nhất ở phương pháp** (thiết kế switchback, suy diễn ngẫu nhiên hoá, khoá kết quả,
   làm mù người dẫn) **và yếu nhất ở chỗ chưa chạm dữ liệu thật**: vẫn **0 phiên thí nghiệm ngẫu nhiên
   thật**, và mọi khoá API nền tảng trong `.env` đều rỗng.
2. **Rào cản số một giữa "bản demo" và "sản phẩm tự chạy" đã được gỡ trong đợt này:** bộ thu bình luận
   trước chỉ chạy bằng lệnh terminal, nay chạy nền trong máy chủ và bật bằng nút trên web; đơn hàng trước
   không có đường ghi, nay nhập được bằng tay hoặc tệp CSV xuất từ Seller Center.
3. **Đợt kiểm toán tìm được nhiều lỗi thật mà bộ 1.157 test cũ không bắt**, trong đó có hai lỗi âm thầm
   làm hỏng dữ liệu: kho bộ nhớ lưu bình luận trùng khi tải cao, và link đo đếm thiếu click khi chạy sau
   proxy Caddy. Đường Shopee chưa từng lưu được một bình luận nào, và ký sai theo tài liệu gốc.
4. **Không nền tảng nào cho đọc live của người khác qua API chính thức**, trừ chat YouTube công khai. Đường
   đúng cho người bán là kết nối **tài khoản của chính mình**: Facebook Page, YouTube, Shopee Live (tài liệu
   Shopee có ghi Việt Nam), TikTok Shop (số liệu theo phút, chỉ sau khi phiên kết thúc).
5. **SerpAPI không dùng được cho livestream**: không đọc được bình luận, người xem, quà hay đơn; không có
   TikTok/Shopee. Chỉ đáng dùng gói miễn phí cho Google Trends và Google Shopping để chọn hàng ghim.

---

## 2. Hạn chế và vấn đề

Quy ước trạng thái: **ĐÃ SỬA** (có commit + test) · **MỘT PHẦN** · **CÒN MỞ** · **GIỚI HẠN NỀN TẢNG**
(không sửa được bằng mã).

### 2.1 Những gì chặn "sản phẩm tự chạy"

| # | Vấn đề | Trạng thái 17/09 | Ghi chú |
|---|---|---|---|
| 1 | Bộ thu bình luận chỉ chạy bằng lệnh terminal, phiên tạo trên web luôn "THIẾU nguồn" | **ĐÃ SỬA** | Bộ thu chạy nền (`POST /sessions/{id}/ingest`): chờ buổi live bắt đầu, thử lại khi mất mạng, dừng ngay khi thiếu khoá, tự dừng khi phiên kết thúc, tự nối lại sau khi máy chủ khởi động lại. Nút bấm ở Bàn trợ live và bước 4 của Chuẩn bị phiên |
| 2 | Không kiểm thử được đường ống đầu-cuối khi chưa có khoá nền tảng nào | **ĐÃ SỬA** | Nguồn `mo_phong`: kịch bản 200 bình luận tổng hợp (do tác tử AI soạn, khai rõ trong tệp) phát như một buổi live. Máy chủ chỉ cho dùng trên phiên chạy thử hoặc phiên mẫu |
| 3 | Không có đường ghi đơn hàng; tín hiệu "đối soát doanh thu" vĩnh viễn THIẾU | **ĐÃ SỬA** | `POST /sessions/{id}/orders` và `/orders/import` (CSV), chống trùng theo mã đơn, gán khối theo thời điểm đặt, không đọc cột người mua |
| 4 | Không có đăng nhập, không tách dữ liệu theo chủ (danh mục sản phẩm dùng chung toàn hệ thống) | **CÒN MỞ** | Ước lượng 2–3 tuần-người. Chặn cứng việc mở cho nhiều người bán cùng lúc |
| 5 | Kết nối nền tảng bằng cách dán khoá vào `.env` rồi khởi động lại; chưa có OAuth; token Shopee sống 4 giờ và chưa tự làm mới | **CÒN MỞ** | Trang Bắt đầu nay hiện nền tảng nào sẵn sàng và thiếu biến nào |
| 6 | Chưa tự phát hiện "buổi live vừa bắt đầu" từ phía nền tảng | **MỘT PHẦN** | Bộ thu tự chờ lên sóng khi đã biết nguồn; Facebook để trống nguồn thì tự tìm buổi đang phát trên Page. Chưa dùng webhook `live_videos` (Facebook) hay RSS + `videos.list` (YouTube) |
| 7 | Không ghim hộ được sản phẩm trên nền tảng | **GIỚI HẠN NỀN TẢNG** | YouTube, Facebook, TikTok không có API ghim. Shopee có `update_show_item`: client đã viết và test, **chưa nối vào bộ thực thi** |
| 8 | Bộ thực thi tự động và bộ thu chỉ an toàn khi máy chủ chạy **một** tiến trình | **CÒN MỞ** | Cần khoá tư vấn (advisory lock) trên Postgres trước khi chạy nhiều worker |
| 9 | Chưa có địa chỉ công khai HTTPS; `docker compose up` chưa từng chạy thành công trên máy nhóm (Docker daemon cần quyền quản trị) | **CÒN MỞ** | Việc của con người; thể lệ chung kết đòi chạy ổn định ≥ 48 giờ |

### 2.2 Lỗi kỹ thuật tìm được và đã kiểm chứng

| Lỗi | Hậu quả | Trạng thái |
|---|---|---|
| Kho bộ nhớ không an toàn đa luồng (route `def` của FastAPI chạy trong threadpool) | 8 luồng giao cùng một bình luận ra bản **trùng** ở 12/300 lượt | **ĐÃ SỬA** — khoá tái nhập cho mọi phương thức |
| `Broadcaster.publish` đụng hàng đợi asyncio từ luồng phụ | Bàn trợ live nhận cập nhật trễ tới khi có I/O khác | **ĐÃ SỬA** |
| Link đo `/r/{code}` băm địa chỉ của Caddy | Mọi người xem chung một vân tay, click hợp lệ bị đánh dấu vô hiệu — **biến kết quả chính bị đếm thiếu** | **ĐÃ SỬA** — chỉ tin `X-Forwarded-For` từ proxy tin cậy |
| `docker-compose.yml` không truyền `INGEST_TOKEN` và khoá nền tảng vào container | Bản công khai chạy với mọi đường ghi **mở** dù người vận hành tin là đã khoá | **ĐÃ SỬA** |
| API trả 422 cho bình luận gắn nhãn `shopee`, bộ thu vứt bản ghi | Đường Shopee có 26 test xanh nhưng **chưa từng lưu được một bình luận** | **ĐÃ SỬA** |
| Shopee Live ký bằng `shop_id`, và ký trên **phần đuôi** của đường dẫn | Theo tài liệu gốc (API loại "User", ký bằng `user_id` trên đường dẫn đầy đủ) sẽ bị từ chối khi chạy thật; test cũ khoá chặt cách ký sai | **ĐÃ SỬA** — vector ký tính độc lập bằng `openssl`; **chưa có cuộc gọi thật** |
| Lệnh bộ thu Shopee chạy trước giờ phát chết với traceback | Người vận hành không biết phải làm gì | **ĐÃ SỬA** |
| Bình luận đi qua bộ thu luôn có `pii_kinds` rỗng (lọc tại nguồn rồi máy chủ lọc lại chữ đã sạch) | Mất thông tin "loại dữ liệu cá nhân đã che" dùng cho báo cáo tuân thủ | **ĐÃ SỬA** |
| Ô "Lượt bấm" báo "không có link đo" khi đã tạo link mà chưa ai bấm (giới hạn #8 của HDSD) | Người vận hành tưởng link chưa được tạo | ⏳ đang sửa trong đợt này |
| Facebook đọc bình luận với bộ lọc mặc định `filter_low_quality` | Bình luận "chất lượng thấp" bị Facebook **âm thầm** lọc khỏi dữ liệu | ⏳ đang kiểm và sửa |

### 2.3 Dữ liệu, NLP và khoa học

| Vấn đề | Mức độ | Việc cần làm |
|---|---|---|
| **0 phiên thí nghiệm ngẫu nhiên thật**; mọi bằng chứng nhân quả là mô phỏng | Lớn nhất | Tầng 2 của kế hoạch kiểm thử (mục 4): live thật trên kênh của nhóm |
| Mọi khoá nền tảng trong `.env` rỗng | Chặn tầng 2 | YouTube API key (~10 phút), Facebook Page token (~25 phút) |
| Bộ phân loại ý định 0,565 đo trên **nhãn do tác tử AI gán**, n = 3 buổi; mặc định vẫn phục vụ bản v1 | Chưa đủ để ra quyết định | Hai thành viên gán lại tập kiểm tra trên bảng xáo trộn, đo κ |
| Dữ liệu gán nhãn cục bộ còn handle YouTube có dấu (lọc lại chưa chạy) | Dữ liệu cá nhân | Chạy lại bộ lọc lên `data/labeling/`, đo lại |
| Tiền đăng ký chưa khoá; độ dài khối chưa chốt vì chưa có 5 phiên thăm dò | Chặn kết luận khoa học | Sau các phiên thăm dò |
| Người xem thực đo 5–15 đồng thời, trong khi MDE 20,1% giả định ~45–62 | Kết quả có thể không đủ lực | Nói trước với hội đồng: sản phẩm bán hạ tầng đo lường, không bán con số đẹp |

### 2.4 Giao diện — đánh giá bằng ảnh chụp thật (1366×768, 1920×1080, 390×844)

**Điểm tốt đã xác nhận:** wizard 4 bước rõ và giữ tiến độ trên URL; đồng hồ khối BẬT/TẮT và đếm ngược
đọc được trong một cái liếc; cảnh báo sắp đổi khối không nhấp nháy; trạng thái rỗng của Bàn trợ live có
hướng dẫn; màn người dẫn ở 1366 đẹp và tối giản.

| Lỗi | Mức | Trạng thái |
|---|---|---|
| Phát lại phiên mẫu hiện băng "PHÁT LẠI DỮ LIỆU THẬT" | P0 uy tín | ⏳ |
| Bấm thẻ A nhưng máy chủ bốc thăm ghim sản phẩm B, bàn không giải thích | P0 | ⏳ |
| Màn người dẫn vỡ bố cục trên điện thoại (chữ chồng, giá đè chân trang) | P0 | ⏳ |
| Màn người dẫn mở trước khi phát sóng bị khoá vào phiên khác | P0 | ⏳ |
| Bàn trợ live ở 1366×768: nút hành động của thẻ #1 nằm dưới mép màn hình | P1 | ⏳ |
| Bấm trong khối TẮT báo "kiểm tra kết nối API" thay vì lý do thật (giới hạn #6) | P1 | ⏳ |
| `/replay?session=` mở nhầm buổi (giới hạn #5); hai khung dưới luôn rỗng | P1 | ⏳ |
| Kết thúc phiên sớm, đồng hồ vẫn ghi "BẬT — chuyển khối sau…" | P1 | ⏳ |
| Wizard bước 3 là tường chữ thuật ngữ và tự mâu thuẫn độ dài khối | P1 | ⏳ |
| Thanh điều hướng trên điện thoại cắt chữ, đẩy chip chế độ ra ngoài; favicon 404 | P2 | ⏳ |

### 2.5 Vận hành và hồ sơ

- GitHub Actions chưa từng chạy được một bước nào (nghi khoá thanh toán): CI trên badge README chưa phải
  bằng chứng.
- Toàn bộ commit mang một tác giả "LiveLift Team": thể lệ chấm lịch sử commit thật.
- Transcript Claude Code tự xoá sau 30 ngày, cần đặt `cleanupPeriodDays` để giữ Prompt Log.

---

## 3. Chạy với phiên live Facebook, YouTube, TikTok, Shopee như thế nào

Nguyên tắc: **chỉ đọc buổi live của chính mình hoặc của người đã ủy quyền, qua API chính thức**.

| Nền tảng | Đọc bình luận | Người xem | Đơn hàng | Ghim qua API | Cần chuẩn bị |
|---|---|---|---|---|---|
| **YouTube** | Chính thức (`liveChatMessages`), cả kênh người khác | Chính thức | Không có | Không có | `YOUTUBE_API_KEY` miễn phí (Google Cloud Console → bật YouTube Data API v3 → tạo API key), ~10 phút |
| **Facebook** (Page của mình) | Chính thức (`/comments`, `live_filter=no_filter`) | Chính thức (`live_views`) | Không có | Không có | Page token có `pages_read_engagement` **và** `pages_read_user_content`; phát live qua phần mềm cần tài khoản ≥ 60 ngày, Page ≥ 100 người theo dõi |
| **Shopee Live** (shop mình) | Chính thức, cửa sổ 10 giây | Chính thức | **Chính thức** (GMV, đơn, thêm giỏ) | **Có** (`update_show_item`) | Tài khoản Shopee Open Platform + ủy quyền; `SHOPEE_USER_ID`; phải có một cuộc gọi thật để chốt vùng Việt Nam |
| **TikTok Shop** | Không có nội dung, chỉ số đếm | Chính thức | **Chính thức, theo phút, sau khi phiên kết thúc** | Không có | App "Seller in-house" gắn shop; biến kết quả đo **hậu kiểm** |
| **TikTok LIVE thường** | Không có API chính thức | Không có | Không có | Không có | Mọi công cụ trên thị trường dùng WebSocket không chính thức — không dùng cho dữ liệu nghiên cứu |
| **Lazada, Instagram** | Chưa xác minh / cần App Review | — | — | — | Để sau |

**Với nền tảng không ghim được qua API**, LiveLift làm "trợ lý": Bàn trợ live nói khi nào ghim sản phẩm
nào, người vận hành bấm ghim trên app, còn click được đo độc lập bằng link đo `/r/{code}` của chính
LiveLift. Đơn hàng nhập bằng tệp CSV xuất từ Seller Center sau buổi live.

---

## 4. Kiểm thử ba tầng

| Tầng | Làm gì | Tiêu chí qua tầng |
|---|---|---|
| **1 — không cần phát live** | (a) Bộ test tự động; (b) bật bộ thu với nguồn **mô phỏng** trên một phiên chạy thử và xem bình luận chảy vào Bàn trợ live; (c) phân tích VOD YouTube đã kết thúc; (d) test hợp đồng từ mẫu phản hồi trong tài liệu API | Bình luận vào kho đã che SĐT; bàn cập nhật trong vài giây; không lỗi |
| **2 — live thật của nhóm, không khán giả ngoài** | YouTube (OBS, không công khai, 30 phút) và Facebook Page của nhóm; 3 thành viên gửi bình luận theo kịch bản có mã duy nhất; một người ghim theo lịch LiveLift | Thu đủ ≥ 98% bình luận kịch bản; độ trễ đo được; hạn mức YouTube dự phóng cho 90 phút ≤ 30% ngày |
| **3 — thí điểm với khán giả thật** | Một shop đối tác có văn bản đồng ý; lịch gán sinh và niêm phong trước giờ phát; LiveLift gợi ý, người dẫn thực hiện | Phiên đưa được vào mẫu phân tích theo quy tắc tiền đăng ký |

---

## 5. SerpAPI

**Không phù hợp làm nguồn dữ liệu livestream.** SerpAPI cào trang kết quả tìm kiếm (Google, YouTube Search,
Amazon…). Không engine nào đọc chat live, người xem đồng thời, quà hay đơn hàng; không có engine TikTok,
Shopee hay Lazada. Tìm video YouTube đang live thì API chính thức rẻ hơn. Giá trị thật duy nhất là Google
Trends và Google Shopping để chọn hàng ghim và khung giờ phát; gói miễn phí 250 lượt/tháng là đủ.

---

## 6. Lộ trình tự động hoá

| Giai đoạn | Việc | Trạng thái |
|---|---|---|
| **A — xong 17/09** | Bộ thu chạy nền + nút bấm; nguồn mô phỏng; ghi đơn và nhập CSV; mức sẵn sàng nền tảng; sửa 10+ lỗi kiểm chứng | Xong, có test |
| **B — trước 30/09** | Chạy tầng 2 trên YouTube và Facebook của nhóm; địa chỉ công khai HTTPS; nối Shopee `update_show_item` vào bộ thực thi; phát hiện live bằng webhook Facebook `live_videos` và RSS YouTube; YouTube `streamList` | Chưa làm |
| **C — hackathon và chung kết** | Đăng nhập và tách dữ liệu theo chủ; OAuth cho từng nền tảng; tự làm mới token Shopee; adapter TikTok Shop hậu kiểm theo phút; khoá tư vấn cho nhiều worker; thông báo Telegram/Zalo cho người vận hành | Chưa làm |

---

## 7. Việc chỉ con người làm được

1. Xin `YOUTUBE_API_KEY` và Facebook Page token, dán vào `.env`, khởi động lại máy chủ.
2. Phát một buổi live thử 30 phút trên kênh của nhóm (tầng 2).
3. Đăng ký Shopee Open Platform hoặc TikTok Shop Partner nếu có shop thật để thử.
4. Lấy máy chủ và tên miền cho địa chỉ công khai; chạy liên tục 48 giờ trước chung kết.
5. Gán lại tập kiểm tra ý định bằng hai người để đo κ.
