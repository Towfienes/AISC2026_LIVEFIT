# FACT SHEET — Một bộ số chuẩn duy nhất

*Tạo 06/09/2026 · cập nhật 14/09/2026 · Mọi tài liệu (thuyết minh, slide, kế hoạch, mô tả) TRỎ VỀ file này.
Sửa số ở đây trước, rồi đồng bộ ra các tài liệu khác — không bao giờ ngược lại.*

> **Lý do tồn tại:** kiểm toán 06/09 phát hiện các tài liệu gốc đang lệch nhau
> (ngân sách 17,2M vs 15,2M; 31 vs 30 phiên; hạn nộp 14 vs 15/09). Một giám khảo
> kỹ tính bắt được lệch số trong 5 phút và mất niềm tin vào mọi số còn lại.

## 1. Các số PHẢI CHỐT (đang lệch giữa tài liệu — cần quyết định của nhóm)

| Số | Kế-Hoạch-Triển-Khai | Mô-Tả-Dự-Án | ĐÃ CHỐT | Ghi chú |
|---|---|---|---|---|
| **Hạn nộp vòng 1** | 14/09 (dòng 229) | 15/09 (dòng 536) | ⬜ __/09 | **GỌI BTC XÁC MINH HÔM NAY** — "trễ 1 ngày = loại" |
| **Tổng ngân sách** | 17.200.000đ (§9.1) | 15.200.000đ (§8.2) | ⬜ | Khác nhau ở: quảng cáo 29 vs 30 phiên, bổ sung hàng 1,5M, poster 0,8M. Khuyến nghị: dùng bảng §9.1 chi tiết hơn làm gốc, cộng lại cho khớp |
| **Số phiên mục tiêu** | 31 (§8.4) | 30 (§8.2, §14) | ⬜ | Chọn MỘT số, dùng thống nhất |
| **Người xem đồng thời mục tiêu** | ≥ 80 (§8.4) | "vài trăm" giả định CV 0,5 (§8.2) | ⬜ | **Thực đo: 300k quảng cáo ≈ 5–15 đồng thời** (TONG-KET P0) — mục tiêu 80 hụt ~10 lần. Phải hạ mục tiêu hoặc đổi chiến lược (đối tác) và sửa MỌI bảng lực thống kê theo |

## 2. Các số đã đo được (nguồn: repo, sinh lại được bằng lệnh)

| Số | Giá trị | Nguồn kiểm chứng |
|---|---|---|
| Hiệu chuẩn A/A ước lượng viên | bác bỏ 4,5% (danh nghĩa 5%), p nhị thức = 0,872 | gate `test_sim_validation.py`, 200 lặp |
| Độ phủ KTC 95% | 95,5% | cùng gate |
| MDE đo được (điều kiện sim hiệu chỉnh) | 20,1% | sweep 4 mức tác động × 60 lặp, `analysis/power` |
| Intent classifier | macro-F1 0,870 — **trên 320 câu tự biên soạn, 5-fold CV** | `python -m livelift.nlp.train_intent` |
| ⚠️ Quy tắc quote số intent | LUÔN kèm caveat "trên bộ biên soạn; số trên chat thật đang đo" | `docs/benchmarks/intent-classifier.md` |
| Live-fire VOD thật | 262 phút, 14.903 bình luận qua API | phiên "quan sát" trong DB |
| Hiệu chỉnh KuaiLive | 1,16M phòng live shop thật (SIGIR 2026) | `docs/benchmarks/kuailive-calibration.md` |
| Bộ kiểm thử | **993 test nhanh xanh + 16 cổng Monte-Carlo = 1.009** (đếm 14/09/2026) | `pytest -m "not slow"` và `pytest -m slow`; đối chiếu tự động bằng `scripts/dong_bo_so_test.py --xem-truoc` |
| Sổ sự cố | **41 sự cố có nguyên nhân gốc** (đếm 14/09/2026) | đếm số hàng bảng trong `docs/incident-log.md` |
| Bình luận thật đã chạy qua API | **19.126 bình luận · 16 buổi live · 7 ngành hàng** (lô đo 10/09/2026) | `docs/benchmarks/live-fire-da-nguon.md` §1 — con số 14.903 ghi ở bản 06/09 là lô CŨ, đã bị lô 10/09 thay thế |
| Bộ phân loại ý định trên CHAT THẬT | **macro-F1 0,271** (200 bình luận gán nhãn tay) — thua baseline luôn đoán "khac" | `docs/benchmarks/intent-classifier.md`; **luôn quote CẶP 0,870 / 0,271, không bao giờ quote riêng số đẹp** |
| Độ phủ KTC dưới hiệu ứng lưu | bán rã 0 giây → **100%**; 120 giây → **84%**; 180 giây → **60%** (lệch −0,3% / −20,3% / −29,8%) | docstring `run_validation` trong `src/livelift/sim/validate.py`; đo 02/09 trên SimParams đã hiệu chỉnh KuaiLive. **Con số 76% cũ là TRƯỚC hiệu chỉnh, đã bị thay** |
| Điều kiện đo MDE 20,1% | mô phỏng ~45–62 người xem đồng thời | `src/livelift/sim/simulator.py`; **phải nói kèm: đo thật chỉ được 5–15 người xem đồng thời** |
| Số bản migration | 9 (0001–0009) | `ls src/livelift/migrations/*.up.sql` |
| Số phiên live THẬT đã chạy | **0** (tính đến 14/09/2026) | trung thực — không tuyên bố khác đi cho đến khi có |

