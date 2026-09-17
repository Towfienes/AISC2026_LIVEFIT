# Livestream thương mại: Trung Quốc, Ấn Độ, bài báo 2024–2026 và bài học cho LiveLift (17/09/2026)

> **Nguồn gốc tài liệu (khai thật).** Tác tử Claude (vai tổng biên tập) soạn tài liệu này ngày 17/09/2026 từ ba báo
> cáo nghiên cứu của ba tác tử khác nhau: Trung Quốc; Ấn Độ đối chiếu Hàn Quốc và Đông Nam Á; bài báo và công nghệ
> mới. Báo cáo thô nằm trong scratchpad của phiên làm việc, **không có trong kho**.
>
> **Kiểm chứng không đồng đều giữa các phần, nói thẳng:**
> - Tác tử kiểm chứng độc lập đã gửi kết quả cho **4 phát hiện đầu của phần Trung Quốc** (3 xác nhận, 1 đúng một phần).
>   Kết quả kiểm chứng cho phần còn lại của Trung Quốc, và cho toàn bộ phần Ấn Độ và bài báo, **không tới được tổng
>   biên tập**.
> - Vì vậy tổng biên tập **tự đối chiếu** các khẳng định quan trọng ngày 17/09/2026: đọc lại các trang người kiểm chứng
>   đã tải (văn bản quy định trên gov.cn, tài liệu API WeChat, SDK chính thức của 巨量引擎, báo Trung/Việt/Hàn/Ấn, Công
>   báo Ấn Độ, hướng dẫn ASCI, đặc tả UPI); tra **arXiv API** cho 24 mã bài; tra **Crossref API** cho 12 DOI; mở lại bằng
>   WebFetch trang MIS Quarterly, TNGlobal, Social Media Today, Bộ Công an, Cổng thông tin Chính phủ.
> - Khẳng định nào không đối chiếu được đều ghi **[Chưa kiểm lại]**. Khẳng định bị phát hiện sai đã **bỏ** hoặc **sửa**
>   (danh sách ở Phụ lục A).
>
> **Phạm vi:** chỉ để hiểu thị trường và phương pháp. Theo quyết định của chủ dự án ngày 17/09/2026, tài liệu này
> **không** đề xuất tích hợp đường đọc bình luận không chính thức nào; các đường không chính thức cũ trong kho vẫn giữ
> nguyên.
>
> **Ngày truy cập:** mọi URL truy cập ngày **17/09/2026**, trừ khi ghi khác. Nguồn tiếng Trung, Hàn được dịch ý, kèm
> trích nguyên văn ngắn.
>
> **Mức chắc chắn:** **[Đã kiểm]** = người kiểm chứng xác nhận · **[TBT đối chiếu]** = tổng biên tập tự đọc lại nguồn
> gốc và khớp · **[Một phần]** · **[Chưa kiểm lại]** · **[Suy luận]** · **[Thứ cấp]** = báo, blog, diễn đàn.

---

## 0. Mười kết luận

1. **Switchback trong phòng live đã được dùng ở quy mô công nghiệp.** 快手 (Kuaishou) dùng 时间片轮转 cho can thiệp trong
   phòng live khi thí nghiệm hai phía không xử lý được nhiễu; 美团 (Meituan) công bố quy trình; Swiggy (Ấn Độ) có
   *"Time Sliced Randomized"* trong nền tảng thí nghiệm. **[Đã kiểm] / [TBT đối chiếu]**
2. **Bằng chứng có đối chứng về giá trị của số liệu thời gian thực:** thí nghiệm ngẫu nhiên thực địa cho người dẫn xem
   số bán hàng thời gian thực làm doanh số hàng đặt trước tăng **khoảng 40%** (MIS Quarterly 2025). **[TBT đối chiếu]**
3. **Hiệu ứng của AI trong live nhỏ hơn quảng cáo:** trợ lý AI cho người mua **+3,00% doanh số, −12,55% trả hàng**
   (ISR 2025); người dẫn số **không** tăng doanh số đáng kể so với không live, trừ khi có **hỏi–đáp thời gian thực**
   (+25%, ISR 2026). Con số +30% đến +230% của nhà cung cấp không có đối chứng. **[Đã kiểm] / [Một phần]**
4. **Không nền tảng lớn nào mở luồng bình luận cho "công cụ phân tích bán hàng".** Ở Trung Quốc bình luận chỉ mở qua
   "trò chơi tương tác" được chủ phòng gắn vào; không thấy API ghi "giảng giải/ghim". Ấn Độ không sàn nào có API live
   công khai. Thiết kế "LiveLift ra lịch – người dẫn thao tác – đo sau" **đúng chuẩn thị trường**. **[TBT đối chiếu] một phần**
5. **Cào dữ liệu live đã thua kiện ở Trung Quốc:** 100 vạn NDT (vụ "小葫芦", 21/12/2021) và 490 vạn NDT (蝉小红 của 蝉妈妈,
   tin 05/2025). Đây là lý do mạnh cho quyết định chỉ dùng API chính thức. **[TBT đối chiếu]**
6. **Khách hàng mục tiêu nên là shop tự phát sóng**, không phải KOL: dịp 618/2025 店播 chiếm **50% GMV live** của 抖音.
   Phiên dài và lặp lại mới đủ khối cho switchback. **[TBT đối chiếu]**
7. **Hai rủi ro phương pháp:** thuật toán nền tảng phân bổ lượt hiển thị có thể làm ước lượng thông thường **lệch, thậm chí
   đổi dấu** (arXiv 2406.14380, bối cảnh thí nghiệm theo creator); giới thiệu lâu một sản phẩm tăng doanh thu sản phẩm đó
   nhưng **giảm doanh thu cả phiên** (POM 2025). **[TBT đối chiếu]**
8. **Với ≤ 10 cụm, khoảng tin cậy chuẩn cụm chỉ phủ khoảng 82%** thay vì 95% (Pankratev, DoorDash, 2026). Kiểm định ngẫu
   nhiên hóa — thứ LiveLift **đã dùng làm phân tích chính** — là lựa chọn đúng. **[TBT đối chiếu]**
9. **Rất nhiều bài học đã có sẵn trong LiveLift** (rerandomization cân bằng đầu/giữa/cuối, cân bằng transition, burn-in
   có độ nhạy, chuẩn hóa viewer-giây, màn người dẫn bị làm mù, nhật ký gán và phơi nhiễm chỉ-ghi-thêm). Việc mới đáng làm
   chủ yếu là **viết bằng chứng vào hồ sơ**, **giao thức phiên** và **`analysis/carryover.py`** (mục 6).
10. **Việt Nam có hạ tầng dữ liệu chính thức tốt hơn Ấn Độ** (Shopee `update_show_item`, TikTok Shop số theo phút) và
    content commerce đã chiếm **37% GMV sàn ĐNÁ** nửa đầu 2026. Thị phần 4 sàn VN năm 2025 là **ước tính** lệch nhau giữa
    hai đơn vị (429,7 và 458,16 nghìn tỷ đồng). **[TBT đối chiếu]**

---

## 1. Trung Quốc

### 1.1 Quy mô và cơ cấu

| Chỉ số | Giá trị | Nguồn | Mức |
|---|---|---|---|
| GMV livestream thương mại 2025 | **69.461 亿 NDT**, +30,42%; tỷ lệ thâm nhập 36,02% (*"增速继续下降"*); chi tiêu bình quân 12.362 NDT/người, +43,92% | 网经社, https://www.100ec.cn/detail--6659027.html | [TBT đối chiếu] |
| 店播 (shop tự phát) dịp 618/2025 | *"店铺自播已贡献直播总成交额的50%"*; *"破千万商家中近七成采用了店播模式"* | 新播场 trên 腾讯新闻, 02/01/2026, https://news.qq.com/rain/a/20260102A04G9100 | [TBT đối chiếu] |
| Người dẫn tầm trung dịp 双11/2025 | *"腰部主播…贡献了45%的GMV"*; nhóm siêu đầu giảm thị phần 32% → 30% (trích 《2025"双11"直播电商数据分析与洞察报告》) | như trên | [TBT đối chiếu] |
| 双11/2025 trên 抖音 | *"销售额破千万的店播数量同比增长53%，52万个商家的店播销售额翻倍"* | https://www.xinbaomu.com/info/115616.shtml | [TBT đối chiếu] |
| 快手电商 2025 | Tổng GMV 1,6 vạn tỷ NDT; Q4/2025 có "AI互动助手" trong live | https://www.stcn.com/article/detail/3697844.html | [Chưa kiểm lại] |

**Ý nghĩa:** shop tự phát sóng hằng ngày, nhiều giờ, cùng người dẫn và rổ hàng là điều kiện lý tưởng cho switchback;
KOL phát thưa thì khó có đủ khối. **[Suy luận]**

### 1.2 Quy định mới: 《直播电商监督管理办法》

Lệnh số 117 của 市场监管总局 và 国家网信办: thông qua 24/11/2025, công bố 18/12/2025, **hiệu lực 01/02/2026**. Toàn văn:
https://www.gov.cn/gongbao/2026/issue_12666/202604/content_7065114.html **[TBT đối chiếu]**

