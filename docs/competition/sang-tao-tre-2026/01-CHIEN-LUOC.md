# 01 — CHIẾN LƯỢC ĐOẠT GIẢI NHẤT BẢNG C
## Cuộc thi Sáng tạo trẻ Quốc gia trong lĩnh vực Trí tuệ nhân tạo năm 2026 (TW Đoàn)

*Soạn 14/09/2026 · Đội LiveLift — Ngô Bình Minh, Lê Xuân Khánh, Ngô Lâm Tiến · Khoa CNTT, ĐH Tôn Đức Thắng*
*Trạng thái đội: **đã được ĐH Tôn Đức Thắng cử** → hạn nộp **30/9/2026**, **vào thẳng Vòng Khu vực**, không qua Vòng loại Quốc gia. Còn **16 ngày**.*

> **Quy tắc của tài liệu này:** mọi khẳng định về thế giới bên ngoài đều kèm URL hoặc trỏ
> vào file gốc trong máy. Chỗ nào không tìm được thì ghi thẳng **"KHÔNG TÌM THẤY"** kèm
> việc phải làm để lấp. Không suy đoán, không bịa số hiệu văn bản, không bịa tên dự án.

---

## 0. TÓM TẮT ĐIỀU HÀNH — KHUYẾN NGHỊ DỨT KHOÁT

**1. GIỮ LiveLift. TÁI ĐỊNH VỊ TRIỆT ĐỂ. KHÔNG ĐỔI ĐỀ TÀI.**
Rubric Bảng C có 8 trọng tâm, **6 trong số đó là về phương pháp, dữ liệu, kiểm chứng, rủi
ro và đạo đức** — đúng mặt mạnh nhất của LiveLift. Chỉ trọng tâm số 1 (cấp thiết / tác
động) là điểm yếu, và **đó là vấn đề đóng gói, không phải vấn đề bản chất**. Khung định vị
mới + 3 phương án câu mở đầu: **§3**.

**2. RỦI RO BỊ LOẠI VÌ "SAI NHÓM CHỦ ĐỀ": THẤP.** Trang Bảng C chính thức đặt tên chủ đề là
**"AI cho Phát triển kinh tế - xã hội"**, thể lệ liệt kê thẳng *"sản xuất, quản lý, ... phát
triển kinh tế - xã hội"*, và **`MẪU 3` không có ô nào để chọn nhóm chủ đề** — không tồn tại
cơ chế hành chính để loại hồ sơ vì lý do này. Chi tiết + việc phải gọi BTC xác nhận: **§1.1**.

**3. PHÁT HIỆN QUYẾT ĐỊNH GIẢI NHẤT: đội đang chuẩn bị cho 40% và bỏ trống 60%.**
Vòng Khu vực 10–11/10 tại TP.HCM là **hackathon 2 ngày trên bộ dữ liệu thô lạ + yêu cầu
thực tiễn do BTC ra** — LiveLift **không được dùng ở vòng đó**. Hồ sơ LiveLift chỉ chiếm
40%. **Đội có thể có hồ sơ xuất sắc nhất cuộc thi mà vẫn trượt.** Toàn bộ chương **§5** dành
cho việc này, gồm dự báo dạng dữ liệu, bộ "đồ nghề hackathon" phải dựng trước, quy trình 48
giờ chia việc 3 người, và cách ghi điểm khác biệt khi cả phòng đều dùng LLM.

**4. VIỆC ĐÒN BẨY CAO NHẤT CHO HỒ SƠ (40%): XÓA CON SỐ "0 PHIÊN THÍ NGHIỆM THẬT".**
Chạy 2–3 phiên switchback thật trước 28/09, dù phòng chỉ 5–15 người xem, dù kết quả null.
"0 phiên" là lỗ hổng chí mạng ở trọng tâm **1, 5 và 7 cùng lúc**. "3 phiên thật, kết quả
chưa kết luận được, MDE 60%, và đây là lý do" là một câu trả lời **mạnh**; "0 phiên" thì
không có câu trả lời nào cả.

**5. RỦI RO LIÊM CHÍNH ĐANG BỊ BỎ QUA: lịch sử commit.** 42 commit của repo **đều mang một
tác giả duy nhất "LiveLift Team"**, mỗi commit gói trọn một ngày công việc lớn. Thể lệ bắt
nộp commit history thật + Prompt Log đầy đủ và yêu cầu phân định *"phần đội tự xây / phần AI
tạo ra / phần kế thừa nguồn mở"*. **Tuyệt đối không viết lại lịch sử git** (đó mới đúng là
giả mạo) — nhưng phải sửa cách làm từ hôm nay. Chi tiết: **§4 trọng tâm 4** và **§8**.

---

## 1. SỰ THẬT ĐÃ XÁC MINH VỀ CUỘC THI

### 1.1 Câu hỏi sống còn: "nhóm chủ đề do BTC công bố" là gì?

Thể lệ viết (file gốc `AI2026_Ke hoach_The le_phathanh.pdf`, trang 11):

> *"**Bảng C:** - Hình thức thi: Đội thi nộp hồ sơ dự án thuộc các nhóm chủ đề, lĩnh vực
> do Ban Tổ chức công bố. **Dự án cần hướng tới giải quyết vấn đề thực tiễn, có giá trị
> ứng dụng trong học tập, đời sống, sản xuất, quản lý, dịch vụ công, phát triển kinh tế -
> xã hội hoặc phục vụ cộng đồng.**"*

Và (trang 3, lặp lại ở trang 9):

> *"Ban Tổ chức sẽ công bố một số nhóm chủ đề gợi ý và/hoặc bộ dữ liệu công khai để thí
> sinh lựa chọn; **thí sinh có thể sử dụng dữ liệu tự thu thập** nếu bảo đảm tuân thủ quy
> định về quyền riêng tư, bản quyền và dữ liệu cá nhân."*

**Kết quả truy tìm ngày 14/09/2026 — đã quét 8 nguồn:**

