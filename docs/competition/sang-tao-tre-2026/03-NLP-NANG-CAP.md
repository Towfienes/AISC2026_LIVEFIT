# 03 — CỨU PHÂN HỆ NLP: TỪ 0,211 LÊN 0,565 TRÊN CHAT THẬT

*Lập 14/09/2026 · phục vụ **MẪU 3 mục 5, 6, 7, 8, 9, 11** và **trọng tâm 4, 5, 6, 8***
*Mọi con số sinh lại được bằng một lệnh; lệnh ghi ở §10. Số gốc:
[`docs/benchmarks/intent-eval/results.json`](../../benchmarks/intent-eval/results.json).*

> **Một dòng:** bộ phân loại ý định của LiveLift từng đạt macro-F1 **0,870 trên 320 câu
> đội tự viết** nhưng chỉ **0,271 trên chat bán hàng thật** — thua baseline `return "khac"`.
> Tài liệu này dựng lại **khung đo trung thực trước**, đo lại con số cũ trên một tập test
> mới (**0,211**), rồi nâng lên **0,565** (KTC95 **0,491–0,649**) bằng ba thay đổi rẻ tiền:
> sửa bộ nhãn, gán nhãn dữ liệu thật bằng LLM, thêm đặc trưng "ai đang nói".
> **Hai cải tiến đã thử và KHÔNG hiệu quả cũng được báo cáo đủ số.**

---

## 1. KIỂM KÊ DỮ LIỆU — CÁI GÌ CÓ THẬT, CÁI GÌ KHÔNG

Trước khi cải tiến, phải biết mình có gì. Kết quả kiểm kê **không khớp hoàn toàn** với
những gì tài liệu cũ mô tả, và chỗ không khớp được ghi ra đây trước tiên.

### 1.1. Dữ liệu nhãn thật sự tồn tại trên đĩa

| Nguồn | Đường dẫn | Số dòng | Nhãn? | Vai trò trong tài liệu này |
|---|---|---:|---|---|
| Bộ **tự biên soạn** (bộ 6 lớp gốc) | `src/livelift/nlp/data/intent_dataset.jsonl` | **320** | có, 6 lớp | baseline tiền đăng ký, giữ nguyên |
| Bộ tự biên soạn **gán lại 11 lớp** ✨ | `src/livelift/nlp/data/intent_dataset_11.jsonl` | **320** | có, 11 lớp | **train** |
| Lô 1 — chat thật phiên `b519f75c` | `data/labeling/lot1-achan-b519f75c/comments_b519f75c.jsonl` | **6.586** | **KHÔNG** | nguồn để gán nhãn |
| Lô 1 — batch đã xuất đi gán nhãn | `.../batch.jsonl` + `strata.jsonl` | **1.800** | **KHÔNG** (trước 14/09) | — |
| Lô 1 — **nhãn LLM** ✨ | `.../train_llm.jsonl` | **1.800** | có, 11 lớp | **train** (kê khai §7) |
| Lô 2 — gán nhãn **TAY, mù**, 3 buổi live | `data/labeling/lot2-da-nguon-10-09/{to_label,gold}.txt` + `key.json` | **393** | có, 11 lớp | **TEST — không bao giờ train** |

✨ = tạo ra trong đợt làm việc 14/09/2026 này.

### 1.2. Ba chỗ tài liệu cũ nói khác thực tế

| Tài liệu cũ nói | Thực tế trên đĩa 14/09 | Hệ quả |
|---|---|---|
| *"Có lô ~1.800 nhãn đã xuất"* (`docs/benchmarks/intent-classifier.md`) | `batch.jsonl` có **1.800 dòng nhưng KHÔNG có nhãn**. Không tồn tại `a.jsonl` / `b.jsonl` / `consensus.jsonl` / `reviewed.jsonl` / `train_extra.jsonl`. Lô mới **xuất ra để đi gán**, chưa ai gán | Câu "đã xuất 1.800 nhãn" dễ bị đọc thành "đã có 1.800 nhãn". **Đã sửa bằng cách gán thật** (§7) |
| *"19.126 bình luận thật từ 16 buổi live"* (`FACT-SHEET.md`) | **Không nằm trên đĩa.** Store là in-memory; ảnh chụp hiện tại (`data/snapshot/livelift-store.json`) chỉ còn **757 bình luận của 16 phiên MÔ PHỎNG**. 19.126 bình luận thật **sinh lại được** từ VOD công khai bằng `scripts/live_fire_da_nguon.py nap`, nhưng **không phải là một tệp có sẵn** | Con số 19.126 vẫn đúng và kiểm chứng được, nhưng phải nói kèm *"sinh lại từ 16 VOD YouTube công khai"*, không được nói *"chúng tôi có một bộ dữ liệu 19.126 dòng"* |
| *"200 bình luận chat thật gán nhãn tay"* (nguồn của con số 0,271) | Tồn tại như **quy trình** (`random.Random(20260908).sample(comments, 200)` + nhãn tay), nhưng **file nhãn của 200 dòng ấy không được lưu**. Chỉ lô 2 (393 dòng, 10/09) còn đủ ba file ghép được | **Con số 0,271 không tái lập được từng dòng.** Vì vậy tài liệu này **đo lại từ đầu** trên lô 2 và công bố **0,211** làm số "TRƯỚC" chính thức |

> Điểm cuối cùng là điểm quan trọng nhất và nó bất lợi cho đội: **0,271 là một con số
> không còn kiểm chứng được đến từng dòng**. Đội không xoá nó khỏi tài liệu (nó phản ánh
> đúng một phép đo đã làm), nhưng từ nay mọi bảng dùng **0,211 ± KTC** — con số chạy lại
> được bằng lệnh trên dữ liệu còn nguyên vẹn.

### 1.3. Phân bố nhãn của tập TEST (393 dòng, người gán)

| Lớp | Số dòng | Tỷ lệ | | Lớp | Số dòng | Tỷ lệ |
|---|---:|---:|---|---|---:|---:|
| `khac` | 153 | 38,9% | | `van_chuyen` | 14 | 3,6% |
| `cam_on_khen` | 86 | 21,9% | | `hoi_gia` | 14 | 3,6% |
| `chao_hoi` | 42 | 10,7% | | `hoi_sanpham` | 11 | 2,8% |
| `chot_don` | 33 | 8,4% | | `che_dat` | 5 | 1,3% |
| `bao_gia_shop` | 32 | 8,1% | | `hoi_size` | 3 | 0,8% |
| | | | | **`hoi_daily`** | **0** | **0,0%** |

