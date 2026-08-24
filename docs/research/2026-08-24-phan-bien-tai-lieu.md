# Phản biện dự án LiveLift — Báo cáo rà soát

## Điểm xuất sắc cần giữ

1. **Quy tắc hiển thị nguồn con số (E2-04)** — phân biệt "ước lượng dự báo" với "tác động đo được, KTC 95%", có kiểm thử tự động. Đây là chống overclaim ở cấp giao diện, gần như không đội sinh viên nào nghĩ tới. Không được cắt.
2. **Tiền đăng ký bằng commit + khóa sau tuần 6** — câu trả lời "chỉ vào mã commit" cho câu hỏi p-hacking là điểm ăn tiền nhất khi phản biện.
3. **Cam kết viết lại bảng lực thống kê bằng CV đo được ở tuần 3–4** và nguyên tắc "chốt độ dài khối theo dữ liệu, không theo cỡ mẫu mong muốn" (mục 7.2) — đúng chuẩn nghề.
4. **Holdback ngẫu nhiên = chính tầng ngoài của thí nghiệm** (mục 13.2) — hạ tầng khoa học trùng với cơ chế định giá là luận điểm kinh doanh hiếm và thuyết phục.
5. **Thứ tự cắt phạm vi cố định + điều kiện kích hoạt định lượng** (mục 10) và danh sách "không bao giờ cắt" 4 mục.
6. **Phân tích ITT/LATE, lý giải chế độ tự động để giữ tuân thủ ≈95%**, tách `tiktok_public/` khỏi lõi, lọc PII tại ingest, salt xoay theo phiên, từ chối phát biểu "đầu tiên trên thế giới".
7. **Demo mời giám khảo đổi tham số tại chỗ** (mục 12) — giải đúng nỗi nghi "video dựng sẵn".

## Lỗi/Mâu thuẫn cụ thể

**L1. Bảng MDE mâu thuẫn với chính quy tắc washout của nhóm.** Số học bảng 7.2 đúng (kiểm tra: 3900/6=650 chu kỳ, 4×0,5/√325=11,1%; 3900/12→162/nhánh→15,7%; 3900/18→108→19,2% ✓). Nhưng quy tắc 7.2 của kế hoạch: `washout ≥ trung vị thời gian ở lại` và `khối ≥ 2×washout`. Dòng đẹp nhất "5+1 phút" chỉ hợp lệ nếu trung vị ở lại ≤ 1 phút — vô lý với phòng live bán hàng có người xem gắn bó (chính mục 6.4 thừa nhận "nếu thời gian ở lại trung bình là mười phút… washout một phút không xóa được gì"). Với trung vị 5–7 phút thực tế: washout ≥5, khối ≥10 → chu kỳ ≥15 phút → ~260 chu kỳ, 130/nhánh → MDE ở CV=0,8 ≈ 28%. Tức mục tiêu bảng 8.4 "MDE ≤ 20%" và "≥500 khối hợp lệ" gần như bất khả thi theo chính quy tắc của nhóm. Giám khảo giỏi sẽ bắt đúng vòng luẩn quẩn này.

**L2. 3.900 phút trộn lẫn dữ liệu hiệu chỉnh với dữ liệu khẳng định.** Mô tả 7.1 tính "10 tuần (tuần 3–12), 30 phiên", nhưng tiền đăng ký chỉ commit tuần 6 và các phiên tuần 3–5 được dùng để *chọn* độ dài khối. Phiên dùng để hiệu chỉnh thiết kế không được đếm vào mẫu khẳng định — nếu trừ đi, chuỗi chính thức chỉ còn 18 phiên tự chạy (tuần 6–11) = 1.620 phút + 1.200 phút đối tác **chưa ký**. Bảng lực thống kê "3.900 phút" vì thế vừa phồng ~40%, vừa dựa trên đối tác chưa tồn tại — mâu thuẫn với "nhóm vẫn hoàn thành dự án mà không cần ai" (8.3): không có đối tác thì 500 khối là không thể (31 phiên × ~15 khối = 465 < 500, và đó là với chu kỳ 6 phút).

**L3. Ngân sách hai tài liệu lệch nhau.** Kế hoạch 9.1: **17.200.000đ** (quảng cáo 8+21=29 phiên = 8,7M). Mô tả 8.2: **15.200.000đ** (30 phiên × 300k = 9M, không có bổ sung hàng 1,5M, không có poster 0,8M). Cùng nộp hai tài liệu này là lộ điểm trừ. Thêm: lịch tuần 3–5 có **9** phiên nhưng ngân sách ghi "8 phiên"; giai đoạn 2 (T6–T11) có 6 tuần × 3 = **18** phiên nhưng ngân sách ghi "21 phiên"; bảng 8.4 mục tiêu "**31** phiên" trong khi mô tả ghi "**30**".

