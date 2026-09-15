<!-- NGUỒN NỘI DUNG HỒ SƠ DỰ ÁN BẢNG C — Cuộc thi Sáng tạo trẻ Quốc gia về AI 2026 -->
<!-- Sửa ở đây rồi chạy: .venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/dung_ho_so.py -->
<!-- Giới hạn CỨNG 20 trang. Mọi con số phải khớp docs/competition/FACT-SHEET.md -->
<!-- Dòng bắt đầu bằng <!-- là chú thích, không ra bản nộp -->

# 1. Bài toán hoặc vấn đề thực tiễn cần giải quyết

**Tên sản phẩm: LiveLift — nền tảng đo lường nhân quả cho phiên livestream bán hàng.**

Việt Nam có khoảng 2,5 triệu phiên livestream bán hàng mỗi tháng với hơn 50.000 nhà bán. Mỗi phiên là hàng chục quyết định: ghim sản phẩm nào, ghim lúc nào, giữ bao lâu, tung mã giảm giá ở phút thứ mấy. Gần như toàn bộ số quyết định đó hôm nay ra bằng kinh nghiệm truyền miệng.

Lý do không phải vì nhà bán lười nhìn số. Lý do là **số liệu họ có không trả lời được câu họ cần hỏi**. TikTok LIVE Manager cho GMV, hoa hồng, lượt xem sản phẩm, người xem đồng thời — miễn phí, chi tiết theo phút. Tất cả trả lời "phiên vừa rồi bán được bao nhiêu". Không công cụ nào trả lời "**bao nhiêu trong số đó là do hành động của bạn**".

Một tình huống điển hình: phút 30 người trợ live ghim sản phẩm B; phút 35 doanh thu nhích lên. Ít nhất ba lời giải thích cùng khớp về thời điểm — vì vừa ghim B, vì thuật toán nền tảng vừa đẩy thêm người vào phòng, hoặc vì người dẫn vừa kể xong một câu chuyện hay. Nhìn số liệu sau phiên thì cả ba đều đúng như nhau. Muốn tách được nguyên nhân thật cần một thứ mà quan sát không bao giờ có: **một phiên bản của chính buổi live đó, trong đó bạn không ghim**.

## 1.1 Vì sao A/B test thông thường không giải được

A/B test chia người dùng thành hai nửa. Trong livestream thì không chia được: cả phòng nhìn **cùng một màn hình**. Thứ duy nhất chia được là **thời gian** — đó chính là thiết kế **switchback**: cắt phiên 90 phút thành 16 khối 5 phút, mỗi khối bốc thăm bật hoặc tắt can thiệp, lịch bốc thăm khóa lại trước khi lên sóng, rồi so kết quả hai nhóm khối. Ví von: muốn biết cái quạt có làm mát phòng không mà chỉ có một quạt và một phòng, ta bật 5 phút — tắt 5 phút — bốc thăm thứ tự, rồi so nhiệt độ hai bên.

## 1.2 Vì sao bài toán này cấp thiết và ai đang bị bỏ lại

Switchback không mới — Uber, DoorDash, Lyft đều dùng. Nhưng **năng lực chạy thí nghiệm hôm nay là đặc quyền của bên sở hữu nền tảng**: Statsig, Eppo, GrowthBook đều giả định bạn sở hữu nơi thí nghiệm diễn ra để nhúng SDK và chia luồng người dùng. Giá là rào chắn thứ hai — Eppo báo giá 15.050–87.250 USD/năm, phần lớn khách trả khoảng 42.000 USD/năm, tức khoảng 1,1 tỷ đồng (tỷ giá 26.200 đ/USD ngày 11/09/2026).

Nhà bán livestream Việt Nam **không sở hữu TikTok hay Facebook**, và không có 1,1 tỷ đồng một năm. Thứ duy nhất họ kiểm soát là **hành động của chính mình theo thời gian** — LiveLift biến đúng thứ đó thành đơn vị bốc thăm, để **hạ chi phí của một năng lực khoa học xuống mức một tổ ba người dùng được**. Sai một quyết định vận hành thì nhân với 2,5 triệu phiên mỗi tháng.

**Nghị quyết số 57-NQ/TW ngày 22/12/2024 của Bộ Chính trị** xác định đột phá phát triển khoa học, công nghệ, đổi mới sáng tạo và chuyển đổi số quốc gia là nhiệm vụ chiến lược. Thương mại qua livestream đang là một trong những mũi tăng trưởng nhanh nhất của kinh tế số Việt Nam. Nhưng một ngành tăng trưởng bằng kinh nghiệm truyền miệng thì **không tăng được năng suất** — không đo được nhân quả thì không tối ưu được gì, chỉ lặp lại may rủi ở quy mô lớn hơn.

LiveLift xây đúng lớp hạ tầng còn thiếu đó — lớp đo lường — và **mở mã nguồn theo giấy phép AGPL-3.0** để nó là hạ tầng dùng chung, không phải công cụ độc quyền của một công ty. Nhóm chọn làm điều này ở phía **hộ kinh doanh nhỏ**, nhóm thường bị bỏ lại sau cùng trong mọi làn sóng công nghệ.

## 1.3 Bài toán có gốc học thuật, không phải nhóm tự nghĩ ra

Xie, Sharma và Mehra (*Production and Operations Management* 34(12), 2025) nghiên cứu đúng câu hỏi vận hành này — trình bày một sản phẩm bao lâu thì bán tốt hơn — và tìm ra một **đánh đổi**: trình bày một sản phẩm lâu hơn thì doanh thu của sản phẩm đó cao hơn, nhưng thời lượng trình bày trung bình tăng thì doanh thu cả phiên lại giảm. Một đánh đổi như vậy không có đáp án chung — mỗi nhà bán phải tự đo trên phòng live của mình. Nhưng dữ liệu của họ là **hồi cứu** từ hai nền tảng Trung Quốc, không gán ngẫu nhiên. Wang và cộng sự (*Information Systems Research* 36(4), 2025) có thí nghiệm ngẫu nhiên thật, đo được doanh số tăng 3,00% và tỷ lệ trả hàng giảm 12,55% — nhưng họ bốc thăm theo người dùng và chạy **từ bên trong nền tảng**.

Khoảng trống: **chưa có công bố nào làm thí nghiệm ngẫu nhiên bên trong một phiên live, từ phía người đi thuê sân.** Đó là chỗ LiveLift đứng.

## 1.4 Vì sao bài toán này đáng làm trong thời đại AI

Trong thời đại AI, cái nguy hiểm không phải là thiếu số liệu — mà là **có số liệu sai mà vẫn tin**. Khoảng trống đó đang được lấp bằng một nền kinh tế "bí kíp livestream" mua đi bán lại, mà phần lớn là sự trùng hợp được đặt tên.

Xây một sản phẩm đo lường thì dễ; xây một sản phẩm **chịu được việc người khác kiểm chứng** mới khó. Vì vậy dự án này tự chứng minh trước, rồi mới nói về dữ liệu thật — và để chứng minh nhóm nói thật, chính hệ thống này đã **tự bác bỏ một con số đẹp của chính nhóm**: bộ phân loại ý định đạt macro-F1 0,870 trên bộ câu mẫu do AI soạn nhưng chỉ còn **0,211** trên chat thật, thua cả cách đoán bừa. Nhóm đã đo, đã ghi vào sổ sự cố công khai, và không giấu. Toàn bộ hồ sơ này viết theo nguyên tắc đó.

# 2. Mục tiêu, phạm vi và đối tượng ứng dụng của sản phẩm

## 2.1 Mục tiêu

