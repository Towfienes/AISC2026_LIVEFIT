# Khảo sát đối thủ: CELLAXNET — trợ lý AI cho thương mại điện tử (UIT, Top 3 AREA 303)

**Ngày khảo sát:** 10/09/2026
**Nguồn gốc:** người dùng gửi link Facebook https://www.facebook.com/share/1ERf7kmCcD/ và hỏi: họ làm gì, phương pháp và kết quả thế nào, LiveLift có làm tốt bằng họ không, học hỏi được gì.
**Trạng thái xác minh:** link resolve thành công (bài đăng công khai, không chặn đăng nhập). Toàn bộ thông tin về CELLAXNET đến từ **một bài đăng Facebook duy nhất** — chưa có website, GitHub, demo hay bài báo nào được lập chỉ mục để đối chiếu. Những gì không xác minh được đều ghi rõ bên dưới.

---

## 1. Họ là ai, làm gì

| Mục | Thông tin | Nguồn + ngày truy cập |
|---|---|---|
| Tên dự án | **CELLAXNET – AI Assistant for E-commerce** | Bài đăng FB của Khoa Hệ Thống Thông Tin, Trường ĐH Công nghệ Thông tin (UIT), truy cập 10/09/2026 |
| Đội | 4 sinh viên UIT khóa 2024: Lê Thế Vinh (CTTT2024), Ngô Quang Nhiệm (CTT2024), Thái Nguyễn Thanh Phú (CTTT2024), Nguyễn Phan Hoàng Quân (CTT2024) | Bài đăng FB, truy cập 10/09/2026 |
| Thành tích | **Top 3** cuộc thi AREA 303 – The Buffalo Playground (53 đội, 227 thí sinh). Bài đăng khoảng 09/09/2026 ("1 ngày trước" tại thời điểm truy cập). Không rõ hạng cụ thể (nhất/nhì/ba) và không rõ bảng thi (Charging Buffalo hay Wild Buffalo) | Bài đăng FB, truy cập 10/09/2026 |
| Đối tượng phục vụ | Nhà bán lẻ vừa và nhỏ ngành **thời trang, mỹ phẩm** trên **Shopee, Lazada, TikTok Shop** | Bài đăng FB, truy cập 10/09/2026 |
| Tính năng công bố | (1) Phân tích cảm xúc khách hàng, (2) phát hiện review ảo, (3) định giá động (dynamic pricing), (4) gợi ý sản phẩm, (5) nhận diện khách hàng có nguy cơ rời bỏ (churn risk). Bài đăng mô tả "backend, frontend hoàn chỉnh và nhiều tính năng" | Bài đăng FB, truy cập 10/09/2026 |

**Về cuộc thi AREA 303 – The Buffalo Playground** (bối cảnh để định cỡ thành tích):

- Sân chơi AI, Data & E-commerce **dành cho sinh viên UIT**, khẩu hiệu "Unbox Data. Unlock E-com." Đơn vị tổ chức gắn với **Ba3.studio** (studio "Creative eCommerce" tại TP.HCM, hỗ trợ chuyển đổi số cho SME; liên hệ support@ba3.studio). Nguồn: forum.uit.edu.vn/t/…/161513, truy cập 10/09/2026; trang FB và LinkedIn của Ba3.studio, truy cập 10/09/2026.
- Hai bảng: **Charging Buffalo** (giải bài toán thật do BTC đưa) và **Wild Buffalo** (ý tưởng tự do). Ba vòng: Discovery 303, Decode 303, Area 303. Đăng ký 04/06–23/07/2026, đội 3–5 người. Nguồn: forum.uit.edu.vn, truy cập 10/09/2026.
- Đây là cuộc thi **cấp trường** (phạm vi sinh viên UIT), quy mô 53 đội — nhỏ hơn đáng kể so với AISC'26.

## 2. Phương pháp và kết quả của họ — những gì biết và KHÔNG biết

**Biết (từ bài đăng):** danh sách tính năng ở trên; sản phẩm ở dạng prototype dự thi có backend + frontend chạy được; lọt Top 3/53 đội.

**KHÔNG xác minh được** (đã tìm bằng WebSearch nhiều truy vấn — CELLAXNET không có dấu vết web nào ngoài bài đăng này, tính đến 10/09/2026):