**Đọc bảng này là đã thấy nguyên nhân của 0,271:** hai lớp xã giao (`chao_hoi` +
`cam_on_khen`) chiếm **32,6%** chat thật và **không hề có trong bộ 6 lớp cũ**; `bao_gia_shop`
(shop tự dán bảng giá) chiếm thêm **8,1%**. Tức **hơn 40% chat thật** rơi vào những lớp mà
mô hình cũ *không có chỗ để đặt*, nên nó ép chúng vào 6 lớp ý định mua.

`hoi_daily` có **0 mẫu trong tập test** — nó vẫn nằm trong bộ nhãn vì lô LLM tìm được 40 mẫu
thật, nhưng **không có bất kỳ con số chất lượng nào cho lớp này**. Nói rõ ở §8.

### 1.4. Tỷ lệ nền ý định mua — con số quyết định mọi thứ

Đo trên **tầng ngẫu nhiên đơn giản** (mẫu không chệch), từng buổi live:

| Buổi live | Dòng gán nhãn | Tầng ngẫu nhiên | **Ý định mua THẬT** |
|---|---:|---:|---:|
| `1NMt8BChQrI` — "Vừa trả đơn vừa tâm sự" | 147 | 72 | **0/72 = 0,0%** |
| `gT0LDiBta2k` — Khai trương Achan Shop Tuyên Quang | 168 | 103 | **7/103 = 6,8%** |
| `47oGShxf80A` — Live Sale quần áo giá rẻ | 78 | 25 | **12/25 = 48,0%** |

Ba buổi, ba thế giới khác nhau. Đây là lý do **không tồn tại "một con số chính xác"** cho
radar ý định, và là lý do bảng kết quả dưới đây luôn in kèm cột **từng buổi**.

---

## 2. THIẾT KẾ ĐÁNH GIÁ — DỰNG TRƯỚC KHI CẢI TIẾN

Mã: `src/livelift/nlp/eval_intent.py`. Test khoá: `tests/test_nlp_eval_harness.py` (**39 test nhanh + 1 cổng `slow`**).

### 2.1. Năm quyết định, và lý do từng cái

**(a) Chia theo BUỔI LIVE, không theo dòng — `leave_one_session_out`.**
Bình luận trong một buổi không độc lập: cùng người bán, cùng mặt hàng, cùng bảng giá dán
lặp hàng chục lần. Chia ngẫu nhiên theo dòng sẽ để bản sao gần-trùng nằm cả hai phía và
thổi phồng điểm. Ở đây mỗi buổi lần lượt làm test, hai buổi kia làm train.

**(b) Rào chắn rò rỉ theo VĂN BẢN, chạy lại trước mỗi fold.**
Chia theo buổi *không* chặn được rò rỉ văn bản: cùng người bán dán cùng bảng giá ở nhiều
buổi, và `chào cả nhà` xuất hiện ở mọi buổi. Đo được: **9/345** văn bản gold duy nhất trùng
khít một dòng trong lô LLM. Khung loại mọi dòng train trùng khít dòng test và **đếm**:
**62 dòng bị loại** trong lần chạy công bố. Chín dòng không làm đổi kết quả — nhưng một
khung tự nhận là trung thực thì phải loại và đếm, chứ không đoán là chúng vô hại.

**(c) Nhãn TEST do NGƯỜI gán; nhãn TRAIN có thể do LLM gán.**
Nếu cả hai do cùng một LLM sinh thì điểm đo được là "mức đồng ý với LLM đó", không phải
độ chính xác. Lô người gán (3 buổi) **chỉ test**; lô LLM gán (buổi thứ tư) **chỉ train**.

**(d) macro-F1 lấy trung bình trên HỢP của nhãn thật và nhãn dự đoán.**
Đây là mặc định của `sklearn.f1_score(average="macro")` và là đúng quy ước đã sinh ra con
số 0,271: lớp mà mô hình **bịa ra** nhưng không tồn tại trong nhãn thật vẫn nhận F1 = 0 và
được tính vào trung bình. Bịa lớp phải bị phạt. Cột `macro-F1 (chỉ lớp có nhãn thật)` in
kèm để thấy khoảng cách giữa hai quy ước. Test `test_macro_f1_matches_sklearn_default_convention`
khoá công thức này lại.

**(e) Hai tầng test đọc hai câu hỏi khác nhau — và không được trộn.**

| Tầng | n | Cách rút | Trả lời được câu hỏi |
|---|---:|---|---|
| `random` (set B) | **200** | ngẫu nhiên đơn giản | *"Chạy thật thì đúng bao nhiêu?"* — **đây là con số vận hành** |
| `predicted` (set A) | **193** | tối đa 15 dòng / lớp mô hình CŨ dự đoán | *"Khi nó kêu, nó đúng bao nhiêu?"* — đo precision, giàu lớp hành động một cách nhân tạo |

Mọi bảng in cả hai. Ai trích một con số mà không nói tầng nào là trích sai.

### 2.2. Chỉ số

- **macro-F1** (quy ước (d)) + **F1 từng lớp** + **ma trận nhầm lẫn**.
- **KTC95 bootstrap percentile** cho macro-F1 (2.000 lần lấy lại mẫu, seed 2026).
  ⚠️ Bootstrap lấy lại mẫu theo **dòng** nên chỉ phản ánh bất định do cỡ mẫu. Bất định thật
  lớn hơn: đơn vị lấy mẫu thật sự là **buổi live**. Ba buổi thì bootstrap theo cụm vô nghĩa,
  nên bảng in thẳng **macro-F1 từng buổi**.
- **Precision nhãn hành động** (5 lớp `hoi_gia/hoi_size/che_dat/chot_don/van_chuyen`) + **KTC95
  Wilson**. Đây là chỉ số sát sản phẩm nhất: trong mọi lần hệ thống nói *"có khách đang hỏi
  giá"*, bao nhiêu lần là thật. Nhầm `chao_hoi` thành `cam_on_khen` không làm ai mất đơn;
  gắn nhầm `chot_don` thì trung control đuổi theo một khách không tồn tại.

---

## 3. BẢNG BASELINE — BA BASELINE BẮT BUỘC + ARTIFACT ĐANG CHẠY

Test = 393 dòng người gán, gộp từ ba fold leave-one-session-out.

