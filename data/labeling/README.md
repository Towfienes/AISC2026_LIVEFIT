# `data/labeling/` — các lô gán nhãn ý định

Thư mục này chứa **bình luận thật** (đã lọc PII ở tầng ingest) lấy từ các phiên
quan sát, chuẩn bị để gửi đi 2 LLM gán nhãn.

> **Chỉ file README.md này vào git.** Mọi thứ khác bị `.gitignore` chặn
> (`data/labeling/*`). Bình luận đã lọc PII vẫn là dữ liệu người dùng — chính
> sách của dự án là dữ liệu nằm trong DB, không nằm trong repo. Ai cần lô cụ
> thể thì **sinh lại** bằng lệnh ghi dưới đây, không copy file qua git.

## Lô 1 — `lot1-achan-b519f75c/`

| | |
|---|---|
| Phiên nguồn | `b519f75c-09ab-4cb4-8dff-f5c492c142be` |
| Buổi live | "Mega Live: Achan Shop Hải Phòng" — bán hàng thật, 117 phút |
| VOD | `youtube.com/watch?v=ZU_0QJzsR6w` (công khai) |
| Bình luận trong phiên | 6.586 |
| Sau khử trùng lặp | 5.340 (loại **1.246** dòng trùng id hoặc trùng text) |
| **Đã xuất** | **1.800 dòng** |
| ├ tầng `random` | **180** (10%) — mẫu ngẫu nhiên đơn giản, ước lượng prevalence **không chệch** |
| └ tầng `uncertain` | **1.620** (90%) — uncertain-first, giá trị học cao nhất |
| Seed | `2026` |
| Bộ nhãn | **11 lớp** (`livelift.nlp.labels.INTENT_LABELS`) |
| Ngày xuất | 08/09/2026 |

### File trong lô

| File | Nội dung |
|---|---|
| `comments_b519f75c.jsonl` | 6.586 bình luận đã lọc PII, đổ từ `GET /sessions/{id}/comments` |
| `batch.jsonl` | **1.800 dòng** `{"id", "text"}` — đây là file gửi cho LLM |
| `strata.jsonl` | 1.800 dòng `{"id", "stratum"}` — `random` hay `uncertain`. **Không** gửi cho LLM |
| `prompt.txt` | Prompt hệ thống hoàn chỉnh: guideline 11 lớp + ví dụ mỗi lớp + quy ước |

`batch.jsonl` cố tình **không** mang trường `stratum`: tầng ngẫu nhiên phần lớn
là `khac`, để LLM thấy được cấu trúc đó sẽ gây mỏ neo. Cùng lý do, thứ tự dòng
trong batch đã được trộn lại bằng chính seed đó.

### Sinh lại lô này

```bash
cd d:/AISC2026/livelift
# API phải đang chạy (store in-memory ⇒ phiên nằm trong tiến trình API)
.venv/Scripts/python -m uvicorn livelift.api.main:app --port 8000

# 1. đổ bình luận của phiên ra JSONL
curl -s http://127.0.0.1:8000/sessions/b519f75c-09ab-4cb4-8dff-f5c492c142be/comments \
  | python -c "import json,sys; [print(json.dumps({'comment_id':c['comment_id'],'text_scrubbed':c['text'],'intent_confidence':c['intent_confidence']},ensure_ascii=False)) for c in json.load(sys.stdin)]" \
  > data/labeling/lot1-achan-b519f75c/comments_b519f75c.jsonl

# 2. xuất lô (cùng seed ⇒ cùng 1.800 dòng, byte-for-byte)
.venv/Scripts/python -m livelift.nlp.label_llm export \
    --input data/labeling/lot1-achan-b519f75c/comments_b519f75c.jsonl \
    --out-dir data/labeling/lot1-achan-b519f75c \
    --limit 1800 --random-fraction 0.10 --seed 2026 --uncertain-first
```

Khi store là Postgres (dữ liệu nằm trong DB thật), bỏ bước 1 và dùng thẳng cờ
`--session b519f75c-09ab-4cb4-8dff-f5c492c142be` thay cho `--input`.

### Trạng thái nhãn của lô 1 (cập nhật 14/09/2026)

| | |
|---|---|
| File nhãn | `train_llm.jsonl` — **1.800 dòng** `{id, text, label, stratum, session, labeler}` |
| Người/máy gán | **LLM (Claude), một mô hình, KHÔNG có đồng thuận 2 model, KHÔNG có người duyệt** |
| Bộ nhãn | 11 lớp |
| Dùng vào | **CHỈ huấn luyện.** Không một con số đánh giá nào đo trên nhãn do AI sinh |
| Kê khai | `docs/competition/sang-tao-tre-2026/03-NLP-NANG-CAP.md` §7 (Điều 5 §5–6) |

