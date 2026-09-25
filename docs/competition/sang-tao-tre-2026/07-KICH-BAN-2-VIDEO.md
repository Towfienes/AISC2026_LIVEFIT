# Kịch bản 2 video bắt buộc — Bảng C, đường trường cử

*Căn cứ: `BRIEF-THE-LE.md` §3. Mỗi video **tối đa 05:00**. Thiếu một trong hai là loại về hình thức.
Viết lại 25/09/2026 theo giao diện hiện tại (`/`, `/bat-dau`, `/chay-phien`, `/desk`, `/host`,
`/bao-cao/[id]`, `/ket-qua`) và theo hồ sơ `noi-dung.md` bản 25/09. Thay cho bản 15/09.*

> **Ba luật bao trùm cả hai video**
>
> 1. **Không nói con số nào không có trong `docs/competition/FACT-SHEET.md` và `noi-dung.md`.**
>    Giám khảo Bảng C được quyền "kiểm tra, xác minh sản phẩm"; một số trong video lệch hồ sơ
>    là mất điểm trọng tâm 5. Bảng "Số được phép nói" ở cuối tệp là danh sách duy nhất.
> 2. **Không quay dữ liệu cá nhân thật.** Mọi bình luận trên hình lấy từ nguồn **Mô phỏng**
>    (200 câu tổng hợp do tác tử AI soạn, số điện thoại trong đó là số giả) trên một phiên
>    **chạy thử**. Không mở VOD của người khác, không mở `.env`, không mở `data/labeling/`.
> 3. **Không cắt ghép che bước.** Điều 5 khoản 7 Thể lệ cấm giả mạo video demo. Đoạn chờ thì
>    tua nhanh và ghi rõ trên hình "tua nhanh ×N"; đoạn chuyển cảnh giữa hai lượt quay thì ghi
>    "chuyển cảnh" — không ghép để trông như một lượt.

**Cả ba thành viên xuất hiện trên hình ở cả hai video** (vòng Khu vực bắt buộc video có mặt tất cả
thành viên; tập từ vòng này). Webcam góc phải dưới, đổi người theo cột "Ai" ở bảng dưới.

---

## VIDEO 1 — THUYẾT TRÌNH (mục tiêu 4:50, trần 5:00)

Thể lệ yêu cầu đúng 5 nội dung, theo thứ tự: **vấn đề · phương pháp xây dựng giải pháp · kết quả
đạt được · giá trị thực tiễn · khả năng phát triển**. Mỗi nội dung có một thẻ tiêu đề nhỏ góc trên
để giám khảo tick được.

Hình thức: slide chiếm màn hình, người nói ở ô webcam; mở và kết thúc bằng cảnh cả ba người.
Slide lấy thẳng hình của hồ sơ (`docs/competition/sang-tao-tre-2026/hinh/`) — không vẽ hình mới
có số khác.