**Mục tiêu tổng quát:** xây hạ tầng đo lường nhân quả cho phiên livestream bán hàng dành cho bên **không sở hữu nền tảng** — mỗi quyết định trong phiên thành một thí nghiệm có xác suất gán ghi trước khi lên sóng, kết quả trả về kèm khoảng tin cậy, và bộ ước lượng phải **tự chứng minh được là nó đúng** trước khi nói về dữ liệu thật.

Sáu mục tiêu cụ thể và trạng thái trung thực tại ngày nộp hồ sơ:

| Mục tiêu | Chỉ số nghiệm thu | Trạng thái |
|---|---|---|
| MT1. Bộ ước lượng đạt mức ý nghĩa danh nghĩa | A/A 200 lần lặp: bác bỏ 3,50% (7/200) so với danh nghĩa 5%, p nhị thức 0,4168; phủ KTC 95% đo được 96,50% | **Đạt** |
| MT2. MDE đo được bằng mô phỏng, không suy từ công thức | MDE 20,1% (sweep 4 mức tác động × 60 lặp); công thức giải tích cho 30,1% và công thức đó sai | **Một phần** — đo ở điều kiện 45–62 người xem đồng thời |
| MT3. Chạy ≥18 phiên thí nghiệm thật có gán ngẫu nhiên | **0 phiên** tính đến 14/09/2026 | **Chưa đạt** — khoảng cách lớn nhất của dự án |
| MT4. Hạ tầng nạp dữ liệu thật chạy đúng, tái lập được | 19.126 bình luận · 16 buổi live · 7 ngành hàng; chạy lại sau 2 ngày trùng từng con số | **Đạt** |
| MT5. Quyền riêng tư và liêm chính cưỡng chế bằng máy | Cổng tự động đòi recall ≥95% cho số điện thoại, email, địa chỉ và ≥70% cho tên người; phiên chưa có lịch gán kèm `design_hash` bị API chặn HTTP 409 | **Một phần** — mẫu thử của cổng không có handle có dấu nên bỏ lọt; đã sửa 15/09 (mục 3.2) |
| MT6. Tự bác bỏ số của chính mình | Phân loại ý định macro-F1 0,870 trên bộ câu mẫu do AI soạn nhưng **0,211 trên chat thật** — công bố cả hai, rồi nâng lên 0,565 (mục 8.3) | **Đạt** |

MT3 là mục tiêu chưa đạt và nhóm nêu nó ở ngay trang đầu thay vì giấu xuống mục hạn chế. Lý do trình bày ở mục 11.

## 2.2 Phạm vi

**Trong phạm vi:** phiên livestream bán hàng tiếng Việt trên Facebook và YouTube; can thiệp thuộc quyền của nhà bán (ghim sản phẩm, nhắc mã giảm giá, đổi kịch bản thoại); biến kết quả đo qua link rút gọn có gắn tham số đo của chính nhà bán.

**Ngoài phạm vi, có chủ ý:** không can thiệp vào thuật toán phân phối của nền tảng (không làm được và không được phép); không dự đoán doanh thu (dự báo không có khoảng tin cậy nhân quả là thứ nhóm cố ý từ chối làm); không phục vụ phiên đấu giá (chat toàn chữ số, hệ thống mù hoàn toàn — đã đo và ghi nhận).

## 2.3 Đối tượng ứng dụng

| Nhóm | Mô tả | Vì sao khớp | Điều kiện bắt buộc |
|---|---|---|---|
| Nhà bán vừa | Tổ vận hành 1–3 người, bán qua website riêng hoặc inbox Messenger/Zalo | Khách vốn đã phải rời nền tảng để chốt đơn, nên link đo ghi đúng một cú nhấp thật | Có tên miền thật; tạo link đo trước phiên |
| KOL có người trợ live | Một người dẫn, một người trợ live | Đủ người để giữ giao thức làm mù người dẫn | Bắt buộc hai người; phiên từ 90 phút |
| Agency nhiều phòng live | Nhiều phòng, so sánh chéo | Nhiều phòng = nhiều cụm, lực thống kê tốt hơn | Chưa phục vụ được hôm nay |

Nhóm khớp nhất là **nhà bán vừa**. Ngoài thương mại, phương pháp và phần lõi kỹ thuật chuyển giao được sang mọi bối cảnh "một kênh phát, nhiều người xem, muốn biết cách nói nào hiệu quả hơn": truyền thông chiến dịch cộng đồng, phổ biến pháp luật, tư vấn tuyển sinh trực tuyến.

# 3. Dữ liệu sử dụng, nguồn dữ liệu và tính hợp lệ của dữ liệu

## 3.1 Các loại dữ liệu

| Loại dữ liệu | Nguồn | Cách thu thập | Quy mô | Cơ sở được phép dùng |
|---|---|---|---|---|
| Bình luận livestream tiếng Việt | **Chat replay của các buổi phát trực tiếp công khai đã kết thúc (VOD) trên YouTube** | Tải bằng **yt-dlp** (mã nguồn mở), nạp qua `POST /replays/youtube` | 19.126 bình luận · 16 buổi · 7 ngành hàng | Nội dung công khai, dùng **phi thương mại** cho đánh giá; đã ẩn danh; **không phát hành lại**. Hạn chế pháp lý nêu ở 3.3 |
| Câu mẫu ý định mua (do AI soạn) | Claude (Anthropic) | AI soạn ngày 01/09/2026 theo bộ nhãn nhóm thiết kế; nhóm rà soát | 320 câu, 5-fold CV | Dữ liệu tổng hợp, không chứa dữ liệu cá nhân; kê khai là sản phẩm AI |
| Nhãn tham chiếu trên chat thật | Bình luận thật đã qua bộ lọc PII | **Tác tử AI (Claude) gán ngày 09/09/2026**; chưa có nhãn người độc lập | 393 bình luận, 3 buổi (tập kiểm tra giữ riêng) | Kê khai là nhãn do AI gán; gán lại bằng người là việc đang làm |
| Sự kiện nhấp link đo | Hệ thống của chính nhóm | Endpoint `GET /r/{code}` tự vận hành | Theo phiên | Dữ liệu do hệ thống sinh ra |
| Dữ liệu mô phỏng | Bộ mô phỏng của nhóm | Sinh bằng `livelift.sim` | Hàng trăm nghìn khối | Hoàn toàn tổng hợp |
| KuaiLive (hiệu chỉnh mô phỏng) | Bộ dữ liệu công bố kèm bài SIGIR 2026 | Dùng để hiệu chỉnh tham số mô phỏng | 1,16 triệu phòng live | Bộ dữ liệu nghiên cứu công khai |

Nhóm **chưa thu thập được dữ liệu Facebook nào**: đường nạp Facebook Graph API đã viết xong và kiểm thử nhưng chưa có Page đối tác cấp token, nên không có con số nào trong hồ sơ này đến từ Facebook.

## 3.2 Bảo vệ dữ liệu cá nhân

Bình luận livestream **công khai vẫn chứa dữ liệu cá nhân** — người xem bình luận kèm số điện thoại, địa chỉ, tên thật để đặt hàng. Nhóm coi đây là rủi ro pháp lý hạng nhất, xử lý theo **Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15** (hiệu lực 01/01/2026) và **Nghị định 356/2025/NĐ-CP** (thay thế Nghị định 13/2023/NĐ-CP) bằng ba lớp cưỡng chế bằng máy:

1. **Khử nhận dạng ngay tại cổng nạp**, trước khi ghi xuống đĩa — không có đường nào ghi dữ liệu chưa lọc. Bộ lọc nhận diện số điện thoại (nhiều kiểu phân tách), email, địa chỉ, tên người, số tài khoản ngân hàng, tài khoản mạng xã hội; chuẩn hóa NFKC và xử lý ký tự keycap để chống né bằng emoji chữ số.
2. **Cổng chất lượng tự động**: recall từng loại PII phải đạt ≥95%, không đạt thì mã không vào được nhánh chính.
3. **Không lưu định danh người bình luận**: chỉ giữ mã băm theo phiên để chống trùng lặp.

