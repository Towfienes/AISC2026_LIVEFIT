# MDE đơn hàng theo số phiên × cỡ khán giả × q2

*Sinh lại bằng đúng một lệnh:* `python analysis/power/bang_mde_don_hang.py`

> **KỊCH BẢN — KHÔNG PHẢI SỐ ĐO.** Không dòng nào trong bảng này là kết quả
> quan sát của LiveLift. Ba đầu vào là prior/giả định, liệt kê ngay dưới đây.

## Nguồn prior và điều KHÔNG được dùng

- **Phễu click→đơn**: pv→giỏ **9.33%** × giỏ→mua **24.33%** ≈ **2.27%** — Taobao UserBehavior, Alibaba Tianchi bộ #649 (100 triệu tương tác, 11–12/2017). Khác nền tảng, khác năm, khác quốc gia: dùng làm prior, không làm số công bố.
- **Quét q2 (giỏ→mua)**: 0.15, 0.25, 0.35, 0.50 — prior 0.2433 nằm giữa hai mốc 0.15 và 0.25. q1 (pv→giỏ) giữ nguyên.
- **Nhánh đối tác**: nhân **khán giả** ×**4.9** (arXiv:2106.03415). Chỉ nhân khán giả — nguồn đó không nói gì về phễu hay tỷ lệ nhấp nên hai đại lượng này giữ nguyên.
- **Tỷ lệ nhấp**: bảng chính dùng **0.30** click hợp lệ / 1000 giây·người xem — một GIẢ ĐỊNH. Dự án chưa có số đo; xem bảng độ nhạy bên dưới.

**CẤM map KuaiLive vào phễu này.** 'Click' của KuaiLive là *vào phòng live*, không phải nhấp sản phẩm ghim — hai hành vi khác nhau về ngữ nghĩa. `docs/benchmarks/kuailive-calibration.md` đã nêu đúng giới hạn đó cho `base_click_prob_per_min`; ràng buộc ở đây mạnh hơn, vì một tỷ lệ chuyển đổi sai ngữ nghĩa sẽ đi thẳng vào con số đơn hàng.

## Cách tính (dùng lại đúng machinery MDE hiện có)

- Bố cục phiên: **90 phút**, khối **5 phút**, khối biên nhân đôi → **16 khối đo/phiên**; burn-in **60s** cắt khỏi cửa sổ kết quả của từng khối (đúng quy tắc `core.features.block_frame`).
- Đơn kỳ vọng mỗi khối: `λ_k = tỷ_lệ_nhấp/1000 × khán_giả × cửa_sổ_k × q1 × q2`.
- Đơn là biến ĐẾM HIẾM nên phương sai bị nhiễu đếm chi phối: CV nạp vào `mde_relative` là **CV Poisson** `√(trung bình_k 1/λ_k)` — cùng đại lượng mà `poisson_floor()` đo trên dữ liệu thật.
- MDE đã chia cho tuân thủ 0.95 và nhân biên độ kiểm định ngẫu nhiên hóa đo được ×1.2 (xem docstring `livelift.analysis.power`).

> **Đây là SÀN.** Con số MDE dưới đây là cận DƯỚI: nó giả định biến kết quả không có phương sai nào ngoài nhiễu đếm. Phiên thật có sốc cấp phiên, biến động khán giả, thay đổi sản phẩm — MDE thật chỉ có thể LỚN HƠN.

## Bảng chính — tỷ lệ nhấp 0.30/1000 giây·người xem

Cột *Khán giả* ghi `danh nghĩa (hiệu dụng sau nhân đối tác)`.

