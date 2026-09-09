# Live-fire: chat bán hàng THẬT — "Mega Live: Achan Shop Hải Phòng"

*Đo ngày 08/09/2026 · phiên quan sát `b519f75c-09ab-4cb4-8dff-f5c492c142be`*

> **Kết luận một dòng:** macro-F1 **0,870** đo trên bộ biên soạn **KHÔNG chuyển
> giao** sang chat bán hàng thật. Trên 200 bình luận thật lấy ngẫu nhiên, cùng
> mô hình đó đạt **macro-F1 0,271** và **accuracy 0,920 — THẤP HƠN** baseline
> tầm thường "luôn đoán `khac`" (0,995). Trong 932 bình luận được gắn nhãn ý
> định hành động, ước tính chỉ **~7%** là đúng.

## Lệnh tái lập

```bash
# 0. API (in-memory store) — phiên được tạo lại từ VOD công khai
cd d:/AISC2026/livelift && .venv/Scripts/python -m uvicorn livelift.api.main:app --port 8000

# 1. Đọc lại phiên + toàn bộ bình luận đã lọc PII
curl http://127.0.0.1:8000/sessions/b519f75c-09ab-4cb4-8dff-f5c492c142be
curl http://127.0.0.1:8000/sessions/b519f75c-09ab-4cb4-8dff-f5c492c142be/comments > comments.json

# 2. Hai mẫu dùng trong tài liệu này (Python chuẩn, seed cố định)
#    Mẫu A — 200 bình luận ngẫu nhiên đơn giản:  random.Random(20260908).sample(comments, 200)
#    Mẫu B — tối đa 30 mỗi lớp trong 932 dự đoán non-khac: random.Random(4242)

# 3. Lô gán nhãn thật xuất ra từ chính phiên này (1.800 dòng)
.venv/Scripts/python -m livelift.nlp.label_llm export \
    --input data/labeling/lot1-achan-b519f75c/comments_b519f75c.jsonl \
    --out-dir data/labeling/lot1-achan-b519f75c \
    --limit 1800 --random-fraction 0.10 --seed 2026 --uncertain-first
```

## 1. Nguồn — nói rõ đây là gì

| | |
|---|---|
| Buổi live | "Mega Live: Achan Shop Hải Phòng" — khai trương cửa hàng, **bán hàng thật** |
| Nguồn | `youtube.com/watch?v=ZU_0QJzsR6w` — VOD **công khai**, chat replay công khai |
| Thời lượng | 117 phút |
| Bình luận vào hệ thống | **6.586** (đã qua lọc PII ở tầng ingest) |
| Loại phiên | `platform=replay`, `design.analysis_only=true` — **quan sát**, không có gán ngẫu nhiên, **không sinh số nhân quả nào** |

Khác biệt so với live-fire 02/09: lần đó là VOD **kỹ thuật** (stream cờ vua
tiếng Anh) — chỉ kiểm được hành vi ngoài miền. Lần này là **chat mua bán tiếng
Việt đúng miền đích**, tức lần đầu bộ phân loại bị chấm trên chính thứ nó được
sinh ra để đọc.

## 2. Phương pháp

Toàn bộ số liệu đọc lại **qua chính API của hệ thống**, không qua đường tắt nào.

1. **Mẫu A — prevalence & macro-F1.** 200 bình luận lấy **ngẫu nhiên đơn giản**
   từ 6.586 (`random.Random(20260908)`). Người gán nhãn thủ công theo guideline
   6 lớp *đang hành hiệu tại thời điểm đo*, **không nhìn dự đoán của model
   trước**. Mẫu ngẫu nhiên → ước lượng prevalence không chệch.
2. **Mẫu B — precision từng lớp.** Mẫu A quá ít dự đoán non-`khac` (17 dòng) để
   đo precision. Lấy thêm **theo tầng**: tối đa 30 dòng mỗi lớp trong 932 dự
   đoán non-`khac` (`hoi_size` chỉ có 16 → lấy hết) = **136 dòng**, gán nhãn
   tay như trên. Precision từng lớp × số dự đoán của lớp đó trên cả phiên =
   ước lượng số dương tính THẬT.
