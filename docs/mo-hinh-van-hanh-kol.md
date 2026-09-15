# Mô hình vận hành: KOL / shop dùng LiveLift thật thì như thế nào?

*Viết cho chủ dự án, không phải cho kỹ sư. Mọi câu "chạy được / không chạy được"
trong tài liệu này đều được kiểm chứng bằng mã nguồn hoặc bằng một lần chạy thật
ngày 11/09/2026 — chỗ nào chưa thử thì ghi thẳng là **chưa thử**.*

---

## 0. Trả lời thẳng năm câu hỏi, trong một trang

| Câu hỏi của anh | Trả lời ngắn |
|---|---|
| **Mở phiên live từ nền tảng khác rồi bật sản phẩm lên thì test được không?** | **Được một phần, và phần được phụ thuộc nền tảng.** YouTube: được. Facebook Page của chính mình: được sau ~25 phút lấy token. TikTok: **không** — không đọc được một bình luận nào. Shopee: adapter đã viết xong, chỉ thiếu tài khoản. |
| **Nếu dùng sản phẩm thì hiện đang cần làm những gì?** | Tối thiểu để **một phiên chạy được**: tạo phiên + bốc lịch BẬT/TẮT. Chỉ hai thứ đó. Nhưng để **ra được một con số nhân quả** thì cần thêm ba thứ nữa: nguồn bình luận, **số người xem theo thời gian**, và **link đo click**. Thiếu một trong ba → hệ thống tự tuyên bố "không đo được", không bịa số. |
| **Khi ra product, một KOL muốn dùng thì thế nào?** | Hôm nay: **không tự dùng được**. Không có đăng nhập, không có tài khoản riêng, danh mục sản phẩm dùng chung toàn hệ thống, bộ thu bình luận là một lệnh chạy trong terminal. Cần một kỹ sư ngồi cạnh. Danh sách việc phải làm để bỏ được kỹ sư đó: **mục 6**. |
| **Mở một live bán hàng bất kỳ rồi bật dự án lên có được không, hay phải cấu hình?** | **Phải cấu hình.** Có đúng **một** đường dán-link-là-xong: `POST /replays/youtube` với một buổi YouTube **đã kết thúc** — không cần tài khoản gì, 1–2 phút ra báo cáo. Nhưng đó là **chế độ quan sát**: không có số nhân quả. Mọi thứ còn lại đều cần cấu hình trước phiên. |
| **Cho chuyên nghiệp thì mới đạt hiệu quả — vậy cách dùng như nào?** | Đúng, và đây là điều quan trọng nhất trong tài liệu: **LiveLift không phải dashboard cắm-vào-là-có-số. Nó là một hệ thí nghiệm.** "Chuyên nghiệp" ở đây không có nghĩa là giao diện đẹp hơn, mà là: có người vận hành riêng tách khỏi người dẫn, có link đo riêng, phiên **≥ 90 phút**, và chấp nhận rằng một nửa thời lượng phiên hệ thống **không được can thiệp** (nhánh đối chứng). Đổi lại: một con số có khoảng tin cậy, không phải một cảm giác. |

---

## 1. Điều phải hiểu trước tiên: ba CHẾ ĐỘ dùng, không phải một

LiveLift không có một nút "bật lên là có số". Nó có ba chế độ, mỗi chế độ đòi
hỏi khác nhau và **trả về loại kết luận khác nhau**. Nhầm ba chế độ này là nhầm
gốc.

| | **Chế độ 1 — QUAN SÁT** | **Chế độ 2 — ĐỀ XUẤT** | **Chế độ 3 — THÍ NGHIỆM ĐẦY ĐỦ** |
|---|---|---|---|
| Câu hỏi trả lời được | *"Buổi live đó diễn ra thế nào?"* | *"Bây giờ nên ghim cái gì?"* | *"Ghim theo hệ thống có **làm tăng** nhấp sản phẩm không?"* |
| Loại kết luận | Mô tả. Có dán nhãn `— quan sát, chưa kiểm chứng nhân quả` | Gợi ý, có ghi lại xác suất chọn | **Nhân quả**, có khoảng tin cậy 95% và p-value |
| Cần buổi live của ai | **Của bất kỳ ai** (YouTube công khai) | Của chính mình | **Bắt buộc của chính mình** |
| Chạy được hôm nay? | ✅ Chạy ngay, không cần tài khoản | ⚠️ Chạy được nhưng phải bấm tay | ⚠️ Chạy được, nhưng đòi hỏi nhiều nhất |
| Endpoint chính | `POST /replays/youtube` | `GET /sessions/{id}/state` → `POST .../actions/execute` | Toàn bộ vòng đời phiên |

### 1.1 Chế độ QUAN SÁT — cái duy nhất "dán link là xong"

**Bắt buộc (không có thì không chạy):**

1. Một link YouTube của buổi live **đã kết thúc** và **chat replay còn tồn tại**.
   Đó là tất cả.

**Nên có (có thì tốt hơn nhiều):**

- Buổi live có **≥ 100 bình luận**. Đo ngày 10/09 trên 17 video: 16 video vào được,
  nhưng chỉ **7 buổi** đạt ngưỡng đó, và **1 buổi 715 phút có 0 bình luận**. Có
  track `live_chat` **không** có nghĩa là có chat.
- `YTDLP_COOKIES_FROM_BROWSER=chrome` trong `.env` nếu YouTube bắt xác minh không phải bot.

**Hệ thống tự làm:**

- Tải chat replay, **lọc PII trước khi ghi** (số điện thoại viết bằng chữ, địa chỉ,
  tên — file chat thô bị xóa ngay sau khi parse, không bao giờ nằm lại trên đĩa).
- Phân loại ý định từng bình luận (11 lớp), dựng nhịp bình luận theo ô 30 giây,
  phát hiện **khoảnh khắc** (spike bình luận so với nền 5 phút trước đó).
- Đọc các sự kiện trả tiền công khai (Super Chat / quà / hội viên) nếu buổi đó có.
- **Tự dán nhãn là phiên QUAN SÁT** và từ chối in bất kỳ con số nhân quả nào.

**Cái chế độ này KHÔNG BAO GIỜ cho anh:**

- **Số người xem.** VOD đã kết thúc không còn lộ số người xem đồng thời — vĩnh viễn,
  không phải lỗi cài đặt. Cột người xem là **chỗ trống**, hệ thống ghi "THIẾU",
  không ghi 0.
- **Số nhấp sản phẩm.** Buổi live của người khác không đi qua link đo của mình.
- **Bất kỳ câu nhân quả nào.** Buổi phát gốc không có bốc thăm, nên không có gì để
  suy diễn.

### 1.2 Chế độ ĐỀ XUẤT — hệ thống gợi ý, người vận hành tự quyết

**Bắt buộc:**

1. Một phiên do **chính mình** vận hành, đã tạo trong hệ thống.
2. **Lịch gán khối đã được bốc và lưu trước khi phát sóng.** Không có lịch thì
   `POST /start` trả **409** — kiểm chứng ngày 11/09: *"Chưa có lịch gán khối —
   phiên không được phép phát sóng khi chưa sinh và lưu lịch gán"*.
3. **Ít nhất một sản phẩm còn tồn kho** trong danh mục. Không có thì bấm thẻ trả
   409 *"Không có sản phẩm còn hàng để ghim"*.
