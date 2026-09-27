# Kịch bản và lời dẫn lồng tiếng cho 2 video bắt buộc (Bảng C, đường trường cử)

**Sản phẩm:** LiveLift - Nền tảng thí nghiệm vận hành và hỗ trợ ra quyết định cho livestream thương mại.

*Căn cứ: `BRIEF-THE-LE.md` phần 3. Mỗi video tối đa 5 phút; thiếu một trong hai video là bị loại về hình thức.
Viết lại ngày 27/09/2026. Hai video đã được dựng sẵn phần hình (slide và bản quay màn hình tự động của
sản phẩm thật); đội chỉ cần **lồng tiếng** theo lời dẫn dưới đây. Mốc thời gian khớp với tệp video đã dựng
(dữ liệu ghép video của đợt dựng ngày 27/09/2026). Nếu dựng lại video thì mốc có thể lệch vài giây,
khi đó lấy mốc trong tệp phụ đề `.srt` đi kèm video làm chuẩn.*

## Ba quy tắc cho cả hai video

1. **Chỉ nói con số có trong `docs/competition/FACT-SHEET.md` và hồ sơ dự án.** Bảng "Số được phép nói" ở cuối
   tệp là danh sách duy nhất. Giám khảo Bảng C được quyền kiểm tra, xác minh sản phẩm; một con số trong video
   lệch hồ sơ là mất điểm.
2. **Không có dữ liệu cá nhân thật trên hình.** Mọi bình luận trên hình lấy từ nguồn Mô phỏng (200 câu tổng hợp
   do tác tử AI soạn, số điện thoại trong đó là số giả) trên một phiên chạy thử. Không mở bản phát lại của người
   khác, không mở `.env`, không mở `data/labeling/`.
3. **Không cắt ghép che bước.** Điều 5 khoản 7 Thể lệ cấm giả mạo video demo. Phần giữa video demo là nguyên một
   lượt quay tự động; chỗ nào tua nhanh hay chuyển cảnh thì ghi rõ trên hình.

Nhịp đọc gợi ý khoảng 4 đến 4,5 âm tiết mỗi giây, tức nhịp thuyết trình vừa phải. Một người có thể đọc cả video;
cột "Người đọc" của video 1 chỉ là gợi ý nếu muốn chia cho ba bạn. Cách đọc một số từ: "macro-F1" đọc là
"ma-crô ép một", "yt-dlp" đọc là "y t d l p", "A/B test" đọc là "A B test".

---

## VIDEO 1: THUYẾT TRÌNH (4 phút 44 giây, trần 5 phút)

Thể lệ yêu cầu đủ 5 nội dung theo thứ tự: vấn đề, phương pháp xây dựng giải pháp, kết quả đạt được, giá trị thực
tiễn, khả năng phát triển. Hình là 12 slide; chữ trên slide hiện dần đúng lúc câu tương ứng
bắt đầu.