3. Khoảng tin cậy 95% dùng công thức **Wilson** (mẫu nhỏ, tỷ lệ gần 0 — Wald sẽ
   cho cận âm).

**Giới hạn của phương pháp, nói trước:** một người gán nhãn, không đo được
đồng thuận giữa người gán (κ). Với các trường hợp mơ hồ ("111" là spam số hay
chốt đơn?) tài liệu này chọn cách **có lợi cho model** rồi vẫn báo con số thấp —
tức các số dưới đây là **cận trên lạc quan**, không phải cận dưới bi quan.

## 3. Số liệu hệ thống tự báo — đã kiểm chứng lại từng con số

### 3.1 Phân bố ý định (6.586 bình luận)

| Nhãn | Số lượng | Tỷ lệ |
|---|---:|---:|
| `khac` | 5.654 | 85,8% |
| `chot_don` | 608 | 9,2% |
| `hoi_gia` | 108 | 1,6% |
| `che_dat` | 102 | 1,5% |
| `van_chuyen` | 98 | 1,5% |
| `hoi_size` | 16 | 0,2% |

### 3.2 Độ tự tin

Trung vị **0,443** · p10 **0,328** · p90 **0,719** · min 0,208 · max 0,974.

Ngưỡng abstain hiện tại là **0,45**. Trung vị nằm **dưới** ngưỡng: **3.397 /
6.586 = 51,6%** số dự đoán bị đẩy về `khac` vì thiếu tự tin. Nói cách khác **quá
nửa** đầu ra của model trên chat thật không phải là một phán đoán, mà là một
lần từ chối phán đoán. Trong 5.654 nhãn `khac`, **60,1%** là abstain chứ không
phải model thật sự nhận ra "đây là chuyện ngoài lề".

### 3.3 PII đã che

**588 / 6.586 bình luận (8,9%)** bị che ít nhất một mục, tổng **609 lượt**
(21 bình luận có từ 2 loại trở lên):

| Loại | Lượt |
|---|---:|
| `name` | 270 |
| `address` | 209 |
| `social` | 123 |
| `order` | 6 |
| `phone` | 1 |

Đếm placeholder trong text khớp chính xác: `[TÊN]` 270 · `[ĐỊA CHỈ]` 209 ·
`[MXH]` 123 · `[MÃ ĐƠN]` 6 · `[SĐT]` 1. Bộ lọc PII **chạy đúng như thiết kế**
trên dữ liệu thật — đây là phần duy nhất của pipeline vượt qua live-fire này mà
không phải sửa gì.

## 4. Độ chính xác THẬT — con số phải nói ra

### 4.1 Mẫu A (200 ngẫu nhiên)

| Chỉ số | Bộ biên soạn (5-fold CV) | **Chat thật** |
|---|---:|---:|
| macro-F1 | 0,870 | **0,271** |
| Accuracy | 0,866 | **0,920** |
| Accuracy của baseline "luôn đoán `khac`" | — | **0,995** |

F1 từng lớp trên mẫu A: `hoi_gia` 0,667 · `khac` 0,958 · `hoi_size` **0** ·
`che_dat` **0** · `chot_don` **0** · `van_chuyen` **0**.

Bốn lớp F1 bằng 0 vì trong 200 bình luận thật **không có lấy một** trường hợp
thật nào của chúng, trong khi model vẫn gắn 15 nhãn. Accuracy 0,920 nghe đẹp
nhưng **vô nghĩa**: dữ liệu lệch 199/200 về `khac` nên một hàm `return "khac"`
đạt 0,995. **Model đang tệ hơn một dòng code không làm gì.**

### 4.2 Prevalence ý định hành động thật

