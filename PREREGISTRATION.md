# LiveLift — Tiền đăng ký phân tích

> **TRẠNG THÁI: BẢN MẪU — CHƯA KHÓA.**
> Bản này được điền đầy đủ và **khóa bằng commit trước phiên khẳng định đầu tiên (tuần 6,
> dự kiến 29/09–05/10/2026)**. Sau commit khóa, mọi thay đổi ước lượng viên/thiết kế bị cấm;
> phân tích ngoài danh sách mục 8 phải dán nhãn "khám phá hậu nghiệm" (HARNESS §4).
> Các ô `<...>` là chỗ điền; các phần không có `<...>` đã được chốt từ nghiên cứu 24/08/2026.

Commit khóa: `<hash — tự động khi khóa>` · Ngày khóa: `<YYYY-MM-DD, trước phiên khẳng định đầu tiên>`
Người chịu trách nhiệm: TN (trưởng phân tích) · Người duyệt: `<thành viên thứ hai>`

---

## 1. Câu hỏi nghiên cứu chính

Chiến lược ghim sản phẩm do LiveLift đề xuất (nhánh BẬT) có làm thay đổi **tỷ lệ nhấp
sản phẩm theo khối** so với chiến lược mặc định của đội vận hành (nhánh TẮT) hay không?

Ước lượng chính là **ITT cấp khối** trong chuỗi phiên Live Lab chế độ tự động
(tuân thủ kỳ vọng ≈95%); LATE báo cáo bổ sung (mục 5d).

## 2. Thiết kế ngẫu nhiên hóa

Thiết kế switchback trong-phiên hai tầng; tầng ngoài được tiền đăng ký ở đây.
Cài đặt tham chiếu: `livelift.core.assigner.generate_schedule` (chính hàm chạy production).

- **Đơn vị ngẫu nhiên hóa:** khối thời gian trong phiên, dài `<X>` phút (quy trình chọn X
  ở mục 3 — X **không** được chọn trước trong bản mẫu này).
- **Gán:** i.i.d. **Bernoulli(0,5)** mỗi khối (BẬT/TẮT), propensity 0,5 ghi vào
  `experiment_block.propensity`.
- **Rerandomization:** chuỗi gán được vẽ lại đến khi **mỗi 1/3 phiên (đầu/giữa/cuối) có
  ≥ 2 khối mỗi nhánh** (Ni, Kalfountzou & Bojinov 2025); số lần vẽ lại (`n_redraws`)
  lưu cùng lịch.
- **Khối biên nhân đôi:** khối đầu và khối cuối phiên dài **2×X** phút (quy tắc 2m,
  Bojinov, Simchi-Levi & Zhao 2023) — khối biên nhiễm carryover nhiều hơn nên kéo dài
  chứ không vứt bỏ.
- **Jitter ranh giới:** ±30 giây, ngẫu nhiên theo seed của lịch, để ranh giới khối không
  đồng bộ với kịch bản show (Xiong, Chin & Taylor 2024).
- **KHÔNG có washout thiết kế** (`washout_min = 0`): ghi log toàn bộ thời gian; carryover
  xử lý bằng **burn-in ở tầng phân tích** (Hu & Wager 2022) — xem mục 4. Quyết định này
  giải mâu thuẫn L1 (bảng lực vs. quy tắc washout) trong báo cáo phản biện.
- **Sinh lịch TRƯỚC phiên:** lịch + seed + tham số thiết kế được sinh và lưu vào
  `experiment_block` / `live_session.design` tại mốc T−1h, trước phát sóng
  (runbook `ops/runbooks/quy-trinh-phien.md`). Phiên không có lịch đã lưu không được phát.
- **Xác suất gán dùng cho suy diễn** là xác suất *có điều kiện trên tập chuỗi qua được
  rerandomization* — mọi redraw trong kiểm định ngẫu nhiên hóa dùng đúng thủ tục sinh
  lịch production (cùng ràng buộc), không dùng Bernoulli không ràng buộc.