4. Một người ngồi bàn điều khiển và **bấm**.

**Nên có:**

- Link đo click (nếu không có thì thẻ gợi ý vẫn hiện, nhưng chúng xếp hạng bằng
  **prior**, không bằng dữ liệu của phiên).
- Nguồn bình luận trực tiếp (để radar ý định có gì để đọc).

**Hệ thống tự làm:**

- Chấm điểm từng sản phẩm bằng hậu nghiệm Gamma-Poisson **đúng đơn vị của biến kết
  quả chính** (nhấp / 1.000 viewer-giây), rồi đưa ra tối đa 3 thẻ.
- Khi mô hình **thật sự không chắc** (các khoảng ước lượng còn chồng lấn), nó **bốc
  thăm** giữa các ứng viên và **ghi lại xác suất đã bốc** — đây là thứ không công cụ
  thương mại nào ghi.
- Chặn cứng: thẻ gợi ý (`source='forecast'`) **không thể** mang khoảng tin cậy.
  Đây là ràng buộc kiểu dữ liệu, không phải quy ước — một thẻ dự báo kèm KTC
  không dựng lên được.

**Đo được gì:** tuân thủ (bao nhiêu khối BẬT thật sự có ghim), toàn bộ vết quyết
định (chọn gì, lúc nào, với xác suất bao nhiêu, trong tập ứng viên nào). **Không**
đo được tác động — đó là chế độ 3.

> ⚠️ **Một sự thật phải nói ngay:** chế độ phiên có nhãn `auto` (Tự động), nhưng
> **hôm nay không có bộ thực thi tự động nào ở phía máy chủ**. Nhãn `mode` được lưu
> và hiển thị, không có tiến trình nào đọc nó để tự ghim. Kiểm chứng bằng mã: không
> có scheduler, không có worker, không có tác vụ nền nào gọi `execute_action`.
> Trong một phiên 90 phút với khối 5 phút có **8 khối BẬT** — nghĩa là một người
> phải bấm **8 lần**, đúng lúc, suốt phiên. Xem mục 6, việc số 4.

### 1.3 Chế độ THÍ NGHIỆM ĐẦY ĐỦ — cái duy nhất cho ra con số nhân quả

**Bắt buộc — thiếu bất kỳ dòng nào là không có kết quả:**

| # | Điều kiện | Vì sao | Điều gì xảy ra nếu thiếu |
|---|---|---|---|
| 1 | Phiên **do chính mình vận hành** | Phải can thiệp được thì mới bốc thăm được | Không có chế độ 3, chỉ còn chế độ 1 |
| 2 | **Lịch BẬT/TẮT bốc trước khi lên sóng** | Đây là toàn bộ tính hợp lệ | API chặn `start` bằng 409 |
| 3 | **Link đo `/r/{code}`** cho từng sản phẩm, **có gắn `session_id`** | Biến kết quả chính = nhấp qua link đo | Tín hiệu `clicks` = THIẾU → năng lực "thí nghiệm nhân quả" = THIẾU |
| 4 | **Số người xem theo thời gian** (telemetry) | Là **mẫu số**: nhấp / 1.000 viewer-giây | Khối có < 60 viewer-giây bị **loại khỏi phân tích**, không phải tính là 0 |
| 5 | Phiên **≥ 90 phút** với khối 5 phút | Cần đủ khối để cân bằng | Xem bảng ngay dưới |
| 6 | Danh mục sản phẩm + tồn kho | Để có cái mà ghim | Bấm thẻ → 409 |
| 7 | Người dẫn **bị làm mù** với thiết kế | Người dẫn hào hứng hơn ở khối BẬT là nhiễu trực tiếp | Đo "hệ thống + tâm lý người dẫn", không đo hệ thống |

**Độ dài phiên — đo thật ngày 11/09/2026, khối 5 phút:**

| Thời lượng phiên | Số khối đo | Bảo đảm mỗi nhánh / mỗi 1/3 phiên | Cặp khối liền kề cùng nhánh | Hệ thống cảnh báo? |
|---:|---:|---:|---:|---|
| 30 phút | 4 | **0** (thiết kế cần 2) | **1** (cần 3) | ✅ cảnh báo kép |
| 60 phút | 10 | **1** (cần 2) | 3 | ✅ cảnh báo |
| **90 phút** | **16** (8 BẬT / 8 TẮT) | **2 — ĐẠT** | **3 — ĐẠT** | không cảnh báo |

**Kết luận vận hành, một dòng: dưới 90 phút thì đừng chạy chế độ 3.** Hệ thống vẫn
cho chạy, nhưng nó **nói thẳng trước khi lên sóng** rằng bảo đảm thiết kế không đạt.

**Nên có:**

- Hai người: một dẫn (chỉ nhìn màn hình `/host`), một vận hành (nhìn bàn điều khiển,
  ngồi khuất tầm mắt người dẫn).
- `INGEST_TOKEN` bật khi chạy trên môi trường thật — nó bảo vệ **cả 15 endpoint ghi**
  (không chỉ đường nạp bình luận). Máy chủ chạy thí nghiệm thật nên đặt thêm
  `PUBLIC_DEMO_WRITES=false` để khoá sạch đường ghi; để `true` chỉ khi cần cho người
  ngoài bấm thử trên phiên demo. Xem `docs/competition/sang-tao-tre-2026/08-VA-XAC-THUC.md`.
- `RESULTS_FREEZE_UNTIL` đặt đúng ngày đóng băng — trước ngày đó hệ thống **từ chối
  hiển thị** ước lượng tác động, chỉ trả số vận hành. Cấu hình sai định dạng thì
  **khóa luôn** cho tới khi sửa.

**Hệ thống tự làm:**

- Bốc thăm Bernoulli(0,5) từng khối, **vẽ lại** tới khi cân bằng; jitter ranh giới
  ±30 giây để nhịp đổi khối không đồng bộ với kịch bản show.
- Công bố **`design_hash`** = SHA-256 của (tham số thiết kế + seed) **trước** khi
  phát. Ai giữ hash đó đều kiểm tra lại được là thiết kế đã chạy đúng là thiết kế
  đã công bố.
- Ghi toàn bộ lịch vào bảng **chỉ-ghi-thêm** ngay lúc bốc; mọi hành động ghim đi vào
  một bảng chỉ-ghi-thêm thứ hai. Tuân thủ là đại lượng **dẫn xuất** từ phép nối hai
  bảng — không ai sửa được thành khớp nhau.
- Phân loại click hợp lệ tại thời điểm ghi (5 quy tắc IAB/GIVT-lite), **gắn cờ chứ
  không xóa**.
- Chặn cứng `/host`: màn hình người dẫn **không có trường nào** để mang thông tin
  khối. Kiểm chứng hôm nay: `/state?role=host` trả về đúng 4 khóa —
  `pinned_product`, `price`, `stock`, `elapsed_s`.
- Từ chối can thiệp thủ công ngoài **ba** lý do: `hết hàng`, `sai giá`, `sự cố kỹ thuật`.
- Chạy đúng đường phân tích đã tiền đăng ký: kiểm định ngẫu nhiên hóa **vẽ lại bằng
  chính hàm gán production**, KTC 95% bằng nghịch đảo kiểm định.

---

