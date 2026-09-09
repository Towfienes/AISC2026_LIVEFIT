# Chương trình nghiên cứu vòng 2 — 07/09/2026

*Quy trình: 6 nghiên cứu viên đọc phân công (62 reading note, mỗi paper: kết quả →
giả định → chuyển giao → gãy-ở-đâu-trong-bối-cảnh-LiveLift) → seminar 3 phản biện
độc lập (phương pháp luận / kỹ thuật / chiến lược thi; 34 đề xuất, 102 verdict) →
PI chốt agenda. Toàn văn: [`data/2026-09-07-*.json`](data/). Theo HARNESS §4:
phương pháp từ văn liệu phải qua research log trước khi vào code — file này là log đó.*

## Nguyên tắc chốt sau seminar

1. **Tuần này đóng băng feature** — quick wins chỉ nhận việc ngày-công phục vụ trực
   tiếp hồ sơ vòng 1 (14/09). Trượt vòng 1 thì 34 đề xuất thành giấy vụn.
2. **Capacity thật**: các đề xuất "trước khóa prereg" cộng ~14–16 tuần-công cho đội
   4 người — đã cắt còn 6 hạng mục; phần còn lại xếp làn sau.
3. **Một câu chuyện carryover duy nhất** (pilot hợp nhất → m̂ → quy tắc 5ph/10ph
   viết trước) — không 4 cơ chế rải 3 khu vực.
4. **Mọi propensity ước bằng redraw qua hàm gán production** — acceptance region
   ngày càng hẹp (rerandomization + arm-balance + transition), công thức đóng sai dần.
5. **5 điểm nhấn thi**, mọi kỹ thuật phải là bằng chứng cho một trong năm — không có
   điểm nhấn thứ 6: ① hóa đơn tự kiểm toán đến từng click · ② phòng điều khiển thống
   kê (replay + CS) · ③ Sim Validation Report một trang · ④ dataset intent livestream
   Việt đầu tiên · ⑤ quyết định ship có kiểm định (primary + guardrail NIM).
6. **Đòn bẩy lớn nhất không phải code**: một đối tác 200–500 khán giả giảm SE nhiều
   hơn toàn bộ CUPED + cv* cộng lại → một người làm BD track song song, và kịch bản
   demo 5 phút phải có bản thu dự phòng.

## Làn 1 — Quick wins (ngày-công, phục vụ hồ sơ vòng 1)

| # | Việc | Nguồn | Điểm chốt |
|---|---|---|---|
| Q1 | **Tiền đăng ký "click hợp lệ"** — GIVT-lite (UA bot regex, header prefetch, chỉ GET) + dedup refractory τ=10s (sens. {5,30,60}) + cap 5/hash/link/khối; **flag-don't-drop** (cột `is_valid`/`invalid_reason`, không xóa row); rule mù với assignment; primary = VALID clicks, raw = secondary | IAB Click 2009; Fabijan KDD'19; MRC IVT | Nguồn bias đơn lẻ lớn nhất của outcome công khai: 1 crawler burst ≈ nhân đôi CTR một khối ở 5–15 viewer. Gate sim: bias valid <10% khi raw >20% |
| Q2 | **Ràng buộc transition trong acceptance** — #cặp (1,1) ≥3 và (0,0) ≥3, lệch ≤1; đối xứng nên biên giữ 0.5; ~15 dòng trong `outer.py`; PHẢI vào trước phiên confirmatory đầu tiên | arXiv:2604.02489; 2602.23257 | Cứu CRT + τ̂₁ khỏi phiên degenerate; giảm 10–20% variance của sensitivity |
| Q3 | **Tách `assignment_event` / `exposure_event`** (append-only) + `design_hash` = SHA256(DesignParams∪seed) công bố trước phiên; compliance thành VIEW; ITT giữ nguyên | PlanOut WWW'14; Fabijan | Mở 3 khóa: exposure-weighting chính-xác-giây, audit trail, móng billing |
| Q4 | **Bảng MDE đơn hàng giải tích** (prior funnel 2,3% pv→mua từ Taobao UserBehavior, quét q2∈[0.15,0.5], nhãn "kịch bản"; CẤM map KuaiLive cho funnel) | Tianchi #649; LSEC | Nửa ngày trả lời "sao không đo đơn hàng?" bằng số: chỉ khả thi ở nhánh đối tác |
| Q5 | **SRM đợt 1** — integrity recount cross-pipeline + delivery exact-binomial trên tick (kỳ vọng = tỷ lệ ON/OFF từ schedule ĐÃ persist); tuyệt đối không SRM trên viewers/clicks (hậu-can-thiệp); fail = cờ phiên, không sửa dữ liệu | Fabijan KDD'19 | ~6% thí nghiệm Microsoft dính SRM; "chi-square sai dưới rerandomization, chúng tôi redraw exact" là mini-điểm-nhấn |

