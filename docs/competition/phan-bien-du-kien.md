# Câu trả lời phản biện — 4 câu hỏi CHẮC CHẮN bị hỏi mà hồ sơ chưa trả lời

*Tạo 06/09/2026, từ phản biện đối kháng (vai giám khảo trưởng) trên toàn bộ hồ sơ.
Bổ sung cho bảng 9 câu hỏi khó đã có ở Kế-Hoạch §11 — 4 câu này đang là điểm mù.*

---

## Câu 1 — "Nhà bán Việt live trên TikTok Shop và Facebook. Sao sản phẩm ingest YouTube?"

**Trả lời (1 slide):**

- Chúng em **chọn YouTube làm nền tảng pilot có chủ đích**, không phải vì không biết
  thị trường: YouTube là nền tảng duy nhất có **API chính thức, công khai, hợp pháp**
  cho comment + số người xem realtime mà một đội sinh viên tiếp cận được ngay.
  Facebook cần App Review cho Page ngoài nhóm (đã nộp song song — Development Mode đọc
  được Page của nhóm ngay); TikTok **không có API công khai** cho live comment —
  mọi công cụ hiện có đều scrape không chính thức, vi phạm ToS.
- Kiến trúc ingest được thiết kế **đa nền tảng từ ngày đầu**: mọi nguồn đi qua cùng
  một chuẩn (comment/tick 30s → PII filter → khối), nguồn mới = một adapter
  (`src/livelift/ingest/`). Collector TikTok public đã tồn tại ở dạng **cách ly**
  (`collectors/tiktok_public`, chỉ dùng cho phân tích quan sát, CI chặn import ngược).
- Lộ trình: pilot YouTube + Facebook Page đối tác (mùa thi) → TikTok Shop khi có
  **TikTok Shop Partner API** (đường chính thức duy nhất; yêu cầu pháp nhân — việc
  sau mùa thi). **Phương pháp không phụ thuộc nền tảng** — switchback + shortlink đo
  click là của chúng em, chạy được ở bất cứ đâu có comment và người xem.

## Câu 2 — "Nếu TikTok Shop / Shopee tự làm A/B ghim sản phẩm thì startup này còn gì?"

**Trả lời (1 slide):**

- **Xung đột lợi ích cấu trúc:** sàn tối ưu GMV **của sàn** và phí quảng cáo, không
  trung lập cho từng nhà bán. Một công cụ đo lường mà bên bán tin được phải **độc lập
  với bên bán hạ tầng phát** — cùng lý do thị trường cần Nielsen dù đài truyền hình
  tự đo rating được.
- **Đa nền tảng là mặc định của nhà bán Việt:** một shop live đồng thời/luân phiên
  Facebook + TikTok + Shopee. Sàn chỉ thấy phòng của sàn; LiveLift là **lớp đo lường
  nằm về phía nhà bán**, gom mọi phòng về một chuẩn đo.
- **Dữ liệu thí nghiệm thuộc về nhà bán:** lịch gán, propensity, kết quả — nhà bán
  mang đi được. Sàn không có động cơ cung cấp điều đó.
- Và thực tế SOTA: các sản phẩm AI livestream đang có (TikTok Live Studio AI,
  LiveThinking của Taobao, Syntopia…) đều **tối ưu mà không đo nhân quả** — không
  cái nào có propensity logging + randomization inference đã hiệu chuẩn A/A. Đó là
  moat phương pháp của chúng em, đã chạy được, không phải lời hứa.

## Câu 3 — "Lift đo được là bao nhiêu?" (khi kết quả có thể 'chưa kết luận được')

**Chủ động định khung TRƯỚC trong hồ sơ vòng 1, không đợi bị hỏi:**

- Với ngưỡng khán giả thực đo (300k quảng cáo ≈ 5–15 người xem đồng thời), xác suất
  các phiên đầu cho khoảng tin cậy rộng là **cao — và chúng em nói điều đó trước**.
- Định vị đúng: **chúng em không bán một con số đẹp; chúng em bán hạ tầng đo lường
  tự chứng minh được.** Kết quả "chưa kết luận được" + MDE trung thực + đường tăng
  lực đã tính sẵn (nhiều phiên hơn, phòng đối tác 200–500 người, trọng số exposure,
  CUPED đa biến theo văn liệu 2026) **vẫn là kết quả hợp lệ** — và là thứ không đội
  nào khác dám trình.
- Câu chốt tập dượt: *"Cả ngành đang ra quyết định bằng cảm giác. Đội duy nhất DÁM
  đo và nói thật con số đo được đến đâu — chính là sản phẩm."*

## Câu 4 — "Cơ sở pháp lý THU THẬP dữ liệu người xem?" (không chỉ lọc PII)

Hồ sơ hiện viện dẫn Luật 91/2025 cho khâu **lọc**; cần trả lời đủ khâu **thu thập**:

- **Nghị định 13/2023/NĐ-CP** (bảo vệ dữ liệu cá nhân): bình luận của người xem được
  xử lý → cơ chế của chúng em: (1) **khử nhận dạng tại ingest** — text thô không bao
  giờ chạm đĩa, author id bị drop lúc parse, salt xoay theo phiên; (2) không lưu chuỗi
  hành vi theo cá nhân; (3) phiên do nhóm vận hành có **thông báo công khai trong
  phần mô tả live** rằng bình luận được phân tích ẩn danh phục vụ nghiên cứu.
- **ToS nền tảng:** YouTube Data API — dùng đúng quota, đúng mục đích được cấp;
  Facebook Graph — chỉ Page có ủy quyền (Development Mode / App Review); TikTok —
  KHÔNG thu thập live (collector cách ly chỉ dữ liệu công khai, chỉ phân tích quan sát).
- **Ba nguồn dữ liệu hợp lệ** đã tuyên bố trong README: API chính thức có ủy quyền ·
  dữ liệu công khai (chỉ quan sát) · dữ liệu nhóm tự tạo.
- ✅ Việc cần làm (P1): thêm 1 đoạn "cơ sở pháp lý thu thập" vào thuyết minh, và một
  dòng thông báo chuẩn vào runbook phiên live (`ops/runbooks/quy-trinh-phien.md`).

---

*Diễn tập: mỗi câu trả lời đọc to ≤ 60 giây. Người ngoài đóng vai giám khảo, gồm
kịch bản kết quả null (câu 3) — trước vòng thuyết trình.*