## 2. Điều gì THỰC SỰ bắt buộc — kiểm chứng bằng cách chạy thật

Tôi dựng một bản LiveLift sạch trong bộ nhớ (không chạm vào API đang giữ 13 phiên
thật) và thử từng giả thuyết. Kết quả:

| Câu hỏi | Kết quả THẬT | Ý nghĩa vận hành |
|---|---|---|
| Bắt buộc tạo sản phẩm trước không? | **KHÔNG.** Phiên không có sản phẩm nào vẫn `schedule` → `start` → `live` (HTTP 200) | Có thể lên sóng với danh mục rỗng — và thu về một thí nghiệm **rỗng**. Hệ thống không chặn, nhưng cũng không giấu |
| Bắt buộc có lịch gán không? | **CÓ.** `start` khi chưa bốc lịch → **409** | Đây là quy tắc bất biến duy nhất được cưỡng chế ở tầng API |
| Bắt buộc có link đo không? | **KHÔNG để chạy, CÓ để đo** | Ma trận tín hiệu sau phiên: `clicks → missing`, năng lực *"thí nghiệm nhân quả (BẬT/TẮT)"* → **missing**, lý do *"thiếu clicks, ticks"* |
| Tạo link đo cho sản phẩm chưa có? | **404 "Không tìm thấy sản phẩm"** | Muốn có link đo thì **bắt buộc** phải tạo sản phẩm trước. Đây là ràng buộc thật duy nhất bắt sản phẩm phải tồn tại |
| Phiên chỉ có bình luận, không có người xem, không có click? | Báo cáo ra `ket_qua_thi_nghiem.estimable = **false**`, kèm câu *"Chưa đủ khối đo được để ước lượng (0 khối, cần ≥ 4) — tuyên bố thiếu, không trả số"* | **Hệ thống không bịa số.** Đây là điểm mạnh nhất của nó |
| Có đường nào ghi **đơn hàng** vào hệ thống không? | **KHÔNG.** Toàn bộ 22 đường dẫn của API, không có đường nào ghi đơn. Bảng `order_event` và hàm `add_order` **tồn tại trong mã nhưng không có ai gọi** | Năng lực *"đối soát doanh thu"* **vĩnh viễn = THIẾU** cho tới khi có endpoint. Xem mục 4 và mục 6 |
| Danh mục sản phẩm có tách theo chủ/theo phiên không? | **KHÔNG.** Tạo sản phẩm ở phiên 1, phiên 2 (khác nền tảng) **vẫn thấy nguyên** trên thẻ gợi ý | Hai KOL dùng chung một máy chủ sẽ thấy hàng của nhau. **Chặn việc mở dịch vụ cho nhiều người** — mục 6, việc số 1 |
| Link đo tạo **không kèm `session_id`** thì sao? | Bấm 2 link (một có, một không), phiên chỉ ghi nhận **1** lượt nhấp | **Cái bẫy đắt nhất của cả hệ thống.** Link thiếu `session_id` vẫn chuyển hướng bình thường, người xem không thấy gì lạ, nhưng **cú bấm biến mất khỏi thí nghiệm** |
| Bấm link bằng `curl`? | HTTP **302** (vẫn chuyển hướng) nhưng bị gắn cờ không hợp lệ | Đúng thiết kế: redirect **không bao giờ** được hỏng vì chuyện đo đạc |

---

## 3. Bốn tình huống thật, viết như kịch bản

### (a) KOL live trên YouTube

**Hôm nay làm được đến đâu:** đây là nền tảng hoàn chỉnh nhất.

| Bước | Việc | Ai làm | Hôm nay? |
|---|---|---|---|
| 1 | Xin `YOUTUBE_API_KEY` ở Google Cloud Console (miễn phí, không cần thẻ, không cần xét duyệt) | Kỹ sư | ⏳ **chưa làm** — `.env` đang trống. ~10 phút |
| 2 | Tạo sản phẩm + nhập link trang sản phẩm thật (giao diện `/chay-phien`, bước 1) | KOL | ✅ |
| 3 | Tạo phiên, chọn thời lượng **≥ 90 phút** | KOL | ✅ |
| 4 | Bốc lịch BẬT/TẮT, **ghi lại seed** | Hệ thống | ✅ |
| 5 | Bấm "Bắt đầu phát sóng" → hệ thống sinh link đo `/r/{code}` cho từng sản phẩm có URL hợp lệ | Hệ thống | ✅ |
| 6 | **Khởi động bộ thu bình luận** — một lệnh trong terminal, cần **video id** của buổi live | Kỹ sư | ⚠️ **CLI, không có nút bấm** |
| 7 | Trong phiên: dán link `/r/{code}` vào bình luận ghim mỗi khi giới thiệu sản phẩm | Người vận hành | ✅ (thủ công) |
| 8 | Trong mỗi khối BẬT: bấm thẻ gợi ý ở bàn điều khiển (8 lần / 90 phút) | Người vận hành | ⚠️ **phải bấm tay** |
| 9 | Kết thúc phiên → xem báo cáo | Hệ thống | ✅ |

**Hai đường thu YouTube, chọn đúng:**

| | `INGEST_YOUTUBE_BACKEND=api` | `=ytdlp` |
|---|---|---|
| Cần gì | `YOUTUBE_API_KEY` | không cần gì |
| Hôm nay chạy được? | ❌ (chưa có key) | ✅ |
| Hợp Điều khoản dịch vụ? | ✅ **hợp lệ** | ❌ **KHÔNG** — robots.txt YouTube chặn đúng hai đường yt-dlp gọi |
| Độ trễ bình luận (đo thật) | 2–5 giây | **~24 giây (p50), 37 giây (p90)** |
| Quota | 10.000 đv/ngày — phiên 90 phút poll 5 giây ≈ 5.400 đv (**quá nửa ngày**) | không có |

> **Việc số 1 của toàn bộ dự án là xin cái key đó.** 10 phút, miễn phí, và nó biến
> toàn bộ đường YouTube từ "trái Điều khoản" thành hợp lệ. Rào cản duy nhất đang là
> *chưa ai tạo project Google Cloud*.

**Cái YouTube KHÔNG có:** bất kỳ tín hiệu thương mại nào. Không đơn hàng, không GMV.
Nếu KOL bán qua YouTube thì khách phải rời nền tảng để mua — nghĩa là **link đo hoạt
động đúng bản chất**, và đó chính là lý do YouTube là nơi thí nghiệm dễ chạy nhất.

### (b) KOL live trên Facebook — Fanpage của chính họ

| Bước | Việc | Thời gian | Hôm nay? |
|---|---|---|---|
| 1 | KOL là quản trị viên Fanpage + tạo một app Meta ở **Development Mode** | ~15 phút | ⏳ |
| 2 | Lấy **Page token dài hạn** với **hai** quyền: `pages_read_engagement` **và** `pages_read_user_content` | ~10 phút. **Không cần App Review** | ⏳ `.env` đang trống |
| 3 | Chạy `python scripts/kiem_tra_facebook.py` — phải in **"KẾT LUẬN: SẴN SÀNG"**, và nó in luôn `Live video id` để dán vào bộ thu | 30 giây | ✅ script đã có |
| 4–9 | Giống YouTube từ bước 2 trở đi | | |