| # | Hệ thống | macro-F1 (393) | KTC95 | Accuracy | Precision nhãn hành động | macro-F1 tầng **ngẫu nhiên** (200) |
|---|---|---:|---|---:|---:|---:|
| **B0** | Luôn đoán lớp đa số `khac` | 0,056 | [0,051; 0,063] | 0,389 | — (0 dự đoán) | 0,078 [0,070; 0,099] |
| **B1** | Từ khoá (tiền đăng ký, `classify_keywords`) | 0,146 | [0,109; 0,180] | 0,387 | 20,9% (18/86) | 0,178 [0,086; 0,246] |
| **B2** | **TF-IDF+LogReg ĐANG CHẠY** (`intent_clf.joblib`, abstain 0,45) | **0,211** | **[0,172; 0,247]** | 0,338 | **23,0%** (54/235) | **0,208 [0,095; 0,286]** |
| **B3** | TF-IDF+LogReg train lại trên 320 câu biên soạn, bộ 6 lớp | 0,199 | [0,163; 0,234] | 0,303 | 21,9% (57/260) | 0,163 [0,089; 0,227] |

**macro-F1 từng buổi live** (cột này là bất định thật):

| Hệ thống | `1NMt8BChQrI` (0% ý định mua) | `gT0LDiBta2k` (6,8%) | `47oGShxf80A` (48%) |
|---|---:|---:|---:|
| B0 · luôn đoán `khac` | 0,107 | 0,065 | 0,030 |
| B1 · từ khoá | 0,081 | 0,170 | 0,162 |
| B2 · **đang chạy** | **0,064** | **0,138** | **0,412** |
| B3 · biên soạn 6 lớp | 0,054 | 0,133 | 0,409 |

Mô hình đang chạy **thua baseline tầm thường ở buổi không có ai mua** (0,064 so với
0,107) và chỉ thắng rõ ở buổi mà **gần một nửa** chat là ý định mua. Đó không phải
một mô hình phân loại ý định — đó là một mô hình đoán rằng ai cũng đang mua hàng.

**Đọc bảng:**

1. **"0,271 ± bao nhiêu?"** — câu hỏi giám khảo chắc chắn hỏi — nay có đáp án:
   trên tập test còn kiểm chứng được, mô hình đang chạy đạt **0,211, KTC95 [0,172; 0,247]**.
   Trên riêng tầng ngẫu nhiên 200 dòng: **0,208, KTC95 [0,095; 0,286]** — khoảng rộng gấp
   đôi, đúng như cỡ mẫu 200 cho phép nói.
2. **Accuracy của B2 (0,338) THẤP HƠN B0 (0,389).** Mô hình đã huấn luyện thua một hàm
   `return "khac"` về accuracy. Nó chỉ hơn ở macro-F1, và hơn vì lý do buồn: nó *có* bắt
   được `hoi_gia` đôi khi, còn B0 thì không bao giờ.
3. **B3 ≈ B2.** Ngưỡng abstain 0,45 chỉ mua thêm 0,012 macro-F1. Vấn đề không nằm ở ngưỡng.

---

## 4. BẢNG TRƯỚC/SAU

| # | Hệ thống | macro-F1 (393) | KTC95 | Accuracy | Precision hành động | macro-F1 tầng ngẫu nhiên | Precision hành động, tầng ngẫu nhiên |
|---|---|---:|---|---:|---:|---:|---:|
| B2 | **TRƯỚC** — artifact đang chạy | 0,211 | [0,172; 0,247] | 0,338 | 23,0% (54/235) | 0,208 | 21,4% (9/42) |
| C1 | Bộ nhãn 11 lớp + bộ biên soạn gán lại + gold 2 buổi | 0,557 | [0,487; 0,614] | 0,608 | 46,2% (43/93) | 0,451 | 36,0% (9/25) |
| **C2** | **SAU** — C1 + 1.800 nhãn LLM trên buổi thứ tư | **0,565** | **[0,491; 0,649]** | **0,741** | **66,7%** (40/60) | **0,519** | **66,7%** (6/9) |
| C3 | C2 + từ chối trả lời, ngưỡng chọn **trong tập train** | 0,492 | [0,440; 0,562] | 0,713 | 65,2% (30/46) | 0,541 | 83,3% (5/6) |

**Chênh lệch công bố: macro-F1 0,211 → 0,565 (+0,354).** KTC95 của hai bên **không chồng
lấn** ([0,172; 0,247] so với [0,491; 0,649]), nên chênh lệch này không phải nhiễu cỡ mẫu.
Accuracy 0,338 → 0,741, đồng thời **vượt luôn baseline tầm thường** (0,389) — điều mô hình
cũ không làm được. Precision nhãn hành động **23,0% → 66,7%**.

**F1 từng lớp của C2** (so với bộ 6 lớp cũ, nơi bốn lớp có F1 = 0 trên chat thật):

| Lớp | P | R | **F1** | Nhãn thật | Lần dự đoán | | Lớp | P | R | **F1** | Nhãn thật | Lần dự đoán |
|---|---:|---:|---:|---:|---:|---|---|---:|---:|---:|---:|---:|
| `hoi_gia` | 0,812 | 0,929 | **0,867** | 14 | 16 | | `chao_hoi` | 0,909 | 0,952 | **0,930** | 42 | 44 |
| `hoi_size` | 0,333 | 0,667 | **0,444** | 3 | 6 | | `cam_on_khen` | 0,713 | 0,837 | **0,770** | 86 | 101 |
| `che_dat` | 0,167 | 0,200 | **0,182** | 5 | 6 | | `hoi_sanpham` | 0,333 | 0,182 | **0,235** | 11 | 6 |
| `chot_don` | 0,833 | 0,455 | **0,588** | 33 | 18 | | `hoi_daily` | 0,000 | — | **0,000** | **0** | 2 |
| `van_chuyen` | 0,643 | 0,643 | **0,643** | 14 | 14 | | `bao_gia_shop` | 0,812 | 0,812 | **0,812** | 32 | 32 |
| | | | | | | | `khac` | 0,750 | 0,726 | **0,738** | 153 | 148 |

**macro-F1 từng buổi live của C2 — và đây là chỗ phải trung thực:**

| Buổi live | macro-F1 | Accuracy | Precision hành động | Tỷ lệ nền ý định mua |
|---|---:|---:|---:|---:|
| `1NMt8BChQrI` | 0,372 | 0,776 | **0,0% (0/11)** | **0,0%** |
| `gT0LDiBta2k` | 0,525 | 0,762 | 75,0% (6/8) | 6,8% |
| `47oGShxf80A` | 0,635 | 0,628 | 82,9% (34/41) | 48,0% |

**Bệnh gốc CHƯA khỏi.** Precision nhãn hành động vẫn đi theo **tỷ lệ nền của buổi**, đúng
như phát hiện 10/09: ở buổi không có ai mua, mô hình mới vẫn gắn 11 nhãn hành động và
**sai cả 11**. Cái đã cải thiện là *quy mô sai*: mô hình cũ gắn **235** nhãn hành động trên
cùng tập test, mô hình mới gắn **60** — bớt được **74%** cảnh báo giả trong khi bắt được
nhiều ca đúng hơn.