Phân bố: `khac` 1.149 · `cam_on_khen` 382 · `chao_hoi` 173 · `hoi_daily` 40 ·
`bao_gia_shop` 33 · `hoi_sanpham` 18 · `van_chuyen` 3 · `chot_don` 1 · `hoi_gia` 1 ·
`hoi_size` 0 · `che_dat` 0.

> **Lô này nghèo ý định mua.** Phiên `b519f75c` là "mega live tâm sự": 1.800 dòng chỉ
> chứa **2** dòng ý định mua. Nó dạy được xã giao (`chao_hoi`, `cam_on_khen`), bảng giá
> shop (`bao_gia_shop`) và câu hỏi đại lý (`hoi_daily` — **nguồn duy nhất của lớp này
> trong toàn bộ dữ liệu**), nhưng **không dạy được ý định mua**. Đó là lý do bảng
> ablation A4 cho thấy bỏ bộ biên soạn đi thì macro-F1 sập 0,200.

### Bước tiếp theo cho lô này

```bash
# gửi batch.jsonl + prompt.txt đi 2 LLM độc lập -> a.jsonl, b.jsonl {id,label}
.venv/Scripts/python -m livelift.nlp.label_llm merge \
    --model-a a.jsonl --model-b b.jsonl \
    --batch data/labeling/lot1-achan-b519f75c/batch.jsonl \
    --out-dir data/labeling/lot1-achan-b519f75c
# người duyệt xử lý disagreements.jsonl -> reviewed.jsonl, rồi:
.venv/Scripts/python -m livelift.nlp.label_llm finalize \
    --consensus data/labeling/lot1-achan-b519f75c/consensus.jsonl \
    --reviewed  data/labeling/lot1-achan-b519f75c/reviewed.jsonl \
    --out       data/labeling/lot1-achan-b519f75c/train_extra.jsonl
```

## Lô 2 — `lot2-da-nguon-10-09/`

Lô **gán nhãn tay MÙ**, không phải lô gửi LLM. 393 dòng từ **ba** buổi live khác
nhau (`gT0LDiBta2k`, `1NMt8BChQrI`, `47oGShxf80A`), gộp và xáo trộn trước khi in
ra để người gán **không thấy** dự đoán của model, lớp, hay tên phiên — sửa đúng
điểm yếu phương pháp của lô 1 (gán theo từng tầng nên biết mình đang soi lớp
nào). Sinh ra §4 của `docs/benchmarks/live-fire-da-nguon.md`.

Kết quả quan trọng nhất: precision nhãn hành động **1,3% / 12,3% / 67,9%** giữa
ba buổi — nó đi theo **tỷ lệ nền** ý định mua của buổi (0,0% / 6,8% / 48,0%),
không theo model. Chi tiết trong `lot2-da-nguon-10-09/README.md`.

## Dùng hai tầng cho đúng việc

| Câu hỏi | Dùng tầng | Vì sao |
|---|---|---|
| "Bao nhiêu % chat là hỏi giá?" | **chỉ `random`** (180 dòng) | mẫu ngẫu nhiên ⇒ ước lượng không chệch |
| "Thêm dữ liệu train" | **cả hai** | nhãn nào cũng là nhãn |
| "Model sai ở đâu?" | **chủ yếu `uncertain`** | đó chính là chỗ nó kém chắc chắn nhất |

**Không bao giờ** ước lượng prevalence từ tầng `uncertain` hay từ cả lô gộp:
tầng đó cố ý lấy thiên lệch về những câu model kém nhất.

## Nợ phải trả trước khi huấn luyện lại — ✅ ĐÃ TRẢ 14/09/2026

`src/livelift/nlp/data/intent_dataset.jsonl` còn **60 dòng `khac`** viết theo bộ
6 lớp cũ; khoảng **34/60** thuộc lớp khác theo guideline 11 lớp. Phải gán nhãn
lại chúng **trước** khi train, nếu không model học hai luật mâu thuẫn cùng lúc.
Chi tiết: `docs/benchmarks/live-fire-achan.md` §5.3.

**Đã trả:** `scripts/gan_lai_nhan_11.py` gán lại **42/60 dòng** (11 → `cam_on_khen`,
4 → `chao_hoi`, 27 → `hoi_sanpham`; 18 dòng còn lại đúng là `khac`) và ghi ra
`src/livelift/nlp/data/intent_dataset_11.jsonl`. File gốc **không bị sửa** — nó là
baseline tiền đăng ký. Ước lượng cũ "34/60" hơi thấp: con số thật là 42.

```bash
.venv/Scripts/python scripts/gan_lai_nhan_11.py --kiem-tra   # chỉ kiểm tra
.venv/Scripts/python scripts/gan_lai_nhan_11.py              # ghi file
```