> **Cái bẫy đắt nhất ở Facebook:** `pages_read_engagement` chỉ cho đọc nội dung **Page
> tự đăng**. Bình luận là nội dung **người xem**. Thiếu `pages_read_user_content` thì
> đọc được **0 bình luận** — mà đó chính là thứ cần đo. Đã thử thật 5 đường không
> token: **không đường nào lấy được một bình luận nào.**

**Live của Page người khác:** cần Advanced Access + Business Verification của Meta.
Dự trù **4–6 tuần**, và phải có văn bản đồng ý của chủ Page. Không lách.

**Video Facebook đã kết thúc của Page mình có đọc được bình luận không?**
**Gần như chắc chắn có, nhưng nhóm CHƯA kiểm chứng được** (chưa có token). Đừng ghi
vào hồ sơ như việc đã chạy. Sau khi có token: phát live thử 2 phút, kết thúc, gọi
`/{video-id}/comments` — 5 phút là biết.

**Một rủi ro kinh doanh phải nói với KOL:** dán link ngoài vào bình luận trên Facebook
có thể bị hạ phân phối. Nhóm **chưa đo** mức độ ảnh hưởng — đây là câu hỏi cho chính
KOL, không phải cho kỹ sư.

### (c) KOL live trên TikTok Shop — tình huống phổ biến nhất ở Việt Nam, và khó nhất

**Nói thẳng trước: hôm nay LiveLift gần như không làm được gì tự động cho một KOL
bán trên TikTok Shop.** Không có cách diễn đạt nào làm điều này dễ nghe hơn.

**Ba lớp tường, đã thử thật, không phải phỏng đoán:**

| Lớp | Đã thử gì | Kết quả THẬT |
|---|---|---|
| Bình luận live đang phát | Bắt tay WebSocket giao thức Webcast | **HTTP 400, 10/10 lần, 0 bình luận** |
| Bình luận nội dung đã kết thúc | Trang hồ sơ, trang `/live`, `api/comment/list` | Trang WAF 1.155–1.462 byte; API trả `status_code 5` = từ chối; thêm tham số chuẩn → thân phản hồi **0 byte** |
| Công cụ sẵn có | `yt-dlp` trên video TikTok | `Unexpected response`. Và quyết định hơn: `yt_dlp/extractor/tiktok.py` **không có `_get_comments`** — yt-dlp **chưa bao giờ** đọc bình luận TikTok. Đây không phải "hỏng hôm nay mai sửa" |
| Đường chính thức | TikTok Research API (**có** endpoint bình luận) | **Việt Nam không đủ điều kiện** — yêu cầu tổ chức học thuật Mỹ/EEA/UK/Canada/Thụy Sĩ. FAQ chỉ nói *"hy vọng mở rộng"* — một lời hứa, không phải lộ trình có ngày |

**Và lớp tường thứ tư, nặng hơn cả ba lớp trên — chuyện đo lường, không phải chuyện
kỹ thuật:**

> Người mua trên TikTok Shop bấm **giỏ hàng trong app**. Họ không bấm link ngoài.
> Nghĩa là **biến kết quả chính của LiveLift (nhấp qua `/r/{code}`) không tồn tại**
> trên kênh này. Và nếu ta cố ép — dán link ngoài để đo — thì ta **đẩy khách ra khỏi
> phễu mua hàng của chính KOL**. Không KOL nào chấp nhận đánh đổi doanh thu thật lấy
> một phép đo. **Đừng đề xuất phương án đó.**

**Vậy hôm nay LiveLift làm được gì cho KOL TikTok?**

| Việc | Được không? | Ghi chú |
|---|---|---|
| Đọc bình luận tự động | ❌ | Ba lớp tường ở trên |
| Đọc số người xem | ❌ | Cùng lý do |
| Đo click | ❌ | Khách mua trong app |
| **Phát song song lên YouTube (restream) rồi chạy LiveLift trên luồng YouTube** | ✅ **ĐƯỢC — và đây là đường thật duy nhất hôm nay** | Có bằng chứng: một buổi `[LAZLIVE]` đã vào hệ thống qua YouTube VOD. Khán giả YouTube khác khán giả TikTok, nên kết luận chỉ áp cho luồng YouTube — phải nói rõ điều đó |
| Nhập bình luận + số người xem **bằng tay** qua API | ✅ về kỹ thuật, ❌ về thực tế | `POST /comments` và `POST /ticks` nhận dữ liệu nhập tay. Nhưng phải gõ **liên tục suốt phiên**, và giao diện web **không có ô nhập** — chỉ làm được bằng lệnh. Không ai làm nổi ở nhịp live thật |
| Tạo phiên `platform=tiktok` | ✅ tạo được | Nhưng bộ thu **không nhận** `tiktok` (chỉ `youtube`, `facebook`, `shopee`). Phiên sẽ rỗng |

**Đường để làm được sau này — xếp theo giá trị ÷ công sức:**

1. **Dò danh mục TikTok Shop Partner API** (`open-api.tiktokglobalshop.com`). Hôm nay
   **chưa dò được**: cổng xác nhận `app_key` có thật, nhưng đường `live/...` là do
   **đoán tên** và đối chứng cũng trả 404 — nên 404 ở đây chỉ có nghĩa "đoán sai tên",
   **không** có nghĩa "không tồn tại". Phải đăng nhập Partner Center đọc danh mục v2.
   **30 phút để có kết luận dứt điểm.** TikTok Shop là kênh live-commerce lớn nhất
   Việt Nam — nếu họ có module live như Shopee thì đó là nguồn dữ liệu giá trị nhất
   của cả đề tài, và hoàn toàn hợp Điều khoản vì là API chính thức cho shop của chính mình.
2. **Nhập đơn hàng sau phiên** (xuất báo cáo đơn từ TikTok Shop → nhập vào LiveLift →
   gán về khối theo dấu thời gian đặt đơn). Xem phân tích ở mục 4.3 — **có giá trị
   nhất về mặt phương pháp, nhưng hôm nay chưa có đường ghi đơn vào hệ thống**.
3. Restream sang YouTube — làm được ngay, nhưng đo trên tập khán giả khác.

**Câu nên nói với hội đồng (và với KOL), nguyên văn:**

> *"TikTok là kênh live-commerce lớn nhất Việt Nam nhưng không có API công khai cho
> bình luận live. Chúng tôi đã hiện thực và kiểm chứng một bộ thu thập cách ly; tính
> đến 11/09/2026 đường không chính thức bị chặn ở tầng WebSocket (HTTP 400, 10/10 lần)
> và ở tầng WAF với nội dung đã kết thúc, còn Research API chính thức không mở cho tổ
> chức Việt Nam. Kết quả của chúng tôi vì vậy dựa trên các nền tảng có API chính thức."*

### (d) Shop tự live trên nhiều nền tảng cùng lúc

**Hôm nay:** mỗi nền tảng là **một phiên riêng** trong LiveLift, và **một tiến trình
thu riêng**. Không có khái niệm "một buổi live, nhiều nguồn".

| Việc | Trạng thái |
|---|---|
| Tạo 2 phiên (YouTube + Facebook) cho cùng một buổi phát | ✅ làm được |
| Chạy 2 bộ thu song song | ✅ làm được — cô lập phiên đã kiểm chứng: chạy **chồng nhau** (không chỉ nối tiếp) trên cùng một store, 0 rò rỉ, 0 va chạm mã bình luận |
| Gộp số liệu hai nền tảng thành một phiên | ❌ **không có** |
| Một lịch BẬT/TẮT dùng chung cho cả hai luồng | ❌ **không có** — mỗi phiên bốc lịch riêng |