## 3. Độ dài khối và burn-in — quy trình chốt (tiền đăng ký QUY TRÌNH, không chọn trước kết quả)

Nghiên cứu chưa thống nhất giữa khối 5 phút (carryover ngắn + tự tương quan dương →
switch nhiều; Wen et al. 2024) và khối dài hơn (nếu carryover dài; dwell 5–7 phút).
Bất đồng này được giải **bằng dữ liệu hiệu chỉnh tuần 3–4**, theo thủ tục cố định sau:

1. Trên 5 phiên thăm dò (tuần 3–4, **không đếm vào mẫu khẳng định**), đo:
   (a) **t_mix**: impulse response của tỷ lệ nhấp sau khi bỏ ghim (phút về gần mức nền);
   (b) phân phối dwell của người xem (trung vị, p75);
   (c) tự tương quan dư của tỷ lệ nhấp theo khối sau khử FE-phiên;
   (d) CV trong-phiên của tỷ lệ nhấp theo khối; ICC **cấp phiên**.
2. Chạy power curve trên simulator đã hiệu chỉnh (`livelift.sim`) trên lưới
   độ dài khối {5, 10, 15} phút × carryover {đo được, 0, 2× đo được}.
3. **Quy tắc quyết định:** chọn X nhỏ nhất trong lưới sao cho, với t_mix đo được,
   bias mô phỏng của ước lượng viên chính (có burn-in b=1) < 10% hiệu ứng và MDE mô phỏng
   nhỏ nhất. Nếu t_mix > 3 phút, X=5 bị loại và lưới xét {10, 15}.
4. Kết quả (X, các số đo, power curve) ghi vào notebook `analysis/calibration/`,
   commit `<hash>`; giá trị chốt điền vào mục 2 khi khóa.

**Burn-in phân tích:** chính b = **1 phút** đầu mỗi khối bị loại khỏi ước lượng
(exposure và click tính từ giây 60); **sensitivity bắt buộc b ∈ {0, 2, 3} phút** báo cáo
kèm mọi kết quả chính. Nếu ước lượng đổi dấu hoặc mất ý nghĩa theo b, phải báo cáo trung
thực như một hạn chế. (Cài đặt: tham số `burn_in_s` của `livelift.core.features.block_frame`.)

## 4. Biến kết quả

### 4.1 Biến chính

**Tỷ lệ nhấp sản phẩm theo khối, chuẩn hóa exposure:**

```
y_b = 1000 × (số click hợp lệ trong khối b, sau burn-in) / (viewer-giây exposure của khối b, sau burn-in)
```

đơn vị: **click / 1.000 viewer-giây**.

- **Định nghĩa vận hành của một click** (mọi nền tảng): một request đến redirect tự host
  `/r/{code}` của shortlink UTM ghim trong bình luận/overlay, ghi ở bảng `click_event`
  với timestamp **server-side**, sau khử trùng lặp bằng `dedup_hash` (salt xoay theo
  phiên). Click quy về khối chứa timestamp của nó. Đây là định nghĩa duy nhất — không
  dùng số liệu click của nền tảng.
- **Viewer-giây exposure** = tích phân số người xem đồng thời trên phần khối sau burn-in
  (từ `session_tick` 30 giây).
- **Quy tắc tối thiểu:** khối có exposure < `E_min` giây·người xem bị loại khỏi phân tích.
  Giá trị đang cài đặt: `MIN_EXPOSURE_VIEWER_S = 60` (một người xem trong một phút) —
  `<chốt lại từ hiệu chỉnh tuần 3; phải khớp hằng số trong core/features.py>`
  viewer-giây bị loại (`excluded_reason='low_exposure'`), tiền đăng ký trước, áp dụng
  mù với nhánh gán.

### 4.2 Thứ cấp (khám phá, không hiệu chỉnh đa kiểm định)

