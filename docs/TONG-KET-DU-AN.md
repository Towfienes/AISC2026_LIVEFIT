# LiveLift — Tổng kết dự án

*Cập nhật 03/09/2026 · tài liệu sống — cập nhật sau mỗi cột mốc*

Ba phần: **(I) đã đạt được gì** (kèm số kiểm chứng được), **(II) cần làm thêm gì**
(ưu tiên P0/P1/P2, ghi rõ việc nào cần con người), **(III) mục tiêu & tầm nhìn khi
hoàn thành**.

---

## I. ĐÃ ĐẠT ĐƯỢC GÌ

### I.1 Nền khoa học — thứ quyết định giải thưởng

| Thành phần | Trạng thái | Bằng chứng |
|---|---|---|
| Bộ gán switchback 2 tầng theo văn liệu 2023–2025 (endpoint-double, rerandomization, jitter, burn-in thay washout) | ✅ | `core/assigner/` + 1000-lịch balance gate |
| Kiểm định ngẫu nhiên hóa studentized, redraw bằng **hàm gán production trên toàn lịch** + Fisher CI | ✅ | `analysis/estimators.py` |
| **Ước lượng viên được chứng minh hiệu chỉnh**: A/A 200 lặp → bác bỏ 4.5% (nhị thức p=0.872), coverage 95.5% | ✅ | gate `test_sim_validation.py` |
| Từ chối có kỷ luật: thiết kế không kiểm định được → `estimable=False` + lý do, **không bao giờ bịa số** | ✅ | sửa lỗi FATAL "NaN→significance" (52% dương tính giả → 6.2%) |
| MDE gắn với **lực thống kê đo được** (margin 1.2 đo bằng sweep), within-session CV, poisson_floor | ✅ | `analysis/power.py`, gate MDE-khớp-lực |
| Mô phỏng **hiệu chỉnh theo KuaiLive** (1.16M phòng shop thật) + đo trung thực dưới hiệu ứng lưu | ✅ | `docs/benchmarks/kuailive-calibration.md` |
| Kiểm toán đối kháng 4 góc + 2 phản biện/phát hiện: 16/16 xử lý | ✅ | `docs/incident-log.md` (13 sự cố đủ root cause) |
| Tiền đăng ký phân tích bản mẫu đầy đủ (quy tắc hiệp biến hợp lệ, sensitivity burn-in, 2 kịch bản lực) | ✅ chưa khóa | `PREREGISTRATION.md` — khóa tuần 6 |

### I.2 Sản phẩm

| Thành phần | Trạng thái |
|---|---|
| Vòng đời phiên trọn vẹn trên giao diện (4 bước, không cần lệnh) + cảnh báo khoa học trước phát sóng | ✅ `/chay-phien` |
| Bàn trung control 3 vùng · màn hình host **làm mù ở cấp kiểu dữ liệu** · replay engine | ✅ |
| Trang Kết quả: tác động + KTC + p trung thực (sàn hoán vị, "chưa kết luận được") | ✅ `/ket-qua` |
| Phân tích VOD YouTube thật: **live-fire 14.903 bình luận thật qua API** — nhãn "quan sát", không số nhân quả | ✅ |
| Ma trận tín hiệu: "đo được gì, thiếu tín hiệu nào, vì sao" cho nguồn bất kỳ | ✅ `GET /sessions/{id}/signals` |
| Phân loại ý định tiếng Việt **đã train** (macro-F1 0.870 vs 0.653 keyword; ngưỡng tự tin chống ngoài miền) | ✅ |
| Thẻ hành động Gamma-Poisson: cold-start = prior = khám phá đều đúng propensity | ✅ |
| Đo click qua redirect tự phục vụ; lọc PII tiếng Việt recall ≥95%; QC 6 mục sau phiên | ✅ |
| UI kit 10 component chuẩn Tremor/shadcn/Linear, skeleton loading, 0 dependency thêm | ✅ |
| Ingest YouTube/Facebook API chính thức (đúng quota/streamList/live_filter) | ✅ code, ⏳ chưa chạy với credential thật |