**Một lỗ hổng nhóm tự phát hiện khi kiểm toán hồ sơ này:** biểu thức nhận diện tài khoản mạng xã hội chỉ khớp ký tự ASCII, nên **bỏ lọt tên tài khoản YouTube có dấu tiếng Việt hoặc gạch nối**. Mở dữ liệu gán nhãn lưu cục bộ ra đếm còn 57 lượt nhắc tên tài khoản trong nội dung bình luận; các tệp này không nằm trong kho mã công khai. Nguyên nhân gốc: cổng kiểm thử **có** đo loại `social`, nhưng **mọi mẫu thử đều là handle ASCII**, nên cổng xanh trong khi dạng handle thật đi qua — cổng chỉ bảo vệ được đúng những gì mẫu thử của nó chứa. Nhóm đã sửa biểu thức (15/09/2026) và thêm mẫu thử theo đúng hình dạng handle thật; việc lọc lại dữ liệu đã lưu và đo lại mô hình đang được thực hiện. Sự cố ghi trong sổ sự cố của dự án.

Nhóm nêu lỗi này thay vì im lặng, vì đó chính là bằng chứng cho cơ chế mà nhóm đang trình bày: cổng tự động chỉ bảo vệ được thứ nó có đo, và một dự án trung thực phải công bố cả chỗ nó đo thiếu.

## 3.3 Tính hợp lệ của nguồn dữ liệu — nêu rõ hạn chế

**YouTube Data API v3 không cung cấp chat replay của buổi phát đã kết thúc** (endpoint `liveChatMessages` chỉ phục vụ buổi đang phát). Vì vậy dữ liệu đánh giá của nhóm được tải bằng `yt-dlp`. Nhóm nêu rõ hai điều:

- **Cách này không đi qua API chính thức**, do đó không phù hợp với điều khoản dịch vụ của YouTube về truy cập tự động. Nhóm phát hiện điều này trong kiểm toán nội bộ và ghi nhận công khai thay vì bỏ qua.
- **Xử lý:** (a) dữ liệu VOD chỉ dùng **offline, phi thương mại, để đánh giá mô hình**, đã ẩn danh, không phát hành lại và không nằm trong kho mã công khai; (b) **đường chạy của sản phẩm thật chỉ dùng API chính thức** — YouTube Data API v3 cho buổi đang phát và Facebook Graph API cho Page có token; (c) hướng đi đúng về lâu dài là dữ liệu từ chính phiên live của nhóm và của nhà bán đối tác **có sự đồng ý**, và đó là ưu tiên số một sau vòng này (mục 12).

Đây là một hạn chế thật của dự án. Nhóm trình bày nó ở mục "tính hợp lệ của dữ liệu" chứ không giấu xuống phụ lục, vì Điều 5 Thể lệ coi việc che giấu nguồn dữ liệu và API là hành vi bị nghiêm cấm, và vì một hồ sơ khoa học phải chịu được việc người khác mở kho mã ra kiểm.

# 4. Quy trình tiền xử lý, làm sạch, chuẩn hóa hoặc tổ chức dữ liệu

```
Bình luận thô  →  Khử PII  →  Chuẩn hóa  →  Khử trùng  →  Gắn khối thời gian  →  Kho
   (API)         (bắt buộc)    (NFKC,        (platform,     (block_id theo lịch     (Postgres)
                               teencode,      ext_id)        gán đã khóa)
                               emoji)
```

**Bước 1 — Khử nhận dạng.** Chạy trước mọi bước khác, kể cả trước khi ghi log. Đây là quyết định kiến trúc: nếu khử PII đặt sau khâu lưu trữ thì dữ liệu thô có PII vẫn tồn tại trên đĩa dù chỉ vài giây.

**Bước 2 — Chuẩn hóa văn bản tiếng Việt mạng xã hội.** Chuẩn hóa Unicode NFKC (gộp các cách gõ dấu khác nhau về một dạng); ánh xạ teencode phổ biến; giữ emoji thay vì xóa, vì emoji mang tín hiệu ý định thật (🛒, 🔥, ❤️); giữ nguyên câu không dấu thay vì cố thêm dấu, vì thêm dấu sai làm hỏng nghĩa nhiều hơn là giúp.

**Bước 3 — Khử trùng lặp tất định.** Khóa duy nhất `(platform, ext_id)`: cùng một bình luận nạp lại bao nhiêu lần cũng chỉ vào kho một lần. Nhờ khóa này, chạy lại toàn bộ một buổi live sau hai ngày cho **trùng từng con số** — đây là điều kiện để kết quả kiểm chứng lại được.

**Bước 4 — Gắn khối thời gian.** Mỗi bình luận và mỗi lượt nhấp được gán vào khối 5 phút theo **lịch bốc thăm đã khóa trước khi lên sóng**. Không có bước này thì mọi phân tích nhân quả phía sau vô nghĩa.

**Bước 5 — Tổ chức để phân tích.** Đơn vị phân tích là **khối**, cụm là **phiên**; mọi sai số chuẩn đều gộp theo cụm phiên. Hai bảng riêng `assignment` (gán) và `exposure_event` (phơi nhiễm thực tế) cho phép đối chiếu "định làm gì" với "thực tế đã làm gì" — đây là nền cho ước lượng LATE ở mục 5.

**Xử lý dữ liệu sai lệch.** Lượt nhấp không hợp lệ (bot, trùng lặp, quá nhanh) được **đánh cờ chứ không xóa**, theo thông lệ đo lường IAB: xóa âm thầm là một dạng can thiệp vào dữ liệu mà người đọc kết quả không nhìn thấy.

# 5. Thuật toán, mô hình, phương pháp hoặc công cụ trí tuệ nhân tạo được sử dụng

Hệ thống có **ba lõi kỹ thuật**, mỗi lõi giải một bài toán khác nhau.

## 5.1 Lõi A — Thiết kế thí nghiệm và suy luận nhân quả

| Thành phần | Phương pháp | Vai trò |
|---|---|---|
| Thiết kế | Switchback hai tầng, khối ~5 phút, khối đầu/cuối nhân đôi (Bojinov và cs., 2023) | Biến thời gian thành đơn vị bốc thăm |
| Gán ngẫu nhiên | Bernoulli(0,5) + tái ngẫu nhiên hóa ràng buộc ≥2 khối/nhánh/pha; jitter ±30 giây | Cân bằng nhánh mà vẫn giữ tính ngẫu nhiên |
| Xử lý hiệu ứng lưu | Burn-in khi **phân tích** b ∈ {0..3} phút (Hu–Wager), **không** washout khi thiết kế | Bỏ ảnh hưởng còn sót của khối trước mà không phí thời lượng phát sóng |
| Ước lượng chính | Randomization inference studentized + khoảng tin cậy Fisher | Không cần giả định phân phối; hợp cỡ mẫu nhỏ |
| Ước lượng phụ | Horvitz–Thompson; OLS hiệu ứng cố định theo phiên + hiệu chỉnh Lin; Wald LATE | Kiểm tra chéo, và ước lượng tác động trên nhóm thực sự phơi nhiễm |
| Giảm phương sai | CUPED đa biến tất định | Tăng lực thống kê mà không đổi kỳ vọng |

Điểm cốt lõi của randomization inference ở đây: khi tính phân phối giả định vô hiệu, hệ thống **bốc thăm lại bằng đúng hàm gán đang chạy trên production**, không phải bằng một hàm mô phỏng viết riêng cho khâu phân tích. Nếu hàm gán có lỗi, lỗi đó xuất hiện ở cả hai phía và kiểm định vẫn hợp lệ.

