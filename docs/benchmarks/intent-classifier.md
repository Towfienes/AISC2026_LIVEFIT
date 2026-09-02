# Benchmark: Bộ phân loại ý định bình luận tiếng Việt

*Cập nhật 02/09/2026 · sinh lại bằng `python -m livelift.nlp.train_intent`*

## Kết quả

| Mô hình | macro-F1 | Accuracy |
|---|---|---|
| Baseline từ khóa (tiền đăng ký, ablation) | 0.653 | 0.669 |
| **TF-IDF (char 2-5 + word 1-2) + Logistic Regression — holdout 30%** | **0.831** | 0.823 |
| **TF-IDF + LogReg — 5-fold cross-validation** | **0.870** | 0.866 |

F1 theo lớp (5-fold CV): `hoi_gia` 0.855 · `hoi_size` 0.917 · `che_dat` 0.816 ·
`chot_don` 0.939 · `van_chuyen` 0.917 · `khac` 0.780.

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
   Gán nhãn ~200–300 bình luận/tuần theo **active learning** — ưu tiên những
   câu mô hình hiện tại kém chắc chắn nhất.
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

### Giới hạn phải nói khi trình bày

- Con số 0.87 đo trên **cùng phân phối** với dữ liệu huấn luyện (biên soạn).
  Trên chat thật, kỳ vọng **giảm** — bao nhiêu thì chỉ dữ liệu thật trả lời được.
- Lớp `khac` (F1 0.78) là lớp mở — mọi thứ không thuộc 5 ý định kia — nên luôn
  khó nhất; nhầm lẫn chủ yếu rơi vào `hoi_gia`/`khac`.
- Quy ước nhãn cho câu đa ý định ("size M giá nhiêu"): lấy ý định *hành động
  gần nhất với chốt đơn* làm nhãn chính.