**Và đây là vấn đề phương pháp, không phải vấn đề phần mềm:** nếu shop phát cùng nội
dung lên hai nền tảng, **hai lịch bốc thăm độc lập sẽ xung đột** — cùng một phút,
lịch YouTube nói BẬT còn lịch Facebook nói TẮT, mà người dẫn thì chỉ có một. Không
thể tuân thủ cả hai.

**Cách dùng đúng hôm nay:**

- Chọn **một** nền tảng làm nền tảng thí nghiệm (nơi bốc thăm và đo click).
- Các nền tảng còn lại chạy **chế độ quan sát**: thu bình luận, vẽ radar, làm báo cáo
  mô tả — và **không** suy diễn nhân quả từ chúng.
- Ghi rõ trong báo cáo: kết luận nhân quả áp cho **luồng nào**.

Làm đa nền tảng đúng cách đòi hỏi một tầng "buổi phát" trên tầng "phiên", với một
lịch dùng chung và nhiều nguồn tín hiệu đổ về. **Chưa có, chưa thiết kế.**

---

## 4. Vấn đề link đo click — trung tâm của toàn bộ phép đo

Biến kết quả chính, nguyên văn từ tiền đăng ký §4.1:

```
y_khối = 1000 × (số LƯỢT NHẤP HỢP LỆ trong khối, sau burn-in)
              / (viewer-giây exposure của khối, sau burn-in)
```

**Một click = một request đến `/r/{code}` của chính mình.** Không dùng số liệu click
của nền tảng. Không có định nghĩa thứ hai.

### 4.1 Trường hợp link đo DÙNG ĐƯỢC thật

| Tình huống bán hàng | Link đo hoạt động? | Ghi chú |
|---|---|---|
| Shop có **website riêng** / landing page | ✅ **Hoàn hảo** | Đây là ca lý tưởng: `/r/{code}` → trang sản phẩm của shop. Đúng bản chất một cú nhấp |
| Bán qua **inbox** (Messenger / Zalo) | ✅ **Dùng được và rất hợp Việt Nam** | `/r/{code}` → `m.me/...` hoặc `zalo.me/...`. Bấm là mở chat, và ta đếm được cú bấm |
| **Facebook Live** của Page mình, dán link vào bình luận ghim | ✅ Dùng được | Rủi ro kinh doanh: có thể bị hạ phân phối. Chưa đo |
| **YouTube Live**, link ở mô tả / bình luận ghim | ✅ Dùng được | Khách vốn đã phải rời nền tảng để mua |
| Bán trên sàn nhưng **phát trên YouTube/Facebook** | ⚠️ Dùng được nhưng đo thứ khác | `/r/{code}` → trang sản phẩm Shopee/Lazada trên web. Đếm được **ý định rời nền tảng để xem hàng**, không đếm được đơn |

### 4.2 Trường hợp link đo KHÔNG dùng được

| Tình huống | Vì sao | Còn đo được gì? |
|---|---|---|
| **TikTok Shop** | Giỏ hàng trong app. Ép dùng link ngoài = phá phễu mua hàng | **Hôm nay: không gì cả** (không có cả bình luận). Sau này: đơn hàng nhập tay, hoặc Partner API |
| **Shopee Live** | Giỏ trong app, web công khai là "màn hình đẩy sang app" | **Nhiều hơn hẳn:** API chính thức trả `gmv`, `orders`, `atc`, `ctr`, `ccu`, `likes`, `comments`… Đây là nền tảng **duy nhất** khảo sát được vừa cho bình luận vừa cho tín hiệu chuyển đổi |
| Live không bán gì cụ thể (giải trí, xây kênh) | Không có sản phẩm để ghim | Radar ý định + nhịp phiên. Chế độ quan sát |

### 4.3 Ba phương án đo thay thế — và đánh giá thẳng về tính hợp lệ thống kê

#### Phương án A — Đếm bình luận **chốt đơn** theo khối (dùng bộ phân loại ý định sẵn có)

*Biến kết quả: số bình luận nhãn `chot_don` / 1.000 viewer-giây, theo khối.*

**Điều tốt:** nhãn được gán bởi một bộ phân loại **mù với nhánh gán** — nó chỉ đọc văn
bản, không biết khối đang BẬT hay TẮT. Sai số phân loại vì thế là **không vi sai**
(non-differential): nó **kéo ước lượng về 0**, chứ không tạo ra hiệu ứng giả. Nói
cách khác: nếu phương án này cho kết quả có ý nghĩa, kết quả đó **đáng tin về dấu**;
nếu không có ý nghĩa, ta không kết luận được gì. Và vì so sánh nằm **trong cùng một
buổi live**, precision của buổi đó là hằng số cho cả hai nhánh — đúng lợi thế của
thiết kế switchback trong-phiên.

**Điều xấu, và nó rất xấu — đã đo thật trên 4 buổi live:**

| Buổi | Tỷ lệ nền ý định mua THẬT | Precision đo được |
|---|---:|---:|
| `1NMt8BChQrI` (tâm sự / trả đơn) | 0,0% | **1,3%** |
| `ZU_0QJzsR6w` (Achan Hải Phòng) | 0,5% | 11,0% |
| `gT0LDiBta2k` (khai trương) | 6,8% | 12,3% |
| `47oGShxf80A` ("comment mã để chốt đơn") | 48,0% | **67,9%** |

**Bốn buổi, bốn con số, chênh nhau hơn 50 lần.** Không tồn tại "độ chính xác của radar
ý định"; chỉ tồn tại độ chính xác **trên một buổi cụ thể**. Model gắn nhãn hành động
cho ~1/6 số dòng **bất kể** buổi đó thật sự có bao nhiêu ý định mua, và trên mẫu ngẫu
nhiên gộp nó **vẫn thua** một dòng `return "khac"` về accuracy (0,785 so với 0,905).

**Rủi ro chưa loại trừ được:** nếu việc ghim thẻ làm thay đổi **cách người ta viết**
(ví dụ ghim sản phẩm khiến khách gõ "mã 12" thay vì "cái này bao nhiêu"), thì tỷ lệ
phân loại sai **khác nhau giữa hai nhánh** → sai số trở thành **vi sai** → có thể sinh
thiên lệch thật. Không có cách loại trừ bằng dữ liệu hiện có. Phải nêu như một hạn chế.

**Phán quyết:** dùng được như **biến kết quả thứ cấp đã tiền đăng ký**. **Không** nâng
lên biến chính khi chưa đo lại precision trên chính kênh của chính KOL đó, bằng gán
nhãn tay mù. Công suất sẽ thấp hơn nhiều so với đo click, nên cần nhiều phiên hơn nhiều.

#### Phương án B — Nhịp bình luận thô (không qua model)

*Biến kết quả: bình luận/phút theo khối.*

**Hợp lệ về đo lường** (đếm thô, không có model nào để sai), gán khối chính xác vì
mỗi bình luận mang dấu thời gian nền tảng. Nhưng nó đo **mức độ ồn ào**, không đo ý
định mua. Đây là một biến kết quả **khác**, không phải proxy của click. Gọi đúng tên
là *"tương tác"*, và tuyệt đối không suy ra doanh thu từ nó.

