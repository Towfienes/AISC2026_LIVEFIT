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
sản phẩm HỢP LỆ theo khối** (định nghĩa hợp lệ ở mục 4.1, sửa 08/09) so với chiến lược
mặc định của đội vận hành (nhánh TẮT) hay không?

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
- **Cân bằng transition (bổ sung 08/09/2026, trước khóa):** acceptance rule yêu cầu thêm,
  trên chuỗi khối đo được, **#cặp liền kề (BẬT,BẬT) ≥ 3 VÀ #(TẮT,TẮT) ≥ 3 VÀ
  |#(BẬT,BẬT) − #(TẮT,TẮT)| ≤ 1** — bảo đảm mọi phiên có đủ dữ liệu focal cho các ước
  lượng nhạy carryover (HT cặp liền kề kiểu Ni et al. 2025; CRT gộp khối Liu & Zhong).
  Ràng buộc **đối xứng dưới hoán vị BẬT↔TẮT** nên xác suất biên mỗi khối giữ đúng 0,5;
  đây là dạng khả thi duy nhất của blocked-SRSB (Zeng et al. 2026, arXiv:2604.02489)
  khi chỉ có một stream. Phiên ngắn không đủ khối: yêu cầu bị hạ theo trần khả thi của
  chuỗi, giá trị thực thi lưu ở `realized_transition_pairs` kèm cảnh báo trước phát sóng
  (không bao giờ chết vòng lặp — trần `max_redraws` giữ nguyên).
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
- **Cam kết thiết kế `design_hash` (bổ sung 08/09/2026, trước khóa — gói Q3):** cùng lúc
  sinh lịch, hệ thống tính `design_hash = SHA256(JSON chuẩn tắc của tham số thiết kế ∪
  seed)` và công bố nó ở phản hồi `POST /schedule`, trong `live_session.design`, và trên
  thanh trạng thái bàn điều khiển. Lịch là hàm tất định của (tham số, seed) nên hash này
  là vân tay của toàn bộ ngẫu nhiên hóa: người đọc giữ `design.params` + `design.seed`
  tính lại được và xác nhận thiết kế đã chạy đúng là thiết kế đã công bố.
- **Ghi sự kiện chỉ-ghi-thêm (bổ sung 08/09/2026, trước khóa — gói Q3):** TOÀN BỘ lịch
  được materialize vào `assignment_event` ngay lúc sinh (ý định thí nghiệm), và mọi hành
  động ghim/bỏ ghim của bàn được ghi vào `exposure_event` (thực tế vận hành) — hai bảng
  không có đường sửa/xóa ở tầng ứng dụng. **Tuân thủ trở thành đại lượng DẪN XUẤT** từ
  phép nối hai bảng (`livelift.core.quality.derive_compliance`), không còn là con số ghi
  đè được trên `experiment_block.compliance_rate`. Phiên ghi trước bổ sung này giữ nguyên
  đường cũ (`intervention_log`); hai nguồn không bao giờ trộn trong cùng một phiên.
  **Estimand chính KHÔNG đổi:** ITT vẫn theo `assignment`; hai bảng này chỉ phục vụ
  first-stage/LATE (mục 5(d)) và dấu vết kiểm chứng.
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
   độ dài khối {5, 10, 15} phút × carryover {đo được, 0, 2× đo được}
   × ICC cấp phiên {0, đo được ở 1(d)}.
   *(Sửa 09/09, gói P1-K2 — trước khi khóa.)* Trục ICC mới thêm vào: cho tới 09/09
   simulator **không có** cách nạp ICC đo được ở 1(d) vào mô phỏng — cú sốc phiên
   `session_shock_sd` chỉ nhân lượt vào, tức nhân cả tử lẫn mẫu của một tỷ lệ, nên
   không tạo ICC ở biến kết quả. Bước 1(d) đo ICC rồi bước 2 vứt đi. Knob
   `SimParams.session_click_sigma` (ánh xạ σ→ICC **đo được**, bảng chuẩn ở
   `docs/benchmarks/sim-icc-map.md`, sinh lại bằng
   `python analysis/calibration/bang_icc_mo_phong.py`) khép vòng đó lại. Khi bước
   1(d) cho ICC đo được trên phiên thật, tra bảng đó ra σ tương ứng rồi chạy lưới
   ở bước 2 — đó là toàn bộ đường nạp, không có bước ước đoán nào.