| Mốc | Ai | Nội dung | Lời thoại (đọc gần nguyên văn) | Cảnh quay |
|---|---|---|---|---|
| 0:00–0:15 | Cả 3 | Mở | **Minh:** "Chúng em là đội LiveLift, trường Đại học Tôn Đức Thắng: em là Minh, đây là Khánh và Tiến. Sản phẩm của chúng em đo xem một hành động trong phiên livestream có thật sự làm bán được hơn không." | Cả ba ngồi cạnh nhau, cỡ trung |
| 0:15–0:55 | Minh | **Vấn đề** | "Phút 30 người trợ live ghim sản phẩm B, phút 35 doanh thu nhích lên. Vì ghim, vì nền tảng vừa đẩy thêm người vào phòng, hay vì người dẫn vừa kể một câu chuyện hay? Số liệu sau phiên không tách được. Công cụ của nền tảng trả lời 'bán được bao nhiêu', chưa có công cụ nào nhà bán tự dùng được để trả lời 'bao nhiêu là do mình'. Các thí nghiệm ngẫu nhiên trong livestream đã làm được điều đó — nhưng do chính nền tảng chạy. Nhà bán không sở hữu nền tảng." | Slide: đường doanh thu có ba mũi tên giải thích; dòng nguồn [6], [7] của hồ sơ |
| 0:55–1:45 | Khánh | **Phương pháp (1): thí nghiệm** | "Trong livestream cả phòng nhìn một màn hình, nên không chia người xem được. Thứ chia được là thời gian. Phiên 90 phút chia thành 16 khối, khối đầu và cuối 10 phút, mỗi khối bốc thăm bật hay tắt can thiệp. Lịch bốc thăm được lưu kèm một mã băm trước giờ phát; chưa có lịch thì hệ thống không cho lên sóng. Người dẫn không được thấy khối nào đang bật, vì biết thì sẽ hào hứng hơn và phép đo thành đo tâm lý người dẫn. Kết quả tính bằng kiểm định ngẫu nhiên hóa, bốc lại bằng đúng hàm gán đang chạy." | Hình 1 của hồ sơ (`h1-switchback.png`), zoom lần lượt vào khối đầu, mốc khóa lịch, dải burn-in |
| 1:45–2:15 | Khánh | **Phương pháp (2): phần AI** | "Phần AI nằm ở hai chỗ. Một bộ lọc che số điện thoại, địa chỉ, tên tài khoản ngay khi bình luận vào hệ thống, trước khi ghi đĩa. Và một bộ phân loại ý định mua cho bình luận tiếng Việt, để người trợ live thấy khách đang hỏi giá hay chốt đơn. Nhãn ý định chỉ hiện trên bàn điều khiển, không đi vào phép tính nhân quả." | Hình 6 (`h2-kien-truc.png`), khoanh ba ô đỏ: lọc PII, HTTP 409, khóa kết quả |
| 2:15–3:25 | Tiến | **Kết quả đạt được** | "Bộ ước lượng được kiểm trên mô phỏng có đáp án: 200 lần thí nghiệm giả không có tác động, hệ thống báo có tác động 3,50% số lần, sát mức 5% cho phép; khoảng tin cậy chứa giá trị thật 96,50% số lần. Hệ thống đã nạp 19.126 bình luận quan sát từ 16 buổi phát lại trên YouTube — tải bằng yt-dlp, không qua API chính thức, và chúng em ghi rõ điều đó trong hồ sơ. Bộ phân loại ý định đạt 0,870 trên câu mẫu do AI soạn, nhưng trên chat thật chỉ 0,211; sau khi làm lại bộ nhãn và dữ liệu, lên 0,542 — đo so với nhãn tham chiếu do tác tử AI gán, chưa phải nhãn người. Độ đúng khi báo 'có khách muốn mua' tăng, nhưng tỷ lệ bắt được giảm. 2.032 kiểm thử tự động, 99 sự cố có phân tích nguyên nhân gốc. Điều chưa có: chưa có phiên thí nghiệm ngẫu nhiên thật nào — 0 phiên." | Hình 2 (`h3-hieu-chuan-aa.png`), rồi Bảng 7 của hồ sơ (dòng B2 và C2 tô đậm, cột recall khoanh); dòng "0 phiên" để trên nền trắng, chữ lớn |
| 3:25–4:05 | Minh | **Giá trị thực tiễn** | "Nhà bán không cần sở hữu TikTok hay Facebook: họ chỉ bốc thăm hành động của chính mình theo thời gian. Mã nguồn mở, chạy được trên một máy chủ phổ thông, không cần GPU. Nhưng chúng em nói rõ ai dùng được: lực thống kê phụ thuộc số người xem và số phiên. Với vài chục người xem trở lên, hoặc gộp nhiều phiên, hệ thống phát hiện được tác động vừa phải; nhà bán chỉ có vài người xem thì chỉ thấy được tác động rất lớn. Nghị quyết 57 coi khoa học, công nghệ và chuyển đổi số là đột phá quan trọng hàng đầu; LiveLift đưa cách làm thí nghiệm vào một kênh kinh tế số đang chạy bằng kinh nghiệm." | Hình 4 (`h4-mde.png`), khoanh vùng 5–15 người xem và chữ "ước tính, chưa đo" |
| 4:05–4:40 | Tiến | **Khả năng phát triển** | "Trước vòng Khu vực: khóa API YouTube chính thức, một buổi phát thử trên kênh của nhóm, và hai bạn gán nhãn lại tập kiểm tra để có nhãn người. Tháng 10–11: phiên ngẫu nhiên thật đầu tiên với shop đối tác có văn bản đồng ý. Trước chung kết: địa chỉ công khai chạy liên tục 48 giờ. Phương pháp này dùng được ở mọi nơi có một kênh phát và nhiều người xem." | Bảng 10 của hồ sơ (lộ trình) |
| 4:40–4:55 | Cả 3 | Chốt | **Khánh:** "LiveLift không hứa làm bạn bán nhiều hơn." **Tiến:** "Nó cho bạn biết hành động nào thật sự có tác dụng, kèm khoảng tin cậy." **Minh:** "Cảm ơn thầy cô." | Cả ba trên hình |