### I.3 Kỷ luật kỹ thuật

157 test (4 hành trình người dùng end-to-end) · contract test web↔API sinh từ sự cố
thật · hai store chung contract · CI 5 job + nightly gate thống kê · 13 sự cố ghi sổ
với root cause + gate chặn tái diễn · mọi benchmark sinh lại được bằng script.

---

## II. CẦN LÀM THÊM GÌ

### P0 — đường găng, cần CON NGƯỜI, trước 14/09

| Việc | Ai | Ghi chú |
|---|---|---|
| Xác minh hạn nộp vòng 1 với BTC (tài liệu đang lệch 14 vs 15/09) + hợp nhất một bộ số (ngân sách 17,2M, số phiên) | SP | trễ 1 ngày = loại |
| Lập Fanpage + app Facebook Developer (Development Mode **đọc được Page mình ngay**, không chờ App Review) · nộp App Review song song cho Page đối tác | SP + KS | điền `FACEBOOK_*` vào `.env` là ingest chạy |
| Chốt mặt hàng, đặt lô đầu (~3M) — đơn giá thấp, mua lặp lại, dễ gói | SP | CV quyết định lực thống kê |
| Chạy 2–3 phiên thử + quảng cáo đo **chi phí thật/người xem** — kế hoạch gốc hụt ~10 lần (300k ≈ 5–15 concurrent, không phải 80) | SP + TN | quyết định: tăng ngân sách / hạ ngưỡng / dồn vào đối tác |
| Gửi 10 thư mời đối tác dữ liệu (mẫu sẵn `ops/templates/`) | SP | 10 phiên phòng 200–500 người > 30 phiên phòng 20 người |

### P1 — trước khi khóa tiền đăng ký (tuần 6)

| Việc | Ai | Ghi chú |
|---|---|---|
| **Hiệu chỉnh tuần 3 trên kênh THẬT**: đo t_mix (suy giảm sau bỏ ghim), dwell, CV trong-phiên, ICC phiên → chốt độ dài khối + burn-in | TN | bảng đo sẵn: hiệu ứng lưu bán rã ≥3ph làm coverage tụt 60% → nếu t_mix dài, **khối 10 phút** (poisson_floor: cắt ~35% MDE) |
| Điền và **khóa PREREGISTRATION.md** bằng commit | TN | mẫu đã đầy đủ, chỉ điền số đo |
| Ghi đơn hàng vào hệ thống (bảng `order_event` có, **chưa có API ghi**) → QC đối soát doanh thu chạy được | KS | thiếu là gói Performance không kiểm chứng được |
| Chạy ingest thật với credential (YouTube API key, FB token) trên 2 phiên thử | KS | code xong, cần khóa thật |
| Gán nhãn đợt 1 bình luận thật (~300, active learning: câu model kém chắc nhất) → retrain, cập nhật benchmark bằng số thật | NC | pipeline sẵn: `python -m livelift.nlp.train_intent` |

### P2 — trước chung kết

| Việc | Ghi chú |
|---|---|
| Model A dự báo người xem — **chỉ nếu** thắng baseline trung bình trượt trên backtest rolling-origin (quyết định bằng số, không mặc định làm) | thiết kế + tiêu chí đã có trong docs/research |
| ViSoBERT fine-tune khi đủ 2–3k nhãn thật; TF-IDF hiện tại làm ablation | |
| Slide "giới hạn tự khai": MDE thật, coverage dưới hiệu ứng lưu dài, blinding không tuyệt đối, một can thiệp, một cửa hàng | chất liệu có sẵn trong benchmarks/incident-log |
| Wild cluster bootstrap cho OLS (~30 cụm) làm sensitivity phụ | đã ghi trong prereg mẫu |
| Kịch bản demo chung kết: replay + đổi tham số tại chỗ + "hiện phần bên trong" | `/replay` đã có what-if hết hàng |

