# Kế hoạch 16 ngày tới hạn nộp 30/09/2026

*Lập 14/09/2026. Đội **đã được ĐH Tôn Đức Thắng cử**, nên vào **thẳng Vòng Khu vực** —
không phải qua Vòng loại Quốc gia. Chi tiết thể lệ ở `BRIEF-THE-LE.md`.*

## Ba mốc, và trọng số thật của chúng

| Mốc | Ngày | Chiếm bao nhiêu điểm |
|---|---|---|
| **Nộp hồ sơ** | **30/09/2026** | **40%** của suất vào chung kết |
| **Vòng Khu vực — hackathon 2 ngày, TP.HCM** | **10–11/10/2026** | **60%** |
| Vòng Chung kết — cải tiến 12 giờ + phản biện, Hà Nội | 20–22/11/2026 | quyết định giải Nhất |

> **Điều dễ hiểu sai nhất:** Vòng Khu vực **không** phải buổi bảo vệ LiveLift.
> BTC đưa **một bộ dữ liệu thô lạ + một yêu cầu thực tiễn**, đội xây giải pháp
> tại chỗ trong 2 ngày. Hồ sơ LiveLift chỉ mang 40%. Một đội có hồ sơ xuất sắc
> mà không luyện hackathon vẫn trượt. Kế hoạch dưới đây chia đôi nguồn lực.

---

## GIAI ĐOẠN 1 — Chặn rủi ro loại (14–17/09)

Việc ở giai đoạn này **không nâng điểm**, chúng chỉ giữ cho đội không bị loại hoặc mất trắng một hạng mục.

Trạng thái cập nhật cuối ngày 14/09:

| # | Việc | Ai làm | Trạng thái |
|---|---|---|---|
| 1 | **Bật kho mã sang Public**, kiểm bằng cửa sổ ẩn danh | Minh | ⬜ **CHƯA — chỉ con người làm được.** Kiểm ẩn danh trả 404; link hạng mục "đường dẫn kho mã" sẽ chết trong tay giám khảo |
| 2 | **Xin giấy xác nhận sinh viên** cho cả 3 | Cả 3 | ⬜ **CHƯA — bắt đầu hôm nay**, mất 1–3 ngày làm việc, không ép nhanh được |
| 3 | Điền thông tin thí sinh (địa chỉ cư trú cả 3, SĐT Khánh và Tiến) | Cả 3 | ⬜ **CHƯA** — bộ dựng hồ sơ đang báo đỏ |
| 4 | **Sửa bộ lọc PII + chạy lại trên dữ liệu đã lưu** | Khánh | ◪ **Mã sửa 15/09** (`SOCIAL_HANDLE_RE` dùng `\w` Unicode + 2 test mới). **Còn phải:** lọc lại `data/labeling/`, mở tệp ra kiểm bằng mắt, chạy lại `python -m livelift.nlp.eval_intent` và cập nhật macro-F1 nếu đổi |
| 5 | **Đo lại số hiệu chuẩn, sửa ở mọi nơi** | — | ☑ **XONG.** `scripts/do_lai_so_hieu_chuan.py` → `docs/benchmarks/so-hieu-chuan.json`; đã sửa 6 tài liệu; thêm cổng `tests/test_so_hieu_chuan.py` chống trôi |
| 6 | **Sửa câu mâu thuẫn về nguồn dữ liệu** | — | ☑ **XONG.** Hồ sơ mục 3.3 nay nêu rõ dữ liệu qua yt-dlp, lý do kỹ thuật, và hướng xử lý |
| 7 | Làm xanh lại `pytest` và job lint | — | ☑ **XONG.** `ruff check`/`format` sạch; xung đột hai test `focus-ring` đã giải bằng ngoại lệ có ghi lý do + test canh ngoại lệ |
| 8 | **Vá xác thực 12 endpoint ghi** | — | ☑ **XONG.** Cổng gắn ở cấp ứng dụng; máy chủ tự quyết phiên thật/mẫu theo việc có token hay không |

## GIAI ĐOẠN 2 — Nâng điểm hồ sơ (17–25/09)

Xếp theo **đòn bẩy**: điểm thu được trên mỗi đồng công sức. Điểm hiện tại theo kiểm toán nội bộ: **50/80**.

