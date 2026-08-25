# Nhật ký phiên — mẫu (kế hoạch phụ lục B, mở rộng)

*Điền trong vòng 1 giờ sau khi kết thúc phiên (mốc T+1h của runbook). Người điền: SP.
Lưu một bản mỗi phiên: `ops/logs/nhat-ky-phien-<số-phiên>-<YYYY-MM-DD>.md`.*

---

```
Phiên số:                       Ngày:                     Nền tảng:
Session ID (uuid):
Host:                           Chế độ: tự động / đề xuất
Thời lượng thực tế:             Ngân sách quảng cáo:
Người xem đỉnh:                 Người xem trung bình:

--- Lịch gán ---
Seed lịch gán (ghi từ output livelift-schedule):
Lịch sinh lúc (giờ, phải TRƯỚC giờ phát sóng):
Số khối:            BẬT:            TẮT:            Số lần redraw (n_redraws):

--- Thực thi ---
Số hành động thực thi:          Số lần can thiệp thủ công:
Lý do can thiệp thủ công (chỉ được: hết hàng / sai giá / sự cố kỹ thuật — ghi từng lần + block):

Sự cố kỹ thuật (mất ingest, rớt mạng, camera... — ghi khoảng thời gian):

--- Sự cố burn-in ---
(Bất thường trong ~1–2 phút đầu khối: đổi ghim trễ, host đang chốt đơn dở giữa lúc chuyển
khối, hype còn kéo dài từ khối trước... — ghi block_index + mô tả; phân tích dùng để
sensitivity check b ∈ {0,1,2,3} phút)



--- Sự cố làm mù ---
(Host nhìn thấy màn hình operator? Ai đó nói to trạng thái/ranh giới khối? Host đoán được
BẬT/TẮT và nói ra? — ghi block_index + mô tả. KHÔNG GIẤU: khối liên quan sẽ được cân nhắc
excluded_reason, giấu thì hỏng cả chuỗi)



--- Ghi chú ---
Ghi chú định tính (điều gì bất thường trong phiên):

Ghi chú vận hành 3 dòng (HARNESS §5 — điều gì vướng tay, thẻ nào bị bỏ qua và vì sao,
màn hình thiếu gì):
1.
2.
3.

--- Chất lượng dữ liệu ---
livelift-qc: đạt / không đạt — chi tiết từng mục không đạt:

Shortlink hoạt động cả phiên: có / không — chi tiết:

Người điền:                     Giờ điền:
```
