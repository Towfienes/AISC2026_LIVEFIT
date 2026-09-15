# Kịch bản 2 video bắt buộc — Bảng C, Vòng loại

*Căn cứ: `BRIEF-THE-LE.md` §3. Cả hai video đều **tối đa 05 phút**. Thiếu một trong hai là loại về hình thức.*

> **Luật bao trùm cả hai video:** không nói một con số nào không có trong
> `docs/competition/FACT-SHEET.md`. Giám khảo Bảng C được thể lệ giao quyền
> "kiểm tra, xác minh sản phẩm"; một con số trong video không khớp hồ sơ là
> mất điểm trọng tâm 5 *khả năng kiểm chứng đầu ra* — chỗ đắt nhất của bảng này.

---

## VIDEO 1 — THUYẾT TRÌNH (≤ 5:00)

Thể lệ yêu cầu đúng 5 nội dung: **vấn đề cần giải quyết · phương pháp xây dựng giải pháp · kết quả đạt được · giá trị thực tiễn · khả năng phát triển**. Kịch bản dưới đây đi đúng thứ tự đó để giám khảo tick được từng ô.

Hình thức: người nói xuất hiện trên hình (webcam góc nhỏ), slide chiếm phần còn lại. Cả 3 thành viên nên xuất hiện — vòng sau bắt buộc, tập trước từ bây giờ.

| Thời lượng | Người nói | Nội dung | Hình trên màn |
|---|---|---|---|
| 0:00–0:25 | Minh | **Móc câu.** "Phút 30 ghim sản phẩm B, phút 35 doanh thu tăng. Vì sao? Ba lời giải thích cùng đúng: vì vừa ghim, vì nền tảng vừa đẩy người vào phòng, vì người dẫn vừa kể xong chuyện hay. Cả ngành đang quyết định bằng thứ chưa qua một phép thử nào." | Cảnh quay màn hình một phiên live thật + đường doanh thu nhích lên |
| 0:25–1:00 | Minh | **Vấn đề & quy mô.** 2,5 triệu phiên/tháng, hơn 50.000 nhà bán. Dữ liệu thì thừa, nhưng mọi công cụ chỉ trả lời "bán được bao nhiêu", không cái nào trả lời "bao nhiêu là do bạn". Năng lực thí nghiệm hôm nay là đặc quyền: Eppo ~42.000 USD/năm ≈ 1,1 tỷ đồng. | Slide 3 con số lớn |
| 1:00–1:50 | Khánh | **Phương pháp.** Không chia được người xem vì cả phòng nhìn một màn hình → chỉ chia được **thời gian**. Ví von cái quạt và căn phòng. Switchback: 90 phút → 16 khối 5 phút, mỗi khối bốc thăm bật/tắt, **lịch khóa trước khi lên sóng**. | Hoạt hình dải khối bật/tắt chạy dọc trục thời gian |
| 1:50–2:40 | Khánh | **Ba cơ chế liêm chính** — phần khác biệt nhất, nói chậm: (1) khóa tiền đăng ký bằng `design_hash`, không có thì API chặn 409; (2) khóa kết quả *fail-closed* — chưa tới mốc thì chính nhóm cũng không xem được p-value; (3) làm mù người dẫn. **Đây là mã nguồn, không phải lời hứa.** | Quay màn hình thật: thử gọi API khi chưa có design_hash → HTTP 409 |
| 2:40–3:40 | Tiến | **Kết quả đạt được.** A/A 200 lần: bác bỏ 3,50% so với danh nghĩa 5%, phủ KTC 96,50%. 19.126 bình luận thật từ 16 buổi live. 1.174 kiểm thử. **Và số xấu:** mô hình ý định 0,870 trên bộ tự soạn nhưng chỉ **0,211 trên chat thật** — nhóm tự đo, tự công bố, truy ra 3 nguyên nhân, rồi dựng lại khung đo và nâng lên **0,565**. **Và 0 phiên thí nghiệm thật — nói thẳng.** | Bảng kết quả, ô số xấu tô đỏ chứ không giấu |
| 3:40–4:20 | Tiến | **Giá trị thực tiễn.** Hạ chi phí của một năng lực khoa học từ 1,1 tỷ đ/năm xuống mức tổ ba người dùng được. Gắn Nghị quyết 57-NQ/TW: đưa phương pháp khoa học vào một ngành kinh tế số. | Bảng so sánh 4 nhóm giải pháp (mục 9.1 hồ sơ) |
| 4:20–4:50 | Minh | **Khả năng phát triển.** Ưu tiên 1: những phiên ngẫu nhiên thật đầu tiên. Ưu tiên 2: NLP dùng được cho quyết định. Mở rộng: lõi phương pháp không gắn với thương mại — truyền thông cộng đồng, phổ biến pháp luật, khuyến nông trực tuyến. | Slide lộ trình |
| 4:50–5:00 | Cả 3 | Chốt: "LiveLift không hứa giúp bạn bán nhiều hơn. LiveLift nói cho bạn biết **cái gì thật sự có tác dụng** — kèm khoảng tin cậy." | Cả 3 trên hình |