| Mốc | Hình trên màn | Người đọc | Lời dẫn (đọc gần nguyên văn) |
|---|---|---|---|
| 0:01 đến 0:14 | Slide 1: Mở đầu | Minh | Chúng em là đội LiveLift, Trường Đại học Tôn Đức Thắng, gồm Minh, Khánh và Tiến. LiveLift là nền tảng thí nghiệm vận hành và hỗ trợ ra quyết định cho livestream thương mại. Nói gọn, LiveLift đo xem một quyết định trong phiên live có thật sự giúp bán được hơn hay không. |
| 0:16 đến 0:23 | Slide 2: Vấn đề: lượt nhấp tăng, nhưng vì đâu? | Minh | Hãy bắt đầu bằng một tình huống quen thuộc. Phút thứ 30, người trợ live ghim sản phẩm B. Năm phút sau, lượt nhấp vào B tăng lên. |
| 0:24 đến 0:29 | Slide 2 | Minh | Vì vừa ghim, vì nền tảng vừa đẩy thêm người vào phòng, hay vì người dẫn vừa kể một câu chuyện hay? |
| 0:29 đến 0:32 | Slide 2 | Minh | Nhìn số liệu sau phiên, không ai tách được ba khả năng này. |
| 0:33 đến 0:42 | Slide 3: Vấn đề: nhà bán chưa có công cụ để tự đo | Minh | Công cụ của nền tảng trả lời câu hỏi phiên này bán được bao nhiêu. Chưa có công cụ nào nhà bán tự dùng được để biết bao nhiêu trong đó là nhờ hành động của mình. |
| 0:43 đến 0:56 | Slide 3 | Minh | Thí nghiệm ngẫu nhiên trong livestream đã đo được tác động như vậy. Ví dụ, khi người dẫn được xem số bán theo thời gian thực, doanh số hàng đặt trước tăng khoảng 40%. Nhưng các thí nghiệm đó do nền tảng chạy, còn nhà bán không sở hữu nền tảng. |
| 0:57 đến 1:04 | Slide 4: Phương pháp: chia thời gian thay vì chia người xem | Khánh | Phần thứ hai là phương pháp. Trong livestream, cả phòng cùng nhìn một màn hình, nên không thể chia người xem thành hai nhóm như A/B test. |
| 1:05 đến 1:17 | Slide 4 | Khánh | Thứ chia được là thời gian. Phiên 90 phút được chia thành 16 khối. Khối đầu và khối cuối dài 10 phút, 14 khối ở giữa mỗi khối 5 phút. Mỗi khối được bốc thăm để bật hoặc tắt can thiệp, ví dụ ghim một sản phẩm. |
| 1:18 đến 1:26 | Slide 5: Phương pháp: ba nguyên tắc để kết quả đáng tin | Khánh | Để kết quả đáng tin, hệ thống giữ ba nguyên tắc. Một, lịch bốc thăm được lưu kèm một mã băm trước giờ phát. Chưa có lịch thì hệ thống không cho lên sóng. |
| 1:27 đến 1:36 | Slide 5 | Khánh | Hai, màn hình của người dẫn không có lịch khối, để người dẫn không đổi cách nói theo lịch. Người dẫn vẫn thấy sản phẩm đang ghim, nên thứ được đo là cả chiến lược ghim. |
| 1:37 đến 1:44 | Slide 5 | Khánh | Ba, kết quả được tính bằng kiểm định ngẫu nhiên hóa, tức là bốc thăm lại bằng đúng hàm gán đang chạy. Không đủ dữ liệu thì hệ thống nói là chưa đủ. |
| 1:45 đến 1:54 | Slide 6: Phương pháp: phần AI nằm ở hai chỗ | Khánh | Phần AI của sản phẩm nằm ở hai chỗ. Thứ nhất là bộ lọc che số điện thoại, địa chỉ và tên tài khoản ngay khi bình luận vào hệ thống, trước khi ghi xuống đĩa. |
| 1:55 đến 2:05 | Slide 6 | Khánh | Thứ hai là bộ phân loại ý định mua cho bình luận tiếng Việt, giúp người trợ live thấy khách đang hỏi giá hay đang chốt đơn. Nhãn ý định chỉ hiện trên bàn điều khiển, không dùng để tính tác động. |
| 2:06 đến 2:18 | Slide 7: Kết quả: kiểm tra cái thước trước khi đo | Tiến | Phần thứ ba là kết quả. Trước khi đo người bán, chúng em kiểm tra cái thước trên mô phỏng có đáp án. Chạy 200 thí nghiệm giả không có tác động, hệ thống báo nhầm 3,50% số lần, dưới mức 5% cho phép. |
| 2:19 đến 2:23 | Slide 7 | Tiến | Với tác động biết trước, ước lượng chỉ lệch −0,84%. |
| 2:24 đến 2:27 | Slide 7 | Tiến | Và khoảng tin cậy chứa đúng giá trị thật 37 trên 40 lần. |
| 2:28 đến 2:36 | Slide 8: Kết quả: bộ phân loại ý định | Tiến | Với bộ phân loại ý định, chúng em nói cả số chưa đẹp. Trên câu mẫu do AI soạn, điểm macro-F1 là 0,870. |
| 2:36 đến 2:39 | Slide 8 | Tiến | Nhưng trên chat thật, điểm chỉ còn 0,211. |
| 2:40 đến 2:57 | Slide 8 | Tiến | Sau khi làm lại bộ nhãn và dữ liệu, điểm lên 0,542. Chấm cùng thang 6 lớp với bản cũ thì từ 0,370 lên 0,572. Bản mới báo đúng hơn, nhưng bắt được ít trường hợp hơn. Các điểm này đo so với nhãn tham chiếu do tác tử AI gán, chưa phải nhãn người. |
| 2:59 đến 3:18 | Slide 9: Kết quả: đã làm được và điều chưa có | Tiến | Hệ thống đã nạp 19.126 bình luận quan sát từ 16 buổi phát lại trên YouTube, tải bằng yt-dlp, không qua API chính thức và chưa có sự đồng ý của người bình luận. Hồ sơ ghi rõ điều này. Mã nguồn có 2.116 kiểm thử tự động và 121 sự cố được phân tích nguyên nhân gốc. |
| 3:19 đến 3:23 | Slide 9 | Tiến | Điều chưa có: chưa có phiên thí nghiệm ngẫu nhiên thật nào. Con số hôm nay là 0 phiên. |
| 3:25 đến 3:45 | Slide 10: Giá trị thực tiễn | Minh | Phần thứ tư là giá trị thực tiễn. Nhà bán không cần sở hữu TikTok hay Facebook, họ chỉ bốc thăm hành động của chính mình theo thời gian. Mã nguồn mở, chạy trên một máy tính cá nhân, không cần GPU. Nghị quyết 57 coi khoa học, công nghệ và chuyển đổi số là đột phá quan trọng hàng đầu. LiveLift đưa cách làm thí nghiệm vào kênh bán hàng lâu nay chạy bằng kinh nghiệm. |
| 3:46 đến 4:02 | Slide 10 | Minh | Chúng em cũng nói rõ ai dùng được. Trên mô phỏng, với khoảng 59 người xem và 8 phiên, mức tăng lượt nhấp nhỏ nhất phát hiện được là 16,4%. Nhà bán chỉ có 5 đến 15 người xem thì chỉ thấy được tác động rất lớn. Con số 5 đến 15 là ước tính từ giá quảng cáo, chưa đo. |
| 4:04 đến 4:12 | Slide 11: Khả năng phát triển | Tiến | Phần cuối là khả năng phát triển. Trước vòng Khu vực, chúng em sẽ có khóa API YouTube chính thức, phát thử trên kênh của nhóm, và gán nhãn người cho tập kiểm tra. |
| 4:13 đến 4:19 | Slide 11 | Tiến | Tháng 10 và 11, chúng em tìm nhà bán đối tác và chạy phiên ngẫu nhiên thật đầu tiên khi có văn bản đồng ý. |
| 4:20 đến 4:24 | Slide 11 | Tiến | Trước vòng Chung kết, sản phẩm chạy trên một địa chỉ công khai liên tục 48 giờ. |
| 4:25 đến 4:31 | Slide 11 | Tiến | Hướng mở rộng gần nhất là TikTok Shop, qua API chính thức, cùng với đăng nhập và tách dữ liệu theo từng nhà bán. |
| 4:32 đến 4:43 | Slide 12: Kết thúc | Khánh, Tiến, Minh, mỗi người một câu | LiveLift không hứa làm bạn bán nhiều hơn. Nó cho bạn biết hành động nào thật sự có tác dụng, kèm khoảng tin cậy. Mã nguồn và mọi số liệu có trong kho GitHub trên màn hình. Cảm ơn thầy cô đã lắng nghe. |