**Phán quyết:** dùng được, rẻ, trung thực — miễn là không đặt tên sai.

#### Phương án C — Đối soát đơn hàng theo khối sau phiên

*Biến kết quả: số đơn (hoặc GMV) theo khối, lấy từ báo cáo đơn của nền tảng.*

Về nguyên tắc **đây là phương án đúng nhất**: đơn hàng là biến kết quả thật, thứ KOL
thật sự quan tâm. Nhưng có ba rào cản, và cả ba đều thật.

**Rào cản 1 — kỹ thuật, hôm nay:** **không có đường ghi đơn hàng vào hệ thống.** Bảng
`order_event` tồn tại trong CSDL, hàm `Store.add_order` tồn tại trong mã, nhưng
**không một dòng nào trong toàn repo gọi nó** — không endpoint, không CLI, không
adapter. Đây là việc phải làm trước khi bàn tiếp.

**Rào cản 2 — công suất thống kê, đã đo:** đơn hàng là biến **đếm hiếm**, phương sai
bị nhiễu đếm chi phối. Đã tính MDE bằng đúng bộ máy lực thống kê của dự án: ở quy mô
khán giả của giai đoạn thí nghiệm (**≤ 50 người xem đồng thời**), MDE tốt nhất trong
toàn lưới vẫn **~79%** — nghĩa là chỉ phát hiện được những hiệu ứng lớn phi thực tế.
**Đây là lý do đơn hàng bị giữ ở mục thứ cấp trong tiền đăng ký.**

> ⚠️ Với một KOL lớn (vài nghìn người xem đồng thời, hàng trăm đơn mỗi phiên) con số
> này sẽ **tốt hơn nhiều** — nhưng nhóm **chưa tính** cho quy mô đó. Phải chạy lại
> `python analysis/power/bang_mde_don_hang.py` với λ (số đơn/khối) thật của chính KOL
> đó trước khi hứa bất cứ điều gì. **Không bịa.**

**Rào cản 3 — phương pháp, và ít người nghĩ tới:** khách "chốt đơn" trong bình luận
rồi mới lên đơn sau vài phút đến vài giờ. Với khối 5 phút, **độ trễ đặt đơn sẽ trộn
lẫn hai nhánh** và làm nhòe hoàn toàn phép so sánh. Phải **đo độ trễ đó trước**; nếu
nó lớn thì khối phải dài hơn (15–20 phút), số khối giảm, và công suất lại giảm theo.
Đây là một đánh đổi có thật, không né được.

**Phán quyết:** phương án đúng nhất về bản chất, **chưa dùng được hôm nay**, và khi
dùng được thì phải kèm ba con số đo trước: λ thật, độ trễ đặt đơn, và MDE tính lại.

#### Phương án D (chỉ Shopee) — `get_session_metric`

API chính thức của Shopee trả `gmv`, `orders`, `atc`, `ccu` cho phiên của shop đã ủy
quyền. **Cảnh báo quan trọng:** đó là **số cộng dồn từ đầu phiên**, không phải sự kiện
có dấu thời gian. Muốn có số theo khối thì phải lấy **hiệu** giữa hai mốc đầu/cuối
khối — và **phải khai báo trong phương pháp** rằng biến kết quả là sai phân của một
bộ đếm cộng dồn. Thêm nữa, ranh giới khối có jitter ±30 giây nên lịch gọi API phải
bám đúng ranh giới thật, không phải ranh giới danh nghĩa. Đây là điểm chắc chắn bị
phản biện hỏi.

### 4.4 Tóm tắt mục 4 trong một bảng

| Kênh bán | Biến kết quả chính khả thi | Chất lượng |
|---|---|---|
| Website riêng / inbox | **Click qua `/r/{code}`** | ★★★ Đúng thiết kế |
| YouTube / Facebook + link ngoài | **Click qua `/r/{code}`** | ★★★ |
| Shopee Live | `orders`/`gmv` sai phân theo khối | ★★ Cần khai báo phương pháp |
| TikTok Shop | Đơn hàng nhập tay sau phiên | ★ Chưa có đường ghi; cần đo độ trễ đặt đơn |
| Bất kỳ, khi không có gì khác | Bình luận `chot_don` theo khối | ☆ Thứ cấp, precision dao động 1,3%–67,9% |

---

## 5. Checklist setup cho một KOL/shop dùng thật

### 5.1 LÀM MỘT LẦN (cài đặt ban đầu)

| # | Việc | Ai | Bao lâu | Bỏ qua thì hỏng gì |
|---|---|---|---:|---|
| 1 | **Dựng máy chủ có tên miền thật** (`docker compose up -d`, đặt `DOMAIN=` trong `.env`, trỏ DNS). Caddy tự xin HTTPS | Kỹ sư | ~1 ngày | **Hỏng toàn bộ phép đo.** Link `localhost/r/{code}` **không bấm được từ điện thoại 4G của người xem** → 0 click → không có biến kết quả |
| 2 | `YOUTUBE_API_KEY` (Google Cloud, miễn phí) | Kỹ sư | ~10 phút | Phải dùng đường yt-dlp — **trái Điều khoản YouTube**, trễ ~24 giây, và phải khai báo phương pháp nếu dữ liệu vào bài |
| 3 | **Facebook Page token** + đủ **hai** quyền | Kỹ sư + KOL | ~25 phút | Đọc được **0 bình luận** trên Facebook |
| 4 | Đặt `NEXT_PUBLIC_PUBLIC_API_BASE` = tên miền công khai, rồi **build lại web** (`docker compose build web`) | Kỹ sư | 10 phút | Link đo hiện ra vẫn trỏ `localhost` → người xem bấm không ra gì |
| 5 | Đặt `INGEST_TOKEN` (bảo vệ **cả 15** endpoint ghi) + chọn `PUBLIC_DEMO_WRITES` | Kỹ sư | 5 phút | Bất kỳ ai trên Internet bơm được bình luận giả, **kết thúc được phiên đang chạy**, bắn can thiệp, hoặc bắt máy chủ tải video bất kỳ |
| 6 | Đặt `RESULTS_FREEZE_UNTIL` = ngày đóng băng dữ liệu | Trưởng phân tích | 2 phút | Nhìn trộm kết quả giữa chừng → mất tính tiền đăng ký |
| 7 | Sao lưu CSDL ra **ngoài máy** (script `backup.sh` đang ghi vào `./backups` cục bộ) | Kỹ sư | 30 phút | Mất máy là mất sạch |
| 8 | **Chốt giao thức làm mù với KOL**: ai dẫn, ai vận hành, máy vận hành đặt ở đâu | Chủ dự án | 1 buổi họp | Người dẫn hào hứng hơn ở khối BẬT → đo tâm lý người dẫn, không đo hệ thống. Đây là lỗi **không sửa được sau khi đã chạy** |
| 9 | (Nếu bán Shopee) Đăng ký **Shopee Open Platform** + shop ủy quyền OAuth | Kỹ sư + KOL | vài ngày chờ duyệt | Bỏ lỡ nền tảng **duy nhất** cho cả bình luận lẫn đơn hàng qua API chính thức |