## 5.2 Lõi B — Xử lý ngôn ngữ tự nhiên tiếng Việt thời gian thực

| Thành phần | Phương pháp | Vai trò |
|---|---|---|
| Lọc PII | Luật + từ điển địa danh + chuẩn hóa NFKC/keycap | Khử nhận dạng trước khi lưu; cổng recall ≥95% (điện thoại/email/địa chỉ), ≥70% (tên người) |
| Phân loại ý định | **11 lớp**; TF-IDF n-gram ký tự + hồi quy logistic, huấn luyện trên câu mẫu do AI soạn + nhãn LLM trên chat thật | Ước lượng tín hiệu ý định mua theo khối |
| Khung đánh giá | Leave-one-session-out theo buổi live + KTC bootstrap + 3 baseline bắt buộc | Chống rò rỉ theo phiên — cái bẫy lớn nhất của bài toán này |
| Kiểm soát đầu ra | Tín hiệu ý định **không** đi vào phần phân tích nhân quả. Lớp chặn tín hiệu theo tỷ lệ nền của từng buổi **chưa có trong mã** | Thà không dùng còn hơn dùng sai |

Nhóm **đã thử và bỏ** cơ chế từ chối trả lời theo ngưỡng tin cậy: khi chọn ngưỡng một cách trung thực (không nhìn tập kiểm tra) nó làm macro-F1 giảm 0,073, vì ngưỡng hiệu chuẩn ở buổi live này không chuyển giao sang buổi khác. Chi tiết ở mục 9.4.

## 5.3 Lõi C — Ba cơ chế liêm chính cưỡng chế bằng kiến trúc

Đây là phần nhóm coi là đóng góp riêng, và nó là **mã nguồn chứ không phải cam kết bằng lời**:

1. **Khóa tiền đăng ký.** Kế hoạch phân tích (biến kết quả chính, burn-in, bộ ước lượng) được ghi vào `PREREGISTRATION.md` và băm thành `design_hash`. Phiên không có lịch gán kèm `design_hash` thì API **chặn phát sóng bằng HTTP 409**.
2. **Khóa kết quả theo thời gian.** Cờ `RESULTS_FREEZE_UNTIL` chạy theo nguyên tắc *fail-closed*: chưa tới mốc mở khóa thì ước lượng, giá trị p và khoảng tin cậy **không trả về**, kể cả cho chính nhóm phát triển. Mục đích: chống nhìn lén kết quả rồi dừng phiên đúng lúc số đang đẹp.
3. **Làm mù người dẫn.** Màn hình `/host` không hiển thị thông tin khối hay nhánh gán. Nếu người dẫn biết mình đang ở khối "bật", họ sẽ hào hứng hơn, và phép đo trở thành phép đo tâm lý người dẫn.

## 5.4 Công cụ AI dùng trong quá trình phát triển

Nhóm sử dụng công cụ lập trình có hỗ trợ của AI (Claude Code) trong suốt quá trình phát triển, và **kê khai đầy đủ** theo Điều 5 Thể lệ. Phân định phần tự xây dựng / phần AI hỗ trợ / phần kế thừa nguồn mở, cùng quy trình kiểm chứng đầu ra, trình bày trong **Bản kê khai** nộp kèm hồ sơ; lịch sử câu lệnh đầy đủ đặt tại liên kết ở mục 13.

# 6. Quy trình huấn luyện, tinh chỉnh, tích hợp hoặc khai thác mô hình

## 6.1 Nguyên tắc chống rò rỉ dữ liệu

Tập kiểm tra được tách theo **buổi live**, không tách theo dòng. Nếu cùng một buổi live nằm cả ở tập huấn luyện lẫn tập kiểm tra, mô hình học được văn phong và mặt hàng của buổi đó và điểm số sẽ đẹp giả tạo. Đây là cái bẫy lớn nhất của bài toán này và nhóm đã dựng cổng kiểm thử để chặn.

## 6.2 Quy trình

1. **Dựng khung đánh giá TRƯỚC khi sửa mô hình.** Đây là quyết định quan trọng nhất của cả quy trình: cải tiến trước rồi mới đo thì không cách nào biết cải tiến là thật hay chỉ là chọn được con số đẹp. Khung gồm 3 baseline bắt buộc (đoán lớp đa số · từ khóa · mô hình đang chạy), chia leave-one-session-out, và KTC bootstrap 2.000 lần.
2. **Xây lại bộ nhãn.** Mở rộng 6 → **11 lớp** sau khi đo trên chat thật cho thấy hơn 40% bình luận là **xã giao và bảng giá của chính shop** — hai lớp không có trong bộ nhãn cũ, nên mô hình buộc phải ép chúng vào các lớp mua hàng. Định nghĩa lớp và hướng dẫn gán nhãn gom về một chỗ (`nlp/labels.py`).
3. **Gán nhãn — và một điều nhóm phải nói rõ.** Cả ba nguồn nhãn hiện có **đều do AI tạo**: 393 dòng chat thật dùng làm **tập kiểm tra** do một tác tử Claude gán ngày 09/09; 320 câu mẫu do Claude soạn ngày 01/09; 1.800 nhãn huấn luyện do LLM gán. Nhóm chỉ thiết kế bộ nhãn và rà soát. Vì vậy mọi con số ở mục 8.3 và 9 đo **mức đồng thuận với nhãn tham chiếu do AI gán**, chưa phải độ chính xác so với con người. Gán lại tập kiểm tra bằng hai thành viên độc lập trên bảng xáo trộn, rồi đo độ đồng thuận κ, là việc đang làm.
4. **Huấn luyện và đo lại.** Đặc trưng TF-IDF n-gram ký tự (chịu được teencode, thiếu dấu, viết dính) + hồi quy logistic. Mỗi thay đổi đo lại bằng cùng một lệnh; kết quả ghi tự động ra `docs/benchmarks/intent-eval/results.json` và `results.md`.
5. **Ablation.** Tắt lần lượt từng thành phần để biết cái nào thật sự đóng góp — kể cả khi câu trả lời là "không đóng góp gì" (mục 9.4).

Toàn bộ chạy lại được bằng **một lệnh**: `python -m livelift.nlp.eval_intent`.

# 7. Chỉ số, phương pháp hoặc tiêu chí đánh giá kết quả

Hệ thống được chấm ở **ba tầng độc lập**, vì một con số duy nhất không nói được sản phẩm có đúng không.

## 7.1 Tầng 1 — Bộ ước lượng có đúng không (kiểm chứng bằng mô phỏng)

| Chỉ số | Ý nghĩa | Kết quả đo |
|---|---|---|
| Tỷ lệ bác bỏ A/A | Chạy thí nghiệm giả không có tác động; phải bác bỏ đúng 5% | **3,50%** (7/200; p nhị thức 0,4168) |
| Độ phủ khoảng tin cậy 95% | KTC phải chứa giá trị thật 95% số lần | **96,50%** (193/200) |
| Thu hồi tác động biết trước | Cấy tác động đã biết, đo lại có đúng không | độ lệch **−0,84%**, phủ KTC 92,50% |
| MDE | Tác động nhỏ nhất phát hiện được | **20,1%** (điều kiện 45–62 người xem đồng thời) |
| Độ bền với hiệu ứng lưu | Phủ KTC khi hiệu ứng kéo dài sang khối sau | bán rã 0 s → **100%**; 120 s → **84%**; 180 s → **60%** |

Bảng cuối là một **kết quả xấu mà nhóm công bố nguyên**: nếu hiệu ứng của can thiệp kéo dài quá 2 phút sang khối kế tiếp, khoảng tin cậy mất độ phủ nghiêm trọng. Đây là điều kiện sử dụng của sản phẩm, không phải chi tiết giấu được.

