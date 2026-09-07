# Pipeline nhãn LLM cho bộ phân loại ý định (gói F)

*06/09/2026 · code: `src/livelift/nlp/label_llm.py` · test: `tests/test_label_llm.py`*

Biến mục "Đường nâng cấp" trong `docs/benchmarks/intent-classifier.md` thành
quy trình chạy được: gán nhãn 14.903 bình luận VOD thật (đã qua lọc PII, đang
nằm trong DB dạng phiên quan sát) bằng **2 LLM độc lập + người duyệt bất
đồng**, ưu tiên các câu mô hình hiện tại kém chắc chắn nhất (active learning —
cột `intent_confidence`, migration 0003).

**Nguyên tắc:** code trong repo KHÔNG gọi API LLM nào — chỉ chuẩn bị batch và
gộp kết quả. Việc gửi batch là thao tác thủ công của nhóm, chi phí và model
được chọn ngoài mã nguồn.

## Quy trình 4 bước

1. **Export** — xuất batch + prompt (system prompt = guideline 6 lớp + 8 ví
   dụ/lớp trích tự động từ bộ 320 mẫu biên soạn):

   ```bash
   python -m livelift.nlp.label_llm export --out-dir lot1 --limit 2000 --uncertain-first
   # -> lot1/batch.jsonl ({id, text}) + lot1/prompt.txt
   ```

   `--uncertain-first`: sắp theo `intent_confidence` tăng dần; câu chưa có
   confidence (baseline từ khóa chấm) đứng đầu — đúng thứ tự active learning.

2. **Gửi 2 LLM** (thủ công, qua batch API của nhà cung cấp): cùng
   `prompt.txt` làm system prompt, mỗi model trả một file JSONL `{id, label}`.
   Dùng 2 model KHÁC HỌ (ví dụ một Claude + một GPT/Gemini) để bất đồng phản
   ánh câu khó thật, không phải thiên kiến chung một nhà.

3. **Merge** — chỉ giữ nhãn khi 2 model trùng nhau; mọi bất đồng (kể cả id bị
   một model bỏ sót) rơi vào file cho người duyệt, kèm text:

   ```bash
   python -m livelift.nlp.label_llm merge --model-a a.jsonl --model-b b.jsonl \
       --batch lot1/batch.jsonl --out-dir lot1
   # -> lot1/consensus.jsonl + lot1/disagreements.jsonl + thống kê tỷ lệ đồng thuận
   ```

   Nhãn ngoài 6 lớp (`hoi_gia, hoi_size, che_dat, chot_don, van_chuyen, khac`)
   bị từ chối ngay — không lọt vào bất kỳ file đầu ra nào.

4. **Người duyệt bất đồng → Finalize → Retrain** — người duyệt sửa
   `disagreements.jsonl` thành `reviewed.jsonl` (thêm trường `label`), rồi:

   ```bash
   python -m livelift.nlp.label_llm finalize --consensus lot1/consensus.jsonl \
       --reviewed lot1/reviewed.jsonl --out lot1/train_extra.jsonl
   python -m livelift.nlp.train_intent   # sau khi gộp train_extra vào dataset
   ```

   File train mang trường `source` (`llm-consensus` / `human`) để mọi con số
   benchmark truy được nguồn gốc nhãn — nhãn người duyệt luôn thắng nhãn
   consensus cùng id.

## Chi phí ước tính (để lập kế hoạch, không phải cam kết)

- 14.903 bình luận × ~30 token/câu + prompt hệ thống ~1.5k token (được cache
  ở batch API) ≈ **~25–30 triệu token vào + ~1 triệu token ra cho MỖI model**
  nếu gửi từng câu; gửi theo lô 20 câu/request giảm phần prompt lặp xuống còn
  **~3–4 triệu token vào/model**.
- Với giá batch API phổ biến 2025–2026 (~$0.5–$3 /1M token vào cho các model
  hạng trung), tổng 2 model ước **dưới $30** cho toàn bộ 14.903 câu — và lô
  đầu 2.000 câu uncertain-first chỉ vài đô la.
- Chi phí thật nằm ở **người duyệt**: với tỷ lệ đồng thuận kỳ vọng 80–90%
  (theo văn liệu dưới), 2.000 câu để lại ~200–400 bất đồng ≈ 2–4 giờ duyệt.

## Văn liệu

- Quy trình LLM-as-annotator: hai model gán độc lập, giữ nhãn đồng thuận,
  người duyệt xử lý bất đồng — ACL 2024 Workshop NLP+CSS (LLM annotation cho
  dữ liệu xã hội; đồng thuận đa model cho chất lượng gần chuyên gia với chi
  phí thấp hơn nhiều lần).
- ViGoEmotions (2026): áp dụng quy trình đồng thuận LLM + người duyệt cho
  dữ liệu mạng xã hội tiếng Việt — xác nhận quy trình hoạt động trên đúng
  miền ngôn ngữ của LiveLift.

(Tóm tắt 5 dòng theo quy trình HARNESS.md §4 nằm trong `docs/research-log.md`.)

## Mốc tiếp theo (roadmap chung kết)

Đủ **2–3k nhãn đã duyệt** → fine-tune **`5CD-AI/visobert-14gb-corpus`**
(ViSoBERT pretrain trên text mạng xã hội Việt), benchmark so với TF-IDF+LogReg
hiện tại làm ablation, **xuất ONNX INT8** để suy luận CPU trong container API
— giữ nguyên chữ ký `classify` / fallback từ khóa như hiện nay.
