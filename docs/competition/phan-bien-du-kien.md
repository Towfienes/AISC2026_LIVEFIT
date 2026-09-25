# Câu trả lời phản biện — 4 câu hỏi CHẮC CHẮN bị hỏi mà hồ sơ chưa trả lời

*Tạo 06/09/2026, từ phản biện đối kháng (vai giám khảo trưởng) trên toàn bộ hồ sơ.
Bổ sung cho bảng 9 câu hỏi khó đã có ở Kế-Hoạch §11 — 4 câu này đang là điểm mù.*

*Cập nhật 25/09/2026 sau kiểm toán: câu 1 trả lời bằng đường API chính thức theo quyết định
17/09 ("chỉ API chính thức, không đọc bình luận kiểu người xem"); câu 3 sửa "thực đo" thành
**ước tính, chưa đo**; câu 4 thay NĐ 13/2023 bằng NĐ 356/2025/NĐ-CP và tách rõ khâu thu thập.
Mọi con số khớp `docs/competition/FACT-SHEET.md`.*

---

## Câu 1 — "Nhà bán Việt live trên TikTok Shop và Facebook. Sao sản phẩm ingest YouTube?"

**Trả lời (1 slide):**

- **LiveLift chỉ dùng API chính thức, trên kênh của chính nhà bán hoặc của đối tác đồng ý.**
  Mỗi nền tảng là một bộ nối riêng; lõi đo lường không đổi. Tình trạng từng nền tảng:
  - **YouTube** (YouTube Data API, bình luận live thời gian thực): khoá API miễn phí, không
    cần duyệt ứng dụng — là nền tảng pilot vì nhóm lấy được ngay.
  - **Facebook** (Graph API, Page của chính mình): chế độ Development đọc được Page của nhóm
    không cần App Review; Page đối tác mới cần duyệt.
  - **Shopee Live** (Open Platform, loại xác thực User): có API ghim sản phẩm
    `update_show_item`; bộ nối đã viết (`src/livelift/ingest/shopee.py`).
  - **TikTok**: đường chính thức là **TikTok Shop Open Platform cho người bán**
    (`shop_lives/*`, quyền "TikTok Shop Analytics"): số liệu phiên live **theo từng phút,
    chỉ có SAU khi phiên kết thúc**, không có nội dung bình luận, và shop phải có Account
    Manager. Nên với TikTok, LiveLift chạy chế độ **đối chiếu sau phiên**: lịch BẬT/TẮT vẫn
    bốc và niêm phong trước giờ phát, kết quả so theo phút từ số liệu của chính shop. Bộ nối
    đã viết theo tài liệu chính thức (`src/livelift/ingest/tiktok_shop.py`) — chưa gọi thật
    vì nhóm chưa có shop đủ điều kiện. Nguồn: `docs/research/2026-09-17-tiktok-duong-chinh-thuc.md`.
- **Nói thẳng tình trạng:** tới 25/09/2026 nhóm **chưa có khoá API nền tảng nào**, nên mọi bộ
  nối chính thức mới được kiểm bằng dữ liệu mẫu và mã lỗi theo tài liệu — chưa có cuộc gọi
  nào với một buổi live thật.
- **Phương pháp không phụ thuộc nền tảng:** switchback + link đo lượt nhấp là của nhóm, chạy
  được ở bất cứ đâu nhà bán điều khiển được hành động của chính mình.
- *Nếu bị hỏi về thư mục `collectors/tiktok_public` trong kho:* mã từ giai đoạn khảo sát, cách
  ly khỏi lõi (CI chặn import ngược), không nằm trên đường chạy sản phẩm. Từ 17/09 nhóm quyết
  định không đọc bình luận kiểu người xem; việc gỡ hẳn thư mục đang chờ chủ dự án chốt.

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
  moat phương pháp của nhóm: đã hiệu chuẩn trên mô phỏng (A/A bác bỏ 3,50%, độ phủ KTC
  96,50%), **chưa chạy trên phiên thật nào**.

## Câu 3 — "Lift đo được là bao nhiêu?" (khi kết quả có thể 'chưa kết luận được')

**Chủ động định khung TRƯỚC, không đợi bị hỏi:**