**Một sự cố về tính tái lập, và cách nhóm đóng nó lại.** Khi rà soát hồ sơ này (14/09/2026), nhóm chạy lại cổng A/A và ra **3,50%**, trong khi tài liệu đang công bố **4,5%**. Truy nguyên: 4,5% là số đo thật ngày 30/08, mã đã thay đổi nhiều lần sau đó và không ai đo lại — con số cũ cứ thế được chép sang tài liệu mới. Về thống kê cả hai đều tương thích mức danh nghĩa 5%, nhưng **con số không tái lập được thì không có giá trị**, và hồ sơ này tự hứa mọi số sinh lại được bằng một lệnh.

Nguyên nhân gốc: cổng Monte-Carlo chỉ *in* số khi nó đỏ; khi xanh thì số mới biến mất. Nhóm đã viết `scripts/do_lai_so_hieu_chuan.py` — đo lại bằng đúng tham số của cổng, ghi kết quả kèm ngày đo và bản mã nguồn vào `docs/benchmarks/so-hieu-chuan.json`, và có chế độ `--kiem` chạy trước mỗi lần nộp để báo đỏ nếu tài liệu lệch khỏi số đo. **Mọi con số hiệu chuẩn trong hồ sơ này lấy từ tệp đó, đo ngày 14/09/2026.**

## 7.2 Tầng 2 — Mô hình AI có đúng không

Macro-F1, F1 theo từng lớp, ma trận nhầm lẫn, và **khoảng tin cậy bootstrap cho macro-F1** — vì một con số không kèm sai số thì không kiểm chứng được. Bắt buộc chấm trên **hai tập**: bộ câu mẫu và **chat thật giữ riêng theo buổi**.

## 7.3 Tầng 3 — Hệ thống có chạy được không

| Chỉ số | Kết quả |
|---|---|
| Kiểm thử tự động | **1.174** (1.157 nhanh + 17 cổng Monte-Carlo), đếm 15/09/2026 |
| Sự cố có phân tích nguyên nhân gốc | **47**, ghi trong `docs/incident-log.md` |
| Thông lượng nạp bình luận | ~900 bình luận/giây |
| Độ trễ nạp (YouTube) | p50 24 giây · p90 37 giây |
| Tính tất định | Chạy lại một buổi sau 2 ngày: trùng từng con số |
| Cô lập phiên | Kiểm cả khi chạy song song: tuyệt đối |

# 8. Kết quả thử nghiệm, phân tích ưu điểm, hạn chế và khả năng mở rộng

## 8.1 Live-fire đa nguồn — điều đã kiểm chứng được

Ngày 10/09/2026 nhóm chạy toàn bộ đường ống trên **19.126 bình luận thật từ 16 buổi live, 7 ngành hàng**, gồm cả một buổi 117 phút với 6.586 bình luận nạp qua API trong khoảng 75 giây. Kết quả: hạ tầng nạp, khử PII, khử trùng, cô lập phiên và tính tất định đều đạt.

## 8.2 Kết quả tự bác bỏ — phần nhóm coi là giá trị nhất

Cùng đợt live-fire đó **bác bỏ chính tuyên bố của nhóm về mô hình AI**. Bộ phân loại ý định đạt macro-F1 **0,870** trên 320 câu mẫu do AI soạn, nhưng chỉ **0,211** trên chat thật — **thua cả baseline "luôn đoán lớp đa số"**. Nhóm truy ra ba cơ chế sai:

1. **Thiếu lớp** — khoảng 40% bình luận livestream Việt Nam là xã giao, một lớp không có trong bộ nhãn ban đầu (đo độc lập lần hai trên 3 người bán khác cho kết quả tương tự).
2. **Đa nghĩa tiếng Việt** — "bao nhiêu" có thể là hỏi giá, hỏi số lượng còn lại, hoặc nói đùa.
3. **Không mô hình hóa người nói** — bình luận của chính chủ shop và của khách bị xử lý như nhau.

Một phát hiện thứ hai còn quan trọng hơn với người dùng: **radar ý định không có một độ chính xác duy nhất**. Tỷ lệ nền ý định mua thật đo được trên ba buổi live trong tập kiểm tra là **0,0% · 6,8% · 48,0%** — cùng một mô hình cho kết quả rất khác nhau tùy buổi. Một sản phẩm quảng cáo "độ chính xác 87%" mà không nói điều này là đang nói sai với người dùng.

## 8.3 Kết quả sau cải tiến — đo lại bằng phương pháp chặt hơn

Nhóm dựng lại khung đánh giá trước khi sửa bất cứ thứ gì: tập kiểm tra **393 bình luận thật với nhãn tham chiếu do tác tử AI gán** (mục 6.2), chia **leave-one-session-out theo buổi live**, khoảng tin cậy bootstrap. Kết quả:

| | Trước cải tiến | Sau cải tiến |
|---|---:|---:|
| macro-F1 trên chat thật | **0,211** [0,172; 0,247] | **0,565** [0,491; 0,649] |
| Accuracy | 0,338 (*thua* baseline đoán bừa 0,389) | 0,741 |
| Precision nhãn hành động | 23,0% (54/235) | **66,7%** (40/60) |

Hai khoảng tin cậy **không chồng lấn**. Chi tiết baseline và ablation ở mục 9.

**Một đính chính nhóm phải nêu:** con số 0,271 từng công bố **không tái lập được** — tệp nhãn 200 dòng dùng hồi 08/09 không được lưu lại. Vì vậy con số "trước cải tiến" chính thức từ nay là **0,211**, đo trên tập nhãn hiện có và chạy lại được bằng một lệnh (`python -m livelift.nlp.eval_intent`). Nhóm chọn công bố số tái lập được thay vì giữ một con số đẹp hơn mà không ai kiểm lại được.

**Bệnh gốc chưa khỏi:** precision vẫn đi theo tỷ lệ nền của từng buổi — với buổi có 0% ý định mua, mô hình vẫn sai cả 11 dự đoán. Đây là lý do không có con số nào của radar ý định đi vào phần phân tích nhân quả. Một lớp chặn tín hiệu theo tỷ lệ nền của từng buổi **chưa có trong mã** và là việc cần làm.

## 8.3 Ưu điểm

- **Tính kiểm chứng**: mọi con số trong hồ sơ này sinh lại được bằng một lệnh; bộ ước lượng tự chứng minh trên A/A trước khi chạm dữ liệu thật.
- **Liêm chính cưỡng chế bằng kiến trúc**, không bằng cam kết (mục 5.3).
- **Tất định**: cùng đầu vào cho cùng đầu ra, kể cả sau nhiều ngày.
- **Chi phí vận hành thấp**: chạy được trên một máy chủ phổ thông.

## 8.4 Hạn chế — nêu đầy đủ

- **0 phiên thí nghiệm ngẫu nhiên thật.** Toàn bộ buổi live đã chạy là **quan sát**: không gán ngẫu nhiên, không link đo, không sinh ra con số nhân quả nào. Giao diện tự dán nhãn đúng như vậy để không ai hiểu nhầm.
- **Lực thống kê ở phòng live thật còn yếu.** MDE 20,1% đo ở 45–62 người xem đồng thời, trong khi thực đo với 300.000 đồng quảng cáo chỉ kéo được 5–15 người xem đồng thời.
- **Mô hình ý định chưa dùng được cho quyết định** (mục 8.2).
- **Không đo được đơn hàng trực tiếp**: đơn nằm trong ứng dụng của nền tảng; hệ thống chỉ đo được lượt nhấp hợp lệ qua link đo.
- **Mù với phiên đấu giá**; **TikTok chưa vào được** (WebSocket bị Cloudflare từ chối 10/10 lần — cần Partner API).

