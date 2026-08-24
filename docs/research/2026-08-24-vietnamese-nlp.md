# TOPIC 3 — Vietnamese NLP for LiveLift: Comment-Intent Radar + PII Filter

## Bottom-line recommended stack

| Component | Recommendation | Fallback |
|---|---|---|
| Intent classifier | **ViSoBERT** (or PhoBERT-base-v2) fine-tuned, exported to **ONNX INT8** for CPU serving | Keyword/regex baseline (below) |
| Word segmentation | **VnCoreNLP RDRSegmenter** (only if using PhoBERT; ViSoBERT skips this) | pyvi ViTokenizer |
| PII: phones | **Regex first** (E.164-normalizing), incl. obfuscation variants | — |
| PII: addresses | **Gazetteer** from `vietnamadminunits` (34-province 2025 data + 63-province legacy + mapping) | — |
| PII: person names | underthesea NER as a *supplementary* signal, low confidence on noisy text | Capitalized-token + honorific heuristic ("chị Lan", "anh Minh") |
| Normalization | Small teencode dictionary (~300 entries) + underthesea `text_normalize`; skip seq2seq for MVP | — |
| Training data | ViOCD + UIT-ViSFD for pre-finetuning; **self-labeled Live Lab comments (~2–3k)** for final head | — |

---

## (a) Intent classification: model choice and best practice

**Use ViSoBERT, not PhoBERT, as first choice.** ViSoBERT (XLM-R architecture, 5CD/UIT, EMNLP 2023) is pre-trained specifically on Vietnamese Facebook/TikTok/YouTube comments — exactly LiveLift's text distribution (teencode, no diacritics, emojis). It beats PhoBERT on every social-media benchmark tested (e.g., emotion recognition on UIT-VSMEC: 68.1% acc vs. lower PhoBERT scores) and — critically for your pipeline — **does not require Vietnamese word segmentation**, removing the VnCoreNLP/Java dependency from the real-time path. Source: [ViSoBERT (EMNLP 2023)](https://arxiv.org/abs/2310.11166).