---

## 5. BẢNG ABLATION — ĐÓNG GÓP TỪNG THÀNH PHẦN (MẪU 3 mục 9)

Mỗi dòng tắt **đúng một** thành phần so với cấu hình đầy đủ A0. Hai dòng cuối so bộ nhãn,
nên phải chấm trên **cùng không gian nhãn 6 lớp** (so macro-F1 trên 6 lớp với macro-F1 trên
10 lớp là so hai cái thang khác nhau).

| # | Cấu hình | macro-F1 (393) | Δ so với A0 | Accuracy | Precision hành động | macro-F1 tầng ngẫu nhiên |
|---|---|---:|---:|---:|---:|---:|
| **A0** | **Đầy đủ** (chuẩn hoá + phong cách + 11 lớp + mọi nguồn) | **0,565** | — | 0,741 | 66,7% | 0,519 |
| A1 | − chuẩn hoá văn bản (NFKC/teencode/emoji) | 0,564 | **−0,001** | 0,735 | 68,4% | 0,500 |
| A2 | − đặc trưng phong cách (caps / mốc giá / `‖`) | 0,576 | **+0,011** | 0,735 | 64,3% | 0,545 |
| A3 | − 1.800 nhãn LLM buổi thứ tư | 0,557 | **−0,008** | **0,608** | **46,2%** | 0,451 |
| A4 | − bộ biên soạn (chỉ dữ liệu thật) | **0,365** | **−0,200** | 0,677 | 87,5% (7/8) | 0,331 |
| A5 | − gold 2 buổi trong train (chỉ biên soạn + LLM) | 0,582 | **+0,017** | 0,730 | 71,0% | 0,429 |
| A6 | + từ chối trả lời (ngưỡng chọn trong train) | 0,492 | **−0,073** | 0,713 | 65,2% | **0,541** |
| A7 | **Bộ nhãn 6 lớp** (chấm trên không gian 6 lớp) | 0,574 | — | 0,850 | 54,8% | 0,455 |
| A8 | **Bộ nhãn 11 lớp**, gộp về 6 khi chấm (cùng thang A7) | **0,609** | **+0,035 vs A7** | **0,880** | **66,7%** | 0,626 |

### Đọc bảng ablation — kể cả những dòng bất lợi

**Cái hiệu quả:**

- **Bộ biên soạn là xương sống (A4: −0,200).** Bỏ 320 câu tự viết, macro-F1 sập gần một
  nửa. Lý do rõ ràng và đo được: nó là **nguồn duy nhất** dạy được `hoi_size` (50 mẫu),
  `che_dat` (50) và phần lớn `chot_don`/`van_chuyen` — chat thật của ba buổi này quá thưa
  ý định mua để dạy nổi. Precision hành động của A4 lên 87,5% chỉ vì nó gần như **không
  dám dự đoán gì** (8 dự đoán trên 393 dòng): đó là precision của sự im lặng.
- **Bộ nhãn 11 lớp thắng bộ 6 lớp trên chính thang đo của bộ 6 lớp (A8 vs A7: +0,035
  macro-F1, +0,030 accuracy, +11,9 điểm precision hành động).** Đây là bằng chứng
  quan trọng nhất của cả tài liệu: thêm lớp không chỉ giúp mô tả chat thật đầy đủ hơn —
  nó **làm mô hình bớt sai ngay trên bài toán cũ**, vì `chào cả nhà` cuối cùng cũng có
  một chỗ để đi thay vì bị ép thành `chot_don`.
- **1.800 nhãn LLM đổi cả hành vi sản phẩm (A3).** macro-F1 gần như không đổi (−0,008,
  nằm sâu trong nhiễu), nhưng **accuracy 0,608 → 0,741** và **precision hành động 46,2% →
  66,7%**, số nhãn hành động phát ra giảm 93 → 60. Lô này dạy mô hình *chat thật trông
  như thế nào*, và nó là nguồn duy nhất có `hoi_daily` (40 mẫu) và `bao_gia_shop` (33).

**Cái KHÔNG hiệu quả — báo cáo đủ số:**

- **Chuẩn hoá văn bản: −0,001. Bằng không.** Module `normalize.py` (NFKC, teencode, gom ký
  tự kéo dài, tách emoji) tốn một buổi viết và **không mua được gì đo được**. Giả thuyết
  giải thích: TF-IDF **char 2–5-gram** vốn đã dung sai với mất dấu và teencode — đó chính
  là lý do kiến trúc này được chọn từ đầu — nên chuẩn hoá làm lại một việc đã xong. Module
  được giữ lại vì nó có ích cho mô hình có tokenizer (ViSoBERT, xem §8), **không phải vì
  nó cải thiện mô hình hiện tại**.
- **Đặc trưng phong cách: −0,011 (tức TẮT nó thì TỐT HƠN).** Chín đặc trưng "ai đang nói"
  (tỷ lệ viết hoa, số mốc giá, dấu `‖`) **làm giảm** macro-F1, dù chúng nâng precision hành
  động 64,3% → 66,7% và giúp `bao_gia_shop` đạt F1 0,812. Đọc đúng: chúng giúp đúng cái
  chúng được thiết kế để giúp (tách bảng giá shop khỏi khách hỏi giá) và **trả giá ở chỗ
  khác** — 9 đặc trưng số dày đặc cạnh hàng vạn đặc trưng TF-IDF thưa sẽ hút trọng số.
  Chênh lệch nằm gọn trong KTC nên **không được tuyên bố là có hại**; đúng mực là:
  *chưa chứng minh được lợi ích trên macro-F1*.
- **Gold 2 buổi trong tập train: +0,017 khi BỎ ĐI (A5).** Nhãn người gán của hai buổi khác
  **không giúp** mô hình đoán buổi thứ ba — thậm chí hơi hại. Với 3 buổi thì đây chưa phải
  kết luận, nhưng nó là cảnh báo thẳng: **dữ liệu thật của buổi này không tự động chuyển
  giao sang buổi khác**, và chiến lược "cứ gán thêm nhãn là tốt lên" có thể sai.

---

## 6. TUỲ CHỌN TỪ CHỐI TRẢ LỜI — TRỌNG TÂM 8 "KIỂM SOÁT ĐẦU RA"

### 6.1. Thực đơn điểm vận hành (đường cong độ phủ ↔ độ chính xác)

