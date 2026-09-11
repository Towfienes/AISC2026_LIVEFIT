# Vị thế và lộ trình — LiveLift đang ở đâu so với khoa học và sản phẩm thương mại

**Ngày lập:** 11/09/2026 · **Gói:** VI-THE
**Phạm vi:** đối chiếu trung thực trạng thái repo với (a) văn liệu switchback + live
commerce gần nhất, (b) sản phẩm thương mại đang bán trên thị trường; rồi chốt vị thế,
khoảng cách lên product thật, và các cột mốc.
**Nguyên tắc:** mọi con số về LiveLift phải truy được về file trong repo; mọi con số về
bên ngoài phải có nguồn + ngày truy cập; cái gì không xác minh được thì ghi "chưa xác
minh". Không suy diễn số thay đối thủ.

---

## 1. TRẠNG THÁI THẬT — cái gì ĐÃ CHẠY, cái gì mới là MÃ

Đây là phần quan trọng nhất của tài liệu. Mọi phát biểu vị thế bên dưới chỉ có giá trị
nếu cột này trung thực.

### 1.1 Đã chạy thật, có bằng chứng tái lập được

| Hạng mục | Số đo | Nguồn trong repo |
|---|---|---|
| Buổi live THẬT nạp trọn qua chính API của hệ thống | **24 buổi** (16 buổi đợt 10/09 + 8 buổi đợt 11/09), **≈34.000 bình luận thật không trùng lặp**, 8+ ngành hàng | `docs/benchmarks/live-fire-da-nguon.md`, `docs/benchmarks/nhat-ky-test.md` |
| Server đang phục vụ xem trực tiếp (11/09) | **13 phiên · 17.535 bình luận** trên `127.0.0.1:8000` + web `:3000` | `nhat-ky-test.md` §"Trạng thái server" |
| Tái lập từng bit | Achan Hải Phòng chạy lại **3 lần, 3 tiến trình, cách nhau 2 ngày → trùng từng con số** (6.586 bl) | `live-fire-da-nguon.md` §3.1 |
| Cô lập phiên | nối tiếp **và** song song trong thread pool, đối chiếu file gốc: **0 rò rỉ, 0 va chạm `comment_id`** | `live-fire-da-nguon.md` §3.2–3.3 |
| Thông lượng | ~**900 bình luận/giây**, nút thắt là mạng | `live-fire-da-nguon.md` §3.4 |
| Hiệu chỉnh ước lượng viên (A/A 200 lặp) | bác bỏ **4,5%** (danh nghĩa 5%, nhị thức p=0,872), độ phủ KTC **95,5%** | gate `tests/test_sim_validation.py` |
| MDE gắn lực đo được | **20,1%** (công thức cũ sai 30,1%), biên studentized 1,2 đo bằng sweep | `docs/benchmarks/order-mde.md` |
| Ánh xạ knob → ICC (400 phiên) + lưới SBC | 4/4 ô xanh, **cổng có răng** (tiêm lỗi → đỏ) | `sim-icc-map.md`, `sim-validation-report.md` |
| Lọc PII tiếng Việt trên chat thật | bắt SĐT viết bằng chữ, không nhầm giá tiền 7 chữ số; recall ≥95%/loại ở gate | `live-fire-da-nguon.md` §7, `tests/test_pii_filter.py` |
| Một buổi **ĐANG PHÁT** | 104 bình luận + 7 tick người xem qua toàn tuyến, trễ p50 **24,1 s** — nhưng qua đường **yt-dlp trái ToS YouTube**, chỉ dùng dự phòng | `docs/research/2026-09-09-youtube-ytdlp-live.md` |
| Gán nhãn tay MÙ để tự chấm điểm mình | 393 dòng, 4 buổi | `live-fire-da-nguon.md` §4 |
| Kỷ luật kỹ thuật | **672 test** thu thập được hôm nay (`pytest --collect-only`, 11/09); 24 sự cố ghi sổ đủ root cause | `tests/`, `docs/incident-log.md` |

### 1.2 Đã đo và **tự bác bỏ** (phải nói mỗi lần trình bày)

- **Radar ý định KHÔNG có một độ chính xác nào dùng được để phát biểu.** Precision nhãn
  hành động trên 4 buổi thật (gán nhãn tay mù): **1,3% · 11,0% · 12,3% · 67,9%** — chênh
  hơn 50 lần, đi theo **tỷ lệ nền** ý định mua của buổi đó, không theo model. Accuracy gộp
  **0,785**, vẫn **thua baseline `return "khac"` (0,905)**. Con số 0,870 của bộ biên soạn
  **không chuyển giao**.
- **Radar tệ nhất đúng ở chỗ cần nhất**: buổi chat đông nhưng thưa ý định mua
  (`1NMt8BChQrI`, 606 nhãn hành động, ước ~2 nhãn đúng).
- **Không đọc được live đấu giá** (chat là chuỗi trả giá thuần số) — 30,9% nội dung giá
  trị nhất bị bỏ sót.
- **Không có dữ liệu người xem cho VOD** — vĩnh viễn, không phải lỗi cài đặt.

### 1.3 MỚI LÀ MÃ — chưa chạy với dữ liệu/điều kiện thật

