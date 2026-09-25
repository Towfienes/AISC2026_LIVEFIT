<!-- NGUỒN NỘI DUNG HỒ SƠ DỰ ÁN BẢNG C — Cuộc thi Sáng tạo trẻ Quốc gia về AI 2026 -->
<!--
DỰNG (cần .venv-docx có python-docx; Word để đếm trang):
  .venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/dung_ho_so.py
  bản nháp khi còn ô ⬜ hoặc thiếu hình: thêm  --out-dir <thư mục> --cho-phep-o-trong
Giới hạn CỨNG 20 trang, Word đếm. Mọi con số phải khớp docs/competition/FACT-SHEET.md
và nguồn ghi ngay cạnh số. Số test đồng bộ lần cuối bằng scripts/dong_bo_so_test.py --xem-truoc.
Số NLP lấy từ docs/benchmarks/intent-eval/results.md (sinh lại 25/09/2026, sau khi lọc lại PII).

CÚ PHÁP MÀ BỘ DỰNG HIỂU (sửa 25/09/2026):
  # 1. Tiêu đề                 mục cấp 1 — phải đủ 1..13 đúng thứ tự MẪU 3
  # Tên không số               mục cấp 1 KHÔNG đánh số: được phép (Tóm tắt, Tài liệu tham khảo)
  ## 1.1 Tiêu đề / ### …       mục cấp 2 / cấp 3; không được trùng số mục
  một dòng văn                 một đoạn văn canh đều
  - nội dung / 1. nội dung     gạch đầu dòng / danh sách số (thụt treo)
  > dòng                       khung nền nhạt một ô (dùng cho Tóm tắt dự án); "> - " là gạch đầu dòng trong khung
  : Bảng N. Chú thích          đặt NGAY TRÊN một bảng; chú thích in đậm "Bảng N." phía trên bảng
  | ô | ô |                    bảng; hàng đầu là tiêu đề (tô nền, lặp mỗi trang); |---:| canh phải
  ![Hình N. Chú thích](hinh/tep.png){width=16cm}
                               hình canh giữa, chú thích "Hình N." ngay dưới; thiếu tệp thì bộ dựng
                               in [THIẾU HÌNH: …] ở bản nháp và CHẶN bản nộp (không sập)
  **đậm**, *nghiêng*, `mã`     trong câu, lồng được (mã in Consolas nền nhạt, không lọt dấu `)
  ```  …  ```                  khối mã, giữ liền một khối
  ⬜                           ô đội PHẢI điền — còn ô này thì bộ dựng không ra bản nộp
Hình và Bảng đánh số liên tục 1..n theo thứ tự xuất hiện. "mục X.Y", "Hình N", "Bảng N"
phải trỏ tới thứ có thật — bộ dựng kiểm và chặn nếu sai.
Tài liệu tham khảo đánh [n] thủ công theo danh mục cuối tệp.
-->

# Tóm tắt dự án

> **LiveLift** là phần mềm mã nguồn mở (AGPL-3.0) giúp nhà bán livestream đo **tác động nhân quả** của hành động trong phiên (ghim sản phẩm, nhắc mã giảm giá) bằng thí nghiệm **switchback**: các khối thời gian bốc thăm bật hoặc tắt can thiệp theo lịch khóa trước giờ phát, rồi so hai nhóm khối bằng kiểm định ngẫu nhiên hóa. Đi kèm là bộ lọc dữ liệu cá nhân và bộ phân loại ý định mua cho bình luận tiếng Việt.
> - Mô phỏng có đáp án: A/A bác bỏ **3,50%** (7/200, danh nghĩa 5%); thu hồi tác động biết trước lệch **−0,84%**, KTC 95% phủ **92,50%** (37/40) (đo lại 25/09/2026, Bảng 4).
> - Ý định trên chat thật: macro-F1 **0,211** (v1, mặc định) → **0,542** (v2, bật bằng biến môi trường) trên 393 bình luận, thang 11 lớp (cùng thang 6 lớp: 0,370 → 0,572); nhãn tham chiếu do tác tử AI gán, chưa có nhãn người.
> - **19.126** bình luận quan sát từ 16 buổi phát lại trên YouTube, tải bằng yt-dlp, không qua API chính thức và chưa có đồng ý của người bình luận; đã dừng thu từ 17/09/2026 (mục 3.3).
> - **2.093** kiểm thử tự động, chạy lại ngày 25/09/2026: 2.091 đạt, 2 bỏ qua có lý do; **109** sự cố có phân tích nguyên nhân gốc (`docs/incident-log.md`).
> **Chưa có:** phiên thí nghiệm ngẫu nhiên thật nào, khóa API nền tảng nào, nhà bán nào ngoài nhóm dùng thử.

**Viết tắt:** A/A – thí nghiệm giả, không tác động; burn-in – phần đầu khối bị bỏ khi phân tích; CUPED – giảm phương sai bằng hiệp biến; CV – hệ số biến thiên; KTC – khoảng tin cậy; LATE – tác động trên nhóm tuân thủ; LLM – mô hình ngôn ngữ lớn; LOSO – giữ riêng từng buổi làm tập kiểm tra; macro-F1 – F1 trung bình đều các lớp; MDE – tác động nhỏ nhất phát hiện được; NLP – xử lý ngôn ngữ tự nhiên; OLS FE – hồi quy hiệu ứng cố định theo phiên; PII – thông tin nhận dạng cá nhân; RI – kiểm định ngẫu nhiên hóa; VOD – bản phát lại; κ – độ đồng thuận giữa hai người gán nhãn.

# 1. Bài toán hoặc vấn đề thực tiễn cần giải quyết

**Tên sản phẩm: LiveLift — hạ tầng đo lường nhân quả cho phiên livestream bán hàng.**

Ở Việt Nam, AccessTrade ước khoảng 2,5 triệu phiên livestream bán hàng mỗi tháng với hơn 50.000 nhà bán [10] (số thứ cấp năm 2024, nhóm chưa truy được báo cáo gốc). Mỗi phiên có hàng chục quyết định — ghim sản phẩm nào, lúc nào, giữ bao lâu, nhắc mã giảm giá khi nào — phần lớn dựa vào kinh nghiệm. Công cụ của nền tảng như TikTok LIVE Manager trả lời “phiên vừa rồi bán được bao nhiêu”; theo rà soát công cụ và tài liệu của nhóm (09/2026), chưa có công cụ nào nhà bán tự dùng được để trả lời “**bao nhiêu trong số đó là do hành động của mình**”.

Ví dụ: phút 30 người trợ live ghim sản phẩm B, phút 35 lượt nhấp vào B nhích lên. Có thể vì vừa ghim B, vì nền tảng vừa đẩy thêm người vào phòng, hoặc vì người dẫn vừa kể xong một câu chuyện hay. Số liệu sau phiên không tách được ba khả năng này; muốn tách phải so cùng buổi live đó lúc ghim và lúc không ghim.

## 1.1 Vì sao A/B test thông thường không dùng được

A/B test chia người dùng làm hai nửa; trong livestream cả phòng nhìn **cùng một màn hình** nên không chia được. Thứ chia được là **thời gian**, tức thiết kế **switchback** (Hình 1): phiên 90 phút chia thành 16 khối (khối đầu và cuối 10 phút, 14 khối giữa 5 phút), mỗi khối bốc thăm bật hoặc tắt can thiệp, lịch khóa trước giờ phát.

**Mô hình hóa.** Gọi *Y*(1), *Y*(0) là số lượt nhấp hợp lệ trên 1.000 giây·người xem của một khối (sau burn-in) khi khối bật và khi tắt. Đại lượng cần ước lượng là τ, trung bình *Y*(1) − *Y*(0) trên các khối, theo nhánh được gán; mỗi khối chỉ thấy một giá trị nên τ ước lượng bằng hiệu trung bình hai nhóm khối, p và KTC lấy từ phân phối ngẫu nhiên hóa (mục 5.1). Giả định then chốt: tác động không kéo sang khối sau quá burn-in (mục 7.1).

![Hình 1. Lịch 16 khối của một phiên 90 phút sinh bằng chính hàm gán của sản phẩm (seed 42); 60 giây đầu mỗi khối bị bỏ khi phân tích; lịch và `design_hash` được lưu trước giờ phát.](hinh/h1-switchback.png){width=16cm}

## 1.2 Vì sao cấp thiết và ai đang bị bỏ lại

Thí nghiệm ngẫu nhiên trong livestream đã cho thấy quyết định trong phiên tác động thật tới doanh số: cho người dẫn xem số bán theo thời gian thực làm doanh số hàng đặt trước tăng khoảng 40% [7]; trợ lý AI cho người mua tăng doanh số 3,00%, giảm trả hàng 12,55% [6]. Nhưng các thí nghiệm đó do **nền tảng** chạy, và công cụ thí nghiệm chuyên nghiệp (Statsig, Eppo, GrowthBook) cũng giả định người dùng sở hữu nơi thí nghiệm diễn ra. Rào chắn chính là **quyền sở hữu nền tảng**, không phải giá. Nhà bán chỉ kiểm soát hành động của chính mình theo thời gian; LiveLift biến đúng thứ đó thành đơn vị bốc thăm và mở mã nguồn cho mọi người.

**Nghị quyết 57-NQ/TW ngày 22/12/2024 của Bộ Chính trị** coi khoa học, công nghệ, đổi mới sáng tạo và chuyển đổi số là “đột phá quan trọng hàng đầu” [15]; không đo được tác động thì không biết thay đổi nào đáng giữ.

## 1.3 Gốc học thuật và khoảng trống

Xie, Sharma và Mehra [5] tìm ra một **đánh đổi**: trình bày một sản phẩm lâu hơn thì doanh thu sản phẩm đó cao hơn, nhưng thời lượng trình bày trung bình tăng thì doanh thu cả phiên giảm; không có đáp án chung, mỗi phòng live phải tự đo, và dữ liệu của họ là hồi cứu. Trong phạm vi rà soát tài liệu và công cụ của nhóm (09/2026), **chưa tìm thấy công bố hay công cụ nào cho người bán tự chạy switchback trong phiên livestream của mình**. Vì rủi ro lớn nhất khi dùng số liệu là tin vào số sai, dự án kiểm chứng bộ ước lượng trên mô phỏng trước, và đo mô hình AI trên chat thật chứ không chỉ trên câu mẫu (mục 8.2).

# 2. Mục tiêu, phạm vi và đối tượng ứng dụng của sản phẩm

## 2.1 Mục tiêu

**Mục tiêu tổng quát:** xây dựng hạ tầng đo lường nhân quả cho phiên livestream bán hàng, dành cho bên không sở hữu nền tảng: mỗi quyết định trong phiên thành một thí nghiệm có xác suất gán ghi trước giờ phát, kết quả kèm KTC, và bộ ước lượng phải qua kiểm chứng trên mô phỏng có đáp án trước khi dùng cho dữ liệu thật.

: Bảng 1. Mục tiêu cụ thể và trạng thái tại ngày 25/09/2026

| Mục tiêu | Chỉ số nghiệm thu | Trạng thái |
|---|---|---|
| MT1. Bộ ước lượng đạt mức danh nghĩa | A/A 200 lần: bác bỏ 3,50% (7/200), p 0,4168; thu hồi 40 lần: phủ KTC 92,50% | **Đạt khi không có hiệu ứng lưu**; có lưu thì độ phủ tụt (Hình 3) |
| MT2. MDE đo bằng mô phỏng | 16,4% ở ~59 người xem, 8 phiên, từ CV mô phỏng (Hình 4) | **Một phần**: quét lực trực tiếp 30/08 không sinh lại được |
| MT3. ≥18 phiên thí nghiệm thật có gán ngẫu nhiên | **0 phiên** | **Chưa đạt**: khoảng cách lớn nhất (mục 8.5, 12) |
| MT4. Hạ tầng nạp đúng, tái lập được | VOD qua yt-dlp: 19.126 bình luận; chạy lại 1 buổi sau 2 ngày trùng từng con số; API chính thức **chưa chạy với khóa thật** | **Một phần** |
| MT5. Quyền riêng tư, liêm chính thực thi bằng mã | Cổng recall PII; phiên chưa có lịch gán bị chặn phát sóng (HTTP 409) | **Một phần** (mục 3.2) |
| MT6. Kiểm chứng mô hình AI trên chat thật | 0,870 trên câu mẫu AI soạn, 0,211 trên chat thật; sau cải tiến 0,542 | **Một phần**: nhãn do AI gán |

## 2.2 Phạm vi

**Trong phạm vi:** phiên livestream bán hàng tiếng Việt mà nhà bán là chủ kênh hoặc được ủy quyền, đọc qua API chính thức (YouTube, Facebook, Shopee); can thiệp thuộc quyền nhà bán: ghim sản phẩm, nhắc mã giảm giá đã công bố cho mọi người xem, đổi kịch bản thoại. Biến kết quả chính là lượt nhấp hợp lệ qua link đo; biến phụ là đơn hàng nhập từ tệp CSV. **Ngoài phạm vi, có chủ ý:** đọc bình luận bằng cách giả làm người xem (quyết định 17/09/2026); bình luận TikTok LIVE (không có API chính thức); can thiệp thuật toán phân phối; dự báo doanh thu; phiên đấu giá.

## 2.3 Đối tượng ứng dụng

Đối tượng phù hợp nhất là **nhà bán tự phát sóng trên Facebook hoặc YouTube, có lượng xem ổn định**, chốt đơn qua website riêng hoặc inbox: phiên dài, lặp đều nên đủ khối, và link đo trỏ tới trang sản phẩm hoặc `m.me`, `zalo.me` nên ghi được cú nhấp thật. **KOL có người trợ live** cũng khớp, vì cần hai người: một người nắm lịch, người dẫn không biết lịch (mục 5.3). Nhà bán chốt bằng giỏ hàng trong ứng dụng (TikTok Shop, Shopee Live) **chưa dùng được biến kết quả chính**, nên 2,5 triệu phiên ở mục 1 là quy mô ngành, không phải quy mô LiveLift phục vụ được hôm nay.

**Lực thống kê quyết định ai dùng được.** Với lượt nhấp, MDE tỷ lệ nghịch với căn bậc hai của số người xem nhân số phiên (Hình 4). Nhóm **ước tính từ giá quảng cáo (CPM), chưa đo**, rằng 300.000 đồng quảng cáo chỉ kéo được 5–15 người xem đồng thời; ở mức đó, với 18 phiên, tác động lượt nhấp dưới khoảng 21–67% không thể phát hiện (sàn Poisson, Hình 4), còn với đơn hàng MDE là 179–327%. Vì vậy LiveLift nhắm tới nhà bán có vài chục người xem trở lên, hoặc gộp nhiều phiên cho một câu hỏi. Đây là giả thuyết thiết kế: nhóm **chưa phỏng vấn hay thử với nhà bán nào ngoài đội**.

# 3. Dữ liệu sử dụng, nguồn dữ liệu và tính hợp lệ của dữ liệu

## 3.1 Các loại dữ liệu

: Bảng 2. Các loại dữ liệu, nguồn và cơ sở sử dụng

| Loại dữ liệu | Nguồn, cách thu | Quy mô | Cơ sở sử dụng, giới hạn |
|---|---|---|---|
| Bình luận 16 buổi live đã kết thúc (YouTube, kênh bên thứ ba) | **yt-dlp, không qua API chính thức**, 10/09/2026 | 19.126 bình luận, 7 ngành hàng; 3 buổi chiếm 84,5% | **Quan sát**, chỉ để đánh giá; **không có sự đồng ý** của người bình luận |
| Câu mẫu ý định | Claude (Anthropic) soạn ngày 01/09/2026 theo bộ nhãn của nhóm | 320 câu | Tổng hợp, không chứa dữ liệu cá nhân |
| Nhãn ý định trên bình luận thật | **Tác tử AI (Claude) gán**; nhóm quyết định bộ nhãn | 393 dòng kiểm tra (3 buổi), 1.800 dòng huấn luyện | Chưa có nhãn người (mục 6) |
| Lượt nhấp; đơn hàng | Link đo `/r/{code}`; đơn nhà bán tự xuất CSV | Chưa có phiên thật | Nhấp: chỉ lưu mã băm có muối theo phiên; đơn: không đọc người mua |
| Dữ liệu tổng hợp | Bộ mô phỏng; 200 bình luận tác tử AI soạn 17/09 | 38.848 khối (Bảng 4, Hình 2–4) | Chỉ trên phiên chạy thử, phiên mẫu |
| KuaiLive [8] | 21 ngày dữ liệu Kuaishou | 1,16 triệu phòng live | Phi thương mại; chỉ hiệu chỉnh hình dạng mô phỏng |

## 3.2 Bảo vệ dữ liệu cá nhân

Bình luận công khai vẫn chứa dữ liệu cá nhân: người xem ghi số điện thoại, địa chỉ để đặt hàng. Để giảm rủi ro theo Luật 91/2025/QH15 [11] và Nghị định 356/2025/NĐ-CP [12], sản phẩm có ba lớp trong mã; chúng không thay cho căn cứ xử lý (mục 3.3):

1. **Lọc định danh trước khi truyền hoặc lưu:** bộ thu lọc văn bản trước khi gửi đi hay ghi nhật ký, API lọc lại lần hai trước khi ghi kho; nhận diện số điện thoại (kể cả số viết bằng chữ, emoji chữ số), email, mã đơn, địa chỉ, tên người, số tài khoản, tài khoản mạng xã hội. **Ngoại lệ:** trên đường yt-dlp, tệp chat thô nằm trong thư mục tạm cho tới khi đọc xong thì bị xóa.
2. **Cổng kiểm thử:** recall ≥95% cho sáu loại và ≥70% cho tên người, trên 95 câu dữ liệu giả do Claude soạn ngày 24/08/2026 (email, số tài khoản mới có 4 mẫu mỗi loại). CI trên GitHub chưa chạy được, nên cổng hiện chạy tay.
3. **Không lưu định danh người bình luận, kể cả dạng băm;** chống trùng bằng mã bình luận của nền tảng. Lượt nhấp chỉ lưu mã băm dấu vân tay thiết bị trộn mã phiên và muối ngẫu nhiên, nên không nối được một người qua hai phiên.

**Lỗ hổng tự phát hiện.** Bộ lọc từng bỏ lọt tên tài khoản YouTube có dấu (thấy 15/09; mẫu thử khi đó đều là tên ASCII) và tên viết dính liền `chữ@tên`, `@@tên` (vá 25/09, `b331076`). Dữ liệu gán nhãn lưu cục bộ được lọc lại (`scripts/gan_mu/loc_lai_pii.py`: 57 tên tài khoản, rồi 16 dòng của 8 tên), quét lại còn 0, mọi số NLP ở mục 8–9 được đo lại. Từ vựng tệp mô hình v2 ngày 14/09 có một từ sinh từ tên tài khoản; tệp đã đóng gói lại (bản cũ còn trong lịch sử git của kho công khai), cổng `tests/test_artifact_khong_pii.py` nay kiểm cả từ vựng.

## 3.3 Tính hợp lệ của nguồn dữ liệu

**Nguồn không chính thức.** YouTube Data API v3 chỉ trả bình luận khi buổi phát đang diễn ra; 19.126 bình luận ở Bảng 2 được tải bằng yt-dlp, cách truy cập tự động mà điều khoản dịch vụ và `robots.txt` của YouTube không cho phép khi chưa được đồng ý. Dữ liệu này không có can thiệp hay bốc thăm nên không sinh con số nhân quả nào.

**Sự đồng ý và vai trò pháp lý.** Điều 5 khoản 8 Thể lệ không cho đội thi thu thập, xử lý dữ liệu cá nhân khi chưa có sự đồng ý hợp lệ [16]; Luật 91/2025/QH15 đòi sự đồng ý trước khi thu thập (Điều 11 khoản 1), không coi im lặng là đồng ý (Điều 9 khoản 4 điểm d), và Điều 19 không có trường hợp miễn đồng ý nào dành riêng cho nghiên cứu. Người bình luận trong 16 buổi không được hỏi ý kiến, nên nhóm **không tự nhận căn cứ xử lý** cho tập này. Với tập đó nhóm là bên kiểm soát và xử lý dữ liệu cá nhân (Điều 2 khoản 9) và chỉ giảm thiểu rủi ro: lọc định danh trước khi lưu, không lưu tên hay mã người bình luận, không công bố nguyên văn, không đưa lên kho mã hay thư mục minh chứng (trừ vài dòng chat đã thay danh tính và lọc, dùng làm dữ liệu kiểm thử, và vài câu ví dụ đã lọc trong `nlp/labels.py`). Khi gán nhãn và rà dữ liệu (09–15/09), bình luận được đưa vào Claude (Anthropic, ngoài Việt Nam) khi bộ lọc chưa bắt được tên tài khoản có dấu (mục 3.2): đó là xử lý dữ liệu cá nhân thu tại Việt Nam trên nền tảng ở nước ngoài (Điều 20 khoản 1 điểm c), và nhóm chưa lập hồ sơ đánh giá tác động theo khoản 2. Khi LiveLift chạy cho một nhà bán, nhà bán là **bên kiểm soát** (Điều 2 khoản 7), đơn vị vận hành là **bên xử lý** theo hợp đồng (khoản 8); mẫu thỏa thuận xử lý dữ liệu (Điều 37 khoản 2 điểm a) và căn cứ xử lý lượt nhấp của người bấm link đo **chưa có**, phải có trước phiên thật đầu tiên (Bảng 10).

<!-- DUYỆT: chọn A hoặc B. Đoạn dưới là PHƯƠNG ÁN A (giữ phần đã lọc định danh, xoá bản thô trước ngày nộp). Phương án B (xoá toàn bộ tập 16 buổi) và bảng kiểm kê ngày 25/09: scratchpad wf3/phuong-an-3-3.md. Chọn A: làm xong các bước xoá, che trước 30/09 rồi điền ngày làm thật vào ô trống (tối 25/09 câu hứa "Trước 30/09" đã đổi thành ô trống để bộ dựng chặn bản nộp cho tới khi làm thật; ngoài câu đó đoạn A giữ nguyên chờ duyệt). Hội đồng thử 25/09 cho rằng căn cứ "Điều 2 khoản 1" không đứng được vì câu nguyên văn vẫn tra ngược được người viết (định nghĩa khử nhận dạng ở Điều 2 khoản 11); lượt sửa 2 tối 25/09 đã thay câu căn cứ đó bằng đoạn của giám khảo đạo đức–pháp lý (không coi phần còn giữ là đã khử nhận dạng, bảo vệ như dữ liệu cá nhân) — việc chọn A hay B vẫn chờ trưởng nhóm. Chọn B: thay đoạn dưới bằng đoạn B và sửa các câu mục 6, 8, 9 theo tệp đó. -->
**Lưu và xóa tập 16 buổi.** Bản đầy đủ 19.126 bình luận không được lưu thành tệp sau lần chạy 10/09; chỉ còn giữ, đã lọc định danh và lưu cục bộ, 6.586 bình luận của 1 buổi và 393 bình luận của 3 buổi dùng cho mục 8–9. Kiểm kê ngày 25/09 còn thấy định danh ở ba nơi ngoài kho mã: bản sao lưu dữ liệu gán nhãn trước khi lọc lại (33 tên tài khoản), 16 dòng có tên dính liền (đã lọc, mục 3.2), và bản lưu nhật ký gốc của công cụ AI (kết quả công cụ có trích bình luận còn tên tài khoản). Prompt Log đã xuất lại; quét bộ lọc và đối chiếu băm độc lập đều ra 0. Ngày ⬜/09/2026 nhóm đã xóa bản sao lưu và che tên tài khoản người bình luận trong bản lưu nhật ký gốc. Nhóm không coi phần còn giữ là đã khử nhận dạng (Luật 91/2025/QH15 Điều 2 khoản 11): câu nguyên văn vẫn tra ngược được người viết qua bản phát lại công khai, và bộ lọc bằng biểu thức chính quy không bảo đảm bắt hết. Vì vậy phần này được bảo vệ như dữ liệu cá nhân, chỉ dùng để kiểm lại mục 8–9, không cung cấp thêm cho ai, và bị xóa khi có tập thay thế qua API chính thức, chậm nhất 22/11/2026, hoặc ngay khi Ban Tổ chức hay cơ quan có thẩm quyền yêu cầu. Bình luận và lượt nhấp trong kho chưa có thời hạn xóa tự động; bản sao lưu cơ sở dữ liệu tự xóa sau 14 ngày.

**Đường chuyển sang API chính thức.** Từ 17/09/2026 nhóm dừng thu mới từ kênh không thuộc nhóm hay đối tác. Hai đường yt-dlp còn trong mã (kể cả tùy chọn đọc cookie trình duyệt để vượt kiểm tra chống robot) và bộ thu TikTok dùng thư viện dịch ngược (`collectors/tiktok_public`, cách ly khỏi lõi) chỉ giữ tạm tới khi khóa chính thức chạy được. Phiên thí nghiệm và tập đánh giá mới chỉ lấy qua API chính thức, trên kênh của nhóm hoặc nhà bán đối tác có văn bản đồng ý.

# 4. Quy trình tiền xử lý, làm sạch, chuẩn hóa hoặc tổ chức dữ liệu

1. **Lựa chọn dữ liệu.** 17 video chọn theo quy trình ghi sẵn trong `docs/benchmarks/live-fire-da-nguon.md`, 16 nạp được; buổi dưới 30 bình luận không dùng cho kết luận nào. Tập kiểm tra NLP rút tất định từ 3 buổi: 193 dòng theo lớp mà mô hình cũ dự đoán (để đo precision) và 200 dòng ngẫu nhiên (để ước tỷ lệ nền).
2. **Lọc định danh** trước mọi bước khác, kể cả ghi nhật ký (mục 3.2): đặt sau khâu lưu thì dữ liệu thô vẫn tồn tại trên đĩa.
3. **Khử trùng tất định:** khóa `(platform, ext_id)` cho bình luận, mã đơn cho đơn hàng; lô huấn luyện loại thêm 1.246 dòng trùng. Nhờ vậy chạy lại một buổi sau hai ngày cho trùng từng con số.
4. **Gắn khối** theo lịch đã khóa (Hình 1): bình luận theo giờ nền tảng, lượt nhấp theo giờ máy chủ, đơn theo thời điểm đặt; đơn ngoài khung giờ phiên bị từ chối và đếm riêng. Phiên phân tích VOD không có lịch gán nên không vào được phân tích nhân quả.
5. **Chuẩn hóa cho mô hình**, chỉ ở nhánh NLP: NFKC, gom ký tự kéo dài, tách emoji, giãn teencode, không tự thêm dấu. Đo ngày 25/09, bỏ bước này không làm giảm macro-F1 (mục 9.4).
6. **Tổ chức để phân tích:** đơn vị là khối, cụm là phiên; hai bảng `assignment_event` (gán) và `exposure_event` (phơi nhiễm thực tế) đối chiếu “định làm gì” với “đã làm gì”, là nền cho ước lượng LATE.

**Dữ liệu sai lệch** được gắn cờ, không xóa: lượt nhấp vi phạm một trong 5 quy tắc dựa trên hướng dẫn đo lượt nhấp của IAB và MRC [9] (robot, tải trước, không phải GET, nhấp lại trong 10 giây, quá 5 lượt mỗi thiết bị mỗi khối) vẫn nằm trong chuỗi thô và được báo song song. Bình luận mô phỏng bị chặn khỏi lô gán nhãn.

# 5. Thuật toán, mô hình, phương pháp hoặc công cụ trí tuệ nhân tạo được sử dụng

Phần suy luận nhân quả là thống kê, không học máy. Phần AI nằm ở bộ phân loại ý định (học có giám sát), khâu gán nhãn bằng mô hình ngôn ngữ lớn, và công cụ lập trình có AI hỗ trợ (mục 5.4).

## 5.1 Lõi A — Thiết kế thí nghiệm và suy luận nhân quả

: Bảng 3. Thành phần của lõi thiết kế và suy luận

| Thành phần | Phương pháp | Trạng thái trong mã |
|---|---|---|
| Thiết kế | Switchback, khối 5 phút, khối đầu và cuối dài gấp đôi (thiết kế tối ưu [1]) | Đang chạy |
| Gán ngẫu nhiên | Bernoulli(0,5), bốc lại tới khi mỗi nhánh có ≥2 khối trong mỗi phần ba phiên; biên khối lệch ±30 giây | Đang chạy (bảo đảm từ 90 phút) |
| Hiệu ứng lưu | Khi phân tích bỏ 60 giây đầu mỗi khối [2]; độ nhạy 0, 2, 3 phút | Đang chạy |
| Kiểm định chính | RI với thống kê chuẩn hóa, KTC Fisher bằng nghịch đảo kiểm định [3] | Nguồn duy nhất của ước lượng, p và KTC trong báo cáo |
| Chọn sản phẩm trong khối BẬT | Hậu nghiệm Gamma–Poisson của tỷ lệ nhấp (tối đa 3 sản phẩm); khoảng chồng lấn với sản phẩm đứng đầu thì bốc đều, ghi xác suất 1/k | Chạy ở chế độ Tự ghim; xác suất được lưu, chưa vào báo cáo |

RI chỉ dựa vào cơ chế gán đã biết nên chính xác ở mẫu nhỏ, không cần giả định phân phối, cho giả thuyết “không khối nào bị tác động” [3]; KTC Fisher thêm giả định tác động cộng như nhau ở mọi khối, nên độ phủ phải kiểm bằng mô phỏng (mục 7.1). Phân phối tham chiếu dựng bằng cách bốc lại qua đúng hàm gán đang chạy, kể cả điều kiện bốc lại, với tham số đã lưu của phiên (`design_hash`, mục 5.3). Thẻ ghim có thể giữ chân hay đuổi người xem, nên báo cáo kiểm định cả mẫu số giây·người xem và gắn cờ khi lệch (`PREREGISTRATION.md` §5e).

## 5.2 Lõi B — Xử lý ngôn ngữ tự nhiên tiếng Việt

**Lọc PII** dùng luật, từ điển địa danh, chuẩn hóa NFKC và ký tự keycap, chạy tại cổng nạp (mục 3.2). **Phân loại ý định** dùng TF-IDF n-gram ký tự và từ + hồi quy logistic: bản **v1** (mặc định; 6 lớp, học trên 320 câu mẫu do AI soạn) đạt macro-F1 0,211 trên chat thật; bản **v2** (11 lớp, thêm 9 đặc trưng hình thức như tỷ lệ chữ hoa, ký hiệu giá) đạt 0,542 khi chưa áp ngưỡng (mục 9.3) và chỉ bật bằng `LIVELIFT_INTENT_MODEL=v2`. Khi xác suất dự đoán cao nhất dưới ngưỡng 0,45, cả hai trả nhãn “khác”. Nhãn ý định **không đi vào phân tích nhân quả**; chúng chỉ hiện trên bàn trợ live để người trợ live thấy khách đang hỏi gì.

## 5.3 Lõi C — Ba cơ chế liêm chính thực thi bằng mã

1. **Cam kết thiết kế trước giờ phát.** Lịch gán là hàm tất định của (tham số thiết kế, seed); hệ thống băm cặp đó thành `design_hash` (SHA-256) và lưu cùng lịch trước khi lên sóng, nên ai có tệp thiết kế cũng kiểm lại được lịch không bị sửa. Phiên chưa có lịch thì API từ chối phát sóng (HTTP 409). Kế hoạch phân tích `PREREGISTRATION.md` **chưa khóa**; sẽ khóa bằng một commit trước phiên thí nghiệm khẳng định đầu tiên.
2. **Khóa kết quả theo thời gian.** Khi đặt `RESULTS_FREEZE_UNTIL`, trước mốc đó bản tổng hợp và trang kết quả không trả ước lượng, p, KTC của phiên thật, kể cả cho nhóm. Mặc định biến này để trống, và đường `/sessions/{id}/report` còn trả chênh lệch trung bình của phiên thật trong lúc khóa — lỗi phải đóng trước phiên thật đầu tiên.
3. **Làm mù người dẫn, một phần.** Màn `/host` chỉ nhận 4 trường (thời gian đã phát, sản phẩm đang ghim, giá, tồn kho), không có lịch, khối hay nhánh (mô hình dữ liệu cấm trường thừa; kiểm thử `test_case_8`). Nhưng người dẫn vẫn thấy sản phẩm đang ghim, mà ở chế độ Tự ghim lệnh ghim chỉ đến trong khối BẬT, nên có thể đoán nhánh: phép so là giữa chiến lược ghim của LiveLift và cách làm thường lệ của đội, tính cả phản ứng của người dẫn (`PREREGISTRATION.md` §1).

## 5.4 Công cụ AI dùng trong quá trình phát triển

Nhóm dùng Claude Code (Anthropic) suốt quá trình phát triển; ngày 21/09/2026 một thành viên dùng thêm OpenAI Codex và Google Antigravity. **Gần như toàn bộ mã, kiểm thử, sổ sự cố và bản nháp tài liệu do Claude viết**; đội đặt bài toán, ra yêu cầu, chọn phương án, duyệt, vận hành và chịu trách nhiệm. Phân định chi tiết nằm trong **Bản kê khai** nộp kèm; lịch sử câu lệnh ở mục 13.

# 6. Quy trình huấn luyện, tinh chỉnh, tích hợp hoặc khai thác mô hình

**Chống rò rỉ.** Tập kiểm tra tách theo buổi live (LOSO); vì cùng một câu chào hay bảng giá lặp lại ở nhiều buổi, trước mỗi lần huấn luyện khung đánh giá còn loại mọi dòng huấn luyện trùng khít văn bản với tập kiểm tra (62 dòng).

1. **Dựng khung đánh giá trước khi sửa mô hình:** 4 baseline (Bảng 7), LOSO, KTC bootstrap 2.000 lần, macro-F1 từng buổi.
2. **Xây lại bộ nhãn 6 → 11 lớp:** trên 200 bình luận rút ngẫu nhiên, 40% là xã giao, loại không có chỗ trong bộ nhãn cũ (`nlp/labels.py`).
3. **Gán nhãn, cả ba nguồn đều do AI tạo:** 393 dòng kiểm tra do một tác tử Claude gán ngày 09/09 trên bảng xáo trộn; 320 câu mẫu do Claude soạn ngày 01/09; 1.800 nhãn huấn luyện do Claude gán. Nhóm quyết định bộ nhãn và cách rút mẫu (có seed), rà soát quy trình nhưng không duyệt từng nhãn. Mọi con số ở mục 8–9 vì vậy đo **mức đồng thuận với nhãn tham chiếu do AI gán**, chưa phải độ chính xác so với con người. Gán lại bằng hai thành viên độc lập rồi đo κ **chưa làm** (mục 12).
4. **Huấn luyện:** TF-IDF n-gram + hồi quy logistic, cân bằng lớp, seed 2026; số công bố đo bằng LOSO, còn tệp mô hình v2 (cấu hình chốt 14/09) học trên toàn bộ 2.513 dòng, kể cả 393 dòng kiểm tra, và được đóng gói lại ngày 25/09 trên dữ liệu đã lọc lại (mục 3.2).

**Tích hợp vào sản phẩm.** Bộ phân loại chạy tại cổng nạp ngay sau bước lọc PII; mặc định là **v1**, **v2** bật bằng biến môi trường (mục 5.2). Khi nạp, mô hình phải trả lời đúng một lần dự đoán thử; lỗi (tệp hỏng, lệch phiên bản scikit-learn) thì hệ thống chuyển hẳn sang bộ từ khóa, `/health` báo `keyword_fallback` kèm lý do. Dự án ghim đúng scikit-learn 1.9.0 của tệp mô hình: với ràng buộc cũ (<1.8), 393/393 bình luận từng âm thầm rơi về bộ từ khóa.

**Tái lập.** Bảng ở mục 9.3–9.4 sinh bằng `python -m livelift.nlp.eval_intent --ablation --coverage`; nhãn tham chiếu và dự đoán từng dòng (không kèm văn bản) nằm trong `docs/benchmarks/intent-eval/results.json`, đủ để tính lại Bảng 7–8. Văn bản bình luận không nằm trong kho mã và không được cung cấp cho người khác vì người bình luận chưa đồng ý (mục 3.3).

# 7. Chỉ số, phương pháp hoặc tiêu chí đánh giá kết quả

**Chỉ số của sản phẩm.** Biến kết quả chính của một phiên thí nghiệm là số lượt nhấp hợp lệ trên 1.000 giây·người xem của từng khối, sau burn-in (`PREREGISTRATION.md` §4.1). Kết luận rơi vào đúng một trong bốn trạng thái (`analysis/narrate.py`): **dương** (KTC 95% nằm hẳn trên 0), **âm** (nằm hẳn dưới 0), **chưa phát hiện tác động** (KTC chứa 0), **chưa đủ điều kiện** (thiếu khối hoặc đang khóa). Hệ thống được đánh giá ở ba tầng độc lập.

## 7.1 Tầng 1 — Bộ ước lượng có đúng không

: Bảng 4. Kiểm chứng bộ ước lượng trên mô phỏng có đáp án

| Chỉ số | Tiêu chí đạt (cổng kiểm thử) | Kết quả | Nguồn |
|---|---|---|---|
| Bác bỏ A/A, 200 lần lặp | nhị thức hai phía, H0 = 5%, p ≥ 0,01 | 3,50% (7/200), KTC [1,4%; 7,1%], p 0,4168 | `so-hieu-chuan.json`, đo lại 25/09, khớp |
| Độ phủ KTC 95% (A/A) | đối ngẫu với dòng trên (193 = 200 − 7), không độc lập | 96,50% (193/200) | như trên |
| Thu hồi tác động biết trước, 40 lần | lệch dưới 10% tác động; phủ qua kiểm định nhị thức | lệch −0,84%; phủ 92,50% (37/40), KTC [79,6%; 98,4%] | như trên |

Bảng 4 sinh lại bằng `scripts/do_lai_so_hieu_chuan.py --kiem`, lệnh báo đỏ khi số đo lại lệch số đã ghi; A/A chạy 6 phiên 60 phút mỗi lần lặp, thu hồi chạy 8 phiên 90 phút, và số lần lặp còn ít nên KTC của chính các tỷ lệ này rộng (Hình 2).

Hình 3 là kết quả bất lợi: khi tác động kéo sang khối sau (thời gian bán rã 0, 120, 180 giây), độ phủ KTC còn 96%, 76%, 57% (n = 75 mỗi mức) và ước lượng bị kéo về 0 khoảng 21–32%: với dạng lưu cùng chiều đã mô phỏng, hệ thống đánh giá thấp chứ không phóng đại; dạng khách chỉ mua sớm hơn chứ không mua thêm chưa được mô phỏng và có thể làm ước lượng phóng đại. Cổng kiểm thử chỉ đòi ở 120 s không đổi dấu và phủ ≥60%. Đây là điều kiện sử dụng, và là lý do độ dài khối chỉ chốt sau khi đo thời gian tắt dần trên phiên thăm dò.

## 7.2 Tầng 2 — Mô hình AI

- macro-F1, F1 từng lớp, ma trận nhầm lẫn, KTC bootstrap theo dòng 2.000 lần; số từng buổi và trên 200 dòng rút ngẫu nhiên, vì bất định thật nằm ở cấp buổi.
- **Precision và recall nhãn hành động** (hỏi giá, hỏi size, chê đắt, chốt đơn, vận chuyển), KTC Wilson: báo “có khách muốn mua” thì đúng bao nhiêu, và bắt được bao nhiêu khách thật sự muốn mua.
- **Tiêu chí đạt:** vượt cả bốn baseline; KTC không chồng lấn với bản đang chạy; vượt ở từng buổi; số trên câu mẫu luôn đi cùng số trên chat thật.

![Hình 2. Hiệu chuẩn A/A và thu hồi tác động (mô phỏng), kèm KTC của chính các tỷ lệ.](hinh/h3-hieu-chuan-aa.png){width=16cm}

![Hình 3. Độ phủ KTC 95% và độ lệch khi tác động kéo sang khối sau (3 seed × 25 lần lặp mỗi mức).](hinh/h5-luu-hieu-ung.png){width=16cm}

## 7.3 Tầng 3 — Hệ thống có chạy được không

: Bảng 5. Chỉ số vận hành

| Chỉ số | Kết quả | Nguồn |
|---|---|---|
| Kiểm thử tự động | 2.093 = 2.066 nhanh + 17 cổng chậm + 10 trình duyệt; chạy 25/09: 2.091 đạt, 2 bỏ qua, 0 lỗi | `dong_bo_so_test.py` |
| Sự cố có phân tích nguyên nhân gốc | 109 | `docs/incident-log.md` |
| Tốc độ nạp | 835–923 bình luận/giây (một tiến trình, kho bộ nhớ, không tính thời gian tải về) | chạy toàn tuyến 10/09 (mục 8.1) |

# 8. Kết quả thử nghiệm, phân tích ưu điểm, hạn chế và khả năng mở rộng

Mọi kết quả trong mục này là **quan sát hoặc mô phỏng**; chưa có phiên thí nghiệm ngẫu nhiên thật nào (MT3).

## 8.1 Chạy toàn tuyến trên dữ liệu thật

Ngày 10/09/2026 nhóm chạy toàn bộ đường ống trên 19.126 bình luận của 16 buổi phát lại (tải bằng yt-dlp, mục 3.3). Buổi lớn nhất 117 phút, 6.586 bình luận: tải 69 giây, xử lý 8 giây. Nạp, khử PII, khử trùng, cô lập phiên và tính tất định đều đạt.

Sau đợt hoàn thiện 17–18/09, một phiên chạy trọn không cần thao tác kỹ thuật: bộ thu chạy nền bật bằng một nút, nguồn mô phỏng để tập dượt (bị từ chối trên phiên thật), nhập đơn từ CSV. Bộ nối Shopee Live, TikTok Shop và công cụ kiểm tra khóa YouTube có kiểm thử nhưng **chưa chạy với khóa thật**. Thử 25/09 trên bản build: phiên chạy thử nhận đủ 200/200 bình luận mô phỏng, che 10/10 câu có dữ liệu cá nhân giả.

## 8.2 Kết quả tự bác bỏ

Cùng đợt đo đó bác bỏ tuyên bố của nhóm về mô hình ý định: macro-F1 0,870 trên 320 câu mẫu do AI soạn (kiểm chứng chéo 5 phần) nhưng 0,211 trên chat thật; tỷ lệ đúng 0,338 còn thấp hơn cách luôn đoán lớp đa số (0,389). Ba cơ chế sai: bộ nhãn thiếu lớp (40% bình luận là xã giao); đa nghĩa tiếng Việt (“đắt” là chê giá hay “bán đắt hàng”); không phân biệt người nói (bảng giá shop tự dán bị đọc thành khách hỏi giá). Tỷ lệ nền ý định mua mỗi buổi rất khác nhau — 0% (0/72), 6,8% (7/103), 48,0% (12/25) — nên không có một con số độ chính xác duy nhất để công bố.

## 8.3 Kết quả sau cải tiến

macro-F1 tăng từ 0,211 lên 0,542, KTC hai bản không chồng lấn, bản mới tốt hơn ở cả ba buổi (Bảng 7). Precision nhãn hành động tăng từ 23,0% lên 65,5%, nhưng **recall giảm từ 78,3% xuống 55,1%**: bản cũ báo “có khách muốn mua” nhiều và bắt được nhiều hơn, bản mới báo ít hơn và đúng hơn. Tổng cảnh báo giảm từ 235 xuống 58, trong đó cảnh báo sai giảm từ 181 xuống 20. Ở buổi gần như không có ý định mua (1/147 dòng), bản mới vẫn phát 11 cảnh báo và sai cả 11; bản cũ phát 88, sai 87.

Hai đính chính: con số 0,271 từng ghi trong README **không tái lập được** (tệp nhãn 08/09 không được lưu), nên số “trước cải tiến” chính thức là 0,211; số 0,565 ngày 14/09 đo **trước** khi lọc lại tên tài khoản, đo lại 25/09 được 0,542, hai KTC chồng lấn gần hết.

## 8.4 Ưu điểm

Số hiệu chuẩn sinh lại được bằng lệnh, số NLP tính lại được từ dự đoán từng dòng (mục 6); cam kết liêm chính nằm trong mã (mục 5.3). Hệ thống mới chạy trên máy cá nhân (mục 10.2); mô hình ý định dưới 1 MB, không cần GPU.

## 8.5 Hạn chế

- **0 phiên thí nghiệm ngẫu nhiên thật**; mọi bằng chứng nhân quả là mô phỏng. **Chưa có khóa API chính thức nào**; độ trễ trên đường chính thức chưa đo.
- **Lực thống kê** (Hình 4, mục 2.3): MDE lượt nhấp 16,4% ở ~59 người xem, 8 phiên, tính từ CV mô phỏng, sát sàn Poisson 16,0% nên là mức lạc quan; với đơn hàng, ở 15 người xem và 18 phiên, MDE là 179–327% (`docs/benchmarks/order-mde.md`) nên đơn hàng chỉ là biến phụ.
- **Mô hình ý định chưa đủ để ra quyết định:** nhãn tham chiếu do AI gán; 3 buổi kiểm tra, 2 buổi cùng hệ thống cửa hàng với buổi huấn luyện, 51/69 dòng hành động đến từ một buổi, nên 0,542 nhiều khả năng lạc quan với nhà bán mới.
- **Đơn hàng** chỉ nhập được bằng CSV sau buổi, báo cáo hiện chỉ đếm số đơn. **TikTok Shop:** không có bình luận qua API chính thức (mục 8.6). **Phiên đấu giá:** chat toàn chữ số, bộ phân loại không đọc được.

![Hình 4. MDE của lượt nhấp (cận dưới Poisson) theo số người xem và số phiên, với hai giả định tỷ lệ nhấp; vùng 5–15 người xem là ước tính từ CPM, chưa đo; điểm 16,4% tính bằng công thức từ CV đo trên 8 phiên mô phỏng.](hinh/h4-mde.png){width=16cm}

## 8.6 Khả năng mở rộng

Chi phí phân tích tăng theo số khối, chi phí nạp tăng theo số bình luận; thêm một nền tảng là thêm một bộ nối. Giới hạn đã biết: hạn mức YouTube Data API mặc định 10.000 đơn vị/ngày; một buổi 90 phút tốn khoảng 2.900 đơn vị nếu mỗi lượt đọc chat tính 1 đơn vị như bảng giá chính thức, nhưng vượt hạn mức nếu tính 5 đơn vị như một dự án nguồn mở ghi nhận (chưa đo); bộ thu chỉ an toàn với một tiến trình. Hướng mở rộng gần nhất là TikTok Shop: API chính thức chỉ trả số liệu theo phút sau phiên, cho tài khoản chính thức của shop; bộ nối đã gộp số đó về khối, có kiểm thử, nhưng chưa nối vào bộ thu, chưa chạy với shop thật, và GMV theo phút là số quy đổi nên chỉ làm biến phụ.

# 9. So sánh với phương án cơ sở và phân tích đóng góp của các thành phần

## 9.1 So với các nhóm giải pháp hiện có

Công cụ phân tích livestream trả lời “bán được bao nhiêu”, nền tảng thí nghiệm chuyên nghiệp trả lời “bao nhiêu là do bạn” nhưng đòi sở hữu nền tảng (mục 1.2); LiveLift nhắm vào ô trống giữa hai nhóm, và năng lực đó mới được kiểm chứng trên mô phỏng.

## 9.2 So sánh phương án ước lượng

: Bảng 6. Các phương án ước lượng và trạng thái kiểm chứng

| Phương án | Vai trò | Trạng thái kiểm chứng |
|---|---|---|
| RI + KTC Fisher | Chính | Đạt mọi cổng A/A và thu hồi ở Bảng 4 |
| Hiệu hai trung bình / Hájek | — | Trùng nhau về đại số khi xác suất gán không đổi; đã gỡ khỏi báo cáo |
| OLS FE + Lin, KTC chuẩn cụm | Phụ | Có kiểm thử đúng hướng; **chưa đo độ phủ bằng mô phỏng** |
| RI + CUPED đa biến | Độ nhạy | Có cổng A/A với ngưỡng lỏng (20%); chưa hiệu chuẩn chính thức |

Lý do lấy RI làm kết luận chính: với ít phiên, KTC dựa trên sai số chuẩn cụm hụt độ phủ — Pankratev [4] (phần 3.2.1) ghi nhận với 10 cụm trở xuống, KTC của cả bốn phương pháp được so chỉ chứa giá trị thật khoảng 82% số lần thay vì 95%.

## 9.3 So sánh với baseline trên chat thật

: Bảng 7. Phân loại ý định trên 393 bình luận thật (LOSO theo buổi, nhãn tham chiếu do tác tử AI gán, đo 25/09/2026)

| Hệ thống | macro-F1 [KTC 95%] | Tỷ lệ đúng | Precision hành động | Recall hành động |
|---|---|---:|---:|---:|
| B0 · luôn đoán lớp đa số | 0,056 [0,051; 0,063] | 0,389 | — | 0% (0/69) |
| B1 · từ khóa (tiền đăng ký) | 0,146 [0,109; 0,180] | 0,387 | 20,9% (18/86) | 26,1% |
| B2 · **v1 đang chạy** | **0,211** [0,172; 0,247] | 0,338 | 23,0% (54/235) | 78,3% |
| B3 · cùng kiến trúc, học lại trên câu mẫu | 0,199 [0,163; 0,234] | 0,303 | 21,9% (57/260) | 82,6% |
| C1 · 11 lớp, thêm nhãn 2 buổi còn lại | 0,563 [0,491; 0,621] | 0,611 | 47,2% (43/91) | 62,3% |
| C2 · C1 + 1.800 nhãn LLM (**v2**) | **0,542** [0,478; 0,625] | 0,730 | 65,5% (38/58) | 55,1% |

C2 tốt hơn B2 ở cả ba buổi (macro-F1 0,064 / 0,412 / 0,138 lên 0,368 / 0,599 / 0,525; KTC ở Hình 5b). Thang 11 lớp có bốn lớp mà B2 không thể đoán (171/393 dòng), nên một phần mức tăng đến từ bộ nhãn mới: chấm cùng thang 6 lớp cũ, B2 đạt 0,370 [0,306; 0,432], C2 đạt 0,572 [0,471; 0,667], KTC vẫn không chồng lấn (Bảng 8). 193 dòng được rút theo nhãn bản cũ dự đoán nên số trên 393 dòng không phải con số vận hành; trên riêng 200 dòng rút ngẫu nhiên, macro-F1 là 0,208 → 0,516, precision hành động 21,4% (9/42) → 66,7% (6/9, KTC 35–88%), recall 47,4% (9/19) → 31,6% (6/19). B2 chấm với ngưỡng 0,45 như sản phẩm, C2 thì không; cùng ngưỡng, v2 cho macro-F1 0,523, precision 73,9%.

![Hình 5. (a) Ma trận nhầm lẫn của v2 (C2), chuẩn hóa theo hàng; (b) macro-F1 và KTC 95% của các hệ thống ở Bảng 7 và C3, A4 ở Bảng 8; nhãn tham chiếu do tác tử AI gán.](hinh/h6-nlp.png){width=16cm}

## 9.4 Ablation — đóng góp của từng thành phần

: Bảng 8. Bỏ lần lượt từng thành phần khỏi bản đầy đủ (C2), đo 25/09/2026

| Cấu hình | macro-F1 [KTC 95%] | Chênh với bản đầy đủ |
|---|---|---:|
| Bản đầy đủ (C2) | **0,542** [0,478; 0,625] | — |
| A4 · − bộ 320 câu mẫu | 0,362 [0,317; 0,423] | **−0,180** |
| − 1.800 nhãn LLM | 0,563 [0,491; 0,621] | +0,021 |
| − chuẩn hóa văn bản | 0,559 [0,488; 0,643] | +0,017 |
| − đặc trưng “ai đang nói” | 0,576 [0,513; 0,682] | +0,034 |
| − nhãn AI của 2 buổi còn lại | 0,580 [0,504; 0,666] | +0,038 |
| + tự chọn ngưỡng từ chối theo tập huấn luyện (C3) | 0,493 [0,441; 0,562] | −0,049 |
| Cùng thang 6 lớp: v1 đang chạy (B2) · học lại 6 lớp · C2 gộp về 6 | 0,370 · 0,579 · 0,572 | — |

**Đọc bảng.** Chỉ bộ 320 câu mẫu có đóng góp rõ (−0,180, KTC không chồng lấn): lô nhãn LLM chỉ có 5 dòng nhãn hành động trên 1.800, nên thiếu câu mẫu là thiếu gần hết ví dụ mua hàng. Nhãn LLM nâng precision từ 47,2% lên 65,5%; chênh macro-F1 +0,021 đổi dấu thành −0,034 khi chỉ chấm 10 lớp có trong nhãn tham chiếu, nên chưa kết luận được. Các dòng còn lại lệch dưới 0,05 với KTC chồng lấn: với 3 buổi kiểm tra, không kết luận được thành phần nào có hại hay có ích.

**Vì sao vẫn giữ bản đầy đủ.** Cấu hình v2 chốt ngày 14/09; chọn lại theo điểm trên chính tập kiểm tra là khớp quá mức. Baseline transformer (ViSoBERT, PhoBERT) chưa chạy: đây là so sánh còn thiếu. Claude không dùng làm baseline được vì chính nó gán nhãn tham chiếu; cũng vì thế, precision tăng nhờ 1.800 nhãn LLM có thể một phần do mô hình học theo cách gán của Claude.

# 10. Kiến trúc hệ thống và phương án triển khai

**Thành phần:** API FastAPI (Python 3.11), giao diện Next.js 14, PostgreSQL 16 (9 migration), Redis, Caddy làm cổng HTTPS, tác vụ sao lưu hằng ngày; đóng gói bằng Docker Compose (7 dịch vụ). Giao diện: `/chay-phien` (bốc lịch, bật bộ thu), `/desk` (trợ live), `/host` (người dẫn), `/ket-qua`, `/bao-cao` (Hình 7).

**Ba cổng chặn** (Hình 6): bình luận không qua bộ khử PII thì không có đường nào ghi xuống kho; phiên chưa có lịch gán thì không phát sóng được (HTTP 409); khóa kết quả chỉ có hiệu lực khi đặt `RESULTS_FREEZE_UNTIL` (mục 5.3). Cùng với `INGEST_TOKEN`, đó là điều kiện bắt buộc trước khi mở bản công khai.

![Hình 6. Kiến trúc, luồng dữ liệu và ba cổng chặn (tô đỏ): lọc PII trước khi ghi, HTTP 409 khi chưa có lịch, khóa kết quả.](hinh/h2-kien-truc.png){width=16cm}

## 10.1 Phương án triển khai và lý do chọn

Vòng chung kết đòi sản phẩm chạy ổn định ít nhất 48 giờ, nên các gói miễn phí tự ngủ đông khi không có truy cập bị loại. Dự kiến dùng **Oracle Cloud Always Free** (Singapore, 2 OCPU / 12 GB RAM, 0 đồng), dự phòng **Vultr** trả theo thời gian dùng (khoảng 17.000 đồng cho 48 giờ). Lớp phủ `docker-compose.prod.yml` khai báo toàn bộ hệ thống cho một lệnh `docker compose … up -d` (chưa chạy trọn, mục 10.2), có trần bộ nhớ, healthcheck, sao lưu hằng ngày giữ 14 ngày.

## 10.2 Khả năng duy trì — đã kiểm và chưa kiểm

- **Đã kiểm (14/09):** 5/5 bản sao lưu qua kiểm tra toàn vẹn; khôi phục được sau khi buộc dừng tiến trình đột ngột; tắt API giữa chừng thì trang vẫn trả HTTP 200, không lộ vết ngăn xếp.
- **Đã kiểm (25/09):** quét 79 commit trên mọi nhánh: 0 khóa bí mật thật; tệp compose hợp lệ; luồng người bán lần đầu chạy trọn trên bản build.
- **Chưa kiểm:** `docker compose up` trọn vẹn (hệ thống đang chạy bằng `scripts/chay_local.py`). **Chưa có địa chỉ demo công khai** tại ngày 25/09/2026 (mốc ở mục 12).

![Hình 7. Giao diện chụp tự động ngày 25/09/2026: (a) bốc lịch BẬT/TẮT trước giờ phát; (b) bàn trợ live, bình luận mô phỏng đã che dữ liệu cá nhân; (c) màn người dẫn không thấy khối; (d) kết quả trên dữ liệu mẫu, gắn nhãn DEMO.](hinh/h7-giao-dien.png){width=16cm}

# 11. Phân tích rủi ro, yêu cầu bảo mật, đạo đức trí tuệ nhân tạo và an toàn dữ liệu

## 11.1 Rủi ro và biện pháp

: Bảng 9. Rủi ro, biện pháp đã có và phần còn thiếu

| Rủi ro | Biện pháp đã có | Còn thiếu |
|---|---|---|
| Lộ dữ liệu cá nhân người xem | Khử PII trước khi ghi; cổng recall; không lưu định danh người bình luận | Xóa tự động; đầu mối nhận yêu cầu xem, xóa |
| Ít phiên, ít người xem nên kết luận sai | RI; luôn trả KTC; trạng thái “chưa đủ điều kiện” | Mô phỏng lực theo số người xem đo thật |
| Nhìn trước kết quả rồi dừng phiên | Khóa kết quả, cấu hình sai thì khóa luôn | Bắt buộc đặt mốc trên máy chạy thật; đóng đường `/report` |
| Nhà bán quyết định theo nhãn ý định sai | Nhãn không vào phân tích nhân quả; công bố cặp số câu mẫu và chat thật | Nhãn “chưa dùng cho quyết định” trên giao diện |
| Quên bật bảo vệ khi lên Internet | Cổng cấp ứng dụng; 6/19 route ghi đòi token | Bắt buộc `INGEST_TOKEN` (mặc định tắt) |
| Vi phạm điều khoản nền tảng | Bộ thu mặc định dùng API chính thức; dữ liệu VOD chỉ mang nhãn “quan sát” | Gỡ hai đường yt-dlp (kể cả tùy chọn cookie trình duyệt) và bộ thu TikTok không chính thức |

## 11.2 Khuôn khổ pháp lý và đạo đức AI

- **Luật Trí tuệ nhân tạo số 134/2025/QH15** [13] và **Nghị định 142/2026/NĐ-CP** [14]: nhà cung cấp tự phân loại hệ thống trước khi đưa vào sử dụng và chịu trách nhiệm về tính chính xác, trung thực của kết quả phân loại (NĐ 142 Điều 6 khoản 1), theo ba mức (Điều 6 khoản 3): **cao** nếu thuộc Danh mục do Thủ tướng ban hành; **trung bình** nếu có thể gây nhầm lẫn vì người dùng không nhận biết mình tương tác với AI hay nội dung do AI tạo (Điều 9 khoản 1); còn lại là **thấp**.
- **LiveLift có tự ra quyết định.** Ở chế độ mặc định **Tự ghim**, trong mỗi khối BẬT của lịch đã khóa, hệ thống tự chọn sản phẩm (tầng chọn sản phẩm ở Bảng 3, trong tối đa 3 sản phẩm của nhà bán) và ra lệnh ghim mà không chờ người bấm, qua đúng hàm của nút người trợ live, có nhật ký, hiện ngay trên màn người dẫn; thao tác ghim trên ứng dụng của nền tảng vẫn do người làm. Khối TẮT hệ thống không ra lệnh; người trợ live đã thao tác trong khối thì hệ thống để yên; nhà bán chọn được **Chỉ gợi ý**, khi đó không có lệnh nào nếu người không bấm.
- **Tự đánh giá sơ bộ, chưa có ý kiến chuyên gia pháp lý: mức thấp.** Không thuộc mức trung bình: người dùng là nhân sự nhà bán, biết mình dùng công cụ (Điều 9 khoản 1 điểm b), và hệ thống không cung cấp nội dung ra công chúng (Điều 9 khoản 3 điểm c); chưa đối chiếu được Danh mục rủi ro cao (Điều 7). Cần chuyên gia xem tiêu chí “mức độ tự động” và “khả năng giám sát, can thiệp của con người” (Điều 8 khoản 1 điểm a): Chỉ gợi ý cho người xem xét trước khi lệnh có hiệu lực (Điều 8 khoản 2 điểm b), Tự ghim chỉ cho can thiệp sau. Nhóm phân loại lại theo Điều 11 khoản 1 khi đổi chức năng hoặc khi Danh mục thay đổi.
- **Luật 91/2025/QH15** [11], **Nghị định 356/2025/NĐ-CP** [12]: vai trò, sự đồng ý, xử lý ở nước ngoài, thời hạn lưu ở mục 3.3; Điều 30 (xử lý bằng AI phải có xác thực, phân quyền) chạm các điểm còn mở ở mục 11.4. **Điều 5 Thể lệ** [16]: kê khai trong Bản kê khai nộp kèm.

## 11.3 Phương án kiểm soát đầu ra

Mỗi ràng buộc dưới đây nằm trong mã và có kiểm thử: (1) không đủ khối hoặc đang khóa thì báo cáo trả “chưa đủ điều kiện” thay vì con số; (2) số dự báo của mô hình không được kèm KTC (API từ chối); (3) buổi live của người khác (VOD) không có lịch gán nên chỉ mang nhãn “quan sát”; (4) thiếu tín hiệu (tim, quà, đơn hàng) thì ghi “thiếu”, không lặng lẽ ra số yếu; (5) nhãn dữ liệu mẫu/thật do máy chủ quyết định, phiên chạy thử và phiên mẫu không vào kết quả gộp thật; (6) dưới ngưỡng xác suất 0,45 bộ phân loại trả “khác”, nhãn ý định không vào phân tích nhân quả; (7) “Tự ghim” chỉ ra lệnh trong khối BẬT của lịch đã khóa (mục 11.2).

## 11.4 An toàn thông tin

Rà soát ngày 14/09 phát hiện 12/15 đường ghi khi đó không có xác thực. Cách sửa là **một cổng duy nhất ở cấp ứng dụng**: mọi route ghi phải khai báo mức bảo vệ, quên khai báo thì kiểm thử đỏ. Hiện 19 route ghi: 6 bắt buộc token, 13 còn lại khách thao tác được **nhưng chỉ trên dữ liệu mẫu** do máy chủ quyết định. Bí mật qua biến môi trường; HTTPS, header bảo mật, trang lỗi không lộ vết ngăn xếp.

**Còn mở:** xác thực chỉ bật khi đặt `INGEST_TOKEN`; WebSocket chưa kiểm nguồn gọi; chưa tách dữ liệu theo nhà bán; `npm audit` ngày 25/09 báo Next.js 14.2.32 có 2 lỗ hổng nghiêm trọng (thực thi mã từ xa, một lỗi chỉ trên máy chủ Windows), vá từ bản 15.5.24; nâng cấp xếp trước khi mở địa chỉ công khai (Bảng 10).

# 12. Hướng phát triển, hoàn thiện và khả năng ứng dụng trong thực tiễn

: Bảng 10. Lộ trình gắn với các vòng thi

| Mốc | Việc | Tiêu chí xong |
|---|---|---|
| Trước vòng Khu vực (10–11/10/2026) | Có khóa API YouTube, Page token; phát thử trên kênh nhóm; hai thành viên gán nhãn lại 393 dòng | Đo hạn mức thật; báo κ, đo lại mục 9.3 |
| Tháng 10–11/2026 | Tìm nhà bán đối tác (chưa có); trước phiên thật: thỏa thuận xử lý dữ liệu, căn cứ xử lý lượt nhấp, đóng đường lọt khóa kết quả; rồi phiên thăm dò → chốt độ dài khối → khóa `PREREGISTRATION.md` → phiên ngẫu nhiên thật | Tiến tới ≥18 phiên (MT3); công bố cả khi âm |
| Trước vòng Chung kết (20–22/11/2026) | Nâng Next.js; địa chỉ công khai ≥48 giờ; bắt buộc `INGEST_TOKEN`, `RESULTS_FREEZE_UNTIL` | `kiem_tra_truoc_demo.py` xanh, kiểm cả hai biến |
| Sau cuộc thi | Đăng nhập, tách dữ liệu theo nhà bán; kết nối nền tảng bằng OAuth | Nhiều nhà bán dùng chung máy chủ mà dữ liệu không lẫn |

**Khả năng ứng dụng.** Điều kiện tối thiểu để một nhà bán dùng thật: khóa API chính thức của kênh mình, hai người (người trợ live nắm lịch, người dẫn không biết trước lịch), lượng xem đủ cho mức tác động muốn phát hiện (Hình 4), và chấp nhận chạy nhiều phiên cho một câu hỏi (trên mô phỏng: 8 phiên 90 phút, khoảng 12 giờ phát, ở ~59 người xem cho MDE 16,4%). Thứ nhà bán nhận được là câu trả lời kèm KTC cho đúng hành động của mình, kể cả “chưa phát hiện tác động”; LiveLift không hứa tăng doanh số. **Duy trì:** mã nguồn mở AGPL-3.0, máy chủ từ 0 đồng (mục 10.1), nhưng hôm nay cần kỹ sư cài đặt; thu phí bản lưu trữ sẵn là **giả thuyết**, chưa hỏi nhà bán.

# 13. Lịch sử câu lệnh và hình ảnh minh chứng quá trình phát triển sản phẩm

**Kho mã nguồn (công khai):** https://github.com/bminhnemhoi/AISC2026_LIVEFIT, nhánh `main` tại commit ⬜ *điền sau khi hợp nhất và đẩy lên*; lịch sử commit thật, commit có AI hỗ trợ mang dòng khai báo đồng tác giả.

**Thư mục minh chứng (Google Drive, mở quyền xem cho mọi người có liên kết):** ⬜ *dán liên kết và thử mở bằng cửa sổ ẩn danh trước khi nộp*

- **Prompt Log:** hội thoại với Claude Code xuất từ nhật ký gốc (83 câu lệnh người gõ trong 5 phiên, 598 nhật ký tác tử con), kèm bảng băm SHA-256; đã che khóa bí mật và dữ liệu cá nhân, phần cắt bớt có đánh dấu. Ảnh chụp system prompt có ở 3/5 phiên; tệp chỉ dẫn `HARNESS.md` nộp kèm. Nhật ký Codex và Antigravity (21/09) do thành viên đã dùng tự xuất.
- **Minh chứng tiến trình:** mốc commit theo ngày sinh từ `git log`; ảnh giao diện bản hiện tại chụp tự động ngày 25/09/2026 (13 màn hình, ghi mã commit); ảnh các mốc trước chụp lại từ commit cũ ⬜ *đội bổ sung trước khi nộp*. **Tài liệu kỹ thuật:** tiền đăng ký, sổ sự cố, số hiệu chuẩn, kết quả NLP, báo cáo nạp dữ liệu.
- **Bản kê khai** công cụ AI, mô hình, dữ liệu, API, thư viện, mã kế thừa, có chữ ký ba thành viên.

# Tài liệu tham khảo

1. Bojinov, I., Simchi-Levi, D., Zhao, J. (2023). Design and Analysis of Switchback Experiments. *Management Science* 69(7), 3759–3777. doi:10.1287/mnsc.2022.4583.
2. Hu, Y., Wager, S. (2022). Switchback Experiments under Geometric Mixing. arXiv:2209.00197.
3. Liu, J., Zhong, L. (2026). Randomization Tests in Switchback Experiments. arXiv:2602.23257.
4. Pankratev, S. (2026). Design-Aware Variance Reduction for Switchback Experiments: A Comparative Study. arXiv:2606.27662.
5. Xie, Sharma, Mehra (2025). Designing E-commerce Livestreams: How Product Presentation Duration Affects Sales? *Production and Operations Management* 34(12). doi:10.1177/10591478251314455.
6. Wang và cs. (2025). Artificial Intelligence (AI) Assistant in Online Shopping: A Randomized Field Experiment on a Livestream Selling Platform. *Information Systems Research* 36(4). doi:10.1287/isre.2023.0103.
7. He, Y., Huang, N., Wang, L., Sun, Y. (2025). Real-Time Sales Data, Streamer Improvisation, and Sales Performance: Evidence From Live Stream Selling. *MIS Quarterly* 49(4), 1567–1594.
8. Qu và cs. (2026). KuaiLive: A Real-time Interactive Dataset for Live Streaming Recommendation. SIGIR 2026. arXiv:2508.05633.
9. Interactive Advertising Bureau, Media Rating Council (2009). Click Measurement Guidelines v1.0.
10. VnEconomy (18/11/2024), dẫn AccessTrade: vneconomy.vn/bung-no-xu-huong-tieu-dung-livestream.htm.
11. Quốc hội (2025). Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15, thông qua 26/6/2025, hiệu lực 01/01/2026 (Công báo số 971+972 ngày 24/7/2025).
12. Chính phủ (2025). Nghị định số 356/2025/NĐ-CP ngày 31/12/2025 hướng dẫn Luật Bảo vệ dữ liệu cá nhân.
13. Quốc hội (2025). Luật Trí tuệ nhân tạo số 134/2025/QH15, thông qua 10/12/2025, hiệu lực 01/3/2026.
14. Chính phủ (2026). Nghị định số 142/2026/NĐ-CP ngày 30/4/2026 quy định chi tiết một số điều và biện pháp thi hành Luật Trí tuệ nhân tạo, hiệu lực 01/5/2026 (Công báo số 278 ngày 18/5/2026).
15. Bộ Chính trị (2024). Nghị quyết số 57-NQ/TW ngày 22/12/2024 về đột phá phát triển khoa học, công nghệ, đổi mới sáng tạo và chuyển đổi số quốc gia.
16. Ban Bí thư TW Đoàn (2026). Thể lệ Cuộc thi Sáng tạo trẻ Quốc gia trong lĩnh vực Trí tuệ nhân tạo năm 2026, Điều 5.