| Nhánh | Phiên | Khán giả | q2 | Đơn/khối | Đơn/phiên | CV Poisson | MDE tương đối | MDE tuyệt đối (đơn/phiên) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| không đối tác | 18 | 15 (15) | 0.15 | 0.017 | 0.28 | 7.85 | 327% | 0.92 |
| không đối tác | 18 | 15 (15) | 0.25 | 0.029 | 0.47 | 6.08 | 253% | 1.18 |
| không đối tác | 18 | 15 (15) | 0.35 | 0.041 | 0.65 | 5.14 | 214% | 1.40 |
| không đối tác | 18 | 15 (15) | 0.50 | 0.058 | 0.93 | 4.30 | 179% | 1.67 |
| có đối tác (×4.9) | 18 | 15 (74) | 0.15 | 0.086 | 1.37 | 3.54 | 148% | 2.03 |
| có đối tác (×4.9) | 18 | 15 (74) | 0.25 | 0.143 | 2.28 | 2.75 | 115% | 2.61 |
| có đối tác (×4.9) | 18 | 15 (74) | 0.35 | 0.200 | 3.20 | 2.32 | 97% | 3.09 |
| có đối tác (×4.9) | 18 | 15 (74) | 0.50 | 0.285 | 4.57 | 1.94 | 81% | 3.70 |
| không đối tác | 18 | 50 (50) | 0.15 | 0.058 | 0.93 | 4.30 | 179% | 1.67 |
| không đối tác | 18 | 50 (50) | 0.25 | 0.097 | 1.55 | 3.33 | 139% | 2.16 |
| không đối tác | 18 | 50 (50) | 0.35 | 0.136 | 2.17 | 2.81 | 117% | 2.55 |
| không đối tác | 18 | 50 (50) | 0.50 | 0.194 | 3.11 | 2.35 | 98% | 3.05 |
| có đối tác (×4.9) | 18 | 50 (245) | 0.15 | 0.285 | 4.57 | 1.94 | 81% | 3.70 |
| có đối tác (×4.9) | 18 | 50 (245) | 0.25 | 0.476 | 7.61 | 1.50 | 63% | 4.77 |
| có đối tác (×4.9) | 18 | 50 (245) | 0.35 | 0.666 | 10.66 | 1.27 | 53% | 5.65 |
| có đối tác (×4.9) | 18 | 50 (245) | 0.50 | 0.951 | 15.22 | 1.06 | 44% | 6.75 |
| không đối tác | 18 | 150 (150) | 0.15 | 0.175 | 2.80 | 2.48 | 103% | 2.89 |
| không đối tác | 18 | 150 (150) | 0.25 | 0.291 | 4.66 | 1.92 | 80% | 3.74 |
| không đối tác | 18 | 150 (150) | 0.35 | 0.408 | 6.52 | 1.62 | 68% | 4.42 |
| không đối tác | 18 | 150 (150) | 0.50 | 0.583 | 9.32 | 1.36 | 57% | 5.28 |
| có đối tác (×4.9) | 18 | 150 (735) | 0.15 | 0.856 | 13.70 | 1.12 | 47% | 6.41 |
| có đối tác (×4.9) | 18 | 150 (735) | 0.25 | 1.427 | 22.84 | 0.87 | 36% | 8.27 |
| có đối tác (×4.9) | 18 | 150 (735) | 0.35 | 1.998 | 31.97 | 0.73 | 31% | 9.78 |
| có đối tác (×4.9) | 18 | 150 (735) | 0.50 | 2.854 | 45.67 | 0.61 | 26% | 11.69 |
| không đối tác | 18 | 500 (500) | 0.15 | 0.583 | 9.32 | 1.36 | 57% | 5.28 |
| không đối tác | 18 | 500 (500) | 0.25 | 0.971 | 15.53 | 1.05 | 44% | 6.82 |
| không đối tác | 18 | 500 (500) | 0.35 | 1.359 | 21.75 | 0.89 | 37% | 8.07 |
| không đối tác | 18 | 500 (500) | 0.50 | 1.942 | 31.07 | 0.74 | 31% | 9.65 |
| có đối tác (×4.9) | 18 | 500 (2450) | 0.15 | 2.854 | 45.67 | 0.61 | 26% | 11.69 |
| có đối tác (×4.9) | 18 | 500 (2450) | 0.25 | 4.757 | 76.12 | 0.48 | 20% | 15.10 |
| có đối tác (×4.9) | 18 | 500 (2450) | 0.35 | 6.660 | 106.57 | 0.40 | 17% | 17.86 |
| có đối tác (×4.9) | 18 | 500 (2450) | 0.50 | 9.515 | 152.24 | 0.34 | 14% | 21.35 |
| không đối tác | 28 | 15 (15) | 0.15 | 0.017 | 0.28 | 7.85 | 262% | 0.73 |
| không đối tác | 28 | 15 (15) | 0.25 | 0.029 | 0.47 | 6.08 | 203% | 0.95 |
| không đối tác | 28 | 15 (15) | 0.35 | 0.041 | 0.65 | 5.14 | 172% | 1.12 |
| không đối tác | 28 | 15 (15) | 0.50 | 0.058 | 0.93 | 4.30 | 144% | 1.34 |
| có đối tác (×4.9) | 28 | 15 (74) | 0.15 | 0.086 | 1.37 | 3.54 | 119% | 1.62 |
| có đối tác (×4.9) | 28 | 15 (74) | 0.25 | 0.143 | 2.28 | 2.75 | 92% | 2.10 |
| có đối tác (×4.9) | 28 | 15 (74) | 0.35 | 0.200 | 3.20 | 2.32 | 78% | 2.48 |
| có đối tác (×4.9) | 28 | 15 (74) | 0.50 | 0.285 | 4.57 | 1.94 | 65% | 2.97 |
| không đối tác | 28 | 50 (50) | 0.15 | 0.058 | 0.93 | 4.30 | 144% | 1.34 |
| không đối tác | 28 | 50 (50) | 0.25 | 0.097 | 1.55 | 3.33 | 111% | 1.73 |
| không đối tác | 28 | 50 (50) | 0.35 | 0.136 | 2.17 | 2.81 | 94% | 2.05 |
| không đối tác | 28 | 50 (50) | 0.50 | 0.194 | 3.11 | 2.35 | 79% | 2.45 |
| có đối tác (×4.9) | 28 | 50 (245) | 0.15 | 0.285 | 4.57 | 1.94 | 65% | 2.97 |
| có đối tác (×4.9) | 28 | 50 (245) | 0.25 | 0.476 | 7.61 | 1.50 | 50% | 3.83 |
| có đối tác (×4.9) | 28 | 50 (245) | 0.35 | 0.666 | 10.66 | 1.27 | 43% | 4.53 |
| có đối tác (×4.9) | 28 | 50 (245) | 0.50 | 0.951 | 15.22 | 1.06 | 36% | 5.41 |
| không đối tác | 28 | 150 (150) | 0.15 | 0.175 | 2.80 | 2.48 | 83% | 2.32 |
| không đối tác | 28 | 150 (150) | 0.25 | 0.291 | 4.66 | 1.92 | 64% | 3.00 |
| không đối tác | 28 | 150 (150) | 0.35 | 0.408 | 6.52 | 1.62 | 54% | 3.54 |
| không đối tác | 28 | 150 (150) | 0.50 | 0.583 | 9.32 | 1.36 | 45% | 4.24 |
| có đối tác (×4.9) | 28 | 150 (735) | 0.15 | 0.856 | 13.70 | 1.12 | 37% | 5.14 |
| có đối tác (×4.9) | 28 | 150 (735) | 0.25 | 1.427 | 22.84 | 0.87 | 29% | 6.63 |
| có đối tác (×4.9) | 28 | 150 (735) | 0.35 | 1.998 | 31.97 | 0.73 | 25% | 7.84 |
| có đối tác (×4.9) | 28 | 150 (735) | 0.50 | 2.854 | 45.67 | 0.61 | 21% | 9.38 |
| không đối tác | 28 | 500 (500) | 0.15 | 0.583 | 9.32 | 1.36 | 45% | 4.24 |
| không đối tác | 28 | 500 (500) | 0.25 | 0.971 | 15.53 | 1.05 | 35% | 5.47 |
| không đối tác | 28 | 500 (500) | 0.35 | 1.359 | 21.75 | 0.89 | 30% | 6.47 |
| không đối tác | 28 | 500 (500) | 0.50 | 1.942 | 31.07 | 0.74 | 25% | 7.73 |
| có đối tác (×4.9) | 28 | 500 (2450) | 0.15 | 2.854 | 45.67 | 0.61 | 21% | 9.38 |
| có đối tác (×4.9) | 28 | 500 (2450) | 0.25 | 4.757 | 76.12 | 0.48 | 16% | 12.10 |
| có đối tác (×4.9) | 28 | 500 (2450) | 0.35 | 6.660 | 106.57 | 0.40 | 13% | 14.32 |
| có đối tác (×4.9) | 28 | 500 (2450) | 0.50 | 9.515 | 152.24 | 0.34 | 11% | 17.12 |