## Làn 2 — Trước khóa prereg (tuần 6) — 6 hạng mục, không hơn

| # | Việc | Nguồn | Điểm chốt |
|---|---|---|---|
| P1 | **Gói 4 knob sim đối kháng, thứ tự bắt buộc ICC→dwell→mẫu-số→share-shock**: frailty Gamma trên p_click (fit NB từ KuaiLive) + shock click cấp phiên (lưới ICC {0,.02,.05,.10}); dwell mixture bounce/engaged LogNormal; hazard rời phụ thuộc z(t) (mẫu số nội sinh) + true_effect đa-estimand; share-shock compound-Poisson (Hawkes chỉ nếu moment lệch >50%) | KuaiLive; SIGIR'10; YTLive 2510.24769 | FPR 4.5% hiện tại đo trên thế giới ICC≈0 — con số tự khen. Chạy lại TOÀN BỘ gate + đo lại MDE/CV trước khi chốt prereg |
| P2 | **Sim Validation Report một trang kiểu SBC** — ECDF-band Modrák + ~20 ô lưới lớn dần theo knob; thêm ô "hiệu ứng nhân tính vs Fisher CI cộng-hằng"; tự thẩm định bằng tiêm 3 lỗi biết trước; phân tầng per-PR/nightly/weekly; đóng băng cùng prereg | 2211.02383; 1804.06788 | Nâng từ "FPR 4.5% một thế giới" lên "uniform trên ~20 thế giới đối kháng" — artifact phản biện mạnh nhất, khung chấm CHUNG cho mọi đề xuất khác |
| P3 | **Mẫu số nội sinh**: p-value chính giữ RI exact (click lẫn exposure đều imputable dưới sharp null); CI qua linearization L_b = click_b − r̂₀·exposure_b (r̂₀ cố định qua redraw, ghi prereg); delta method Deng chỉ mô tả (K=18–31 vùng coverage lệch); gate ICS trên exposure_b; kết quả knob quyết định secondary outcome viewer-giây/khối | Deng 1803.06336; ICS 2510.01127 | Trả lời câu phản biện sắc nhất ("ghim giữ người xem thì mẫu số nhiễm"); SE sai cỡ 2× nếu làm naive |
| P4 | **CUPED đa biến v1 — chỉ hiệp biến tất định** (sin/cos giờ + spline phút-vào-phiên; RI giữ exact vì bất biến qua redraw); ridge, fold theo PHIÊN; lịch sử streamer lùi v2 khi ≥3 phiên; lag trong-phiên CẤM (hậu-can-thiệp); timebox 1 tuần | 2608.24038; 2606.27662 | Kỳ vọng 15–25% VR ⇒ MDE giảm ~8–13% — con số slide được; regime map nói n_cl<50 → CUPAC/ridge, KHÔNG DR |
| P5 | **Spec kiểm định chính + văn bản prereg mở rộng**: cài CẢ HAI statistic (khối-đều vs Hájek exposure-weighted), chọn MỘT LẦN bằng ngưỡng cv* đo trên pilot (phạt macro (1+cv²)); gatekeeping hierarchy cho >15 cờ; quy tắc loại phiên + Lee bounds; estimand compound treatment ("ON = pin dưới inner policy π, ĐÓNG BĂNG model suốt đợt"); danh sách guardrail + NIM; tách `estimators.py` → adjust/robust/carryover; commit hash code phân tích vào prereg | 2606.03012; Chung–Romano; 2402.11609 | Chọn sai phía cv* trả giá (1+cv²)≈2–3× phương sai; quyết định one-shot không sửa được sau khóa |
| P6 | **Giao thức pilot hợp nhất tuần 3** (4–6 phiên đo đồng thời 4 thứ): t_mix qua local-projection distributed-lag (bỏ positive-part truncation); m̂ theo Liu–Zhong Alg 2-3 (propensity section bằng redraw); cv* + within-CV; R² biến tiên lượng. **Quy tắc 5ph→10ph viết vào prereg TRƯỚC khi thấy số**, kèm operating characteristics đo trên sim (chọn 10ph ≥80% khi halflife ≥120s, ≤10% khi =0) | 2607.11694; Hu–Wager v4; 2602.23257 | Biến quyết định thiết kế lớn nhất còn lại thành thủ tục tiền đăng ký có OC — "không đội nào khác có" |