### 5.2 TRƯỚC MỖI PHIÊN

| Mốc | Việc | Ai | Bao lâu | Bỏ qua thì hỏng gì |
|---|---|---|---:|---|
| **T−24h** | Chốt danh mục sản phẩm, kiểm tồn kho, nhập vào hệ thống **kèm URL trang sản phẩm thật** | KOL | 20 phút | Không có URL → hệ thống **không tạo link đo** cho sản phẩm đó, và nó nói thẳng điều đó trên màn hình |
| **T−24h** | **Tạo link đo `/r/{code}` cho từng sản phẩm — BẮT BUỘC có `session_id`** | Kỹ sư | 10 phút | ⚠️ **Cái bẫy số 1.** Link thiếu `session_id` vẫn chuyển hướng bình thường nhưng **cú bấm biến mất khỏi thí nghiệm**. Đã kiểm chứng: 2 cú bấm → phiên chỉ ghi nhận 1 |
| **T−24h** | Mở thử từng link **từ 4G trên điện thoại** (không phải từ máy đang chạy hệ thống) | Kỹ sư | 5 phút | Phát hiện lỗi tên miền/HTTPS **sau khi lên sóng** là mất cả phiên |
| **T−2h** | Khởi động bộ thu, xác nhận **heartbeat**: `posted` bám sát `seen`, `failures=0`, `lỗi gần nhất: không có` | Kỹ sư | 15 phút | Token hết hạn / cạn quota phát hiện giữa phiên = mất dữ liệu không lấy lại được |
| **T−2h** | Bơm 3 bình luận thử có số điện thoại giả → phải ra `[SĐT]` | Kỹ sư | 5 phút | Bộ lọc PII hỏng mà không ai biết = sự cố dữ liệu cá nhân |
| **T−1h** | **Bốc lịch BẬT/TẮT và lưu. Ghi lại `seed` và `design_hash`** | Trưởng phân tích | 5 phút | Không có lịch thì API **chặn phát sóng** (409). Không ghi seed thì không tái lập được |
| **T−1h** | **Đọc cảnh báo thiết kế nếu có.** Phiên < 90 phút sẽ có cảnh báo tiếng Việt ngay tại đây | Trưởng phân tích | 2 phút | Phát hiện thiết kế không đủ mạnh **lúc phân tích** thay vì lúc còn sửa được |
| **T−30'** | Thiết bị, mạng dự phòng | KOL | 20 phút | Mất mạng giữa phiên = khối bị loại |
| **T−15'** | Mở `/host` trên máy người dẫn. Mở bàn điều khiển trên máy người vận hành, **đặt khuất tầm mắt người dẫn** | Người vận hành | 5 phút | Hỏng làm mù |
| **T−10'** | Xác nhận: phiên đúng thời lượng, đúng nền tảng; link đo đã sẵn trong clipboard/soạn sẵn bình luận | Người vận hành | 5 phút | Lúng túng phút đầu = mất khối đầu (vốn dài gấp đôi) |
| **T−5'** | Thông báo xử lý dữ liệu hiển thị trong phòng live | KOL | 1 phút | Vấn đề pháp lý/đạo đức |

### 5.3 TRONG PHIÊN

| Việc | Ai | Nhịp | Bỏ qua thì hỏng gì |
|---|---|---|---|
| Dẫn phiên, **chỉ nhìn màn hình `/host`** | KOL | liên tục | Nhìn bàn điều khiển = biết mình đang ở khối nào = hỏng làm mù |
| **Bấm thẻ gợi ý trong mỗi khối BẬT** | Người vận hành | **8 lần / phiên 90 phút** | Tuân thủ tụt → ước lượng ITT bị suy giảm. Không có bộ tự động nào làm thay (mục 6, việc 4) |
| Dán link đo `/r/{code}` vào bình luận ghim khi giới thiệu sản phẩm | Người vận hành | mỗi lần đổi sản phẩm | Không dán = không có click = không có biến kết quả |
| **Không đọc to trạng thái khối, không đếm ngược chuyển khối** | Người vận hành | liên tục | Hỏng làm mù |
| Khối TẮT: **làm y như thường lệ**, không bình luận gì về hệ thống | Cả hai | ~một nửa phiên | Nhánh đối chứng bị nhiễm = mất điểm so sánh |
| Can thiệp tay **chỉ với 3 lý do**: `hết hàng`, `sai giá`, `sự cố kỹ thuật` | Người can thiệp | khi cần | API **từ chối** lý do khác. Can thiệp bừa = hỏng tuân thủ |
| Theo dõi heartbeat của bộ thu | Kỹ sư | mỗi 60 giây | Bộ thu chết mà không biết = mất bình luận cả đoạn |
| Nếu bộ thu chết: **khởi động lại ngay**, rồi gửi lại phần đệm (`spool_replay`) | Kỹ sư | ngay lập tức | Gửi trùng **an toàn** (có khóa idempotency) — nên cứ chạy lại, đừng ngần ngại |

### 5.4 SAU PHIÊN

| Mốc | Việc | Ai | Bỏ qua thì hỏng gì |
|---|---|---|---|
| **T+15'** | Bấm "Kết thúc phiên" (nếu chưa) | Người vận hành | Phiên treo ở `live` → các khối chưa phát bị tính vào phân tích |
| **T+30'** | `livelift-qc --session-id <id> --recount-clicks` — mọi mục đỏ phải truy nguyên nhân, **không sửa số liệu** | Kỹ sư | Số hỏng đi vào kết quả cuối mà không ai biết |
| **T+30'** | Chép cả **ba** con số độ nhạy τ ∈ {5, 30, 60} giây vào nhật ký | Kỹ sư | Không chứng minh được kết luận bền với ngưỡng lọc bot |
| **T+1h** | Ghi nhật ký phiên theo mẫu, **kể cả mục "Sự cố làm mù"** | KOL / vận hành | Vi phạm làm mù bị giấu = kết quả không đáng tin, và hội đồng sẽ hỏi |
| **T+24h** | Xem báo cáo sau phiên; đối chiếu **ma trận tín hiệu** trước khi tin bất kỳ con số nào | Trưởng phân tích | Đọc một con số mà không biết nó đứng trên tín hiệu nào |

---

## 6. Khoảng cách đến "bật lên là chạy"

Đây là danh sách chính xác những gì còn thiếu để một KOL **không biết kỹ thuật** tự
dùng được. Ước lượng công sức là **ước lượng thô của kỹ sư, chưa đo** — ghi ra để xếp
ưu tiên, không phải để cam kết tiến độ.