### Nợ kỹ thuật đã biết (không giấu)

- Job phân tích VOD chạy in-process (đủ cho pilot; quá 3–4 job song song cần queue).
- `base_click_prob` mô phỏng là giả định — **không thể** hiệu chỉnh từ KuaiLive (ngữ
  nghĩa click khác); chờ phiên thử.
- Số intent 0.870 đo trên bộ biên soạn cùng phân phối — trên chat thật sẽ giảm (đã
  ghi rõ trong benchmark, có kế hoạch đo lại).
- Docker Desktop trên máy dev thỉnh thoảng tự tắt (3 lần) — không phải lỗi dự án,
  nhưng VPS production cần daemon ổn định.

---

## III. MỤC TIÊU & TẦM NHÌN KHI HOÀN THÀNH

### Khi mùa thi kết thúc (11/2026), "hoàn thành" nghĩa là

1. **Một con số có bảo chứng** đứng giữa slide chung kết: *tác động của chiến lược ghim
   LiveLift lên tỷ lệ nhấp, KTC 95%, từ ≥18 phiên thật, phân tích đúng tệp tiền đăng ký
   đã khóa* — kèm MDE thật và câu trả lời thẳng biến nào đủ lực, biến nào không. Kết
   quả *không* có ý nghĩa thống kê vẫn là kết quả hợp lệ — giá trị nằm ở **hạ tầng đo
   lường tự chứng minh được**.
2. **Một sản phẩm người ngoài dùng được**: đối tác dữ liệu chạy phiên của họ ở chế độ
   đề xuất, nhận báo cáo tác động trên chính phòng của mình.
3. **Một hồ sơ phương pháp** giám khảo khó bắt bẻ: mọi câu hỏi dự kiến (p-hacking?
   ngưỡng đâu ra? thư viện chết thì sao? ai kiểm chứng con số thu tiền?) đều có câu
   trả lời là một *cơ chế* — commit tiền đăng ký, seed tái lập, holdback ngẫu nhiên —
   không phải một lời hứa.

### Tầm nhìn sản phẩm sau mùa thi

**Năm 1 — "Grammarly cho vận hành livestream":** nhà bán vừa (tổ trung control 1–3
người) mở LiveLift cạnh OBS; hệ thống gợi ý ghim/ưu đãi theo trạng thái phòng, và mỗi
gợi ý được *đo* thay vì *tin*. Gói Free (báo cáo sau phiên) → Pro 990k/tháng (đủ tính
năng, 1 phòng) → Agency 3,9M (nhiều phòng, so sánh chéo).

**Năm 2 — định giá bằng chính khoa học:** gói Performance thu % trên giá trị tăng thêm,
đo bằng **holdback ngẫu nhiên 10% khối** — cơ chế đo trùng với tầng ngoài của thí
nghiệm, nhà bán tự xem nhật ký holdback trong tài khoản. LiveLift là công cụ hiếm hoi
trên thị trường **tự chứng minh được giá trị của mình**; công cụ luật-ngưỡng không làm
được điều này.

**Dài hạn — tri thức vận hành ngành:** dữ liệu thí nghiệm tích lũy đa cửa hàng (ẩn
danh, đồng ý rõ ràng) trả lời những câu hỏi cả ngành đang đoán mò: khung giờ nào ghim
gì, nhịp ưu đãi bao lâu, chiến thuật nào chỉ là mê tín. Trở thành lớp đo lường chuẩn
cho live commerce Việt Nam — nơi mọi "kinh nghiệm" đều có thể truy về một thí nghiệm.

### La bàn khi phải đánh đổi

1. Đúng trước, đẹp sau — một con số sai được nói chắc chắn là thất bại tệ nhất.
2. Người bán là người dùng, không phải nhà thống kê — mọi kết luận phải đọc được
   trong 10 giây bằng tiếng Việt thường.
3. Minh bạch là moat — đối thủ có thể sao chép dashboard, khó sao chép niềm tin.