## 3. Số thị trường dùng trong hồ sơ (kèm nguồn, cập nhật 09/2026)

| Số | Giá trị | Nguồn |
|---|---|---|
| Phiên live bán hàng VN/tháng | ~2,5 triệu; >50.000 nhà bán | Mô-Tả §2 (giữ nguồn gốc khi trích) |
| TikTok Shop VN | 42% GMV e-commerce, +148% YoY (H1/2025) | khảo sát SOTA 06/09 |
| Tỷ lệ chuyển đổi livestream vs feed | ~7,8% vs 2,1% (3,7×) | khảo sát SOTA 06/09 |
| Live commerce SEA | ~14% GMV sàn (~17,6 tỷ USD) | khảo sát SOTA 06/09 |
| Bằng chứng bình duyệt bài toán ghim | Xie–Sharma–Mehra, POM 2025: thời lượng pin vs doanh thu phiên có dạng **chữ U ngược** | slide động cơ |

## 4. Giá gói (TRẠNG THÁI: giả thuyết — chưa phỏng vấn WTP nào)

Free (báo cáo sau phiên) → Pro 990k/tháng → Agency 3,9M/tháng → Performance (% giá trị
tăng thêm, đo bằng holdback 10% khối). **Không trình bày như giá đã kiểm chứng** —
ghi "định giá dự kiến, sẽ hiệu chỉnh sau 5 phỏng vấn nhà bán (kế hoạch tuần này)".
Chuẩn ngành tham chiếu: experimentation platform bán usage-based freemium; lift đo được
là công cụ chứng minh ROI, không phải đơn vị tính tiền.

## 5. Quy tắc dùng file này

1. Trước khi viết bất kỳ số nào vào thuyết minh/slide: tra ở đây. Không có → thêm vào đây trước.
0. **Luật thêm ngày 14/09/2026:** hồ sơ thuyết minh có câu trỏ thẳng vào file này
   ("Mọi số của hồ sơ chốt ở docs/competition/FACT-SHEET.md"). Chấm lại hồ sơ hôm ấy
   phát hiện file này KHÔNG chứa hai con số mà hồ sơ nói nó chốt, và bản thân nó còn
   dừng ở lô đo 06/09. Một giám khảo mở file ra kiểm mất 30 giây là bắt được. Từ nay:
   **sửa hồ sơ mà không sửa file này là chưa xong việc.**
2. Ô ⬜ nào còn trống sau 08/09 là việc P0 chưa xong.
3. Người review chéo hồ sơ đối chiếu từng số trong bản nộp với file này trước khi nộp ≥24h.
