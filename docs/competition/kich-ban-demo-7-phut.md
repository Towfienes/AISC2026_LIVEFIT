# Kịch bản demo 7 phút trước hội đồng

*Viết ngày 14/09/2026. Mọi bước dưới đây đã bấm thật trên máy và chụp màn hình
lại; không bước nào là dự định.*

Bài này trả lời đúng ba câu: **bấm gì**, **nói gì**, và **nếu hỏng thì làm gì**.
Đọc một lần trước hôm thi, in ra một trang, để cạnh bàn phím.

---

## 0. Chuẩn bị — làm trước giờ trình bày 15 phút

Bốn lệnh, theo đúng thứ tự. Đừng bỏ lệnh nào, kể cả khi "hôm qua vẫn chạy".

```bash
# (1) Khởi động sạch: dừng tiến trình cũ, dọn thư mục build thừa, đo kho,
#     đợi /health xanh, rồi TẢI THẬT tệp CSS về cân.
.venv/Scripts/python scripts/chay_local.py --force --tach

# (2) Số trong tài liệu phải khớp số trong kho mã (hội đồng có thể đối chiếu).
.venv/Scripts/python scripts/dong_bo_so_test.py --xem-truoc

# (3) Gieo bộ demo vàng vào ĐÚNG kho đang chạy. Gọi lại không sinh bản trùng.
curl -X POST http://127.0.0.1:8000/demo/seed-vang

# (4) Gieo một phiên ĐANG PHÁT mới, để đồng hồ nằm trong lịch khối.
curl -X POST http://127.0.0.1:8000/demo/seed \
     -H "Content-Type: application/json" \
     -d '{"n_sessions":1,"duration_min":60}'
```

Bước (4) quan trọng hơn vẻ ngoài của nó. Phiên đang phát gieo từ hôm trước sẽ
hiện `04:33:44 / 01:00:00` và khối hiện tại là **NGOÀI KHỐI** — người dẫn nhìn
vào tưởng hệ thống hỏng. Gieo mới thì đồng hồ nằm giữa lịch khối, và mọi thứ
trên bàn trợ live động đậy đúng như buổi live thật. Tên phiên có kèm giờ gieo
nên trong danh sách cứ chọn cái mới nhất.

Mở sẵn **ba tab** và đừng mở thêm tab nào trong lúc trình bày:

| Tab | Địa chỉ | Dùng ở phút |
|---|---|---|
| 1 | `http://127.0.0.1:3000/` | 0–1 |
| 2 | `http://127.0.0.1:3000/desk` | 2–4 |
| 3 | `http://127.0.0.1:3000/ket-qua` | 4–6,5 |

Mở thêm một cửa sổ riêng cho `/host` và kéo sang màn phụ nếu có hai màn. Không
có màn phụ thì dùng `Alt+Tab`, đừng mở thành tab thứ tư — lúc căng thẳng rất dễ
bấm nhầm.

---

## 1. Phút 0:00–1:00 — Đặt vấn đề, đừng mở phần mềm vội

Để nguyên trang chủ trên màn hình. **Nói**, không bấm:

> Phút 30 của một buổi live, người trợ live ghim sản phẩm B. Phút 35, doanh thu
> nhích lên thấy rõ. Tối đó ngồi tổng kết, không ai trả lời được câu đơn giản
> nhất: vì sao? Vì vừa ghim B? Vì đúng phút đó thuật toán nền tảng đẩy thêm
> người vào phòng? Hay vì người dẫn vừa kể xong một câu chuyện hay?
>
> Ba lời giải thích ấy chồng lên nhau trong cùng năm phút, và nhìn số liệu sau
> phiên thì cả ba đều khớp. Mọi công cụ hiện có — TikTok LIVE Manager, Kalodata,
> Chanmama — đều trả lời được câu "phiên vừa rồi bán được bao nhiêu". Không công
> cụ nào trả lời được câu "bao nhiêu trong số đó là do hành động của bạn".

Chỉ tay lên ba ô số trên trang chủ (19.126 · 16 · 993) và nói một câu:

> Ba con số này là số liệu nhóm em đo được, không phải số quảng cáo. Mỗi con số
> truy về được đúng một tệp trong kho mã.

**Không** đọc to phần giới thiệu tính năng. Hội đồng tự đọc được.

---

## 2. Phút 1:00–2:00 — Vì sao không A/B test được

Vẫn chưa bấm gì. Đây là phần quyết định bài thi, và nó là một ý chứ không phải
một màn hình:

> Cách chuẩn để trả lời câu đó là A/B test: chia người xem làm hai nửa. Trong
> livestream thì không chia được, vì mọi người trong phòng nhìn cùng một màn
> hình. Không thể ghim sản phẩm cho một nửa khán giả và đồng thời không ghim cho
> nửa còn lại — trừ khi bạn là chủ nền tảng.
>
> Nên phải chia thời gian thay vì chia người. Muốn biết cái quạt có làm mát
> phòng không mà chỉ có một cái quạt và một căn phòng, ta bật 5 phút, tắt 5
> phút, bốc thăm thứ tự để không tự lừa mình, rồi so nhiệt độ khoảng bật với
> khoảng tắt. LiveLift làm đúng vậy với phiên live: cắt 90 phút thành 16 khối 5
> phút, mỗi khối bốc thăm bật hoặc tắt, và **lịch bốc thăm lưu lại trước khi lên
> sóng**.

Câu cuối là câu phải nhấn. Nó là ranh giới giữa thí nghiệm và quan sát.

---

## 3. Phút 2:00–4:00 — Bàn trợ live: cho xem lịch đã bốc

Chuyển sang **tab 2** (`/desk`). Ô chọn phiên tự chọn phiên đang phát mới nhất,
nên bình thường không phải bấm gì — chỉ liếc xem đồng hồ có nằm trong thời
lượng phiên không (đúng thì nó hiện kiểu `00:30:31 / 01:00:00` kèm
`KHỐI HIỆN TẠI · #6/10`). Nếu thấy **NGOÀI KHỐI** thì mở ô chọn và lấy phiên có
giờ gieo mới nhất.

**Bấm và nói theo thứ tự này:**

1. **Chỉ vào dải BẬT/TẮT** ở giữa màn hình.

   > Đây là lịch đã bốc, sinh ra trước giờ phát và gắn vân tay SHA-256. Nhóm em
   > không thể sửa nó giữa phiên — có sửa thì bảng ghi lại, vì bảng này chỉ ghi
   > thêm chứ không ghi đè.

2. **Chỉ vào ô "KHỐI HIỆN TẠI"** bên trái.

   > Người trợ live chỉ cần biết đúng một điều: giờ đang ở khối BẬT hay khối
   > TẮT, và còn bao lâu thì chuyển.

3. **Chỉ vào thẻ "HÀNH ĐỘNG GỢI Ý"** bên phải.

   > Trong khối BẬT, hệ thống gợi ý ghim sản phẩm nào. Trong khối TẮT, hệ thống
   > im lặng hoàn toàn — đội vận hành làm như thường lệ. Chênh lệch giữa hai
   > nhánh chính là thứ cần đo.

4. **Chỉ vào ô "TIM & QUÀ — THIẾU nguồn"** (góc dưới trái). Đây là chỗ ăn điểm,
   đừng lướt qua.

   > Ô này nói THIẾU chứ không hiện số 0. Nguồn tim và quà tặng thì nền tảng
   > không mở, nên hệ thống tuyên bố là không có, thay vì vẽ một đường phẳng ở
   > mức 0 rồi để người dùng tưởng khán giả không tương tác. Đây là một sự cố
   > thật nhóm em từng mắc và đã sửa.

5. **Chỉ vào khối BÁO ĐỘNG màu đỏ** ở dưới cùng bên phải (nếu có).

   > Một khối BẬT đã trôi qua mà không ai ghim. Hệ thống nói thẳng là không ghim
   > bù được, và khối này sẽ bị tính là không tuân thủ trong báo cáo. Nó không
   > lặng lẽ bỏ qua, cũng không cho sửa lại lịch sử.

6. **Chuyển sang cửa sổ `/host`** (Alt+Tab).

   > Đây là màn hình người dẫn nhìn. Nó có đúng bốn trường: sản phẩm đang ghim,
   > giá, tồn kho, thời gian phát. Không có chữ BẬT, không có chữ TẮT, không có
   > lịch.
   >
   > Đây không phải quy ước nội bộ mà là ràng buộc ở cấp kiểu dữ liệu: muốn hiện
   > trạng thái khối lên màn này thì phải sửa định nghĩa kiểu, và bộ kiểm thử sẽ
   > chặn. Vì nếu người dẫn biết mình đang ở khối BẬT, họ sẽ nói hăng hơn, và thứ
   > đo được sẽ là tâm lý người dẫn cộng với hệ thống, không phải hệ thống.

Quay lại tab 2 trước khi sang phần sau.

---

## 4. Phút 4:00–6:30 — Kết quả: phần mạnh nhất của bài

Chuyển sang **tab 3** (`/ket-qua`). Kéo xuống mục **PHIÊN DEMO**.

Ở đây có sáu phiên demo vàng, phủ **cả ba trạng thái** mà màn kết quả có thể
rơi vào. Mở theo đúng thứ tự này — thứ tự là một lập luận, đừng đảo:

### 4a. Mở "Demo vàng · DƯƠNG rõ #1" (bấm **Kết quả**)

> Tác động +1,224, khoảng tin cậy 95% từ +0,932 đến +1,498. Khoảng này không
> chứa 0, nên có bằng chứng thí nghiệm rằng hệ thống làm tăng lượt nhấp.
>
> Con số này không tính bằng công thức tiệm cận. Hệ thống bốc lại lịch gán mười
> nghìn lần bằng **chính hàm bốc thăm đang chạy thật**, rồi xem chênh lệch thật
> nằm ở đâu trong phân bố đó. Làm vậy vì một phiên chỉ có 16 đến 24 khối, cỡ mẫu
> đó quá nhỏ để công thức thông thường cho sai số đúng.

### 4b. Mở "Demo vàng · NULL (KTC chứa 0) #1"

> Tác động −0,173, khoảng tin cậy từ −0,490 đến +0,181. Khoảng này chứa 0, nên
> **không** kết luận được là có tác động.
>
> Nhóm em dựng màn hình cho trạng thái này công phu ngang trạng thái đẹp, và đó
> là chủ ý. Null là kết cục dễ xảy ra nhất trong thí nghiệm thật. Một công cụ
> chỉ tôn vinh kết quả đẹp thì sớm muộn người dùng sẽ học được rằng cứ chạy lại
> đến khi ra số đẹp thì thôi.

### 4c. Mở "Demo vàng · CHƯA ĐỦ ĐIỀU KIỆN" — **đây là điểm nhấn của cả bài**

> Phiên này hệ thống **từ chối trả về một con số**, và nói rõ vì sao: 3 khối đo
> được, cần ít nhất 4. Nó không hạ ngưỡng, không nội suy, không đưa ra một con
> số kèm ghi chú nhỏ.
>
> Chỗ này ra đời từ một sự cố thật. Ngày 30/08, hệ thống từng tuyên bố "có ý
> nghĩa thống kê" trên dữ liệu thuần nhiễu: chạy 200 phiên mô phỏng không có tác
> động nào, nó tuyên 105 phiên là có ý nghĩa với p nhỏ hơn 0,001. Nguyên nhân là
> hàm thống kê trả về NaN khi một nhánh có dưới 2 khối, mà trong Python mọi phép
> so sánh với NaN đều cho False, nên bộ đếm ra 0 và p-value rơi thẳng xuống sàn.
> Giao diện đọc "cận dưới lớn hơn 0" là đúng nên hiện chữ "có bằng chứng".
>
> Tức là một dấu hiệu THIẾU dữ liệu bị đọc thành bằng chứng MẠNH. Sau đó nhóm em
> đặt luật: thà nói chưa kết luận được còn hơn đưa ra một con số. Màn hình các
> thầy cô đang nhìn chính là luật đó.

Nếu hội đồng chỉ có 5 phút, **bỏ 4a và 4b, giữ 4c**.

### 4d. Kéo xuống "Tóm tắt 3 câu"

> Ba câu này soạn bằng template tất định, không có mô hình ngôn ngữ nào sinh
> chữ. Rê chuột lên từng câu sẽ hiện nguồn của từng con số trong câu. Nhóm em cố
> ý không dùng AI sinh văn ở đây, vì một câu tóm tắt sai trong báo cáo khoa học
> thì tệ hơn là không có câu nào.

---

## 5. Phút 6:30–7:00 — Đóng bài bằng chỗ còn thiếu

Không mở thêm màn hình nào. Nói thẳng:

> Ba chỗ nhóm em còn thiếu, xin nói trước khi hội đồng hỏi.
>
> Thứ nhất: **chưa chạy phiên thí nghiệm ngẫu nhiên thật nào**. Mọi con số ở
> trên hoặc từ dữ liệu mô phỏng có tác động biết trước, hoặc từ 16 buổi live
> thật nhưng là phân tích hồi cứu, không có bốc thăm. Phiên khẳng định đầu tiên
> nhóm em đặt lịch ngày 06/10.
>
> Thứ hai: **bộ phân loại ý định bình luận chưa dùng được**. Trên bộ tự biên
> soạn nó đạt macro-F1 0,870, nhưng trên chat bán hàng thật chỉ còn 0,271 — thua
> cả cách đoán bừa một nhãn. Nhóm em công bố con số đó thay vì giấu, và xếp radar
> ý định xuống biến thứ cấp.
>
> Thứ ba: **chưa đo được tới đơn hàng**. Biến chính là lượt nhấp hợp lệ qua link
> đo của chính nhà bán. Đơn hàng nằm trong app của nền tảng, và ở quy mô dưới 50
> người xem đồng thời thì cỡ mẫu cũng chưa đủ để nói gì về nó.
>
> Cả 41 sự cố trong sổ đều do chính nhóm em tìm ra, không phải do người ngoài
> chỉ. Nhóm em tin một đội dám nói giới hạn của mình bằng số thì đáng tin hơn
> một đội khẳng định mọi thứ đều tốt.