| Hạng mục | Trạng thái thật |
|---|---|
| **Thí nghiệm switchback ngẫu nhiên trên một phiên live thật** | **CHƯA CHẠY LẦN NÀO.** Toàn bộ 24 buổi live-fire là **quan sát**: không gán ngẫu nhiên, không link đo, không sinh số nhân quả. Hệ thống tự dán nhãn như vậy trên UI và `/signals`. Mọi bằng chứng nhân quả hiện nay đến từ **mô phỏng**. |
| Ingest YouTube/Facebook API **chính thức** | Code + test sẵn sàng; **chưa chạy với credential thật** (`docs/TONG-KET-DU-AN.md` §II P1) |
| Link đo click `/r/{code}` | Có code + quy tắc hợp lệ GIVT-lite; **chưa đo trên khán giả thật** |
| Ghi đơn hàng | Bảng `order_event` có trong migration, **chưa có API ghi** → gói Performance chưa kiểm chứng được |
| Tiền đăng ký | `PREREGISTRATION.md` ghi rõ **"TRẠNG THÁI: BẢN MẪU — CHƯA KHÓA"**, dự kiến khóa tuần 6 (29/09–05/10) |
| Lưu trữ production | Mặc định đang chạy **in-memory store**; `PostgresStore` có và có contract test, nhưng **chưa vận hành thật dưới tải**. Tắt uvicorn là mất sạch 13 phiên đang nạp |
| Thu thập TikTok | WebSocket bị từ chối **HTTP 400 ở 10/10 lần → 0 bình luận** (09/09). Không dùng được |
| Holdback billing / gói Performance | Chỉ là thiết kế trong `chuong-trinh-nghien-cuu-vong-2.md` (F4), điều kiện kích hoạt chưa đạt |
| Đăng nhập / đa người dùng / đa tổ chức | **Không tồn tại.** Chỉ có một `INGEST_TOKEN` bearer cho endpoint ghi (`api/routes/events.py`); **mọi endpoint đọc là mở** |
| Thanh toán, hoá đơn, pháp nhân | Không tồn tại |

### 1.4 Lệch số trong tài liệu (phải hợp nhất trước khi nộp)

`README.md` gắn badge **249 test**; `docs/TONG-KET-DU-AN.md` ghi **611**; `pytest
--collect-only` hôm nay ra **672**. Ba con số ở ba nơi là đúng kiểu lỗi mà chính dự án
này đi bắt ở người khác. Hợp nhất là việc nửa giờ, phải làm trước hồ sơ vòng 1.

---

## 2. SO VỚI KHOA HỌC

### 2.1 Câu hỏi then chốt: đã có ai làm thí nghiệm ngẫu nhiên TRONG phiên livestream chưa?

**Kết quả tìm kiếm (11/09/2026, nhiều truy vấn tiếng Anh + tiếng Trung + tiếng Việt):
chưa tìm thấy công trình nào chạy thí nghiệm ngẫu nhiên theo KHỐI THỜI GIAN BÊN TRONG
một phiên livestream bán hàng.** Những gì tồn tại chia làm ba nhóm, không nhóm nào trùng
ô này:

1. **Switchback là kỹ thuật đã chín, nhưng ở miền khác** — gọi xe, giao đồ ăn, đấu giá
   quảng cáo, marketplace hai phía. Đơn vị thời gian là *giờ/ngày của cả nền tảng*,
   không phải *phút trong một phiên của một nhà bán*.
2. **Thí nghiệm ngẫu nhiên trong live commerce là có, nhưng do NỀN TẢNG chạy và
   randomize ở cấp NGƯỜI DÙNG** — điển hình là Wang et al., *Information Systems
   Research* 36(4) 2025 (trợ lý AI trên nền tảng bán hàng livestream: +3,00% doanh số,
   −12,55% tỷ lệ trả hàng).
