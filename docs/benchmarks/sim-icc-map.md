# Ánh xạ knob không đồng nhất → ICC cấp phiên (SỐ ĐO)

Lệnh tái lập (sinh chính file này):

```
python analysis/calibration/bang_icc_mo_phong.py
```

400 phiên × 90 phút, khối 5 phút, burn-in 60 giây, `treatment_effect=0`, `master_seed=909`. `y` là biến kết quả chính (lượt nhấp hợp lệ / 1.000 giây·người xem) trên các khối ĐO ĐƯỢC sau burn-in. ICC = ANOVA một chiều ICC(1) (Shrout & Fleiss 1979), **không chặn ở 0**; ± là sai số chuẩn bootstrap theo CỤM PHIÊN (400 lần lặp, cùng seed).

Hai bảng dùng CÙNG chuỗi seed phiên (cùng lượt vào, cùng thời gian ở lại, cùng nhiễu AR(1)), nên khác biệt giữa các hàng là do knob chứ không do may rủi của seed. Hàng đầu mỗi bảng (knob = 0) là cùng một thế giới, và đúng ra phải cho cùng một con số — đó là phép tự kiểm của chính file này.

## 1. `session_click_sigma` — knob ICC chính thức

| `session_click_sigma` | ICC(y) ± SE bootstrap cụm | trung bình y | phương sai TRONG-phiên | phiên | khối |
|---:|---|---:|---:|---:|---:|
| 0.000 | +0.008 ± 0.005 | 1.002 | 0.0853 | 400 | 6400 |
| 0.030 | +0.018 ± 0.006 | 1.001 | 0.0851 | 400 | 6400 |
| 0.060 | +0.048 ± 0.008 | 1.000 | 0.0855 | 400 | 6400 |
| 0.095 | +0.101 ± 0.011 | 1.000 | 0.0860 | 400 | 6400 |
| 0.100 | +0.110 ± 0.012 | 1.001 | 0.0863 | 400 | 6400 |
| 0.200 | +0.333 ± 0.021 | 1.000 | 0.0860 | 400 | 6400 |
| 0.300 | +0.535 ± 0.023 | 0.998 | 0.0848 | 400 | 6400 |

## 2. `click_frailty_cv` — knob PHÂN TÁN, có tác dụng phụ ICC

Frailty theo người xem `u_i ~ Gamma(1/cv², cv²)` được kỳ vọng KHÔNG đụng tới ICC. Đo ra thì có: khán giả hữu hạn (~500 lượt vào/phiên) nên trung bình frailty của phiên tự nó là một nhân tử cấp phiên với CV ≈ cv/√N. Bảng này là số đo của tác dụng phụ đó — công bố chứ không giấu.

| `click_frailty_cv` | ICC(y) ± SE bootstrap cụm | trung bình y | phương sai TRONG-phiên | phiên | khối |
|---:|---|---:|---:|---:|---:|
| 0.000 | +0.008 ± 0.005 | 1.002 | 0.0853 | 400 | 6400 |
| 0.500 | +0.022 ± 0.006 | 0.998 | 0.0883 | 400 | 6400 |
| 1.000 | +0.038 ± 0.007 | 1.003 | 0.0992 | 400 | 6400 |
| 1.500 | +0.059 ± 0.008 | 1.002 | 0.1229 | 400 | 6400 |
| 2.000 | +0.083 ± 0.010 | 1.007 | 0.1536 | 400 | 6400 |

**Đọc bảng.**

- Hàng knob = 0 **không** cho ICC = 0. ICC(1) theo ANOVA lệch LÊN khi phương sai trong-cụm không đều, mà `session_shock_sd` (cú sốc lượt vào) làm đúng thế: phiên đông đo tỷ lệ chính xác hơn phiên vắng. Hàng này là NỀN của thước đo — đọc "σ=0" là "ICC ≈ 0,01", không phải "không phân cụm".
- Cột **trung bình y** phải giữ nguyên trên mọi hàng của CẢ HAI bảng: hai knob đều là nhân tử mean-1 (`exp(N(0,σ²) − σ²/2)` và `Gamma` kỳ vọng 1). Một hàng lệch mức là dấu hiệu số hạng hiệu chỉnh trung bình bị mất.
- Cột **phương sai TRONG-phiên** là thứ PHÂN BIỆT hai knob: bảng 1 giữ nguyên nó (knob phiên dịch cả phiên), bảng 2 làm nó tăng (frailty làm phân tán chính các khối). Muốn quay ICC thì dùng bảng 1; bảng 2 là khi câu hỏi là quá phân tán.
- Ba mốc dùng cho cổng hiệu chuẩn: σ=0,03 → ICC≈0,02; **σ=0,06 → ICC≈0,05** (thế giới hai cổng `-m slow` chạy); σ=0,095 → ICC≈0,10.