---

## 6. Hỏng thì làm gì

Ba tình huống đã xảy ra thật, kèm cách xử trong 30 giây.

| Triệu chứng | Nguyên nhân thường gặp | Làm gì ngay |
|---|---|---|
| Trang hiện ra như văn bản thô, không màu, không bố cục | Thư mục build hỏng hoặc tiến trình cũ giữ cổng 3000 | Chạy lại `scripts/chay_local.py --force --tach`, mất khoảng 60 giây. Trong lúc chờ thì nói tiếp phần 2 (không cần màn hình) |
| `/ket-qua` không có phiên demo nào | Chưa gieo, hoặc API vừa khởi động lại | `curl -X POST http://127.0.0.1:8000/demo/seed-vang` |
| Bàn trợ live hiện **NGOÀI KHỐI**, đồng hồ chạy quá thời lượng phiên | Phiên đang phát là phiên cũ gieo từ hôm trước | Gieo phiên mới bằng lệnh (4) ở mục 0, rồi chọn lại phiên có giờ gieo mới nhất |
| `/health` báo `durable: false` | Chưa bật PostgreSQL — hệ thống đang chạy kho RAM | **Không sao cho buổi demo.** Nếu hội đồng hỏi thì trả lời thẳng: dữ liệu đang nằm trong RAM có ảnh chụp mỗi 30 giây, phiên live thật thì bật Postgres trước. Trang /health nói đúng điều đó, không giấu |

Một nguyên tắc cho cả buổi: **nếu một màn hình không lên, đừng bấm lại lần thứ
ba.** Chuyển sang phần nói, xử lý sau. Hội đồng nhớ nội dung chứ không nhớ ai
bấm trượt.

---

## 7. Bốn câu hỏi chắc chắn sẽ bị hỏi

**"Sao không dùng luôn Statsig/Eppo cho nhanh?"**
Vì cả ba nền tảng đó đều giả định bạn sở hữu nơi thí nghiệm diễn ra: nhúng SDK
và chia luồng người dùng. Nhà bán livestream không sở hữu TikTok hay Facebook.
Thứ duy nhất họ kiểm soát là hành động của chính mình theo thời gian — và
LiveLift biến đúng thứ đó thành đơn vị bốc thăm. Một Statsig rẻ hơn cũng không
giải quyết được, vì cái thiếu không phải tiền mà là quyền chia luồng người xem.

**"Đo lượt nhấp thì có ý nghĩa gì với nhà bán? Họ cần doanh thu."**
Đúng, và nhóm em nói thẳng là chưa đo tới đó. Lý do là cỡ mẫu: ở quy mô không
quá 50 người xem đồng thời, hiệu ứng nhỏ nhất mà thiết kế đủ sức phát hiện với
biến đơn hàng vẫn khoảng 79%, còn với biến nhấp là 20,1%. Đo một thứ không đủ
sức phát hiện thì báo cáo sẽ luôn nói "không có tác động", bất kể sự thật.

**"Sao chưa chạy phiên thật nào mà đã đi thi?"**
Vì thứ nhóm em mang đi thi là phương pháp đo và hạ tầng thực hiện nó, cộng bằng
chứng rằng bộ ước lượng đã hiệu chỉnh đúng: A/A 200 lần lặp cho tỷ lệ bác bỏ
4,5% so với mức danh nghĩa 5%, độ phủ khoảng tin cậy 95,5%, thu hồi tác động
biết trước lệch −0,3%. Chạy phiên thật trước khi bộ ước lượng hiệu chỉnh xong
thì con số đầu tiên thu được cũng không tin được.

**"TikTok là nền tảng lớn nhất, sao không làm TikTok?"**
Nhóm em đã thử và thất bại, có ghi lại: Cloudflare từ chối bắt tay WebSocket
10/10 lần, và yt-dlp không có bộ trích bình luận cho TikTok — kiểm trong mã
nguồn của họ chứ không đoán. Nên hệ thống chỉ dùng API chính thức: YouTube,
Facebook Graph, Shopee Open Platform. Bộ thu TikTok để riêng ngoài lõi và có
cổng CI chặn mọi lệnh import ngược vào lõi, để một ngày nó hỏng thì không kéo
theo phần đo lường.
