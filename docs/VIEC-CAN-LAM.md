# Việc cần làm — trạng thái ngày 18/09/2026

*Viết cho đội LiveLift (Minh, Khánh, Tiến). Người phụ trách theo làn trong
`docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md`. Mỗi việc có tiêu chí "xong khi" để không ai
phải đoán. Kết quả chi tiết của đợt kiểm toán nằm ở
`docs/research/2026-09-17-danh-gia-toan-dien-va-lo-trinh-tu-dong.md`.*

## Mốc thời gian

| Mốc | Ngày |
|---|---|
| Nộp hồ sơ Sáng tạo trẻ AI (Bảng C, trường cử) | **30/09/2026** |
| Vòng Khu vực — hackathon 2 ngày, 60% điểm | **10–11/10/2026** |
| Chung kết — cải tiến 12 giờ, sản phẩm chạy ổn định ≥ 48 giờ | **20–22/11/2026** |

## Hiện trạng một đoạn

Sản phẩm đã có bộ thu bình luận chạy nền (bật bằng nút), nguồn Mô phỏng để kiểm thử, nhập đơn hàng
CSV, giao diện v3 đã sửa các lỗi P0/P1, và 1.555 test nhanh + 17 cổng Monte-Carlo + 10 test trình duyệt
đều xanh. **Điểm yếu lớn nhất không nằm ở mã:** chưa có khoá API thật nào, chưa có buổi live thật nào
đi qua đường chính thức, và vẫn **0 phiên thí nghiệm ngẫu nhiên thật**.

---

## P0 — làm ngay, xong trước 21/09

| # | Việc | Ai | Làm thế nào | Xong khi |
|---|---|---|---|---|
| 1 | Lấy **YouTube API key** | Khánh | `docs/HUONG-DAN-LAY-KHOA-API.md` mục 2 | Trang Bắt đầu ghi YouTube **Sẵn sàng** |
| 2 | Lấy **Facebook Page token** cho Fanpage của nhóm | Khánh | `docs/HUONG-DAN-LAY-KHOA-API.md` mục 3 | `scripts/kiem_tra_facebook.py` ra `KẾT LUẬN: SẴN SÀNG` |
| 3 | Xác minh kênh YouTube phát live, kiểm tra Fanpage đủ điều kiện phát | Tiến | Mục 2.5 và 3.4 của hướng dẫn trên | Bấm được "Phát trực tiếp" trên cả hai |
| 4 | **Buổi phát thử 30 phút** trên YouTube và Fanpage | Cả đội | Mục 7 của hướng dẫn trên | Thu ≥ 98% bình luận kịch bản, SĐT giả hiện `[SĐT]`, đã ghi hạn mức; nhật ký lưu theo `ops/templates/nhat-ky-phien.md` |
| 5 | **Quyết định về các đường không chính thức cũ** (xem mục "Quyết định cần chốt") | Minh | Họp 15 phút | Ghi quyết định vào `docs/incident-log.md` hoặc tài liệu này |

## P1 — trước khi nộp hồ sơ 30/09