## Độ nhạy theo tỷ lệ nhấp (ô neo: 18 phiên, 15 người xem, q2 = 0.25)

| Tỷ lệ nhấp /1000 gs·nx | Đơn/phiên | CV Poisson | MDE tương đối |
|---:|---:|---:|---:|
| 0.20 | 0.31 | 7.44 | 310% |
| 0.30 | 0.47 | 6.08 | 253% |
| 0.40 | 0.62 | 5.26 | 220% |
| 1.00 | 1.55 | 3.33 | 139% |

## Mốc tỉnh táo (assert trong `tests/test_power.py`)

- 15 người xem × 90 phút, tỷ lệ nhấp 0.30/1000 giây·người xem, prior phễu đầy đủ → **0.45 đơn/phiên** trong cửa sổ phân tích (4440 giây/phiên sau burn-in). Khớp bậc với mốc kỳ vọng 0.3–0.6 đơn/phiên của agenda.
- Cùng ô đó nhưng lấy tỷ lệ nhấp suy ra từ machinery mô phỏng hiện có (`SimParams.base_click_prob_per_min = 0.06`/người xem·phút ⇒ 1.00/1000 giây·người xem) → **1.51 đơn/phiên**, tức cao hơn mốc agenda khoảng 2.5–5.0 lần. Cùng bậc độ lớn, nhưng KHÔNG trùng: ghi ra ở đây thay vì làm tròn cho khớp. Tham số mô phỏng đó vốn được đánh dấu là GIẢ ĐỊNH và chỉ phiên thăm dò mới chốt được.

## Kết luận đọc được ngay

- Ở quy mô một Page tự vận hành (≤ 50 người xem đồng thời), MDE tốt nhất trong bảng vẫn là **79%** — nghĩa là **không có ô nào biến đơn hàng thành biến kết quả khẳng định được**. Đơn hàng ở lại đúng chỗ của nó: thứ cấp/mô tả (PREREGISTRATION §4.2), báo cáo kèm bất định, không dùng để kết luận.
- Ô đầu tiên đạt MDE ≤ 30% cần khoảng **500 người xem đồng thời hiệu dụng** — chỉ với tay tới được qua nhánh đối tác.
- Đòn bẩy duy nhất có thật là **khán giả**: MDE tỉ lệ với CV Poisson ∝ `1/√khán_giả`. Nhân ×4.9 khán giả của nhánh đối tác chia MDE cho ≈ **2.21** — đúng bậc, không hơn.
- Thêm phiên (18 → 28) chỉ chia MDE cho √(28/18) ≈ 1.25. Không đủ để cứu endpoint này.