**Ba điều bắt buộc giữ trong video 1** (có thể đổi cách nói, không bỏ ý):

1. Nói cả số chưa tốt: 0,211 trên chat thật, 0 phiên thí nghiệm thật, dữ liệu tải bằng yt-dlp chưa có sự đồng ý.
2. Nói rõ nhãn tham chiếu do tác tử AI gán, chưa phải nhãn người; màn người dẫn chỉ che lịch một phần.
3. Không nói "API chính chủ" cho 19.126 bình luận, không nói "địa chỉ demo công khai" khi chưa có; con số 5 đến 15
   người xem luôn đi kèm chữ "ước tính từ giá quảng cáo, chưa đo".

---

## VIDEO 2: DEMO SẢN PHẨM (4 phút 26 giây, trần 5 phút)

Thể lệ yêu cầu quay: quá trình vận hành, các chức năng chính, kết quả xử lý, khả năng tích hợp, khả năng ứng dụng.
Hình là **bản quay màn hình tự động của sản phẩm thật**: ngày 25/09/2026, trình duyệt do Playwright điều khiển
(`scripts/chup_giao_dien.py quay`, kịch bản bấm do tác tử AI viết) chạy LiveLift bản build trên máy của nhóm,
với dữ liệu mẫu có nhãn DEMO và một phiên chạy thử tạo ngay lúc quay. Phần giữa video là nguyên một lượt quay,
không cắt ghép bên trong; đầu và cuối có thẻ tên sản phẩm và link GitHub. Mỗi cảnh có thẻ tên phần ở góc trên.