| Điều | Nguyên văn ngắn | Ý nghĩa cho LiveLift |
|---|---|---|
| 16 | Thông tin giao dịch gồm *"直播视频回放记录、直播互动信息"*, lưu *"不少于三年"* | Bình luận là **chứng cứ giao dịch nền tảng giữ**, không phải dữ liệu bên thứ ba tự do lấy |
| 11 | Phòng live lớn: *"采取技术监测、实时巡查等管理措施"* | Hạ tầng thời gian thực của nền tảng phục vụ quản trị, không mở ra ngoài |
| 17, 34 | Cấm *"利用人工智能等技术手段，编造、传播虚假或者引人误解的商业信息"* | Gợi ý lời thoại do AI sinh phải có người duyệt |
| 26 | Liên kết thông tin người bán: *"不得多次跳转"*, *"不得设置连续多次验证、强制关注账号…等不合理访问限制"* | Nguyên tắc tốt cho link đo `/r/{code}`: một lần chuyển hướng, không bắt đăng nhập hay theo dõi |
| 31 | *"对直播间互动内容进行实时管理"*; sửa sai tại chỗ, lưu hồ sơ ≥ 3 năm | Có nhu cầu thị trường cho công cụ điều hành/tuân thủ thời gian thực |
| 37 | Nhân vật do AI tạo phải *"持续向消费者提示该人物图像、视频由人工智能等技术生成"* | Nếu có thử người dẫn số, gắn nhãn AI **liên tục** |

Quan hệ với 《网络直播营销管理办法（试行）》 (2021), thay thế hay song song, **chưa xác minh**.

### 1.3 API chính thức cho người bán và nhà phát triển

| Nền tảng | Số liệu phòng live | Trong lúc phát? | Nội dung bình luận | Ghi/can thiệp sản phẩm | Nguồn | Mức |
|---|---|---|---|---|---|---|
| **视频号** (WeChat Channels) `POST /channels/livedashboard/getlivedata` | Người xem, bình luận (số người), từng sản phẩm: `exp_uv`, `clk_uv`, `clk_pv`, `clk_pay_ratio`, `gmv` | **Có**: khối `on_air`, mỗi chỉ số có `n: 10`, `last_n_mins_value`, `last_2n_to_n_mins_value`, `last_n_mins_percentile`; có `recent_10_min_conversion` và `whole_live_conversion`; sau khi tắt có `median_7_days` | Chỉ số người bình luận | Không thấy | https://developers.weixin.qq.com/doc/channels/API/livedashboard/getlivedata.html — *"本接口支持第三方平台代商家调用。该接口所属的权限集 id 为：176"* | [TBT đối chiếu]; tài liệu không định nghĩa `percentile` so với nhóm nào |
| **巨量千川** (quảng cáo live của 抖音) — "今日直播" | Phòng, luồng vào theo nguồn, sản phẩm, người xem | **Có** (trong ngày) | Không | Không có API ghi, nhưng `product_list` trả `explain_status` (trạng thái đang giảng giải) và `live_product_explain_cnt` (số lần giảng giải) | SDK chính thức https://github.com/oceanengine/ad_open_sdk_go (`models/model_qianchuan_today_live_room_product_list_get_v1_0_response_data_list_inner.go`) | [TBT đối chiếu] |
| **抖音开放平台 — 弹幕玩法/小玩法** | — | — | **Có**: bình luận, tim, quà đẩy về máy chủ nhà phát triển, chỉ khi **chủ phòng gắn (挂载) trò chơi** | Không | https://developer.open-douyin.com/docs/resource/zh-CN/interaction/develop/douyincloud/guide | [TBT đối chiếu] phần cơ chế; bước thẩm định đề xuất [Chưa kiểm lại] |
| **抖店开放平台 / 巨量百应** | Số liệu phòng ở 罗盘 (giao diện) | ? | Không thấy | **Chưa tìm thấy** API "讲解/弹窗"; thao tác "讲解" làm trên giao diện 巨量百应 | https://op.jinritemai.com/docs/api-docs/61/2007 (trang render JS) | [Chưa kiểm lại] |
| **淘宝开放平台** | `taobao.live.contents.query`, `taobao.live.items.query` | ? | Chỉ **đăng** bình luận; đọc chỉ thấy cho trò chơi | Không thấy | https://jaq-doc.alibaba.com/docs/api.htm?apiId=70808 | [Chưa kiểm lại] |
| **快手** | Repo chính thức chỉ có API đẩy luồng (mã 2020) | Không (API) | 小玩法 | Không | https://github.com/KwaiVideoTeam/kuaishou-liveopen-api | [Chưa kiểm lại] |

**Ba bài học thiết kế:**

1. **"10 phút gần nhất so với 10 phút trước"** là khung hiển thị thời gian thực của 视频号. Đây là so sánh trước–sau, **không
   phải nhân quả**, nhưng người bán quen đọc. LiveLift có thể hiển thị cùng khung, **đặt cạnh** ước lượng switchback và
   dán nhãn "mô tả". **[Suy luận]**
2. **Trạng thái "đang giảng giải" và số lần giảng giải là dữ liệu hạng nhất** (千川). LiveLift đã ghi `exposure_event` cho
   mọi lần ghim/bỏ ghim (`PREREGISTRATION.md` mục 2), nên bài học này **đã có**; chỉ cần nêu trong hồ sơ.
3. **Bình luận chính thức = kênh trò chơi tương tác có chủ phòng đồng ý.** Tương đương chính thức ở Việt Nam là YouTube
   `streamList`, Facebook Page `/comments`, Shopee `get_latest_comment_list`.

### 1.4 Công cụ dữ liệu: chính chủ và bên thứ ba