| Ngưỡng tự tin | macro-F1 | Accuracy | Độ phủ nhãn hành động | **Precision hành động** | KTC95 Wilson |
|---:|---:|---:|---:|---:|---|
| 0,00 (không từ chối) | 0,565 | 0,741 | 15,3% | 66,7% | [0,541; 0,773] |
| 0,40 | 0,587 | 0,741 | 13,2% | 75,0% | [0,618; 0,848] |
| 0,45 *(ngưỡng sản phẩm hiện tại)* | 0,560 | 0,741 | 12,0% | 74,5% | [0,605; 0,848] |
| 0,60 | 0,577 | 0,730 | 8,4% | **87,9%** | [0,727; 0,952] |
| 0,70 | 0,546 | 0,700 | 7,6% | **90,0%** | [0,744; 0,965] |
| 0,80 | 0,488 | 0,674 | 5,6% | 90,9% | [0,722; 0,975] |

Bảng này là **thực đơn**, không phải kết quả đã thẩm định: chọn điểm đẹp nhất trên đây rồi
công bố nó chính là gọt tham số theo tập test.

### 6.2. Thí nghiệm trung thực: chọn ngưỡng mà KHÔNG nhìn test

Khung tự chọn ngưỡng bằng **leave-one-session-out lồng bên trong tập train** (quy tắc định
trước: ngưỡng **thấp nhất** đạt precision hành động ≥ 0,70 trên buổi được giữ lại trong nội
bộ train). Ngưỡng chọn được ở ba fold: **0,00 · 0,65 · 0,00**.

Kết quả (dòng C3/A6):

| Đo trên | macro-F1 | Precision hành động |
|---|---:|---:|
| Cả 393 dòng | **0,492** (từ 0,565 — **tệ đi 0,073**) | 65,2% (từ 66,7% — tệ đi) |
| Riêng tầng ngẫu nhiên 200 dòng | **0,541** (từ 0,519 — **tốt lên 0,022**) | **83,3%** (5/6, từ 66,7%) |

**Kết luận trung thực: hiệu chuẩn ngưỡng KHÔNG chuyển giao ổn định giữa các buổi live.**
Hai trong ba fold chọn ngưỡng 0,00 (tức "đừng từ chối gì cả") vì buổi dùng để hiệu chuẩn đã
đạt yêu cầu precision sẵn; fold còn lại chọn 0,65 và bóp recall của buổi thứ ba. Trên phân
phối vận hành thật (tầng ngẫu nhiên) abstain có vẻ giúp — nhưng mẫu chỉ còn **6 dự đoán
hành động**, KTC95 Wilson của 5/6 là **[0,436; 0,972]**, rộng đến mức không kết luận được gì.

**Khuyến nghị vận hành (nêu rõ là lựa chọn sản phẩm, không phải kết quả thí nghiệm):** giữ
ngưỡng **0,45** như hiện tại và bổ sung **hai lớp kiểm soát đầu ra không dựa vào ngưỡng**:

1. **Chặn theo tỷ lệ nền:** nếu trong 5 phút gần nhất tỷ lệ nhãn hành động vượt ngưỡng
   hợp lý của buổi (đo được từ chính buổi đó), **tắt radar** thay vì đẩy cảnh báo giả.
   Đây là biện pháp đúng cơ chế lỗi, vì cơ chế lỗi là tỷ lệ nền chứ không phải độ tự tin.
2. **Nhãn hiển thị luôn kèm nguồn gốc:** thẻ gợi ý phải ghi "mô hình · độ tin cậy X" và
   **không bao giờ hiện khoảng tin cậy** (quy tắc chống overclaim cấp giao diện đã có gate
   `test_web_*`). Radar ý định **không nằm trong ước lượng nhân quả** —
   `analysis/estimators.py` không đọc `intent_label`, và điều đó không đổi.

---

## 7. GÁN NHÃN BẰNG LLM — KÊ KHAI THEO ĐIỀU 5

> **Khối này phải được chép nguyên văn vào [`05-BAN-KE-KHAI.md`](05-BAN-KE-KHAI.md) mục
> "dữ liệu do AI hỗ trợ tạo ra".** Điều 5 §5–6 cho phép dùng LLM **nếu kê khai trung thực**;
> §7 cấm che giấu nguồn dataset.

| Hạng mục | Kê khai |
|---|---|
| **Việc AI làm** | Gán nhãn 11 lớp cho **1.800 bình luận thật** của phiên `b519f75c` (lô 1), tạo `data/labeling/lot1-achan-b519f75c/train_llm.jsonl` |
| **Mô hình** | Claude (Anthropic), truy cập qua Claude Code — cùng công cụ đã kê khai ở §I.1 của `05-BAN-KE-KHAI.md` |
| **Đầu vào** | `batch.jsonl` (1.800 dòng, đã lọc PII ở tầng ingest) + guideline 11 lớp trong `src/livelift/nlp/labels.py` |
| **Đội làm gì** | Viết guideline; rút mẫu hai tầng có seed (`--random-fraction 0.10 --seed 2026`); định nghĩa quy ước cho ca mơ hồ; hợp nhất và kiểm tra phân bố; **quyết định lô này CHỈ dùng để train, không bao giờ để test** |
| **Dùng vào đâu** | **Chỉ làm dữ liệu huấn luyện.** Không một con số đánh giá nào trong tài liệu này đo trên nhãn do AI sinh |
| **Phân bố nhãn sinh ra** | `khac` 1.149 · `cam_on_khen` 382 · `chao_hoi` 173 · `hoi_daily` 40 · `bao_gia_shop` 33 · `hoi_sanpham` 18 · `van_chuyen` 3 · `chot_don` 1 · `hoi_gia` 1 · `hoi_size` 0 · `che_dat` 0 |
| ⚠️ **Hạn chế 1 — một mô hình, không đồng thuận** | Quy trình thiết kế sẵn trong `label_llm.py` là **2 LLM độc lập + người duyệt bất đồng**. Lô này chỉ chạy **một** mô hình, **không có người duyệt**. Không đo được κ giữa người gán |
| ⚠️ **Hạn chế 2 — hiệu chuẩn quy ước từ tập test** | Người/AI gán nhãn lô 1 đã **đọc nhãn của lô 2** để thống nhất quy ước (ví dụ: tiếng cười `Kkkk` → `cam_on_khen`, spam chữ số → `khac`). Đây là *hiệu chuẩn hướng dẫn gán nhãn*, hợp lệ và thông thường, nhưng nó khiến **mọi lợi ích đo được của lô LLM đều mang thiên lệch lạc quan**. Không thể báo cáo một con số đồng thuận LLM–người không chệch từ lô này; muốn có thì phải gán một lô người **mới** |
| ⚠️ **Hạn chế 3 — lô nghèo ý định mua** | Phiên `b519f75c` là "mega live tâm sự": chỉ **1** dòng `hoi_gia`, **1** `chot_don`, **0** `hoi_size`, **0** `che_dat` trong 1.800 dòng. Lô này dạy được xã giao và bảng giá shop, **không dạy được ý định mua** |

