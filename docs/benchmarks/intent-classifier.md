# Benchmark: Bộ phân loại ý định bình luận tiếng Việt

*Cập nhật 08/09/2026 · sinh lại bằng `python -m livelift.nlp.train_intent`*

> ⚠️ **ĐỌC TRƯỚC KHI TRÍCH BẤT KỲ CON SỐ NÀO.** Con số 0.870 dưới đây đo trên bộ
> **tự biên soạn**, cùng phân phối với dữ liệu huấn luyện. Trên chat bán hàng
> **thật**, cùng mô hình đó đạt **macro-F1 0.271** và precision gộp **11%** —
> đo ngày 08/09 trên 6.586 bình luận thật, xem
> [live-fire-achan.md](live-fire-achan.md). **Không được nêu 0.870 một mình.**

## Kết quả

| Mô hình | Bộ đo | macro-F1 | Accuracy |
|---|---|---|---|
| Baseline từ khóa (tiền đăng ký, ablation) | biên soạn | 0.653 | 0.669 |
| **TF-IDF (char 2-5 + word 1-2) + LogReg — holdout 30%** | biên soạn | **0.831** | 0.823 |
| **TF-IDF + LogReg — 5-fold cross-validation** | biên soạn | **0.870** | 0.866 |
| Cùng mô hình đó, **chat bán hàng THẬT** (200 mẫu ngẫu nhiên) | live-fire 08/09 | **0.271** | 0.920 |
| Baseline tầm thường `return "khac"` trên chính 200 mẫu đó | live-fire 08/09 | 0.166 | **0.995** |

F1 theo lớp (5-fold CV, bộ biên soạn): `hoi_gia` 0.855 · `hoi_size` 0.917 ·
`che_dat` 0.816 · `chot_don` 0.939 · `van_chuyen` 0.917 · `khac` 0.780.

Trên chat thật, bốn lớp `hoi_size` / `che_dat` / `chot_don` / `van_chuyen` có
**F1 = 0** (không có trường hợp thật nào trong 200 mẫu, model vẫn gắn 15 nhãn).

Suy luận: < 1ms/bình luận trên CPU, artifact 84 KB, không cần torch/GPU.
Fallback tự động về baseline từ khóa khi thiếu sklearn hoặc thiếu artifact.

## Dữ liệu huấn luyện là gì — nói thẳng

**320 bình luận được biên soạn thủ công** (60/50/50/50/50/60 theo lớp), mô phỏng
chat live bán hàng Việt thực tế: có dấu / mất dấu / teencode / viết tắt / emoji /
lỗi gõ. Đây là **bộ khởi động (bootstrap)**, không phải dữ liệu cào từ production.

### Vì sao không train trên một bộ dữ liệu lớn với benchmark SOTA?

Câu hỏi đúng — và câu trả lời có ba tầng:

1. **Lõi của LiveLift không phải là mô hình dự đoán.** Giá trị khoa học nằm ở
   *thí nghiệm ngẫu nhiên hóa* — thứ không cần big data để đúng, mà cần ngẫu
   nhiên hóa hợp lệ. "Huấn luyện" tương đương của phần lõi là **thẩm định ước
   lượng viên bằng Monte-Carlo** (200 lần lặp A/A: FPR 4.5%, coverage 95.5%) và
   **hiệu chỉnh mô phỏng theo KuaiLive** (5,36 triệu tương tác thật — xem
   `docs/benchmarks/kuailive-calibration.md`). Đó chính là "bộ dữ liệu lớn" của
   dự án, dùng đúng chỗ của nó.
2. **Không tồn tại bộ dữ liệu công khai nào cho bài toán này.** Ý định mua hàng
   trong chat livestream tiếng Việt chưa có dataset gán nhãn công khai (đã rà:
   UIT-ViOCD là phát hiện phàn nàn, UIT-ViSFD là sentiment theo khía cạnh —
   khác nhãn, khác miền). Mọi hệ thống thương mại trong ngành đều phải tự gán
   nhãn dữ liệu của chính mình.
3. **Thành phần này không cần SOTA để hoàn thành vai trò.** Radar ý định là
   công cụ hiển thị cho trung control + biến khám phá — **không nằm trong ước
   lượng nhân quả**. Yêu cầu đúng của nó là: hơn hẳn baseline có thể giải thích
   được, kỳ vọng được hiệu chỉnh trung thực, và có đường nâng cấp sạch.

### Đường nâng cấp (đã lên kế hoạch, không phải hứa suông)

1. **Ngay khi Live Lab chạy:** mọi bình luận thật (đã lọc PII) nằm sẵn trong DB.
   Gán nhãn theo **protocol hai tầng** (`--random-fraction`): một phần lấy
   **ngẫu nhiên đơn giản** để ước lượng prevalence *không chệch*, phần còn lại
   **uncertain-first** để lấy giá trị học. Lô thuần uncertain-first dạy được
   model nhưng không bao giờ trả lời được "thật ra có bao nhiêu khách hỏi giá"
   — chính live-fire 08/09 cho thấy vì sao cần cả hai. Lô đầu tiên đã xuất:
   **1.800 dòng** từ phiên `b519f75c` (180 ngẫu nhiên + 1.620 bất định), xem
   `data/labeling/README.md`.