| # | Việc | Ai | Làm thế nào | Xong khi |
|---|---|---|---|---|
| 6 | **Đồng bộ số liệu trong hồ sơ** — `noi-dung.md` §7.3 còn ghi 1.174 test và 47 sự cố | Minh | Sửa thành 1.555 test nhanh + 17 cổng Monte-Carlo + 10 test trình duyệt, 58 sự cố; thêm bộ thu nền, nhập đơn CSV, kết quả buổi phát thử; chạy `scripts/dong_bo_so_test.py --xem-truoc` và `scripts/do_lai_so_hieu_chuan.py --kiem`; dựng lại bằng `.venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/dung_ho_so.py` | PDF ≤ 20 trang, không còn ô ⬜, số khớp README |
| 7 | **Chụp lại ảnh** trong `docs/HUONG-DAN-SU-DUNG.md` — ảnh hiện là giao diện 11/09 | Tiến | Chạy local, chụp lại các bước có thay đổi (trang chủ, wizard bước 2–4, Bàn trợ live, màn người dẫn, phát lại, báo cáo) | Không còn ảnh cũ mâu thuẫn chữ hướng dẫn |
| 8 | **Chạy thật `docker compose up` với Postgres** trên một máy có quyền quản trị | Tiến + Minh | `docs/luu-tru-du-lieu.md`, `docs/competition/sang-tao-tre-2026/04-TRIEN-KHAI.md`; sau đó chạy `pytest -m db tests/test_store_contract.py` với `DATABASE_URL` trỏ vào Postgres | `/health` báo `durable: true`; test hợp đồng kho xanh trên Postgres |
| 9 | **Địa chỉ công khai HTTPS** cho link đo | Tiến | `04-TRIEN-KHAI.md` §4 (Oracle Cloud Free hoặc VPS theo giờ, tên miền `.id.vn`) | Điện thoại ngoài mạng nhà bấm được `https://<tên-miền>/r/<mã>` |
| 10 | **Giao diện web gửi được token** — bản công khai đặt `INGEST_TOKEN` thì nút bật bộ thu và nhập đơn đang bị từ chối | Minh + Tiến | Tối thiểu: ô nhập mã người vận hành lưu trong phiên trình duyệt, gắn header `Authorization` cho các lệnh ghi | Bản công khai khoá được đường ghi mà người vận hành vẫn dùng đủ nút |
| 11 | **Bật lại GitHub Actions** — CI chưa từng chạy được bước nào | Minh | Kiểm tra thanh toán/giới hạn ở Settings → Billing của tài khoản GitHub | Badge CI xanh từ một lần chạy thật |
| 12 | **Lọc lại dữ liệu gán nhãn** bằng bộ lọc handle mới rồi đo lại mô hình ý định | Khánh | `python -m livelift.nlp.eval_intent` sau khi lọc `data/labeling/` | Sự cố 15/09 về handle có dấu chuyển sang ĐÓNG |
| 13 | **Hai người gán nhãn lại tập kiểm tra**, đo độ đồng thuận κ | Khánh + Tiến | Bảng xáo trộn, gán mù, không mở `results.json` trước | Có số κ người–người thay cho nhãn do tác tử AI gán |
| 14 | **Giữ transcript làm Prompt Log** — Claude Code tự xoá sau 30 ngày | Khánh | Đặt `cleanupPeriodDays` trong cài đặt Claude Code; sao lưu thư mục transcript | Transcript từ 24/08 vẫn còn đủ |
| 15 | **Phiên thí nghiệm thật đầu tiên có khán giả** (nếu có shop đối tác đồng ý) | Cả đội | Tầng 3 trong tài liệu đánh giá mục 4; lịch gán sinh và niêm phong trước giờ phát | Có ≥ 1 phiên đủ điều kiện vào mẫu phân tích; nếu không kịp thì hồ sơ nói thẳng 0 phiên |

## P0b — việc mới từ đợt nghiên cứu 18/09 (TikTok, YouTube, thị trường)

*Nguồn: `docs/research/2026-09-17-tiktok-duong-chinh-thuc.md`,
`docs/research/2026-09-17-youtube-kiem-thu-chinh-thuc.md`,
`docs/research/2026-09-17-thi-truong-trung-quoc-an-do-va-bai-bao-moi.md`.*

| # | Việc | Ai | Làm thế nào | Xong khi |
|---|---|---|---|---|
| 24 | **Chạy `scripts/kiem_tra_youtube.py` ngay sau khi có API key** (việc 1) | Khánh | `.venv\Scripts\python scripts\kiem_tra_youtube.py --video <link buổi live>` | In `SẴN SÀNG`; ghi lại giá quota thật của `liveChatMessages.list` (1 hay 5 đơn vị) vào `docs/research/2026-09-17-youtube-kiem-thu-chinh-thuc.md` |
| 25 | **Tắt Dual stream khi phát thử YouTube** | Tiến | Trong YouTube Studio, chọn phát ngang, không bật luồng dọc | Link đo trong chat bấm được ở mọi thiết bị; ghi kết quả vào nhật ký phiên |
| 26 | **Đo lại hai câu hỏi còn mở của YouTube khi có key**: video Không công khai có đọc được chat không, buổi Sắp phát có `activeLiveChatId` trước giờ không | Khánh | Chạy công cụ kiểm tra với hai loại video | Ghi câu trả lời có bằng chứng vào tài liệu YouTube |
| 27 | **Xin Account Manager cho shop TikTok Shop** (điều kiện bắt buộc để đăng ký seller developer) | Minh | Gửi ticket "Account Manager eligibility review" ở Help Center của Seller Center | Có phản hồi bằng văn bản; nếu bị từ chối thì ghi vào tài liệu và chuyển sang đường xuất CSV |
| 28 | **Đọc điều khoản TikTok Shop trước khi dựa vào dữ liệu API cho hồ sơ** | Minh | Mục 8 của tài liệu TikTok: điều 2.7(g) cấm dùng dữ liệu người dùng cuối "for your own purposes", mục 4 coi dữ liệu là thông tin mật của TikTok | Quyết định ghi rõ: dùng API cho vận hành, còn số liệu công bố lấy từ tệp shop tự xuất, hoặc xin văn bản cho phép |
| 29 | **Tạo shop thử TikTok Shop (sandbox, có Việt Nam)** để chạy `scripts/kiem_tra_tiktok_shop.py` | Khánh | Partner Center → test shop; lưu ý shop thử có thể không có dữ liệu LIVE | Script chạy tới bước gọi API thật, dù dữ liệu rỗng |
| 30 | **Đưa các phương pháp đã chọn từ Trung Quốc vào hồ sơ và sản phẩm** | Minh | Bảng "phương pháp → áp dụng" trong tài liệu thị trường: ưu tiên chuẩn hoá theo người-xem-giây, phân tách theo nguồn lưu lượng, cảnh báo ngưỡng theo phút | Hồ sơ nêu được ít nhất 2 phương pháp có dẫn nguồn quốc tế |

