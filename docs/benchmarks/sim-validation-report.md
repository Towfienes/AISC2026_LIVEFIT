# Thẩm định mô phỏng — lưới SBC (BỘ KHUNG / SKELETON)

Lệnh tái lập (sinh chính file này):

```
python -m livelift.sim.cli --grid --grid-reps 100 --sessions 3 --minutes 60 --effect 0.3 --draws 200 --seed 2026
```

**TRẠNG THÁI: SKELETON.** Lưới ở đây chỉ có 2×2 = 4 ô × 100 lần lặp — đủ để chứng minh đường ống chạy và ô ĐỎ là *có thể chạm tới* (test nghịch đảo trong `tests/test_sim_report.py`), CHƯA phải bằng chứng hiệu chuẩn đầy đủ. Lưới đầy đủ (~20 ô: hiệu ứng lưu × ICC × tác động, 1000 lần lặp/ô) là việc của tuần khóa tiền đăng ký; con số của nó KHÔNG được suy đoán từ đây.

Ba tiêu chí mỗi ô (HARNESS.md §2):

1. **Đồng đều p-value** — chỉ kiểm ở ô A/A, nơi giả thuyết không sắc thực sự đúng. `D` là độ lệch ECDF lớn nhất (cũng chính là thống kê KS); nó được đối chiếu hai lần: với p-value chính xác của KS, và với băng đồng thời 95% kiểu DKW/Massart — băng này *bảo thủ* ở n nhỏ nên KS mới là công cụ sắc.
2. **Độ phủ** khoảng tin cậy Fisher: khoảng Wilson quanh tỷ lệ phủ quan sát phải chứa mức danh nghĩa 95%. Khoảng lấy ở mức 99% (không phải 95%) theo đúng quy ước của các cổng hiệu chuẩn sẵn có — phán quyết ở mức 5% sẽ làm một ô ĐỎ oan cứ mỗi 20 ô dù đường ống hoàn hảo.
3. **Lệch** so với chân trị CRN: < 10% tác động thật. Ở ô A/A tác động thật ≈ 0 nên không có mẫu số — báo lệch TUYỆT ĐỐI kèm sai số Monte-Carlo thay vì bịa một tỷ lệ phần trăm chia cho ~0.

Ghi chú về cột tác động: `0.3` là mức đang dùng cho cổng hiệu chuẩn hiện có, **không** phải MDE đã đo. Bảng MDE trong PREREGISTRATION.md §6 còn là ô trống chờ số hiệu chỉnh tuần 3–4; khi có, ô này chạy lại ở đúng MDE.

Trục ICC là knob `SimParams.session_click_sigma` (gói P1-K2); mục cuối file nói σ nào cho ICC nào, bảng đầy đủ (SỐ ĐO, sinh lại được) ở `docs/benchmarks/sim-icc-map.md`. Hai cổng Monte-Carlo `-m slow` chạy đúng thế giới ICC≈0,05 này với NGUYÊN ngưỡng của bản không phân cụm: `test_aa_false_positive_rate_near_alpha_under_session_icc` và `test_effect_recovery_bias_and_coverage_under_session_icc`.

| Ô | reps | Đồng đều p (KS D / p) | D vs băng DKW | Độ phủ (Wilson 99%) | Lệch (tương đối ± MC) | Tỷ lệ bác bỏ | Kết luận |
|---|---:|---|---|---|---|---:|:--:|
| ICC≈0.01 (σ=0) × A/A (tác động 0) | 100 | D=0.083, p=0.4753 | 0.083 / 0.136 | 97.0% [88.9%, 99.2%] | +0.0039 ± 0.0107 (tuyệt đối) | 4.0% | **XANH** |
| ICC≈0.01 (σ=0) × tác động 0.3 | 100 | không áp dụng (có tác động) | — | 96.0% [87.5%, 98.8%] | +0.7% ± 3.7% | 47.0% | **XANH** |
| ICC≈0.05 (σ=0.06) × A/A (tác động 0) | 100 | D=0.079, p=0.5391 | 0.079 / 0.136 | 97.0% [88.9%, 99.2%] | +0.0024 ± 0.0108 (tuyệt đối) | 4.0% | **XANH** |
| ICC≈0.05 (σ=0.06) × tác động 0.3 | 100 | không áp dụng (có tác động) | — | 95.0% [86.1%, 98.3%] | +1.5% ± 3.8% | 48.0% | **XANH** |

Tất cả 4 ô XANH theo tiêu chí đã nêu ở trên.

### Ánh xạ σ → ICC (đo được, không giả định)

Bảng đầy đủ (σ ∈ {0; 0,03; 0,06; 0,095; 0,1; 0,2; 0,3}) nằm ở `docs/benchmarks/sim-icc-map.md` và sinh lại được bằng một lệnh:

```
python analysis/calibration/bang_icc_mo_phong.py
```

400 phiên × 90 phút, khối 5 phút, burn-in 60 giây, tác động 0; ICC = ANOVA một chiều của `y` theo cụm phiên (`livelift.sim.report.session_icc`); ± là sai số chuẩn bootstrap theo CỤM PHIÊN. Không chép lại bảng vào đây: một bảng SỐ ĐO chép tay sang file thứ hai là chỗ để hai con số lặng lẽ lệch nhau.

Hai mốc mà lưới trên thực sự chạy: **σ=0 → ICC +0,008 ± 0,005** và **σ=0,06 → ICC +0,048 ± 0,008**.

σ=0 cho ICC≈0,01 **chứ không phải 0**: ICC(1) theo ANOVA lệch lên khi phương sai trong-cụm không đều, mà `session_shock_sd` (cú sốc lượt vào) làm đúng thế. Đó là số đo, không phải giả định.