**Ba điều bắt buộc có trong video 1:**
1. Nói số xấu (0,211; 0 phiên; dữ liệu qua yt-dlp) trong phần kết quả, không để giám khảo tự tìm.
2. Nói rõ nhãn tham chiếu do tác tử AI gán — hồ sơ và kho mã đều ghi như vậy.
3. Không nói "API chính chủ" cho 19.126 bình luận, không nói "địa chỉ demo công khai" khi chưa có.

---

## VIDEO 2 — DEMO SẢN PHẨM (mục tiêu 4:50, trần 5:00)

Thể lệ yêu cầu quay: **quá trình vận hành · các chức năng chính · kết quả xử lý · khả năng tích hợp ·
khả năng ứng dụng**. Mỗi phần có thẻ tiêu đề nhỏ góc trên.

Hình thức: quay màn hình **một lượt** trên bản build (không phải `next dev`), trình duyệt 1920×1080
hồ sơ sạch; webcam góc phải dưới đổi người theo cột "Ai". Chờ khối chạy thì bộ thu đặt Mô phỏng
×10 và ghi "tua nhanh ×N" nếu phải tua thêm.

| Mốc | Ai | Phần | Thao tác trên màn hình | Lời thoại |
|---|---|---|---|---|
| 0:00–0:15 | Tiến | Mở | Trang chủ `/`; chỉ vào chip **Dữ liệu mẫu / Dữ liệu thật** ở đầu trang | "Mọi màn hình thầy cô sắp xem đều ghi rõ đâu là dữ liệu mẫu, đâu là dữ liệu thật. Hôm nay mọi bình luận là dữ liệu mô phỏng." |
| 0:15–1:05 | Tiến | **Vận hành (1): chuẩn bị phiên** | `/chay-phien` → "Dùng sản phẩm mẫu" → "Điền link mẫu" → bước 2: YouTube, 90 phút, **Chạy thử** → "Tạo phiên" → "Bốc thăm": hiện lịch 16 khối và mã bằng chứng lịch | "Lịch bốc thăm sinh ở đây, trước giờ phát, kèm mã băm của tham số và hạt giống. Ai giữ tệp thiết kế cũng tính lại được mã này để thấy lịch không bị sửa." |
| 1:05–1:25 | Tiến | **Vận hành (2): cổng chặn** | Tab thứ hai `/docs` (Swagger của API) → `POST /sessions/{id}/start` với một phiên **vừa tạo, chưa bốc lịch** → trả **409** | "Phiên chưa có lịch thì chính người tạo ra nó cũng không cho lên sóng được." |
| 1:25–1:45 | Tiến | **Vận hành (3): lên sóng** | Quay lại phiên đã bốc lịch → bước 4: tích "đã dán link", "Mở màn người dẫn" → "Bắt đầu phát sóng"; **sau khi lên sóng** mới bật **Bộ thu bình luận = Mô phỏng ×10** trên `/desk` (thứ tự bản quay thô 25/09 đã chạy trọn) | "Bộ thu bình luận chạy nền trong máy chủ, bật bằng một nút. Nguồn Mô phỏng chỉ dùng được cho phiên chạy thử — phiên thật bị máy chủ từ chối." |
| 1:45–2:40 | Khánh | **Chức năng chính (1): bàn trợ live** | `/desk`: dải khối, đồng hồ khối, bình luận chảy vào; dừng ở một bình luận có `[SĐT]`; chỉ radar ý định | "Đây là một số điện thoại giả trong kịch bản mô phỏng — và đây là thứ được ghi xuống: `[SĐT]`. Bộ lọc chạy trước khi ghi đĩa. Radar ý định cho người trợ live thấy khách đang hỏi gì; bản đang chạy mặc định là bản cũ, và nhãn này không dùng để tính tác động." |
| 2:40–3:05 | Khánh | **Chức năng chính (2): làm mù người dẫn** | Mở `/host` cạnh `/desk` (chia đôi màn hình) | "Cùng một phiên. Màn người dẫn chỉ có thời gian, sản phẩm đang ghim, giá, tồn kho — không có khối, không có nhánh." |
| 3:05–3:45 | Khánh | **Kết quả xử lý** | Trên `/desk`: "Kết thúc phiên" → xác nhận hai bước → "Xem báo cáo phiên →": nhãn **CHẠY THỬ — không tính vào kết quả gộp**, "Chưa đủ khối", ô THIẾU ở tim/quà/đơn. Rồi `/ket-qua?env=demo`: bản gộp CHỈ dữ liệu mẫu, nhãn MÔ PHỎNG; từ danh sách phiên mẫu ngay dưới, bấm "Báo cáo" (`/bao-cao/<id>`) của ba phiên demo vàng ở ba trạng thái (DƯƠNG, NULL, CHƯA ĐỦ ĐIỀU KIỆN — xem `docs/demo-vang.md`). Rồi `/ket-qua` mặc định: 0 phiên thật, "CHƯA ĐỦ ĐIỀU KIỆN" | "Phiên chạy thử không lọt vào kết quả thật. Không đủ dữ liệu thì hệ thống nói chưa đủ, không ép ra một con số. Còn kết quả thật hôm nay là 0 phiên — đúng như hồ sơ." |
| 3:45–4:25 | Minh | **Khả năng tích hợp** | `/bat-dau`: trả lời 3 câu hỏi → khối trạng thái nền tảng (đọc `GET /platforms`) hiện nền tảng nào thiếu khóa. Quay lại báo cáo phiên chạy thử (`/bao-cao/<id>`): ô nhập đơn hàng CSV (tệp mẫu tổng hợp); mở một link đo `/r/{code}` đã tạo ở bước 4 của `/chay-phien`. Terminal: `python scripts/kiem_tra_youtube.py` báo thiếu khóa (không in khóa) | "Mỗi nền tảng là một bộ nối riêng qua API chính thức; lõi phân tích không đổi. Đơn hàng nhập từ tệp xuất của Seller Center, không đọc thông tin người mua. Hôm nay chúng em chưa có khóa nền tảng nào, nên luồng thầy cô vừa xem chạy bằng nguồn mô phỏng." |
| 4:25–4:50 | Minh | **Khả năng ứng dụng** | Terminal: `pytest tests/test_pii_filter.py -q` chạy xong trên hình; mở trang GitHub của kho, cuộn tới README | "Mỗi con số trong hồ sơ có lệnh chạy lại trong kho mã công khai này. Sản phẩm dùng được cho nhà bán tự phát sóng có lượng xem ổn định, và cho mọi nơi có một kênh phát, nhiều người xem." |
| 4:50–4:55 | Cả 3 | Chốt | Cả ba trên webcam | **Minh:** "Cảm ơn thầy cô đã theo dõi." |