## P2 — sau 30/09, cho hackathon và chung kết

| # | Việc | Ghi chú |
|---|---|---|
| 16 | Đăng ký **Shopee Open Platform** và gọi thật lần đầu | Chốt vùng Việt Nam; `HUONG-DAN-LAY-KHOA-API.md` mục 4 |
| 17 | Nối `update_show_item` của Shopee vào bộ thực thi tự động, tự làm mới token 4 giờ | Shopee là nền tảng duy nhất ghim được qua API |
| 18 | Bộ nối **TikTok Shop** hậu kiểm số liệu LIVE theo phút | Mục 5 của hướng dẫn khoá |
| 19 | Tự phát hiện buổi live bắt đầu: webhook Facebook `live_videos`, RSS + `videos.list` của YouTube; chuyển YouTube sang `liveChatMessages.streamList` | Giảm hạn mức, bớt thao tác tay |
| 20 | **Đăng nhập và tách dữ liệu theo người bán**; kết nối nền tảng bằng OAuth thay cho `.env` | ~2–3 tuần-người; điều kiện để nhiều người bán dùng chung |
| 21 | Khoá tư vấn Postgres để bộ thu và bộ thực thi chạy an toàn với nhiều worker | Hiện chỉ an toàn một tiến trình |
| 22 | Khoá **PREREGISTRATION.md** sau 5 phiên thăm dò, chốt độ dài khối | Điều kiện để công bố kết luận nhân quả |
| 23 | Bộ đồ nghề hackathon + diễn tập 8 giờ trên dữ liệu thô | Vòng Khu vực chiếm 60% điểm |
| 31 | Nối bộ nối TikTok Shop vào báo cáo phiên (đối chiếu GMV/đơn theo khối) | `src/livelift/ingest/tiktok_shop.py` đã có `gop_theo_khoi`; cần đường ghi và nhãn nguồn |
| 32 | Chuyển YouTube sang `liveChatMessages.streamList` (đẩy tin, ít lượt gọi hơn) | Giá quota của streamList chưa được công bố; đo sau khi có key |
| 33 | Đổi auth_code lấy token và tự làm mới token TikTok Shop | Hiện làm tay theo mục 5.2 của hướng dẫn khoá |

---

## Quyết định cần chốt

**Các đường đọc dữ liệu không chính thức còn trong kho.** Ngày 17/09/2026 đội quyết định **không** phát
triển hướng đọc bình luận kiểu người xem (lý do ở `docs/HUONG-DAN-LAY-KHOA-API.md` mục 0.1). Kho vẫn
còn ba thứ thuộc loại này, cần chốt giữ hay gỡ:

| Thành phần | Đang dùng cho | Khuyến nghị |
|---|---|---|
| `collectors/tiktok_public/` (TikTokLive + Euler Stream) | Bằng chứng phép đo 09/09: TikTok chặn 10/10 lần | Gỡ mã, giữ báo cáo đo `docs/benchmarks/tiktok-collector-2026-09.md` |
| Backend `INGEST_YOUTUBE_BACKEND=ytdlp` cho live | Dự phòng khi chưa có API key | Gỡ sau khi có YouTube API key (việc 1) |
| Phân tích VOD YouTube qua yt-dlp (`/replays/youtube`, Luồng 2 của hướng dẫn) | 19.126 bình luận live-fire, demo "phân tích buổi đã kết thúc" | Quyết định riêng: giữ thì ghi rõ là **quan sát, nguồn không chính thức** ở mọi nơi trình bày; gỡ thì phải thay số liệu trong hồ sơ |

**Chủ dự án đã chốt ngày 18/09/2026: GIỮ cả ba** cho tới khi có khoá chính thức chạy được, vì chưa chắc
xin được API TikTok. Tài liệu và giao diện phải tiếp tục ghi rõ chúng là nguồn không chính thức.

**Không làm (đã chốt):** tiện ích trình duyệt đọc bình luận, Playwright/Selenium mở trang live, WebSocket
dịch ngược, nhận dạng chữ từ màn hình, dịch vụ cào trả phí (Apify, ScrapeCreators, EnsembleData), SerpAPI
làm nguồn bình luận.