Số đơn theo khối, tỷ lệ chuyển đổi click→đơn, GMV, biên đóng góp, tốc độ bình luận
có intent mua.

## 5. Ước lượng viên và suy diễn

Đơn vị phân tích = **khối**; cụm = **phiên** (~`<n>` phiên là cỡ mẫu ràng buộc, không phải
số khối — sốc cấp phiên chi phối). Không bao giờ phân tích cấp click.
Cài đặt tham chiếu: `livelift.analysis.estimators`.

**(a) PRIMARY — kiểm định ngẫu nhiên hóa với thống kê studentized + Fisher CI nghịch đảo.**
Vẽ lại phân bổ bằng **chính hàm gán production** (`generate_schedule`, cùng `DesignParams`
và ràng buộc rerandomization, seed mới mỗi draw) — trong-phiên đúng sơ đồ, không "xáo
outcome". Thống kê: hiệu hai trung bình studentized. Số draw: **2.000** (10.000 cho kết
quả cuối). p-value hai phía; **KTC 95% bằng nghịch đảo kiểm định** trên lưới hiệu ứng
hằng τ₀. (Bojinov & Shephard 2019; Bojinov et al. 2023. Cài đặt:
`analyze_outer(y, z, session_ids, phases, ...)`.)

**(b) Horvitz–Thompson/Hájek — ghi chú trung thực (sửa 06/09).** Với propensity hằng
p = 0,5 của tầng ngoài, ước lượng Hájek (IPW tự chuẩn hóa, `ht_effect`) **trùng đại số
với hiệu hai trung bình** ở (a) — trọng số hai nhánh bằng nhau nên mỗi trung bình có
trọng số thu gọn về trung bình nhánh. Nó KHÔNG phải một ước lượng viên độc lập thứ hai,
vì vậy báo cáo chỉ công bố **một** con số chính từ (a); `estimate_ht` đã bị gỡ khỏi
báo cáo API (`/experiment/summary`). Hàm `ht_effect` được giữ trong mã (kèm test) cho
tầng trong — nơi propensity thay đổi theo khối và IPW mới thực sự khác — và để kiểm
toán chính đẳng thức này.

**(c) Secondary giảm phương sai — OLS FE-phiên + hiệp biến kiểu Lin (2013).**
`y_b` hồi quy trên gán + FE phiên + hiệp biến demeaned và tương tác với gán
(Lin 2013 — không bao giờ hại độ chính xác tiệm cận). SE cụm theo phiên; với ~30 cụm
dùng **wild cluster bootstrap** (9.999 reps).

> **QUY TẮC HỢP LỆ CỦA HIỆP BIẾN (sửa 02/09).** Mọi hiệp biến phải được xác định tại
> **thời điểm sinh lịch gán**, tức không đổi khi vẽ lại vector gán.
>
> - **Hợp lệ:** chỉ số khối, vị trí chuẩn hóa trong phiên `t/T`, giai đoạn (đầu/giữa/cuối),
>   độ dài khối, `start_offset_s`, và các đặc trưng cấp phiên có TRƯỚC phiên (host, nền
>   tảng, thứ trong tuần, khung giờ, lượng người xem lúc mở phòng).
> - **KHÔNG hợp lệ:** `pre_viewers`, `pre_comment_rate`, `pre_like_rate` — chúng đo trong
>   cửa sổ thuộc khối **liền trước**, mà khối đó đã được ngẫu nhiên hóa. Vì rerandomization
>   tạo tương quan âm giữa các gán liền kề (đo được: −0,169), các biến này là **hậu can
>   thiệp** so với khối k−1 và đưa vào sẽ gây thiên lệch. Cũng không hợp lệ: hiệp biến lấy
>   từ cửa sổ burn-in của **chính khối đang xét** — đó là cửa sổ hậu-can-thiệp rõ nhất.
>
> Ba trường `pre_*` vẫn được TÍNH và lưu để phân tích khám phá hậu nghiệm (ví dụ hiệu ứng
> không đồng nhất theo mức hưng phấn — S-O-R, IMCOM 2026), nhưng **không vào ước lượng
> viên khẳng định**.