## Làn 3 — Trong chuỗi khẳng định (không chạm kiểm định chính)

- **C1 · PROTOCOL v1.0 gán nhãn**: SRS 10% + gold 300 câu 2-người-độc-lập, Krippendorff α tự viết (~100 dòng, không thêm dep) báo theo lớp kèm bootstrap CI; temperature=0+seed, 2 LLM khác nhà, hoán vị thứ tự lớp; audit 5% consensus, gate sai ≤5%; guideline semver + prompt_sha256 từng dòng. *(2604.09638; ViGoEmotions)*
- **C2 · Wild cluster bootstrap chuẩn MNW**: WCR-Rademacher B=9.999 (2^18≫B, không cần Webb), tự viết ~150 dòng numpy score-trick; cross-check CV3-jackknife; nếu 1–2 phiên đối tác chiếm >30% exposure → trọng tài là RI+CV3. **Cùng máy móc chạy guardrail non-inferiority** (ship ⟺ primary thắng AND ∀g cận-dưới-CI > −NIM; không tốn α, hiệu chỉnh β) → khối "ship decision" trên trang báo cáo. *(MNW 2205.03285; Spotify 2402.11609)*
- **C3 · Gói carryover sensitivity**: V̂_up (mẫu số chặn-trên Liu–Zhong, propensity bằng redraw) + cờ Hausman-RI τ̂₀−τ̂₁ studentized (chỉ là cờ, không gate) + CRT section r=2 **kích hoạt chỉ khi m̂≥1** (m̂=0 sạch → một dòng phụ lục, không tốn tuần công). *(2602.23257)*
- **C4 · OPE track**: gate `inner_replay` blocking trước mọi số OPE (bias<10%, coverage CS, **negative controls**: chứng minh DM thiên lệch xuống + Wald i.i.d. under-cover trên sim của TA); rồi `ope.py`: IPS w≤3 không clip, estimand ν̃_T, empirical-Bernstein CS, DR với r̂ predictable. *(Zhan 2106.02029; Waudby-Smith 2210.10768)*

## Làn 4 — Chung kết

- **F1 · "Phòng điều khiển thống kê"**: replay π_log/π_greedy/π_margin + dải CS của HIỆU hai policy; caveat C1–C4 in cứng; panel CS chỉ hiện SAU phiên/freeze (chống kênh feedback vào lời streamer); demo sân khấu chạy chế độ replay.
- **F2 · ViSoBERT fine-tune + ablation 4 dòng × 3 seed** (train Colab T4 free, infer CPU ONNX INT8); giữ hàng "consensus-only vs consensus+human"; dòng ViSoLex normalize kèm delta CI. Gate swap-in: hơn TF-IDF ≥5 điểm trên gold thật + p95 <50ms.
- **F3 · Công bố dataset — BƯỚC 0 NGAY TUẦN NÀY: kiểm ToS + search-traceability 50 câu**; mặc định phương án B (phát hành phần tự-stream, đối tác on-request); DATASHEET Gebru + PII re-audit trên file xuất (gate 0-hit trong CI) + split theo phiên + HF Croissant + Zenodo DOI + CC BY-NC-SA.
- **F4 · Holdback billing tự kiểm toán** *(điều kiện: event tables ≥5 phiên + đối tác ký)*: commitment seed (fallback offline là đường chính, NIST beacon tùy chọn) + ledger CSV ký số + `billing_audit.py` ngoài `src/` cho nhà bán tự recount; ghost-pins chỉ báo cáo kèm CI, KHÔNG lên hóa đơn.
- **F5 · MAD hóa inner tier — go/no-go bằng số** (regret sim <5%, coverage CS gộp-phiên đạt band — lý thuyết chỉ per-phiên, gộp phải chứng minh bằng gate, còn ≥6 tuần); prereg đợt mới, CẤM gộp outer hai đợt.
- **F6 · Giám sát e-process tối giản** (chỉ stream tick-delivery ~50 dòng; alert nhị phân, log niêm phong tới sau freeze; kích hoạt khi bắt đầu phiên đối tác).