**L4. Hạn nộp vòng 1 lệch nhau:** kế hoạch E6-01 và tuần 3 ghi "**chậm nhất 14/09**"; mô tả 14.2 ghi "**hạn 15/09**" đặt ở *tuần 2*. Lịch tổng cũng lệch: mô tả dùng khung 12 tuần (thí nghiệm tuần 6–12), kế hoạch dùng 14 tuần (thí nghiệm tuần 6–11, đóng băng giữa tuần 12). Phải hợp nhất một lịch duy nhất.

**L5. "Tỷ lệ nhấp sản phẩm" — biến kết quả chính — chưa được định nghĩa cách đo trên Facebook Live.** Toàn bộ thiết kế xoay quanh product CTR theo khối, nhưng Facebook Live tại Việt Nam bán chủ yếu qua bình luận chốt đơn; không có thẻ sản phẩm đo click gốc như TikTok Shop, YouTube Live cũng vậy. Không tài liệu nào nói sự kiện "nhấp" đến từ đâu (link rút gọn ghim trong bình luận? overlay riêng?). Nếu không trả lời được, biến chính không tồn tại — đây là lỗ hổng nghiêm trọng nhất về đo lường.

**L6. Host không bị làm mù — và E2-08 chủ động phá mù.** Bảng điều khiển host "hiện… thời gian còn lại của khối" tức host biết ranh giới khối và suy ra được BẬT/TẮT. Host hào hứng hơn trong khối BẬT là kênh gây nhiễu trực tiếp lên CTR; ước lượng khi đó đo "hệ thống + tâm lý host", không phải hệ thống. Chưa có dòng nào bàn về blinding.

**L7. "Đồng ý" pháp lý bị đánh tráo bằng "thông báo".** Mục 11.2 ghi "Đồng ý có lưu trữ: hiển thị thông báo xử lý dữ liệu trong phòng live" — trong khi 11.1(b) tự trích Nghị định "cấm cơ chế mặc định đồng ý". Xem thông báo rồi tiếp tục xem ≠ đồng ý chủ động theo Luật 91/2025. Cơ sở đúng nên là khử nhận dạng ngay tại ingest + lợi ích chính đáng, không nên tự nhận có "consent". Ngoài ra VLiveBench dùng TikTokLive (giao thức reverse-engineered) vẫn vi phạm ToS nền tảng dù dữ liệu công khai — cần thừa nhận thay vì gộp vào "ba nguồn hợp lệ".

**L8. ICC đo sai cấp cụm.** Mục 7.1 đo "tương quan giữa các khối liền kề" — đó là tự tương quan, không phải ICC theo cụm phiên. Cụm thật là *phiên* (sốc chung: host, ngân sách quảng cáo, thuật toán đẩy): 465 khối nằm trong chỉ ~30 phiên, design effect 1+(m−1)ρ với m≈15 có thể nuốt phần lớn lực thống kê. Kiểm định ngẫu nhiên hóa cũng phải hoán vị theo đúng sơ đồ phân tầng-trong-phiên, chưa được nêu.

## Rủi ro bị đánh giá thấp

**R1. 80 người xem đồng thời với 300k/phiên là phi thực tế — thiếu khoảng 5–10 lần.** Toán: 80 đồng thời × 90 phút = 7.200 người-phút. Khách quảng cáo lạnh ở lại ~3–5 phút → cần 1.400–2.400 lượt vào phòng/phiên → phải mua được lượt vào với ≤125–210đ. Thực tế CPM Facebook VN ~25–60k → 300k mua ~5–12 nghìn hiển thị, CTR vào live 1–2% → 50–240 lượt vào → đóng góp ~5–15 người đồng thời, cho một Page mới không lịch sử tương tác còn tệ hơn. Phương án dự phòng "tăng lên 500k/phiên" (a) không lấp nổi khoảng cách 10×, (b) tốn thêm ~4,2M cho 21 phiên còn lại — vượt quỹ dự phòng 2M. Đây là rủi ro tồn vong đúng như tài liệu tự nhận, nhưng thuốc chữa đang bị định giá sai một bậc độ lớn.

**R2. App Review Meta: nộp 25/08, cần dùng 08/09 (2 tuần) — trong khi hồ sơ nộp ngày 1 chưa có app chạy được để quay screencast minh họa quyền, và quyền đọc bình luận cho Page *của đối tác* thường đòi Business Verification mà sinh viên khó có. Điểm chưa khai thác: với Page *của chính nhóm*, quản trị viên app ở chế độ development có thể đọc được dữ liệu mà chưa cần App Review — Live Lab có thể chạy sớm hơn kế hoạch tưởng, còn tích hợp đối tác (tuần 8) mới là chỗ App Review thực sự chặn.**

