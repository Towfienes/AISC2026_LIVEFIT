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
| Ô "Lượt bấm" báo "không có link đo" khi đã tạo link mà chưa ai bấm (giới hạn #8 của HDSD) | Người vận hành tưởng link chưa được tạo | **ĐÃ SỬA** (`abbbeb1`) — `test_links_but_no_clicks_is_degraded_not_missing_and_never_ok`, `test_zero_links_is_missing_with_the_create_link_wording` |
| Facebook đọc bình luận với bộ lọc mặc định `filter_low_quality` | Bình luận "chất lượng thấp" bị Facebook **âm thầm** lọc khỏi dữ liệu | **ĐÃ SỬA** (`abbbeb1`) — gửi `live_filter=no_filter` + `order=chronological`; `test_every_real_poll_request_carries_no_filter_and_chronological`; **chưa có cuộc gọi thật** |

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

Cột *Lỗi* và *Mức* là ảnh chụp lúc đánh giá (trước commit `abbbeb1`). Cột *Trạng thái* cập nhật 17/09/2026
sau `abbbeb1`, theo quy ước ở đầu mục 2, kèm tên test hồi quy. Các test này phần lớn đọc mã nguồn web
(lớp CSS, nhánh hiển thị), một số chạy hàm thuần của web với API thật. Bố cục màn người dẫn trên điện thoại, nút thẻ #1
ở 1366×768 và thanh điều hướng di động **đã được đo lại trên trình duyệt thật** ở vòng kiểm chứng cuối
(mục 2.6).

| Lỗi | Mức | Trạng thái |
|---|---|---|
| Phát lại phiên mẫu hiện băng "PHÁT LẠI DỮ LIỆU THẬT" | P0 uy tín | **ĐÃ SỬA** — nhãn theo `is_demo` của máy chủ; `test_d1_phien_demo_tu_may_chu_duoc_ghi_du_lieu_mau`, `test_d1_dang_tai_thi_khong_khang_dinh_du_lieu_that` |
| Bấm thẻ A nhưng máy chủ bốc thăm ghim sản phẩm B, bàn không giải thích | P0 | **ĐÃ SỬA** — bàn nói rõ sản phẩm máy chủ đã bốc; `test_c3_boc_tham_that_cua_may_chu_duoc_noi_ro`, `test_c3_khong_boc_tham_thi_im_lang_khac_the_thi_noi` |
| Màn người dẫn vỡ bố cục trên điện thoại (chữ chồng, giá đè chân trang) | P0 | **ĐÃ SỬA** (test đọc mã, chưa chụp lại ảnh 390×844) — `test_d6_host_khong_con_khung_co_dinh_mot_man`, `test_d6_ten_hang_nho_o_man_hep_va_len_bac_hien_thi_o_man_rong` |
| Màn người dẫn mở trước khi phát sóng bị khoá vào phiên khác | P0 | **ĐÃ SỬA** — đọc `?session=`, không có thì chọn lại phiên đang phát mỗi lần poll; màn vẫn bị làm mù; `test_d7_ma_trong_link_uu_tien_tuyet_doi`, `test_d7_chon_lai_phien_moi_lan_poll_khong_phai_mot_lan_luc_tai`, `test_d7_man_host_van_bi_lam_mu` |
| Bàn trợ live ở 1366×768: nút hành động của thẻ #1 nằm dưới mép màn hình | P1 | **ĐÃ SỬA** (test đọc mã, chưa chụp lại ảnh 1366×768) — `test_c5_dau_trang_gon_khi_dang_phat`, `test_c5_the_lich_cao_vua_noi_dung_va_hero_hai_cot` |
| Bấm trong khối TẮT báo "kiểm tra kết nối API" thay vì lý do thật (giới hạn #6) | P1 | **ĐÃ SỬA** — hiện nguyên câu máy chủ, khoá nút theo lịch; `test_c1_409_khoi_tat_hien_nguyen_cau_may_chu`, `test_c1_chi_loi_mang_that_moi_noi_kiem_tra_ket_noi`, `test_c2_khoa_nut_theo_lich_that` |
| `/replay?session=` mở nhầm buổi (giới hạn #5); hai khung dưới luôn rỗng | P1 | **ĐÃ SỬA** — `test_d2_hook_uu_tien_ma_trong_link_va_mac_dinh_la_buoi_moi_nhat`, `test_d3_the_xep_lai_khong_bia_so`, `test_d3_cau_rong_noi_dung_ly_do_khong_day_nguoi_dung_di_tim` |
| Kết thúc phiên sớm, đồng hồ vẫn ghi "BẬT — chuyển khối sau…" | P1 | **ĐÃ SỬA** — hiện "ĐÃ KẾT THÚC" + nút xem báo cáo; `test_c4_hero_da_ket_thuc_thang_moi_trang_thai_khoi`, `test_c4_trang_thai_phien_theo_ca_poll_khong_chi_websocket` |
| Wizard bước 3 là tường chữ thuật ngữ và tự mâu thuẫn độ dài khối | P1 | **ĐÃ SỬA** — một câu tóm tắt khớp lịch thật, chi tiết kỹ thuật gập lại; `test_h3_buoc_3_mot_cau_tom_tat_va_khuyen_nghi_doi_thoi_luong`, `test_h3_tom_tat_khop_lich_that_30_phut`, `test_h3_chi_tiet_ky_thuat_nam_sau_details` |
| Thanh điều hướng trên điện thoại cắt chữ, đẩy chip chế độ ra ngoài; favicon 404 | P2 | **ĐÃ SỬA** (test đọc mã, chưa chụp lại ảnh 390×844) — `test_e2_topnav_khong_con_la_dai_cuon_ngang`, `test_e2_chip_che_do_luon_thay_tren_moi_do_rong`, `test_e1_app_co_bieu_tuong_svg_mau_brand_tren_nen_toi` |

### 2.5 Vận hành và hồ sơ

- GitHub Actions chưa từng chạy được một bước nào (nghi khoá thanh toán): CI trên badge README chưa phải
  bằng chứng.
- Toàn bộ commit mang một tác giả "LiveLift Team": thể lệ chấm lịch sử commit thật.
- Transcript Claude Code tự xoá sau 30 ngày, cần đặt `cleanupPeriodDays` để giữ Prompt Log.


### 2.6 Vòng kiểm chứng cuối — trình duyệt thật và phản biện hai phiếu

Sau khi sửa các lỗi ở mục 2.2 và 2.4, sản phẩm đi qua một vòng kiểm chứng độc lập gồm hai phần.

**Kiểm thử đầu-cuối trên bản build production** (`next build` + `next start`, Chromium thật, đo bằng
toạ độ phần tử chứ không chỉ nhìn ảnh):

| Luồng | Kết quả | Bằng chứng đo được |
|---|---|---|
| Nút hành động thẻ #1 ở 1366×768 | Đạt | Nút nằm ở y = 597–635 px, trong khung 768 px đầu, không cần cuộn |
| Bộ thu nguồn Mô phỏng trên phiên chạy thử | Đạt | Bình luận đầu tiên lên bàn sau 1,1 giây; bộ đếm 1 → 20 trong 16 giây; SĐT giả hiện `[SĐT]` |
| Chặn Mô phỏng trên phiên thật | Đạt | Không có tuỳ chọn trên giao diện; gọi thẳng API nhận 422 |
| Ghim trong khối BẬT, máy chủ bốc thăm | Đạt | Bàn ghi rõ "bốc thăm công bằng giữa 2 sản phẩm…, thẻ bạn bấm là …" |
| Khối TẮT | Đạt | Không còn nút Thực hiện; API 409; bàn không nói "kiểm tra kết nối" |
| Màn người dẫn 390×844 và 1366×768 | Đạt | Tên hàng, giá, tồn kho, đồng hồ không chồng nhau, đều trong khung; hiện hàng vừa ghim sau 0,37 giây |
| Làm mù màn người dẫn ở tầng mạng | Đạt | 114 phản hồi API không chứa `assignment`, `design_hash`, `block_index`, `propensity` |
| Kết thúc phiên, báo cáo, nhập CSV | Đạt | Nhập mới 2 · Lỗi 1 (đúng dòng ngày sai) · doanh thu 375.000 ₫; nhập lại ra Trùng 2 |
| Trang Bắt đầu, Kết quả, báo cáo mã sai | Đạt | Bảng nền tảng đúng; "KHÔNG CÓ PHIÊN NÀY" |
| Nút "Bắt đầu xem thử" khi mất API | **Trượt → ĐÃ SỬA** | Mở phiên mô phỏng phía trình duyệt nhưng ghi "DỮ LIỆU THẬT" |
| Ô "Bình luận / phút" khi bộ thu đang chạy | **Trượt → ĐÃ SỬA** | Luôn 0 dù bình luận đang về (tick không mang nhịp bình luận) |

**Phản biện theo bốn góc** (bảo mật và riêng tư, đúng đắn backend, logic web, hai gói chưa phản biện).
Mỗi phát hiện phải được **hai** người hoài nghi độc lập cùng xác nhận mới được giữ. Kết quả: **35 lỗi xác
nhận** (6 P1, 29 P2), gồm cả 7 lỗi quan sát trực tiếp trên trình duyệt và 7 lỗi tài liệu. **Cả 35 đã
được xử lý**, mỗi lỗi có test hồi quy; các lỗi đáng chú ý nhất:

| Lỗi | Hậu quả nếu không sửa |
|---|---|
| Nhấp đúp nút "Kết thúc phiên" vượt qua bước xác nhận (P1) | Kết thúc buổi live ngoài ý muốn, không hoàn tác được; đo được 36/36 lần trên Chrome |
| Facebook tự tìm buổi live chỉ dò một lần (P1) | Host phát lại là mất toàn bộ bình luận mà màn hình vẫn ghi "Đang thu" |
| Bình luận Mô phỏng do AI soạn lọt vào lô xuất gán nhãn NLP (P1) | Dữ liệu tổng hợp trộn vào tập huấn luyện, mất dấu nguồn gốc |
| Bộ thu nền vứt bình luận khi kho chập chờn | Mất dữ liệu âm thầm; nay giữ hàng đợi và ghi lại theo đúng thứ tự |
| Nhập CSV nhận đơn ngoài khung giờ phiên; khách vãng lai bơm 5.000 dòng mỗi lượt | Doanh thu gán sai phiên; ngập kho trên bản trưng bày |
| Log của bộ thu in nguyên `YOUTUBE_API_KEY` | Lộ khoá trong nhật ký |
| Màn người dẫn không tham số tự nhảy sang phiên mới hơn giữa buổi | Người dẫn đọc giá của hàng mẫu giữa buổi live thật |

---

## 3. Chạy với phiên live Facebook, YouTube, TikTok, Shopee như thế nào

Nguyên tắc: **chỉ đọc buổi live của chính mình hoặc của người đã ủy quyền, qua API chính thức**.
Đội đã quyết định không đọc bình luận kiểu người xem. Cách lấy khoá từng nền tảng:
`docs/HUONG-DAN-LAY-KHOA-API.md`; việc cần làm theo ưu tiên: `docs/VIEC-CAN-LAM.md`.

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