## KHÔNG làm (đóng tranh luận)

| Đề xuất | Lý do |
|---|---|
| θ* power-optimal CUPED | Vô hình với giám khảo; plug-in nhiễu ăn hết gain ở cell 5–15 viewer. Mở lại chỉ khi CUPED v1 pass + macro share <20% |
| SRSB/P&G rerandomization tiên lượng | Đổi cơ chế gán giữa mùa = lớp rủi ro cao nhất repo; gain không lên slide. Chỉ khi pilot R²≥0.2 VÀ còn ≥4 tuần sau 5 điểm nhấn |
| Merge 6 phiếu self-consistency | Mâu thuẫn protocol temperature=0; tối ưu nội bộ giám khảo không thấy |
| Lớp nhãn CTA trên transcript | Phụ thuộc PhoWhisper chưa build; điểm nhấn thứ 6 không tồn tại |
| Hawkes đầy đủ + comment clustering | 2 tuần+ cho giá trị biên; 5–15 viewer thoái hóa về vài shock rời rạc |
| JA4 TLS fingerprint / SIVT | Đụng Caddy; in-app browser VN (Zalo/FB webview) → false positive giết click thật. GIVT-lite là sàn đủ |

## Danh sách đọc bắt buộc (xếp hạng)

1. **arXiv:2602.23257** Liu–Zhong — xương sống: V̂_up, CRT, m̂; ai đụng estimators đều phải đọc
2. **arXiv:2508.05633** KuaiLive — dùng được gì (hình dạng) vs CẤM gì (funnel, mức tuyệt đối)
3. **Fabijan KDD 2019** — SRM taxonomy; nguyên tắc "rule mù với assignment"
4. **arXiv:1803.06336** Deng — vì sao mẫu số nội sinh làm SE sai cỡ 2×
5. **arXiv:2606.03012** — phân rã S_res/S_macro, phạt (1+cv²), ngưỡng cv*
6. **arXiv:2608.24038** CUPED on Steroids — fold tôn trọng randomization
7. **arXiv:2209.00197 v4** Hu–Wager — b=(t_mix/2)·logT
8. **arXiv:2205.03285** MNW — vùng nguy hiểm G nhỏ/cluster lệch
9. **arXiv:2210.10768** — anytime-valid OPE, estimand ν̃
10. **arXiv:2106.02029** Zhan — DM thiên lệch xuống trên log bandit
11. **arXiv:2211.02383** Modrák — SBC ECDF-band cho Sim Validation Report
12. **IAB Click 2009 + arXiv:2402.11609** — valid click + guardrail không tốn α

## Điều seminar phát hiện mà cả 6 NCV bỏ sót (ghi để không quên)

- **Gatekeeping cấp câu chuyện**: >15 cờ/kiểm định mỗi cái α riêng → phải có hierarchy + quy tắc đọc khi mâu thuẫn (đã nhét vào P5).
- **Độ mịn phân phối RI dưới chồng ràng buộc**: đếm số lịch khả thi phân biệt được + p-value tối thiểu đạt được (validation của P5).
- **Fisher CI cộng-hằng vs lift nhân tính**: đo coverage dưới hiệu ứng nhân trong Sim Report (ô mới của P2).
- **Compound treatment**: "ON" = pin dưới policy π — phải đóng băng inner model suốt đợt confirmatory (P5).
- **Loại phiên là post-treatment selection**: cờ chất lượng có thể tương quan với randomization → bắt buộc sensitivity all-sessions + bounds (P5).