- Hiện có **0 phiên thí nghiệm ngẫu nhiên thật** — chưa có con số lift thật nào.
- Theo **ước tính trên giấy (chưa đo)**, 300.000đ quảng cáo chỉ kéo được khoảng 5–15 người
  xem đồng thời (tính từ CPM ngày 24/08, `docs/research/2026-08-24-phan-bien-tai-lieu.md`
  mục R1). Điểm MDE mô phỏng gần nhất của nhóm là 16,4% ở khoảng 59 người xem đồng thời
  (8 phiên mô phỏng, Hình 4 hồ sơ); ở 5–15 người xem và 18 phiên, riêng sàn Poisson đã là
  21–37% (tỷ lệ nhấp 1,00) hoặc 39–67% (tỷ lệ nhấp 0,30) — cận dưới, nguồn
  `docs/competition/sang-tao-tre-2026/hinh/du-lieu/tom-tat.json`. Con số 20,1% của phép quét
  30/08 chưa đo lại, không trích. Nên xác suất các phiên
  đầu cho khoảng tin cậy rộng là **cao — và nhóm nói điều đó trước**.
- Định vị đúng: **nhóm không bán một con số đẹp; nhóm bán hạ tầng đo lường tự chứng minh
  được.** Kết quả "chưa kết luận được" + MDE trung thực + đường tăng lực đã tính sẵn (nhiều
  phiên hơn, phòng đối tác 200–500 người, trọng số exposure, CUPED đa biến) **vẫn là kết quả
  hợp lệ**.
- Câu chốt tập dượt: *"Cả ngành đang ra quyết định bằng cảm giác. Nhóm em đo, và nói thật
  con số đo được đến đâu."*

## Câu 4 — "Cơ sở pháp lý THU THẬP dữ liệu người xem?" (không chỉ lọc PII)

Trả lời đủ cả khâu **thu thập**, không chỉ khâu lọc — và không nhận một căn cứ chưa đối chiếu:

- **Khung pháp lý:** Luật Bảo vệ dữ liệu cá nhân **91/2025/QH15** (hiệu lực 01/01/2026) và
  **Nghị định 356/2025/NĐ-CP** (thay Nghị định 13/2023/NĐ-CP).
- **Đường sản phẩm:** chỉ API chính thức, chỉ đọc phiên live của **chính nhà bán** (hoặc
  đối tác đồng ý) — nhà bán là bên có quyền với kênh của mình, LiveLift xử lý thay họ.
  Biện pháp: (1) **khử nhận dạng tại ingest** — text thô không bao giờ chạm đĩa, author id
  bị bỏ lúc parse, salt xoay theo phiên; (2) không lưu chuỗi hành vi theo cá nhân; (3) phiên
  do nhóm vận hành **sẽ** có thông báo công khai trong phần mô tả live rằng bình luận được
  phân tích ẩn danh (chưa có phiên thật nào nên chưa áp dụng).
- **Bộ dữ liệu quan sát 16 buổi (19.126 bình luận):** lấy từ VOD YouTube **công khai** bằng
  yt-dlp — **không phải API chính thức**, và nhóm đã tự ghi nhận cách lấy này không phù hợp
  điều khoản dịch vụ của YouTube (`docs/nen-tang-ho-tro.md`: "yt-dlp trái ToS YouTube"). Dữ liệu đi qua cùng bộ khử nhận dạng, chỉ dùng phân tích
  quan sát; từ 17/09 nhóm quyết định không mở rộng kiểu thu thập này, đường sản phẩm chỉ
  dùng API chính thức.
- **Ba nguồn dữ liệu** đã tuyên bố trong README: API chính thức có ủy quyền · dữ liệu công
  khai (chỉ quan sát) · dữ liệu nhóm tự tạo.
- Việc cần làm (P1): thêm một đoạn "cơ sở pháp lý thu thập" vào thuyết minh, và một dòng
  thông báo chuẩn vào runbook phiên live (`ops/runbooks/quy-trinh-phien.md`).

---

*Diễn tập: mỗi câu trả lời đọc to ≤ 60 giây. Người ngoài đóng vai giám khảo, gồm
kịch bản kết quả null (câu 3) — trước vòng thuyết trình.*