| Mốc | Cảnh | Lời dẫn (đọc gần nguyên văn) |
|---|---|---|
| 0:00 đến 0:03 | Mở đầu | Đây là bản quay màn hình tự động của sản phẩm thật. |
| 0:03 đến 0:10 | Mở đầu | Mọi màn hình đều ghi rõ đâu là dữ liệu mẫu, đâu là dữ liệu thật. Hôm nay mọi bình luận là dữ liệu mô phỏng. |
| 0:11 đến 0:22 | Vận hành (1): chuẩn bị phiên | Bước đầu là chuẩn bị phiên. Chúng em dùng sản phẩm mẫu và điền link mẫu. Mỗi sản phẩm có một link đo riêng, lượt bấm vào link là con số hệ thống dùng để kết luận. |
| 0:23 đến 0:28 | Vận hành (1): chuẩn bị phiên | Buổi live chọn YouTube, 90 phút, chế độ chạy thử. |
| 0:28 đến 0:34 | Vận hành (1): chuẩn bị phiên | Bấm bốc thăm, hệ thống sinh lịch 16 khối bật và tắt. |
| 0:34 đến 0:52 | Vận hành (1): chuẩn bị phiên | Lịch được lưu kèm mã băm của tham số và hạt giống, trước giờ phát. Mục chi tiết kỹ thuật hiện mã bằng chứng của lịch và hạt giống bốc thăm. Ai giữ tệp thiết kế cũng tính lại được mã này, để thấy lịch không bị sửa. |
| 0:53 đến 1:04 | Vận hành (2): cổng chặn | Tiếp theo là cổng chặn. Chúng em mở trang tài liệu API và gọi lệnh bắt đầu phát sóng cho một phiên vừa tạo nhưng chưa bốc lịch. |
| 1:06 đến 1:13 | Vận hành (2): cổng chặn | Máy chủ trả về mã 409. Phiên chưa có lịch thì chính người tạo cũng không cho lên sóng được. |
| 1:14 đến 1:24 | Vận hành (3): lên sóng | Quay lại phiên đã bốc lịch. Ở bước cuối, đội rà danh sách kiểm tra trước giờ phát, rồi bấm bắt đầu phát sóng. |
| 1:25 đến 1:36 | Vận hành (3): lên sóng | Sau khi lên sóng mới bật bộ thu bình luận với nguồn mô phỏng. Nguồn này chỉ dùng được cho phiên chạy thử, phiên thật bị máy chủ từ chối. |
| 1:36 đến 1:52 | Chức năng chính (1): bàn trợ live | Đây là bàn trợ live. Phía trên là khối đang chạy, đồng hồ đếm tới lúc chuyển khối và lịch bật tắt. Bình luận mô phỏng bắt đầu chảy vào, kèm số người xem và số bình luận mỗi phút. |
| 1:53 đến 2:05 | Chức năng chính (1): bàn trợ live | Đây là một số điện thoại giả trong kịch bản mô phỏng, và đây là thứ được ghi xuống: [SĐT]. Bộ lọc chạy trước khi ghi đĩa. |
| 2:06 đến 2:21 | Chức năng chính (1): bàn trợ live | Radar ý định cho người trợ live thấy khách đang hỏi giá, hỏi size hay chốt đơn. Bản đang chạy mặc định là bản cũ, và nhãn này không dùng để tính tác động. |
| 2:22 đến 2:39 | Chức năng chính (2): màn người dẫn | Cùng một phiên, bên trái là bàn trợ live, bên phải là màn người dẫn. Màn người dẫn chỉ có thời gian, sản phẩm đang ghim, giá và tồn kho, không có lịch khối. Người dẫn vẫn thấy sản phẩm đang ghim, nên thứ được đo là cả chiến lược ghim. |
| 2:40 đến 2:49 | Kết quả xử lý | Kết thúc phiên cần xác nhận hai bước, rồi mở báo cáo phiên. |
| 2:50 đến 3:01 | Kết quả xử lý | Báo cáo ghi rõ đây là phiên chạy thử, không tính vào kết quả gộp. Nguồn nào chưa có dữ liệu thì báo cáo ghi là thiếu, không tự điền cho đủ. |
| 3:02 đến 3:22 | Kết quả xử lý | Trang kết quả với dữ liệu mẫu cho thấy ba trường hợp: có tác động rõ, không phát hiện tác động, và chưa đủ điều kiện. Không đủ dữ liệu thì hệ thống nói là chưa đủ, không ép ra một con số. |
| 3:23 đến 3:32 | Kết quả xử lý | Còn kết quả thật hôm nay là 0 phiên, đúng như hồ sơ. |
| 3:32 đến 3:47 | Khả năng tích hợp | Trang bắt đầu hỏi ba câu, rồi cho biết nền tảng nào đã sẵn sàng và nền tảng nào còn thiếu khóa. Mỗi nền tảng là một bộ nối riêng qua API chính thức, lõi phân tích không đổi. |
| 3:48 đến 3:53 | Khả năng tích hợp | Đơn hàng nhập từ tệp CSV của Seller Center, không đọc thông tin người mua. |
| 3:53 đến 4:06 | Khả năng tích hợp | Công cụ kiểm tra khóa YouTube báo chưa có khóa. Hôm nay chúng em chưa có khóa nền tảng nào, nên luồng thầy cô vừa xem chạy bằng nguồn mô phỏng. |
| 4:06 đến 4:23 | Khả năng ứng dụng | Bộ kiểm thử của bộ lọc dữ liệu cá nhân chạy xong, tất cả đều đạt. Mỗi con số trong hồ sơ có lệnh chạy lại trong kho mã công khai. Sản phẩm dùng được cho nhà bán tự phát sóng có lượng xem ổn định, chốt đơn qua website riêng hoặc inbox. |
| 4:24 đến 4:26 | Kết | Cảm ơn thầy cô đã theo dõi. |

