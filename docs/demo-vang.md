# Bộ phiên DEMO VÀNG

Sáu phiên mô phỏng `is_demo=true`, seed CỐ ĐỊNH (20261, 20262, 20263, 20271, 20272, 20281),
phủ đủ **cả ba trạng thái** của màn kết quả — để demo và chụp ảnh từng trạng
thái mà không phải chờ dữ liệu thật, và để trạng thái NULL / CHƯA ĐỦ ĐIỀU KIỆN
được trình bày công phu ngang trạng thái DƯƠNG (yêu cầu phản biện khoa học).

Sinh lại (tất định — cùng seed ⇒ cùng ước lượng/KTC/trạng thái, chỉ session_id
đổi vì là UUID):

    .venv/Scripts/python scripts/seed_demo_vang.py --backend postgres --ghi-doc

Ba hàng rào đi kèm (gói DEMO-THẬT, PREREGISTRATION §8.2):

- mọi phiên dưới đây mang `is_demo=true` **từ lúc sinh**, bất biến về sau;
- chúng bị loại khỏi `/experiment/summary` mặc định (`env=real`) và mọi đầu ra
  khoa học thật (kể cả export lô gán nhãn NLP) — xem riêng từng phiên qua
  `/sessions/{id}/bao-cao`, luôn kèm cờ `is_demo` để UI vẽ nhãn DEMO;
- khóa §7 (`RESULTS_FREEZE_UNTIL`) KHÔNG áp cho phiên demo: hiệu ứng của chúng
  là tham số gõ vào simulator, không có gì để nhìn trộm — nhờ đó bộ demo dùng
  được ngay trong cửa sổ khóa chiến dịch.

## Phiên mẫu (lần seed gần nhất — kho `postgres`, 2026-09-12 16:22 UTC)

| Trạng thái | Phiên (title) | session_id | n khối | Ước lượng | KTC 95% | Ghi chú |
|---|---|---|---|---|---|---|
| DƯƠNG rõ (KTC loại 0) | Demo vàng · DƯƠNG rõ #1 | `160b0bd3-924b-445a-93b6-10938038cc35` | 16 | +1.224 | [+0.932, +1.498] |  |
| DƯƠNG rõ (KTC loại 0) | Demo vàng · DƯƠNG rõ #2 | `b828d45e-1f96-47fe-acbb-d40b875812b2` | 16 | +0.795 | [+0.539, +1.056] |  |
| DƯƠNG rõ (KTC loại 0) | Demo vàng · DƯƠNG rõ #3 | `032b7a12-c4dc-42cd-a74d-e8a37c88bb8a` | 16 | +1.059 | [+0.663, +1.442] |  |
| NULL (KTC chứa 0) | Demo vàng · NULL (KTC chứa 0) #1 | `0dd00539-c06c-411e-8931-2fc9e71b70e1` | 16 | -0.173 | [-0.490, +0.181] |  |
| NULL (KTC chứa 0) | Demo vàng · NULL (KTC chứa 0) #2 | `b634d8e8-c529-4fc6-a36e-e8697f79fafb` | 16 | +0.206 | [-0.031, +0.396] |  |
| CHƯA ĐỦ ĐIỀU KIỆN (estimable=false) | Demo vàng · CHƯA ĐỦ ĐIỀU KIỆN | `ecb330a2-5f7a-4d2f-b617-a73a845f3761` | 3 | — | — | Chưa đủ khối đo được để ước lượng (3 khối, cần ≥ 4) — tuyên bố thiếu, không trả số. |

Xem một trạng thái: mở `/sessions/<session_id>/bao-cao` (trường
`ket_qua_thi_nghiem`) hoặc trang kết quả của web với phiên tương ứng.
Bản gộp CHỈ-DEMO (có nhãn MÔ PHỎNG): `GET /experiment/summary?env=demo`.