- Không có số liệu phương pháp nào được công bố: không accuracy/F1 cho phân tích cảm xúc hay phát hiện review ảo, không mô tả mô hình, không dữ liệu huấn luyện.
- Không có case study, không số người dùng, không doanh thu, không giá bán.
- Không có demo công khai, GitHub, website, không rõ có tiếp tục phát triển sau cuộc thi hay không.
- Không có bằng chứng nào về đo lường nhân quả (thí nghiệm ngẫu nhiên, ghi propensity, nhóm đối chứng). Theo mô tả, cả 5 tính năng đều thuộc lớp **ML mô tả/dự đoán trên dữ liệu sàn** (hồi cứu). *Đây là suy luận từ mô tả tính năng, chưa xác minh trực tiếp.*

## 3. So sánh với LiveLift theo từng trục

### (a) Họ có đo lường nhân quả không, hay chỉ đếm/dự đoán?

Theo mọi thông tin công khai: **không có dấu hiệu đo lường nhân quả**. CELLAXNET thuộc lớp "phân tích + gợi ý" (sentiment, fake review, pricing, recommendation, churn) — trả lời câu hỏi *"dữ liệu nói gì?"*, không trả lời *"hành động này TẠO RA bao nhiêu giá trị?"*. Ngay cả định giá động — tính năng gần can thiệp nhất — cũng không có bằng chứng được đánh giá bằng thí nghiệm. LiveLift được xây quanh đúng khoảng trống đó: switchback ngẫu nhiên trong phiên, ghi propensity, kiểm định bằng chính hàm gán production (A/A 200 lặp: bác bỏ 4.5%, coverage 95.5%). **Trên trục này hai bên không cùng hạng cân — nhưng cần công bằng: họ không định thi đấu ở trục này.**

### (b) Họ có gì mà LiveLift chưa có (đáng học hỏi)

1. **Phủ mặt "kệ hàng" (marketplace):** review, giá, danh mục, gợi ý sản phẩm trên Shopee/Lazada/TikTok Shop — LiveLift chủ đích chỉ đo trong phiên live, không chạm dữ liệu sau phiên trên sàn.
2. **Phát hiện review ảo** — một bài toán chất lượng tín hiệu có tính đối kháng (adversarial). LiveLift có lọc PII và phân loại ý định nhưng **chưa có detector cho bình luận seeding/spam trong phiên live** — hiện tượng rất phổ biến ở live Việt và có thể làm nhiễm ước lượng lift.
3. **Định giá là một đòn bẩy can thiệp** — LiveLift hiện có ghim sản phẩm/voucher/kịch bản hành động; mức giảm giá (voucher depth) chưa là một arm thí nghiệm.
4. **Churn/khách hàng nguy cơ rời bỏ** — tư duy xuyên phiên (khán giả quay lại hay không), trong khi LiveLift đo từng phiên độc lập.
5. **Bài học pitch thi đấu:** ban giám khảo phản ứng tốt với "backend + frontend hoàn chỉnh, nhiều tính năng" — độ RỘNG nhìn thấy được. Chiều sâu phương pháp của LiveLift cần được trình diễn trực quan không kém (xem §4).

### (c) LiveLift có gì họ không có (điểm khác biệt)

| Năng lực LiveLift | Phía CELLAXNET (công khai) |
|---|---|
| Thí nghiệm switchback ngẫu nhiên hai tầng trong phiên, propensity chính xác, lịch gán lưu trước phát sóng | Không có dấu hiệu |
| Suy diễn tự chứng minh: randomization test bằng chính hàm gán production; A/A 200 lặp | Không có |
| Liêm chính cấp kiến trúc: làm mù host (model 4 trường, /host không bao giờ thấy nhánh), số dự báo không thể mang CI, seed tái lập | Không có |
| Ma trận tín hiệu — thiếu tín hiệu thì tuyên bố, không bịa số | Không có |
| Kiểm chứng live-fire: 19.126 bình luận thật từ 16 buổi, đa nguồn; hiệu chỉnh mô phỏng theo KuaiLive (1,16 triệu phòng) | Không có số liệu nào công bố |
| NLP live-commerce Việt: lọc PII recall ≥95% (SĐT viết chữ, teencode), phân loại ý định F1 0.87 | Có "phân tích cảm xúc" nhưng không số liệu |
| Kỷ luật kỹ thuật: 598 test nhanh + 13 gate slow, CI công khai | "Backend, frontend hoàn chỉnh" — không kiểm chứng được |