| Nguồn | Tìm thấy gì |
|---|---|
| [ai.tainangviet.vn/bang-thi/C](https://ai.tainangviet.vn/bang-thi/C) | **Chủ đề Bảng C ghi một dòng duy nhất: "AI cho Phát triển kinh tế - xã hội".** Kèm 5 "kỹ năng trọng tâm": thiết kế hệ thống AI · dữ liệu và mô hình · chỉ số đo lường · bảo mật · đạo đức AI. **Không có danh sách nhóm chủ đề chi tiết, không có bộ dữ liệu công khai** |
| [ai.tainangviet.vn](https://ai.tainangviet.vn/) (trang chủ) | Không công bố danh sách chủ đề hay dataset |
| [ai.tainangviet.vn/ho-so](https://ai.tainangviet.vn/ho-so) | Chỉ liệt kê thành phần hồ sơ Bảng C; không có danh mục chủ đề |
| [ai.tainangviet.vn/faq](https://ai.tainangviet.vn/faq) | Không có câu hỏi nào về danh mục chủ đề. **Nhưng có một chi tiết cực kỳ quan trọng: "Bảng C: Hackathon trực tiếp 2 ngày trên dataset và bài toán xã hội nóng BTC cung cấp"** — hai chữ *"xã hội nóng"* không có trong thể lệ PDF, đây là thông tin bổ sung từ chính BTC |
| [ai.tainangviet.vn/lo-trinh](https://ai.tainangviet.vn/lo-trinh) | Chỉ mốc thời gian. Xác nhận Vòng Khu vực miền Nam **10–11/10/2026 tại TP.HCM** |
| [tainangviet.vn/ai-art120/](https://tainangviet.vn/ai-art120/) — Thông báo tổ chức, đăng **25/07/2026** | Không liệt kê nhóm chủ đề. Có nêu BTC *"dự kiến triển khai chương trình huấn luyện chuyên đề, tập huấn, hội thảo và tọa đàm"* |
| `ai.tinhoctre.vn` / `sangtao-ai.tinhoctre.vn` | Chuyển hướng 301 về `ai.tainangviet.vn` — **không phải site riêng, không có nội dung riêng** |
| [263.org.vn/Ke-hoach-The-le-cuoc-thi-Sang-tao-tre-AI-2026](https://263.org.vn/Ke-hoach-The-le-cuoc-thi-Sang-tao-tre-AI-2026) | Chuyển hướng 301 thẳng sang Google Drive `14VhnJ0NB_UUtVdRr3DpKCmOU1hu9kh36` — **chính là file PDF đội đã tải về**. **Không có phụ lục, biểu mẫu hay hướng dẫn nào khác** ngoài `AI2026_Mẫu hồ sơ.docx` |
| [facebook.com/cytast.twd](https://www.facebook.com/cytast.twd/) (fanpage CYTAST — cơ quan thường trực BTC) | **KHÔNG ĐỌC ĐƯỢC** — Facebook chặn truy cập tự động. **Việc phải làm: một thành viên mở fanpage bằng tài khoản cá nhân, kéo hết bài đăng từ 25/07/2026 đến nay, chụp lại mọi thông báo về Bảng C.** Đây là kênh có xác suất cao nhất còn sót thông tin |

**PHÁN QUYẾT: KHÔNG TÌM THẤY danh sách "nhóm chủ đề gợi ý" chi tiết. Nhưng rủi ro bị loại
về hình thức là THẤP.** Ba căn cứ:

1. Chủ đề Bảng C công bố chính thức là **"AI cho Phát triển kinh tế - xã hội"** — livestream
   thương mại thuộc kinh tế số, nằm đúng tâm chủ đề.
2. Thể lệ liệt kê thẳng **"sản xuất, quản lý, ... phát triển kinh tế - xã hội"** trong các
   lĩnh vực được chấp nhận.
3. **`MẪU 3` — mẫu hồ sơ bắt buộc của Bảng C — KHÔNG có ô nào để khai "nhóm chủ đề" hay
   "lĩnh vực".** Đã trích toàn văn 13 mục từ `AI2026_Mẫu hồ sơ.docx`: trang đầu là bảng
   thông tin 3 thí sinh, rồi đi thẳng vào *"1. Bài toán hoặc vấn đề thực tiễn cần giải
   quyết"*. **Không tồn tại cơ chế hành chính để loại một hồ sơ vì "sai nhóm chủ đề".**

**Một dấu hiệu nữa cho thấy danh sách chủ đề sẽ đến muộn:** cùng cơ quan thường trực (Trung
tâm Phát triển KHCN và Tài năng trẻ — CYTAST) tổ chức Hội thi Tin học trẻ toàn quốc, và ở
hội thi đó họ công bố chủ đề bằng **một công văn riêng, ra sau kế hoạch gốc**: Công văn
**số 30-CV/KHCN ngày 11/3/2026** giới thiệu chủ đề Bảng D1 là *"Tìm hiểu, khám phá cuộc sống
xung quanh em"*, căn cứ Kế hoạch 441-KH/TWĐTN-KHCN ngày 10/02/2026
([bản gốc PDF](https://tainangviet.vn/source/files/THT2026_CV_trien_khai_hoi_thi_signed.pdf)).
**Nếp làm việc của họ là: kế hoạch trước, chủ đề sau, bằng công văn riêng.** Hãy trông đợi
một công văn tương tự cho AI 2026, và rất có thể chủ đề hackathon Bảng C chỉ được mở ngay
tại điểm thi ngày 10/10.

**VIỆC PHẢI LÀM (P0, 15 phút, hôm nay):** gọi **0988.086.273 (đ/c Nguyễn Sỹ Vinh)** — hoặc
**0344 268 982 (đ/c Đoàn Quang Trung, chuyên viên Phòng KHCN, CYTAST)**, số lấy từ công văn
30-CV/KHCN nêu trên — hỏi đúng ba câu:
1. *"Bảng C đã công bố danh mục nhóm chủ đề gợi ý chưa? Nếu có thì ở đâu ạ?"*
2. *"Dự án về công cụ đo lường hiệu quả cho hộ kinh doanh bán hàng livestream có thuộc nhóm
   'AI cho phát triển kinh tế - xã hội' không ạ?"*
3. *"Bộ dữ liệu và đề bài của hackathon Bảng C có được công bố trước ngày thi không, hay mở
   đề tại chỗ ạ?"* ← **câu này quan trọng nhất, quyết định toàn bộ §5**

Ghi lại ngày giờ gọi, tên người trả lời, nội dung trả lời **vào chính file này**. Trước khi
có xác nhận đó, coi rủi ro là *"thấp nhưng chưa bằng không"*.

### 1.2 ĐÍNH CHÍNH BRIEF — một chỗ đang sai, sửa trước khi nó vào hồ sơ

| Chỗ | `BRIEF-THE-LE.md` đang ghi | Sự thật trong file gốc | Hệ quả |
|---|---|---|---|
| Số hiệu kế hoạch | *"Kế hoạch số 01-KH/TWĐTN-KHCN ngày 03/7/2026"* | Bản PDF phát hành ghi **`Số:    -KH/TWĐTN-KHCN`** và **`Hà Nội, ngày   tháng   năm 2026`** — **bỏ trống cả số lẫn ngày** | **Nếu trích số hiệu này vào hồ sơ, đội đang bịa một số hiệu văn bản của TW Đoàn.** Xóa ngay. Chỉ được viết: *"Kế hoạch của Ban Bí thư Trung ương Đoàn về tổ chức Cuộc thi Sáng tạo trẻ Quốc gia trong lĩnh vực Trí tuệ nhân tạo năm 2026"*, dẫn nguồn [263.org.vn](https://263.org.vn/Ke-hoach-The-le-cuoc-thi-Sang-tao-tre-AI-2026) |

Ngoài chỗ trên, BRIEF trích thể lệ **chính xác**: 8 trọng tâm đánh giá Bảng C đã đối chiếu
từng chữ với trang 11–12 của PDF gốc — khớp hoàn toàn. 13 mục MẪU 3 — khớp hoàn toàn. Yêu
cầu Vòng Khu vực — khớp hoàn toàn.

*(BRIEF cũng nói "hai đường vào". Thể lệ thực ra có **ba**: tỉnh/thành đoàn cử — tối đa 05
đội Bảng C/tỉnh, tr.8; trường CĐ/ĐH/học viện cử — tối đa 05 đội, tr.9; và tự do qua Vòng
loại. Vì trường đã cử đội rồi nên chi tiết này không còn giá trị hành động, chỉ ghi lại cho
đúng hồ sơ.)*

### 1.3 Bản đồ trọng số — hiểu đúng thì mới phân bổ đúng 16 ngày

```
GIẢI NHẤT BẢNG C — chỉ 01 giải cho toàn quốc
│
├── Xét vào Chung kết = 40% hồ sơ ban đầu + 60% Vòng Khu vực
│   ├── 40%  Hồ sơ MẪU 3 (≤20 trang) + video thuyết trình ≤5' + video demo ≤5'
│   │        + Prompt Log + kho mã nguồn + bản kê khai AI   ← LiveLift ở ĐÂY
│   │        Hạn: 30/9/2026 (trường đã cử → nộp thẳng, không qua Vòng loại)
│   │
│   └── 60%  HACKATHON 2 NGÀY, 10–11/10/2026, TP.HCM
│            BTC cấp 01 bộ dữ liệu THÔ + 01 yêu cầu thực tiễn
│            ("bài toán xã hội nóng" — theo FAQ chính thức)
│            ← LiveLift KHÔNG ở đây. Đây là 60% đang bỏ trống.
│
└── Chung kết 20–22/11, Hà Nội (tối đa 05 đội Bảng C/khu vực vào)
    ├── Kiểm tra hồ sơ + XÁC MINH SẢN PHẨM
    ├── Thử thách cải tiến 12 GIỜ (tối ưu hệ thống · đánh giá mô hình ·
    │   bảo mật · kiểm soát đầu ra · tích hợp dữ liệu/API/RAG/AI Agent)
    ├── Trình diễn + phản biện kỹ thuật chuyên sâu
    └── ĐIỀU KIỆN CỨNG: sản phẩm chạy ổn định trên môi trường trực tuyến
        ≥48 GIỜ trước kiểm tra và suốt phiên chấm.
        Không truy cập được do lỗi chủ quan → điểm vận hành CÓ THỂ TÍNH 0.
```

**Ba hệ quả không được quên:**
- **Hồ sơ chỉ là 40%.** Hồ sơ hoàn hảo mà hackathon yếu thì không vào Chung kết.
- **Vòng Khu vực chấm trên một bài toán đội chưa từng thấy.** Thứ chuyển giao được từ
  LiveLift sang đó là **quy trình, kỷ luật đánh giá và mã hạ tầng dùng lại được** — không
  phải bài toán livestream.
- **Điều kiện 48 giờ online là điều kiện loại.** LiveLift hiện **chưa có URL công khai nào**
  (`docker-compose.yml` + Caddy đã sẵn sàng nhưng chưa triển khai lần nào). Deploy sớm, đừng
  để tháng 11.

Thêm một dữ kiện về mật độ cạnh tranh ở Vòng Khu vực: ngoài đội trường cử và tỉnh/thành đoàn
cử, thể lệ (tr.13, khoản 4.2.3) còn mở cửa **đặc cách tối đa 50 đội/01 miền** cho nhóm thí
sinh dự Vòng Khu vực Hội thi Tin học trẻ toàn quốc 2026 và học sinh giỏi Toán/Tin quốc gia,
cộng **tối đa 20 đội tự do/bảng/khu vực**. **Vòng Khu vực miền Nam Bảng C sẽ đông.** Vào được
Vòng Khu vực không phải là đã gần giải.

---

## 2. LIVELIFT CÓ PHÙ HỢP KHÔNG — PHÁN QUYẾT THẲNG

### 2.1 Chấm LiveLift trên chính 8 trọng tâm của BTC (không tự khen)

| # | Trọng tâm | Trạng thái | Vì sao |
|---|---|---|---|
| 1 | Cấp thiết, giá trị thực tiễn, **khả năng tác động** | ⚠️ **YẾU** | Bài toán thật nhưng **0 người dùng thật, 0 phiên thật, 0 thư xác nhận của nhà bán**. "2,5 triệu phiên/tháng" là số thị trường, không phải tác động của LiveLift |
| 2 | Tính khoa học, logic, phù hợp của phương pháp | ✅ **RẤT MẠNH** | Switchback 2 tầng theo Bojinov–Simchi-Levi–Zhao (2023), kiểm định ngẫu nhiên hóa studentized, Fisher CI, Hájek IPW, OLS-Lin, LATE. Gần như chắc chắn không đội sinh viên nào có thứ tương đương |
| 3 | Chất lượng & **tính hợp lệ** của dữ liệu | ✅ mạnh, ⚠️ 2 lỗ | Lọc PII tiếng Việt recall ≥95% chạy **trước** khi ghi đĩa; 3 nguồn hợp lệ khai rõ; live-fire 19.126 bình luận thật qua API chính thức. Lỗ: (a) `collectors/tiktok_public` là vùng xám; (b) trích dẫn pháp lý phải cập nhật (xem §7 — tin tốt: hai văn bản README đang dẫn đều **đúng**) |
| 4 | **Mức độ làm chủ** mô hình/kiến trúc/quy trình | ✅ kỹ thuật mạnh, 🔴 **bằng chứng yếu** | Kỹ thuật rõ ràng. Nhưng **42 commit đều mang một tác giả duy nhất "LiveLift Team"**, commit gói trọn từng ngày lớn. Giám khảo được yêu cầu soi commit history + Prompt Log để phân biệt *"đội tự xây / AI tạo ra / kế thừa nguồn mở"*. **Rủi ro lớn nhất chưa ai xử lý** |
| 5 | Kết quả thử nghiệm, **khả năng kiểm chứng đầu ra** | ✅ mạnh trên mô phỏng, 🔴 **trống trên thực địa** | A/A 200 lặp bác bỏ 4,5% (danh nghĩa 5%, p nhị thức 0,872); coverage 95,5%; MDE 20,1% đo bằng sweep; 993 test nhanh + 16 gate Monte-Carlo; 41 sự cố có root cause. Nhưng **0 phiên ngẫu nhiên thật** — toàn bộ bằng chứng nhân quả là mô phỏng |
| 6 | Phân tích, so sánh phương án, tối ưu, xử lý rủi ro | ✅ **RẤT MẠNH** | Sổ sự cố 41 mục có nguyên nhân gốc + gate chặn tái diễn; bảng ánh xạ knob→ICC 400 phiên; lưới SBC có "răng" (lỗi tiêm vào làm ô đỏ đúng như phải thế); so sánh 3 nhóm công cụ đối thủ; tự phát hiện và sửa công thức MDE sai (30,1% → 20,1%) |
| 7 | Sáng tạo, khả thi, **triển khai / mở rộng / duy trì** | ⚠️ **YẾU** | Chưa deploy công khai lần nào; phụ thuộc nền tảng đội không sở hữu (TikTok **đã đo và thất bại**); mô hình giá chưa phỏng vấn WTP nào; 300k quảng cáo chỉ ra 5–15 người xem đồng thời, hụt mục tiêu ~10 lần |
| 8 | An toàn, bảo mật, **đạo đức AI**, trách nhiệm | ✅ mạnh, ⚠️ thiếu 1 mục | Khử nhận dạng tại ingest, salt xoay theo phiên, không lưu chuỗi hành vi cá nhân, làm mù màn hình host ở **cấp kiểu dữ liệu** (model riêng 4 trường). Thiếu: **"phương án kiểm soát đầu ra"** — MẪU 3 mục 11 hỏi thẳng, hồ sơ hiện chưa trả lời tách bạch |

**Tổng: 3 trọng tâm rất mạnh, 2 mạnh-có-lỗ, 2 yếu, 1 rủi ro liêm chính.**
**Không có trọng tâm nào mà LiveLift *không thể* ăn điểm.**

### 2.2 Bốn nghi ngờ trong đề bài — trả lời từng cái

**(a) "Bài toán thương mại/B2B, trong khi cuộc thi của Đoàn thiên về học tập, đời sống,
dịch vụ công, cộng đồng."**

Đúng một nửa, và nửa đúng đó đã được xử lý bằng thể lệ. Thể lệ **tự tay liệt kê** *"sản
xuất, quản lý, phát triển kinh tế - xã hội"* **ngang hàng** với *"dịch vụ công"* và *"phục
vụ cộng đồng"*; trang Bảng C chính thức đặt tên chủ đề là **"AI cho Phát triển kinh tế -
xã hội"** ([nguồn](https://ai.tainangviet.vn/bang-thi/C)).

Vấn đề **không phải** LiveLift sai chủ đề. Vấn đề là **hồ sơ hiện đang tự kể mình như một
sản phẩm SaaS cho doanh nghiệp** — "nền tảng thí nghiệm", "moat phương pháp", "gói Pro
990k/tháng", "Agency 3,9M" — chứ không kể mình như **một công cụ bảo vệ người bán nhỏ khỏi
việc ra quyết định mù**. Đó là lỗi đóng gói, sửa bằng cách viết lại, không phải bằng cách
đổi đề tài. **§3** là bản sửa.

**(b) "0 phiên thí nghiệm ngẫu nhiên thật."**

Đây là điểm yếu **thật và nghiêm trọng nhất**. Nhưng cũng là điểm yếu **rẻ nhất để sửa**: hệ
thống đã chạy trọn vòng đời phiên trên giao diện (`/chay-phien`, 4 bước không cần gõ lệnh),
đã live-fire **19.126 bình luận thật** qua API trên 16 buổi live / 7 ngành hàng, đã có link
đo `/r/{code}` do chính đội vận hành. **Thiếu duy nhất là bấm nút chạy trên một buổi live
thật của chính đội.** Chạy 2–3 phiên trong 16 ngày là hoàn toàn khả thi và đổi được nhiều
điểm nhất trên mỗi đồng công sức (§4, hành động #1).

**(c) "Bộ phân loại ý định chỉ đạt macro-F1 0,271 trên chat thật."**

**Đây không phải điểm yếu. Đây là tài sản — nếu kể đúng cách.** Thể lệ Bảng C có nguyên một
trọng tâm về *"khả năng kiểm chứng đầu ra"*, một trọng tâm về *"phân tích... hạn chế, rủi ro"*,
và Điều 5 nghiêm cấm *"giả mạo... dữ liệu thử nghiệm"*. Một đội **tự đo lại số đẹp của chính
mình trên dữ liệu thật, phát hiện nó sụp từ 0,870 xuống 0,271, thua cả baseline luôn đoán
"khác", ghi vào sổ sự cố, và từ chối huấn luyện lại khi chưa có nhãn** — đó chính xác là thứ
mọi hội đồng nói họ muốn thấy nhưng gần như không bao giờ được thấy.

Cách kể bắt buộc: **luôn quote cặp 0,870 / 0,271**, kèm phát hiện sâu hơn trong
`docs/benchmarks/live-fire-da-nguon.md` §4 — *precision nhãn hành động chạy từ **1,3% đến
67,9%** tuỳ buổi, và nguyên nhân là **tỷ lệ nền** ý định mua của buổi đó (0,0% → 48,0%) chứ
không phải model; độ tự tin dùng được TRONG một phiên (AUC 0,696) nhưng KHÔNG so sánh được
GIỮA các phiên*. Đó là **một kết luận khoa học có giá trị**, không phải một thất bại.
**Nhưng phải rút radar ý định ra khỏi vị trí "tính năng chính"** — nó là một thành phần đang
được đánh giá, không phải một tính năng đã dùng được.

**(d) "Phụ thuộc nền tảng mà đội không sở hữu."**

Thật, và không giấu được. Cách xử lý gồm ba phần:
1. Đưa vào **đúng mục 11 (rủi ro) và mục 12 (hướng phát triển)** của MẪU 3, kèm bảng khả năng
   theo nền tảng đã có sẵn (`docs/nen-tang-ho-tro.md`, 8 nền tảng) và **bằng chứng đã đo
   TikTok thất bại** — đo rồi báo thất bại mạnh hơn là không đo.
2. Nhấn mạnh đúng sự thật kỹ thuật: **biến kết quả chính của LiveLift là lượt nhấp hợp lệ
   qua link chuyển hướng `/r/{code}` do chính đội vận hành** — không phụ thuộc API của nền
   tảng nào. Nền tảng chỉ cấp tín hiệu phụ (bình luận, người xem).
3. Dùng **ma trận tín hiệu** (`GET /sessions/{id}/signals`) làm câu trả lời có cấu trúc:
   *"nguồn này cho tín hiệu gì → đo được năng lực gì → thiếu tín hiệu nào thì tuyên bố thẳng
   là không đo được"*. Đây là thiết kế đúng, và nó biến một điểm yếu thành một minh chứng
   về khả năng phân tích rủi ro (trọng tâm 6).

### 2.3 PHÁN QUYẾT

**GIỮ LiveLift. TÁI ĐỊNH VỊ. KHÔNG ĐỔI ĐỀ TÀI.** Lý do xếp theo sức nặng:

1. **6/8 trọng tâm là về phương pháp, dữ liệu, kiểm chứng, rủi ro, đạo đức.** Đề tài nào khác
   cũng phải xây lại toàn bộ nền đó từ đầu — bất khả thi trong 16 ngày.
2. **Điểm yếu duy nhất mang tính bản chất (trọng tâm 1) là điểm yếu về CÁCH KỂ.** Livestream
   bán hàng không hề xa "đời sống": hàng chục nghìn hộ kinh doanh và người bán nhỏ đang sống
   bằng nó.
3. **Đổi sang một bài toán "được lòng Đoàn hơn" (y tế / giáo dục / nông nghiệp) sẽ đặt đội
   vào đúng vùng đông đối thủ nhất, với một sản phẩm 2 tuần tuổi** — cách chắc chắn nhất để
   thua. Xem §6.
4. **Bản sắc trung thực của LiveLift khớp với văn hoá chấm của Đoàn hơn cả chủ đề.** Thể lệ
   dành hẳn Điều 5 cho liêm chính, bắt nộp Prompt Log đầy đủ, cấm giả mạo dữ liệu thử nghiệm.
   Một đội mang theo sổ sự cố 41 mục và một con số **tự bác bỏ chính mình** là đội duy nhất
   trong phòng chứng minh được điều đó bằng **vật chứng** thay vì lời hứa.

---

## 3. KHUNG TÁI ĐỊNH VỊ — LÀM SAO MỘT BÀI TOÁN B2B ĂN ĐIỂM Ở CẢ 8 TRỌNG TÂM

### 3.1 Bốn phép đổi trục (làm đúng bốn cái này là xong 80%)

| Đang kể | Phải đổi thành | Vì sao |
|---|---|---|
| **Đối tượng:** "nhà bán / doanh nghiệp / agency" | **"hộ kinh doanh và người bán nhỏ — trong đó phần lớn là thanh niên khởi nghiệp"** | Chuyển từ *khách hàng B2B* sang *nhóm yếu thế cần được bảo vệ*. Đây là ngôn ngữ Đoàn đọc được |
| **Giá trị:** "tăng doanh thu / tăng tỷ lệ chuyển đổi" | **"giúp người bán nhỏ không mất tiền vào quyết định sai và vào 'bí kíp' vô căn cứ"** | Tránh doanh thu thuần; nói về **giảm lãng phí** và **chống thông tin sai** — cả hai đều là giá trị cộng đồng |
| **Bản chất sản phẩm:** "nền tảng thí nghiệm / experimentation platform / SaaS" | **"hạ tầng đo lường nhân quả — một lớp hạ tầng dùng chung cho kinh tế số"** | "Hạ tầng" là từ khoá của Nghị quyết 57. "Nền tảng SaaS" là từ khoá của gọi vốn |
| **Điểm nhấn khoa học:** "moat phương pháp, đối thủ không có" | **"công cụ tự chứng minh và tự bác bỏ được kết luận của chính nó"** | Đổi từ *lợi thế cạnh tranh* sang *liêm chính khoa học*. Trọng tâm 5 và 8 ăn thẳng |

### 3.2 Ba phiên bản câu mở đầu — chọn một, dùng thống nhất cho MẪU 3 mục 1, video thuyết trình, và slide đầu

**PHƯƠNG ÁN A — "Người bán nhỏ" (khuyến nghị dùng làm câu mở đầu chính)**

> *"Ở Việt Nam có hơn 50.000 nhà bán đang sống bằng livestream, với khoảng 2,5 triệu phiên
> mỗi tháng. Phút 30 họ ghim sản phẩm B; phút 35 doanh thu tăng 40%. Do ghim sản phẩm? Do
> thuật toán vừa đẩy thêm 500 người xem? Do người dẫn kể chuyện hay? **Không ai biết — nên
> phần lớn "kinh nghiệm" mà cả ngành đang mua đi bán lại chỉ là sự trùng hợp được đặt tên.**
> LiveLift là hạ tầng đo lường nhân quả biến mỗi quyết định trong một buổi live thành một
> thí nghiệm có kết quả đo được, để người bán nhỏ biết cái gì thật sự ra tiền — thay vì phải
> tin lời đồn."*

Vì sao mạnh: kể bằng một cảnh cụ thể, đặt nhân vật là người bán nhỏ, và chốt bằng một mệnh
đề **chống thông tin sai lệch** — thứ hội đồng Đoàn đọc là giá trị cộng đồng.

**PHƯƠNG ÁN B — "Kinh tế số / Nghị quyết 57" (dùng làm đoạn 2 của mục 1, phần "tính cần
thiết trong bối cảnh hiện nay")**

> *"Nghị quyết 57-NQ/TW ngày 22/12/2024 của Bộ Chính trị đặt mục tiêu đến năm 2030 kinh tế
> số đạt tối thiểu 30% GDP. Thương mại qua livestream đang là mũi tăng trưởng nhanh nhất
> của kinh tế số Việt Nam. Nhưng một ngành tăng trưởng bằng kinh nghiệm truyền miệng thì
> không thể tăng năng suất: **không đo được nhân quả thì không tối ưu được gì, chỉ lặp lại
> may rủi ở quy mô lớn hơn.** LiveLift xây đúng lớp hạ tầng còn thiếu đó — lớp đo lường — và
> mở mã nguồn theo AGPL-3.0 để nó trở thành hạ tầng dùng chung chứ không phải công cụ độc
> quyền của một công ty."*

Vì sao mạnh: nối thẳng vào chủ trương bằng **số hiệu văn bản đúng và chỉ tiêu trích đúng**
(xem §7), và câu cuối biến giấy phép AGPL từ một chi tiết kỹ thuật thành một cam kết cộng đồng.

**PHƯƠNG ÁN C — "Liêm chính dữ liệu trong thời đại AI" (dùng làm câu chốt mục 1 và câu mở
đầu video thuyết trình)**

> *"Trong thời đại AI, cái nguy hiểm không phải là thiếu số liệu — mà là **có số liệu sai mà
> vẫn tin**. Mọi dashboard đều trả lời được "bao nhiêu"; gần như không dashboard nào dám trả
> lời "có phải do bạn làm không". LiveLift được xây để trả lời đúng câu hỏi đó. Và để chứng
> minh chúng em nói thật: chính hệ thống này đã **tự bác bỏ một con số đẹp của chính chúng
> em** — bộ phân loại ý định đạt macro-F1 0,870 trên bộ tự biên soạn nhưng chỉ còn **0,271**
> trên chat bán hàng thật, thua cả cách đoán bừa. Chúng em đã đo, đã ghi vào sổ sự cố, và
> không giấu."*

Vì sao mạnh: đây là **thứ không đội nào khác trong phòng dám nói**, và nó ăn thẳng vào trọng
tâm 5 (kiểm chứng đầu ra), trọng tâm 8 (đạo đức, trách nhiệm) và Điều 5 (liêm chính).

**CÁCH DÙNG ĐƯỢC KHUYẾN NGHỊ:** MẪU 3 mục 1 = **A** (đoạn 1) → **B** (đoạn 2) → **C** (đoạn
chốt). Video thuyết trình 5 phút mở bằng **C**, vì 15 giây đầu phải làm giám khảo ngẩng đầu lên.

### 3.3 Ánh xạ khung mới vào từng trọng tâm — câu nào ăn điểm nào

| Trọng tâm | Câu/bằng chứng phải xuất hiện trong hồ sơ |
|---|---|
| 1. Cấp thiết, tác động | Phương án A + B. Số thị trường có nguồn. **Và ≥2 phiên thật + ≥3 xác nhận của người bán thật** (xem §4) |
| 2. Khoa học, logic | Sơ đồ 2 tầng; trích Bojinov et al. 2023, Hu–Wager 2022, Lin 2013; giải thích **vì sao switchback chứ không A/B chia người** (không chia được người xem trong một phòng live) |
| 3. Dữ liệu hợp lệ | Bảng 3 nguồn × giấy phép × cơ sở pháp lý; lọc PII chạy **trước** khi ghi đĩa; trích **Luật 91/2025/QH15** + **NĐ 356/2025/NĐ-CP** (§7) |
| 4. Làm chủ | Bản kê khai AI chi tiết + phân công từng người từng phân hệ + commit bằng tên thật từ nay |
| 5. Kiểm chứng đầu ra | A/A 4,5%, coverage 95,5%, MDE 20,1%, 1.009 test, **cặp 0,870/0,271**, cơ chế `estimable=False` |
| 6. Phân tích, rủi ro | Sổ sự cố 41 mục; bảng ablation ICC; tự sửa MDE 30,1%→20,1%; bảng so sánh 3 nhóm đối thủ |
| 7. Triển khai, duy trì | **URL công khai chạy được** + Docker một lệnh + AGPL-3.0 + lộ trình; bảng khả năng 8 nền tảng |
| 8. An toàn, đạo đức | Làm mù ở cấp kiểu dữ liệu; salt xoay theo phiên; **mục "phương án kiểm soát đầu ra" viết riêng**; trích **Luật TTNT 134/2025/QH15** (§7) |

---

## 4. BẢN ĐỒ ĐIỂM — 8 TRỌNG TÂM, CHẤM 1–10, VÀ HÀNH ĐỘNG XẾP THEO ĐÒN BẨY

### 4.1 Chấm hiện trạng (14/09/2026)

| # | Trọng tâm | Điểm | Bằng chứng cho điểm này |
|---|---|---:|---|
| 1 | Cấp thiết, giá trị thực tiễn, khả năng tác động | **4/10** | Bài toán có bằng chứng bình duyệt (Xie–Sharma–Mehra, POM 2025: thời lượng ghim vs doanh thu có dạng chữ U ngược) và số thị trường có nguồn. Nhưng: **0 phiên thật, 0 người dùng ngoài đội, 0 thư xác nhận, 0 phỏng vấn WTP**. Tác động hiện là *giả thuyết* |
| 2 | Tính khoa học, logic, phù hợp của phương pháp | **9/10** | Switchback 2 tầng (Bojinov–Simchi-Levi–Zhao 2023), burn-in thay washout (Hu–Wager 2022), kiểm định ngẫu nhiên hóa studentized vẽ lại **bằng chính hàm gán production trên toàn lịch**, Fisher CI qua nghịch đảo kiểm định, Hájek IPW, OLS FE + tương tác Lin (2013), LATE qua IV. Mất 1 điểm vì chưa có bản giải thích 1 trang cho giám khảo **không chuyên thống kê** |
| 3 | Chất lượng dữ liệu, quy trình xử lý, tính hợp lệ nguồn | **7/10** | Lọc PII tiếng Việt recall ≥95%/loại chạy **trước khi ghi đĩa** (SĐT viết chữ, teencode, 2 thế hệ đơn vị hành chính); 19.126 bình luận thật qua API chính thức, 16 buổi, 7 ngành hàng; hiệu chỉnh mô phỏng bằng KuaiLive 1,16M phòng shop thật. Trừ điểm: `collectors/tiktok_public` là vùng xám chưa xử lý dứt; chưa có **bảng nguồn × giấy phép × căn cứ pháp lý** trình bày được |
| 4 | Mức độ làm chủ mô hình/thuật toán/kiến trúc/quy trình | **5/10** | Kỹ thuật thì 9/10. Nhưng trọng tâm này chấm **bằng chứng làm chủ**, và bằng chứng đang yếu: **42/42 commit mang một tác giả duy nhất "LiveLift Team"**; chưa có bản kê khai AI; chưa có phân công ai làm phân hệ nào; Prompt Log chưa được tổ chức thành dạng nộp được |
| 5 | Kết quả thử nghiệm, phương pháp đánh giá, kiểm chứng đầu ra | **7/10** | A/A 200 lặp: bác bỏ 4,5% (danh nghĩa 5%, p nhị thức 0,872); coverage 95,5%; thu hồi tác động biết trước sai lệch −0,3%; MDE 20,1% đo bằng sweep 4 mức × 60 lặp; 993 test nhanh + 16 gate Monte-Carlo; lưới SBC 4/4 xanh và **có răng** (lỗi tiêm vào làm ô đỏ). Trừ nặng vì **0 phiên ngẫu nhiên thật** — toàn bộ là mô phỏng |
| 6 | Phân tích, so sánh phương án, tối ưu, xử lý rủi ro | **8/10** | 41 sự cố có nguyên nhân gốc + gate chặn tái diễn; tự phát hiện và sửa lỗi FATAL "NaN → significance" (52% phiên null bị tuyên có ý nghĩa → 6,2%); tự sửa công thức MDE 30,1% → 20,1%; bảng ánh xạ knob→ICC 400 phiên tách được hai cơ chế; khảo sát 3 nhóm công cụ đối thủ. Trừ vì MẪU 3 **mục 9 (so sánh baseline + ablation)** chưa được viết thành một mục độc lập |
| 7 | Sáng tạo, khả thi, triển khai, mở rộng, duy trì | **5/10** | Docker một lệnh + Caddy HTTPS + 9 migration + backup verify + CI 5 job. Nhưng **chưa từng deploy công khai**; TikTok đã đo và thất bại; 300k đồng quảng cáo chỉ ra 5–15 người xem đồng thời (hụt mục tiêu 80 khoảng 10 lần); giá gói chưa phỏng vấn ai |
| 8 | An toàn thông tin, bảo mật, đạo đức AI, trách nhiệm | **7/10** | Khử nhận dạng tại ingest; salt xoay theo phiên; không lưu chuỗi hành vi cá nhân; **làm mù màn hình host ở cấp kiểu dữ liệu** (model riêng 4 trường — không phải ẩn bằng CSS); `RESULTS_FREEZE_UNTIL` cưỡng chế tiền đăng ký; AGPL-3.0. Trừ vì thiếu hẳn mục **"phương án kiểm soát đầu ra"** mà MẪU 3 mục 11 hỏi thẳng |

**Tổng ước lượng: 52/80.** Trần thực tế đạt được trong 16 ngày: **~68/80**.

### 4.2 Hành động xếp theo ĐÒN BẨY (điểm thu được ÷ công sức bỏ ra)

| # | Hành động | Nâng trọng tâm | Công | Điểm ước tính | Ai |
|---:|---|---|---|---:|---|
| **1** | **Chạy 2–3 phiên switchback THẬT** trên kênh của chính đội (dù 5–15 người xem, dù kết quả null). Ghi đầy đủ: lịch gán lưu trước phát sóng, seed, nhật ký vận hành, báo cáo sau phiên | 1, 5, 7 | 2 ngày | **+7** | Bình Minh + Lâm Tiến |
| **2** | **Deploy công khai HTTPS** với tên miền thật + trang `/health` + uptime monitor. Đặt link vào hồ sơ để giám khảo tự mở | 7, 5, 1 | 4 giờ | **+4** | Xuân Khánh |
| **3** | **Gói liêm chính:** từ hôm nay commit bằng **tên thật 3 thành viên** (`git config user.name/email`); thêm `CONTRIBUTORS.md` + `docs/phan-cong.md` ghi ai làm phân hệ nào; xuất **Prompt Log đầy đủ có System Prompt**; viết **bản kê khai AI/model/thư viện/dataset/API** với cột *đội tự xây / AI tạo ra / kế thừa nguồn mở*. **KHÔNG viết lại lịch sử git cũ** | 4, 8 | 1 ngày | **+5** | Cả 3 |
| **4** | **Viết lại MẪU 3 đúng 13 mục, ≤20 trang**, theo khung tái định vị §3. Đặc biệt viết **mục 9 (baseline + ablation)** và **mục 11 (kiểm soát đầu ra)** thành mục độc lập, không gộp | 1, 6, 8 | 2 ngày | **+5** | Bình Minh |
| **5** | **Lấy 3–5 xác nhận của người bán thật**: biên bản phỏng vấn có chữ ký/ảnh, hoặc thư đồng ý cho chạy thử trên phòng live của họ. Mẫu thư đã có sẵn `ops/templates/` | 1, 7 | 1 ngày | **+4** | Bình Minh |
| **6** | **Bảng nguồn dữ liệu × giấy phép × căn cứ pháp lý** (1 trang), trích **Luật 91/2025/QH15**, **NĐ 356/2025/NĐ-CP**, **Luật TTNT 134/2025/QH15** (§7). Xử lý dứt điểm `collectors/tiktok_public`: hoặc gỡ khỏi bản nộp, hoặc ghi rõ "không dùng, cách ly bằng CI" | 3, 8 | 3 giờ | **+3** | Xuân Khánh |
| **7** | **Một trang "vì sao switchback chứ không A/B"** vẽ tay được, cho giám khảo không chuyên thống kê | 2, 6 | 2 giờ | **+2** | Lâm Tiến |
| **8** | **Hai video** (thuyết trình ≤5', demo ≤5'), mở bằng Phương án C (§3.2) | 1, 7 | 1 ngày | **+2** | Cả 3 |
| **9** | **Đồng bộ FACT-SHEET ↔ hồ sơ**: TONG-KET-DU-AN.md đang ghi *611 test / 24 sự cố* (bản 07/09) trong khi FACT-SHEET ghi *1.009 test / 41 sự cố* (bản 14/09). **Một giám khảo mở hai file là bắt được** | 4, 6 | 1 giờ | **+2** | Lâm Tiến |

**Tổng nếu làm hết: +34 → ~86/80 lý thuyết, thực tế sẽ về ~68/80 sau khi trừ hao.**

**Nếu chỉ làm được 3 việc, làm #1, #2, #3.** Ba việc đó nâng đúng ba lỗ hổng chí mạng: không
có thực địa, không chạy được cho người ngoài xem, và không chứng minh được là đội tự làm.

---

## 5. CHUẨN BỊ VÒNG KHU VỰC — 60% ĐIỂM, HIỆN ĐANG BỎ TRỐNG

> **Đây là chương quan trọng nhất của tài liệu này.** Hồ sơ LiveLift là 40%. Vòng Khu vực
> là 60%, thi trên **một bài toán đội chưa từng thấy**, và LiveLift **không được dùng**.
> Một đội có hồ sơ xuất sắc nhất cuộc thi vẫn có thể trượt Chung kết ở đây.

### 5.1 Biết chắc những gì (trích thể lệ, trang 11–12 và FAQ chính thức)

| Hạng mục | Nội dung |
|---|---|
| **Thời gian, địa điểm** | **10–11/10/2026, thi trực tiếp tại TP.HCM** (miền Nam). Hackathon **02 ngày** tại điểm thi |
| **Đề bài** | BTC cung cấp **01 bộ dữ liệu THÔ** + **01 yêu cầu thực tiễn** thuộc nhóm chủ đề đã công bố. FAQ chính thức mô tả là **"dataset và bài toán xã hội nóng"** ([nguồn](https://ai.tainangviet.vn/faq)) |
| **Nhiệm vụ** | *"Đội thi sử dụng AI để phân tích dữ liệu, nhận diện vấn đề, tìm ra xu hướng và đề xuất giải pháp phù hợp"* + *"Đề xuất một mô hình/giải pháp giải quyết vấn đề"* |
| **Mốc trong ngày** | BTC công bố **mốc mở đề, kiểm tra tiến độ, hỗ trợ kỹ thuật, nộp bài** trong hướng dẫn thi |
| **Phải nộp** | (1) **Repo GitHub/GitLab có commit history thật**, cấp quyền cho BTC/giám khảo · (2) **Báo cáo kỹ thuật PDF**: phương pháp luận, kiến trúc, mô hình/thuật toán, quy trình huấn luyện/tích hợp, **AI evaluation metrics**, **so sánh baseline/ablation** · (3) **Video demo ≤10 phút có mặt TẤT CẢ thành viên** · (4) **Prompt Log đầy đủ gồm System Prompt và toàn bộ conversation history** + danh mục công cụ AI/mô hình/thư viện/dataset/API/mã tham khảo, **nêu rõ phần đội tự xây / phần AI tạo ra / phần kế thừa nguồn mở** |
| **Người hướng dẫn** | Chỉ được góp ý định hướng; **không được viết mã, xử lý dữ liệu, dựng mô hình hay viết báo cáo thay đội** |

**Đọc kỹ danh sách "phải nộp": nó gần như trùng khít với những gì LiveLift đã có sẵn quy
trình.** Đó là lợi thế chuyển giao lớn nhất của đội, và nó không nằm ở lĩnh vực livestream —
nó nằm ở **kỷ luật giao nộp**.

### 5.2 Dự báo nhóm chủ đề và dạng dữ liệu thô — xếp hạng theo xác suất

**Trạng thái sự thật: BTC CHƯA CÔNG BỐ danh mục nhóm chủ đề (§1.1).** Phần dưới là **suy
luận có căn cứ, KHÔNG phải thông tin từ BTC** — dùng để chuẩn bị, không được trích vào hồ sơ.

Bốn ràng buộc định hình đề bài:
1. **"Bài toán xã hội nóng"** (FAQ) + chủ đề bảng là **"AI cho Phát triển kinh tế - xã hội"**.
2. **2 ngày, 3 sinh viên, máy cá nhân, mạng hội trường** → dữ liệu phải vừa phải: bảng hoặc
   văn bản, cỡ MB–vài trăm MB. Không thể là kho ảnh/video hàng chục GB.
3. **Phải sạch pháp lý** (thể lệ cấm dữ liệu cá nhân trái phép, bắt ẩn danh dữ liệu liên quan
   trẻ em/học sinh/nhà trường) → nghiêng mạnh về **dữ liệu mở, dữ liệu hành chính đã ẩn danh,
   dữ liệu thống kê công khai**.
4. **Phải chấm được khách quan** → cần một chỉ số định lượng rõ (F1, MAE, MAPE…) hoặc một
   sản phẩm phân tích có thể so sánh giữa các đội.

| Hạng | Dạng dữ liệu / bài toán | Xác suất | Vì sao |
|---:|---|---|---|
| **1** | **Văn bản tiếng Việt + nhãn**: phản ánh kiến nghị của người dân, đánh giá dịch vụ công, bình luận mạng xã hội, tin giả/tin độc hại. Bài toán: phân loại · định tuyến · tóm tắt · phát hiện điểm nóng | **CAO** | "Dữ liệu đặc thù Việt Nam (ngôn ngữ)" là mô-típ lặp lại của chính hệ sinh thái Đoàn/Sở KHCN; dễ ẩn danh; nhẹ; chấm bằng macro-F1 rất gọn; và **chống lừa đảo/tin giả đang là chủ đề thắng giải** (xem §8) |
| **2** | **Chuỗi thời gian môi trường/thiên tai**: AQI, quan trắc nước, mưa–lũ, cảnh báo sạt lở. Bài toán: dự báo ngắn hạn · phát hiện bất thường · cảnh báo sớm | **CAO** | Chủ đề "nóng" đúng nghĩa đen; dữ liệu quan trắc công khai; **AI Hackathon 2025 (Sở KHCN TP.HCM) có đội thắng bằng ứng dụng AI cảnh báo sạt lở** ([nguồn](https://plo.vn/ung-dung-ai-canh-bao-sat-lo-gianh-chien-thang-tai-ai-hackathon-2025-post884089.html)); Giải thưởng Tuổi trẻ sáng tạo 2025 vinh danh SAVE.AI cảnh báo lũ quét, sạt lở |
| **3** | **Bảng hành chính – kinh tế xã hội theo tỉnh/xã**: thống kê dân số, lao động–việc làm thanh niên, y tế cơ sở, dịch bệnh theo tuần. Bài toán: phân cụm, dự báo, phát hiện bất bình đẳng vùng miền | **TRUNG BÌNH–CAO** | Rất khớp "phát triển kinh tế - xã hội"; bối cảnh 2026 có **mô hình chính quyền địa phương hai cấp** (được nhắc thẳng trong công văn 30-CV/KHCN của chính CYTAST) → dữ liệu theo đơn vị hành chính mới là chủ đề thời sự |
| **4** | **Giao thông – an toàn giao thông**: lưu lượng, tai nạn, camera đếm xe | **TRUNG BÌNH** | Nóng, có sẵn, nhưng dữ liệu camera nặng và khó ẩn danh |
| **5** | **Giáo dục**: phổ điểm thi, kết quả học tập ẩn danh, khảo sát học đường | **TRUNG BÌNH** | Rất sẵn và rất "Đoàn", nhưng thể lệ bắt **ẩn danh bắt buộc** dữ liệu học sinh/nhà trường → BTC có thể ngại |
| **6** | **Nông nghiệp**: giá nông sản, sâu bệnh, năng suất | **THẤP–TRUNG BÌNH** | Khớp chủ đề nhưng ít "nóng" hơn ở một kỳ thi tổ chức tại TP.HCM |
| **7** | **Ảnh/thị giác máy tính quy mô lớn** | **THẤP** | Không khả thi trong 2 ngày với máy cá nhân |

**KẾT LUẬN CHIẾN LƯỢC QUAN TRỌNG NHẤT CỦA CHƯƠNG NÀY:**
Đừng đánh cược vào việc đoán đúng lĩnh vực. **Hãy đánh cược vào việc mọi lĩnh vực đều phải
đi qua cùng một bộ giao nộp.** Bốn thứ phải nộp (repo · báo cáo có metrics/baseline/ablation ·
video · prompt log + kê khai) **không đổi theo đề bài**. Chuẩn bị trước bộ giao nộp là khoản
đầu tư có xác suất trúng 100%, trong khi đoán lĩnh vực có xác suất trúng ~30%.

### 5.3 BỘ ĐỒ NGHỀ HACKATHON — 8 món phải dựng xong trước 08/10

> Dựng thành một repo riêng `hack-kit`, **public, có commit history thật của cả 3 người**,
> để ngày thi chỉ `git clone` rồi đổ dữ liệu vào. Việc chuẩn bị trước công cụ chung là hợp
> lệ — thể lệ chỉ cấm người ngoài làm thay và cấm giả mạo, không cấm mang theo thư viện của
> chính mình. **Kê khai `hack-kit` trong bản kê khai là xong.**

**Món 1 — Khung repo `hack-kit/` (giao: Xuân Khánh · 3 giờ)**
```
hack-kit/
├── README.md              # 10 dòng: chạy cái gì, ra cái gì
├── Makefile               # make eda / make baseline / make train / make report / make all
├── pyproject.toml         # pin sẵn: pandas, polars, scikit-learn, lightgbm, statsmodels,
│                          # matplotlib, pyarrow, underthesea, transformers, sentence-transformers
├── .github/workflows/ci.yml  # lint + test + smoke-run trên dữ liệu giả — XANH SẴN
├── .gitignore · LICENSE
├── du_lieu/{tho,sach}/    # thô KHÔNG commit, sạch có schema
├── src/ · eval/ · bao_cao/ · prompt_log/
└── tests/                 # 5 test khung: đọc dữ liệu, chia fold, metric, seed, báo cáo
```
Yêu cầu nghiệm thu: `make all` chạy được end-to-end trên **dữ liệu giả tự sinh** và tạo ra
một PDF báo cáo rỗng-nhưng-đúng-cấu-trúc. CI xanh.

**Món 2 — `00_khaosat.py` / notebook EDA tự động (giao: Lâm Tiến · 4 giờ)**
Đầu vào: một đường dẫn (csv/tsv/xlsx/json/jsonl/parquet, kể cả thư mục nhiều file).
Đầu ra tự động, không cần gõ thêm lệnh:
- Bảng hồ sơ từng cột: kiểu, % thiếu, số giá trị khác nhau, min/max/median, top-10 giá trị
- Cờ cảnh báo: cột hằng, cột trùng, ID rò rỉ nhãn, ngày không parse được, mã hoá lỗi font
- **Phát hiện tự động dạng bài**: có cột thời gian? có cột văn bản dài? nhãn nhị phân/đa lớp/liên tục?
- 8 biểu đồ chuẩn (phân phối nhãn, thiếu dữ liệu, tương quan, chuỗi theo thời gian…)
- Xuất `bao_cao/eda.md` + `bao_cao/hinh/*.png` **dán thẳng vào báo cáo kỹ thuật được**

**Món 3 — Ba pipeline mẫu chạy được ngay (giao: cả 3, mỗi người 1 · 6 giờ/người)**

| Pipeline | Baseline bắt buộc (chạy trước) | Mô hình chính | Ghi chú |
|---|---|---|---|
| **A. Dữ liệu bảng** | Dự đoán lớp đa số / trung vị | LightGBM + StratifiedKFold + hiệu chuẩn xác suất (`CalibratedClassifierCV`) + permutation importance | Có sẵn hàm xử lý cột phân loại, cột ngày, cột tiền |
| **B. Văn bản tiếng Việt** | TF-IDF **char n-gram (2–5)** + LinearSVC | PhoBERT/ViSoBERT fine-tune nếu kịp, so sánh thẳng với baseline | **Tái dùng trực tiếp `src/livelift/nlp/` và bộ lọc PII tiếng Việt của LiveLift** — chuẩn hoá dấu, teencode, SĐT viết chữ, đơn vị hành chính 2 thế hệ. Đây là tài sản đội đã có mà đội khác không có |
| **C. Chuỗi thời gian** | Naive + **seasonal naive** | ETS/SARIMA (statsmodels) và LightGBM với đặc trưng trễ | Backtest **rolling-origin** bắt buộc, không dùng KFold ngẫu nhiên |

Nghiệm thu: mỗi pipeline chạy được trên một dataset công khai bất kỳ trong **dưới 15 phút**
và in ra bảng metric.

**Món 4 — `eval/danh_gia.py`: khung đánh giá dùng chung (giao: Lâm Tiến · 4 giờ) — MÓN QUAN TRỌNG NHẤT**
Một hàm duy nhất mọi thí nghiệm phải đi qua:
```python
danh_gia(ten_thi_nghiem, y_that, y_du_doan, bai_toan="phan_loai" | "hoi_quy" | "chuoi")
```
Nó tự động:
- Tính metric đúng loại bài (macro-F1/AUC/MAE/MAPE…) **và metric của baseline**
- **Khoảng tin cậy 95% bằng bootstrap** cho mỗi metric — gần như không đội nào làm việc này
- Ghi một dòng vào `eval/so_thi_nghiem.csv` (tên, tham số, seed, metric, thời gian)
- Sinh `bao_cao/bang_ketqua.md` và **`bao_cao/bang_ablation.md` tự động** từ chính sổ đó
Kết quả: **bảng so sánh baseline và bảng ablation không phải viết tay** — chỉ cần chạy đủ
thí nghiệm. Đây chính là hai thứ BTC đòi đích danh trong báo cáo kỹ thuật.

**Món 5 — Mẫu báo cáo kỹ thuật đã đúng mục BTC đòi (giao: Bình Minh · 3 giờ)**
`bao_cao/mau-bao-cao.md` với các mục **khớp từng chữ** với thể lệ, mỗi mục có sẵn chỗ trống
và hướng dẫn một dòng:
1. Bài toán và cách đội hiểu yêu cầu của BTC
2. Phương pháp luận (gồm **mục "tiền đăng ký mini"** — xem §5.6)
3. Dữ liệu: nguồn, hồ sơ dữ liệu, tiền xử lý, **rà PII**
4. Kiến trúc hệ thống (sơ đồ)
5. Mô hình/thuật toán và vai trò từng thành phần
6. Quy trình huấn luyện/tinh chỉnh/tích hợp
7. **AI evaluation metrics** (tự động từ Món 4)
8. **So sánh baseline** (tự động)
9. **Ablation** (tự động)
10. Phân tích lỗi (10 ca sai thật, nhóm theo nguyên nhân)
11. Rủi ro, bảo mật, đạo đức AI, **phương án kiểm soát đầu ra**
12. Hạn chế và hướng phát triển
13. **Bản kê khai**: công cụ AI · mô hình · thư viện · dataset · API · mã tham khảo, với cột
    *đội tự xây / AI tạo ra / kế thừa nguồn mở*
Kèm `make report`: markdown → PDF một lệnh. **Phải thử build ít nhất 1 lần trước ngày thi.**

**Món 6 — Hạ tầng Prompt Log (giao: Xuân Khánh · 2 giờ)**
Thể lệ đòi **"System Prompt và toàn bộ conversation history"**. Chuẩn bị trước:
- `prompt_log/README.md` giải thích cấu trúc
- `prompt_log/system-prompt.md` — chép đúng System Prompt của mọi công cụ AI đội dùng
- Quy ước: mỗi phiên làm việc xuất ra `prompt_log/YYYY-MM-DD-HHMM-<ten>.md`, có dấu thời gian
- Script `prompt_log/gom.py` gộp tất cả thành một PDF/ZIP nộp được
- **Thói quen phải tập trước:** xuất log **ngay sau mỗi phiên**, không để dồn đến cuối. Trong
  48 giờ hackathon, việc dồn log đến giờ chót là cách mất điểm dễ nhất.

**Món 7 — Hộp dụng cụ "dữ liệu Việt Nam" (giao: Xuân Khánh · 3 giờ)**
Thứ đội khác sẽ mất 3–4 giờ để làm lại tại chỗ, đội mang theo sẵn:
- Bộ chuẩn hoá tiếng Việt: Unicode dựng sẵn/tổ hợp, teencode, viết tắt, dấu câu
- **Bộ lọc PII tiếng Việt của LiveLift** (đã có, recall ≥95%/loại) — dùng để **rà dataset của
  BTC** và ghi vào mục đạo đức dữ liệu. Đây là một đòn ghi điểm gần như chắc chắn
- Danh mục đơn vị hành chính **cả hai thế hệ** (trước/sau sáp nhập, mô hình hai cấp) + hàm ánh xạ
- Hàm parse ngày tháng kiểu Việt, tiền tệ ("12tr5", "1 triệu 2"), số điện thoại viết chữ

**Món 8 — Gói trình bày (giao: Bình Minh · 2 giờ)**
- Kịch bản video demo **10 phút có mặt cả 3 người** — chia sẵn ai nói phần nào, mỗi người
  nói về **phần mình thật sự làm** (thể lệ và ban giám khảo sẽ hỏi chéo)
- Khung slide 8 trang: bài toán → dữ liệu → baseline → phương pháp → kết quả có KTC → ablation
  → giới hạn & kiểm soát đầu ra → hướng phát triển
- Checklist quay: thiết bị, ánh sáng, micro, phần mềm ghi màn hình đã cài và **đã thử**

### 5.4 Quy trình 48 giờ — phân vai và mốc

**Phân vai cố định (ai cũng biết mình làm gì, không bàn lại trong lúc thi):**

| Người | Vai | Trách nhiệm không được nhường |
|---|---|---|
| **Ngô Bình Minh** (đội trưởng) | **Chủ bài toán & Đánh giá** | Giữ **một** câu hỏi chính và **một** metric chính; chống scope creep; viết báo cáo; là người duy nhất được quyền nói "dừng, không làm nữa" |
| **Lê Xuân Khánh** | **Dữ liệu & Hạ tầng** | Đọc dữ liệu, làm sạch, rà PII, repo/CI/commit, đóng gói nộp bài, Prompt Log |
| **Ngô Lâm Tiến** | **Mô hình & Ablation** | Baseline trước, mô hình sau; mọi thay đổi phải chạy qua `danh_gia.py`; phân tích lỗi |

**Lịch 48 giờ:**

| Giờ | Việc | Sản phẩm phải có ở cuối mốc |
|---|---|---|
| **0–2** | Cả 3 đọc đề. Chạy `00_khaosat.py`. **Chốt 1 câu hỏi + 1 metric + 1 baseline tầm thường.** Viết **`TIEN-DANG-KY.md`** (½ trang: metric, cách chia dữ liệu, tiêu chí thành công) và **commit ngay** | `eda.md` + `TIEN-DANG-KY.md` đã commit, có dấu thời gian |
| **2–6** | **Baseline chạy end-to-end, có số.** Không được làm gì khác trước khi có số baseline | Một dòng trong `so_thi_nghiem.csv` |
| **6–20** | Nâng cấp mô hình. **Mỗi thay đổi = một dòng trong sổ thí nghiệm.** Khánh song song làm sạch dữ liệu + dựng khung nộp bài | ≥6 dòng sổ; bảng ablation tự sinh đã có nội dung |
| **20–28** | **Ngủ luân phiên, bắt buộc** — 2 người ngủ, 1 người trực. Ghi vào kế hoạch để không ai áy náy | Không ai thức trắng 48 giờ |
| **28–36** | **ĐÓNG BĂNG MÔ HÌNH.** Từ đây không đổi mô hình nữa. Làm: demo chạy được · phân tích lỗi 10 ca · **phương án kiểm soát đầu ra** · rà PII trên dữ liệu BTC · kiểm tra thiên lệch theo nhóm | Demo bấm được; mục 10, 11 của báo cáo xong |
| **36–44** | Viết báo cáo (các bảng đã tự sinh, chỉ viết phần chữ) · quay video 10 phút · gom Prompt Log · viết bản kê khai | PDF + MP4 + ZIP log |
| **44–46** | **Diễn tập nộp:** clone repo sạch sang máy khác, chạy lại `make all`, kiểm tra quyền truy cập repo cho BTC, mở thử mọi link | Biên bản kiểm tra 12 mục (§5.5) |
| **46–48** | **Nộp sớm.** Đệm 2 giờ cho sự cố mạng/hệ thống | Đã nộp, có ảnh chụp xác nhận |

**Ba luật cứng trong 48 giờ:**
1. **Baseline trước mọi thứ.** Không có số baseline thì không được chạm vào mô hình phức tạp.
2. **Không đổi metric sau giờ thứ 2.** Đã khoá trong `TIEN-DANG-KY.md`.
3. **Giờ 36 là đóng băng.** Một mô hình xoàng có báo cáo tử tế thắng một mô hình tốt không
   kịp viết báo cáo — vì rubric chấm **báo cáo, metrics, baseline, ablation**, không chấm
   riêng độ chính xác.

### 5.5 Checklist nộp bài — 12 mục, đọc to từng mục trước khi bấm nộp

1. ☐ Repo GitHub/GitLab **public hoặc đã cấp quyền cho BTC/giám khảo** — đã thử mở bằng chế độ ẩn danh
2. ☐ Commit history **thật, rải đều 2 ngày, có tên cả 3 thành viên**
3. ☐ `README.md` chạy được: clone → 1 lệnh → ra kết quả
4. ☐ Báo cáo kỹ thuật PDF có **đủ 13 mục** §5.3 Món 5
5. ☐ Báo cáo có **AI evaluation metrics** ghi rõ công thức và cách chia dữ liệu
6. ☐ Báo cáo có **bảng so sánh baseline**
7. ☐ Báo cáo có **bảng ablation**
8. ☐ Video demo **≤10 phút**, **có mặt cả 3 thành viên**, mỗi người nói phần mình làm
9. ☐ **Prompt Log đầy đủ có System Prompt + toàn bộ conversation history**
10. ☐ **Bản kê khai** công cụ AI/mô hình/thư viện/dataset/API/mã tham khảo, có cột *tự xây / AI tạo / nguồn mở*
11. ☐ Mục **rủi ro – bảo mật – đạo đức AI – kiểm soát đầu ra** không để trống
12. ☐ Mọi link Google Drive **đã mở quyền truy cập** (lỗi kinh điển làm mất điểm)

### 5.6 Ghi điểm khác biệt khi cả phòng đều dùng LLM — 8 đòn, xếp theo hiệu quả

Giả định an toàn: **hầu hết đội sẽ nộp một wrapper LLM/chatbot/RAG có giao diện đẹp, một con
số accuracy duy nhất, không baseline, không ablation, không khoảng tin cậy, prompt log gom
vội giờ chót.** Tám đòn dưới đây đều rẻ và đều đánh đúng chữ trong rubric:

| # | Đòn | Đánh vào | Vì sao đội khác không làm |
|---:|---|---|---|
| **1** | **Baseline tầm thường có số thật** — "đoán lớp đa số", "seasonal naive". Và **dám công bố khi mô hình xịn thua baseline** | Kết quả thử nghiệm · so sánh phương án | Vì nó làm mô hình của họ trông kém. LiveLift **đã sống bằng văn hoá này**: intent 0,271 thua baseline "khac" và đội vẫn công bố |
| **2** | **Bảng ablation thật** — bỏ từng thành phần, chạy lại, ghi số | Phân tích đóng góp thành phần | Tốn thời gian nếu không có khung tự động. Đội **có Món 4 nên gần như miễn phí** |
| **3** | **Khoảng tin cậy bootstrap trên mọi metric** thay vì một con số trần trụi | Khoa học · kiểm chứng đầu ra | Gần như không sinh viên nào nghĩ tới. Đội đã làm Fisher CI ở LiveLift |
| **4** | **`TIEN-DANG-KY.md` commit ở giờ thứ 2** — khoá metric và tiêu chí **trước khi nhìn kết quả**, rồi nêu thẳng trong báo cáo: *"chúng em khoá tiêu chí lúc 9h15, commit `abc1234`, và không đổi"* | Khoa học · liêm chính · trách nhiệm | **Không đội nào làm.** Đây là chữ ký nhận dạng của LiveLift, chuyển giao nguyên vẹn, chi phí 20 phút |
| **5** | **Rà PII trên chính dataset của BTC** bằng bộ lọc tiếng Việt có sẵn, báo cáo số trường nhạy cảm phát hiện và cách xử lý | Đạo đức AI · an toàn dữ liệu | Cần công cụ sẵn. **Đội có, đội khác không có** |
| **6** | **Phương án kiểm soát đầu ra**: ngưỡng tin cậy, **cơ chế từ chối trả lời khi không đủ căn cứ**, guardrail cho đầu ra LLM, ghi log quyết định | Kiểm soát đầu ra · an toàn | LiveLift đã có nguyên lý này dưới dạng `estimable=False` + lý do tiếng Việt — bê thẳng sang |
| **7** | **Phân tích lỗi 10 ca sai thật**, nhóm theo nguyên nhân, kèm ảnh chụp | Phân tích · tối ưu | Ai cũng biết nên làm, ít ai kịp làm vì không đóng băng mô hình đúng giờ |
| **8** | **Kiểm tra thiên lệch theo nhóm** (vùng miền, giới, nhóm tuổi nếu dữ liệu có) và nói thẳng giới hạn | Đạo đức AI | Rất hợp gu hội đồng Đoàn, chi phí 30 phút |

**Nguyên tắc bao trùm:** trong một phòng mà ai cũng có LLM, **thứ khan hiếm không phải là mô
hình — mà là bằng chứng rằng bạn biết mô hình của mình sai ở đâu.** Toàn bộ tài sản văn hoá
của LiveLift nằm đúng ở chỗ khan hiếm đó.

---

## 6. DỰ BÁO MẶT BẰNG ĐỐI THỦ VÀ "ĐIỂM KHÁC BIỆT KHÔNG SAO CHÉP ĐƯỢC"

### 6.1 Đối thủ sẽ trông như thế nào

Suy ra từ cơ cấu dự thi (sinh viên 19–22, đội ≤3 người, hackathon 2 ngày) và từ mẫu hình các
cuộc thi gần nhất (§8):

| Nhóm | Tỷ lệ ước tính | Đặc điểm | Điểm mạnh | Điểm yếu |
|---|---|---|---|---|
| **A. "Wrapper LLM có giao diện đẹp"** | ~50% | Chatbot/RAG trên dữ liệu BTC, Next.js/Streamlit, deploy Vercel | Demo bắt mắt, kể chuyện tốt | Không baseline, không ablation, một con số accuracy, prompt log gom vội |
| **B. "Lò" trường mạnh** (ĐH KHTN–ĐHQG-HCM, UIT, BK, PTIT…) | ~20% | Kỹ thuật thật, quen benchmark quốc tế. Ví dụ tham chiếu: UIT bốn lần vô địch AI Challenge TP.HCM ([nguồn](https://tuyensinh.uit.edu.vn/uit-lan-thu-4-dang-quang-vo-dich-hoi-thi-thu-thach-tri-tue-nhan-tao-ai-challenge-2025)); ĐH KHTN giữ giải Nhất CNTT Euréka nhiều năm liên tiếp ([Euréka 2025](https://hoahoctro.tienphong.vn/truong-dh-khoa-hoc-tu-nhien-dhqg-tphcm-dan-dau-voi-7-giai-nhat-tai-eureka-2025-post1802598.tpo)) | **Đây là đối thủ thật sự.** Mô hình mạnh, quen tinh chỉnh | Thường yếu ở phần đạo đức/rủi ro/kiểm soát đầu ra và ở việc trình bày cho hội đồng không chuyên |
| **C. Đội sản phẩm/khởi nghiệp** | ~20% | Ý tưởng tác động xã hội, pitch tốt, kỹ thuật trung bình | Câu chuyện hợp gu Đoàn | Ít số, ít kiểm chứng |
| **D. Đội phong trào** | ~10% | Nộp cho đủ | — | — |

**Vị trí LiveLift trong bản đồ này:** đội có **kỷ luật đánh giá của nhóm B** cộng **ý thức tác
động của nhóm C**, nhưng đang thiếu **bằng chứng thực địa** và **năng lực hackathon đã được
tập dượt**. Hai thiếu sót đó chính là §4 hành động #1 và §5.

### 6.2 Năm điểm khác biệt KHÔNG sao chép được trong 2 ngày

1. **Tiền đăng ký có hiệu lực cưỡng chế.** Không phải một lời hứa "chúng em không p-hack" mà
   là `RESULTS_FREEZE_UNTIL` — mã nguồn **từ chối trả kết quả** trước thời điểm đã khoá. Một
   đội khác có thể nói câu đó; không đội nào dựng được cơ chế đó trong 2 ngày.
2. **Ước lượng viên được chứng minh hiệu chỉnh bằng gate tự động.** A/A 200 lặp bác bỏ 4,5%
   với kiểm định nhị thức chính xác p = 0,872; coverage 95,5% — và đó là **một bài test trong
   CI**, chạy lại được trước mặt giám khảo.
3. **Sổ sự cố 41 mục có nguyên nhân gốc và gate chặn tái diễn**, gồm cả lỗi FATAL do chính
   đội tìm ra (52% phiên null từng bị tuyên "có ý nghĩa"). **Không ai làm giả được một sổ sự
   cố** — nó phải được viết dần trong nhiều tuần.
4. **Một con số tự bác bỏ chính mình: 0,870 → 0,271.** Đây là thứ hiếm nhất trong mọi cuộc
   thi. Kèm phát hiện sâu: precision chạy 1,3% → 67,9% theo **tỷ lệ nền** của từng buổi, không
   theo model.
5. **Bộ lọc PII tiếng Việt đã đo recall ≥95%/loại**, chạy trước khi ghi đĩa, xử lý được SĐT
   viết chữ, teencode và hai thế hệ đơn vị hành chính. **Dùng lại được ngay trên dataset của
   BTC ở vòng hackathon** (§5.6 đòn 5) — biến một tài sản của hồ sơ 40% thành điểm ở vòng 60%.

**Cách nói ngắn để đội thuộc lòng:**
> *"Đội khác mang đến một mô hình. Chúng em mang đến một **quy trình chứng minh mô hình đó
> đúng hay sai** — và bằng chứng là chính chúng em đã dùng nó để bác bỏ một con số đẹp của
> mình."*

---

## 7. BỐI CẢNH CHÍNH SÁCH — TRÍCH ĐÚNG SỐ HIỆU, KHÔNG BỊA

> **Tin quan trọng cho đội:** hai văn bản mà `README.md` đang dẫn (**Luật 91/2025/QH15** và
> **NĐ 356/2025/NĐ-CP**) đã được **xác minh là ĐÚNG** trên nguồn chính thức. Không phải sửa.
> Nhưng phải **bổ sung hai văn bản mới rất có lợi** (dòng in đậm dưới) và **gỡ mọi chỗ dẫn
> NĐ 13/2023 như luật hiện hành**.

| Văn bản | Số hiệu | Ban hành | Hiệu lực | Nguồn |
|---|---|---|---|---|
| **Nghị quyết Bộ Chính trị** về đột phá phát triển KHCN, đổi mới sáng tạo và chuyển đổi số quốc gia | **57-NQ/TW** | **22/12/2024** | Văn bản của Đảng | [tulieuvankien.dangcongsan.vn](https://tulieuvankien.dangcongsan.vn/he-thong-van-ban/van-ban-cua-dang/nghi-quyet-so-57-nqtw-ngay-22122024-cua-bo-chinh-tri-ve-dot-pha-phat-trien-khoa-hoc-cong-nghe-doi-moi-sang-tao-va-chuyen-11162) · [toàn văn](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-quyet-ve-dot-pha-phat-trien-khoa-hoc-cong-nghe-doi-moi-sang-tao-va-chuyen-doi-so-quoc-gia-119241224180048642.htm) |
| Chương trình hành động của Chính phủ thực hiện NQ 57 | **03/NQ-CP** | 09/01/2025 | từ ngày ký | [tulieuvankien.dangcongsan.vn](https://tulieuvankien.dangcongsan.vn/he-thong-van-ban/nghi-quyet-cua-chinh-phu/nghi-quyet-so-03nq-cp-ngay-0912025-cua-chinh-phu-ban-hanh-chuong-trinh-hanh-dong-cua-chinh-phu-thuc-hien-nghi-quyet-so-57-nqtw-ngay-11243) |
| **Luật Bảo vệ dữ liệu cá nhân** | **91/2025/QH15** ✅ | QH thông qua **26/6/2025** | **01/01/2026** | [Công báo Chính phủ](https://congbao.chinhphu.vn/tai-ve-van-ban-so-91-2025-qh15-45578-57730?format=pdf) |
| **Nghị định** quy định chi tiết và biện pháp thi hành Luật BVDLCN | **356/2025/NĐ-CP** ✅ | 31/12/2025 | **01/01/2026** | [vanban.chinhphu.vn](https://vanban.chinhphu.vn/?pageid=27160&docid=216387) |
| Nghị định về bảo vệ dữ liệu cá nhân *(cũ)* | 13/2023/NĐ-CP | 17/4/2023 | **ĐÃ HẾT HIỆU LỰC từ 01/01/2026** — bị NĐ 356/2025 thay thế | [chinhphu.vn](https://xaydungchinhsach.chinhphu.vn/toan-van-nghi-dinh-13-2023-nd-cp-bao-ve-du-lieu-ca-nhan-119230516104357809.htm) |
| Luật Dữ liệu | **60/2024/QH15** | 30/11/2024 | 01/7/2025 | [tulieuvankien.dangcongsan.vn](https://tulieuvankien.dangcongsan.vn/he-thong-van-ban/van-ban-quy-pham-phap-luat/luat-du-lieu-so-602024qh15-hieu-luc-thi-hanh-tu-ngay-0172025-11192) |
| Chiến lược quốc gia về nghiên cứu, phát triển và ứng dụng TTNT đến năm 2030 | **127/QĐ-TTg** | 26/01/2021 | từ ngày ký | [vanban.chinhphu.vn](https://vanban.chinhphu.vn/default.aspx?pageid=27160&docid=202565) |
| Luật Công nghiệp công nghệ số | **71/2025/QH15** | 14/6/2025 | 01/01/2026 | [thuvienphapluat.vn](https://thuvienphapluat.vn/van-ban/Cong-nghe-thong-tin/Luat-Cong-nghiep-cong-nghe-so-2025-so-71-2025-QH15-621341.aspx) |
| **Luật Trí tuệ nhân tạo — luật AI đầu tiên của Việt Nam** | **134/2025/QH15** | QH thông qua **10/12/2025** | **01/3/2026** | [thuvienphapluat.vn](https://thuvienphapluat.vn/chinh-sach-phap-luat-moi/vn/ho-tro-phap-luat/chinh-sach-moi/106139/luat-tri-tue-nhan-tao-2025-chinh-thuc-co-hieu-luc) |

**Chỉ tiêu NQ 57 đã xác minh nguyên văn, dùng được ngay** (nguồn: cổng chinhphu.vn ở bảng trên):
- Đến 2030: **Top 3 Đông Nam Á, Top 50 thế giới về năng lực cạnh tranh số**; đóng góp của TFP
  vào tăng trưởng **trên 55%**; tỷ trọng xuất khẩu sản phẩm công nghệ cao **tối thiểu 50%**;
  **kinh tế số đạt tối thiểu 30% GDP**; chi cho R&D đạt **2% GDP**, trong đó **trên 60% từ xã hội**.
- Tầm nhìn 2045: **kinh tế số tối thiểu 50% GDP**.

**Ba cách dùng chính sách để ăn điểm (đặt đúng chỗ, không rải khắp hồ sơ):**
1. **MẪU 3 mục 1** — "tính cần thiết trong bối cảnh hiện nay": dùng chỉ tiêu **kinh tế số ≥30%
   GDP vào 2030** của NQ 57 (Phương án B, §3.2). Một câu, có số hiệu, có ngày.
2. **MẪU 3 mục 3** — tính hợp lệ của dữ liệu: trích **Luật 91/2025/QH15** và **NĐ
   356/2025/NĐ-CP** (hiệu lực từ 01/01/2026) làm căn cứ cho thiết kế khử nhận dạng tại ingest.
3. **MẪU 3 mục 11** — đạo đức AI: trích **Luật Trí tuệ nhân tạo 134/2025/QH15, hiệu lực
   01/3/2026**. **Đây là đòn ít đội nghĩ tới** — một dự án sinh viên viện dẫn được luật AI mới
   nhất của Việt Nam trong mục đạo đức sẽ nổi bật ngay.

**Những thứ KHÔNG được dùng (đã kiểm và không xác minh được — tuyệt đối không bịa):**
- Số hiệu Chương trình hành động của **Đoàn TNCS Hồ Chí Minh** thực hiện NQ 57: **KHÔNG XÁC
  MINH ĐƯỢC.** (Có tồn tại, quán triệt toàn quốc 27/02/2025, 5 nhóm nhiệm vụ và 57 nội dung —
  nhưng không tìm được bản có số hiệu.) Nếu muốn nhắc, chỉ viết mô tả, **không kèm số hiệu**.
- Phong trào **"Tuổi trẻ tiên phong chuyển đổi số"**: **KHÔNG TÌM THẤY** văn bản nào mang đúng
  tên này. Không dùng.
- Phong trào **"Bình dân học vụ số"** là Kế hoạch **01-KH/BCĐTW** của **Ban Chỉ đạo Trung ương**
  (không phải TW Đoàn), và các nguồn **mâu thuẫn về ngày ban hành** (21/4/2025 theo hệ thống
  văn bản của Đảng, 21/3/2025 theo một số cổng tỉnh). Nếu dùng thì **không ghi ngày**.
- Quan hệ giữa Luật 71/2025 và Luật 134/2025 về các điều khoản AI: **chưa xác minh được** điều
  khoản thi hành. **Chỉ trích Luật 134/2025**, đừng trích Điều 41–43 của Luật 71/2025.

---

## 8. LỊCH SỬ: DỰ ÁN ĐOẠT GIẢI CAO BẢNG SINH VIÊN Ở SÂN CỦA ĐOÀN — ĐỌC RA ĐIỀU GÌ

**Đính chính một giả định phổ biến: Hội thi Tin học trẻ toàn quốc KHÔNG có bảng sinh viên.**
Cơ cấu bảng chỉ đến THPT: A (tiểu học), B (THCS), C1/C2 (THPT), D1/D2/D3 (sản phẩm sáng tạo
theo cấp học) — xác nhận tại [trang tổng kết Hội thi lần thứ XXXI, 2025](https://tainangviet.vn/le-tong-ket-va-trao-giai-thuong-hoi-thi-tin-hoc-tre-toan-quoc-lan-thu-xxxi-nam-2025-dar6742/).
Benchmark đúng phải lấy từ các sân sinh viên khác của Đoàn/Hội SVVN.

### 8.1 Bảy ví dụ có tên dự án (kèm nguồn)

| # | Dự án | Năm · Cuộc thi · Giải | Chủ đề | Nguồn |
|---:|---|---|---|---|
| 1 | **PhyLab — Phòng thí nghiệm Vật lý ảo cá nhân hóa bằng AI** (đội AI-mant, liên trường: ĐH Tài chính–Marketing, BK Hà Nội, BK ĐHQG-HCM, Ngoại thương) | 2026 · **Vietnamese Student HackAIthon** (TW Hội Sinh viên VN) · **Giải Nhất bảng B** | Giáo dục | [nhandan.vn](https://nhandan.vn/phong-thi-nghiem-vat-ly-ao-ve-nhat-cuoc-thi-lap-trinh-sinh-vien-post977424.html) |
| 2 | *(tên sản phẩm **KHÔNG TÌM THẤY**)* — Nguyễn Thị Hồng Trang, ĐH Bách khoa – ĐH Đà Nẵng. Đề bài bảng C: **"Thiết kế trợ lý AI Agent đa nhiệm"**, 98 sản phẩm dự thi | 2026 · HackAIthon · **Giải Nhất bảng C** | AI Agent | [nhandan.vn](https://nhandan.vn/phong-thi-nghiem-vat-ly-ao-ve-nhat-cuoc-thi-lap-trinh-sinh-vien-post977424.html) |
| 3 | **ShieldNet — Hệ thống AI đa tầng hỗ trợ và bảo vệ không gian mạng** (ĐH CNTT & Truyền thông Việt–Hàn, ĐH Đà Nẵng) | 2025 · Khởi nghiệp công nghệ trong sinh viên lần 5 (Hội SV ĐH Đà Nẵng + Sở KH&CN) · **Giải Nhất** | Chống lừa đảo online | [tuoitre.vn](https://tuoitre.vn/sinh-vien-khoi-nghiep-dung-ai-de-ban-tra-day-lich-su-ngan-lua-dao-online-20251025143326857.htm) |
| 4 | **Hệ thống giám sát và duy trì độ tỉnh táo cho tài xế bằng công nghệ sóng não** (ĐH Bách khoa Hà Nội) | 2025 · SV_STARTUP lần VII (Bộ GD&ĐT + **TW Đoàn**) · **Giải Nhất bảng sinh viên**, lĩnh vực *Kinh doanh tạo tác động xã hội* | An toàn giao thông / y tế | [vnexpress.net](https://vnexpress.net/15-du-an-cua-hoc-sinh-sinh-vien-gianh-giai-nhat-sv-startup-2025-4876457.html) |
| 5 | **CARBONet — Ứng dụng di động đánh giá nhanh lượng Carbon tích lũy trong rừng** (ĐH Lâm nghiệp) | 2025 · SV_STARTUP · **Giải Nhất bảng sinh viên**, lĩnh vực Nông lâm ngư nghiệp | Môi trường | [vnuf2.edu.vn](https://vnuf2.edu.vn/vi/tin-tuc/sinh-vien-doan-hoi/3860-sinh-vien-vnuf-dat-giai-nhat-cuoc-thi-hoc-sinh-sinh-vien-khoi-nghiep-sv-startup-2025-linh-vuc-nong-lam-ngu-nghiep.html) |
| 6 | **Cải thiện truy vấn đa phương tiện với siêu dữ liệu trực quan cấp cao có cấu trúc...** (Hồ Lê Minh Quân, Hồ Duy Khang — ĐH KHTN, ĐHQG-HCM) | 2025 · **Giải thưởng Euréka** (Thành Đoàn TP.HCM + ĐHQG-HCM) · **Giải Nhất lĩnh vực CNTT** | Nghiên cứu lõi | [hoahoctro.tienphong.vn](https://hoahoctro.tienphong.vn/truong-dh-khoa-hoc-tu-nhien-dhqg-tphcm-dan-dau-voi-7-giai-nhat-tai-eureka-2025-post1802598.tpo) |
| 7 | **OpenCubee_1** (ĐH CNTT, ĐHQG-HCM) — trợ lý ảo truy vấn kho dữ liệu multimedia lớn | 2025 · AI Challenge TP.HCM (Sở KH&CN + **Thành Đoàn TP.HCM**) · **Giải Nhất bảng A sinh viên**, ~4.000 thí sinh / 797 đội | Nghiên cứu ứng dụng | [tuyensinh.uit.edu.vn](https://tuyensinh.uit.edu.vn/uit-lan-thu-4-dang-quang-vo-dich-hoi-thi-thu-thach-tri-tue-nhan-tao-ai-challenge-2025) |

Bổ sung: **SAVE.AI** (cảnh báo lũ quét, sạt lở) và **Sentinel** (cảnh báo thiên tai + bảo vệ
chủ quyền) được vinh danh Giải thưởng **"Tuổi trẻ sáng tạo" toàn quốc 2025** của TW Đoàn, cả
hai đều có sinh viên đồng tác giả ([nguồn](https://tinhdoan.caobang.gov.vn/index.php/tin-tuc/cao-bang-co-02-nhom-tac-gia-vinh-du-nhan-giai-thuong-tuoi-tre-sang-tao-toan-quoc-nam-2025-3189.html)).
Và **AI Hackathon 2025** của Sở KHCN TP.HCM có đội thắng bằng **ứng dụng AI cảnh báo sạt lở**
([nguồn](https://plo.vn/ung-dung-ai-canh-bao-sat-lo-gianh-chien-thang-tai-ai-hackathon-2025-post884089.html)).

### 8.2 Bốn kết luận rút ra — và hàm ý cho LiveLift

**(1) Trục thắng giải là "cứu người / cứu môi trường / bảo vệ người yếu thế", không phải
"tăng hiệu quả kinh doanh".** Đếm chủ đề các dự án giải Nhất tìm được: y tế/sức khoẻ và
môi trường/thiên tai đông nhất; giáo dục và an toàn/chống lừa đảo theo sau; **dịch vụ công
thuần: không tìm thấy dự án giải Nhất bảng sinh viên nào**.

**(2) KHÔNG TÌM THẤY dự án B2B/thương mại thuần nào ở nhóm giải Nhất.** Gần nhất là **S-Box**
(giao hàng thông minh, ĐH Thương mại) — nhưng vẫn được đóng khung là *hạ tầng dịch vụ dân
sinh*, và **CARBONet** có doanh thu tín chỉ carbon nhưng thắng dưới khung môi trường.
*Cảnh báo độ chắc chắn: kết luận dựa trên các dự án được báo chí nêu tên; danh sách đầy đủ 15
giải Nhất SV_STARTUP 2026 đăng dưới dạng ảnh nên không truy được toàn bộ.*

> **Hàm ý trực tiếp cho LiveLift:** đây chính là bằng chứng thực nghiệm cho khuyến nghị §3.
> **Không đổi đề tài — nhưng bắt buộc phải đóng khung LiveLift theo trục "bảo vệ người bán
> nhỏ khỏi quyết định mù và khỏi thông tin sai".** Chú ý mẫu hình của ShieldNet: *chống lừa
> đảo online* là chủ đề vừa thắng giải Nhất năm 2025. LiveLift có một luận điểm rất gần đó và
> chưa dùng: **thị trường "khoá học bí kíp livestream" đang bán kinh nghiệm vô căn cứ cho
> người bán nhỏ; LiveLift là công cụ để họ tự kiểm chứng thay vì phải tin.**

**(3) Hai loại sân chơi, hai chuẩn khác nhau.** Sân NCKH (Euréka, AI Challenge) đòi chiều sâu
gần mức hội nghị quốc tế, có "lò" dẫn dắt (PGS.TS Trần Minh Triết hướng dẫn giải Nhất CNTT
Euréka cả 2024 và 2025). Sân sản phẩm/tác động (HackAIthon, SV_STARTUP, Tuổi trẻ sáng tạo)
chấm **bài toán rõ + demo chạy được + câu chuyện tác động**, kỹ thuật ở mức ứng dụng/tích hợp.
**Cuộc thi này nằm giữa hai sân**: rubric 8 trọng tâm đòi chiều sâu phương pháp *và* đòi tác
động thực tiễn. **LiveLift đang thừa vế một, thiếu vế hai** — đúng như §4 đã chấm.

**(4) Xu hướng 2026 là "làm thật".** SV_STARTUP 2026 được chính truyền thông đóng khung là
**"Làm thật – Thi thật"**, *"chuyển biến rõ nét từ ý tưởng sang sản phẩm, từ phong trào sang
hiệu quả thực chất"* ([Công Lý](https://doanhnhan.congly.vn/sv-startup-2026-lam-that-thi-that-hieu-qua-thuc-chat.html) ·
[VJST](https://vjst.vn/sv-startup-2026-chuyen-bien-ro-net-tu-y-tuong-sang-san-pham-tu-phong-trao-sang-hieu-qua-thuc-chat-86335.html)).
**Đây là lý do mạnh nhất để chạy 2–3 phiên thật trước 30/09.** Trong một mùa mà khẩu hiệu là
"làm thật", con số "0 phiên thật" là thứ đắt nhất mà đội đang mang theo.

*(Ghi chú: các mục **KHÔNG TÌM THẤY** đã kiểm mà không ra kết quả: tên sản phẩm giải Nhất
bảng D3 Tin học trẻ 2021–2026 — báo chí chỉ đăng tên thí sinh; tên dự án giải Nhất bảng C
HackAIthon 2026; đề tài giải Nhất CNTT Euréka 2021; giải thưởng mang tên "Khoa học công nghệ
Quang Trung" của TW Đoàn — không tồn tại, giải đúng tên là **"Quả cầu vàng"**; cuộc thi cấp
quốc gia mang đúng tên "Ý tưởng sáng tạo trẻ" — không tồn tại, tương đương là SV_STARTUP.)*

---

## 9. RỦI RO LOẠI ĐỘI VÀ ĐIỂM CHẾT — KIỂM TRA TRƯỚC KHI NỘP

| Rủi ro | Mức | Xử lý |
|---|---|---|
| **Lịch sử commit một tác giả "LiveLift Team"** cho cả 42 commit, mỗi commit gói trọn một ngày lớn | 🔴 **CAO** | **KHÔNG viết lại lịch sử git** — đó mới là giả mạo và bị Điều 5 cấm đích danh. Xử lý: (a) từ hôm nay commit bằng tên thật từng người; (b) thêm `CONTRIBUTORS.md` + `docs/phan-cong.md` giải thích **trung thực** rằng giai đoạn đầu đội dùng một identity chung và ai phụ trách phần nào; (c) mỗi thành viên phải **giải thích được phân hệ mình phụ trách** khi bị hỏi chéo; (d) bản kê khai AI chi tiết |
| **Prompt Log chưa tổ chức thành dạng nộp được** (thể lệ đòi System Prompt + toàn bộ conversation history) | 🔴 **CAO** | Dựng `prompt_log/` theo §5.3 Món 6 ngay tuần này, không để đến 29/09 |
| **Link Google Drive chưa mở quyền** — MẪU 3 mục 13 ghi rõ *"bắt buộc mở quyền truy cập trước khi nộp"* | 🟠 TRUNG BÌNH | Kiểm bằng trình duyệt ẩn danh, 2 người cùng kiểm |
| **`collectors/tiktok_public`** — thu thập dữ liệu nền tảng không qua API chính thức | 🟠 TRUNG BÌNH | Quyết dứt: gỡ khỏi bản nộp, **hoặc** giữ và ghi rõ "không sử dụng trong kết quả nào, cách ly bằng test CI chặn import ngược", kèm lý do |
| **Số liệu lệch giữa các tài liệu** — `TONG-KET-DU-AN.md` (07/09) ghi 611 test / 24 sự cố; `FACT-SHEET.md` (14/09) ghi 1.009 test / 41 sự cố | 🟠 TRUNG BÌNH | Đồng bộ hết trước khi nộp ≥24 giờ. Đây đúng là kịch bản mà chính FACT-SHEET đã cảnh báo |
| **Số hiệu kế hoạch bịa** (01-KH/TWĐTN-KHCN) nếu lọt vào hồ sơ | 🟠 TRUNG BÌNH | Xóa ngay (§1.2) |
| **Sản phẩm không truy cập được khi giám khảo kiểm** (Chung kết: ≥48 giờ ổn định, lỗi chủ quan → điểm vận hành có thể 0) | 🟡 (cao ở tháng 11) | Deploy sớm + uptime monitor + runbook khôi phục |
| **Video demo thiếu mặt thành viên** (Vòng Khu vực đòi có mặt TẤT CẢ) | 🟡 | Đưa vào checklist §5.5 mục 8 |

---

## 10. NĂM VIỆC PHẢI LÀM NGAY HÔM NAY (14/09/2026)

| # | Việc | Ai | Bao lâu | Xong nghĩa là |
|---:|---|---|---|---|
| **1** | **Gọi BTC** — 0988.086.273 (đ/c Nguyễn Sỹ Vinh) hoặc 0344 268 982 (đ/c Đoàn Quang Trung, CYTAST). Hỏi 3 câu ở §1.1, **quan trọng nhất là câu 3: bộ dữ liệu và đề bài hackathon Bảng C có công bố trước ngày thi không**. Ghi ngày giờ, tên người trả lời, nội dung vào chính file này | **Bình Minh** | **20 phút** | Có 3 câu trả lời ghi thành văn trong file này |
| **2** | **Mở fanpage CYTAST** ([facebook.com/cytast.twd](https://www.facebook.com/cytast.twd/)) bằng tài khoản cá nhân, kéo hết bài từ 25/07/2026 đến nay, chụp màn hình mọi thông báo liên quan Bảng C — đặc biệt tìm **danh mục nhóm chủ đề** và **lịch tập huấn**. Đây là kênh duy nhất chưa quét được | **Lâm Tiến** | **30 phút** | Thư mục ảnh chụp + một dòng kết luận: đã công bố chủ đề hay chưa |
| **3** | **Đặt lại danh tính git và mở gói liêm chính**: mỗi người `git config user.name` + `user.email` bằng tên và email thật; tạo `CONTRIBUTORS.md` và `docs/phan-cong.md` ghi ai phụ trách phân hệ nào; tạo thư mục `prompt_log/` với `system-prompt.md`. **Không chạm vào lịch sử commit cũ** | **Xuân Khánh** (dẫn), cả 3 cùng chạy lệnh | **45 phút** | Commit tiếp theo của mỗi người mang tên thật; 2 file mới đã commit |
| **4** | **Chốt lịch 2 phiên live thật** trước 28/09: chọn ngày, chọn mặt hàng, tạo link đo `/r/{code}`, đặt lịch gán **trước** phát sóng. Việc này phải khởi động HÔM NAY vì nó có thời gian chờ (chuẩn bị hàng, chạy quảng cáo, mời người xem) | **Bình Minh** + **Lâm Tiến** | **1 giờ** | Hai ngày giờ cụ thể ghi vào lịch + danh sách việc chuẩn bị |
| **5** | **Khởi tạo repo `hack-kit`** (§5.3): tạo repo public, dựng khung thư mục, `Makefile`, `pyproject.toml`, CI xanh với một test rỗng. Chỉ cần **khung chạy được**, nội dung làm dần đến 08/10. Cả 3 cùng commit để có commit history thật nhiều tác giả ngay từ đầu | **Xuân Khánh** dựng, cả 3 commit | **1 giờ** | `make all` chạy được trên dữ liệu giả; CI badge xanh; có commit của cả 3 người |

**Tổng thời gian 5 việc: khoảng 3,5 giờ cho cả đội.** Không việc nào cần tiền, không việc nào
cần chờ ai bên ngoài trả lời. Bốn trong năm việc này đều đánh vào những lỗ hổng mà không một
giờ viết hồ sơ nào lấp được.

---

### Lịch rút gọn 16 ngày còn lại

| Ngày | Việc chính |
|---|---|
| 14–15/09 | 5 việc hôm nay + bắt đầu viết lại MẪU 3 theo khung §3 |
| 16–18/09 | Deploy công khai HTTPS; bảng nguồn dữ liệu × giấy phép; xử lý `collectors/tiktok_public` |
| 19–24/09 | **Chạy 2–3 phiên live thật**; lấy 3–5 xác nhận người bán; đồng bộ FACT-SHEET ↔ mọi tài liệu |
| 25–27/09 | Hoàn thiện MẪU 3 (đặc biệt mục 9 và mục 11); quay 2 video; gom Prompt Log + bản kê khai |
| 28/09 | **Review chéo toàn hồ sơ, đối chiếu từng số với FACT-SHEET** (đúng luật nội bộ: ≥24 giờ trước nộp) |
| 29/09 | **Nộp sớm 1 ngày.** Kiểm tra mọi quyền truy cập bằng trình duyệt ẩn danh |
| 30/09 | Hạn cuối — chỉ dùng làm đệm sự cố |
| 01–08/10 | **Toàn lực cho `hack-kit`** (§5.3, 8 món) + diễn tập một hackathon 8 giờ với dataset công khai bất kỳ |
| 09/10 | Nghỉ, chuẩn bị thiết bị, in checklist §5.5 |
| **10–11/10** | **VÒNG KHU VỰC — TP.HCM — 60% ĐIỂM** |