3. **Quy tắc quyết định:** chọn X nhỏ nhất trong lưới sao cho, với t_mix đo được
   **và ICC đo được**, bias mô phỏng của ước lượng viên chính (có burn-in b=1)
   < 10% hiệu ứng và MDE mô phỏng nhỏ nhất. Nếu t_mix > 3 phút, X=5 bị loại và
   lưới xét {10, 15}.
4. Kết quả (X, các số đo, power curve) ghi vào notebook `analysis/calibration/`,
   commit `<hash>`; giá trị chốt điền vào mục 2 khi khóa.

**Burn-in phân tích:** chính b = **1 phút** đầu mỗi khối bị loại khỏi ước lượng
(exposure và click tính từ giây 60); **sensitivity bắt buộc b ∈ {0, 2, 3} phút** báo cáo
kèm mọi kết quả chính. Nếu ước lượng đổi dấu hoặc mất ý nghĩa theo b, phải báo cáo trung
thực như một hạn chế. (Cài đặt: tham số `burn_in_s` của `livelift.core.features.block_frame`.)

## 4. Biến kết quả

### 4.1 Biến chính

**Tỷ lệ nhấp HỢP LỆ theo khối, chuẩn hóa exposure** (sửa 08/09/2026 — gói Q1, trước khóa):

```
y_b = 1000 × (số LƯỢT NHẤP HỢP LỆ trong khối b, sau burn-in) / (viewer-giây exposure của khối b, sau burn-in)
```

đơn vị: **lượt nhấp hợp lệ / 1.000 viewer-giây**.

- **Định nghĩa vận hành của một click** (mọi nền tảng): một request đến redirect tự host
  `/r/{code}` của shortlink UTM ghim trong bình luận/overlay, ghi ở bảng `click_event`
  với timestamp **server-side**. Click quy về khối chứa timestamp của nó. Đây là định
  nghĩa duy nhất — không dùng số liệu click của nền tảng.
