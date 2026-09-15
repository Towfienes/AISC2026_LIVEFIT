# E6-01 — Khung bản thuyết minh vòng 1 (nhập vào mẫu BTC khi có)

*Tạo 06/09/2026. TRẠNG THÁI: khung nội dung + bằng chứng đã có sẵn trong repo.
Việc con người: (1) xin mẫu thuyết minh + rubric chấm từ BTC HÔM NAY, (2) đổ nội dung
dưới đây vào đúng mẫu, (3) mọi con số tra `FACT-SHEET.md`, (4) review chéo, nộp trước hạn ≥24h.*

> Nguyên tắc: giám khảo vòng 1 chấm qua **bản thuyết minh + video demo**, gần như không
> ai clone repo. Mọi thứ mạnh nhất của dự án phải NHÌN THẤY ĐƯỢC trong tài liệu này.

## 1. Vấn đề (½ trang)

- Câu mở: *Phút 30 ghim sản phẩm B, phút 35 doanh thu tăng 40% — do ghim, do thuật
  toán đẩy 500 người xem, hay do host kể chuyện hay? Không ai biết. "Kinh nghiệm"
  cả ngành phần lớn là tương quan giả.*
- Số thị trường: 2,5 triệu phiên/tháng, >50k nhà bán (FACT-SHEET §3).
- Bằng chứng bình duyệt bài toán là thật: POM 2025 — trình bày sản phẩm lâu hơn thì
  doanh thu sản phẩm cao hơn, nhưng thời lượng trung bình tăng thì doanh thu cả phiên
  giảm (đính chính 15/09: không phải "chữ U ngược") → "ghim gì, lúc nào, bao lâu" là
  một đánh đổi chưa có lời giải per-session.
- Khoảng trống: mọi công cụ hiện có (Chanmama, Feigua, Kalodata, cả AI của TikTok/
  Taobao) chỉ quan sát hồi cứu hoặc gợi ý **không đo nhân quả**.

## 2. Giải pháp (1 trang, có hình)

- 1 câu: *LiveLift biến mỗi quyết định ghim sản phẩm trong phiên live thành một thí
  nghiệm ngẫu nhiên đo được.*
- Hình 1: switchback 2 tầng (lấy từ README, vẽ lại sạch).
- 4 gạch đầu dòng cho người không chuyên: khối 5 phút BẬT/TẮT ngẫu nhiên → so trong
  cùng phiên, cùng host, cùng thuật toán → tách giá trị thật khỏi trùng hợp thời điểm
  → mỗi kết luận kèm khoảng tin cậy và có thể tái lập từ seed.
- Screenshot: bàn trung control + trang kết quả (che số chưa chốt).

## 3. Demo & bằng chứng đã chạy được (1 trang — TRỌNG TÂM vòng 1)

| Bằng chứng | Số | 
|---|---|
| Phiên live thật end-to-end | ⬜ CHẠY TRƯỚC 12/09 — screenshot dashboard + số chi phí/người xem đo được |
| Live-fire dữ liệu thật | 14.903 bình luận VOD 262 phút qua toàn pipeline |
| Ước lượng viên tự chứng minh | A/A 200 lặp: bác bỏ 3,50%, coverage 96,50% |
| Mô phỏng hiệu chỉnh dữ liệu thật | KuaiLive 1,16M phòng live shop (SIGIR 2026) |
| NLP tiếng Việt | intent F1 0,870 (bộ biên soạn — caveat trung thực) + lọc PII đã vá đối kháng |
| Kỷ luật kỹ thuật | 157+ test, 13 sự cố root-cause, tiền đăng ký sẽ khóa bằng commit |
| Video demo 2–3 phút | ⬜ quay SAU khi có phiên thật: chạy phiên → desk → kết quả |

## 4. Business (1 trang — track là "Data Driven Business")

- Khách hàng: tổ vận hành 1–3 người của nhà bán vừa; nỗi đau bằng **trích dẫn nguyên
  văn từ 5 phỏng vấn** (⬜ làm tuần này — quan trọng nhất phần business).
- Funnel ra tiền (1 bảng "kịch bản", giả định ghi rõ): click/1000 viewer-giây → đơn
  → GMV → giá trị tăng thêm/tháng cho 1 shop.
- Mô hình giá: Free → Pro 990k → Agency 3,9M (nhãn "dự kiến, hiệu chỉnh sau phỏng vấn
  WTP") + gói Performance đo bằng holdback ngẫu nhiên 10% khối — *sản phẩm hiếm hoi
  tự chứng minh được giá trị của mình*.
- Go-to-market mùa 1: 10 thư đối tác (⬜ gửi tuần này) → phòng 200–500 người xem.
- 2 câu trả lời sẵn: TikTok-gap + moat-vs-sàn (`phan-bien-du-kien.md` câu 1–2).

## 5. Phương pháp & liêm chính (½ trang — điểm khác biệt, viết cho người không chuyên)

- Thiết kế theo văn liệu đỉnh (Bojinov 2023 Mgmt Sci; Hu–Wager 2022) — cùng họ phương
  pháp P&G production hóa 2025 (HBS WP 26-012).
- 4 cơ chế chống tự lừa: tiền đăng ký khóa commit · lịch gán lưu trước phát sóng, seed
  tái lập · màn host làm mù ở cấp kiểu dữ liệu · **dashboard tự khóa kết quả trước ngày
  đóng băng** (tính năng mới — nêu như điểm cộng).
- Giới hạn tự khai (1 đoạn): 0 phiên thật đến nay → mục tiêu 2 phiên trước nộp; số
  intent trên bộ biên soạn; MDE 20,1% ở điều kiện sim; khán giả thưa là rủi ro chính
  và đã có kế hoạch đối tác. *Một đội tự nêu giới hạn bằng số được tin hơn một đội
  khẳng định mọi thứ đều tốt.*

## 6. Đội & kế hoạch đến chung kết (¼ trang)

- Vai trò SP/TN/KS/NC + mốc: vòng 2 (25/09), vận động bình chọn (01/10 — video 90s
  "Đừng đoán nữa — đo đi"), ≥18 phiên trước chung kết, khóa tiền đăng ký tuần 6.

## Checklist trước khi nộp

- [ ] Mẫu + rubric BTC đã có, ma trận đối chiếu mục-hồ-sơ ↔ tiêu-chí-chấm
- [ ] Mọi số khớp FACT-SHEET (người thứ hai đối chiếu từng số)
- [ ] ≥1 phiên live thật có screenshot trong §3
- [ ] Video demo 2–3 phút link sẵn
- [ ] 5 trích dẫn phỏng vấn trong §4
- [ ] Nộp trước hạn ≥ 24h, có xác nhận từ hệ thống BTC