**Kê khai thêm cho lần làm việc này:** bộ 320 câu biên soạn được **gán lại nhãn** sang bộ
11 lớp (42/60 dòng `khac` đổi lớp) bằng `scripts/gan_lai_nhan_11.py`. Bảng gán lại nằm
**trong mã nguồn**, review được từng dòng, và test `test_relabel_table_is_reproducible_from_the_script`
bắt buộc file dữ liệu phải là kết quả của bảng đó. Đây là **trả món nợ** đã tự ghi sổ ở
`docs/benchmarks/intent-classifier.md` §"Nợ bắt buộc trả trước khi huấn luyện lại".

---

## 8. PHÂN TÍCH LỖI — VÍ DỤ CÂU THẬT (ĐÃ LỌC PII)

Sinh bằng `python -m livelift.nlp.eval_intent --errors <file>`. Bình luận đã qua bộ lọc PII
ở tầng ingest (`[TÊN]`, `[ĐỊA CHỈ]`, `[SĐT]`, `[MXH]`).

### 8.1. Sáu cơ chế sai, mỗi cơ chế một câu thật

| # | Ô nhầm lẫn | Câu THẬT | Cơ chế |
|---|---|---|---|
| **1** | `cam_on_khen` → `hoi_size` | **`Hay`** (4 lần, cả 4 sai) | **Đa nghĩa tiếng Việt.** `hay` = "thú vị" (khen) trùng mặt chữ với `hay` = "hoặc" trong câu hỏi cỡ (`L hay XL ạ`, `form chuẩn hay lớn hơn 1 size`). Bộ biên soạn có 50 câu `hoi_size` chứa `hay` với nghĩa "hoặc"; chat thật có `Hay` một mình với nghĩa khen. Char n-gram không phân biệt được |
| **2** | `bao_gia_shop` → `che_dat` | **`Achan Shop đang có bưởi. Mời cả nhà mua ủng hộ ạ (giảm giá 5%)`** (3 lần) | **Đa nghĩa "giảm giá".** Shop nói `giảm giá 5%` (khuyến mãi) trùng mặt chữ với khách nói `giảm giá đi shop` (trả giá). Đặc trưng `is_shouted_pricesheet` không bắt được vì câu này viết thường, chỉ 1 mốc giá |
| **3** | `chot_don` → `khac` (14/33) | **`mã15 khăn 3 cái`** · **`mả 3 2 hủ`** · **`giỏ đi chợ 1c`** · **`ma4chao vàng 4c`** | **Quy ước đặt hàng riêng của từng shop.** Buổi bán quần áo chốt đơn bằng *mã sản phẩm + số lượng*, không có một chữ nào trong 11 từ khoá `chot_don`. Đây là lỗi làm hỏng recall nhiều nhất (0,455) và **không sửa được bằng thêm dữ liệu chung** — phải học từ chính buổi đó |
| **4** | `chot_don` → `bao_gia_shop` | **`1cay son m18 gia 19k`** · **`1 cái chảo nửa 19 k 24310 khách củ`** | **Đặc trưng phong cách phản chủ.** Khách chốt đơn có nhắc giá → khớp mẫu "có mốc giá" của bảng giá shop. Cùng đặc trưng cứu được `bao_gia_shop` (F1 0,812) thì làm hỏng `chot_don` |
| **5** | `khac` → `van_chuyen` | **`Em ship toàn quốc`** · **`Đơn e đi hơi chậm hàng nhiều nên nhận lâu chị đợi hàng dùm em nha`** | **Vẫn là mô hình người nói.** Hai câu này do **shop** nói (trả lời khách), không phải khách hỏi. Guideline nói rõ "ai đang nói quyết định nhãn" nhưng mô hình không có bất kỳ tín hiệu tác giả nào — nền tảng không trả về vai trò mod cho replay |
| **6** | `hoi_sanpham` → `khac` (6/11) | **`có túi`** · **`vai gi em`** · **`bi hen suyên uong đuoc`** | **Câu quá ngắn, sai chính tả nặng.** 2–4 token, không dấu, thiếu chủ ngữ. Không có đặc trưng nào đủ tín hiệu |

### 8.2. Lỗi nào đã KHỎI so với mô hình cũ

| Lỗi 08/09 | Trạng thái 14/09 |
|---|---|
| Lời chào bị gán `chot_don` (lỗi số 1 đo được) | **Khỏi.** `chao_hoi` F1 **0,930**, chỉ 2/42 lời chào bị nhầm — và nhầm sang `cam_on_khen`, vô hại |
| Bảng giá mod dán bị tính là khách hỏi giá | **Khỏi phần lớn.** `bao_gia_shop` F1 **0,812**; chỉ 1/32 bảng giá còn bị gọi là `hoi_gia` |
| `hoi_gia` sai 80% (6/30 đúng, 08/09) | **Khỏi.** `hoi_gia` precision **0,812**, recall 0,929, F1 **0,867** |
| `hoi_size` sai 100% (0/16, 08/09) | **Đỡ nhưng chưa khỏi.** F1 0,444 trên **3 mẫu thật** — cỡ mẫu quá nhỏ để nói gì chắc chắn |

---

## 9. HẠN CHẾ CÒN LẠI — NÓI TRƯỚC KHI GIÁM KHẢO HỎI

1. **Ba buổi live là ba buổi, không phải một mẫu.** Toàn bộ kết luận đứng trên
   `n_session = 3`. KTC bootstrap in trong mọi bảng là **KTC theo dòng** và **hẹp hơn sự
   thật**; bất định thật nằm ở cấp buổi, nơi macro-F1 đi từ 0,372 đến 0,635. Ba buổi thì
   không bootstrap theo cụm được. Cần ≥ 10 buổi mới nói được "mô hình đạt X".
2. **Một người gán nhãn, không có κ.** Lô 2 do một người gán, không đo được đồng thuận
   giữa người gán. Quy tắc định trước cho ca mơ hồ là **chọn lớp hành động** ⇒ mọi con số
   precision là **cận trên có lợi cho mô hình**.
3. **Rò rỉ theo người bán.** Ba buổi test và buổi train LLM **cùng một nhà bán** (hệ thống
   Achan Shop) ở 3/4 phiên. Bảng giá, cách nói, tên sản phẩm lặp lại. Rào chắn trùng khít
   văn bản loại được 62 dòng, nhưng **không loại được trùng phong cách**. Con số 0,565
   gần như chắc chắn **lạc quan** khi áp sang một nhà bán mới.