- **Click HỢP LỆ** (IAB Click Measurement Guidelines 2009, lọc GIVT-lite; Fabijan et al.
  KDD 2019): một click bị gắn cờ KHÔNG hợp lệ (`is_valid=false` + `invalid_reason`,
  không bao giờ xóa row — flag-don't-drop) khi vi phạm một trong 5 quy tắc, cài đặt
  tham chiếu `livelift.core.click_validity.classify_click`:
  1. `givt_ua` — user-agent khớp danh sách robot/spider/công cụ đã biết (regex GIVT-lite,
     case-insensitive: bot, crawler, spider, headless, curl, wget, python-requests,
     scrapy, phantomjs, selenium, …);
  2. `prefetch` — header prefetch/prerender/preview của trình duyệt (`Sec-Purpose` chứa
     prefetch/prerender, `X-Moz: prefetch`, `X-Purpose: preview`);
  3. `non_get` — chỉ request GET được đếm là click;
  4. `refractory` — đã có click ĐƯỢC ĐẾM cùng `dedup_hash` (salt xoay theo phiên) trên
     cùng shortlink trong vòng **τ = 10 giây** trước đó (giá trị chính);
  5. `volume_cap` — quá **M = 5** click được đếm cùng `dedup_hash`/shortlink/khối.
- **Sensitivity bắt buộc:** kết quả chính báo cáo kèm τ ∈ {5, 30, 60} giây (chạy lại
  phân loại bằng `recount_click_validity`, đối soát T+30′ sau phiên qua
  `livelift-qc --recount-clicks`). Nếu kết luận đổi theo τ, báo cáo trung thực như
  một hạn chế.
- **Raw clicks là secondary BẮT BUỘC báo cáo kèm:** chuỗi y_b tính trên TOÀN BỘ click
  (kể cả click bị gắn cờ; `block_frame(include_invalid=True)`, trường `clicks_raw`)
  được báo cáo song song với chuỗi hợp lệ trong mọi kết quả chính; tổng
  `raw_clicks`/`valid_clicks` là số vận hành trong `/experiment/summary`.
- **Nguyên tắc mù với nhánh gán:** mọi quy tắc hợp lệ chỉ dùng thuộc tính request
  (user-agent, header, method, lịch sử request cùng fingerprint) — module phân loại
  không nhận và không được phép nhận nhánh gán/propensity (bất biến có test khẳng định:
  `tests/test_click_validity.py::test_assignment_blindness`).
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

**Vì sao đơn hàng KHÔNG được nâng lên biến chính (bổ sung 08/09/2026, trước khóa — gói
Q4).** Đã tính MDE cho biến kết quả số đơn bằng đúng machinery lực thống kê của mục 6
(`livelift.analysis.power.order_mde_table`; bảng sinh lại được bằng một lệnh:
`python analysis/power/bang_mde_don_hang.py` → `docs/benchmarks/order-mde.md`). Đơn là
biến ĐẾM HIẾM nên phương sai bị nhiễu đếm chi phối; CV nạp vào là CV Poisson
`√(trung bình_k 1/λ_k)` — cùng đại lượng `poisson_floor()` đo trên dữ liệu thật — nên
con số ra là **SÀN**, MDE thật chỉ có thể lớn hơn. Kết quả: ở quy mô khán giả của giai
đoạn thí nghiệm (≤ 50 người xem đồng thời), MDE tốt nhất trong toàn lưới vẫn **~79%**.
Đơn hàng vì thế ở lại mục 4.2, báo cáo kèm bất định, **không dùng để kết luận**; không
có kịch bản nào trong lưới biện minh cho việc chuyển nó lên biến chính.

Chuyển đổi click→đơn dùng **prior** pv→giỏ 9,33% × giỏ→mua 24,33% ≈ 2,27% (Taobao
UserBehavior, Alibaba Tianchi bộ #649), quét q2 ∈ {0,15; 0,25; 0,35; 0,50}; nhánh đối
tác nhân **khán giả** ×4,9 (arXiv:2106.03415). Toàn bộ dán nhãn KỊCH BẢN — không dòng
nào là số đo của dự án. **CẤM map KuaiLive vào phễu này**: 'click' của KuaiLive là *vào
phòng live*, không phải nhấp sản phẩm ghim.

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

**CUPED đa biến — chỉ hiệp biến TẤT ĐỊNH (bổ sung 09/09/2026, trước khóa — gói P4).**
`cuped_adjust_mv(y, X, session_ids)` mở rộng (c) sang nhiều hiệp biến cùng lúc, với X do
`build_deterministic_covariates` sinh: `sin/cos(2π·giờ-trong-ngày/24)` lấy từ **giờ bắt đầu
thật của khối** (đổi sang Asia/Ho_Chi_Minh — nhịp mua sắm theo đồng hồ địa phương) và spline
bậc 2 của **phút-vào-phiên tại giữa khối** (`t`, `t²`, `max(0, t−45)²`, nút 45 phút là hằng số
lịch, KHÔNG khớp từ dữ liệu). Mọi cột là hàm của LỊCH và ĐỒNG HỒ, nên X bất biến khi vẽ lại
vector gán ⇒ kiểm định ngẫu nhiên hóa vẫn CHÍNH XÁC. θ̂ ước lượng bằng ridge dạng đóng, λ chọn
bằng **CV bỏ-một-PHIÊN** (bỏ-một-khối sẽ rò rỉ: các khối cùng phiên chia chung cú sốc phiên).
Báo cáo kèm R² **ngoài-phiên** bên cạnh R² trong-mẫu — số trong-mẫu luôn lạc quan.
Danh sách CẤM ở khung §5c trên vẫn nguyên vẹn: **cấm mọi lag trong-phiên**. Đường này
**TẮT mặc định** (`analyze_outer(adjust='none')`); bật cho kết quả khẳng định là một quyết
định tiền đăng ký của nhóm, phải ghi trước khi mở khóa dữ liệu. Nhắc lại đo lường ở khung
trên: nếu `reducible_share ≈ 0` thì hàm này đúng khi KHÔNG giảm được gì — `se_ratio ≈ 1` và
R² ngoài-phiên ≤ 0 là kết quả trung thực, không phải lỗi.

(Cài đặt: `ols_fe_lin`, `cuped_adjust`, `cuped_adjust_mv`,
`build_deterministic_covariates`, `poisson_floor`.)

**(d) LATE qua biến công cụ** — cho chế độ đề xuất (suggest) và dữ liệu đối tác:
2SLS với Z (gán) làm công cụ cho D = "sản phẩm hệ thống đề xuất thực sự được ghim ≥
`<x>`% khối". **Nguồn của D (cập nhật 08/09/2026, trước khóa — gói Q3):**
`derive_compliance(assignment_event, exposure_event)` — chỉ phơi nhiễm `source='model'`
tính là hệ thống chạy chính sách; ghim tay là bất tuân theo đúng định nghĩa. Phiên ghi
trước gói Q3 rơi về `compliance_rate` + cờ override trong log. Báo cáo first-stage F và
**Anderson–Rubin CI**. (Cài đặt: `late_wald`; mở rộng `linearmodels.IV2SLS`/`ivmodels`.)

**(e) Mẫu số nội sinh — độ nhạy bắt buộc báo cáo (bổ sung 09/09/2026, trước khóa — gói P3).**
Biến kết quả chính là một TỶ LỆ: click hợp lệ chia viewer-giây. Phép chia đó chỉ vô hại nếu
**mẫu số không chịu tác động của can thiệp** — mà ghim thẻ là thay đổi nhìn thấy được trong
phòng live, hoàn toàn có thể giữ chân hoặc đuổi người xem. Giả định đó vì vậy được KIỂM TRA
chứ không được mặc định:

- **Cổng ICS** (`analysis.robust.ics_gate`, arXiv:2510.01127): chạy đúng kiểm định ngẫu nhiên
  hóa ở (a) — cùng cơ chế redraw production, cùng thống kê studentized — nhưng lấy
  **viewer-giây làm biến kết quả**. Mức gắn cờ **α = 0,10** (lỏng hơn 0,05 có chủ đích: bỏ sót
  một mẫu số nội sinh tốn kém hơn nhiều so với in thừa một chú thích). Kết quả là **CỜ**:
  không loại khối, không đổi con số chính, chỉ buộc đọc kèm estimand mẫu-số-cố-định
  (HARNESS §3, flag-don't-drop). Không gắn cờ **KHÔNG** phải bằng chứng mẫu số ngoại sinh —
  ở vài chục phiên kiểm định này ít công suất trước hiệu ứng nhỏ.
  **Đây KHÔNG phải một mục SRM và không thuộc bộ §8.1**: §8.1 cấm chạy SRM trên đại lượng hậu
  can thiệp, và viewer-giây đúng là hậu can thiệp. Khác biệt nằm ở Ý NGHĨA của cờ — SRM đỏ nói
  "dữ liệu hỏng, đi tìm lỗi đường ống", cổng này nói "estimand cần một chú thích".
  Vì nó kiểm định trên đại lượng hậu can thiệp, nó **cũng bị khóa theo §7**: `/experiment/summary`
  chỉ trả cờ này sau ngày mở khóa.
- **Estimand mẫu-số-cố-định** (`analysis.adjust.linearize_ratio`, Deng KDD 2018 /
  arXiv:1803.06336): `L_b = click_b − r0·exposure_b`, chạy **nguyên** pipeline (a) — redraw,
  thống kê studentized, Fisher CI — trên `L_b`. **Quy ước r0 (tiền đăng ký):** `r0` là tỷ lệ
  gộp `Σclick / Σexposure` **của mẫu quan sát**, tính MỘT LẦN từ dữ liệu như đã ghi và **CỐ
  ĐỊNH qua mọi redraw**, mọi điểm lưới Fisher-CI, mọi lần bootstrap. Tính lại r0 bên trong một
  redraw sẽ làm vector kết quả động theo vector gán đang kiểm định và phá tính chính xác của
  kiểm định. **Đơn vị của τ̂ trên đường này là CLICK đã tuyến tính hóa, không phải
  click/1.000 viewer-giây** — chỉ so được dấu và mức ý nghĩa với con số chính, tuyệt đối không
  in cạnh nhau như hai ước lượng cùng thang. Đường này TẮT mặc định
  (`analyze_outer(outcome_mode='ratio')`).
- **Phương sai delta-method theo cụm** (`analysis.adjust.delta_var_ratio`, cùng nguồn Deng):
  **CHỈ MÔ TẢ**. Nó là xấp xỉ chuẩn dựa vào CLT theo cụm; mẫu tiền đăng ký K = 18–31 phiên nằm
  đúng vùng xấp xỉ đó lệch (arXiv:2606.27662), nên **không dùng làm KTC chính**. KTC chính vẫn
  là Fisher CI ở (a), vốn không cần CLT theo cụm.

**Quy tắc nhất quán:** nếu (a) và (c) cho kết luận khác nhau, (a) là kết luận chính;
khác biệt phải được báo cáo và mổ xẻ trong phụ lục. Nếu cổng ICS ở (e) gắn cờ, kết luận chính
phải được báo cáo **kèm** kết quả đường mẫu-số-cố-định, và sự khác biệt (nếu có) là một hạn chế
được nêu thẳng, không phải một lựa chọn hậu nghiệm giữa hai con số.

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

Cổng ICS §5e **cũng nằm trong phạm vi khóa** (bổ sung 09/09, trước khóa — gói P3): nó kiểm
định trên viewer-giây, một đại lượng HẬU CAN THIỆP, nên biết nó có gắn cờ hay không đã là biết
một phần tác động của can thiệp. Trường `denominator_check` vì thế chỉ mang p-value sau ngày
mở khóa; trước đó nó trả về lý do khóa. (Đây là chỗ nó khác các kiểm tra §8.1, vốn chạy trên
đại lượng độc lập với nhánh gán và được phục vụ hằng tuần.)

## 8. Quy tắc loại trừ khối (tiền đăng ký, áp dụng mù với nhánh gán)

Khối bị đánh dấu `excluded_reason` (không bao giờ sửa số liệu) khi:
mất ingest > 60 giây liên tục trong khối; exposure < E_min (mục 4.1); can thiệp thủ công
ngoài 3 lý do cho phép (`hết hàng`, `sai giá`, `sự cố kỹ thuật`); vi phạm làm mù nghiêm
trọng ghi trong nhật ký phiên; lỗi lịch gán (khối không khớp lịch tiền-phiên).
Số khối loại và lý do báo cáo đầy đủ; phân tích độ nhạy có/không khối bị loại.

### 8.1 Kiểm tra toàn vẹn sau phiên — SRM đợt 1 (bổ sung 08/09/2026, trước khóa — gói Q5)

Bộ QC sau phiên (kế hoạch §8.3) lên **8 mục**, thêm hai kiểm tra chẩn đoán. Cài đặt tham
chiếu: `livelift.core.quality`, chạy qua `livelift-qc`.

- **`assignment_integrity`** — số khối và **chuỗi gán** phải khớp giữa lịch ĐÃ LƯU và
  khung phân tích thật sự đi vào ước lượng viên (`core.features.block_frame`). Nguồn lịch
  ưu tiên `assignment_event` (bảng chỉ-ghi-thêm, lọc theo `design_hash` của lượt rút đã
  chạy), rơi về `design['blocks']` cho phiên tiền-Q3; hai nguồn persist mâu thuẫn nhau là
  một lỗi riêng biệt. Lệch bất kỳ = FAIL kèm chi tiết. Kiểm tra tất định, không có α.
- **`telemetry_delivery`** — kiểm định nhị thức CHÍNH XÁC hai phía
  (`scipy.stats.binomtest`) trên số nhịp `session_tick` rơi vào khối BẬT vs TẮT. Kỳ vọng
  là **tỷ lệ THỜI GIAN BẬT/TẮT của lịch đã persist**, *không phải 0,5* — khối biên nhân
  đôi (mục 2) và jitter làm tỷ lệ thời gian lệch khỏi một nửa ở nhiều lịch hoàn toàn hợp
  lệ. Nhịp tick do đồng hồ sinh nên độc lập với nhánh; lệch ⇒ lỗi đường ống hoặc sự cố
  telemetry.

**α = 0,005 mỗi kiểm định**, họ ~10 kiểm tra ⇒ sai lầm loại I toàn họ ≤ 5% (Bonferroni).

**Kết quả là CỜ, không phải hành động.** Không kiểm tra nào tự sửa hay tự loại dữ liệu;
một mục ĐỎ buộc điều tra nguyên nhân trước khi tin số của phiên đó (HARNESS §3). Loại
khối vẫn chỉ theo đúng danh sách lý do ở mục 8.

**TUYỆT ĐỐI KHÔNG chạy SRM trên người xem / bình luận / click.** Ba đại lượng đó là hậu
can thiệp: nếu can thiệp có tác dụng thì chúng PHẢI lệch giữa hai nhánh — đó chính là
điều thí nghiệm đi đo. SRM chỉ hợp lệ trên đại lượng được quyết định trước hoặc độc lập
với nhánh (dấu vết gán; nhịp giao telemetry theo đồng hồ).

**Độ nhạy đã đo (không phỏng đoán).** Ở mức MỘT phiên 90 phút (~180 nhịp),
`telemetry_delivery` chỉ bắt được sự cố thô (mất ~50% nhịp một nhánh); mất 10% là vô
hình. Chẩn đoán mất mát nhỏ phải GỘP cả chuỗi phiên (cộng `TelemetryCounts` rồi kiểm định
một lần): đo được công suất 100% và FPR 0% trên 50 lần lặp × 30 phiên khi mất 10% nhịp
khối TẮT. Bảo thủ ở mức mỗi-phiên là cố ý — một cổng kêu oan hàng tuần sẽ bị bỏ qua.

### 8.2 Quy tắc NẠP PHIÊN vào mẫu phân tích (bổ sung 12/09/2026, trước khóa — gói C)

Mục 8 nói khối nào bị loại. Mục này nói **phiên nào được tính**, và nó tồn tại vì một
sự cố vận hành: cho tới 12/09 `/experiment/summary` gộp **mọi** phiên `status='ended'` có
lịch gán, không phân biệt phiên thật với phiên bấm thử. Hai phiên dò lỗi sống đúng một
giây, không một cú nhấp, đã lọt vĩnh viễn vào kết quả gộp và **không có cách nào gỡ ra**
(`docs/benchmarks/kiem-chung-van-hanh.md` §2.4c). Bản vá thêm một cái cờ — và một cái cờ
loại phiên khỏi kết quả là thứ nguy hiểm, nên quy tắc dùng nó phải nằm ở đây, trong tiền
đăng ký, chứ không nằm trong mã nguồn.

**Một phiên vào mẫu khẳng định khi và chỉ khi cả năm điều sau đúng:**

1. `status = 'ended'` — buổi phát đã diễn ra và đã kết thúc. Phiên `cancelled` (đóng mà
   **chưa từng lên sóng**, trạng thái thêm ở migration 0008) không có khối đo nào: nó
   không mang `start_ts`, nên việc loại nó là **cấu trúc**, không phải một bộ lọc ai đó
   phải nhớ áp dụng.
2. Có lịch gán đã lưu TRƯỚC phiên (mục 2) — không có ngẫu nhiên hóa thì không có estimand.
3. `design.analysis_only` sai — phiên phân tích video của người khác là **quan sát**, không
   bao giờ mang đại lượng thí nghiệm (E2-04).
4. `dry_run` sai — phiên không được khai báo là **chạy thử**.
5. `is_demo` sai — phiên không phải **dữ liệu mẫu** (bổ sung 12/09/2026, trước khóa —
   gói DEMO-THẬT; migration 0009).

**Hai cờ, hai câu hỏi khác nhau — định nghĩa khóa tại đây:**

- `is_demo` = **"dữ liệu này có THẬT không?"** Phiên do máy sinh ra làm dữ liệu mẫu để
  xem thử/tập demo (seed mô phỏng qua `POST /demo/seed`, bộ phiên demo vàng
  `scripts/seed_demo_vang.py`, replay mẫu của demo). Không có buổi phát nào từng diễn ra
  sau con số của nó. Chỉ các máy sinh demo **phía server** đặt được cờ này —
  `POST /sessions` không nhận nó, nên không tồn tại đường nào dán nhãn "dữ liệu mẫu" lên
  một phiên thật, dù vô tình hay cố ý. Phiên demo bị loại khỏi **mọi** đầu ra khoa học
  thật: `/experiment/summary` mặc định (`env=real`), export lô gán nhãn NLP
  (`livelift.nlp.label_llm.collect_from_store` từ chối phiên demo), và mọi đường gộp sau
  này. Nó vẫn xem được riêng — luôn kèm cờ `is_demo` trên payload để giao diện vẽ nhãn
  DEMO/watermark.
- `dry_run` = **"phiên THẬT này có được TÍNH không?"** Người thật vận hành đường ống thật
  nhưng khai báo trước là chạy thử/tập dượt. Dữ liệu thật về cơ chế sinh, chỉ không vào
  mẫu phân tích gộp.

  Không gộp hai cờ làm một: dùng lại `dry_run` cho phiên seed sẽ làm giao diện không phân
  biệt được nhãn "DEMO — dữ liệu mẫu" với "chạy thử", và làm chế độ DEMO/THẬT cấp ứng dụng
  (trường `mode` trên `GET /health`) đếm sai.

  Cả hai cờ cùng ba ràng buộc: khai báo lúc **tạo** phiên, **bất biến** sau đó
  (`store._SESSION_WRITE_ONCE`), mặc định là **thật/tính vào**.

**Bản gộp CHỈ-DEMO (`/experiment/summary?env=demo`)** tồn tại cho màn trình diễn: nó gộp
*duy nhất* phiên `is_demo`, đổi nhãn thành "kết quả MÔ PHỎNG — … KHÔNG phải kết quả thật"
và mang `env='demo'` trên payload; hai bể dữ liệu rời nhau theo cấu trúc, không giá trị
tham số nào trộn được chúng. **Khóa §7 không áp cho dữ liệu demo** (cả `env=demo` lẫn phần
nhân quả của `bao-cao` trên phiên demo): §7 chặn *nhìn trộm kết quả thật* trước ngày mở —
"hiệu ứng" của một phiên demo là tham số ai đó gõ vào simulator, không có gì để nhìn trộm;
và bộ demo vàng phải trình được cả ba trạng thái kết quả ngay trong cửa sổ khóa chiến dịch
(bảo hiểm demo theo cả hai vòng phản biện). Không phiên thật nào lách qua ngoại lệ này vì
không phiên thật nào mang được cờ `is_demo`.

**Cờ `dry_run` — vì sao nó không phải cửa hậu chọn lọc kết quả.** Ba ràng buộc, cả ba đã
cài đặt và có test khẳng định:

- **Khai báo lúc TẠO phiên** (`POST /sessions`), tức **trước** khi bốc lịch gán, trước khi
  lên sóng, trước khi tồn tại một con số nào. Không có ô "loại phiên này" bấm được sau khi
  đọc kết quả.
- **Bất biến sau đó.** Không endpoint nào nhận `dry_run` ngoài lúc tạo; cả hai store đều
  bỏ qua nó trong `update_session` (`store._SESSION_WRITE_ONCE`, cùng danh sách cột
  write-once cho cả memory lẫn Postgres). Gate:
  `tests/test_vong_doi_phien.py::test_the_dry_run_flag_cannot_be_flipped_after_the_fact`.
- **Mặc định là TÍNH VÀO.** `dry_run = false` cho mọi phiên, kể cả phiên ghi trước
  migration 0008. Một phiên thật biến mất âm thầm khỏi mẫu còn tệ hơn một phiên thử lọt
  vào: cái sau nhìn thấy được, cái trước thì không.

**Loại thì phải ĐẾM.** `/experiment/summary` công bố `sessions_excluded` — lý do tiếng Việt
→ số phiên, cho cả bốn nhóm (dữ liệu mẫu/demo, chưa kết thúc/đã huỷ, quan sát, chạy thử).
Một phiên bị loại mà không ai thấy thì không phân biệt được với một phiên chưa từng tồn
tại; con số này để người đọc đối chiếu mẫu thật với mẫu đã khai. Nhóm demo được đếm TRƯỚC
các nhóm khác: phiên demo đứng ngoài vì nó là dữ liệu mẫu, bất kể trạng thái.

**Điều này KHÔNG cho phép:** loại một phiên **thật** sau khi đã chạy. Phiên thật hỏng giữa
chừng (mất ingest, sự cố kỹ thuật, vi phạm làm mù) xử lý ở **cấp khối** theo mục 8 —
`excluded_reason` trên từng khối, báo cáo đầy đủ số khối loại và lý do, kèm phân tích độ
nhạy có/không khối bị loại. Không có đường nào rút cả một phiên khỏi mẫu sau khi thấy số
liệu của nó; nếu một hoàn cảnh bất thường buộc phải làm vậy, nó là **sai lệch tiền đăng ký**
và phải công bố như một sai lệch, kèm kết quả tính cả hai cách.

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
7. Độ nhạy mẫu số nội sinh: cổng ICS + đường estimand mẫu-số-cố-định (§5e) — báo cáo kèm
   kết quả chính, không thay thế nó.
8. Giảm phương sai bằng CUPED đa biến trên hiệp biến tất định (§5c) — báo cáo `se_ratio` và
   R² ngoài-phiên đo được, kể cả khi bằng 0.

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
  Rerandomization.* HBS WP 26-012. (Ràng buộc ≥2 khối/nhánh/giai đoạn; HT cặp liền kề.)
- Zeng, Adjaho, Bucarey, Qin, Zhang, Hoban, Johari & Wager (2026). *Sequentially-
  Rerandomized Switchback Experiments.* arXiv:2604.02489. (Blocked-SRSB cần nhiều đơn vị
  song song — với 1 stream chuyển thành ràng buộc cân bằng transition trong acceptance.)
- Xiong, R., Chin, A., & Taylor, S. (2024). *Data-Driven Switchback Experiments.*
  arXiv:2406.06768. (Jitter ranh giới; cân bằng chu kỳ.)
- Wen, Q., Shi, C., Yang, Y., Tang, W., & Zhu, H. (2024). arXiv:2403.17285.
  (Carryover × tự tương quan → tần suất switch.)
- Fabijan, A., Dmitriev, P., McFarland, C., Vermeer, L., Holmström Olsson, H., & Bosch, J.
  (2019). *Diagnosing Sample Ratio Mismatch in Online Controlled Experiments.* KDD.
  (SRM đợt 1, mục 8.1 — chỉ trên đại lượng độc lập với nhánh.)
- Alibaba Tianchi, bộ dữ liệu **UserBehavior** #649 (Taobao, 11–12/2017). (Prior phễu
  pv→giỏ 9,33% × giỏ→mua 24,33% cho MDE đơn hàng, mục 4.2 — PRIOR, không phải số đo.)
- arXiv:2106.03415 — thương mại điện tử qua livestream. (Hệ số khán giả ×4,9 của nhánh
  đối tác trong bảng MDE đơn hàng, mục 4.2 — KỊCH BẢN.)