**Không quay trong video 2** (và lý do):
- Trang `/ket-qua?phien=<id>` của phiên chạy thử: bản 25/09 từng sập khi phiên có ≥4 khối mà 0 lượt nhấp (kiểm toán 25/09, runtime mục 3.0) — chỉ quay khi bản vá đã vào nhánh nộp và đã thử lại.
- Phân tích VOD YouTube ở `/bat-dau` (đường yt-dlp, không chính thức) và bất kỳ buổi live của người khác.
- Bộ test đầy đủ (`pytest -m "not slow"` mất nhiều phút): chỉ chạy một tệp ngắn trên hình.

**Chuẩn bị trước khi bấm ghi** (≥ 20 phút):
1. Dựng bản build và chạy API với kho sạch (`scripts/chay_local.py`); gieo phiên mẫu bằng `POST /demo/seed-vang`.
2. `python scripts/kiem_tra_truoc_demo.py` xanh.
3. Bấm giờ `pytest tests/test_pii_filter.py -q` trên máy quay; quá 20 giây thì thay bằng tệp ngắn hơn.
4. Đóng mọi cửa sổ có thông tin cá nhân, token, `.env`; tắt thông báo hệ thống; trình duyệt hồ sơ sạch.
5. Tập trước một lượt trọn vẹn, bấm giờ từng phần.