> **Trước khi đầu tư vào giảm phương sai, chạy `poisson_floor()` trên dữ liệu thăm dò.**
> Nếu `reducible_share < 0,15` thì phương sai gần như thuần nhiễu đếm và **không hiệp biến
> nào giúp được** — khi đó bỏ hẳn (c), ghi rõ kết quả đo này trong báo cáo, và đòn bẩy duy
> nhất là THIẾT KẾ (khối dài hơn → nhiều click mỗi khối → CV giảm theo 1/√click). Đo trên
> bộ mô phỏng đã hiệu chỉnh: CV trong-phiên 0,352 vs sàn Poisson 0,356 → phần giảm được
> ≈ 0.

(Cài đặt: `ols_fe_lin`, `cuped_adjust`, `poisson_floor`.)

**(d) LATE qua biến công cụ** — cho chế độ đề xuất (suggest) và dữ liệu đối tác:
2SLS với Z (gán) làm công cụ cho D = "sản phẩm hệ thống đề xuất thực sự được ghim ≥
`<x>`% khối" (từ `compliance_rate` + cờ override trong log). Báo cáo first-stage F và
**Anderson–Rubin CI**. (Cài đặt: `late_wald`; mở rộng `linearmodels.IV2SLS`/`ivmodels`.)

**Quy tắc nhất quán:** nếu (a) và (c) cho kết luận khác nhau, (a) là kết luận chính;
khác biệt phải được báo cáo và mổ xẻ trong phụ lục.

## 6. Lực thống kê — hai kịch bản (trung thực, không trộn dữ liệu hiệu chỉnh)

Phiên hiệu chỉnh tuần 3–5 **không đếm** vào mẫu khẳng định. Bảng điền từ
`livelift.analysis.power.scenario_table` với CV/ICC/compliance đo được tuần 3–4:

| Kịch bản | Số phiên khẳng định | Phút | Khối đo lường | MDE tương đối (α=0,05, power 0,8) |
|---|---|---|---|---|
| A — không đối tác (chỉ tuần 6–11) | `<~18>` | `<~1.620>` | `<...>` | `<...>` |
| B — có đối tác (đã ký) | `<...>` | `<...>` | `<...>` | `<...>` |

MDE hiệu chỉnh đầy đủ: ÷ tỷ lệ tuân thủ, × √deff cụm-phiên (ICC cấp phiên), × hệ số tự
tương quan dư, − ~10% n do burn-in, ÷ √(1−R²) nếu dùng hiệp biến. Nếu MDE kịch bản A
> 20%, con số đó được công bố như-nó-là; không nới thiết kế để "đẹp số".

## 7. Quy tắc dừng

Dừng thu thập vào ngày `<YYYY-MM-DD — cuối tuần 11>` hoặc khi hết `<n>` phiên đã đăng ký,
tùy điều kiện đến trước — **không phụ thuộc kết quả trung gian**. Không nhìn ước lượng
hiệu ứng trước ngày đóng băng dữ liệu `<YYYY-MM-DD>`; bảng theo dõi tuần chỉ hiển thị
chỉ số vận hành (số phiên, số khối hợp lệ, CV, MDE dự kiến) — không hiển thị τ̂.
Ngoại lệ duy nhất: dừng sớm vì an toàn/pháp lý, ghi log công khai.

Cơ chế cưỡng chế ở tầng API (thêm 06/09): đặt `RESULTS_FREEZE_UNTIL=<ngày đóng băng>`
trong cấu hình — trước ngày đó `/experiment/summary` gạt mọi trường suy diễn
(τ̂, p, KTC) và chỉ trả số liệu vận hành; giá trị sai định dạng khóa luôn (fail-closed).

## 8. Quy tắc loại trừ khối (tiền đăng ký, áp dụng mù với nhánh gán)