2. **Chạy lại script này** trên dữ liệu thật → benchmark tự cập nhật; con số
   trên bộ biên soạn được thay bằng con số trên bộ thật, ghi rõ nguồn gốc.
3. **Đủ 2–3k nhãn thật:** fine-tune ViSoBERT (EMNLP 2023 — pretrain đúng trên
   text mạng xã hội Việt), benchmark so với chính mô hình TF-IDF này làm
   ablation. Kỳ vọng thực tế theo văn liệu: macro-F1 0.80–0.88 trên dữ liệu
   thật nhiễu hơn.

### Ngưỡng tự tin — bài học từ live-fire video thật (02/09)

Chạy pipeline trên một VOD livestream thật 262 phút / 14.903 bình luận (tiếng
Anh — stream cờ vua) lộ ra: model tiếng Việt gán nhầm `che_dat` cho 12% chat
tiếng Anh. Thêm **ngưỡng tự tin 0.45**: dưới ngưỡng → trả `khac` (kiêng đoán
ngoài miền). Đo được: độ chính xác tiếng Việt không đổi (in-sample 1.000),
tiếng Anh về `khac` tăng 62% → 81%. Test hồi quy:
`test_out_of_domain_text_mostly_abstains_to_khac`.

### Live-fire chat BÁN HÀNG thật (08/09) — câu hỏi "bao nhiêu" đã có đáp án

Câu "trên chat thật giảm bao nhiêu thì chỉ dữ liệu thật trả lời được" ở mục trên
nay đã đo được: **macro-F1 0.870 → 0.271**, precision gộp của 5 lớp hành động
**11.0%** (KTC95 6.8–17.4%), riêng `hoi_size` sai **100%** (0/16). Toàn bộ phương
pháp, mẫu, ví dụ sai và kết luận: [live-fire-achan.md](live-fire-achan.md).

Ba nguyên nhân, không cái nào sửa được bằng cách chỉnh ngưỡng:
**(a)** bộ nhãn thiếu lớp — 40% chat thật là xã giao, 6% là câu hỏi thương mại
ngoài 6 lớp; **(b)** đa nghĩa tiếng Việt (`bán đắt` ≠ `đắt quá`, `cao` chiều cao
≠ `cao` giá, `đại **gia**`, `**đơn** kiện`); **(c)** không có mô hình về người
nói (bảng giá mod dán bị tính là khách hỏi giá).

---

## Guideline gán nhãn — 11 lớp (cập nhật 08/09/2026)

**Nguồn duy nhất trong code: `src/livelift/nlp/labels.py`.** Prompt cho LLM, thông
báo lỗi của validator và mục này đều lấy từ đó — sửa một chỗ, đổi mọi nơi.

Phân biệt hai tập lớp:

- `INTENT_LABELS` (11 lớp) — bộ **gán nhãn**, người/LLM được phép dùng.
- `TRAINED_LABELS` (6 lớp) — bộ artifact `intent_clf.joblib` **thật sự dự đoán
  được**. Năm lớp mới chưa có nhãn nên **chưa huấn luyện**; model không được
  phép bịa lớp nó chưa học.