4. **Thiên lệch hiệu chuẩn quy ước gán nhãn** (§7, hạn chế 2) — lợi ích của lô LLM đo được
   trong điều kiện có lợi.
5. **`hoi_daily` không có số.** 0 mẫu trong test, 40 mẫu trong train, mô hình phát ra 2 dự
   đoán và cả 2 sai. Lớp này **chưa được thẩm định** và phải nói như vậy.
6. **`che_dat` và `hoi_sanpham` vẫn hỏng** (F1 0,182 và 0,235). `che_dat` có 5 nhãn thật
   trong 393 dòng — không đủ để huấn luyện hay để đánh giá.
7. **Chưa fine-tune ViSoBERT.** Đã kiểm tra môi trường trước khi hứa:
   `torch` **chưa cài**, `transformers` **chưa cài**, `torch.cuda.is_available()` **không
   gọi được** vì không có torch. Máy Windows này **chưa xác nhận có GPU**. Fine-tune
   ViSoBERT trên CPU với ~2,5k mẫu là khả thi về thời gian (vài chục phút/epoch) nhưng đòi
   cài ~2,5 GB phụ thuộc và **một đường mạng ổn định để tải trọng số** — hai thứ không đảm
   bảo được trong 5 ngày còn lại, và một artifact 500 MB không hợp với ràng buộc vận hành
   hiện tại (suy luận < 1 ms/bình luận, artifact 86 KB, không cần torch). **Quyết định:
   không hứa ViSoBERT trong hồ sơ vòng 1.** Module `normalize.py` được giữ lại chính vì
   nó là bước chuẩn bị đúng cho tokenizer của ViSoBERT, dù nó không giúp TF-IDF.
8. **Tăng gấp đôi kích thước artifact.** `intent_clf_v2.joblib` ≈ **925 KB** so với 86 KB
   (từ vựng char n-gram lớn hơn 8 lần vì có dữ liệu thật). Vẫn nạp được trong < 1 s, vẫn
   không cần torch, nhưng con số phải được ghi đúng ở mọi nơi.

---

## 10. LỆNH TÁI TẠO — TOÀN BỘ

```bash
cd d:/AISC2026/livelift

# 0. Cổng chất lượng TRƯỚC khi đụng vào gì (phải xanh)
.venv/Scripts/python -m pytest -m "not slow" -q

# 1. Trả nợ nhãn: gán lại bộ biên soạn 6 lớp -> 11 lớp (tất định)
.venv/Scripts/python scripts/gan_lai_nhan_11.py
#    -> src/livelift/nlp/data/intent_dataset_11.jsonl (320 dòng, 42 dòng đổi lớp)

# 2. Lô nhãn thật (ngoài git theo chính sách PII — sinh lại theo
#    data/labeling/README.md; lô LLM là data/labeling/lot1-achan-b519f75c/train_llm.jsonl)

# 3. Toàn bộ bảng của tài liệu này, MỘT lệnh (~8 phút trên CPU)
.venv/Scripts/python -m livelift.nlp.eval_intent --ablation --coverage --save-model
#    -> docs/benchmarks/intent-eval/results.json   (số gốc, đủ ma trận nhầm lẫn)
#    -> docs/benchmarks/intent-eval/results.md     (bảng Markdown tự sinh)
#    -> src/livelift/nlp/model/intent_clf_v2.joblib + .meta.json

# 4. Ví dụ lỗi thật của §8 (ghi ra ngoài repo — file chứa bình luận người dùng)
.venv/Scripts/python -m livelift.nlp.eval_intent --errors ../loi-intent.md

# 5. Cổng chất lượng SAU
.venv/Scripts/python -m pytest -m "not slow" -q
.venv/Scripts/python -m pytest -m slow -q tests/test_nlp_eval_harness.py
.venv/Scripts/python -m ruff check src tests scripts
```

**Seed cố định ở mọi bước:** rút mẫu `2026`, bootstrap `2026`, `LogisticRegression` `2026`,
lô 2 `SEED_A=20260910` / `SEED_B=4242` / xáo trộn `777`. Chạy lại ra **cùng con số đến chữ
số thứ ba**.

---

## 11. THAY ĐỔI MÃ NGUỒN TRONG ĐỢT NÀY

| File | Loại | Nội dung |
|---|---|---|
| `src/livelift/nlp/eval_intent.py` | **mới** | Khung đánh giá: nạp dữ liệu có xuất xứ, chỉ số thuần Python (macro-F1 / P-R-F1 / ma trận nhầm lẫn / bootstrap / Wilson), leave-one-session-out, rào chắn rò rỉ, 4 baseline, 3 cấu hình cải tiến, 9 dòng ablation, đường cong abstain, phân tích lỗi, sinh JSON + Markdown, đóng gói artifact |
| `src/livelift/nlp/normalize.py` | **mới** | Chuẩn hoá chat Việt (NFKC / teencode / gom kéo dài / emoji / giữ nguyên placeholder PII) + 9 đặc trưng phong cách. **Đo được là không giúp TF-IDF — giữ lại cho lộ trình ViSoBERT** |
| `src/livelift/nlp/data/intent_dataset_11.jsonl` | **mới** | 320 câu biên soạn, nhãn 11 lớp (42 dòng đổi so với bản 6 lớp) |
| `scripts/gan_lai_nhan_11.py` | **mới** | Bảng gán lại + lý do từng ca mơ hồ; sinh file trên một cách tất định |
| `tests/test_nlp_eval_harness.py` | **mới** | **39 test nhanh + 1 cổng `slow`**: công thức macro-F1 khớp sklearn, phạt lớp bịa, Wilson ở đuôi, bootstrap tất định, không buổi nào ở hai phía, rào rò rỉ loại và đếm, từ điển teencode không chứa đại từ đa nghĩa, món nợ nhãn đã trả, bộ biên soạn không dạy được `hoi_daily`/`bao_gia_shop` |
| `src/livelift/nlp/model/intent_clf_v2.joblib` | **mới** | Artifact 11 lớp, huấn luyện trên 2.513 mẫu (393 gold + 320 biên soạn + 1.800 LLM) |
| `docs/benchmarks/intent-eval/` | **mới** | `results.json` + `results.md` tự sinh |

**Artifact cũ `intent_clf.joblib` KHÔNG bị ghi đè** — nó là baseline tiền đăng ký, xoá nó là
xoá khả năng kiểm chứng con số cũ.

### Cổng chất lượng trước và sau