**Ba điều PHẢI có trong video 1** (đây là thứ tách đội này khỏi phần còn lại):
1. Nói ra con số xấu **trước khi** giám khảo tìm thấy nó.
2. Quay màn hình thật cảnh hệ thống **tự chặn chính mình** (HTTP 409) — không slide nào thay được.
3. Nói rõ "0 phiên thí nghiệm thật" — giấu là rủi ro bị loại theo Điều 5 §7; nói ra là bằng chứng của trọng tâm 8 *trách nhiệm của đội thi*.

---

## VIDEO 2 — DEMO SẢN PHẨM (≤ 5:00)

Thể lệ yêu cầu quay: **quá trình vận hành · các chức năng chính · kết quả xử lý · khả năng tích hợp · khả năng ứng dụng**.

Quay màn hình liền mạch một lượt, **không cắt ghép giữa các bước** — cắt ghép ở video demo là thứ giám khảo soi đầu tiên, và Điều 5 §7 cấm giả mạo video demo. Nếu phải cắt, ghi rõ trên hình "tua nhanh ×N".

| Thời lượng | Bước | Quay gì | Câu thoại chốt |
|---|---|---|---|
| 0:00–0:20 | Mở đầu | Trang chủ, chỉ rõ nhãn **chế độ DEMO / chế độ THẬT** | "Mọi thứ các thầy cô sắp xem đều gắn nhãn rõ đâu là mô phỏng, đâu là dữ liệu thật." |
| 0:20–1:10 | **Chuẩn bị phiên** | Wizard: khai danh mục sản phẩm → tạo phiên → **bốc lịch** | "Lịch bốc thăm sinh ra ở đây, kèm `design_hash`. Từ giây này lịch không sửa được nữa." |
| 1:10–1:35 | **Cổng chặn** | Thử phát sóng một phiên **chưa có lịch** → API trả **HTTP 409** | "Hệ thống từ chối chính người tạo ra nó. Đây là cưỡng chế bằng kiến trúc." |
| 1:35–2:30 | **Vận hành trực tiếp** | Bàn điều khiển `/desk`: dải khối, đồng hồ đếm, bình luận chảy vào theo thời gian thực, radar ý định | "Bình luận đi qua bộ khử PII **trước khi** chạm đĩa. Đây là số điện thoại thật trong chat — và đây là thứ được ghi xuống." (chỉ vào chuỗi đã che) |
| 2:30–3:00 | **Làm mù người dẫn** | Mở song song `/host` cạnh `/desk` | "Cùng một phiên. Người dẫn không thấy khối nào bật, khối nào tắt — nếu thấy, phép đo sẽ đo tâm lý người dẫn thay vì đo can thiệp." |
| 3:00–3:40 | **Kết quả xử lý** | Trang `/report` với **ba trạng thái**: đủ bằng chứng / không đủ bằng chứng / chưa đủ dữ liệu | "Không phải phiên nào cũng ra một con số. Ép ra con số khi dữ liệu không đủ là nói dối người dùng." |
| 3:40–4:10 | **Khả năng tích hợp** | Nạp thật từ một VOD YouTube qua API chính chủ; chỉ endpoint link đo `/r/{code}` | "Thêm một nền tảng chỉ là thêm một adapter nạp. Lõi phân tích không đổi." |
| 4:10–4:40 | **Kiểm chứng** | Chạy `pytest -m "not slow"` cho chạy lên màn hình; mở `docs/incident-log.md` | "1.174 kiểm thử. 46 sự cố có phân tích nguyên nhân gốc — kể cả sự cố tự bác bỏ mô hình của chính nhóm." |
| 4:40–5:00 | **Ứng dụng** | Địa chỉ demo công khai trên trình duyệt sạch | "Các thầy cô mở được ngay tại địa chỉ này." |

**Chuẩn bị bắt buộc trước khi bấm ghi** (≥15 phút):
1. Dựng lại CSDL sạch + nạp dữ liệu mẫu, xác nhận trang không trống.
2. Chạy `pytest -m "not slow"` một lượt cho chắc xanh.
3. Đóng mọi cửa sổ có thông tin cá nhân / token; đổi sang hồ sơ trình duyệt sạch.
4. Kiểm tra địa chỉ demo công khai truy cập được từ **mạng khác** (dùng 4G điện thoại).
5. Tắt thông báo hệ thống.

Kịch bản demo chi tiết từng lệnh đã có sẵn ở `docs/competition/kich-ban-demo-7-phut.md` — cắt xuống 5 phút theo bảng trên.

---

## Việc con người phải làm

| Việc | Ai | Hạn |
|---|---|---|
| Dựng slide cho video 1 | Minh | |
| Tập đọc kịch bản, bấm giờ từng đoạn | Cả 3 | |
| Quay video 1 (3 người) | Cả 3 | |
| Quay video 2 (một lượt liền mạch) | Khánh + Tiến | |
| Dựng, thêm phụ đề, kiểm tra độ dài < 5:00 | Tiến | |
| Xem lại: đối chiếu **từng con số** trong video với FACT-SHEET | Minh | trước khi nộp ≥24h |