If you use PhoBERT instead: PhoBERT-base-v2 is fine (large gives ~1pt, doubles latency); you **must** run VnCoreNLP RDRSegmenter on input first — skipping it silently costs several F1 points ([PhoBERT, EMNLP-Findings 2020](https://aclanthology.org/2020.findings-emnlp.92.pdf), [HF model card](https://huggingface.co/vinai/phobert-base)).

**Fine-tuning recipe** (both models): max_len 64 (livestream comments are short), lr 2e-5–5e-5, 3–5 epochs, class-weighted loss (buy-intent will be a minority class), early stopping on macro-F1. Published Vietnamese short-text results cluster at 86–95% accuracy: 92.16% F1 on ViOCD complaint detection, 86.1% on ViHSD hate speech, ~92.7% on phone-review sentiment ([SMTCE benchmark, 2022](https://arxiv.org/pdf/2209.10482); [ViOCD paper, 2021](https://arxiv.org/pdf/2104.11969)).

**CPU real-time inference:** there is **no official DistilPhoBERT** — community distillations exist but are unmaintained; don't bet on them. The right lever is **ONNX Runtime INT8 dynamic quantization** of your fine-tuned base model: published transformer results show up to ~6x speedup on VNNI CPUs and <50ms per inference at ~100MB memory ([Microsoft/HF ONNX quantization, 2020](https://medium.com/microsoftazure/faster-and-smaller-quantized-nlp-with-hugging-face-and-onnx-runtime-ec5525473bb7)). For a base model at seq-len 64, expect **~10–30ms/comment single-thread CPU** — at livestream comment rates (a few/sec) this is comfortable; batch by 500ms micro-windows in a Redis-fed worker. **Action:** add an `onnxruntime` inference worker service to the FastAPI stack; benchmark FP32 vs INT8 on your actual server (INT8 can regress on non-VNNI CPUs — [onnxruntime #12854](https://github.com/microsoft/onnxruntime/issues/12854)).

**Multilingual minis** (DistilmBERT, MiniLM): only ~62–66% on Vietnamese social tasks per SMTCE — not worth it. Skip.

## (b) NER tools for PII (names, addresses)

Benchmark reality check: PhoBERT-based NER hits 93.6–94.7 F1 and VnCoreNLP ~91 F1 on **VLSP 2016** — but that corpus is *newswire*. On noisy livestream comments ("ib e nhé, e ở q7 sdt 09xx…") all these tools degrade badly; none was trained on social text ([NER leaderboard](https://github.com/undertheseanlp/NLP-Vietnamese-progress/blob/master/tasks/named_entity_recognition.md); [PhoNLP, NAACL 2021](https://aclanthology.org/2021.naacl-demos.1.pdf)).

**Recommendation:** architect the PII filter as **rules-first, NER-supplementary**:
1. Regex phone detection (near-perfect recall, see (d)) — this is the PII that actually leaks in live commerce ("để lại sđt em tư vấn").
2. Gazetteer address detection (see (c)).
3. **underthesea** `ner()` as third layer for PER entities — pure-Python pip install, fits FastAPI cleanly; VnCoreNLP needs a Java sidecar and PhoNLP needs a GPU-ish PyTorch stack for marginal gain on out-of-domain text. pyvi has no NER at all.
4. Honorific heuristic: token after "anh/chị/em/cô/chú/bác/bạn" + capitalized word → probable name (cheap, high precision on comments).

**Why:** you need high **recall** on phones/addresses (compliance risk) and only moderate recall on names (lower harm); rules give you auditable recall where it matters, and you avoid shipping a Java dependency in the hot path. Mask, don't drop: replace with `[SĐT]`, `[ĐỊA CHỈ]`, `[TÊN]` tokens before storage/PhoBERT input.

## (c) Address gazetteer — the 2025 merger matters

On 2025-07-01 Vietnam merged 63 provinces → **34**, **abolished districts entirely**, and consolidated wards ([2025 Vietnamese administrative reforms, Wikipedia](https://en.wikipedia.org/wiki/2025_Vietnamese_administrative_reforms)). Viewers will type **both old and new** unit names for years ("quận 7" no longer officially exists but everyone still says it). Therefore load **both** lists:

- **[`vietnamadminunits`](https://github.com/tranngocminhhieu/vietnamadminunits)** (PyPI) — purpose-built for post-merger e-commerce address standardization: parses free-text addresses, ships 63-province legacy data, 34-province current data, and the old→new mapping table; tolerant of missing diacritics/case. **Use this as the canonical dictionary source.**
- [`thanglequoc/vietnamese-provinces-database`](https://github.com/thanglequoc/vietnamese-provinces-database) — SQL dumps (updated to Decree 30/2026/QH16) if you'd rather seed PostgreSQL directly.

**Detection design:** flag a comment as address-PII when it contains (ward/province name from either list) **AND** (a street cue: "số", "đường", "ngõ", "hẻm", "thôn", "xóm", digits+"/"), to avoid false-positives on bare place mentions ("hàng ship về Hà Nội không?" is a question, not PII).

## (d) Phone regex

Since Nov 2018 all VN mobiles are 10 digits with prefixes 03x/05x/07x/08x/09x. Base pattern (national + international):

```
(?:\+84|0084|84|0)(3[2-9]|5[2589]|7[06-9]|8[1-9]|9[0-46-9])\d{7}\b
```

([tungvn gist](https://gist.github.com/tungvn/2460c5ba947e5cbe6606c5e85249cf04); [sent.dm VN format guide](https://www.sent.dm/resources/vn)). **Livestream-specific hardening** (people evade filters): before matching, strip separators `[.\-\s]` between digit groups; map digit-words "không/một/hai/…/chín" and "o/O" → 0; catch zalo-style "09xx xxx xxx". Normalize hits to E.164 for logging. Target: ≥98% recall on your Live Lab logs — measure it, it's an easy audited metric for judges.

## (e) Training datasets

No public **Vietnamese livestream purchase-intent** dataset exists (verified by search — literature is all survey-based purchase-intention studies). Plan accordingly:

- **[UIT-ViOCD](https://nlp.uit.edu.vn/datasets/)** (2021) — 5,485 e-commerce comments, complaint/non-complaint; PhoBERT F1 92.16% — nearest domain match; use for pre-finetuning the "complaint" head.
- **[UIT-ViSFD](https://nlp.uit.edu.vn/datasets/)** (2021) — 11,122 smartphone-feedback comments, aspect-based sentiment (price/shipping/quality aspects map well to intents like `ask_price`, `ask_shipping`).
- **[UIT-VSMEC](https://github.com/kietnv/VietnameseDatasets)** (2019) — 6,927 social comments, 7 emotions — useful for a hype/negativity signal on the radar.
- **Your own Live Lab labels are non-negotiable:** with 30 sessions × 90min you'll collect tens of thousands of comments; label **2–3k** across a compact taxonomy (`buy_intent`, `ask_price`, `ask_size/variant`, `ask_shipping`, `complaint`, `hype/emoji`, `spam/other`) with 2 annotators + adjudication (ViOCD reached κ=0.87; report yours — judges love measured IAA). Bootstrap labeling with the keyword baseline (weak supervision), then correct.

## (f) Teencode normalization

- **[ViLexNorm](https://aclanthology.org/2024.eacl-long.85/)** (EACL 2024) — 10,467 annotated comment pairs; best seq2seq system only reaches 57.74% ERR, and **[ViSoLex](https://arxiv.org/html/2501.07020)** (2025) packages semi-supervised normalizers. Verdict: full ML normalization is immature — **don't put a seq2seq normalizer in the real-time path.**
- **Practical MVP:** a ~300-entry dictionary ("ko/k/hong→không", "sz→size", "ib/inb→nhắn tin", "stk→số tài khoản", "sđt/sdt→số điện thoại", "bn tien→bao nhiêu tiền") + underthesea [`text_normalize`](https://github.com/undertheseanlp/normalization) for Unicode/diacritic canonicalization; mine additional entries from ViLexNorm pairs. This mainly boosts the **keyword baseline and PII rules**; ViSoBERT itself needs little normalization since it was pre-trained on raw social text — another argument for choosing it.

## Fallback keyword baseline (ship this first)

Regex/dictionary classifier over normalized text: `buy_intent`: "chốt", "lấy 1", "order", "mua", "còn hàng ko", "để em 1 cái"; `ask_price`: "bn tiền", "giá", "nhiêu"; `ask_variant`: "size", "màu", "sz M"; `ask_shipping`: "ship", "bao lâu", "cod"; `complaint`: "bóc phốt", "lừa", "tệ", "hoàn tiền". Value: (1) day-one radar while you collect labels; (2) weak-labeling source; (3) published ablation baseline (expect macro-F1 ~0.55–0.65 vs. transformer ~0.85) proving the ML component earns its complexity; (4) graceful degradation if the model worker dies mid-stream.

## Realistic accuracy targets to commit to

- Intent (7 classes, 2–3k labels + ViOCD/ViSFD pre-finetune): **macro-F1 0.80–0.88** (in line with 86–92% on comparable UIT short-text tasks).
- PII phones (regex): **recall ≥0.98**, precision ≥0.95.
- PII addresses (gazetteer+cues): **recall ≥0.85**.
- Person names (NER+heuristics): recall ~0.7 — acceptable given low standalone harm; state this honestly.
- Latency: **<50ms/comment CPU** (ONNX INT8, seq-len 64), radar aggregation per 5-min block well within budget.

Sources: [PhoBERT (EMNLP-Findings 2020)](https://aclanthology.org/2020.findings-emnlp.92.pdf) · [ViSoBERT (EMNLP 2023)](https://arxiv.org/abs/2310.11166) · [PhoNLP (NAACL 2021)](https://aclanthology.org/2021.naacl-demos.1.pdf) · [SMTCE (2022)](https://arxiv.org/pdf/2209.10482) · [ViOCD (2021)](https://arxiv.org/pdf/2104.11969) · [UIT datasets](https://nlp.uit.edu.vn/datasets/) · [ViLexNorm (EACL 2024)](https://aclanthology.org/2024.eacl-long.85/) · [ViSoLex (2025)](https://arxiv.org/html/2501.07020) · [vietnamadminunits](https://github.com/tranngocminhhieu/vietnamadminunits) · [vietnamese-provinces-database](https://github.com/thanglequoc/vietnamese-provinces-database) · [2025 admin reforms](https://en.wikipedia.org/wiki/2025_Vietnamese_administrative_reforms) · [VN phone regex gist](https://gist.github.com/tungvn/2460c5ba947e5cbe6606c5e85249cf04) · [HF+ONNX INT8 quantization](https://medium.com/microsoftazure/faster-and-smaller-quantized-nlp-with-hugging-face-and-onnx-runtime-ec5525473bb7) · [VN NER leaderboard](https://github.com/undertheseanlp/NLP-Vietnamese-progress/blob/master/tasks/named_entity_recognition.md)