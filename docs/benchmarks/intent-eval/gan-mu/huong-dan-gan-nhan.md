# Hướng dẫn gán nhãn ý định — bảng gán mù 25/09/2026

Bảng có **393 bình luận** livestream bán hàng thật, đã lọc thông tin cá nhân
(`[TÊN]`, `[SĐT]`, `[ĐỊA CHỈ]`, `[MXH]`, `[MÃ ĐƠN]`, `[STK]`, `[EMAIL]` là chỗ đã che).

## Quy tắc bắt buộc

1. **Gán độc lập.** Không trao đổi với người gán còn lại cho tới khi cả hai đã nộp.
2. **Không dùng AI** (ChatGPT, Claude, Gemini…) và không tra nhãn cũ. Mục đích của
   bảng này là đo xem nhãn do AI gán trước đây có khớp với người hay không.
3. Mỗi dòng **đúng một nhãn**. Không chắc vẫn phải chọn một nhãn, rồi ghi lý do vào
   cột `ghi_chu`.
4. Điền cột `nhan` bằng **mã nhãn** (ví dụ `hoi_gia`) hoặc **số thứ tự 1–11** trong
   bảng dưới. Không sửa cột `ma_dong` và `binh_luan`, không xoá hay sắp xếp lại dòng.
5. Lưu lại dạng **CSV UTF-8** (Excel: *File → Save As → CSV UTF-8 (Comma delimited)*).
   Nếu Excel dồn mọi thứ vào một cột: *Data → From Text/CSV*, chọn mã hoá UTF-8,
   dấu phân cách là dấu phẩy.
6. **Dữ liệu người dùng:** không đăng lên mạng, không gửi qua kênh công khai; xoá bản
   trên máy cá nhân sau khi nộp.
7. Bình luận bắt đầu bằng `=`, `+`, `-`, `@` có thêm một dấu cách ở đầu để Excel không
   hiểu nhầm là công thức. Bình luận chỉ gồm chữ số có thể bị Excel hiển thị khác (mất
   số 0 ở đầu, dạng `7,8E+07`); cần xem nguyên văn thì mở tệp bằng Notepad.

## 11 nhãn

| Số | Mã nhãn | Tên | Định nghĩa |
|---:|---|---|---|
| 1 | `hoi_gia` | Hỏi giá | KHÁCH hỏi giá (giá bao nhiêu, nhiêu tiền, bn, báo giá đi) — người hỏi là khách, KHÔNG phải shop đang đọc bảng giá (xem bao_gia_shop) |
| 2 | `hoi_size` | Hỏi size | hỏi size / cân nặng / chiều cao / form dáng để CHỌN CỠ mặc — không phải mọi câu chứa chữ 'vừa' hay 'bao nhiêu' |
| 3 | `che_dat` | Chê đắt | chê GIÁ đắt / mắc / cao / trả giá xuống (phàn nàn về giá, KHÔNG phải hỏi giá, KHÔNG phải khen rẻ, KHÔNG phải 'cao' nghĩa chiều cao) |
| 4 | `chot_don` | Chốt đơn | KHÁCH chốt đơn, đặt mua, order (hành động mua của chính người bình luận: 'chốt', 'lấy 1', 'đặt hàng') — không phải shop hô hào 'cả nhà chốt đơn nha' |
| 5 | `van_chuyen` | Vận chuyển | hỏi giao hàng / phí ship / COD / thời gian nhận / gửi đi tỉnh, nước ngoài, hoặc hối đơn đã đặt mà chưa nhận |
| 6 | `chao_hoi` | Chào hỏi | chào hỏi, điểm danh, tạm biệt, chào người dẫn/khán giả khác ('chào cả nhà', 'em chào a chan', 'hello') — không kèm ý định mua |
| 7 | `cam_on_khen` | Cảm ơn / khen | cảm ơn, chúc mừng, chúc sức khỏe, khen, cổ vũ, đồng tình, thả tim/cười — cảm xúc tích cực chung, không kèm ý định mua |
| 8 | `hoi_sanpham` | Hỏi sản phẩm | hỏi VỀ SẢN PHẨM ngoài giá và size: còn hàng không, có bán món X không, hạn dùng, thành phần, xem hàng ở đâu, mua ở kênh nào |
| 9 | `hoi_daily` | Hỏi mở đại lý | hỏi mở đại lý / chi nhánh / cộng tác viên / hợp tác phân phối — khách muốn BÁN CÙNG, không phải mua lẻ |
| 10 | `bao_gia_shop` | Shop tự báo giá | SHOP/mod tự dán bảng giá, tên sản phẩm kèm giá, thông tin khuyến mãi (thường in hoa, lặp lại nhiều lần) — nguồn nhiễu, KHÔNG phải khách hỏi giá |
| 11 | `khac` | Khác | mọi bình luận không thuộc các lớp trên: bàn luận ngoài lề, drama cộng đồng, spam số/emoji, thông tin lịch/sự kiện |

## Quy ước cho ca khó

Quy tắc 1–5 tóm tắt từ mục *Quy ước gán nhãn* của
`docs/benchmarks/intent-classifier.md` (cũng là phần quy ước trong prompt của
`livelift.nlp.label_llm`); quy tắc 6 là quy tắc định trước của lô 2 — để người và AI
được so trên cùng một luật.

1. **Câu đa ý định** ("size M giá nhiêu"): chọn ý định hành động gần với chốt đơn nhất.
2. **Ai đang nói quyết định nhãn.** Shop dán bảng giá → `bao_gia_shop`; shop hô
   "cả nhà chốt đơn nha" → `khac`. Chỉ ý định của **khách** mới tính là ý định mua.
3. **Chào hỏi, khen không bao giờ là ý định mua.** Không gán `chot_don` cho lời chào.
4. **`che_dat` chỉ nói về GIÁ.** "bán đắt" (bán chạy) hay "cao" (chiều cao) không
   phải chê giá; khen rẻ là `cam_on_khen`.
5. Mất dấu, teencode, viết tắt, emoji: vẫn gán như thường.
6. **Ca mơ hồ giữa một lớp hành động và một lớp khác: chọn lớp hành động** (quy tắc
   định trước của lô này). Lớp hành động: `hoi_gia`, `hoi_size`, `che_dat`,
   `chot_don`, `van_chuyen`.

## Nộp bài

Gửi lại tệp CSV đã điền cho trưởng nhóm. Tính độ đồng thuận:

```
.venv/Scripts/python scripts/tinh_kappa.py --bang1 <bảng người 1> \
    --bang2 <bảng người 2> --khoa <thư mục gán mù>/khoa/khoa-gan-mu.csv
```

*Sinh bởi `scripts/gan_mu/tao_bang_gan_mu.py`.*