3. **Nghiên cứu vận hành livestream ở cấp quyết định gần LiveLift nhất là QUAN SÁT** —
   Xie, Sharma & Mehra, *POM* 34(12) 2025 hỏi đúng câu LiveLift hỏi ("trình bày sản phẩm
   bao lâu thì bán tốt hơn?") nhưng trả lời bằng dữ liệu hồi cứu hai nền tảng lớn Trung
   Quốc, không bằng gán ngẫu nhiên.

Đây là **ô trống thật** — và cũng là lý do phải cẩn thận: ô trống có thể trống vì khó,
chứ không chỉ vì chưa ai nghĩ ra. Ba cái khó đã lộ ra trong chính dữ liệu của nhóm: phiên
Việt chat dày rất hiếm (chỉ 7/16 buổi đạt ≥100 bình luận), T ≈ 18–24 khối là cực nhỏ so
với giả định tiệm cận của văn liệu, và outcome đơn hàng nằm ngoài tầm với của bên không
sở hữu nền tảng.

### 2.2 Đối chiếu từng công trình

| Công trình | Họ làm gì | LiveLift khác/hơn/kém |
|---|---|---|
| **Bojinov, Simchi-Levi & Zhao (2023)**, *Mgmt Sci* 69(7):3759–3777 | Thiết kế switchback **tối ưu** theo bậc hiệu ứng lưu m; nền móng lý thuyết của cả dòng | **Dùng làm xương sống** (khối đều, nhân đôi khối đầu/cuối). **Khác**: LiveLift chạy trong *một phiên 90–120 phút*, T≈18–24 khối — vùng mẫu cực nhỏ mà kết quả tiệm cận không đỡ được, nên bắt buộc dùng randomization test exact + Fisher CI thay vì SE tiệm cận. **Kém**: paper có triển khai thật ở quy mô nền tảng; LiveLift chưa chạy một phiên ngẫu nhiên nào |
| **Liu & Zhong (2026)**, arXiv:2602.23257 *Randomization Tests in Switchback Experiments* | CRT dưới non-anticipation + chân trời carryover hữu hạn; chẩn đoán học cửa sổ carryover (m̂); xấp xỉ lực dưới distributed-lag + nhiễu AR(1) | **Là tài liệu đọc bắt buộc #1 của nhóm**. LiveLift đã đi xa hơn ở một điểm: propensity **ước bằng redraw qua chính hàm gán production**, không bằng công thức đóng (vì rerandomization + arm-balance + ràng buộc transition làm vùng chấp nhận hẹp dần). **Kém**: m̂ và V̂_up mới nằm trong kế hoạch làn 2–3, **chưa đo trên dữ liệu thật** |
| **Zeng, Adjaho, Bucarey, Qin, Zhang, Hoban, Johari & Wager (2026)**, arXiv:2604.02489 *Sequentially-Rerandomized Switchback* | Tái ngẫu nhiên hóa mỗi kỳ, cân bằng outcome/hiệp biến trễ; biến thể phân tầng theo lịch sử gán | LiveLift đã có rerandomization + ràng buộc transition ((1,1)≥3, (0,0)≥3). **Chủ động KHÔNG** áp rerandomization theo biến tiên lượng giữa mùa — đã ghi vào mục "KHÔNG làm" của chương trình vòng 2 vì đổi cơ chế gán giữa mùa là lớp rủi ro cao nhất repo. Đây là lựa chọn có lý do, không phải bỏ sót |
| **Ni, Kalfountzou & Bojinov (2025)**, HBS WP **26-012**, P&G | Switchback + rerandomization cho môi trường **đấu giá**, nơi người bán *không kiểm soát được việc randomize user* | **Cùng một logic tồn tại với LiveLift**: không randomize được người → randomize theo thời gian. **Khác địa bàn**: họ ở đấu giá quảng cáo của một tập đoàn; LiveLift ở phiên live của nhà bán vừa và nhỏ Việt Nam, nơi ngân sách và cỡ mẫu nhỏ hơn ba bậc |
| **arXiv:2606.03012** *Powerful Switchback Experiments — Or Not?* | Phân rã phương sai S_res/S_macro, phạt (1+cv²), ngưỡng cv* để chọn thống kê | LiveLift đã đưa vào spec P5: cài **cả hai** thống kê (khối đều vs Hájek theo exposure) và chọn **một lần** bằng cv* đo trên pilot, viết vào prereg. **Kém**: **cv* thật chưa đo** — vẫn là quyết định đang treo |
| **Wang, Huang, He, Liu, Guo, Sun & Chen (2025)**, *ISR* 36(4):2358–2374 | **Thí nghiệm ngẫu nhiên thật trên nền tảng bán hàng livestream**: trợ lý AI cho người xem → +3,00% doanh số, −12,55% trả hàng | **Gần nhất về tinh thần, khác hẳn về vị trí đứng.** Họ randomize **người dùng**, chạy **từ trong nền tảng**, có outcome **đơn hàng + trả hàng** thật. LiveLift randomize **khối thời gian**, chạy **từ phía nhà bán không có quyền nền tảng**. **LiveLift kém rõ ràng**: chưa có phiên ngẫu nhiên nào, chưa có outcome đơn. **LiveLift hơn ở chỗ**: cách của họ chỉ có nền tảng làm được; cách của LiveLift thì 50.000 nhà bán Việt Nam đều làm được |
| **Xie, Sharma & Mehra (2025)**, *POM* 34(12) | Thời lượng trình bày sản phẩm dài hơn → doanh thu sản phẩm cao hơn; dữ liệu hai nền tảng livestream lớn nhất Trung Quốc | **Đây là đối chứng thuyết phục nhất cho luận điểm của LiveLift**: câu hỏi vận hành y hệt (nên ghim/giữ sản phẩm bao lâu), nhưng trả lời bằng **hồi cứu**. Một tạp chí hạng A vẫn phải dùng quan sát cho câu hỏi này — chính là chỗ LiveLift định cắm cờ. Chưa cắm được ngày nào chưa có phiên ngẫu nhiên |
| **KuaiLive (SIGIR'26)**, arXiv:2508.05633 | Bộ dữ liệu tương tác thời gian thực đầu tiên cho recsys livestream: 23.772 user × 452.621 streamer, 21 ngày, Kuaishou | LiveLift **dùng để hiệu chỉnh hình dạng mô phỏng** (`mean_stay_min` 6→10, `comment_rate` 0,25→0,02) và **cấm** map funnel/mức tuyệt đối. Nó là dữ liệu **quan sát cho recsys**, không có can thiệp ngẫu nhiên cấp phiên — không cạnh tranh, là nguyên liệu |
| **LiveForesighter (Kuaishou, 2025)**, arXiv:2502.06557 | Sinh "thông tin tương lai" (chuỗi thống kê hành vi, danh mục sản phẩm kế tiếp) để cải thiện đề xuất livestream | **Đối lập triết lý, cùng miền.** Họ tối ưu dự báo; LiveLift đo nhân quả và **chặn ở cấp kiến trúc** việc số dự báo mang khoảng tin cậy. Họ có hạ tầng và dữ liệu mà LiveLift không bao giờ có; LiveLift có thứ họ không cần: bằng chứng rằng một hành động vận hành *tạo ra* giá trị |
| **Feng, Rong, Tian, Wang & Yao (2025)**, *POM* — *When Persuasion Is Too Persuasive* | Thuyết phục quá mức trong livestream làm tăng **tỷ lệ trả hàng** — phân tích thực nghiệm quan sát | Cảnh báo trực tiếp cho LiveLift: tối ưu click/đơn mà không có guardrail trả hàng là tối ưu một nửa. Guardrail non-inferiority (NIM) mới là **spec** trong làn 3, **chưa cài** — và LiveLift hiện **không có tín hiệu trả hàng nào** |

---

## 3. SO VỚI SẢN PHẨM THƯƠNG MẠI

Chia làm ba lớp. Không lớp nào chạy thí nghiệm ngẫu nhiên trong phiên live (theo khảo
sát 11/09/2026).

### 3.1 Công cụ của chính nền tảng

| Sản phẩm | Họ làm gì | LiveLift khác |
|---|---|---|
| **TikTok LIVE Manager / LIVE Board** | Bàn điều khiển desktop cho TikTok Shop LIVE: lên lịch, gắn sản phẩm, giveaway, kiểm duyệt chat, OBS; **LIVE Dashboard** có GMV, hoa hồng, số sản phẩm bán, lượt xem/nhấp sản phẩm, người xem đồng thời, số liệu thời gian thực + sau phiên. Miễn phí cho người bán | **Họ có thứ LiveLift thiếu nhất: outcome đơn hàng thật, gắn trực tiếp vào giỏ.** Họ **không có** gán ngẫu nhiên, không có propensity, không có khoảng tin cậy, không có làm mù host. Câu họ trả lời là "phiên vừa rồi bán được bao nhiêu"; câu LiveLift trả lời là "**bao nhiêu trong số đó là do hành động của bạn**". Không tìm thấy tính năng A/B test nào trong LIVE Manager 2026 |

### 3.2 Công cụ phân tích dữ liệu live commerce (bên thứ ba)

| Sản phẩm | Họ làm gì | Giá (nếu tìm được) | LiveLift khác |
|---|---|---|---|
| **Kalodata** | Phân tích TikTok Shop: shop, creator, sản phẩm, phiên live — hồi cứu | **Starter 38,30 USD/tháng**, **Professional 83,20 USD/tháng**, Enterprise chưa công bố giá | Phân tích **hồi cứu, cấp thị trường**: "ai đang bán chạy". Không can thiệp, không nhân quả. LiveLift không cạnh tranh ô này và không nên giả vờ cạnh tranh |
| **EchoTik** | Cùng lớp với Kalodata; tự định vị bằng độ chính xác dữ liệu | chưa xác minh được bảng giá | như trên |
| **FastMoss** | Cùng lớp, thường được so sánh ba bên với Kalodata/EchoTik | chưa xác minh | như trên |
| **Chanmama (蝉妈妈)** | Nền tảng phân tích Douyin lâu đời nhất (từ 09/2019), mạnh nhất ở **giám sát phiên live**; mô hình thuê bao Cá nhân / Chuyên nghiệp / Flagship | không công bố giá công khai ở nguồn tiếng Việt/Anh; chưa xác minh | Đối thủ *khái niệm* mạnh nhất trong nhóm này vì họ theo dõi phiên live theo thời gian thực. Nhưng vẫn là **quan sát**: không có nhánh đối chứng, không có xác suất gán |
| **Feigua (飞瓜)** | Phân tích KOL + đa nền tảng, mạnh về cơ sở dữ liệu người ảnh hưởng | chưa xác minh | như trên |

### 3.3 Phần mềm vận hành livestream tại Việt Nam

| Sản phẩm | Họ làm gì | LiveLift khác |
|---|---|---|
| **Pancake POS** (và lớp phần mềm quét đơn livestream VN: **UPOS**, **TPos**, …) | Tự động **chốt đơn theo cú pháp bình luận**, trả lời tự động, gom hàng nghìn đơn từ nhiều phiên, **ẩn số điện thoại/thông tin khách trong bình luận**, đẩy đơn sang GHTK/GHN/Viettel Post. Đã có thị phần thật trong cộng đồng bán hàng online VN | **KHÔNG phải đối thủ — là mảnh ghép còn thiếu.** Họ nắm đúng thứ LiveLift đang trống: **sự kiện đơn hàng ở cấp bình luận**, thời gian thực, trong phiên. Chiến lược đúng là **tích hợp, không cạnh tranh**: một webhook đơn hàng từ Pancake/UPOS vào `order_event` biến biến kết quả chính của LiveLift từ *click* thành *đơn*. Lưu ý trùng chức năng: họ cũng ẩn SĐT trong bình luận — LiveLift phải nói rõ khác biệt (họ ẩn để **chống cướp đơn**, LiveLift khử nhận dạng để **tuân thủ Luật 91/2025/QH15** trước khi ghi đĩa). *Bảng giá cụ thể 2026 chưa xác minh được từ nguồn công khai.* |

### 3.4 Nền tảng thí nghiệm chuyên nghiệp

Đây là nhóm **có switchback thật**, và là nhóm phải đối chiếu nghiêm túc nhất.

| Sản phẩm | Họ làm gì | Giá | LiveLift khác |
|---|---|---|---|
| **Statsig** | Feature flag + thí nghiệm + analytics; **có Switchback Tests trong sản phẩm** kèm tài liệu chính thức, thêm sequential testing và stratified sampling. (OpenAI mua lại 2025; Amplitude tiếp nhận thương hiệu/nền tảng/hợp đồng khách hàng qua hợp tác chiến lược 05/2026) | "dưới 5.000 USD/tháng" cho một thiết lập SaaS điển hình theo tài liệu marketing của chính họ | **Công cụ mạnh hơn LiveLift ở mọi mặt kỹ thuật chung — nhưng không dùng được cho bài toán này.** Statsig đòi **SDK nhúng trong sản phẩm của bạn** và **metric trong data warehouse của bạn**. Nhà bán livestream Việt **không sở hữu** TikTok/Facebook, không nhúng được SDK, không có warehouse. Statsig cũng không có: khái niệm "phiên live", ma trận tín hiệu, làm mù host, lọc PII tiếng Việt, phân loại ý định chat Việt, link đo tự phục vụ |
| **Eppo** | Thí nghiệm warehouse-native, **có UI switchback riêng**. (Datadog mua lại 2025 → Datadog Experiments 2026) | **15.050 – 87.250 USD/năm**, phần lớn khách trả **≈42.000 USD/năm** | Như trên, cộng thêm: mức giá này nằm ngoài mọi khả năng chi trả của nhà bán vừa Việt Nam (≈1,1 tỷ đồng/năm ở mức trung bình) |
| **GrowthBook** | Thí nghiệm mã nguồn mở, warehouse-native | ≈**1.000 USD/tháng** ở quy mô 50 người dùng; có bản tự host | Rẻ nhất nhóm, vẫn cùng giả định "bạn sở hữu sản phẩm và có warehouse" |
| **Optimizely** | A/B testing doanh nghiệp cho web/app | enterprise, không công bố | Không chạm live commerce |

**Kết luận nhóm này — và đây là câu phải nói khi bị hỏi "sao không dùng Statsig?":**
mọi nền tảng thí nghiệm hiện có đều giả định bạn **sở hữu nền tảng nơi thí nghiệm diễn
ra**. Bài toán của nhà bán livestream Việt Nam là bài toán của người **đi thuê sân**:
không SDK, không warehouse, không quyền chia luồng người xem. Thứ duy nhất họ kiểm soát
được là **hành động của chính mình theo thời gian** — và đó chính xác là đơn vị ngẫu
nhiên hóa mà switchback dùng. LiveLift không phải "Statsig rẻ hơn"; LiveLift là
**switchback cho bên không sở hữu nền tảng**.

---

## 4. TUYÊN BỐ VỊ THẾ

> **LiveLift là hạ tầng đo lường nhân quả cho phiên livestream bán hàng — dành cho người
> đi thuê sân.**
>
> Mọi nền tảng thí nghiệm hiện có (Statsig, Eppo, GrowthBook) đòi bạn sở hữu sản phẩm để
> nhúng SDK; mọi công cụ live commerce hiện có (TikTok LIVE Manager, Chanmama, Kalodata,
> Pancake) chỉ đếm lại chuyện đã xảy ra. Nhà bán Việt Nam không sở hữu TikTok hay
> Facebook — thứ duy nhất họ kiểm soát là **hành động của chính mình theo thời gian**.
> LiveLift biến đúng thứ đó thành đơn vị ngẫu nhiên hóa: **switchback theo khối thời gian
> bên trong một phiên live**, xác suất gán ghi trước khi phát sóng, màn hình host bị làm
> mù ở cấp kiểu dữ liệu, và một ước lượng viên **tự chứng minh hiệu chỉnh** (A/A 200 lặp:
> bác bỏ 4,5%, độ phủ 95,5%).
>
> Khác biệt cốt lõi không phải dashboard đẹp hơn — mà là **thứ duy nhất trong nhóm dám tự
> bác bỏ số của chính mình bằng số**: chính LiveLift đã công bố rằng bộ phân loại ý định
> của mình tụt từ F1 0,870 xuống 0,271 trên chat bán hàng thật, và rằng nó thua cả
> baseline ngây thơ. Một công cụ đo lường mà không tự đo được chính nó thì không đáng tin.
>
> **Cho ai:** nhà bán vừa và tổ vận hành 1–3 người trong ~2,5 triệu phiên live mỗi tháng
> ở Việt Nam — những người đang ra quyết định ghim gì, lúc nào, giảm giá bao sâu, bằng
> kinh nghiệm truyền miệng chứ chưa từng bằng một thí nghiệm.

**Ba câu dự phòng khi bị dồn:**

- *"Chỉ là A/B test thôi mà?"* — A/B test chia người. Ở livestream không chia được người
  (ai cũng thấy cùng một màn hình), nên phải chia **thời gian**. Đó là switchback, và các
  ràng buộc của nó (hiệu ứng lưu, T nhỏ, mẫu số nội sinh) là toàn bộ phần khó.
- *"Đã có ai làm chưa?"* — Switchback đã chín ở gọi xe/đấu giá; thí nghiệm live commerce
  đã có nhưng do **nền tảng** chạy và chia theo **người dùng**; nghiên cứu gần nhất về
  đúng câu hỏi vận hành này (POM 2025) vẫn phải dùng dữ liệu **quan sát**. Chỗ trống là
  **trong phiên, từ phía nhà bán**.
- *"Số của các bạn đúng không?"* — Đây là đội duy nhất mang đến một danh sách những thứ
  **của mình** đã sai và đã được đo là sai.

---

## 5. KHOẢNG CÁCH LÊN PRODUCT THẬT

Từ "prototype thi đấu" sang "sản phẩm người ngoài trả tiền dùng". Ước lượng effort theo
**tuần-người**, giả định đội 4 người như hiện tại.

| # | Khoảng trống | Vì sao nó CHẶN | Effort |
|---|---|---|---|
| 1 | **Chưa từng chạy một phiên switchback ngẫu nhiên thật nào.** 24/24 buổi live-fire là quan sát | Toàn bộ mệnh đề giá trị đứng trên mô phỏng. Không có nó thì không có sản phẩm, không có bài thi, không có gì cả | 2–3 tuần-người (không phải code — là vận hành: hàng, quảng cáo, người chạy phiên) |
| 2 | **Không có outcome đơn hàng.** `order_event` chưa có API ghi; click `/r/{code}` chưa đo trên khán giả thật | Khách trả tiền hỏi "tăng bao nhiêu **đơn**", không hỏi "tăng bao nhiêu click". Gói Performance không kiểm chứng được | 1 tuần (API ghi + QC đối soát) + 1–2 tuần (webhook Pancake/UPOS) |
| 3 | **Không có đăng nhập / đa người dùng / đa tổ chức.** Chỉ một `INGEST_TOKEN` cho endpoint ghi; **mọi endpoint đọc mở hoàn toàn** | Ai biết URL là đọc được mọi phiên, kể cả bàn điều phối. Không thể cho 2 khách dùng chung một bản. **Nghiêm trọng nhất: làm mù host hiện chỉ được bảo vệ ở cấp kiểu dữ liệu — không có tầng quyền nào chặn host mở thẳng `/desk`** | 3–4 tuần-người (org/user/role, sở hữu phiên, blinding thành ràng buộc quyền, audit log) |
| 4 | **Lưu trữ production chưa vận hành.** Mặc định in-memory; tắt tiến trình là mất sạch | Mất điện hoặc restart **giữa phiên live** = mất toàn bộ lịch gán và dữ liệu phiên → thí nghiệm hỏng không cứu được | 2–3 tuần (bật Postgres mặc định, tải thật, test khôi phục, queue cho job phân tích vốn đang chạy in-process) |
| 5 | **Radar ý định không dùng được để phát biểu** (precision 1,3%–67,9%) | Đây là tính năng **nhìn thấy rõ nhất** trên UI. Bán nó bây giờ là bán số sai — vi phạm chính la bàn của dự án | 2–3 tuần (gán nhãn lại 60 dòng `khac` + huấn luyện 11 lớp + hiển thị prevalence phiên) — **kèm cam kết hạ cấp radar khỏi trung tâm UI nếu không vượt baseline** |
| 6 | **Không có mô hình triển khai cho khách.** Một `docker-compose` đơn tenant + Caddy một tên miền. Chưa quyết khách tự cài hay mình host | Khách tự cài: AGPL-3.0 buộc mở mã phần sửa đổi → phải chốt dual-licensing, và SME Việt không có người vận hành Docker. Mình host: phát sinh toàn bộ nghĩa vụ ở mục 8–11 | 1 tuần quyết định + 3–4 tuần dựng (khuyến nghị: **mình host**, SME không tự cài được) |
| 7 | **Không có onboarding.** Tài liệu hiện tại viết cho kỹ sư và giám khảo | Khách phải tự tạo phiên, tự gắn link đo, tự hiểu "chưa kết luận được" nghĩa là gì. Không ai làm được điều đó một mình trong 10 phút trước giờ live | 2–3 tuần (luồng 30 phút có người kèm + 5 video ngắn + bảng kiểm trước phiên) |
| 8 | **Không có giá / thanh toán / pháp nhân.** 990k–3,9M mới là dự kiến trên giấy | Không hoá đơn VAT = doanh nghiệp không chi được. Không pháp nhân = không ký được hợp đồng xử lý dữ liệu ở mục 9 | 2 tuần giấy tờ + 1–2 tuần tích hợp cổng thanh toán |
| 9 | **Pháp lý dữ liệu khách hàng của khách.** Luật **91/2025/QH15** hiệu lực **01/01/2026** + NĐ 356/2025. Xử lý bình luận người xem = xử lý dữ liệu cá nhân **bên thứ ba**. Miễn trừ DPIA 5 năm cho DN nhỏ/khởi nghiệp **KHÔNG áp dụng** nếu **kinh doanh dịch vụ xử lý dữ liệu cá nhân** — LiveLift đúng hạng đó | Đây là rủi ro **tồn tại**, không phải rủi ro chất lượng. Bán dịch vụ trước khi có hồ sơ là bán một khoản phạt | 3–4 tuần (hồ sơ DPIA, hợp đồng xử lý dữ liệu với từng nhà bán, cơ chế đồng ý, cập nhật 6 tháng/lần) + chi phí tư vấn luật |
| 10 | **Không có SLA / trực khi phiên đang phát mà hệ thống lỗi.** Không health check ngoài, không trang trạng thái, **không có chế độ rút lui an toàn** | Phiên live không hoãn được. API chết phút 40 của phiên 90 phút, không ai trực, không có đường lùi → khách mất buổi bán, không chỉ mất dữ liệu. Đây là thứ giết niềm tin nhanh nhất | 2–3 tuần (chế độ an toàn: tự chuyển mọi khối về TẮT + ghi sổ; health check; trang trạng thái; lịch trực giờ live 19–23h) |
| 11 | **Backup/khôi phục chưa diễn tập.** Có service backup + verify trong compose, nhưng **chưa có bài khôi phục có tính giờ**; RPO/RTO chưa khai báo | "Có backup" mà chưa restore lần nào thì bằng không. Với dữ liệu thí nghiệm (lịch gán append-only) mất là **không tái tạo được** | 1 tuần (diễn tập restore có tính giờ, công bố RPO/RTO, đưa vào CI hàng tháng) |
| 12 | **Chưa có ai chịu trách nhiệm khi số sai.** Không quy trình đính chính, không báo cáo bất biến có phiên bản, không điều khoản giới hạn trách nhiệm, không người ký duyệt | Sản phẩm này **bán một con số**. Ngày con số đó sai — và sẽ có ngày đó, repo đã ghi 24 sự cố — câu hỏi đầu tiên của khách là "ai chịu?". Không có câu trả lời thì mọi thứ ở trên vô nghĩa | 2 tuần (báo cáo có hash + phiên bản bất biến, quy trình đính chính công khai kiểu sổ sự cố hiện có, điều khoản dịch vụ, một người ký duyệt mỗi báo cáo) |

**Tổng thô: ≈26–35 tuần-người** cho 12 mục, chưa tính mục 1 phụ thuộc vận hành ngoài tầm
kiểm soát. Với đội 4 người làm song song mùa thi, đây là **2 quý sau chung kết** — con số
này nên nói thẳng trong phần tầm nhìn thay vì hứa "sau thi là bán được".

---

## 6. LỘ TRÌNH

### Đến chung kết 11/2026 — mục tiêu là **khoa học**, không phải doanh thu

| Cột mốc | Nội dung | Thời điểm |
|---|---|---|
| **M0 · Hồ sơ vòng 1** | Hợp nhất một bộ số duy nhất (test 249/611/672 → một con số; ngân sách; số phiên), xác minh hạn nộp với BTC, nộp | **12–14/09/2026** |
| **M1 · Pilot hiệu chỉnh tuần 3** | 4–6 phiên thật đo đồng thời: t_mix, m̂ (Liu–Zhong), cv*, CV trong-phiên, ICC → **chốt độ dài khối 5' hay 10'** theo quy tắc viết TRƯỚC khi thấy số. Song song: API ghi đơn hàng + link `/r/{code}` chạy trên khán giả thật lần đầu | **15–21/09/2026** |
| **M2 · Dứt điểm radar ý định** | Gán nhãn lại 60 dòng `khac`, huấn luyện 11 lớp, hiển thị prevalence ý định của phiên cạnh radar. **Nếu không vượt baseline `return "khac"` → hạ cấp radar khỏi trung tâm UI và ghi vào slide giới hạn** | **22–28/09/2026** |
| **M3 · KHÓA tiền đăng ký** | Điền số đo từ M1, khóa `PREREGISTRATION.md` bằng commit, bật `RESULTS_FREEZE_UNTIL` | **29/09–05/10/2026** |
| **M4 · Chuỗi khẳng định** | ≥18 phiên thật (Live Lab + phòng đối tác 200–500 khán giả), SRM đợt 1 mỗi phiên, QC 6 mục sau phiên, không chạm ước lượng viên | **06/10–02/11/2026** |
| **M5 · Chung kết** | Một con số có KTC 95% đúng tệp prereg đã khóa + Sim Validation Report một trang + phòng điều khiển thống kê (replay, đổi tham số tại chỗ) + **slide giới hạn tự khai**. Kết quả không có ý nghĩa thống kê vẫn là kết quả hợp lệ | **11/2026** |

### Sau chung kết — mục tiêu là **sản phẩm**

| Cột mốc | Nội dung | Thời điểm |
|---|---|---|
| **M6 · v1 dùng nội bộ, cứng** | Postgres thành mặc định, queue cho job phân tích, **chế độ rút lui an toàn khi API chết giữa live**, health check + trang trạng thái, **diễn tập khôi phục có tính giờ** (công bố RPO/RTO). Không thêm tính năng nào | **11–12/2026** |
| **M7 · Pilot đối tác (miễn phí, 2–3 nhà bán)** | Đăng nhập + đa tổ chức + phân quyền (blinding thành ràng buộc quyền); pháp nhân + hợp đồng xử lý dữ liệu + hồ sơ DPIA theo Luật 91/2025/QH15; onboarding 30 phút có người kèm; SLA giờ live viết thành văn bản; webhook đơn hàng từ Pancake/UPOS | **Q1/2027** |
| **M8 · Beta có khách trả tiền** | Gói Free / Pro / Agency có hoá đơn VAT + cổng thanh toán VN; **báo cáo bất biến có phiên bản + hash**; quy trình đính chính công khai; một người ký duyệt mỗi báo cáo; điều khoản dịch vụ | **Q2/2027** |
| **M9 · Gói Performance — định giá bằng chính khoa học** | Thu % trên giá trị tăng thêm, đo bằng **holdback ngẫu nhiên 10% khối**; sổ cái ký số + `billing_audit.py` ngoài `src/` để nhà bán **tự recount**. Điều kiện kích hoạt: ≥5 phiên có event table đầy đủ + đối tác ký | **H2/2027** |
| **M10 · Moat công khai** | Công bố **bộ dữ liệu ý định chat livestream tiếng Việt** đầu tiên (DATASHEET, split theo phiên, re-audit PII, DOI Zenodo, CC BY-NC-SA) + báo cáo tri thức vận hành ngành từ dữ liệu thí nghiệm đa cửa hàng (ẩn danh, đồng ý rõ ràng) | **H2/2027 trở đi** |

---

## 7. NGUỒN

| # | Nguồn | Truy cập |
|---|---|---|
| 1 | Bojinov, Simchi-Levi & Zhao, *Design and Analysis of Switchback Experiments*, **Management Science** 69(7):3759–3777 (2023) — https://dl.acm.org/doi/10.1287/mnsc.2022.4583 · arXiv:2009.00148 | 11/09/2026 |
| 2 | Liu & Zhong, *Randomization Tests in Switchback Experiments*, arXiv:2602.23257 (2026) — https://arxiv.org/abs/2602.23257 | 11/09/2026 |
| 3 | Zeng, Adjaho, Bucarey, Qin, Zhang, Hoban, Johari & Wager, *Sequentially-Rerandomized Switchback Experiments*, arXiv:2604.02489 (02/04/2026) — https://arxiv.org/abs/2604.02489 | 11/09/2026 |
| 4 | Ni, Kalfountzou & Bojinov, *Reliable Switchback Experiments with Rerandomization for Auction Environments at Procter & Gamble*, HBS Working Paper **26-012** (09/2025) — https://www.hbs.edu/ris/Publication%20Files/26-012_e60b131f-aa68-4422-97e8-a478d6ed4baa.pdf | 11/09/2026 |
| 5 | *Powerful Switchback Experiments — Or Not?*, arXiv:2606.03012 — https://arxiv.org/html/2606.03012v1 | 11/09/2026 |
| 6 | Wang, Huang, He, Liu, Guo, Sun & Chen, *AI Assistant in Online Shopping: A Randomized Field Experiment on a Livestream Selling Platform*, **Information Systems Research** 36(4):2358–2374 (2025) — https://pubsonline.informs.org/doi/10.1287/isre.2023.0103 (trang chính 403 với công cụ tự động; thông tin lấy từ bản ghi Experts@Minnesota và IDEAS/RePEc) | 11/09/2026 |
| 7 | Xie, Sharma & Mehra, *Designing E-commerce Livestreams: How Product Presentation Duration Affects Sales?*, **POM** 34(12) (13/01/2025) — https://journals.sagepub.com/doi/10.1177/10591478251314455 | 11/09/2026 |
| 8 | Feng, Rong, Tian, Wang & Yao, *When Persuasion Is Too Persuasive: Product Returns in Livestream e-Commerce*, **POM** (2025) — https://journals.sagepub.com/doi/10.1177/10591478231224949 | 11/09/2026 |
| 9 | *KuaiLive: A Real-time Interactive Dataset for Live Streaming Recommendation*, **SIGIR '26** (Melbourne, 20–24/07/2026), arXiv:2508.05633 — https://arxiv.org/abs/2508.05633 · https://doi.org/10.1145/3805712.3808587 | 11/09/2026 |
| 10 | Lu et al., *LiveForesighter: Generating Future Information for Live-Streaming Recommendations at Kuaishou*, arXiv:2502.06557 (02/2025) — https://arxiv.org/abs/2502.06557 | 11/09/2026 |
| 11 | Statsig — *Switchback Tests* (tài liệu sản phẩm) https://docs.statsig.com/experiments/types/switchback-tests · so sánh giá https://www.statsig.com/comparison/statsig-experimentation-platform | 11/09/2026 |
| 12 | Eppo — *Switchback experiments* https://docs.geteppo.com/experiment-analysis/switchbacks/ · giá & thương vụ Datadog/Amplitude: https://www.artisangrowthstrategies.com/blog/growthbook-vs-statsig-vs-eppo-2026 | 11/09/2026 |
| 13 | Kalodata bảng giá (Starter 38,30 USD/th · Professional 83,20 USD/th) — https://winninghunter.com/insights/kalodata-review/ · so sánh EchoTik/Kalodata/FastMoss https://echotik.live/guides/echotik-vs-kalodata-vs-fastmoss | 11/09/2026 |
| 14 | TikTok Seller University — *LIVE Manager* & *LIVE Manager Analytics* https://seller-us.tiktok.com/university/essay?knowledge_id=1195537245292331 · https://seller-us.tiktok.com/university/essay?knowledge_id=7633608400013099 | 11/09/2026 |
| 15 | Pancake POS — chốt đơn livestream theo cú pháp bình luận, ẩn thông tin khách: https://tanhungha.com.vn/pancake-pos-la-gi-n2250.html · lớp phần mềm quét đơn livestream VN: https://giaohangnang.com/blogs/ban-hang/cac-phan-mem-chot-don-livestream · Luật BVDLCN 91/2025/QH15 hiệu lực 01/01/2026 + miễn trừ DPIA: https://vneconomy.vn/nhung-diem-moi-trong-luat-bao-ve-du-lieu-ca-nhan-tu-112026.htm · https://sunteco.vn/luat-91-2025-qh15-va-nghi-dinh-356-2025-doanh-nghiep-can-biet-gi/ · quy mô thị trường live VN (≈2,5 triệu phiên/tháng, >50.000 nhà bán; FB 31,9% · Shopee 30,9% · TikTok 17,2%): https://vneconomy.vn/bung-no-xu-huong-tieu-dung-livestream.htm | 11/09/2026 |

**Ghi chú xác minh:** Chanmama và Feigua **không công bố bảng giá công khai** ở nguồn
tiếng Anh/Việt tra được — chỉ xác nhận được mô hình thuê bao ba bậc của Chanmama. Bảng
giá Pancake/UPOS/TPos 2026 **chưa xác minh được**. Không tìm thấy tính năng A/B test hay
thí nghiệm ngẫu nhiên nào trong TikTok LIVE Manager 2026. Mệnh đề "chưa có công trình nào
làm thí nghiệm ngẫu nhiên theo khối thời gian trong một phiên livestream bán hàng" là
**kết luận có giới hạn của khảo sát ngày 11/09/2026**, không phải chứng minh phủ định.