| Lớp | Định nghĩa | Ví dụ THẬT (phiên `b519f75c`, đã lọc PII) |
|---|---|---|
| `hoi_gia` | **KHÁCH** hỏi giá. Người hỏi phải là khách, không phải shop đọc bảng giá | `trà bao nhiêu tiền một hộp em ơi` · `1 cặp gội bưởi giá bn AChan` · `Cà phê giá sao shop ơi?` · `Báo giá đi` |
| `hoi_size` | Hỏi size / cân nặng / chiều cao / form để **chọn cỡ**. Không phải mọi câu chứa "vừa" hay "bao nhiêu" | *(0/16 dự đoán trên phiên này là đúng — chưa có ví dụ thật)* |
| `che_dat` | Chê **GIÁ** đắt/mắc/cao, trả giá xuống. **Không** phải khen rẻ, **không** phải "cao" nghĩa chiều cao | `500tr cao quá ạ` · `300tr khả thì hơn` · `Mẹt bảo Sầu Riêng ngoài [ĐỊA CHỈ] mà B bán 600k` |
| `chot_don` | **KHÁCH** chốt đơn/đặt mua. Không phải shop hô hào "cả nhà chốt đơn nha" | `Au chưa chốt đơn 👍 Cho xin một đơn ủng hộ Tuyên nào❤` |
| `van_chuyen` | Hỏi giao hàng, phí ship, COD, thời gian nhận, gửi đi tỉnh/nước ngoài, hoặc hối đơn đã đặt | `Sâm mật ông có ship Đài Loan được không em báu` · `có thể gởi hàng qua Hàn Quốc được không em` · `Bưởi giao lâu quá` |
| **`chao_hoi`** ✨ | Chào hỏi, điểm danh, tạm biệt. **10,0%** chat thật | `Chao A Chan ! Chao Ca Nha !` · `chào cả nhà buổi tối bình an` · `EM CHAO CA NHA` · `TINA NGUYEN : HELLO` |
| **`cam_on_khen`** ✨ | Cảm ơn, chúc mừng, chúc sức khỏe, khen, cổ vũ, đồng tình. **28,0%** chat thật | `Chúc mừng Achan shop hp` · `cảm ơn a chan đưa sản phẩm Trà Măng Đen lên kệ` · `Xoài rẻ quá ạ` · `Tuyệt vời quá` |
| **`hoi_sanpham`** ✨ | Hỏi về sản phẩm **ngoài giá và size**: còn hàng, có bán không, HSD, thành phần, xem ở đâu | `có bán dầu dừa ạ` · `còn sốt muối tắc chưa B` · `Thời hạn su dung bao nhiêu em` · `vào đâu để xem các mặt hàng nhỉ` |
| **`hoi_daily`** ✨ | Hỏi mở đại lý / chi nhánh / CTV / hợp tác — khách muốn **BÁN CÙNG**, không mua lẻ | `Tôi muốn mở đại lý ở [ĐỊA CHỈ] có được không bóng` · `mở đại lý bên hàn được không em` · `em có mở sốp Vũng Tàu ko` |
| **`bao_gia_shop`** ✨ | **Shop/mod tự dán** bảng giá, tên sản phẩm kèm giá, khuyến mãi. Nguồn nhiễu, không phải khách hỏi giá | `LỤC TRÀ MĂNG ĐEN ACHAN TEA (HỘP 200G) GIÁ 400K` · `MẮM RUỐC CHAY (200G) GIÁ 60K \|\| SỐT MUỐI TẮC (200G) GIÁ 55K` |
| `khac` | Mọi thứ còn lại: bàn luận ngoài lề, drama, spam số/emoji, thông tin lịch | `77777778👍👍👍👍` · `0h ngày 22/05 đến 0h ngày 24` · `Bấm lai bấm lai khán giả ơi` |

✨ = lớp thêm sau live-fire 08/09, **phát hiện qua mẫu thật**, chưa có trong model.

### Quy ước gán nhãn

1. **Câu đa ý định** ("size M giá nhiêu"): lấy ý định *hành động gần nhất với
   chốt đơn* làm nhãn chính.
2. **Ai đang nói quyết định nhãn.** Shop dán bảng giá → `bao_gia_shop`; shop hô
   "cả nhà chốt đơn nha" → `khac`. Chỉ ý định của **khách** mới tính.
3. **Chào hỏi/khen không bao giờ là ý định mua.** Tuyệt đối không gán `chot_don`
   cho một lời chào — đây là lỗi số 1 đo được trên chat thật.
4. **`che_dat` chỉ về GIÁ.** `bán đắt` (bán chạy) và `cao` (chiều cao) không phải
   chê giá; `Xoài rẻ quá ạ` là `cam_on_khen`, không phải `che_dat`.
5. Bình luận đã lọc PII — `[SĐT]`, `[ĐỊA CHỈ]`, `[TÊN]` là bình thường.
6. Mất dấu / teencode / viết tắt / emoji — vẫn gán như thường.

### ⚠ Nợ bắt buộc trả trước khi huấn luyện lại

**60 dòng `khac` trong `data/intent_dataset.jsonl` phải được gán nhãn lại.**
Chúng được viết khi `khac` còn ôm cả chào hỏi/khen/hỏi sản phẩm, nên nay khoảng
**34/60 (~57%)** mâu thuẫn trực tiếp với guideline này (`chào shop buổi tối`,
`chị chủ xinh quá`, `hạn sử dụng tới khi nào ạ` đang mang nhãn `khac`). Train
trước khi sửa = dạy model đúng sự lẫn lộn mà 5 lớp mới sinh ra để dẹp.

### Giới hạn phải nói khi trình bày

- Con số 0.87 đo trên **cùng phân phối** với dữ liệu huấn luyện (biên soạn).
  Trên chat thật **đã đo**: 0.271. Nêu 0.87 một mình là overclaim.
- Lớp `khac` (F1 0.78) là lớp mở nên luôn khó nhất; nhầm lẫn chủ yếu rơi vào
  `hoi_gia`/`khac`.
- Radar ý định là **công cụ hiển thị + biến khám phá**, KHÔNG nằm trong ước
  lượng nhân quả — `analysis/estimators.py` không đọc `intent_label`.