| Trọng tâm | Đang | Việc nâng điểm | Ai |
|---|---:|---|---|
| **1. Cấp thiết, tác động** | **4** | **Chạy 1–2 phiên live THẬT có gán ngẫu nhiên** (xoá luôn điểm yếu "0 phiên"). Cộng **3–5 phỏng vấn nhà bán thật** có ghi âm/biên bản. Đây là đòn bẩy lớn nhất trong cả bảng | Minh + Khánh |
| **4. Làm chủ** | **5** | Từ nay **commit bằng tên thật từng thành viên**; mở nhánh + PR có người thứ hai duyệt. **Tuyệt đối không viết lại lịch sử git cũ** — đó mới là giả mạo. Viết mục phân công ai làm phân hệ nào | Cả 3 |
| **5. Kết quả, kiểm chứng** | **5** | Xong việc #4 giai đoạn 1. Thêm bảng **baseline + ablation** cho phân hệ NLP (MẪU 3 mục 9 bắt buộc có) | Tiến |
| **7. Triển khai, duy trì** | **5** | **Đưa sản phẩm lên một địa chỉ công khai chạy 24/7**. Thể lệ đòi demo ổn định ≥48 giờ; không truy cập được thì điểm vận hành **có thể tính 0** | Khánh |
| **3. Dữ liệu hợp lệ** | **6** | Xong #3 và #5 giai đoạn 1. Trích đúng **Luật 91/2025/QH15 + NĐ 356/2025/NĐ-CP** (đã thay NĐ 13/2023) | Minh |
| 2. Khoa học | 9 | Giữ nguyên. Không đụng vào | — |
| 6. Phân tích, rủi ro | 8 | Giữ nguyên | — |
| 8. An toàn, đạo đức | 8 | Thêm trích **Luật Trí tuệ nhân tạo 134/2025/QH15** (hiệu lực 01/3/2026) — hầu như không đội nào nghĩ tới | Minh |

## GIAI ĐOẠN 3 — Đóng gói và nộp (25–29/09)

| Việc | Ghi chú |
|---|---|
| Dựng hồ sơ PDF cuối | `dung_ho_so.py` tự đếm trang, tự xuất PDF, tự chặn nếu vượt 20 trang hoặc còn ô trống |
| Quay 2 video | Kịch bản từng giây ở `07-KICH-BAN-2-VIDEO.md`. **Cả 3 phải xuất hiện** |
| Xuất Prompt Log, **đọc lại bằng mắt** rồi đưa lên Drive | `scripts/xuat_prompt_log.py`. Đọc lại tay là bắt buộc — công cụ làm sạch bí mật không hoàn hảo |
| **Mở quyền truy cập Drive** và kiểm bằng cửa sổ ẩn danh | Mục 13 MẪU 3 ghi rõ "bắt buộc mở quyền trước khi nộp" |
| Đối chiếu **từng con số** trong hồ sơ + 2 video với FACT-SHEET | Làm trước hạn ≥24h, người không viết phần đó đi đối chiếu |
| Ký tên, nộp tại ai.tainangviet.vn | Đừng để sát giờ |

## GIAI ĐOẠN 4 — Luyện hackathon (song song, từ 20/09)

**Đây là 60% điểm.** BTC chưa công bố danh mục chủ đề chi tiết; trang Bảng C ghi chủ đề là *"AI cho Phát triển kinh tế – xã hội"*.

| Việc | Vì sao |
|---|---|
| Dựng sẵn **bộ đồ nghề hackathon**: khung pipeline cho dữ liệu bảng, văn bản tiếng Việt, chuỗi thời gian | 2 ngày không đủ để vừa nghĩ vừa dựng khung |
| Mẫu **báo cáo kỹ thuật** có sẵn mục AI evaluation metrics + baseline/ablation | Thể lệ Vòng Khu vực liệt kê đích danh hai mục này |
| Mẫu repo có CI, README, cấu trúc thư mục | Phải nộp repo có commit history thật |
| **Tập chạy thử 1 buổi**: lấy một bộ dữ liệu mở bất kỳ, chạy full quy trình 8 tiếng | Biết mình chậm ở đâu trước khi thi |
| Quy trình chia vai 3 người trong 48 giờ + checklist nộp bài | Đội nào cũng dùng LLM; khác biệt nằm ở quy trình |
| **Gọi BTC hỏi danh mục chủ đề và định dạng dữ liệu** — 0988.086.273 | Rẻ nhất, thông tin đắt nhất |

> **Lợi thế chuyển giao được:** hackathon chấm theo cùng tinh thần rubric — baseline/ablation,
> chỉ số đánh giá, kiểm soát đầu ra, đạo đức dữ liệu. Đó đúng là những thứ LiveLift đã làm
> thành nếp. Đội không cần giỏi hơn về mô hình, chỉ cần **có kỷ luật đánh giá** hơn.

---

## Việc chỉ con người làm được (máy không thay được)

1. Bật repo Public.
2. Xin giấy xác nhận sinh viên.
3. Liên hệ nhà bán đối tác để chạy phiên live thật + phỏng vấn.
4. Gọi BTC xác minh danh mục chủ đề, định dạng dữ liệu hackathon, và số hiệu Kế hoạch.
5. Quay và dựng 2 video.
6. Đọc lại Prompt Log bằng mắt trước khi công bố.
7. Mở quyền Drive và tự kiểm bằng cửa sổ ẩn danh.
8. Ký tên và nộp.