## 8.5 Khả năng mở rộng

Đơn vị dữ liệu là khối thời gian, nên chi phí tính toán tăng tuyến tính theo số phiên chứ không theo số người xem. Kiến trúc tách rời phần nạp dữ liệu khỏi phần phân tích, nên thêm một nền tảng mới chỉ là thêm một adapter nạp. Phương pháp chuyển giao được sang mọi bối cảnh "một kênh phát — nhiều người xem" ngoài thương mại.

# 9. So sánh với phương án cơ sở và phân tích đóng góp của các thành phần

## 9.1 So sánh với các nhóm giải pháp hiện có

| Nhóm | Đại diện | Trả lời được "bán được bao nhiêu"? | Trả lời được "bao nhiêu là do bạn"? | Nhà bán Việt Nam dùng được? |
|---|---|---|---|---|
| (a) Phân tích livestream | TikTok LIVE Manager | Có | **Không** | Có |
| (b) Phần mềm hỗ trợ bán live VN | Các công cụ chốt đơn, trả lời tự động | Một phần | **Không** | Có |
| (c) Nền tảng thí nghiệm chuyên nghiệp | Statsig, Eppo, GrowthBook | Có | Có | **Không** — đòi sở hữu nền tảng; ~1,1 tỷ đ/năm |
| **LiveLift** | | Một phần | **Có, kèm khoảng tin cậy** | **Có** |

Khoảng trống LiveLift nhắm vào nằm đúng ở ô cuối: **năng lực của nhóm (c) với điều kiện sử dụng của nhóm (a)**.

## 9.2 So sánh phương án ước lượng (mô phỏng có đáp án)

| Phương án | Trạng thái kiểm chứng | Nhận xét |
|---|---|---|
| **RI studentized + Fisher CI** (chính) | A/A: bác bỏ 3,50%, phủ 96,50% · thu hồi tác động: lệch −0,84%, phủ 92,50% (`so-hieu-chuan.json`) | Không cần giả định phân phối |
| Horvitz–Thompson (Hájek) | Trùng đại số với diff-in-means tại p = 0,5 — không phải một ước lượng độc lập | Giữ để kiểm tra chéo |
| OLS + FE phiên + Lin | **Chưa đo độ phủ bằng mô phỏng** | Giảm phương sai, cần giả định thêm |
| Diff-in-means không hiệu chỉnh | **Chưa đo độ phủ bằng mô phỏng** | Bỏ qua tương quan trong phiên |

Bản trước của bảng này ghi "thấp hơn / xấp xỉ danh nghĩa" cho ba dòng dưới mà **không có phép đo nào đứng sau**; nhóm đã gỡ và ghi đúng trạng thái. Đo so sánh độ phủ của cả bốn phương án trên cùng mô phỏng là việc đang làm.

## 9.3 So sánh với baseline trên chat thật

Tập kiểm tra: **393 bình luận thật, nhãn tham chiếu do tác tử AI gán** (chưa có nhãn người độc lập), chia **leave-one-session-out theo buổi live** — không buổi nào nằm cả ở tập huấn luyện lẫn tập kiểm tra. Khoảng tin cậy bootstrap 2.000 lần.

| Hệ thống | macro-F1 | KTC 95% | Accuracy | Precision nhãn hành động |
|---|---:|---|---:|---:|
| B0 · luôn đoán lớp đa số | 0,056 | [0,051; 0,063] | 0,389 | — |
| B1 · từ khóa (bản tiền đăng ký) | 0,146 | [0,109; 0,180] | 0,387 | 20,9% |
| B2 · **bản đang chạy trước cải tiến** | **0,211** | [0,172; 0,247] | 0,338 | 23,0% |
| C1 · bộ nhãn 11 lớp | 0,557 | [0,487; 0,614] | 0,608 | 46,2% |
| **C2 · 11 lớp + nhãn LLM trên chat thật** | **0,565** | [0,491; 0,649] | 0,741 | **66,7%** |

Khoảng tin cậy của B2 và C2 **không chồng lấn** — cải tiến là thật, không phải nhiễu. Đáng chú ý: bản trước cải tiến có accuracy 0,338, **thua cả baseline đoán bừa** (0,389); sau cải tiến đạt 0,741. Số cảnh báo sai cho người dùng giảm từ 235 xuống 60.

## 9.4 Ablation — đóng góp thật của từng thành phần

| Bỏ thành phần nào ra khỏi bản đầy đủ | macro-F1 | Chênh lệch |
|---|---:|---:|
| **A0 · bản đầy đủ** | **0,565** | — |
| − bộ 320 câu mẫu (do AI soạn) | 0,365 | **−0,200** |
| − nhãn LLM trên chat thật | 0,557 | −0,008 |
| − chuẩn hóa văn bản (NFKC/teencode/emoji) | 0,564 | −0,001 |
| − đặc trưng "ai đang nói" | 0,576 | **+0,011** |
| − nhãn thật của buổi khác trong tập huấn luyện | 0,582 | **+0,017** |
| + cơ chế từ chối trả lời (ngưỡng chọn trong tập train) | 0,492 | **−0,073** |
| bộ nhãn 6 lớp (chấm cùng thang 6 lớp) | 0,574 | — |
| bộ nhãn 11 lớp (gộp về 6 khi chấm) | **0,609** | **+0,035** |

**Đọc bảng này trung thực:**
- Thứ đóng góp nhiều nhất là **bộ 320 câu mẫu** (bỏ đi mất 0,200). Bộ này cũng do AI soạn, nên kết luận đúng là: dữ liệu mẫu có chủ đích tốt hơn dữ liệu thật gán vội — chưa phải "dữ liệu người làm".
- Bộ **nhãn 11 lớp thắng ngay cả khi chấm trên thang 6 lớp cũ** (0,609 so với 0,574), tức cái lợi đến từ việc *có chỗ đặt* cho hơn 40% chat là xã giao và bảng giá của shop, chứ không phải do đổi cách chấm.
- **Ba thành phần nhóm kỳ vọng có ích thì không có ích**: chuẩn hóa văn bản gần như bằng không (đặc trưng n-gram ký tự đã dung sai sẵn), đặc trưng "ai đang nói" **làm xấu đi**, và cơ chế từ chối trả lời với ngưỡng chọn trung thực (không nhìn tập kiểm tra) **làm xấu đi rõ rệt** — hiệu chuẩn ngưỡng không chuyển giao được sang buổi live mới.

**Vì sao nhóm không chọn cấu hình có điểm cao nhất.** Hai cấu hình bỏ bớt thành phần đạt 0,576 và 0,582, cao hơn bản đầy đủ 0,565. Nhóm vẫn giữ bản đầy đủ, vì các khoảng tin cậy chồng lấn nhau và **chọn cấu hình theo điểm trên chính tập kiểm tra là một dạng khớp quá mức**. Việc đúng là công bố cả bảng và để người đọc thấy.

**Điều nhóm KHÔNG làm, và nói thẳng:** chưa tinh chỉnh ViSoBERT. Máy của nhóm không có `torch`/`transformers` và chưa xác nhận được GPU; hứa một con số transformer mà không chạy được là điều nhóm từ chối làm.

# 10. Kiến trúc hệ thống và phương án triển khai