**Khác biệt bản chất:** CELLAXNET là *trợ lý phân tích cho kệ hàng trên sàn*; LiveLift là *hạ tầng thí nghiệm nhân quả cho phiên live*. Hai sản phẩm gần như không giẫm chân nhau về địa bàn — nhưng là hai *kiểu bài dự thi* cạnh tranh trực tiếp về cách thuyết phục giám khảo.

### (d) "Mình có làm tốt bằng họ không?"

- **Về độ chín phương pháp và bằng chứng:** LiveLift vượt xa những gì CELLAXNET công bố (họ công bố **0** con số phương pháp; LiveLift có A/A, coverage, F1, recall, live-fire đa nguồn có tài liệu).
- **Về độ rộng tính năng hướng người bán trên sàn:** họ phủ vùng LiveLift chủ đích không phủ. Đó là lựa chọn chiến lược, không phải thua kém — nhưng phải nói được điều đó trong 1 câu khi bị so sánh.
- **Về thành tích thi:** Top 3 một cuộc thi cấp trường (53 đội) — đáng ghi nhận nhưng không cùng quy mô AISC'26. Lưu ý: đội này (và các đội UIT tương tự) **hoàn toàn có thể xuất hiện ở AISC'26**.

## 4. Bài học cụ thể nên áp dụng cho LiveLift

1. **Detector bình luận seeding/spam trong phiên** (học từ "phát hiện review ảo"): thêm một cờ chất lượng tín hiệu vào ma trận tín hiệu; khối thời gian bị nhiễm seeding thì *tuyên bố nhiễm* (đúng triết lý không bịa số) thay vì lặng lẽ tính vào lift. Đây là bài học giá trị nhất và khớp kiến trúc sẵn có.
2. **Mức giảm giá/voucher depth như một arm thí nghiệm** (học từ dynamic pricing, nhưng làm *đúng cách nhân quả*): thay vì mô hình giá hộp đen, cho tổ vận hành đo được "giảm 10% với 20% khác nhau bao nhiêu đơn" bằng switchback — biến điểm mạnh của họ thành sân nhà của mình.
3. **Kết cục trễ sau phiên** (học từ churn + hướng marketplace): ghi nhận trong lộ trình một lớp tín hiệu "sau phiên" (khán giả quay lại phiên sau; review sau đơn live). Nếu nguồn không cấp tín hiệu này — tuyên bố qua ma trận tín hiệu như hiện hành.
4. **Trình diễn chiều sâu một cách trực quan khi pitch:** giám khảo thấy "nhiều tính năng" dễ hơn thấy "coverage 95.5%". Chuẩn bị demo 60 giây: màn hình /host bị làm mù cạnh màn hình điều phối, và một lần chạy A/A trực tiếp — để chiều sâu phương pháp *nhìn thấy được* như độ rộng tính năng của đối thủ.
5. **Theo dõi đối thủ tiềm năng tại AISC'26:** bốn thành viên CELLAXNET (K2024 UIT) và hệ sinh thái AREA 303/Ba3.studio là nguồn đội mạnh về AI + e-commerce. Chuẩn bị sẵn 1 slide phân biệt "phân tích mô tả vs đo lường nhân quả" phòng khi bị xếp cùng rổ.

## 5. Nguồn

| # | Nguồn | Truy cập | Ghi chú |
|---|---|---|---|
| 1 | Bài đăng Facebook Khoa HTTT – UIT (link share https://www.facebook.com/share/1ERf7kmCcD/) | 10/09/2026 | Nguồn duy nhất về CELLAXNET; bài đăng công khai, đăng ~09/09/2026 |
| 2 | https://forum.uit.edu.vn/t/area-303-the-buffalo-playground-san-choi-ai-data-e-commerce-danh-cho-sinh-vien-uit/161513 | 10/09/2026 | Thể lệ, bảng thi, mốc thời gian AREA 303 |
| 3 | https://www.facebook.com/Ba3.studio/ và https://www.linkedin.com/in/khoa-nguyen-q/ | 10/09/2026 | Ba3.studio — đơn vị gắn với BTC; "Creative eCommerce Studio" hỗ trợ SME (mô tả tự công bố, chưa xác minh độc lập) |
| 4 | WebSearch nhiều truy vấn ("CELLAXNET…", tổ hợp tính năng) | 10/09/2026 | Xác nhận CELLAXNET **không có** hiện diện web nào khác được lập chỉ mục |

*Tài liệu này tuân thủ nguyên tắc dự án: thông tin không xác minh được đều ghi rõ "chưa xác minh"; không suy diễn số liệu thay đối thủ.*