Trong 200 bình luận, đúng **1** là ý định hành động thật ("trà bao nhiêu tiền
một hộp em ơi" → `hoi_gia`).

- Prevalence thật: **0,50%** (KTC95 Wilson **0,09% – 2,78%**)
- Model gắn nhãn hành động: **8,5%** trên mẫu A, **14,2%** trên cả phiên

### 4.3 Mẫu B — precision từng lớp (136 dòng gán tay)

| Lớp | Đúng / mẫu | Precision | KTC95 | Ước số ĐÚNG trên cả phiên |
|---|---:|---:|---|---:|
| `hoi_gia` | 6/30 | **20,0%** | 9,5–37,3% | ~22 / 108 |
| `van_chuyen` | 5/30 | **16,7%** | 7,3–33,6% | ~16 / 98 |
| `che_dat` | 3/30 | **10,0%** | 3,5–25,6% | ~10 / 102 |
| `chot_don` | 1/30 | **3,3%** | 0,6–16,7% | ~20 / 608 |
| `hoi_size` | 0/16 | **0,0%** | 0,0–19,4% | **0 / 16** |
| **Gộp** | **15/136** | **11,0%** | **6,8–17,4%** | **~68 / 932** |

`hoi_size` **sai 100%** — cả 16 dự đoán của lớp này trên toàn phiên đều sai, đã
soi bằng tay từng dòng.

Quy chiếu ngược: ~68 / 932 nhãn hành động là đúng ⇒ **micro-precision ~7,3%**;
tương đương **1,04%** của 6.586 bình luận. Đối chiếu với ước lượng độc lập từ
mẫu A (0,50%): hai con số cùng bậc độ lớn, đều nằm quanh **0,5–1%**.

**Radar ý định đang thổi phồng khối lượng "khách có ý định mua" lên ~13–14 lần.**

## 5. Phân tích định tính — model sai KIỂU gì

### 5.1 Ví dụ sai rõ ràng (nguyên văn, đã lọc PII)

| Bình luận thật | Model gán | Đúng phải là | Cơ chế |
|---|---|---|---|
| `Chao A Chan ! Chao Ca Nha !` | `chot_don` 0,855 | chào hỏi | lời chào → "ý định mua", tự tin cao |
| `EM CHAO CA NHA` | `chot_don` 0,974 | chào hỏi | tự tin **cao nhất phiên** cho một lời chào |
| `ĐỘNG CHỦ KO THÍCH ĐIỀU NÀY.kkkkk` | `hoi_size` 0,609 | bàn luận | không liên quan gì tới size |
| `Hải phòng toàn đại gia` | `hoi_gia` 0,548 | bàn luận | `đại **gia**` ≈ char-ngram của `giá` |
| `Xoài rẻ quá ạ` | `che_dat` 0,700 | khen | **khen rẻ** bị đọc thành **chê đắt** — ngược hẳn dấu |
| `Cò cao quá` | `che_dat` 0,875 | khen ngoại hình | `cao` = chiều cao, không phải giá cao |
| `chúc ... khai trương buôn may bán đắt` | `che_dat` 0,608 | chúc mừng | `bán **đắt**` = bán chạy, không phải giá đắt |
| `Tôi muốn mở đại lý ở [ĐỊA CHỈ] có được không` | `van_chuyen` 0,593 | hỏi đại lý | lead giá trị cao bị định tuyến sai |
| `Thời hạn su dung bao nhiêu em` | `hoi_size` 0,486 | hỏi sản phẩm | `bao nhiêu` → size |
| `Em vô bình luận mà tụi nó block cũng vì nộp **đơn** tố giác ở tòa án` | `chot_don` 0,665 | bàn luận | `đơn` (tố giác) = `đơn` (hàng) |
| `TRÀ MĂNG ĐEN ... GIÁ 120K` | `che_dat` 0,742 | shop báo giá | shop tự dán bảng giá bị tính là khách |

Ba nhóm cơ chế:

1. **Đa nghĩa tiếng Việt bị char-ngram nuốt chửng.** `đắt` (giá cao) vs `đắt`
   (bán chạy); `cao` (giá) vs `cao` (chiều cao); `gia` trong `đại gia`; `đơn`
   (đơn hàng) vs `đơn` (đơn kiện). Bộ biên soạn **không có** cặp đối nghịch nào
   như vậy nên model chưa từng phải học phân biệt.
2. **Không có mô hình về NGƯỜI NÓI.** Model chấm câu chữ, không biết ai đang
   nói. Bảng giá do mod dán (lặp lại hàng chục lần, in hoa) chiếm **13/30**
   dương tính giả của `hoi_gia` — tức riêng nguồn này gây ~43% lỗi lớp đó.
   Tương tự, shop hô "cả nhà chốt đơn nha" bị tính là khách chốt đơn.
3. **Bộ nhãn thiếu lớp lớn.** Xem mục 6.

### 5.2 Thứ bộ 6 lớp KHÔNG bao phủ — đo trên 200 mẫu

| Nhóm nội dung | Số / 200 | Tỷ lệ |
|---|---:|---:|
| Bàn luận ngoài lề / drama cộng đồng | 85 | **42,5%** |
| Cảm ơn · chúc mừng · khen · cổ vũ | 56 | **28,0%** |
| Chào hỏi · điểm danh | 20 | **10,0%** |
| Spam số / emoji (`777`, `9999`, `❤❤❤`) | 15 | 7,5% |
| Thông tin lịch / sự kiện | 7 | 3,5% |
| **Hỏi sản phẩm** (còn hàng, có bán không, HSD, xem ở đâu) | 4 | 2,0% |
| **Hỏi mở đại lý / chi nhánh / CTV** | 4 | 2,0% |
| Kêu gọi like / share / xem | 4 | 2,0% |
| **Shop tự dán bảng giá** | 2 | 1,0% |
| Hỏi/hối đơn cũ · góp ý dịch vụ | 2 | 1,0% |
| **Ý định hành động thật (trong 5 lớp)** | **1** | **0,5%** |

- **40,0%** chat là **xã giao** (chào hỏi + cảm ơn/khen + kêu gọi tương tác) —
  toàn bộ đang bị dồn vào `khac` như một cái sọt rác.
- **5,0%** (10/200) là câu hỏi **thương mại thật của khách** nhưng nằm ngoài 6
  lớp: hỏi sản phẩm 4 · hỏi đại lý 4 · hối đơn cũ 1 · góp ý dịch vụ 1. Đây là
  phần **đáng tiếc nhất**: hệ thống bỏ lỡ đúng những lead mà trung control cần
  thấy, **gấp 10 lần** số ý định nó bắt được (0,5%). Thêm 1,0% nữa là bảng giá
  do shop tự dán — không phải lead, nhưng là nguồn nhiễu cần tách riêng.

**Cảnh báo về tính đại diện:** phiên này do một nhân vật YouTube đang có tranh
cãi dẫn, nên tỷ lệ drama (42,5%) chắc chắn **cao bất thường** so với một buổi
live bán hàng phổ thông. Các con số về `chao_hoi` / `cam_on_khen` /
`hoi_sanpham` ít nhạy với đặc thù đó hơn, nhưng **một phiên vẫn là một phiên** —
mọi kết luận ở đây cần lặp lại trên ít nhất 2–3 buổi live khác trước khi coi là
tính chất chung. Chat replay của 10 buổi khác đã tải sẵn cho việc đó.

### 5.3 Bộ dữ liệu biên soạn TỰ NÓ đã mâu thuẫn

Rà 60 dòng `khac` trong `src/livelift/nlp/data/intent_dataset.jsonl` bằng
guideline mới: khoảng **34/60 (~57%)** thuộc lớp khác —
`hoi_sanpham` ~18 ("hạn sử dụng tới khi nào ạ", "chất vải là cotton hả shop"),
`cam_on_khen` ~12 ("chị chủ xinh quá", "10 điểm cho shop"),
`chao_hoi` ~4 ("chào shop buổi tối", "hello mọi người").

Hệ quả bắt buộc: **không được huấn luyện lại trước khi gán nhãn lại 60 dòng
này.** Nếu không, model sẽ đồng thời học "chào hỏi là `chao_hoi`" (nhãn mới) và
"chào hỏi là `khac`" (nhãn cũ) — đúng sự lẫn lộn mà lớp mới sinh ra để dẹp.
Lỗi này suýt lọt vào lô gán nhãn đầu tiên: prompt lấy ví dụ `khac` từ chính bộ
biên soạn, nên đã dạy ngược cho LLM. Đã chặn bằng
`test_khac_examples_do_not_contradict_the_new_classes`.

## 6. Việc đã làm sau phát hiện này

1. **Mở rộng bộ nhãn 6 → 11 lớp**, mỗi lớp mới có định nghĩa + ví dụ **thật**
   lấy nguyên văn từ phiên này: `chao_hoi`, `cam_on_khen`, `hoi_sanpham`,
   `hoi_daily`, `bao_gia_shop`. Chi tiết:
   [intent-classifier.md](intent-classifier.md).
2. **Một nguồn duy nhất cho bộ nhãn** — `src/livelift/nlp/labels.py`. Trước đó
   bộ nhãn bị chép ở 4 chỗ; thêm một lớp phải sửa đủ 4 chỗ. Khóa bằng
   `test_label_set_comes_from_exactly_one_module` (kiểm tra `is`, không phải `==`).
3. **Protocol lô gán nhãn hai tầng** (`--random-fraction`): một phần lấy ngẫu
   nhiên đơn giản để ước lượng prevalence **không chệch**, phần còn lại
   uncertain-first để lấy giá trị học. Chính live-fire này cho thấy vì sao cần:
   lô thuần uncertain-first không bao giờ trả lời được câu hỏi "thật ra có bao
   nhiêu khách hỏi giá".
4. **Lô 1.800 nhãn đã xuất** từ đúng phiên này —
   `data/labeling/lot1-achan-b519f75c/`.
5. **CHƯA huấn luyện lại.** Chưa có nhãn thật thì chưa train — 5 lớp mới nằm
   trong guideline nhưng `TRAINED_LABELS` vẫn là 6 lớp cũ, và
   `intent_clf.meta.json` ghi đúng 6 lớp đó. Model không được phép bịa lớp nó
   chưa học.

## 7. Điều này ảnh hưởng gì tới phần khoa học của LiveLift

**Không ảnh hưởng tới ước lượng nhân quả.** Radar ý định là **công cụ hiển thị
cho trung control + biến khám phá**, không nằm trong bất kỳ ước lượng viên nào
(`analysis/estimators.py` không đọc `intent_label`). Tác động ON−OFF, KTC và p
được tính từ click/viewer, không từ nhãn ý định.

**Ảnh hưởng thật, và phải nói khi trình bày:**

- Mọi phát biểu kiểu "hệ thống nhận ra 608 lượt chốt đơn" là **sai** — con số
  đúng ước chừng **20**. Không được để con số 932 xuất hiện ở đâu như một chỉ
  số thành tích.
- Radar ý định trên giao diện hiện tại, với chat kiểu này, **gần như là nhiễu**.
  Trung control tin vào nó sẽ bị dẫn sai.
- Con số **0,870** chỉ được nêu kèm đúng ngữ cảnh của nó ("trên bộ biên soạn,
  cùng phân phối") và **luôn đi kèm 0,271 của chat thật**. Nêu một mình là
  overclaim.

## 8. Việc tiếp theo (theo thứ tự)

1. Gửi lô 1.800 dòng đi 2 LLM → `merge` → người duyệt bất đồng → `finalize`.
2. Gán nhãn lại 60 dòng `khac` của bộ biên soạn theo guideline 11 lớp.
3. Huấn luyện lại, **báo cáo song song hai con số**: bộ biên soạn và bộ thật.
4. Lặp phép đo mục 4 trên ≥2 buổi live khác (chat replay đã có sẵn) để tách
   đặc thù phiên khỏi tính chất chung.
5. Xem lại ngưỡng abstain 0,45 **sau khi** có model mới — chỉnh ngưỡng lúc này
   chỉ là đổi chỗ lỗi, vì gốc là bộ nhãn thiếu lớp chứ không phải ngưỡng sai.
6. `web/src/lib/types.ts` giữ bản sao bộ nhãn riêng (6 lớp). Chưa đụng: thêm
   lớp vào giao diện trước khi model dự đoán được sẽ tạo 5 chuỗi rỗng trên
   radar. Đồng bộ **cùng lúc** với lần huấn luyện lại.