| # | Thiếu gì | Hôm nay ra sao | Cần làm gì | Ước lượng |
|---|---|---|---|---:|
| **1** | **Đăng nhập + tài khoản + tách dữ liệu theo chủ** | **Không có gì.** Không có trang đăng nhập. Danh mục sản phẩm **dùng chung toàn hệ thống** — đã kiểm chứng: phiên 2 thấy nguyên sản phẩm của phiên 1. Bảo vệ duy nhất là `INGEST_TOKEN` (một token dùng chung cho **mọi** endpoint ghi, cộng ranh giới phiên-demo cho khách không token — `src/livelift/api/auth.py`); vẫn **không** có khái niệm chủ sở hữu | Mô hình người dùng/tổ chức; thêm `owner_id` vào sản phẩm/phiên/link đo + migration; lọc theo chủ ở **mọi** truy vấn; đăng nhập | **2–3 tuần-người**. Chặn cứng việc mở cho nhiều người dùng |
| **2** | **Kết nối nền tảng bằng vài cú bấm** | Phải dán token vào `.env` **rồi khởi động lại tiến trình**. Shopee còn khó hơn: token sống **4 giờ**, phiên dài phải làm mới giữa chừng | OAuth callback cho Facebook/Shopee; lưu token mã hóa theo tài khoản; tự làm mới; trang "Kết nối tài khoản" | **~2 tuần-người mỗi nền tảng** |
| **3** | **Bộ thu tự khởi động khi bấm "Lên sóng"** | Là **một lệnh terminal riêng**, cần **video id** của buổi live (người dùng phải tự tìm), một tiến trình cho mỗi phiên, không có giám sát trên giao diện | Ô dán **link buổi live** → tự trích id; trình quản lý tiến trình/hàng đợi; heartbeat và lỗi hiển thị trên màn hình vận hành | **1,5–2 tuần-người** |
| **4** | **Bộ thực thi tự động (chế độ "auto" thật)** | `mode='auto'` **chỉ là cái nhãn** — không có scheduler, không có worker nào đọc nó. Người vận hành bấm **8 lần/phiên 90 phút** | Worker bám lịch khối, gọi `execute` đầu mỗi khối BẬT, ghi `exposure_event`, có đường hủy an toàn | **~1 tuần-người** |
| **4b** | ⚠️ **Giới hạn KHÔNG phần mềm nào vượt được** | **LiveLift không ghim hộ trên nền tảng.** Nó nói *"ghim cái này bây giờ"*; việc bấm ghim trên app TikTok/Facebook/YouTube vẫn là **thao tác tay của con người**. Không có API nào cho phép điều khiển việc ghim sản phẩm trong live của bên thứ ba | Không làm gì được. **Phải nói thẳng với KOL ngay từ đầu** | — |
| **5** | **Chế độ "KOL solo"** | Giao thức làm mù cần **hai người**. KOL tự dẫn + tự bấm sẽ nhìn thấy bàn điều khiển → **biết mình đang ở khối nào** → hỏng làm mù | Phụ thuộc việc 4: máy tự quyết, KOL **chỉ** nhìn `/host` (màn hình đó đã được thiết kế đúng — chỉ 4 trường, không rò khối) | gộp vào việc 4 |
| **6** | **Đường ghi đơn hàng** | Bảng `order_event` + `Store.add_order` **tồn tại nhưng không ai gọi**. Năng lực "đối soát doanh thu" vĩnh viễn = THIẾU | Endpoint ghi đơn + nhập CSV từ báo cáo nền tảng + gán khối theo dấu thời gian + màn hình đối soát | **3–5 ngày-người** cho đường nhập CSV |
| **7** | **Triển khai trên mạng thay vì máy cá nhân** | `docker-compose` + Caddy **đã sẵn sàng** (`DOMAIN` → HTTPS tự động). Thiếu: VPS thật, DNS, sao lưu ngoài máy | Thuê VPS, trỏ DNS, chạy, kiểm link đo từ 4G | **~1 ngày** + chi phí VPS. **Rẻ nhất, và nó đang chặn toàn bộ việc đo click** |
| **8** | **Hướng dẫn trong sản phẩm** | `/chay-phien` đã làm được sản phẩm → phiên → lịch → lên sóng, **không cần terminal**. Thiếu: ô dán link live, hướng dẫn dán link đo vào đâu, nút "kiểm tra link của bạn từ mạng ngoài", cảnh báo nổi bật khi phiên < 90 phút | Bổ sung vào chính trang đó | **3–5 ngày-người** |
| **9** | **Gộp nhiều nền tảng trong một buổi phát** | Không có khái niệm "buổi phát" trên "phiên"; hai lịch bốc thăm sẽ xung đột | Tầng "buổi phát" + một lịch dùng chung + nhiều nguồn tín hiệu | **chưa thiết kế** — cần quyết định phương pháp trước khi ước lượng |

**Đường ngắn nhất để có một KOL thật dùng được, theo đúng thứ tự:**
**7 → 2 → 3 → 1 → 4 → 6.** Việc 7 (dựng trên mạng) rẻ nhất và đang chặn nhiều nhất;
việc 1 (tài khoản) là cái chặn *cuối cùng* trước khi mời được người ngoài nhóm.

---

## 7. Ba điều phải nói thẳng với bất kỳ KOL nào

1. **LiveLift lấy đi một nửa phiên của anh.** Trong nhánh TẮT — khoảng một nửa thời
   lượng — hệ thống **cố tình không giúp gì**. Đó không phải lỗi, đó là cái giá của
   việc biết được sự thật. Một công cụ hứa "tối ưu 100% thời gian" là công cụ không
   bao giờ chứng minh được nó có tác dụng. Nếu KOL không chấp nhận điều này, họ cần
   chế độ 1 hoặc 2, không phải chế độ 3.

2. **Bình luận không phải là chuyển đổi, và radar ý định không có một độ chính xác
   dùng được để phát biểu.** 1,3% · 11,0% · 12,3% · 67,9% trên bốn buổi thật. Nó tệ
   nhất **đúng ở chỗ cần nhất**: buổi chat đông nhưng thưa ý định mua. Đừng để KOL
   nghĩ con số "608 bình luận chốt đơn" là 608 đơn.

3. **Không nền tảng nào cho đọc buổi live của người lạ mà không xin phép.** Đó là
   *thiết kế*, không phải trở ngại kỹ thuật, và nó đúng. Mọi dịch vụ bán "API bình
   luận TikTok/Facebook" trôi nổi đều là scraping có rủi ro pháp lý. LiveLift chọn
   không lách — và đó là một luận điểm, không phải một lời xin lỗi.

---

## 8. Ba việc cần quyết ngay (dành cho chủ dự án)

| Việc | Công | Được gì |
|---|---:|---|
| **Xin `YOUTUBE_API_KEY`** | 10 phút | Biến toàn bộ đường YouTube từ "trái Điều khoản" thành hợp lệ. Rẻ nhất, chặn được câu phản biện nặng nhất |
| **Dò danh mục TikTok Shop Partner API** | 30 phút | Nếu có module live → nguồn dữ liệu giá trị nhất cả đề tài (nền tảng #1 Việt Nam, hợp Điều khoản). Nếu không → **đóng dứt điểm, hết bàn** |
| **Dựng LiveLift trên một VPS có tên miền** | ~1 ngày | Mở khóa việc đo click thật. Hôm nay link đo trỏ `localhost` là không ai bấm được |

---

*Tài liệu liên quan:*
[`nen-tang-ho-tro.md`](nen-tang-ho-tro.md) — bảng khả năng từng nền tảng, có bằng chứng ·
[`../ops/runbooks/quy-trinh-phien.md`](../ops/runbooks/quy-trinh-phien.md) — runbook vận hành chi tiết ·
[`../PREREGISTRATION.md`](../PREREGISTRATION.md) — định nghĩa biến kết quả và quy tắc phân tích ·
[`benchmarks/live-fire-da-nguon.md`](benchmarks/live-fire-da-nguon.md) — 19.126 bình luận thật, và giới hạn của radar ý định