- **Chính chủ** (抖音电商罗盘, 巨量百应, 淘宝直播中控台, 视频号助手) chỉ cho xem **phòng của mình**. Theo tóm tắt kết quả tìm kiếm
  của FAQ 罗盘: số trong lúc live ưu tiên kịp thời; sau phiên được **thống kê và hiệu chỉnh lại**, lấy **số ngày hôm sau
  làm chuẩn** (https://school.jinritemai.com/doudian/web/articlev0/aHyVTUvYbCBv). **[Chưa kiểm lại]** — trang render JS,
  chưa trích được nguyên văn. Dù vậy, bài học "tách số tạm và số đã chốt" vẫn đứng vững vì TikTok Shop chỉ trả số theo
  phút **sau** phiên (tài liệu TikTok cùng ngày).
- **Bên thứ ba** (蝉妈妈, 飞瓜, 抖查查…) theo dõi đối thủ bằng thu thập phía người xem và **ước tính** GMV. Giá phổ biến
  800–3.000 NDT/tháng và sai số GMV "15%–30%" lấy từ trang tổng hợp không rõ tác giả. **[Thứ cấp], [Chưa kiểm lại]**
- **Tiện ích "tự động bật sản phẩm, trả lời bình luận"** tồn tại trên Chrome Web Store (78 người dùng, v0.4.0,
  06/01/2026): cho thấy nhu cầu "hẹn giờ ghim" có thật nhưng nền tảng không mở API. **LiveLift không làm theo hướng này.**
  https://chromewebstore.google.com/detail/pdphciapihdbepnbcchcdjnkdehhlhck **[Chưa kiểm lại]**

### 1.5 Án lệ về cào dữ liệu live

| Vụ | Nội dung | Nguồn | Mức |
|---|---|---|---|
| **抖音 kiện 上海六界 ("小葫芦")** | TAND quận 余杭, Hàng Châu tuyên ngày **21/12/2021**: lấy trái phép thu nhập của người dẫn và **lịch sử tặng quà của người dùng** trong phòng live 抖音 rồi bán; cấu thành cạnh tranh không lành mạnh, xâm phạm quyền thông tin cá nhân của người dẫn và người tặng quà; bồi thường **100 万 NDT** | IT之家 31/12/2021, https://www.ithome.com/0/596/034.htm | [TBT đối chiếu] |
| **小红书 kiện 蝉妈妈 (蝉小红)** | Khởi kiện 08/07/2022; bị đơn *"通过频繁更换用户ID、加速IP更换频率等技术手段，绕过小红书的技术保护措施"*; bồi thường **490 万 NDT** và xóa dữ liệu | 派代 trên 腾讯新闻, 24/05/2025, https://news.qq.com/rain/a/20250524A0697M00 | [TBT đối chiếu]; bài **không nêu** tên tòa và cấp xét xử (báo cáo gốc ghi "chung thẩm TAND trung cấp Hàng Châu" — **bỏ**, chưa có nguồn) |

### 1.6 AI trong live: tuyên bố và bằng chứng

**Tuyên bố của nhà cung cấp, không có đối chứng:** 百度 慧播星 *"GMV平均提升62%"* (https://m.eeo.com.cn/2026/0116/779796.shtml,
[Chưa kiểm lại]); phiên 罗永浩 bản số trên 百度 ngày 15/06/2025, gần 7 giờ, *"观看人次突破1300万、GMV超5500万"*, so với
**một** phiên người thật khác ngày ([TBT đối chiếu], news.qq.com 02/01/2026); 京东 "+30% chuyển đổi" chỉ từ tóm tắt tìm
kiếm (**không dùng**).

**Bằng chứng có đối chứng** (xem thêm mục 3.2):

| Nghiên cứu | Thiết kế | Kết quả | Điều kiện kèm theo | Mức |
|---|---|---|---|---|
| He, Huang, Wang, Sun — *Real-Time Sales Data, Streamer Improvisation, and Sales Performance*, **MIS Quarterly** 49(4):1567–1594, 2025 | Thí nghiệm ngẫu nhiên thực địa trên nền tảng live lớn ở châu Á (Yan Sun thuộc Alibaba Group) | Người dẫn xem số bán hàng thời gian thực: doanh số hàng đặt trước cao hơn **khoảng 40%**; cơ chế là ứng biến dựa trên số liệu | Mạnh hơn với người dẫn ứng biến giỏi và sản phẩm bất định cao | [TBT đối chiếu] https://aisel.aisnet.org/misq/vol49/iss4/17/ |
| He và cộng sự — *The Sales Data Sells*, **AMCIS 2021** (bản hội nghị, cùng nhóm tác giả và bối cảnh hàng đặt trước) | Gán ngẫu nhiên theo số cuối ID tài khoản; 01–03/12/2020 | β = 0,186 trên log(sales), p < 0,01 (bài tự đọc là 18,6%–20%) | Mẫu phân tích cuối 358 và 505 phiên; chỉ 3 ngày; chỉ có ý nghĩa ở người dẫn có lượng theo dõi trung bình; không có hiệu ứng ở người dẫn không mở bảng số | [Đã kiểm] https://aisel.aisnet.org/cgi/viewcontent.cgi?article=1148&context=amcis2021 |
| Wang, Huang, He, Liu, Guo, Sun… — *AI Assistant in Online Shopping*, **ISR** 36(4):2358–2374, 2025 | Thí nghiệm ngẫu nhiên thực địa; trợ lý AI dạng chat **cho người mua** | *"increases sales by 3.00% and reduces product return rates by 12.55%"* | Mạnh hơn với sản phẩm bất định cao và người dẫn có khán giả lớn. Câu "hiệu ứng thật của AI chỉ vài phần trăm" là suy diễn — chỉ nói "trong thí nghiệm này +3,00%" | [Một phần] https://doi.org/10.1287/isre.2023.0103 |
| Liu, Wang, Yang, Wang — *AI-Powered Digital Streamers in Online Retail*, **ISR** 37(2):824–841, 06/2026 (online 26/08/2025) | Phần 1: dữ liệu 328 sản phẩm thời trang trên Tmall (72 người dẫn số, 74 người thật, 182 không live). Phần 2: thí nghiệm với một nhà bán tạp hóa mới trên Tmall | Người dẫn số *"do not significantly improve sales over no live streaming"*; hỏi–đáp thời gian thực: **+25%** sản phẩm bán, **+86%** doanh thu; bốc thăm +17%/+70% | Các con số +25%/+86% đến từ **phần 2**, so với bản người dẫn số cơ bản, không từ dữ liệu 328 sản phẩm | [Đã kiểm] https://doi.org/10.1287/isre.2023.0024 · https://www.eurekalert.org/news-releases/1097754 |

**Cách trích trong hồ sơ:** dùng bản **MIS Quarterly 2025** (tạp chí, khoảng 40%) làm trích dẫn chính; nếu nhắc bản AMCIS 2021
thì ghi là bản hội nghị sơ bộ của cùng nhóm, **không** trình bày hai con số như hai bằng chứng độc lập. Tổng biên tập chưa
đọc toàn văn bản MISQ nên chưa biết vì sao hai con số khác nhau.

### 1.7 Phương pháp đo lường nhân quả ở Trung Quốc

| Nguồn | Nội dung | Mức |
|---|---|---|
| **快手** — 金雅然, DataFunTalk 05/09/2021, đăng lại https://www.sohu.com/a/487950696_121124371 | *"双边实验只能描述简单的组间溢出，在个体和个体之间存在干扰的复杂情况下，双边实验是无法帮助我们判断实验效果，例如直播PK暴击时刻这种情况下，我们通过时间片轮转实验解决"*; *"时间片轮转的核心在于：时间片的选择、实验总周期选择、随机切换时间点"*. Bài **không có số liệu**; ví dụ là cơ chế PK, **không phải** ghim sản phẩm | [Đã kiểm] |
| **美团** — 可信实验白皮书系列04：随机轮转实验, 06/06/2025, bản đăng lại https://segmentfault.com/a/1190000046615732 (bản gốc tech.meituan.com trả 404) | Ba thiết kế: tung đồng xu, ngẫu nhiên hoàn toàn (có phân tầng), ghép cặp. Tung đồng xu *"不太适用于样本量极少的场景"*. Mẫu nhỏ: *"建议采用非参Fisher精确检验计算p值，Neyman方法计算方差/MDE"*. Đơn vị thí nghiệm khác đơn vị phân tích mà tính phương sai sai thì xác suất dương tính giả có thể *"超过25%"* | [TBT đối chiếu] |
| **神策数据** — sổ tay 时间片轮转试验 (27/12/2024) | Lát 24/12/6/3/2/1 giờ; khuyên mô phỏng trên dữ liệu lịch sử để chọn độ dài lát | [Chưa kiểm lại] https://manual.sensorsdata.cn/abtesting/docs/time_slice_round_robin_experiment/v0102 |
| **快手** — 程大曦, DataFun 11/03/2023 | Thí nghiệm hai phía 2×2 (người dẫn × người xem); cần nền tảng kiểm soát phía người xem → LiveLift **không** làm được | [Chưa kiểm lại] https://www.6aiq.com/article/1678514401484 |
| Zhan, Han, Hu, Jiang — *Estimating Treatment Effects under Algorithmic Interference: A Structured Neural Networks Approach*, arXiv 2406.14380 (v5, 03/2026) | Thí nghiệm **theo creator** trên *"a major short-video platform"*: nhóm thí nghiệm và đối chứng **tranh nhau lượt hiển thị** do thuật toán phân bổ; ước lượng hiệu trung bình *"exhibit substantial bias and, in some cases, even reverse the sign of the effect"* | [TBT đối chiếu] https://arxiv.org/abs/2406.14380. Báo cáo gốc ghi bối cảnh "Weixin Channels" — tóm tắt không nói vậy, **bỏ**. Áp sang "thuật toán đẩy traffic sang khối kế tiếp trong một phòng live" là **[Suy luận]** |
| 巨量引擎 blog — nhịp 福袋 (túi quà) để "bẩy" traffic tự nhiên | Phát khoảng 5 phút sau khi mở live, lặp lại khi người xem giảm; cảnh báo phát quá nhiều làm giảm giao dịch | [Chưa kiểm lại] https://www.oceanengine.com/blog/fudai-jiwanyuan-liuliang.html |
| Xie, Sharma, Mehra — *Designing E-commerce Livestreams: How Product Presentation Duration Affects Sales?*, **POM** 34(12):4079–4096, 2025 | Dữ liệu hai nền tảng livestream lớn nhất Trung Quốc: giới thiệu một sản phẩm lâu hơn → doanh thu sản phẩm đó cao hơn, nhưng thời lượng trung bình tăng → **doanh thu cả phiên giảm** | [TBT đối chiếu] phần thư mục và tóm tắt, https://doi.org/10.1177/10591478251314455 |

**Khung 复盘 (hậu kiểm) phổ biến** — 人货场, bốn nhóm chỉ số của 罗盘, ma trận sản phẩm 2×2 (bấm × mua), 五维四率 (ngưỡng cho
ngành mỹ phẩm) — đều là **phân rã phễu và so ngưỡng**, không tách được "vì ghim" khỏi "vì traffic tăng". Nguồn là diễn đàn
nghề (https://www.woshipm.com/operate/6437886.html, https://www.27sem.com/article/5956). **[Thứ cấp], [Chưa kiểm lại]**
Đây đúng là khoảng trống switchback lấp: *chẩn đoán bằng phễu, kết luận bằng thí nghiệm*.

---

## 2. Ấn Độ

### 2.1 Ai còn, ai đã dừng

| Nền tảng | Trạng thái | Số liệu | Nguồn | Mức |
|---|---|---|---|---|
| **TikTok** | Bị chặn từ 29/06/2020 cùng 58 app khác theo Điều 69A Luật CNTT → không có "TikTok Shop Ấn Độ" | — | https://www.pib.gov.in/PressReleseDetailm.aspx?PRID=1635206&reg=3&lang=2 | [Chưa kiểm lại] |
| **Bulbul** (app live commerce độc lập) | Good Glamm Group mua lại (03/2023) | Giá trị giao dịch trung bình *"200–300 rupees [$2–$4]"* so với $15,40 ở một nền tảng hàng đầu Trung Quốc năm 2021. Nhà sáng lập: *"We were just solving too many problems"* | Rest of World 23/10/2023, https://restofworld.org/2023/amazon-live-commerce-india/ | [TBT đối chiếu] |
| **Simsim** (YouTube mua 2021) | Ngừng nhận đơn sau 31/03/2023; YouTube chuyển sang chương trình affiliate | — | https://inc42.com/buzz/two-years-after-acquisition-youtube-shuts-indian-social-commerce-app-simsim/ | [Chưa kiểm lại] |
| **Moj/ShareChat live commerce** | Thu hẹp từ 2023 | — | https://india.entrepreneur.com/news-and-trends/is-live-commerce-dying-in-india/446056 | [Chưa kiểm lại] |
| **Amazon Live India** | Còn | *"Nearly 10% of all visitors on Amazon.in watched a livestream during the first week of sales"*; stream đông nhất *"close to 500,000 unique viewers"* (số Amazon tự công bố, Great Indian Festival 2023). Amazon Ads: *"Amazon.com/live mobile and web experiences is only available in India and the U.S."* | Rest of World (như trên) · https://advertising.amazon.com/solutions/products/amazon-live | [TBT đối chiếu] |
| **Flipkart** (LiveShop+, Vibes) | Còn | H1/2024: 75 triệu người dùng tương tác video commerce; **không** công bố tỷ lệ chuyển đổi | https://inc42.com/buzz/flipkart-says-video-commerce-offering-a-big-success-75-mn-users-engaged-in-h1-2024/ | [Chưa kiểm lại] |
| **Myntra, Meesho, Nykaa** | Còn, dịch sang video/creator | Myntra tự báo nội dung creator *"25%–28% higher conversion"*, không nêu phương pháp | https://www.storyboard18.com/brand-marketing/myntra-meesho-nykaa-intensify-creator-led-commerce-efforts-as-indias-125-billion-e-retail-market-evolves-85544.htm | [Chưa kiểm lại] |
| **YouTube Shopping Ấn Độ** | Còn, tăng mạnh | *"over 40% of eligible creators in India have already joined"*, *"over 3 million videos tagged"*, *"Over 200 million logged-in users in India had shopping-related searches"*, thời gian xem nội dung mua sắm *"more than 250% year over year"*; đang thử *"automatically identify and tag all eligible products mentioned in videos"* | Google India Blog 10/10/2025, https://blog.google/intl/en-in/products/platforms/fueling-the-next-era-of-creator-led-shopping-experiences-in-india/ | [TBT đối chiếu] |
| **Facebook/Instagram Live Shopping** | Facebook dừng 10/2022; Instagram bỏ gắn thẻ sản phẩm khi live từ 16/03/2023 | — | https://www.engadget.com/instagram-live-shopping-shutdown-205824247.html | [Chưa kiểm lại] |

Quy mô: Storyboard18 (03/02/2026) dẫn **Grand View Research**: doanh thu live commerce Ấn Độ 2024 khoảng 4,82 tỷ USD, chỉ
3,8% toàn cầu; các startup gọi tổng *"close to $90 million"* rồi phần lớn đóng cửa hoặc bán rẻ
(https://www.storyboard18.com/digital/despite-1-trillion-creator-led-influence-live-commerce-hasnt-cracked-india-88665.htm).
**[TBT đối chiếu]**. Báo cáo gốc ghi bài "không nêu tên hãng" — sai, bài có nêu. Đây vẫn là số ước tính của hãng nghiên cứu
thị trường, **không đưa vào hồ sơ**.

**Bài học:** live commerce **độc lập** chết; video/creator commerce **gắn vào sàn hoặc YouTube** sống. Không sàn nào công
bố thiết kế đo nhân quả cho live. **[Suy luận]** từ các nguồn trên.

### 2.2 API và hạ tầng

- **Không sàn Ấn Độ nào có API live công khai.** Flipkart Marketplace Seller API có module đơn/giao hàng (ví dụ
  `ShipmentV3Api`), listings, returns, reports; trang tài liệu tổng tổng biên tập đọc không có chữ "Live" hay "Video"
  (https://seller.flipkart.com/api-docs/FMSAPI.html). **[TBT đối chiếu] một phần**. Meesho không có API công khai (tích hợp
  qua đối tác như Fynd Konnect: https://documentation.fynd.com/konnect/channels/marketplaces-webstores/meesho).
  **[Chưa kiểm lại]**
- **So với Việt Nam:** Shopee có `update_show_item` và bình luận 10 giây, TikTok Shop có số LIVE theo phút → Việt Nam
  **mở hơn**. Có thể nêu trong hồ sơ ("vì sao làm ở Việt Nam khả thi"). **[Suy luận]**
- **ONDC** là giao thức mở cho khám phá–đặt hàng–giao; chưa thấy đặc tả live/video
  (https://github.com/ONDC-Official/ONDC-Protocol-Specs). **[Chưa kiểm lại]**
- **UPI:** đặc tả liên kết NPCI v1.6 (11/2017, bản nháp) có tham số `tr` = *"Transaction reference ID. This could be order
  number, subscription number, Bill ID, booking ID…"*, bắt buộc với giao dịch merchant (bản sao
  https://www.labnol.org/files/linking.pdf). **[TBT đối chiếu]**. Ý tưởng cho LiveLift: shop chốt đơn bằng chuyển khoản
  có thể ghi **mã khối trong nội dung chuyển khoản/mã đơn** để quy đơn về khối qua kênh chính thức. Đặc tả VietQR/NAPAS
  **chưa tra**. **[Suy luận]**
- **AI đa ngôn ngữ:** Meesho dùng voice bot GenAI, khoảng 60.000 cuộc gọi/ngày tiếng Anh + Hindi, tự báo 95% giải quyết
  (https://techcrunch.com/2024/11/26/ai-helps-indias-meesho-cut-customer-call-costs-by-75). **[Chưa kiểm lại]**. Không tìm
  thấy công bố nào của Ấn Độ về **ý định mua trong chat live** — khoảng trống không chỉ ở Việt Nam.

### 2.3 Pháp lý Ấn Độ (chỉ để đối chiếu, không phải tư vấn pháp lý)

| Điểm | Nội dung | Nguồn | Mức |
|---|---|---|---|
| DPDP Rules 2025 | Công báo *"New Delhi, the 13th November, 2025"*, G.S.R. 846(E). *"Rules 1, 2 and 17 to 21 shall come into force on the date of their publication"*; Rule 4 sau một năm; *"Rules 3, 5 to 16, 22 and 23 shall come into force eighteen months after"* | https://www.dpdpa.com/DPDP_Rules_2025_English_only.pdf | [TBT đối chiếu] |
| Miễn trừ nghiên cứu | Rule 16: *"The provisions of the Act shall not apply to the processing of personal data necessary for research, archiving or statistical purposes if it is carried on in accordance with the standards specified in Second Schedule"* | như trên | [TBT đối chiếu] |
| Vi phạm dữ liệu | Báo Ủy ban *"without delay"*, chi tiết *"within seventy-two hours of becoming aware of the breach"* | như trên, Rule 7(2) | [TBT đối chiếu] |
| Dữ liệu người dùng tự công khai | DPDP Act Điều 3(c)(ii): Luật không áp dụng cho dữ liệu *"made or caused to be made publicly available by the Data Principal"*; luật sư lưu ý dữ liệu về **người thứ ba** trong bình luận công khai không tự động được miễn | https://www.dpdpa.com/dpdpa2023/chapter-1/section3.html · https://community.nasscom.in/communities/public-policy/publicly-accessible-personal-data-under-dpdp-act-ai-training-and-other | [Chưa kiểm lại] |
| ASCI — quảng cáo qua influencer | *"In live streams, the disclosure label should be announced at the beginning and the end of the broadcast"*; *"The disclosure should be in English OR in the language as the advertisement itself"*; influencer ảo phải báo *"they are not interacting with a real human being"* | https://www.ascionline.in/social/wp-content/uploads/2024/03/ASCI-Guidelines-Influencer-Advertising-In-Digital-Media-1.pdf | [TBT đối chiếu] |
| Bộ Tiêu dùng (DoCA) | Nhãn tài trợ trong live phải *"displayed continuously and prominently during the entire stream"* | https://blog.galalaw.com/post/102i629/endorsements-know-hows-new-influencer-rules-in-india | [Chưa kiểm lại] — trang báo Deccan Herald bị chặn khi đối chiếu |

**Đọc cho LiveLift:** (1) **không** mượn lập luận "dữ liệu tự công khai được miễn" cho Việt Nam; quy tắc hiện hành của
LiveLift (bỏ tên, lọc PII trước khi ghi, xoá chat thô) chặt hơn. (2) Bốn tiêu chí Second Schedule (chỉ dữ liệu cần thiết,
chính xác, lưu đến khi cần, bảo mật hợp lý) là **checklist tham chiếu tốt** cho mục đạo đức dữ liệu. (3) Nhãn tài trợ là
**biến gây nhiễu** nếu thay đổi theo khối → giữ **cố định suốt phiên**.

### 2.4 Đo lường ở Ấn Độ

- **Swiggy XP** hỗ trợ *"Time Sliced Randomized — Switchback experiments when the sequence of test and control is
  completely random"* và *"Time Sliced Deterministic"*; miền thí nghiệm *Exclusive / Conservative / Overlapping* theo
  "pod" (https://bytes.swiggy.com/experimentation-platform-xp-at-swiggy-part-1-e50b7dbdc773). **[TBT đối chiếu]**. Chưa
  biết độ dài lát và cách phân tích.
- **Amazon Live** đo bằng báo cáo sau chiến dịch và Amazon Marketing Cloud (quy gán quan sát, chỉ ở Mỹ):
  https://advertising.amazon.com/resources/whats-new/amazon-marketing-cloud-now-includes-amazon-live-signals.
  **[Chưa kiểm lại]**
- **Không tìm thấy** đội live commerce Ấn Độ nào công bố thí nghiệm nhân quả cho can thiệp trong livestream.

---

## 3. Hàn Quốc, Đông Nam Á và Việt Nam

### 3.1 Hàn Quốc

| Chủ đề | Nội dung | Nguồn | Mức |
|---|---|---|---|
| Quy mô | *"지난해 4조 7,000억 원에서 올해 6조 원까지 커질 전망"*; tăng bình quân 35%, nhưng chỉ *"전체 커머스 대비 1.7% 수준"* (Trung Quốc 60%, Mỹ 4,6%) | Apparel News 29/03/2026, https://www.apparelnews.co.kr/news/news_view/?idx=224212&cat=CAT100 | [TBT đối chiếu] |
| Naver Shopping Live | Dẫn đầu; ra mắt 07/2020; 5 năm *"누적 재생수 130억 뷰, 누적 거래액 4조 원"* | như trên | [TBT đối chiếu] |
| Grip (Kakao đầu tư) | Lỗ hoạt động năm thứ 4 liên tiếp (2024) | https://www.newsway.co.kr/news/view?ud=2025042115590942409 | [Chưa kiểm lại] |
| API | Không tìm thấy endpoint Shopping Live công khai trong Naver Commerce API | — | [Chưa kiểm lại] |

Bài học giống Ấn Độ: nền tảng có sẵn tìm kiếm + thanh toán thắng; app live độc lập lỗ kéo dài. **[Suy luận]**

### 3.2 Đông Nam Á và Việt Nam

| Chủ đề | Số liệu | Nguồn | Mức |
|---|---|---|---|
| Momentum Works — *Live Commerce in Southeast Asia 2026* | Content commerce trên Shopee, TikTok Shop, Lazada: *"$49.7 billion in 2025"*; *"$33.8 billion … in the first half of 2026"*; dự báo *"$77.9 billion"*; *"37 percent of Southeast Asia's platform ecommerce GMV"*. AI live: *"In selected cases, it costs around 20 percent to 25 percent of a comparable human operation"*, đạt *"around 80 percent of human livestream GMV per hour on average"*. Bài **không có số riêng cho Việt Nam** | TNGlobal 08/09/2026, https://technode.global/2026/09/08/southeast-asia-content-commerce-to-reach-77-9b-in-2026-as-live-goes-mainstream-momentum-works/ | [TBT đối chiếu] |
| Việt Nam 2025 — Metric | 4 sàn đạt **429.700 tỉ đồng, +34,75%**; Shopee + TikTok Shop chiếm **97%**; Shop Mall chiếm 2,12% số shop nhưng **32,6%** doanh số hai sàn | Thanh Niên 02/02/2026, https://thanhnien.vn/4-san-thuong-mai-dien-tu-bo-tui-gan-430000-ti-dong-trong-nam-2025-185260202085014664.htm | [TBT đối chiếu] |
| Việt Nam 2025 — YouNet ECI (công bố 12/03/2026) | 4 sàn **458,16 nghìn tỷ đồng, +26%**; Shopee **57,5%**, TikTok Shop **39,6%**; TikTok Shop doanh thu +93% | VietnamPlus 12/03/2026, https://www.vietnamplus.vn/so-ke-thi-phan-voi-shopee-tiktok-shop-tang-truong-doanh-thu-den-93-nam-post1098486.vnp | [TBT đối chiếu] |
| Shopee Live 11/11/2025 | *"hơn 45 triệu sản phẩm"* bán qua livestream và video cả chiến dịch (thông cáo) | https://dantri.com.vn/kinh-doanh/hon-45-trieu-san-pham-ban-ra-qua-livestream-va-video-tai-shopee-1111-20251114173947860.htm | [Chưa kiểm lại] |

**Trong hồ sơ, số thị trường Việt Nam luôn ghi dạng khoảng có hai nguồn** (429,7–458,16 nghìn tỷ đồng; TikTok Shop khoảng
40%), vì cả hai là ước tính từ dữ liệu thu thập, không phải số sàn công bố. Không dùng số AccessTrade (không rõ năm,
chưa mở bài gốc).

---

## 4. Bài báo khoa học 2024–2026

Thư mục (tên, tác giả, ngày, nơi đăng) của **mọi bài arXiv** dưới đây đã được tổng biên tập đối chiếu qua arXiv API
(https://export.arxiv.org/api/query), và của **mọi DOI** qua Crossref API (https://api.crossref.org/works/). Nội dung
"đóng góp chính" lấy từ tóm tắt; câu nào chỉ có trong báo cáo gốc thì ghi rõ.

### 4.1 Thí nghiệm switchback và giao thoa thời gian

| Bài | Nơi đăng | Đóng góp (tóm tắt) | Liên hệ LiveLift | Mức |
|---|---|---|---|---|
| Bojinov, Simchi-Levi, Zhao — *Design and Analysis of Switchback Experiments* | Management Science 69(7):3759–3777, 2023 · https://doi.org/10.1287/mnsc.2022.4583 | Thiết kế tối ưu theo bậc carryover; suy luận chính xác dựa vào cơ chế gán | Nền lý thuyết đang dùng (khối biên 2m) | [TBT đối chiếu] |
| Hu, Wager — *Switchback Experiments under Geometric Mixing* | arXiv 2209.00197, v4 13/12/2025 | Burn-in cải thiện đáng kể tốc độ hội tụ khi có carryover | Đã dùng: burn-in b = 1 phút, độ nhạy {0, 2, 3} | [TBT đối chiếu] thư mục; nội dung [Chưa kiểm lại] |
| Xiong, Chin, Taylor — *Data-Driven Switchback Experiments: Theoretical Tradeoffs and Empirical Bayes Designs* | arXiv 2406.06768, 06/2024 | Dùng dữ liệu lịch sử chọn độ dài khối | Đã có quy trình chọn X bằng mô phỏng (`PREREGISTRATION.md` mục 3) | [TBT đối chiếu] thư mục |
| Wen, Shi, Yang, Tang, Zhu — *Unraveling the Interplay between Carryover Effects and Reward Autocorrelations in Switchback Experiments* | arXiv 2403.17285 (v7 08/2025); báo cáo gốc ghi ICML 2025 | Hiệu quả thiết kế phụ thuộc độ lớn carryover và tự tương quan nhiễu | Ước lượng hai đại lượng này từ phiên thăm dò | [TBT đối chiếu] thư mục |
| Jia, Kallus, Yu — *Clustered Switchback Designs for Experimentation Under Spatio-temporal Interference* | arXiv 2312.15574, v5 03/2025 | Switchback theo cụm không gian × thời gian | Chỉ khi chạy nhiều shop song song | [TBT đối chiếu] thư mục |
| Yu, Ma, Liu — *Minimax Optimal Design with Spillover and Carryover Effects* | arXiv 2501.14602, 01/2025 | Có cả lan tỏa và carryover | Tham khảo cho pilot nhiều shop | [TBT đối chiếu] thư mục |
| **Liu, Zhong — *Randomization Tests in Switchback Experiments*** | arXiv 2602.23257, 26/02/2026 | *"finite-sample valid, distribution-free p-values … using only the known assignment mechanism"*; có kiểm định chân trời carryover và kiểm định non-anticipation | **Hợp nhất với mẫu nhỏ**; đã được nhắc trong `PREREGISTRATION.md`; dùng làm chẩn đoán carryover | [TBT đối chiếu] |
| Zeng, Adjaho, Bucarey, Qin, Zhang, Hoban, Johari, Wager — *Sequentially-Rerandomized Switchback Experiments* | arXiv 2604.02489, 02/04/2026 | Tái ngẫu nhiên hóa theo biến tiên lượng; biến thể *blocked* cho carryover bậc 1 | **Đã áp dạng khả thi** (cân bằng transition) trong bộ sinh lịch | [TBT đối chiếu] thư mục |
| Pankratev — *Powerful Switchback Experiments — Or Not?* | arXiv 2606.03012, 02/06/2026 | Phương sai do cú sốc vĩ mô bị phạt theo mất cân bằng cỡ cụm | Phiên đông/vắng chênh nhau → đưa vào mô phỏng công suất | [TBT đối chiếu] thư mục; trích dẫn nội dung [Chưa kiểm lại] |
| **Pankratev (DoorDash) — *Design-Aware Variance Reduction for Switchback Experiments: A Comparative Study*** | arXiv 2606.27662, v2 20/08/2026 | *"with ten or fewer clusters, the confidence intervals of all four methods contain the true effect only about 82% of the time rather than the intended 95%"* | Lý do giữ kiểm định ngẫu nhiên hóa làm kết luận chính; CUPED/CUPAC chỉ phụ | [TBT đối chiếu] |
| Missault, Masoero (Amazon) — *Carryover detection in switchback experimentation* | NeurIPS 2025 Workshop; https://www.amazon.science/publications/carryover-detection-in-switchback-experimentation | *"Existing estimators require specifying an influence period, i.e. an upper bound on carryover duration, often guessed from intuition. We propose a statistical test that detects when this…"* | Kiểm lại giả định "carryover ≤ 1 khối" sau pilot | [TBT đối chiếu] phần tóm tắt; tên hội thảo [Chưa kiểm lại] |
| Min và cộng sự (11 tác giả) — *Towards Reliable Social A/B Testing* | arXiv 2602.08569, 09/02/2026 | Phân cụm đồ thị xã hội + CUPAC; báo cáo gốc ghi triển khai tại Kuaishou | Không phải thí nghiệm livestream | [TBT đối chiếu] thư mục |
| Wu, Wen, Zhang, Zhu, Li, Shi — *Designing Time Series Experiments in A/B Testing with Transformer Reinforcement Learning* | arXiv 2602.01853, 02/02/2026 | Thiết kế bằng transformer + RL | **Không học** (phá lịch niêm phong trước) | [TBT đối chiếu] thư mục |

Nguồn công nghiệp khác: Statsig switchback có *"Assignment window size"* và burn-in/burn-out
(https://docs.statsig.com/experiments/types/switchback-tests, [Chưa kiểm lại]); DoorDash blog 2018
(https://careersatdoordash.com/blog/switchback-tests-and-randomized-experimentation-under-network-effects-at-doordash/).

### 4.2 Kinh tế học và quản trị về livestream thương mại

Ngoài bốn bài ở mục 1.6:

| Bài | Nơi đăng | Đóng góp | Liên hệ LiveLift | Mức |
|---|---|---|---|---|
| Meng, Mathmann, Wang — *Emotional valence transitions in livestreaming: Elevate engagement but sabotage sales* | JAMS 54(4):1101–1121, 2026 · https://doi.org/10.1007/s11747-026-01169-x | *"80,600 minute-level observations and 12,949 product pitches across 1,308 livestreams"*; đổi cảm xúc thường xuyên làm tương tác tăng rồi giảm, doanh số giảm | Dữ liệu phút × lượt giới thiệu giống LiveLift | [TBT đối chiếu] |
| Chen, Hu, Lu, Hong — *Two Streams to Success* | POM 35(6):2302–2320, 2026 · https://doi.org/10.1177/10591478251403725 | Học sâu tách vai trò thông tin và quan hệ của live | Biến điều chỉnh nếu có transcript | [TBT đối chiếu] |
| Feng, Rong, Tian, Wang, Yao — *When Persuasion Is Too Persuasive* | POM 34(12):3978–3997, 2025 · https://doi.org/10.1177/10591478231224949 | So phiên live với phiên phát lại chỉ khác ở tương tác trực tiếp → hàng trả về cao hơn khi tương tác mạnh | Thêm **tỷ lệ hoàn/hủy** làm chỉ số an toàn | [TBT đối chiếu] |
| Guo, Zhang, Goh, Peng — *Can Social Technologies Drive Purchases in E-Commerce Live Streaming?* | POM 34(12):4039–4059, 2025 · https://doi.org/10.1177/10591478241276131 | Lời kêu gọi hành động (CTA) xã hội của người dẫn và hành vi mua | Nếu thử CTA thì là một can thiệp **khác**, không trộn với ghim | [TBT đối chiếu] |
| Huang, Morozov — *The Promotional Effects of Live Streams by Twitch Influencers* | Marketing Science 44(4):916–932, 2025 · https://doi.org/10.1287/mksc.2022.0400 | *"a small and positive effect"*; báo cáo gốc ghi hiệu ứng tan trong vài giờ | Click tức thời hợp switchback hơn đơn hàng (có thể trễ) | [TBT đối chiếu] thư mục |
| Gu, Zhao, Wu — *A Model of Shoppertainment Live Streaming* | Management Science 71(8):6816–6835, 2025 · https://doi.org/10.1287/mnsc.2023.01724 | Người dẫn có "băng thông" hữu hạn giữa thông tin và giải trí | Khung lý thuyết cho giá trị của ghim (kênh thông tin không tốn lời nói) | [TBT đối chiếu] |
| Zhang, Shi, Liang, Xue — *Birds of a feather: How influencer-brand fit drives product sales in livestream commerce* | JAMS 54(4):1144–1165, 2026 · https://doi.org/10.1007/s11747-026-01187-9 | (báo cáo gốc chưa ghi tác giả; tổng biên tập bổ sung qua Crossref) | Tham khảo phụ | [TBT đối chiếu] thư mục |
| Luo, Lim, Cheah, Lim, Dwivedi — *Live Streaming Commerce: A Review and Research Agenda* | Journal of Computer Information Systems 65(3):376–399 · https://doi.org/10.1080/08874417.2023.2290574 | Báo cáo gốc trích *"causal insights on LSC remain scarce"* từ kết quả tìm kiếm | Chỉ trích câu này sau khi đọc bản gốc | [TBT đối chiếu] thư mục; câu trích [Chưa kiểm lại] |

### 4.3 Hệ thống, dataset và AI từ công nghiệp

| Bài | Nơi đăng | Nội dung | Liên hệ LiveLift | Mức |
|---|---|---|---|---|
| Qu và cộng sự (10 tác giả) — *KuaiLive: A Real-time Interactive Dataset for Live Streaming Recommendation* | arXiv 2508.05633, v2 24/04/2026, *"Accepted by SIGIR 2026"* | Dữ liệu Kuaishou 05/2025: click, bình luận, like, quà; **không có dữ liệu mua hàng**. Giấy phép ghi khác nhau giữa trang dataset (CC BY-NC-SA 4.0) và tóm tắt (CC BY-NC-ND 4.0) | Chỉ để ước lượng hình dạng tự tương quan cho mô phỏng; phi thương mại; đọc file LICENSE trước | [TBT đối chiếu] thư mục; giấy phép [Chưa kiểm lại] |
| Guo và cộng sự — *KuaiLive-M3* | arXiv 2607.24862, 26/07/2026 | Đa phương thức, đa miền | Ít liên quan | [TBT đối chiếu] thư mục |
| Lu, Cao và cộng sự — *LiveForesighter* (Kuaishou) | arXiv 2502.06557, 02/2025, *"Work in progress"* | Báo cáo gốc trích: hành vi giá trị (quà, mua) *"always require users to watch for a long-time (>10 min)"* | Hỗ trợ khối ≥ 10 phút; đơn hàng trễ so với phơi nhiễm | [TBT đối chiếu] thư mục; câu trích [Chưa kiểm lại] |
| Yang, Liu và cộng sự (17 tác giả) — *SARM: LLM-Augmented Semantic Anchor for End-to-End Live-Streaming Ranking* | arXiv 2602.09401, 02/2026 | Xếp hạng live có LLM | Chỉ tham khảo xu hướng | [TBT đối chiếu] thư mục (báo cáo gốc ghi "Kuaishou", chưa đối chiếu) |
| Chen — *VerbalValue: A Socially Intelligent Virtual Host for Sales-Driven Live Commerce* | arXiv 2605.14542, *"Accepted to the CVPR 2026 HiGen Workshop"* | Người dẫn ảo trả lời theo ý định người xem | Gần với "gợi ý trả lời cho người dẫn"; phải tách khỏi can thiệp chính | [TBT đối chiếu] thư mục |
| Hu và cộng sự — *TLive-Omni* | arXiv 2608.20958, 21/08/2026 | Mô hình đa phương thức cho live commerce | LiveLift chỉ cần nhật ký ghim có dấu thời gian | [TBT đối chiếu] thư mục |
| Zhu, Qiang, Bai, Liu, Ouyang — *Chinese Morph Resolution in E-commerce Live Streaming Scenarios* | arXiv 2512.23280, 29/12/2025 | Người dẫn 抖音 dùng từ biến âm để lách kiểm duyệt; dataset 86.790 mẫu | Bộ lọc PII và radar ý định cần chuẩn hoá biến thể (LiveLift đã có `nlp/normalize.py`) | [TBT đối chiếu] |
| Yu và cộng sự — *Leveraging Tripartite Interaction Information from Live Stream E-Commerce* (LSEC) | arXiv 2106.03415, 2021 | Hai dataset người dẫn–người dùng–sản phẩm **có hành vi mua**, công bố tại https://github.com/yusanshi/LSEC-GNN | **Phản ví dụ** cho câu "không có dataset công khai có tín hiệu mua hàng" của báo cáo gốc; chưa rõ có chuỗi thời gian trong phiên | [TBT đối chiếu] (người kiểm chứng tải bài) |

**Khoảng trống, diễn đạt thận trọng:** *"Trong phạm vi khảo sát của nhóm (09/2026), chưa tìm thấy công bố dùng thiết kế
switchback trong phiên livestream để đo hiệu ứng ghim sản phẩm, và chưa tìm thấy dataset công khai có chuỗi số liệu theo
phút trong phiên kèm lịch can thiệp."* Không viết "chưa ai làm" hay "chưa có dataset nào có dữ liệu mua hàng" (đã có LSEC).

### 4.4 NLP tiếng Việt và lọc PII

| Bài/tài nguyên | Nơi đăng | Nội dung | Liên hệ LiveLift | Mức |
|---|---|---|---|---|
| Nguyen, Phan, Nguyen, Nguyen — *ViSoBERT* | arXiv 2310.11166, *"Accepted at EMNLP'2023 Main Conference"* | Mô hình ngôn ngữ đơn ngữ cho văn bản mạng xã hội tiếng Việt; báo cáo gốc trích *"available only for research purposes"* | Ổn cho cuộc thi/bài báo; thương mại hoá phải xin phép | [TBT đối chiếu] thư mục; giấy phép [Chưa kiểm lại] |
| Nguyen, Nguyen, Nguyen — *ViSoLex* | arXiv 2501.07020, COLING 2025 | Kho mã chuẩn hoá từ vựng mạng xã hội tiếng Việt | So sánh với `nlp/normalize.py` hiện có | [TBT đối chiếu] thư mục |
| Tran, Pham, Luu, Nguyen — *ViGoEmotions* | arXiv 2602.08371, *"Accepted as main paper at EACL 2026"* | 27 nhãn cảm xúc; báo cáo gốc chưa ghi tác giả, tổng biên tập bổ sung | Tham khảo quy trình gán nhãn | [TBT đối chiếu] thư mục |
| Le, Hoang, Ha — *Meddies-PII* | arXiv 2609.12544, 11/09/2026 | PII lâm sàng đa ngôn ngữ, có tiếng Việt; hứa công bố dataset khi được chấp nhận | Theo dõi; khác miền với bình luận live | [TBT đối chiếu] thư mục |
| Vats và cộng sự — *REDACT* | arXiv 2606.19881, 18/06/2026 | Benchmark PII theo **dạng bề mặt** (số viết chữ, chèn dấu cách…); chưa rõ có tiếng Việt | Mở rộng test `test_obfuscated_phone_scrubbed` hiện có | [TBT đối chiếu] thư mục |
| Rajgarhia và cộng sự — *An Evaluation Study of Hybrid Methods for Multilingual PII Detection* | arXiv 2510.07551, 10/2025 | Luật + mô hình cho PII đa ngôn ngữ | Ủng hộ kiến trúc regex + NER | [TBT đối chiếu] thư mục |

---

## 5. Công nghệ và chính sách mới của nền tảng 2025–2026

| Nền tảng | Có gì mới | Nguồn | Mức | Ý nghĩa cho LiveLift |
|---|---|---|---|---|
| **TikTok Shop** | Quy tắc LIVE mua sắm (Seller University **Mỹ**): *"Don't use non-real-time verbal interaction such as AI-generated voices, audio recordings, or radio."*; *"Don't use animated figures or content that covers more than 50% of the screen."* **Chưa rõ áp dụng cho Việt Nam**; bài không nêu ngày hiệu lực | Social Media Today 15/06/2026, https://www.socialmediatoday.com/news/tiktok-bans-ai-generated-voices-in-shopping-livestreams/822977/ | [TBT đối chiếu] | Không thiết kế can thiệp dựa trên giọng AI; người dẫn là người thật |
| **Shopee Live** | Trang *"Using AI in Shopee Live: Guidelines & Requirements"* (SG, MY) tồn tại nhưng render JS, chưa trích được nội dung; 03/2026 Sea thử live với "bản sao số" người nổi tiếng được cấp phép | https://seller.shopee.sg/edu/article/24882 · https://finance.yahoo.com/news/sea-tests-ai-celebrity-live-191350855.html | [Chưa kiểm lại] | Nếu đối tác dùng AI host thì ghi là điều kiện thí nghiệm |
| **YouTube Shopping** | Tự xoay vòng sản phẩm ghim 60 giây; nên sắp xếp sản phẩm trước buổi live | https://support.google.com/youtube/answer/12299016 | [Đã kiểm] phần xoay vòng | Tắt xoay vòng trong phiên switchback (tài liệu YouTube cùng ngày) |
| **Facebook/Instagram** | Không còn gắn thẻ sản phẩm trong live | mục 2.1 | [Chưa kiểm lại] | Chỉ còn link đo click `/r/{code}` — đúng thiết kế chỉ số chính |
| **Whatnot** | 07/08/2026 gọi vốn 545 triệu USD, định giá 20 tỷ USD; GMV live 2025 = 8 tỷ USD | https://www.tubefilter.com/2026/08/07/whatnot-series-g-funding-round-545-million-live-shopping/ | [Chưa kiểm lại] | Dẫn chứng quy mô (không phải VN) |
| **Công cụ phân tích bên thứ ba** (Kalodata, FastMoss, EchoTik) | *"Every GMV number you see in any of them is a model output, not a ledger entry."*; *"None of them have a data feed from Seller Center."* | MediaLabs 12/08/2026, https://medialabs-co.com/blog/kalodata-vs-fastmoss-vs-echotik | [Chưa kiểm lại], [Thứ cấp] | Không dùng làm biến kết quả |

**Pháp lý Việt Nam liên quan** (đối chiếu ngày 17/09/2026):

- **Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15**, ban hành 26/06/2025, **hiệu lực 01/01/2026**
  (https://chinhphu.vn/?pageid=27160&docid=214590&classid=1&typegroupid=3). **[TBT đối chiếu]**
- **Nghị định 356/2025/NĐ-CP** quy định chi tiết Luật trên, ban hành 31/12/2025, hiệu lực 01/01/2026
  (https://vanban.chinhphu.vn/?pageid=27160&docid=216387). **[TBT đối chiếu]**. Việc Nghị định này thay Nghị định
  13/2023/NĐ-CP đã được đội xác minh ở `docs/competition/sang-tao-tre-2026/01-CHIEN-LUOC.md`. Lưu ý: một số tệp hồ sơ vẫn
  viện dẫn Nghị định 13/2023 như căn cứ hiện hành (`05-BAN-KE-KHAI.md`, `06-KHO-MA-VA-MINH-CHUNG.md`,
  `phan-bien-du-kien.md`) → việc 37 trong `VIEC-CAN-LAM.md`.
- **Luật Thương mại điện tử 2025, hiệu lực 01/07/2026:** người livestream bán hàng phải cung cấp thông tin để nền tảng
  **xác thực danh tính** (https://nghiencuu.tapchikinhtetaichinh.vn/luat-thuong-mai-dien-tu-2025-khung-phap-ly-moi-cho-livestream-ban-hang-va-tiep-thi-lien-ket-157230.html,
  đăng 26/05/2026). **[Thứ cấp]**; số hiệu 122/2025/QH15 và điều khoản cụ thể chưa đối chiếu văn bản gốc.

---

## 6. Bảng "phương pháp → áp dụng cho LiveLift", xếp theo giá trị trên công sức

Cách xếp: nhóm **A** giá trị cao, công sức ≤ 0,5 ngày; **B** giá trị cao, 1–3 ngày; **C** giá trị trung bình hoặc cần dữ
liệu chưa có; **Đ** = **đã có trong kho**, chỉ cần trích bằng chứng. Mốc: **P0** trước 30/09, **P1** trước hackathon
10–11/10, **P2** trước chung kết 20–22/11, **P3** sau cuộc thi. Tình trạng "đã có" do tổng biên tập đọc mã và
`PREREGISTRATION.md` ngày 17/09/2026.

| Hạng | Phương pháp | Nguồn | Giá trị | Công sức | Mốc | Làm cụ thể | Việc trong VIEC-CAN-LAM |
|---|---|---|---|---|---|---|---|
| A1 | Trích **bằng chứng công nghiệp** cho switchback trong phòng live | 快手 2021, 美团 2025, Swiggy XP | Cao — trả lời "phương pháp lạ?" | 2 giờ | P0 | ½ trang "Bằng chứng từ thị trường đi trước" trong thuyết minh | 29 |
| A2 | Trích **bằng chứng có đối chứng** để đặt kỳ vọng hiệu ứng | MISQ 2025 (~40%), ISR 2025 (+3,00%/−12,55%), ISR 2026 (+25% khi có Q&A) | Cao — biện minh cỡ mẫu và radar câu hỏi | 2 giờ | P0 | Ghi đúng điều kiện kèm theo (mục 1.6); nói thẳng MDE vài phần trăm cần nhiều phiên | 29 |
| A3 | Án lệ cào dữ liệu + quy định 2026 làm lý do **chỉ API chính thức** | Mục 1.2, 1.5 | Cao | 1 giờ | P0 | Một đoạn trong mục đạo đức/pháp lý | 29 |
| A4 | Định vị **shop tự phát sóng** | 店播 50% GMV live 618/2025 | Cao | 1 giờ | P0 | Một câu định vị + lý do kỹ thuật (đủ khối) | 29 |
| A5 | Số thị trường VN dạng **khoảng hai nguồn** | Metric, YouNet ECI | Trung bình, tránh bị bắt lỗi | 30 phút | P0 | Sửa mọi con số thị trường trong hồ sơ | 29 |
| A6 | **Giao thức phiên**: một can thiệp/phiên; nhãn tài trợ cố định suốt phiên; khai báo trước quảng cáo, GMV Max, 福袋, không đổi giữa phiên; tắt xoay vòng ghim YouTube; người dẫn là người thật | Swiggy "pod", ASCI/DoCA, 巨量引擎 福袋, arXiv 2406.14380, YouTube Help, TikTok Seller University US | Cao — chặn biến gây nhiễu rẻ nhất | 0,5 ngày | P0 | Thêm ô vào `ops/templates/nhat-ky-phien.md` (hiện chỉ có "Ngân sách quảng cáo") và một đoạn trong `PREREGISTRATION.md` trước khi khoá | 30 |
| A7 | Viết lại câu **khoảng trống** thận trọng | Mục 4.3 (có LSEC 2021) | Trung bình | 30 phút | P0 | Dùng đúng câu ở mục 4.3 | 29 |
| Đ1 | Kiểm định ngẫu nhiên hóa làm kết luận chính; cảnh báo CI chuẩn cụm hụt độ phủ | Bojinov 2023, Liu–Zhong 2026, Pankratev 2026 (~82%) | Cao | **Đã có** (`analysis/estimators.py`) | P0 (trích) | Thêm trích dẫn Pankratev 2026 vào lý do chọn phân tích | 29 |
| Đ2 | Burn-in khai báo trước + độ nhạy | Hu–Wager, Statsig, 美团 | Cao | **Đã có** (b = 1, {0, 2, 3}) | — | — | — |
| Đ3 | Ngẫu nhiên hóa có cân bằng đầu/giữa/cuối + cân bằng transition | 美团 (ngẫu nhiên hoàn toàn, phân tầng), Zeng 2026 | Cao | **Đã có** (`core/assigner/outer.py`) | — | Trích 美团 làm bằng chứng công nghiệp | 29 |
| Đ4 | Chuẩn hóa theo viewer-giây | Pankratev 2026, POM 2025 | Cao | **Đã có** (`y_b` / 1.000 viewer-giây) | P1 (kiểm) | Kiểm lại tử số gồm **mọi** mã `/r/` trong khối, không chỉ sản phẩm được ghim | 31 |
| Đ5 | Làm mù người dẫn với số theo khối | MISQ 2025 (người dẫn ứng biến theo số) | Cao | **Đã có** (màn `/host` làm mù, quy tắc L6) | P0 (trích) | Trích MISQ 2025 làm lý do trong hồ sơ | 29 |
| Đ6 | Nhật ký ghim/bỏ ghim có dấu thời gian, tuân thủ dẫn xuất, ITT + LATE | 千川 `explain_status` | Cao | **Đã có** (`assignment_event`, `exposure_event`, `derive_compliance`) | — | — | — |
| B1 | **`analysis/carryover.py`**: `ht_lag1`, cổng "gắn cờ, không loại"; chẩn đoán m = 0 so với m = 1 | Liu–Zhong 2026, Missault–Masoero 2025, 快手 | Cao | 2–3 ngày | P2 | Hiện mô-đun **chỉ là kế hoạch, chưa có mã** | 34 |
| B2 | Trường **`data_status` (provisional/settled)**; kết luận nhân quả chỉ dùng số đã chốt | FAQ 罗盘 (chưa kiểm lại), TikTok số theo phút sau phiên | Cao | 0,5–1 ngày | P1 | Áp cho mọi số nền tảng kéo về (TikTok Shop, Shopee) | 32 |
| B3 | **Tổng click cả khối** bên cạnh click sản phẩm được ghim, báo "tạo thêm hay chuyển dịch" | Xie–Sharma–Mehra POM 2025 | Cao | 0,5–1 ngày | P1 | Chỉ số phụ trong báo cáo phiên | 31 |
| B4 | **Chỉ số an toàn** tỷ lệ hủy/trả đơn theo khối | ISR 2025, Feng POM 2025 | Trung bình–cao | 1 ngày | P2 | Dùng đơn nhập CSV/TikTok Shop/Shopee; hiện kho chưa có | 35 |
| B5 | **Mô phỏng công suất có mất cân bằng cỡ cụm** | Pankratev 2026 (2606.03012), 神策 | Cao | 2 ngày | P2 | Dùng phân phối người xem của 16 buổi live-fire; báo MDE theo kịch bản | 36 |
| B6 | **Bộ kiểm thử PII theo dạng bề mặt** 200–300 ca tổng hợp | REDACT, arXiv 2510.07551 | Trung bình–cao | 1 ngày | P1 | Mở rộng test hiện có, không dùng dữ liệu thật | 33 |
| C1 | Thẻ **"10 phút gần nhất vs 10 phút trước"** trên màn điều hành (không phải màn người dẫn) | 视频号 `getlivedata` | Trung bình (dễ hiểu với người bán) | 1 ngày | P1 | Nhãn "so sánh mô tả, chưa phải nhân quả"; **không** hiện trên `/host` | 32 |
| C2 | Biến cơ chế radar: thời gian từ câu hỏi mua tới lúc người dẫn đáp | ISR 2026 (Q&A +25%) | Trung bình | 2–3 ngày | P2 | Cần cách đánh dấu lúc đáp; chỉ khi có đủ bình luận qua kênh chính thức | 38 |
| C3 | Trang **复盘** (phễu, ma trận 2×2, 五维四率 rút gọn) tách khỏi kết quả nhân quả | Diễn đàn nghề TQ | Trung bình (demo) | 2 ngày | P2 | Ghi rõ lớp nào là mô tả | 38 |
| C4 | **Mã khối trong nội dung chuyển khoản/mã đơn** cho shop chốt đơn qua chat | UPI `tr` (NPCI) | Trung bình | 1 ngày tra VietQR + 1 ngày mã | P2 | Tra đặc tả VietQR/NAPAS trước khi cam kết | 38 |
| C5 | **Dataset nhỏ ẩn danh** (số/phút + lịch gán + nhật ký ghim) + datasheet | Khoảng trống mục 4.3 | Trung bình | 2 ngày | P2–P3 | Không có văn bản bình luận | 38 |
| C6 | So sánh ViSoLex với `nlp/normalize.py` | ViSoLex 2025 | Trung bình–thấp | 2–3 ngày | P3 | Kiểm giấy phép trước | — |
| C7 | Gợi ý trả lời bình luận cho người dẫn bằng LLM | VerbalValue 2026, ISR 2026 | Thấp cho thí nghiệm | 2–3 ngày | P3 | Chỉ chạy **ngoài** phiên thí nghiệm | — |
| C8 | Ngẫu nhiên hóa theo tài khoản/shop, switchback theo cụm nhiều shop | AMCIS 2021, Jia–Kallus–Yu, Yu–Ma–Liu | Cao về lâu dài | 5+ ngày | P3 | Khi có ≥ 5 shop đối tác | — |

---

## 7. Không nên làm

| Việc | Vì sao | Nguồn |
|---|---|---|
| Đọc bình luận kiểu người xem (tiện ích trình duyệt, tự động hoá trang, WebSocket dịch ngược, OCR, dịch vụ cào) | Quyết định chủ dự án 17/09/2026; án lệ 100 và 490 vạn NDT | mục 1.5 |
| Mua hoặc dùng số liệu của 蝉妈妈, 飞瓜, Kalodata, FastMoss, EchoTik, 라방바 데이터랩 làm biến kết quả | Là ước lượng mô hình, không công bố cách thu thập; có vụ thua kiện | mục 1.4, 1.5, 5 |
| Tiện ích tự động bật sản phẩm hay tự trả lời bình luận | Không chính thức; trái quyết định 17/09 | mục 1.4 |
| Thí nghiệm hai phía 2×2 | Cần nền tảng kiểm soát phía người xem | mục 1.7 |
| Người dẫn số/AI host trước chung kết | Bằng chứng có đối chứng yếu nếu thiếu Q&A; TikTok Shop Mỹ cấm giọng AI trong LIVE mua sắm; thêm biến nhiễu | mục 1.6, 5 |
| Tự xây app hay sàn phát live | Bulbul, Simsim, Grip: độc lập thì lỗ hoặc đóng | mục 2.1, 3.1 |
| Thiết kế bằng transformer + RL; SRSB đầy đủ | Phá tính "niêm phong lịch trước"; dạng khả thi của blocked-SRSB đã áp | mục 4.1 |
| Phát 福袋 hay đổi ngân sách quảng cáo giữa phiên thí nghiệm | Làm phình tương tác và traffic theo khối | mục 1.7 |
| Dùng KuaiLive làm bằng chứng hiệu ứng ghim | Không có dữ liệu mua; giấy phép phi thương mại | mục 4.3 |
| Mượn lập luận "dữ liệu tự công khai được miễn" của Ấn Độ cho Việt Nam | Khác khung pháp lý; quy tắc hiện hành của LiveLift chặt hơn | mục 2.3 |
| Đưa vào hồ sơ số thị trường không rõ nguồn (AccessTrade, WhatsApp commerce Ấn Độ) hay số tiếp thị của nhà cung cấp người dẫn số | Không kiểm chứng được | mục 1.6, 3.2 |
| Mua Statsig/Eppo | Chỉ cần học cách đặt cửa sổ gán và burn-in | mục 4.1 |

---

## 8. Câu hỏi còn mở

1. Bản MIS Quarterly 2025 (~40%) và bản AMCIS 2021 (18,6%) khác nhau ở mẫu, thời gian hay đặc tả? Cần đọc toàn văn trước khi
   trích.
2. 抖店开放平台/巨量百应 có API ghi "讲解/弹窗" cho nhà cung cấp dịch vụ không? 快手电商开放平台 có API số liệu phòng live không?
3. `percentile` trong API 视频号 so với nhóm nào?
4. FAQ 罗盘 về "hiệu chỉnh lần hai, lấy số ngày hôm sau": cần trích nguyên văn.
5. 《直播电商监督管理办法》 (2026) thay thế hay song song với 《网络直播营销管理办法（试行）》 (2021)?
6. Quy tắc cấm giọng AI trong LIVE mua sắm của TikTok Shop có áp dụng cho Việt Nam không, hiệu lực từ ngày nào?
7. Nội dung *"Using AI in Shopee Live: Guidelines & Requirements"* cho Shopee Việt Nam?
8. Carryover của ghim sản phẩm ngắn (vài phút) hay dài (vài giờ)? Chỉ trả lời được bằng pilot.
9. Giấy phép thật của KuaiLive và ViSoBERT cho sản phẩm dự thi công khai?
10. Đặc tả VietQR/NAPAS: nội dung chuyển khoản có giữ nguyên tới sao kê người bán không, giới hạn độ dài?
11. Luật Quảng cáo Việt Nam và quy định người có ảnh hưởng khi livestream có yêu cầu nhãn tài trợ tương tự DoCA/ASCI không?
12. Momentum Works bản đầy đủ có số riêng cho Việt Nam không (bản trả phí)?

---

## Phụ lục A. Những gì tổng biên tập đã sửa hoặc bỏ so với báo cáo gốc

| Báo cáo gốc viết | Xử lý | Căn cứ |
|---|---|---|
| Cho người dẫn Taobao xem số thời gian thực: +18,6% (AMCIS 2021) là bằng chứng chính | **Đổi** sang MIS Quarterly 2025 (~40%) làm trích dẫn chính; AMCIS chỉ là bản hội nghị sơ bộ, ghi đủ điều kiện | aisel.aisnet.org (MISQ và AMCIS) |
| ISR 2025 (trợ lý AI): "hiệu ứng thật của AI chỉ vài phần trăm" | **Sửa** thành "trong thí nghiệm này +3,00%"; trợ lý phục vụ người mua | Kiểm chứng độc lập: đúng một phần |
| ISR người dẫn số: +25% từ dữ liệu 328 sản phẩm | **Sửa**: +25% đến từ thí nghiệm thứ hai với nhà bán tạp hóa | Kiểm chứng độc lập |
| arXiv 2406.14380 có bối cảnh Weixin Channels | **Bỏ** chi tiết này; tóm tắt chỉ ghi *"a major short-video platform"* | arXiv |
| Vụ 小红书–蝉妈妈: chung thẩm TAND trung cấp Hàng Châu | **Bỏ** tên tòa (bài nguồn không nêu) | news.qq.com 24/05/2025 |
| Storyboard18 không nêu tên hãng nghiên cứu thị trường | **Sửa**: bài dẫn Grand View Research | storyboard18.com |
| "Không tìm thấy dataset công khai nào có tín hiệu mua hàng" | **Thu hẹp**: đã có LSEC (2021) có hành vi mua; khoảng trống chỉ là chuỗi theo phút trong phiên kèm lịch can thiệp | arXiv 2106.03415 |
| Nhiều khuyến nghị (burn-in, ngẫu nhiên hóa cân bằng, chuẩn hóa viewer-giây, làm mù người dẫn, nhật ký ghim) như việc mới | **Đánh dấu "đã có"** | `PREREGISTRATION.md`, `analysis/`, `core/assigner/`, `web/src/app/host/page.tsx` |
| Hồ sơ nên "đối chiếu với Nghị định 13/2023 đang dùng" (báo cáo Ấn Độ) | **Sửa**: căn cứ hiện hành là Luật 91/2025/QH15 + Nghị định 356/2025/NĐ-CP | chinhphu.vn, vanban.chinhphu.vn |
| Tác giả ViGoEmotions, *Birds of a feather*, bài PII lai "chưa xác minh" | **Bổ sung** tác giả | arXiv API, Crossref API |
| Số 京东 +30%, tách thị phần Metric 56,04%/41,31%, số AccessTrade | **Không dùng** (chỉ có tóm tắt tìm kiếm) | — |