**R3. SP quá tải đến mức gãy:** host chính 3 phiên/tuần + vận hành + đóng gói giao ≥8 đơn/phiên + quảng cáo + đối tác + poster + toàn bộ hồ sơ E6. Không ai được phân công đóng hàng/giao hàng. TN cũng là điểm hỏng đơn: "song song một cuộc thi khác tháng 9–11", cột dự phòng ghi "—".

**R4. "Giai đoạn ít thay đổi mã nguồn nhất" mâu thuẫn với chính lịch của nó:** tuần 8 tích hợp phòng đối tác + chế độ đề xuất, tuần 9–10 xây E3-06/07/08 và mô hình B — toàn thay đổi lớn giữa chuỗi thí nghiệm đang chạy. Thiếu: môi trường staging, kiểm thử hồi quy cho assigner, quota YouTube API, chi phí chạy PhoBERT realtime trên VPS 400k/tháng, đồng bộ đồng hồ giữa các nguồn sự kiện.

**R5. Đơn hàng/tồn kho không khớp:** ≥8 đơn × 29 phiên ≈ 232 đơn trên 4,5M vốn hàng → giá vốn ~19k/đơn; hàng giá đó thì phí ship và đóng gói ăn hết biên, còn số liệu GMV thành nhiễu.

## Đề xuất cải thiện ưu tiên

**P0 (làm trước 14/09):**
1. **Định nghĩa vận hành của "lượt nhấp sản phẩm" trên từng nền tảng** (ví dụ: link rút gọn có UTM ghim trong bình luận, đo click qua redirect tự host) — viết thành một mục riêng, vì cả thí nghiệm đứng trên biến này.
2. **Hợp nhất hai tài liệu:** một con số ngân sách (chốt 17,2M), một số phiên (29 hay 30 hay 31), một hạn nộp (xác minh với BTC: 14 hay 15/09), một khung tuần.
3. **Sửa bảng MDE thành hai kịch bản trung thực:** "không đối tác, khối 10–15 phút, chỉ tuần 6–11" (MDE ~25–30%) và "có đối tác". Chủ động đưa con số xấu ra trước — đúng tinh thần mục 12 của chính nhóm.
4. **Nộp App Review với app demo tối thiểu + screencast; ghi rõ Live Lab chạy được ở development mode** để gỡ nút thắt tuần 3.

**P1 (trước tuần 6):**
5. **Giao thức làm mù host:** bỏ hiển thị ranh giới khối khỏi màn hình host (sửa E2-08), host chỉ thấy sản phẩm đang ghim; ghi vào tiền đăng ký như một biện pháp chống nhiễu — biến L6 thành điểm cộng.
6. **Sửa mục pháp lý:** thay "đồng ý = thông báo" bằng lập luận khử nhận dạng tại nguồn + không lưu chuỗi hành vi cá nhân; thừa nhận rủi ro ToS của TikTokLive trong một câu.
7. **Đo ICC ở cấp phiên** và đưa design effect theo cụm-phiên vào bảng MDE; mô tả sơ đồ hoán vị của randomization test.
8. **Làm lại toán quảng cáo:** chạy thử 2–3 phiên đo chi phí thật trên mỗi lượt vào phòng, rồi hạ ngưỡng tiên quyết xuống mức mua nổi (ví dụ 40–50 đồng thời) và bù bằng khối ngắn hơn nếu dữ liệu dwell cho phép — hoặc dồn tiền tuyên bố đối tác dữ liệu là đường sống chính, không phải phụ.

**P2 (trước chung kết):**
9. Phân công người phụ trách đóng gói–giao hàng; định danh backup cho TN ở phần phân tích (NC học trước notebook E3-06/07).
10. Đóng băng mã assigner + ingest từ tuần 6 bằng nhánh riêng; mọi tính năng mới (đối tác, mô hình B) merge sau kiểm thử hồi quy.
11. Thêm một slide "giới hạn tự khai": MDE thật, không blinding hoàn hảo, một loại can thiệp, một cửa hàng — đội tự nêu giới hạn bằng số đúng như triết lý mục 11 của kế hoạch.

**Kết luận:** nền tảng phương pháp thuộc nhóm 1% đội thi sinh viên; ba thứ có thể đánh sập nó là biến kết quả chưa đo được trên nền tảng đã chọn (L5), bài toán khán giả bị định giá thiếu ~10 lần (R1), và bảng lực thống kê tự mâu thuẫn với quy tắc washout của chính nhóm (L1). Sửa ba điểm đó trước 14/09 thì hồ sơ gần như không còn điểm chết.