```
   NGUỒN                 NẠP & LÀM SẠCH            LÕI                    NGƯỜI DÙNG
 ┌──────────┐         ┌────────────────┐    ┌──────────────────┐     ┌──────────────┐
 │ YouTube  │──API──► │  Adapter nạp   │    │ Bộ gán ngẫu nhiên│     │ /desk        │
 │ Data API │         │      ↓         │──► │  (khóa trước khi │────►│ Bàn điều     │
 ├──────────┤         │  KHỬ PII       │    │   lên sóng)      │     │ khiển        │
 │ Facebook │──API──► │  (bắt buộc)    │    ├──────────────────┤     ├──────────────┤
 │ Graph API│         │      ↓         │    │ NLP: phân loại   │     │ /host        │
 ├──────────┤         │  Chuẩn hóa     │    │ ý định + abstain │     │ (LÀM MÙ:     │
 │ Link đo  │──HTTP─► │      ↓         │    ├──────────────────┤     │ không thấy   │
 │ /r/{code}│         │  Khử trùng     │    │ Phân tích nhân   │     │ khối/nhánh)  │
 └──────────┘         │  (platform,    │    │ quả: RI + Fisher │     ├──────────────┤
                      │   ext_id)      │    │ CI, CUPED, LATE  │     │ /report      │
                      └───────┬────────┘    └────────┬─────────┘     │ (KHÓA tới    │
                              ▼                      ▼               │  mốc prereg) │
                      ┌─────────────────────────────────────┐        └──────────────┘
                      │  PostgreSQL — 9 migration có version│
                      │  assignment · exposure_event ·      │
                      │  comment · click · design_hash      │
                      └─────────────────────────────────────┘
```

**Thành phần:** API FastAPI (Python) · giao diện Next.js/TypeScript · PostgreSQL · Caddy làm cổng vào HTTPS · toàn bộ đóng gói bằng Docker Compose.

**Ba cổng chặn trong luồng xử lý** (không vượt qua được bằng cấu hình):
- Nạp dữ liệu **không đi qua bộ khử PII** → không có đường nào ghi xuống kho.
- Phiên **không có `design_hash`** → API trả HTTP 409, không phát sóng được.
- Chưa tới mốc mở khóa prereg → endpoint kết quả **không trả** ước lượng, p, KTC.

![Hình 1 — Lịch bốc thăm sinh ra và khóa lại TRƯỚC khi lên sóng, kèm design_hash. Sau bước này lịch không sửa được.|10.5](../../img/l3-05-buoc3-lich-da-boc.png)

![Hình 2 — Bàn điều khiển phiên trực tiếp: dải khối thời gian, đồng hồ đếm khối, nhật ký can thiệp.|10.5](../../img/l3-07-ban-dieu-khien.png)

![Hình 3 — Màn hình người dẫn được LÀM MÙ: chỉ thấy việc cần làm, không thấy khối hay nhánh gán.|10.5](../../img/l3-11-host-da-ghim.png)

## 10.1 Phương án triển khai và lý do chọn

Thể lệ đòi sản phẩm **chạy ổn định ít nhất 48 giờ** trước thời điểm kiểm tra. Ràng buộc đó loại ngay một nhóm lựa chọn tưởng là tiện:

| Phương án | Chi phí | Có ngủ đông? | Kết luận |
|---|---|---|---|
| Render / Fly.io / Hugging Face Spaces (gói miễn phí) | 0 đ | **Có** | **Loại** — ngủ đông là tử huyệt với yêu cầu 48 giờ |
| **Oracle Cloud Always Free (Singapore)** | **0 đ** | Không | **Chọn** — 2 OCPU / 12 GB RAM, độ trễ ~35 ms từ Việt Nam |
| Vultr (tính tiền theo giây) | ~17.000 đ cho 48 giờ | Không | Dự phòng khi Oracle hết suất |

Tên miền: cả ba thành viên 20 tuổi nên **đủ điều kiện đăng ký tên miền `.id.vn` miễn phí** theo Thông tư 64/2025 (công dân 18–23 tuổi).

Triển khai bằng **một lệnh `docker compose up`**: API, giao diện, PostgreSQL và Caddy (tự cấp chứng chỉ HTTPS). Nhóm bổ sung cho bản chạy thật: **healthcheck cho cả ba dịch vụ** (trước đó không có cái nào, nên chính sách tự khởi động lại chỉ cứu được tiến trình thoát hẳn chứ không cứu tiến trình treo), **xoay vòng nhật ký** (ổ đầy làm PostgreSQL ngừng ghi — kiểu chết âm thầm hay gặp nhất), **trần bộ nhớ**, header bảo mật, và **ba trang lỗi tiếng Việt** thay cho trang mặc định lộ vết ngăn xếp.

## 10.2 Chứng minh khả năng duy trì

Nhóm kiểm chứng bằng cách **phá thật rồi xem hệ thống có sống lại không**, chứ không bằng cấu hình trên giấy:

- **Sao lưu 5/5** đạt kiểm tra toàn vẹn (`gzip -t` + chữ ký `PGDMP`); khôi phục được chứng minh bằng cách **giết cứng tiến trình**, có đối chứng âm để bảo đảm phép thử không tự dối mình.
- **Giết tiến trình API** trong lúc trang đang mở: trang vẫn trả HTTP 200, **không lộ một vết ngăn xếp nào**; bật lại thì đủ 33 phiên.
- Kiểm tra rò rỉ nhãn DEMO/THẬT: **0 chỗ rò**, và client **không giả mạo được** cờ `is_demo`.
- Quét toàn bộ 42 commit tìm bí mật bị lộ: **0**.
- `scripts/kiem_tra_truoc_demo.py` — một lệnh xác nhận mọi phân hệ sẵn sàng trước khi trình diễn trước hội đồng (9 mục kiểm, đã thử cả ba đường hỏng).

**Hạn chế trung thực:** tại ngày viết hồ sơ, `docker compose up` **chưa kiểm chứng được trên máy của nhóm** vì dịch vụ Docker cần quyền quản trị mà nhóm chưa mở được; đường chạy thay thế (`chay_local.py`) thì đã chạy thật và xanh. Việc kiểm chứng Docker và đưa lên địa chỉ công khai là hạng mục đang thực hiện.

**Địa chỉ demo công khai:** ⬜ *điền trước khi nộp*

# 11. Phân tích rủi ro, yêu cầu bảo mật, đạo đức trí tuệ nhân tạo và an toàn dữ liệu

## 11.1 Rủi ro và biện pháp

| Rủi ro | Hậu quả | Biện pháp đã có |
|---|---|---|
| Rò rỉ dữ liệu cá nhân của người xem | Vi phạm Luật 91/2025/QH15 | Khử PII trước khi ghi đĩa; cổng recall ≥95%; không lưu định danh người bình luận |
| Người dùng tin vào kết quả không đủ lực thống kê | Quyết định kinh doanh sai | Luôn trả khoảng tin cậy; báo rõ khi MDE lớn hơn tác động quan tâm |
| Mô hình AI trả lời sai được dùng để ra quyết định | Thiệt hại cho nhà bán | Công bố macro-F1 trên chat thật (0,211 → 0,565, đo so với nhãn tham chiếu do AI gán) **theo cặp với số trên bộ câu mẫu**; tín hiệu ý định không vào phần phân tích nhân quả; lớp chặn theo tỷ lệ nền **chưa có** |
| Nhìn lén kết quả rồi dừng phiên khi số đẹp | Kết quả mất giá trị khoa học | Khóa `RESULTS_FREEZE_UNTIL` *fail-closed* |
| Người dẫn biết nhánh gán | Thiên lệch phép đo | Màn hình `/host` làm mù |
| Lệ thuộc điều khoản dịch vụ của nền tảng | Mất nguồn dữ liệu | Chỉ dùng API chính thức trên đường chạy mặc định; ghi rõ nền tảng nào chưa vào được |
| Bí mật lộ trong kho mã | Chiếm quyền truy cập | Bí mật qua biến môi trường, không vào git |