Khối bị đánh dấu `excluded_reason` (không bao giờ sửa số liệu) khi:
mất ingest > 60 giây liên tục trong khối; exposure < E_min (mục 4.1); can thiệp thủ công
ngoài 3 lý do cho phép (`hết hàng`, `sai giá`, `sự cố kỹ thuật`); vi phạm làm mù nghiêm
trọng ghi trong nhật ký phiên; lỗi lịch gán (khối không khớp lịch tiền-phiên).
Số khối loại và lý do báo cáo đầy đủ; phân tích độ nhạy có/không khối bị loại.

## 9. Biện pháp chống nhiễu (tiền đăng ký như một phần thiết kế)

- **Làm mù host:** màn hình host (route `/host`) chỉ hiện sản phẩm đang ghim, giá, tồn
  kho, tổng thời gian đã trôi — không ranh giới khối, không nhánh, không thời-gian-còn-lại.
- **Làm mù operator một phần:** operator không được xem trước chuỗi gán; không đọc to
  trạng thái khối; giao thức đầy đủ trong runbook. Vi phạm ghi nhật ký, xử lý theo mục 8.
- Can thiệp thủ công giới hạn 3 lý do, validation ở tầng API, ghi log đầy đủ propensity
  và `seconds_since_last_switch`.

## 10. Phân tích thứ cấp / khám phá dự kiến

Danh sách đầy đủ — mọi phân tích ngoài danh sách này dán nhãn "khám phá hậu nghiệm":

1. Hiệu ứng dị biệt theo 1/3 phiên (đầu/giữa/cuối) và theo nhóm giá sản phẩm.
2. Tầng trong: so sánh sản phẩm-vs-sản phẩm bằng IPW/AIPW Hájek trên propensity đã ghi,
   giới hạn tập overlap ngẫu nhiên hóa.
3. Đường suy giảm carryover hậu nghiệm (cập nhật t_mix) và plot τ̂ theo b ∈ {0,1,2,3}.
4. Outcome đơn hàng/GMV theo khối (funnel click→đơn).
5. Tương quan intent bình luận (radar NLP) với click — chỉ mô tả.
6. A/A trên các phiên hiệu chỉnh và trên simulator (false-positive rate ≈ α).

## 11. Tài liệu tham khảo

Toàn văn tổng thuật và đường dẫn trong `docs/research/` (đặc biệt
`2026-08-24-switchback-design.md`, `2026-08-24-estimators.md`,
`2026-08-24-bao-cao-tong-hop-nghien-cuu.md`).

- Bojinov, I., Simchi-Levi, D., & Zhao, J. (2023). *Design and Analysis of Switchback
  Experiments.* Management Science 69(7). (Quy tắc 2m khối biên; HT; randomization test.)
- Hu, Y., & Wager, S. (2022). *Switchback Experiments under Geometric Mixing.* JBES;
  arXiv:2209.00197. (Burn-in phân tích thay washout thiết kế; chọn b, sensitivity.)
- Lin, W. (2013). *Agnostic notes on regression adjustments to experimental data.*
  Annals of Applied Statistics 7(1). (Hiệp biến demeaned + tương tác.)
- Bojinov, I., & Shephard, N. (2019). *Time series experiments and causal estimands.*
  JASA 114(528). (Randomization inference đúng phân bố gán.)
- Ni, T., Kalfountzou, E., & Bojinov, I. (2025). *Reliable Switchback Experiments with
  Rerandomization.* HBS WP 26-012. (Ràng buộc ≥2 khối/nhánh/giai đoạn.)
- Xiong, R., Chin, A., & Taylor, S. (2024). *Data-Driven Switchback Experiments.*
  arXiv:2406.06768. (Jitter ranh giới; cân bằng chu kỳ.)
- Wen, Q., Shi, C., Yang, Y., Tang, W., & Zhu, H. (2024). arXiv:2403.17285.
  (Carryover × tự tương quan → tần suất switch.)
