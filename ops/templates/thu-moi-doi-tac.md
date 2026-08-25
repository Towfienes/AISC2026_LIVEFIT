# Thư mời đối tác dữ liệu — mẫu (kế hoạch phụ lục C)

*Gửi cho nhà bán đang livestream đều đặn (mục tiêu: 10 thư trong tuần 1). Cá nhân hóa
phần 「...」 trước khi gửi. Kênh gửi: tin nhắn Page hoặc email; theo dõi trong bảng
đối tác của nhóm.*

---

Chào anh/chị 「tên」,

Em là sinh viên đang xây một công cụ hỗ trợ vận hành phiên livestream, giúp trả lời câu
hỏi mà hầu như không ai đo được: *hành động nào trong phiên thực sự tạo ra đơn, và hành
động nào chỉ trùng thời điểm.*

Em đang tìm một nhà bán đang livestream đều đặn để dùng thử miễn phí. Cụ thể: em gắn một
màn hình phụ cho tổ trung control, hệ thống gợi ý thời điểm ghim sản phẩm, và sau mỗi phiên
anh/chị nhận một báo cáo cho biết chiến thuật nào hiệu quả trên chính phòng của mình.

Anh/chị không phải trả phí và không phải thay đổi cách làm hiện tại. Em chỉ xin phép ghi
lại dữ liệu vận hành của phiên, đã được xử lý ẩn danh, để phục vụ nghiên cứu.

Nếu anh/chị quan tâm, em xin 15 phút để trình bày cụ thể.

Em cảm ơn anh/chị,
「tên người gửi」 — 「số điện thoại / kênh liên hệ」

---

## Ghi chú nội bộ (không gửi kèm)

- Cam kết trong thư phải khớp hệ thống thật: dữ liệu bình luận đã qua bộ lọc PII tại
  ingest (không lưu bình luận thô), dữ liệu đối tác nằm schema riêng có nhãn `partner_id`.
- Chế độ chạy với đối tác là **đề xuất** (suggest) — hệ thống gợi ý, tổ trung control của
  đối tác quyết định; phân tích dùng LATE/IV nên tuân thủ một phần vẫn có giá trị.
- Không hứa con số hiệu quả cụ thể; báo cáo sau phiên phân biệt rõ số dự báo và số đo được
  (quy tắc E2-04).
- Tích hợp Page đối tác cần Meta App Review (Advanced Access) — nộp hồ sơ từ tháng 9,
  budget 4–6 tuần (xem `docs/research/2026-08-24-apis-competition.md`). Live Lab của nhóm
  không bị chặn bởi việc này.