---

## Số được phép nói (khớp `noi-dung.md` 25/09 — đổi hồ sơ thì đổi bảng này)

| Số | Giá trị | Nguồn |
|---|---|---|
| Thiết kế | Phiên 90 phút · 16 khối · khối đầu và cuối 10 phút, 14 khối giữa 5 phút | `livelift.core.assigner.outer._block_lengths_min`; Hình 1 |
| A/A | 3,50% (7/200), danh nghĩa 5% | `scripts/do_lai_so_hieu_chuan.py --kiem` |
| Độ phủ KTC 95% | 96,50% (193/200) | như trên |
| Bình luận quan sát | 19.126 · 16 buổi · qua yt-dlp | `docs/benchmarks/live-fire-da-nguon.md` |
| Ý định | 0,870 (câu mẫu AI soạn) · 0,211 (chat thật, v1) · 0,542 (chat thật, v2, đo 25/09) — nhãn do tác tử AI gán | `docs/benchmarks/intent-eval/results.md` |
| Kiểm thử | 2.032 (2.005 nhanh + 17 chậm + 10 trình duyệt; chạy 25/09: 2.030 đạt, 2 bỏ qua) — đồng bộ lại ngày quay | `scripts/dong_bo_so_test.py --xem-truoc` |
| Sự cố | 99 | `docs/incident-log.md` |
| Phiên thí nghiệm thật | 0 | FACT-SHEET |
| Người xem | "5–15" chỉ được nói kèm chữ **ước tính từ giá quảng cáo (CPM), chưa đo** | FACT-SHEET |

## Việc con người phải làm

| Việc | Ai | Hạn |
|---|---|---|
| Slide video 1 (dùng hình trong `hinh/`) | Minh | 27/09 |
| Tập đọc, bấm giờ từng đoạn | Cả 3 | 27/09 |
| Quay video 1 (cả 3 trên hình) | Cả 3 | 28/09 |
| Quay video 2 (một lượt, cả 3 xuất hiện ở ô webcam) | Cả 3, Tiến điều khiển máy | 28/09 |
| Dựng, phụ đề, `ffprobe` kiểm độ dài ≤ 300 giây mỗi video | Tiến | 28/09 |
| Đối chiếu từng con số trong hai video với bảng trên | Minh | ≥ 24 giờ trước khi nộp |
| Xem bản quay thô tự động `D:/AISC2026/VIDEO-2509/` (278 giây, chưa lồng tiếng) làm mẫu nhịp; không nộp bản thô. Dùng lại cảnh quay tự động nào thì kê khai là quay bằng Playwright, kịch bản bấm do tác tử AI viết | Tiến | 27/09 |
