# Hiệu chỉnh mô phỏng theo KuaiLive (dữ liệu thật, 21 ngày Kuaishou)

*Sinh bởi `analysis/calibration/kuailive_calibration.py` — chạy lại được toàn bộ.*

- Phòng livestream **bán hàng (shop)**: **1,157,314** phòng
- Lượt vào phòng shop có thời gian xem: **445,575**
- Tổng thời gian xem: **15,179 giờ·người xem**
- Bình luận trong phòng shop: **14,470** · Thả tim: **12,769**

## Phân phối đo được

| Đại lượng | p25 | trung vị | trung bình | p75 | p90 |
|---|---|---|---|---|---|
| Thời lượng phiên shop (phút) | 85 | 134 | 166 | 202 | 290 |
| Thời gian ở lại mỗi lượt vào (phút) | 0.03 | 0.09 | 2.04 | 0.57 | 3.41 |
| — riêng người xem GẮN BÓ (ở lại > 1 phút, 19% số lượt) | 1.8 | 3.6 | 10.0 | 10.4 | 29.1 |

- Tốc độ bình luận: **0.016 / người xem·phút**
- Tốc độ thả tim: **0.014 / người xem·phút**

## Đối chiếu với tham số mô phỏng hiện tại

| Tham số SimParams | Hiện tại | KuaiLive đo được | Khuyến nghị |
|---|---|---|---|
| `mean_stay_min` | 6.0 | 9.95 (gắn bó: trung bình 9.95) | 10.0 |
| `comment_rate_per_viewer_min` | 0.25 | 0.016 | 0.02 |
| `like_rate_per_viewer_min` | 0.8 | 0.014 | 0.01 |

## Hệ quả cho thiết kế thí nghiệm

- **Phân phối ở lại cực lệch phải**: trung vị chỉ 5 giây (người dùng Kuaishou lướt phòng live như lướt feed), nhưng nhóm gắn bó (>1 phút, 19% số lượt) ở lại trung vị 3.6 phút. Với Facebook Live của nhóm — nơi người xem chủ động mở phiên — nhóm gắn bó là nhóm tham chiếu đúng.
- Trung vị ở lại của nhóm gắn bó là cận trên hợp lý cho hiệu ứng lưu; burn-in 60s hiện tại hợp lý. Quy trình tuần 3 vẫn PHẢI đo t_mix trên kênh của chính nhóm — khác nền tảng, khác hành vi.
- Phân phối ở lại lệch phải mạnh (đuôi dài) — người xem trung thành ở rất lâu; khớp mô hình hazard hình học của simulator.

## Những gì KHÔNG hiệu chỉnh được từ bộ này — nói thẳng

- **Tỷ lệ nhấp sản phẩm**: 'click' của KuaiLive là *vào phòng*, không phải nhấp sản phẩm ghim. Hai đại lượng khác nhau về ngữ nghĩa; tham số `base_click_prob_per_min` phải chờ số đo từ phiên thăm dò của chính nhóm.
- **Mức người xem tuyệt đối**: Kuaishou ≠ một Page Facebook Việt mới lập; chỉ dùng được HÌNH DẠNG phân phối, không dùng mức.
- **Mọi thứ về tác động can thiệp** — không có biến can thiệp trong dữ liệu quan sát.