**Không đưa vào video 2** (và lý do): phân tích bản phát lại YouTube ở `/bat-dau` (đường yt-dlp, không chính thức)
và bất kỳ buổi live nào của người khác; bộ kiểm thử đầy đủ (chạy nhiều phút), trên hình chỉ chạy một tệp ngắn.

---

## Số được phép nói (khớp hồ sơ ngày 27/09/2026; đổi hồ sơ thì đổi bảng này)

| Số | Giá trị | Nguồn |
|---|---|---|
| Thiết kế | Phiên 90 phút, 16 khối; khối đầu và cuối 10 phút, 14 khối giữa 5 phút | `livelift.core.assigner.outer._block_lengths_min`; Hình 1 |
| A/A | 3,50% (7/200), mức danh nghĩa 5% | `scripts/do_lai_so_hieu_chuan.py --kiem` |
| Độ phủ KTC 95% | A/A 96,50% (193/200) là mặt kia của tỷ lệ bác bỏ, không nói như bằng chứng thứ hai; thu hồi 40 lần: lệch −0,84%, phủ 92,50% (37/40) | như trên |
| Bình luận quan sát | 19.126 bình luận, 16 buổi, tải bằng yt-dlp | `docs/benchmarks/live-fire-da-nguon.md` |
| Ý định | 0,870 (câu mẫu AI soạn); 0,211 (chat thật, v1); 0,542 (chat thật, v2, đo 25/09), thang 11 lớp; cùng thang 6 lớp: từ 0,370 lên 0,572; nhãn do tác tử AI gán | `docs/benchmarks/intent-eval/results.md` |
| Kiểm thử | 2.116 (gồm 2.089 nhanh, 17 chậm, 10 trình duyệt); chạy ngày 27/09/2026: 2.114 đạt, 2 bỏ qua | `scripts/dong_bo_so_test.py --xem-truoc` |
| Sự cố | 121 | `docs/incident-log.md` |
| Phiên thí nghiệm thật | 0 | FACT-SHEET |
| Người xem | "5 đến 15" chỉ được nói kèm chữ **ước tính từ giá quảng cáo (CPM), chưa đo** | FACT-SHEET |

## Việc còn lại của đội

| Việc | Ai | Hạn |
|---|---|---|
| Lồng tiếng video 1 theo bảng trên, xuất H.264 1920x1080, kiểm thời lượng dưới 300 giây bằng `ffprobe` | Đội trưởng (hoặc chia ba người) | 28/09 |
| Lồng tiếng video 2 theo bảng trên, kiểm thời lượng | Đội trưởng | 28/09 |
| Nghe lại, đối chiếu từng con số đã đọc với bảng "Số được phép nói" | Cả đội | Trước khi nộp ít nhất 24 giờ |