## 11.2 Đạo đức trí tuệ nhân tạo và khuôn khổ pháp lý

Ba văn bản chi phối sản phẩm này, và nhóm đối chiếu từng cái:

- **Luật Trí tuệ nhân tạo số 134/2025/QH15** (Quốc hội khóa XV thông qua ngày 10/12/2025, **hiệu lực 01/3/2026**). LiveLift là hệ thống AI hỗ trợ ra quyết định, **không** thuộc nhóm rủi ro cao: nó không quyết định thay con người, không đánh giá con người, không tác động tới quyền cơ bản. Nhóm thực hiện nghĩa vụ **minh bạch**: người dùng luôn được cho biết phần nào là kết quả mô hình, độ tin cậy bao nhiêu, và khi nào hệ thống không đủ căn cứ để kết luận.
- **Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15** (Quốc hội thông qua 26/6/2025, hiệu lực 01/01/2026) và **Nghị định 356/2025/NĐ-CP** ngày 31/12/2025 quy định chi tiết — văn bản này thay thế Nghị định 13/2023/NĐ-CP. Xử lý ở mục 3.2.
- **Điều 5 Thể lệ Cuộc thi** về kê khai trung thực công cụ AI — xử lý bằng Bản kê khai nộp kèm.

Trên nền đó, nhóm xác định **ba cam kết**, cả ba đều có cơ chế thực thi chứ không chỉ là tuyên bố:

1. **Không tuyên bố quá năng lực thật.** Số xấu công bố cùng số đẹp, luôn theo cặp. Quy tắc nội bộ: không bao giờ trích riêng macro-F1 trên bộ câu mẫu mà không kèm số trên chat thật.
2. **Kiểm soát đầu ra.** Mô hình được phép nói "không chắc". Ba trạng thái kết quả — đủ bằng chứng / không đủ bằng chứng / chưa đủ dữ liệu — thay vì ép mọi phiên ra một con số.
3. **Con người giữ quyền quyết định.** LiveLift **không** tự động hóa việc ghim sản phẩm. Hệ thống đưa bằng chứng, người bán quyết định.

## 11.3 An toàn thông tin

Khi rà soát trước lúc đưa sản phẩm lên Internet, nhóm phát hiện **12 trong 15 endpoint ghi không có xác thực** — người lạ có thể kết thúc một phiên thí nghiệm đang chạy (phá hỏng tính hợp lệ khoa học của phiên đó) hoặc bắt máy chủ tải video bất kỳ. Nhóm đã vá, và cách vá là phần đáng nói:

- **Một cổng duy nhất gắn ở cấp ứng dụng**, không phải từng route. Hệ quả: route ghi thêm về sau **mặc định được bảo vệ**; route quên khai báo rơi về mức ngặt nhất thay vì mở ra. Một cổng kiểm thử đọc thẳng bảng định tuyến nên quên là **kiểm thử đỏ**, không phải lỗ hổng im lặng.
- **Hai mức phân theo thiệt hại thật.** Bắt buộc token với những đường mà bản ghi giả sẽ thành một điểm dữ liệu sai trong kết quả khoa học (bình luận, nhịp phiên, phản ứng) và đường tốn tài nguyên. Các đường còn lại cho thao tác không token **nhưng chỉ trên dữ liệu mẫu**.
- **Máy chủ quyết định dữ liệu là thật hay mẫu, không phải client.** Yêu cầu chứng minh được là người vận hành (có token) thì tạo phiên thật; không có token thì mọi thứ tạo ra đều là dữ liệu mẫu. Nhờ vậy hội đồng chấm **chạy trọn được cả quy trình** — tạo phiên, bốc lịch, phát sóng, ghim, kết thúc — mà thao tác của khách **không bao giờ lẫn vào kết quả thật**. Thử tác động lên phiên thật thì bị từ chối và **trạng thái không đổi một ly** (có kiểm thử đối chứng).
- Giới hạn tần suất đặt ở tầng ứng dụng chứ không ở máy chủ web, vì chỉ ở đó mới biết yêu cầu có token hay không — bộ thu dữ liệu của chính nhóm do đó không bao giờ bị chặn nhầm. Địa chỉ người gọi lấy ở vị trí **không giả mạo được** bằng một dòng lệnh.

Ngoài ra: bí mật quản lý qua biến môi trường (quét toàn bộ 42 commit: **0 bí mật bị lộ**), HTTPS bắt buộc, header bảo mật, trang lỗi tiếng Việt không lộ dấu vết ngăn xếp, sao lưu có kiểm chứng phục hồi.

**Rủi ro nhóm biết là vẫn còn:** danh mục sản phẩm hiện dùng chung toàn hệ thống (chưa có chủ sở hữu); WebSocket chưa kiểm nguồn gọi; và chế độ cho khách thao tác trên dữ liệu mẫu là một **đánh đổi có chủ ý** — máy chạy thí nghiệm thật phải tắt nó bằng cấu hình.

# 12. Hướng phát triển, hoàn thiện và khả năng ứng dụng trong thực tiễn

**Ưu tiên 1 — xóa khoảng cách lớn nhất (MT3).** Chạy những phiên thí nghiệm ngẫu nhiên thật đầu tiên với nhà bán đối tác, phân tích đúng theo tệp tiền đăng ký đã khóa, và công bố kết quả dù là kết quả âm.

**Ưu tiên 2 — làm cho phân hệ NLP dùng được cho quyết định**: hoàn tất tinh chỉnh ViSoBERT trên nhãn chat thật, hiệu chuẩn ngưỡng, và báo cáo độ chính xác **theo từng buổi** thay vì một con số gộp.

**Ưu tiên 3 — độ tin cậy vận hành**: giữ môi trường demo công khai chạy liên tục, giám sát, và quy trình phục hồi có tập dượt.

**Trung hạn:** phát lại phản thực (counterfactual replay) để ước lượng chính sách ghim tốt hơn mà không cần phát sóng thêm; co-pilot nghe hiểu tiếng Việt (PhoWhisper) cho người dẫn; mở rộng nền tảng khi có Partner API.

**Khả năng ứng dụng rộng hơn.** Lõi phương pháp không gắn với thương mại. Bất cứ nơi nào có một kênh phát và nhiều người xem, mà người vận hành muốn biết cách làm nào thật sự hiệu quả hơn, đều dùng được thiết kế này: truyền thông chiến dịch cộng đồng, phổ biến kiến thức pháp luật, tư vấn tuyển sinh, khuyến nông trực tuyến. Chi phí biên gần như bằng không vì cùng một hạ tầng.

# 13. Lịch sử câu lệnh và hình ảnh minh chứng quá trình phát triển sản phẩm

**Kho lưu trữ mã nguồn:** https://github.com/bminhnemhoi/AISC2026_LIVEFIT — có toàn bộ lịch sử thay đổi mã nguồn thật của quá trình phát triển.

**Thư mục minh chứng (Google Drive):** ⬜ *dán liên kết đã mở quyền truy cập trước khi nộp*

Thư mục gồm:
- **Lịch sử câu lệnh (Prompt Log)**: câu lệnh hệ thống và toàn bộ lịch sử hội thoại với công cụ AI, đã làm sạch bí mật và thông tin cá nhân.
- **Ảnh minh chứng quá trình phát triển** từ bản nháp đến bản hoàn thiện, kèm chú thích theo mốc thời gian.
- **Tài liệu kỹ thuật**: tệp tiền đăng ký phân tích, sổ sự cố, báo cáo hiệu chuẩn, báo cáo live-fire.
- **Bản kê khai** công cụ AI, mô hình, bộ dữ liệu, API, thư viện, mã nguồn mở, kèm phân định phần đội tự xây dựng / phần AI hỗ trợ / phần kế thừa.