| | `pytest -m "not slow"` | Ghi chú |
|---|---|---|
| Trước đợt này | **993 passed, 0 failed** | đo lúc 13:56 ngày 14/09 |
| Sau đợt này | **1.059 passed, 1 failed, 1 skipped** | ⚠️ **1 test đỏ KHÔNG thuộc đợt này**: `test_web_design_tokens.py::test_every_focusable_element_shows_a_focus_ring`, đỏ vì ba file giao diện mới `web/src/app/{error,global-error,not-found}.tsx` đang được làm song song. Không có dòng mã Python nào của đợt NLP này chạm tới `web/` |
| Riêng phân hệ NLP | **40 passed** (`tests/test_nlp_eval_harness.py`, gồm cả cổng `slow`) + `test_intent_classifier.py` và `test_label_llm.py` **xanh nguyên vẹn** | `pytest tests/test_nlp_eval_harness.py tests/test_intent_classifier.py tests/test_label_llm.py` |
| `ruff check src tests` | **All checks passed** | |

**Cổng hồi quy mới (`slow`):** `test_upgraded_model_beats_the_shipped_one_on_real_chat` —
bản nâng cấp phải hơn artifact đang chạy **≥ 0,20 macro-F1** trên chat thật (khoảng cách
đo được là +0,354, nên một bản sụt nhẹ vẫn qua còn một bản hỏng thật thì trượt).

### 11.1. Vì sao v2 CHƯA phải mặc định — và thăng cấp thế nào

`intent.py` chọn artifact bằng biến môi trường:

```bash
LIVELIFT_INTENT_MODEL=v2 .venv/Scripts/python -m uvicorn livelift.api.main:app --port 8000
```

Mặc định vẫn là **v1**. Đây là một **quyết định có chủ ý**, không phải việc làm dở dang:
đổi mặc định kéo theo đổi `TRAINED_LABELS` từ 6 lên 11 lớp, mà `TRAINED_LABELS` đang là
hợp đồng của ba cổng đang khoá con số cũ (`test_label_llm.py` đối chiếu nó với sidecar của
artifact; `test_intent_classifier.py` chấm mô hình trên bộ biên soạn **nhãn 6 lớp**;
`train_intent.py` lấy `LABELS` từ nó). Thăng cấp là **một thay đổi riêng, có chủ đích**,
không phải tác dụng phụ của việc thêm một file — nhất là ở tuần nộp hồ sơ.

Đã kiểm chứng sẵn để lần thăng cấp đó chỉ còn là thủ tục — v2 giữ nguyên **mọi bất biến
hành vi mà v1 đang bị khoá** (`test_v2_keeps_every_behaviour_the_shipped_model_is_gated_on`):

| Bất biến | v1 | v2 |
|---|---|---|
| `gia bn v shop` (teencode, mất dấu) → `hoi_gia` | ✅ | ✅ (0,992) |
| `chot 1 don di shop` → `chot_don` | ✅ | ✅ (0,930) |
| `ship cod duoc khong` → `van_chuyen` | ✅ | ✅ (0,988) |
| Chat tiếng Anh ngoài miền → `khac` | 81% | **100%** (10/10) |
| Nạp được từ tiến trình sạch | ✅ | ✅ (`test_v2_artifact_loads_in_a_clean_process`) |

**Danh sách việc của lần thăng cấp** (ước lượng 1–2 giờ):

1. `labels.py`: `TRAINED_LABELS = INTENT_LABELS` (11 lớp).
2. `intent.py`: đổi mặc định `_VARIANT` sang `v2`; cập nhật docstring nêu bộ 11 lớp.
3. `test_intent_classifier.py::test_trained_model_beats_keyword_baseline_by_a_margin`:
   trỏ sang `intent_dataset_11.jsonl` (chấm mô hình 11 lớp bằng nhãn 6 lớp là chấm sai đề).
4. `test_label_llm.py`: đối chiếu `TRAINED_LABELS` với `intent_clf_v2.meta.json`.
5. `train_intent.py`: ghi rõ nó huấn luyện **baseline tiền đăng ký**, không phải artifact
   đang phục vụ.
6. Chạy lại toàn bộ cổng + cập nhật `FACT-SHEET.md`.

### 11.2. Một lỗi tự phát hiện trong chính đợt này

Artifact v2 **bản đầu tiên không nạp lại được**. `joblib` ghi tham chiếu hàm theo
`__module__`; script huấn luyện chạy bằng `python -m livelift.nlp.eval_intent` nên module
mang tên `__main__`, và artifact lưu ra trỏ tới `__main__._normalize_all` — chỉ tiến trình
huấn luyện nạp được, **mọi tiến trình khác đều `AttributeError`**. Lỗi này **không lộ ra
trong lúc huấn luyện**, chỉ một lần nạp từ ngoài mới bắt được.

Sửa tận gốc theo HARNESS.md §3 (test trước, fix sau):
hai hàm biến đổi chuyển sang `livelift.nlp.normalize` — một module không bao giờ là
`__main__`; thêm lớp phòng thủ thứ hai ở `if __name__ == "__main__"`; và thêm cổng
`test_v2_artifact_loads_in_a_clean_process` để lỗi này không bao giờ quay lại lặng lẽ.

---

## 12. VIỆC CÒN LẠI, THEO THỨ TỰ LỢI ÍCH / CHI PHÍ

| # | Việc | Chi phí | Lợi ích kỳ vọng | Vì sao tin như vậy |
|---|---|---|---|---|
| 1 | **Gán nhãn tay 200–300 dòng của một nhà bán KHÁC** (không thuộc hệ thống Achan) | 3–4 giờ | Con số đầu tiên **không** dính rò rỉ theo người bán | Hạn chế 3 là hạn chế lớn nhất còn lại |
| 2 | **Gán 150 dòng `chot_don` của buổi bán quần áo** (quy ước "mã X, N cái") | 1 giờ | Recall `chot_don` 0,455 → kỳ vọng > 0,8 | Cơ chế lỗi 3 ở §8.1 là lỗi *quy ước*, học được bằng vài chục ví dụ |
| 3 | **Người thứ hai gán lại 100 dòng lô 2 → đo κ** | 1 giờ | Trả lời được câu hỏi "nhãn của các bạn đáng tin không" | Hạn chế 2 |
| 4 | **Chặn theo tỷ lệ nền trong phiên** (§6.2) | nửa ngày | Đánh trúng cơ chế lỗi còn lại (buổi 0% ý định mua) | Precision đi theo tỷ lệ nền, không theo độ tự tin |
| 5 | ViSoBERT fine-tune | 1–2 ngày + hạ tầng | Chưa xác định được | §9 mục 7 |

---

*Người chịu trách nhiệm nội dung tài liệu này: đội LiveLift. Mọi con số ở đây do đội tự đo
trên dữ liệu của chính mình, tự công bố cả phần bất lợi, và sinh lại được bằng lệnh ở §10.*
