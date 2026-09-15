# BẢN KÊ KHAI CÔNG CỤ AI, BỘ DỮ LIỆU, API, THƯ VIỆN VÀ MÃ NGUỒN MỞ

**Sản phẩm:** LiveLift — nền tảng thí nghiệm vận hành cho livestream thương mại
**Đội thi:** Ngô Bình Minh (đội trưởng) · Lê Xuân Khánh · Ngô Lâm Tiến — Khoa CNTT, Đại học Tôn Đức Thắng
**Bảng:** C (19–22 tuổi) · Khu vực miền Nam
**Kho mã nguồn:** `https://github.com/bminhnemhoi/AISC2026_LIVEFIT` (xem hạng mục 4 — [`06-KHO-MA-VA-MINH-CHUNG.md`](06-KHO-MA-VA-MINH-CHUNG.md))
**Ngày lập:** 14/09/2026 · **Trạng thái mã nguồn tại thời điểm kê khai:** commit `dd66b38`, 42 commit

---

## Cơ sở pháp lý của bản kê khai

Bản kê khai này lập theo **Điều 5 Thể lệ Cuộc thi Sáng tạo trẻ Quốc gia trong lĩnh vực AI 2026**
(Kế hoạch số 01-KH/TWĐTN-KHCN ngày 03/7/2026), cụ thể:

- **§5–6:** đội được phép dùng LLM, thư viện mở, mô hình pretrained, dataset công khai và API
  **nếu kê khai trung thực**, nêu rõ **phần tự xây dựng / phần do AI hoặc công cụ hỗ trợ tạo ra /
  phần kế thừa từ nguồn mở**, và chứng minh được khả năng **hiểu, kiểm chứng, chỉnh sửa, vận hành
  và chịu trách nhiệm** với sản phẩm.
- **§7:** **che giấu nguồn mã nguồn, dataset hoặc API là hành vi bị nghiêm cấm.**

Nguyên tắc biên soạn: **thà kê khai thừa một mục bất lợi còn hơn thiếu một mục.** Mọi con số trong
tài liệu này sinh lại được bằng lệnh và trỏ về `docs/competition/FACT-SHEET.md` — bộ số chuẩn duy
nhất của dự án. Các mục đánh dấu ⚠️ là **điểm bất lợi do đội tự khai**, không phải do người khác
phát hiện.

---

## I. CÔNG CỤ AI SỬ DỤNG TRONG QUÁ TRÌNH PHÁT TRIỂN

### I.1. Công cụ chính

| Hạng mục | Kê khai |
|---|---|
| **Tên công cụ** | **Claude Code** (Anthropic) — CLI lập trình có agent |
| **Phiên bản** | `2.1.251` (ghi trong trường `version` của mọi bản ghi nhật ký phiên) |
| **Mô hình nền** | Họ mô hình Claude (Anthropic), truy cập qua `api.anthropic.com` |
| **Vai trò** | Cặp lập trình (pair programmer): soạn nháp mã, soạn nháp tài liệu, khảo cứu tài liệu khoa học, chạy lệnh kiểm thử dưới sự điều khiển của đội |
| **Phạm vi** | Toàn bộ vòng đời: hạ tầng, API, giao diện web, thống kê, NLP, tài liệu |
| **Hình thức trả phí** | Thuê bao cá nhân của đội trưởng |
| **Bằng chứng** | 3 phiên làm việc chính, **1.297 câu lệnh của đội**, **~2.345 lượt phản hồi**, **289 nhật ký tiến trình con**, tổng **191 MB** nhật ký thô — xuất ra dạng đọc được bằng `scripts/xuat_prompt_log.py` |

**⭐ Bằng chứng khai báo mạnh nhất — ghi thẳng trong lịch sử commit:**

**42/42 commit (100%) đều mang trailer đồng tác giả AI**, kiểm chứng được bằng một lệnh
(`git log --format="%b" | grep -i "Co-Authored-By"`):

| Trailer | Số commit |
|---|---:|
| `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>` | 29 |
| `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>` | 12 |
| `Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>` | 1 |
| **Tổng** | **42 / 42** |

Nghĩa là: **đội đã khai báo sự tham gia của AI ngay tại thời điểm viết mã**, trong từng commit,
suốt 22 ngày — **trước khi biết đến yêu cầu kê khai của cuộc thi**, chứ không phải khai lùi lại
sau khi đọc thể lệ. Đây là bằng chứng không thể ngụy tạo về sau (sửa trailer sẽ viết lại toàn bộ
hash lịch sử — chính là hành vi "giả mạo commit history" mà Điều 5 §7 cấm, và đội **không** làm).

**Nhật ký phiên (Prompt Log) — kê khai đầy đủ, không cắt xén:**

| Phiên | Khoảng thời gian | Lượt hội thoại | Câu lệnh của đội |
|---|---|---:|---:|
| `feb901dc-ddba-415c-9bd7-c845e5b2221c` | 24/08/2026 → 03/09/2026 | 1.368 | 584 |
| `3c773cb8-b1eb-4198-afb3-95cac7974ee1` | 06/09/2026 → 14/09/2026 | 1.566 | 680 |
| `3b0c8ccf-f9f0-4c53-b50c-f83d4ccb3720` | 14/09/2026 | 71 | 33 |
| **Tổng** | **22 ngày** | **≈3.059** | **≈1.297** |

*(Phiên 14/09 vẫn đang chạy khi lập bảng — số cuối cùng lấy lại bằng `python scripts/xuat_prompt_log.py --kiem-tra` ngay trước khi nộp.)*

⚠️ **Về "System Prompt" mà thể lệ yêu cầu (mục 7, mục 13 MẪU 3):** system prompt của nhà cung cấp
Claude Code **không được lưu trong nhật ký phiên và đội không có quyền truy cập** — đội không thể
nộp thứ mình không có, và không bịa ra một bản thay thế. Cái đội **có** và nộp là:

1. **`HARNESS.md`** — bản hợp đồng quy trình do đội tự viết, đóng vai trò chỉ dẫn hệ thống ở cấp
   dự án: mọi phiên làm việc đều bắt đầu bằng việc trỏ công cụ AI vào file này. Đây là "system
   prompt" thực tế của dự án.
2. **Toàn bộ 1.297 câu lệnh nguyên văn** của đội (đã lọc dữ liệu cá nhân — xem §VIII.4).

### I.2. Công cụ AI KHÔNG sử dụng — kê khai để loại trừ hiểu nhầm

| Công cụ | Trạng thái |
|---|---|
| API LLM gọi từ trong sản phẩm | **KHÔNG CÓ.** Không một dòng mã nào trong repo gọi API LLM. `src/livelift/analysis/narrate.py` sinh câu tường thuật bằng **template chuỗi**, không phải mô hình sinh |
| Nền tảng no-code / low-code | Không dùng |
| Mô hình pretrained tải từ HuggingFace | **Chưa dùng.** ViSoBERT (EMNLP 2023) chỉ nằm trong lộ trình nâng cấp, chưa tích hợp |
| Dịch vụ AI của bên thứ ba trong đường chạy | Không có |

⚠️ **Một ngoại lệ phải khai:** `src/livelift/nlp/label_llm.py` **chuẩn bị** lô dữ liệu để đội **tự
tay** gửi sang 2 LLM bất kỳ (quy trình LLM-as-annotator, đồng thuận 2 mô hình + người duyệt bất
đồng). Module này **không chứa lời gọi mạng nào**; việc gửi/nhận là thao tác thủ công ngoài repo.
Đến 14/09/2026 quy trình này **chưa chạy trên lô thật** — mọi nhãn hiện có đều do **người gán tay**.

---

## II. MÔ HÌNH AI

Toàn bộ dự án có **đúng một mô hình học máy**. Đội đã rà soát toàn bộ mã nguồn tìm mọi điểm tải
checkpoint (`joblib`, `pickle`, `.onnx`, `from_pretrained`, `torch.load`) — kết quả dưới đây là đầy đủ.

| Hạng mục | Kê khai |
|---|---|
| **Tên** | Bộ phân loại ý định bình luận tiếng Việt (`intent_clf`) |
| **Kiến trúc** | TF-IDF ký tự `char_wb` 2–5-gram ⊕ TF-IDF từ 1–2-gram (`FeatureUnion`) → `LogisticRegression` (`C=4.0`, `class_weight="balanced"`, `max_iter=2000`) |
| **Nguồn** | **ĐỘI TỰ HUẤN LUYỆN.** Không kế thừa trọng số từ bất kỳ mô hình pretrained nào |
| **Mã huấn luyện** | `src/livelift/nlp/train_intent.py` — chạy lại được bằng `python -m livelift.nlp.train_intent` |
| **Dữ liệu huấn luyện** | `src/livelift/nlp/data/intent_dataset.jsonl` — **320 câu do đội tự biên soạn** (xem §III.2) |
| **Artifact** | `src/livelift/nlp/model/intent_clf.joblib` (86 KB) + sidecar `intent_clf.meta.json` |
| **Seed** | `2026` — tái lập bit-for-bit |
| **Huấn luyện lúc** | 2026-09-06T16:04:26Z, scikit-learn 1.9.0 (ghi trong sidecar) |
| **Giấy phép** | Cùng giấy phép sản phẩm: **AGPL-3.0-only** |
| **Vai trò trong hệ thống** | **Phụ trợ.** "Radar ý định" trên bảng điều khiển + biến hiệp biến khám phá. **KHÔNG tham gia vào ước lượng nhân quả** — con số thí nghiệm của LiveLift không phụ thuộc mô hình này |
| **Cơ chế dự phòng** | Khi thiếu artifact hoặc thiếu `scikit-learn`, hệ thống tự lùi về baseline từ khóa (`classify_keywords`) — không sập |

### ⚠️ II.1. Hiệu năng thật — kê khai CẶP SỐ, không quote riêng số đẹp

| Đo trên | macro-F1 | Ghi chú |
|---|---:|---|
| 320 câu **tự biên soạn**, 5-fold CV | **0,870** | Con số "đẹp" — chỉ có giá trị nội bộ |
| **200 bình luận CHAT THẬT** gán nhãn tay mù | **0,271** | **Thua cả baseline luôn đoán lớp "khác"** |

Đội chủ động công bố cả hai và **quy định trong `FACT-SHEET.md`: không bao giờ quote riêng 0,870**.
Nguyên nhân đã xác định: dữ liệu biên soạn không phản ánh phân bố chat thật (chat thật đa số là
chào hỏi/tán gẫu, không phải câu hỏi mua hàng). Lộ trình sửa đã có mã chạy được
(`label_llm.py` + active learning), chưa hoàn thành. **Đây là hạn chế đội tự nêu, không giấu.**

### II.2. Mô hình cân nhắc nhưng CHƯA dùng

| Mô hình | Nguồn | Trạng thái |
|---|---|---|
| ViSoBERT `5CD-AI/visobert-14gb-corpus` | HuggingFace, EMNLP 2023 | Lộ trình — sẽ fine-tune khi có 2–3k nhãn thật, đối chứng với mô hình hiện tại làm ablation |
| `underthesea` | PyPI, GPL-3.0 | Khai báo trong extra `[nlp]` của `pyproject.toml` nhưng **KHÔNG được import ở bất kỳ đâu** và **không được cài** trong môi trường chạy. ⚠️ Đây là khai báo thừa — đội đề nghị gỡ khỏi `pyproject.toml` |

---

## III. BỘ DỮ LIỆU

### III.1. Tổng quan — 5 nguồn dữ liệu

| # | Bộ dữ liệu | Nguồn | Quy mô | Có dữ liệu cá nhân? |
|---|---|---|---:|---|
| 1 | Bình luận livestream thật | VOD công khai YouTube | 19.126 bình luận / 16 buổi | **CÓ** ⚠️ |
| 2 | Bộ nhãn ý định | Đội tự biên soạn | 320 câu | Không |
| 3 | Lô gán nhãn **thủ công** | Trích từ (1) | **393 dòng** (3 buổi, bộ TEST) | **CÓ** ⚠️ |
| 4 | Dữ liệu mô phỏng | Sinh bằng mã, có seed | Không giới hạn | Không |
| 5 | KuaiLive (tham chiếu hiệu chỉnh) | Zenodo 16565801 | 1,16 triệu phòng live | Đã ẩn danh sẵn |
| **6** | **Lô gán nhãn do LLM sinh** ⚠️ | Trích từ (1), nhãn do **AI** gán | **1.800 dòng** (1 buổi, chỉ TRAIN) | **CÓ** ⚠️ |

#### ⚠️ (6) Lô nhãn do AI sinh — kê khai bắt buộc theo Điều 5 §5–6

*Tạo 14/09/2026. Nguồn sự thật đầy đủ: [`03-NLP-NANG-CAP.md`](03-NLP-NANG-CAP.md) §7.*

| Hạng mục | Kê khai |
|---|---|
| **Việc AI làm** | Gán nhãn 11 lớp cho **1.800 bình luận thật** của phiên `b519f75c` → `data/labeling/lot1-achan-b519f75c/train_llm.jsonl` |
| **Mô hình** | Claude (Anthropic) qua Claude Code — cùng công cụ đã kê khai ở §I.1 |
| **Đội tự làm** | Guideline 11 lớp (`src/livelift/nlp/labels.py`); rút mẫu hai tầng có seed; quy ước cho ca mơ hồ; hợp nhất + kiểm tra phân bố; **quyết định lô này CHỈ dùng để train** |
| **Dùng vào đâu** | **Chỉ huấn luyện.** Không một con số đánh giá nào trong hồ sơ đo trên nhãn do AI sinh — tập test là 393 dòng **người** gán, ở **buổi live khác** |
| ⚠️ **Hạn chế đội tự khai** | (a) **một** mô hình, **không** đồng thuận 2 LLM, **không** người duyệt — trái với chính quy trình đội đã thiết kế trong `label_llm.py`; (b) quy ước gán nhãn được hiệu chuẩn bằng cách **đọc nhãn của tập test**, nên lợi ích đo được của lô này **mang thiên lệch lạc quan**; (c) lô nghèo ý định mua (1.800 dòng chỉ có 2 dòng ý định mua) |
| **Kiểm chứng được không** | Có. File nhãn nằm trên đĩa, phân bố in ra bằng lệnh, và bảng ablation A3 đo riêng phần đóng góp của nó (accuracy 0,608 → 0,741; precision nhãn hành động 46,2% → 66,7%) |

### III.2. Chi tiết từng bộ

#### (1) Bình luận livestream thật — 19.126 bình luận · 16 buổi live · 7 ngành hàng

| Hạng mục | Kê khai |
|---|---|
| **Nguồn** | Chat replay của **VOD công khai** trên YouTube (video đã kết thúc phát, chat replay ở chế độ công khai) |
| **Cách thu thập** | Tải track phụ đề `live_chat` bằng **yt-dlp**, nạp qua `POST /replays/youtube` (`src/livelift/ingest/youtube_replay.py`) |
| **Cách chọn mẫu** | 6 buổi từ lô 08/09 + 11 buổi tìm bằng 4 truy vấn tiếng Việt (thời trang / mỹ phẩm / gia dụng), lọc lấy video có track `live_chat`. 17 video đẩy qua API → 16 nạp được, 1 lỗi, **chỉ 7/16 đạt ≥100 bình luận** |
| **Buổi lớn nhất** | `ZU_0QJzsR6w` — "Mega Live: Achan Shop Hải Phòng", 117 phút, **6.586 bình luận** |
| **Lưu ở đâu** | CSDL vận hành + `data/labeling/` (cả hai **đều bị `.gitignore`** — không vào kho mã) |
| **Cơ sở pháp lý đội viện dẫn** | **Nghị định 13/2023/NĐ-CP** (thu thập) và **Luật 91/2025/QH15 + NĐ 356/2025/NĐ-CP** (xử lý): **khử nhận dạng ngay tại điểm thu thập + lợi ích chính đáng cho nghiên cứu học thuật phi thương mại**. ⚠️ Đội **KHÔNG tự nhận là đã có sự đồng ý** của người bình luận — một bản nháp trước đây từng coi thông báo trong phòng live là "đồng ý", đội đã **tự phát hiện và sửa** (ghi trong `docs/competition/thuyet-minh/noi-dung.json`) |
| **Dùng để làm gì** | Chỉ **phân tích quan sát** (`design.analysis_only=true`). Không gán ngẫu nhiên, **không sinh ra bất kỳ con số nhân quả nào** — có cổng chặn ở `api/routes/reports.py` |
| **Định danh người bình luận** | **Không bao giờ lưu.** `parse_live_chat_line` chỉ bóc `offset` + `text`; trường `authorName`/`authorExternalChannelId` bị loại ngay tại tầng parse. File tải về bị xóa ngay sau khi parse |

**⚠️ RỦI RO PHÁP LÝ QUAN TRỌNG NHẤT — PHƯƠNG THỨC THU THẬP TRÁI ĐIỀU KHOẢN DỊCH VỤ YOUTUBE**

Đội kê khai thẳng, vì §7 Điều 5 cấm che giấu nguồn:

- **Toàn bộ 19.126 bình luận** — nghĩa là **100% dữ liệu thật của dự án** — được thu bằng **yt-dlp**.
- Điều khoản dịch vụ YouTube cấm truy cập dịch vụ "bằng bất kỳ phương thức tự động nào" trừ khi
  theo `robots.txt` hoặc được YouTube cho phép trước bằng văn bản. `https://www.youtube.com/robots.txt`
  (kiểm tra 09/09/2026) **chặn đúng hai đường mà yt-dlp gọi**: `/live_chat` và `/youtubei/`.
  ⇒ **Ngoại lệ robots.txt không bao trùm cách làm này.**
- Repo đã tự ghi nhận điều này rất rõ trong `src/livelift/ingest/youtube_ytdlp.py` (đường live).
- ⚠️ **Nhưng** `src/livelift/ingest/youtube_replay.py` — module thật sự sinh ra 100% dữ liệu —
  **hiện KHÔNG có cảnh báo điều khoản nào**, dù dùng đúng cơ chế yt-dlp đó.
- ⚠️ **Nghiêm trọng hơn:** module replay có đường `YTDLP_COOKIES_FROM_BROWSER` hướng dẫn nạp
  **cookie đăng nhập YouTube của chính thành viên đội** để vượt kiểm tra chống bot. Dùng phiên đã
  đăng nhập để vượt biện pháp chống tự động hóa là mức vi phạm **nặng hơn** truy cập ẩn danh, và
  gắn trách nhiệm vào tài khoản cá nhân của thành viên.
- ⚠️ Tài liệu thuyết minh hiện ghi đường yt-dlp "chỉ dùng kiểm thử kỹ thuật, không đưa vào hồ sơ
  dự thi" — **câu này mâu thuẫn với thực tế** và phải sửa trước khi nộp.

**Khuyến nghị xử lý của đội (đã đánh giá 3 phương án):**

| Phương án | Đánh giá |
|---|---|
| Giấu, không kê khai | **Loại ngay** — vi phạm §7, rủi ro bị loại đội |
| Gỡ bỏ toàn bộ dữ liệu yt-dlp | Mất 100% bằng chứng thực nghiệm, không kịp thu lại trước hạn |
| **Kê khai minh bạch + rào chắn + sửa lời văn** ✅ | **Chọn phương án này** |

Cụ thể: (a) giữ nguyên dữ liệu đã thu và **khai đúng phương thức** ở mọi nơi trích số;
(b) **tắt `YTDLP_COOKIES_FROM_BROWSER` mặc định** và ghi cảnh báo điều khoản vào
`youtube_replay.py` ngang mức module live; (c) sửa câu mâu thuẫn trong thuyết minh;
(d) **xin `YOUTUBE_API_KEY`** (miễn phí, ~10 phút, không cần app review) và tuyên bố API v3 là
đường chính thức cho mọi phiên từ nay; (e) **không mở rộng quy mô thu** bằng đường này.

#### ⚠️ (3) Lô gán nhãn thủ công — PHÁT HIỆN RÒ RỈ DỮ LIỆU CÁ NHÂN

Đội **mở file dữ liệu ra kiểm trực tiếp** thay vì tin tài liệu, và tìm thấy lỗi:

**Kết quả kiểm `data/labeling/lot1-achan-b519f75c/comments_b519f75c.jsonl` (6.586 dòng):**

| Loại | Kết quả |
|---|---|
| Số điện thoại còn sót | **0** ✅ |
| Email còn sót | **0** ✅ |
| Nhãn `[MXH]` đã che thành công | 123 |
| ⚠️ **Handle mạng xã hội CÒN SÓT** | **53 (37 handle duy nhất)** ❌ |

Ví dụ còn nguyên trong dữ liệu trên đĩa (tên đã che khi đưa vào kho mã — bản gốc là tài khoản thật): `@Cư***`, `@Ng***`, `@Gi***`,
`@Ki***`, `@Bạ***-…`, `@Ng***`, `@DŨ***`, `@Hư***`.
**Mỗi handle này mở thẳng ra một kênh YouTube cụ thể** ⇒ là **định danh trực tiếp** một con người
theo Nghị định 13/2023/NĐ-CP, không phải dữ liệu đã ẩn danh.

**Nguyên nhân gốc (đã truy đến dòng mã):**

```python
# src/livelift/ingest/pii/patterns.py:198
SOCIAL_HANDLE_RE = re.compile(r"(?<![\w.@])@[A-Za-z0-9_.]{3,32}\b")
```

Lớp ký tự **chỉ có ASCII** — không có chữ tiếng Việt có dấu, không có dấu gạch ngang `-`. Mà handle
YouTube tiếng Việt thì gần như luôn có dấu và thường có hậu tố `-xxx`.

**Vì sao cổng chất lượng không bắt được:** `HARNESS.md` §2 quy định cổng "PII recall ≥ 95% từng loại"
nhưng chỉ liệt kê **SĐT, email, mã đơn, địa chỉ** — **không có loại "handle mạng xã hội"**. Bộ
đánh giá `tests/data/pii_comments.jsonl` (95 dòng) cũng **không có nhãn `social`**, và test hiện có
chỉ kiểm handle ASCII (`@hoa_nguyen`). **Lỗi lọt qua vì không ai đo nó**, không phải vì bộ lọc hỏng.

**Phạm vi ảnh hưởng (đã khoanh vùng bằng máy):**

| Nơi | Trạng thái |
|---|---|
| Kho mã GitHub | ✅ **SẠCH** — `data/labeling/*` bị `.gitignore`, không handle nào vào git |
| `data/snapshot/livelift-store.json` | ✅ **SẠCH** — quét 1,77 triệu ký tự: 0 handle, 0 số điện thoại |
| `data/labeling/lot1-…/comments_*.jsonl` (trên đĩa) | ❌ **CÓ 53 handle** |
| Nhật ký phiên Claude Code | ❌ **2 / 292 file** có chứa handle thật |

**Việc phải làm (chi tiết trong [`06-KHO-MA-VA-MINH-CHUNG.md`](06-KHO-MA-VA-MINH-CHUNG.md) §P0):**
sửa regex thành lớp ký tự Unicode + `-`, thêm loại `social` vào bộ đánh giá và vào cổng
`HARNESS.md` §2, rồi **chạy lại bộ lọc trên dữ liệu đã lưu**.

#### (2) Bộ nhãn ý định tự biên soạn — 320 câu

Do **3 thành viên tự viết**, mô phỏng văn phong chat bán hàng tiếng Việt (có/không dấu, teencode,
lỗi chính tả). 6 lớp: `hoi_gia`, `hoi_size`, `che_dat`, `chot_don`, `van_chuyen`, `khac`.
**Không cào từ đâu, không sinh bằng LLM.** Không chứa dữ liệu cá nhân. Giấy phép: AGPL-3.0 theo repo.

#### (4) Dữ liệu mô phỏng

Sinh bằng `src/livelift/sim/simulator.py`, **mọi RNG nhận seed tường minh**, tái lập bit-for-bit.
Tham số phân bố hiệu chỉnh theo KuaiLive (xem dưới). Không chứa dữ liệu người thật. Dùng để thẩm
định ước lượng viên (A/A 200 lặp, độ phủ KTC, MDE).

#### (5) KuaiLive — dữ liệu tham chiếu để hiệu chỉnh mô phỏng

| Hạng mục | Kê khai |
|---|---|
| **Tên đầy đủ** | KuaiLive: A Real-time Interactive Dataset for Live Streaming Recommendation |
| **Công bố** | **SIGIR '26**, arXiv:2508.05633, DOI `10.1145/3805712.3808587` |
| **Tải từ** | **Zenodo record 16565801** (858,2 MB, MD5 `9f0f13950f677a0d9d2224c3e7abb553`) — **công khai, không cần đăng ký hay ký thỏa thuận** |
| ⚠️ **Giấy phép** | **MÂU THUẪN giữa hai nguồn:** trang dự án & bài báo ghi **CC BY-NC-SA 4.0**; metadata Zenodo ghi **CC BY 4.0**. **Đội áp dụng phương án thận trọng: coi là NC (phi thương mại)** — hợp lệ cho dự thi sinh viên, **cấm đóng gói vào bản thương mại LiveLift**. Đội **chưa liên hệ tác giả để xác minh** — đây là việc cần làm |
| **Dùng để làm gì** | Hiệu chỉnh **3 tham số phân bố** của mô phỏng: thời gian ở lại trung bình (6→10 phút), tỷ lệ bình luận/người xem/phút (0,25→0,016), tỷ lệ like (0,014) |
| **Đội KHÔNG dùng để làm gì** | ⚠️ Có **lệnh cấm được mã hóa thẳng vào mã nguồn** (`analysis/power.py:412`, `PREREGISTRATION.md:177`): **cấm ánh xạ KuaiLive lên phễu mua hàng** — vì "click" của KuaiLive là *vào phòng*, không phải *bấm sản phẩm ghim*. Đây là quyết định phương pháp luận của đội |
| **Dữ liệu cá nhân** | Bộ dữ liệu đã ẩn danh sẵn tại nguồn (ID số). **Không tái phân phối** — `data/raw/` bị `.gitignore` |

#### (6) Nguồn tham chiếu khác — chỉ lấy CON SỐ từ bài báo, không lấy dữ liệu

| Nguồn | Lấy gì | Ghi chú |
|---|---|---|
| **Taobao UserBehavior** (Alibaba Tianchi #649) | Tiên nghiệm phễu: pv→cart 9,33% × cart→buy 24,33% ≈ 2,3% | Dùng cho bảng MDE đơn hàng. Không tải dữ liệu về |
| **LSEC** (KDD 2021, arXiv:2106.03415) | Hệ số nhân khán giả ×4,9 | ⚠️ **Bộ dữ liệu bị đội TỪ CHỐI**: không có timestamp + **không có giấy phép** ⇒ rủi ro khi tái phân phối số dẫn xuất. Chỉ trích số từ bài báo đã xuất bản |
| KuaiLive-M3, LiveRec, KuaiRec, KuaiRand, YTLive, UIT-ViOCD, UIT-ViSFD, ViHSD | **Không dùng** | Có khảo sát, ghi trong `docs/research/2026-08-24-datasets-simulation.md`, quyết định bỏ qua |

#### (7) VLiveBench (TikTok) — kê khai một nỗ lực THẤT BẠI

Đội có viết bộ thu thập phòng live TikTok công khai (`collectors/tiktok_public/`) dùng thư viện
**`TikTokLive`** — thư viện **dịch ngược (reverse-engineered)**, không phải API chính thức, định
tuyến qua proxy bên thứ ba **Euler Stream**. ⚠️ Việc dùng **có thể vi phạm điều khoản TikTok**.

**Kết quả thật: WebSocket bị từ chối HTTP 400 trong 10/10 lần thử (09/09/2026) — thu được 0 bình luận.**
Thư viện **không được cài** trong môi trường chạy. Mã vẫn còn trong repo, **cách ly hoàn toàn**
(venv riêng, tiến trình riêng, có cổng CI `scripts/check_isolation.py` chặn `src/` import từ
`collectors/`). **Không một con số nào trong hồ sơ đến từ nguồn này.**
**Khuyến nghị:** giữ mã + README cảnh báo (là bằng chứng trung thực về một hướng đã thử và thất
bại), **không** đưa vào đường chạy mặc định.

---

## IV. API BÊN NGOÀI

Đội đã quét toàn bộ mã nguồn tìm mọi lời gọi mạng ra ngoài. Danh sách dưới đây là **đầy đủ**.

| # | API | Endpoint | Xác thực | Giới hạn | Điều khoản cho phép? | Đã chạy thật? |
|---|---|---|---|---|---|---|
| 1 | **YouTube Data API v3** | `https://www.googleapis.com/youtube/v3` · `/videos`, `/liveChat/messages` | API key (`YOUTUBE_API_KEY`) trong query | **10.000 đơn vị/ngày**; ~5 đơn vị/lệnh; poll tối thiểu 2s; phải tôn trọng `pollingIntervalMillis` | ✅ **CÓ** — API chính thức, dùng trong hạn ngạch được cấp. `search.list` bị **cấm trong mã** (tốn 100 đơn vị/lệnh) | ❌ Chưa — đội **chưa có API key** |
| 2 | ⚠️ **YouTube qua yt-dlp** (live) | `youtube.com/live_chat`, `/youtubei/` | Không | Không | ❌ **KHÔNG** — `robots.txt` chặn đúng 2 đường này | ✅ 1 phiên kiểm thử (104 bình luận, 09/09) |
| 3 | ⚠️ **YouTube qua yt-dlp** (VOD replay) | track `live_chat` của VOD | Không (tùy chọn: cookie trình duyệt ⚠️) | Không | ❌ **KHÔNG** — cùng cơ chế với (2) | ✅ **19.126 bình luận / 16 buổi — 100% dữ liệu thật của dự án** |
| 4 | **Facebook Graph API** | `https://graph.facebook.com/v25.0` · `/{page_id}/live_videos`, `/{id}/comments` | Bearer token trong **header** (`FACEBOOK_PAGE_ACCESS_TOKEN`) | 4.800 lệnh × số người tương tác / 24h trượt; đọc header `X-App-Usage` | ✅ **CÓ** — chỉ đọc **Page của chính đội**, quyền `pages_read_engagement` + `pages_read_user_content`, Standard Access không cần App Review | ❌ Chưa — sẵn sàng kỹ thuật, chưa có token |
| 5 | **Shopee Open Platform API v2** | `https://partner.shopeemobile.com/api/v2` · `/livestream/get_latest_comment_list`, `/get_session_metric`, `/get_session_detail` | **HMAC-SHA256** ký query (`SHOPEE_PARTNER_KEY`), token hạn 4 giờ | Chỉ trả bình luận **10 giây gần nhất** ⇒ mã **cưỡng chế** `poll_s ≤ 8s`, vượt thì `raise` | ✅ **CÓ** — API chính thức cho đối tác | ❌ Chưa — đội **chưa có `SHOPEE_PARTNER_ID`**. Chỉ xác minh endpoint tồn tại bằng đối chứng mã lỗi (11/09) |
| 6 | ⚠️ **TikTok Webcast** (qua `TikTokLive`) | Qua proxy Euler Stream | Không (ẩn danh) | — | ❌ **KHÔNG** — giao thức dịch ngược | ❌ Thất bại 10/10 lần, 0 bình luận |
| 7 | **API LLM** | — | — | — | — | ❌ **KHÔNG CÓ trong mã** |

**Bí mật/khoá được quản lý thế nào:** tất cả qua biến môi trường, `.env` bị `.gitignore`.
Đội đã **quét toàn bộ 42 commit lịch sử git**: **không có khoá API, token hay khoá riêng tư nào bị
commit nhầm**. `.env` cục bộ hiện có **mọi trường credential nền tảng đều rỗng**.
`FACEBOOK_APP_SECRET` có ghi chú trong `.env.example` cấm đưa lên máy chạy ingest.

---

## V. THƯ VIỆN & MÃ NGUỒN MỞ

### V.1. Giấy phép của chính sản phẩm

**AGPL-3.0-only** (`LICENSE`, `pyproject.toml`). Chọn AGPL vì LiveLift là dịch vụ chạy qua mạng —
AGPL buộc mọi bản triển khai qua mạng phải công khai mã nguồn, bảo vệ tính mở của phương pháp.
Mọi phụ thuộc dưới đây đều **cho phép** (BSD/MIT/Apache/Unlicense/PSF) ⇒ **tương thích với AGPL-3.0**.

### V.2. Phụ thuộc Python trực tiếp

| Thư viện | Phiên bản đang dùng | Giấy phép | Dùng để làm gì trong LiveLift |
|---|---|---|---|
| `numpy` | 2.5.2 | BSD-3-Clause | Mảng số nền tảng cho toàn bộ tầng thống kê và mô phỏng |
| `scipy` | 1.18.1 | BSD-3-Clause | Phân vị chuẩn cho công thức MDE, kiểm định nhị thức chính xác ở cổng hiệu chuẩn A/A |
| `pandas` | 3.0.5 | BSD-3-Clause | Đọc/gộp CSV KuaiLive trong `analysis/calibration/kuailive_calibration.py` |
| `statsmodels` | 0.14.6 | BSD-3-Clause | Hồi quy OLS có hiệu ứng cố định theo phiên + sai số chuẩn gom cụm CR1 trong `analysis/robust.py` |
| `scikit-learn` | 1.9.0 | BSD-3-Clause | TF-IDF + LogisticRegression + `classification_report` cho bộ phân loại ý định (`nlp/train_intent.py`) |
| `joblib` | 1.5.3 | BSD-3-Clause | Lưu/nạp artifact `intent_clf.joblib` |
| `lightgbm` | 4.7.0 | MIT | Khai báo trong extra `[ml]` — ⚠️ **hiện chưa được import ở đâu**, dự phòng cho mô hình xếp hạng ứng viên |
| `pydantic` | 2.13.4 | MIT | Định nghĩa & kiểm tra schema toàn bộ hợp đồng API (`api/schemas.py`) |
| `pydantic-settings` | 2.15.0 | MIT | Đọc cấu hình/biến môi trường có kiểm kiểu (`config.py`) |
| `fastapi` | 0.141.1 | MIT | Khung API HTTP + WebSocket của toàn hệ thống |
| `starlette` | 1.6.0 | BSD-3-Clause | Tầng ASGI bên dưới FastAPI (phụ thuộc bắc cầu bắt buộc) |
| `uvicorn[standard]` | 0.52.4 | BSD-3-Clause | Máy chủ ASGI chạy API |
| `psycopg[binary,pool]` | 3.3.4 | LGPL-3.0 | Driver PostgreSQL/TimescaleDB + connection pool (`api/store.py`) |
| `redis` | 8.1.0 | MIT | Hàng đợi/bộ đệm sự kiện thời gian thực |
| `httpx` | 0.28.1 | BSD-3-Clause | Client HTTP bất đồng bộ cho **mọi** adapter nền tảng (YouTube/Facebook/Shopee) |
| ⚠️ `yt-dlp` | 2026.8.19 | **Unlicense** (phạm vi công cộng) | Tải chat replay VOD YouTube — **xem cảnh báo điều khoản §III.2 và §IV** |
| `pytest` | 9.1.1 | MIT | Chạy 890 hàm test / 58 file |
| `pytest-cov` | 7.1.0 | MIT | Đo độ phủ test trong CI |
| `ruff` | 0.16.4 | MIT | Lint + format (cổng CI, 0 lỗi mới được merge) |
| `mypy` | 2.3.1 | MIT | Kiểm kiểu tĩnh |
| `hatchling` | — | MIT | Build backend đóng gói `livelift` |
| `TikTokLive` | ≥6 (**không cài**) | MIT | Chỉ trong `collectors/tiktok_public/requirements.txt` — bộ thu TikTok đã thất bại |
| `underthesea` | **không cài** | GPL-3.0 | ⚠️ Khai báo thừa trong extra `[nlp]`, không được import — đề nghị gỡ |

**Phụ thuộc gián tiếp (bắc cầu):** tổng **51 gói** trong môi trường chạy. Toàn bộ là giấy phép cho
phép (MIT / BSD / Apache-2.0 / PSF / ISC). Sinh lại danh sách đầy đủ bằng:
`.venv/Scripts/python -m pip list --format=freeze`.

### V.3. Phụ thuộc JavaScript (giao diện web)

| Thư viện | Phiên bản | Giấy phép | Dùng để làm gì |
|---|---|---|---|
| `next` | ^14.2.5 | MIT | Khung ứng dụng web (bàn điều khiển, màn hình host, trang kết quả) |
| `react` / `react-dom` | ^18.3.1 | MIT | Thư viện giao diện |
| `recharts` | ^2.12.7 | MIT | Vẽ biểu đồ chuỗi thời gian trên bảng điều khiển & trang kết quả |
| `tailwindcss` | ^3.4.7 | MIT | Hệ thống CSS tiện ích |
| `typescript` | ^5.5.4 | Apache-2.0 | Kiểm kiểu tĩnh cho web |
| `postcss` / `autoprefixer` | ^8.4.39 / ^10.4.19 | MIT | Pipeline biên dịch CSS |
| `@types/*` | — | MIT | Khai báo kiểu |

Khóa phiên bản chính xác: `web/package-lock.json` (70 KB, **đã commit** ⇒ build tái lập được).
**Không có UI kit trả phí, không có template mua sẵn** — bộ 10 component trong `web/src` do đội tự
dựng theo chuẩn thiết kế công khai (Tremor/shadcn/Linear), **0 dependency mới**.

### V.4. Hạ tầng (Docker image)

| Image | Giấy phép | Dùng để làm gì |
|---|---|---|
| `timescale/timescaledb:latest-pg16` | Apache-2.0 / TSL | CSDL chuỗi thời gian cho sự kiện phiên live |
| `redis:7-alpine` | BSD-3-Clause | Bộ đệm / hàng đợi |
| `caddy:2-alpine` | Apache-2.0 | Reverse proxy + TLS tự động cho bản công khai |

---

## VI. MÃ NGUỒN THAM KHẢO / KẾ THỪA

**Kết quả rà soát:** đội đã quét toàn bộ `src/` tìm đoạn mã sao chép (comment ghi nguồn, link
StackOverflow/GitHub/Wikipedia, thuật toán chuẩn). **Không tìm thấy đoạn mã nào chép nguyên văn từ
kho mã của người khác.** Mọi tham chiếu bên ngoài đều là **trích dẫn tài liệu khoa học đặt cạnh
phần cài đặt do đội tự viết**. Đây là danh sách đầy đủ.

### VI.1. Công thức/thuật toán cài đặt lại từ bài báo (đội tự viết mã, trích nguồn tại chỗ)

| Vị trí | Nguồn trích dẫn | Kế thừa cái gì |
|---|---|---|
| `analysis/adjust.py:35,119,162` | Deng, Knoblich & Lu, *Applying the Delta Method in Metric Analytics*, **KDD 2018 / arXiv:1803.06336** | Công thức phương sai delta-method cho chỉ số tỷ lệ — **ghi rõ là phương trình (6) bản arXiv** |
| `analysis/adjust.py:38,377` | arXiv:2608.24038 | CUPED đa biến, chọn ridge-λ |
| `analysis/robust.py:23–27` | Lin, *Agnostic notes on regression adjustments*, **Ann. Appl. Stat. 7(1) 2013**; Cameron–Gelbach–Miller, **REStat 90(3) 2008**; arXiv:2510.01127 | Hiệp biến tương tác kiểu Lin; **hiệu chỉnh CR1**; cổng ICS |
| `analysis/estimators.py:10` | **Bojinov & Shephard, JASA 2019** | Phân bố tham chiếu của kiểm định ngẫu nhiên hóa khớp với thiết kế |
| `analysis/power.py:4` | **J-PAL** | Công thức MDE gốc `(z_{1-α/2}+z_power)·CV·√(2/n)` |
| `analysis/power.py:16` | Hiệu ứng thiết kế **Moulton** | ⚠️ **Cố ý KHÔNG áp dụng**, tắt mặc định, có ghi lý do dẫn xuất |
| `core/assigner/outer.py:7` | Bojinov, Simchi-Levi & Zhao, *Design and Analysis of Switchback Experiments*, **Management Science 69(7) 2023 / arXiv:2009.00148** | **Chính thiết kế switchback** — nền tảng phương pháp của sản phẩm |
| `core/assigner/outer.py:10` | Hu & Wager, **JBES / arXiv:2209.00197** | Cửa sổ burn-in ở khâu phân tích |
| `core/assigner/outer.py:34` | SRSB, arXiv:2604.02489, Algorithm 3 | ⚠️ **Cân nhắc rồi TỪ CHỐI** (đòi đơn vị song song) — ghi lại quyết định |
| `core/quality.py:93,541`, `core/click_validity.py:21` | Bakshy–Eckles–Bernstein **WWW 2014**; Fabijan et al. **KDD 2019** | Kiểm tra chất lượng gán, kiểm định SRM, ngưỡng τ lọc bot |
| `core/features.py:162` | Nguyễn et al., **IMCOM 2026** | Đặc trưng "nhịp like trước khối" liên quan hành vi mua |
| `sim/report.py:10` | Talts et al. (arXiv:1804.06788); Modrák et al. (arXiv:2211.02383) | SBC — ghi rõ **"adapted from"**: chuyển histogram hạng Bayes sang đại lượng tần suất |
| `sim/report.py:258` | Aldor-Noiman et al. (2013) | Dải tin cậy đồng thời — **cân nhắc, ghi caveat, không chép thẳng** |
| `core/moments.py:3` | **Feigua** (sản phẩm thương mại đối thủ) | ⚠️ Kế thừa **ý tưởng UX/thuật toán** (đánh dấu "khoảnh khắc" trên dòng thời gian phát lại bằng phát hiện đỉnh so với trung vị) — không có mã nguồn của Feigua, đội tự cài đặt |

### VI.2. Lược đồ giao thức đọc từ SDK của bên thứ ba

| Vị trí | Nguồn | Kế thừa cái gì |
|---|---|---|
| `ingest/shopee.py:66,167` | **SDK TypeScript chính thức của Shopee** (`src/schemas/region.ts`, `src/fetch.ts`), đọc 11/09/2026 | Bảng host theo khu vực + **lược đồ ký HMAC-SHA256**. Đây là **đặc tả giao thức**, đội **viết lại bằng Python**, không chép mã TypeScript |
| `ingest/youtube_ytdlp.py:19` | `yt_dlp/downloader/youtube_live_chat.py`, hàm `parse_actions_live` | **Đọc để chẩn đoán** nguyên nhân độ trễ giao tin 24s — không chép mã |

### VI.3. Dữ liệu tự biên soạn có kế thừa nội dung thật

`src/livelift/ingest/pii/admin_units.py` — danh sách đơn vị hành chính Việt Nam (**cả 63 tỉnh trước
2025 và tên sau sáp nhập 2025**), do đội tự gõ, **không dẫn nguồn cụ thể**.
⚠️ Đề nghị bổ sung dẫn nguồn (Nghị quyết sáp nhập / Tổng cục Thống kê) để hoàn chỉnh.

`src/livelift/nlp/labels.py:186` — ví dụ mồi cho prompt gán nhãn là **trích nguyên văn bình luận
thật** (đã lọc PII) từ phiên live-fire. Đã ghi chú rõ "trích NGUYÊN VĂN" tại chỗ.

---

## VII. PHÂN ĐỊNH: TỰ XÂY DỰNG / AI HỖ TRỢ / KẾ THỪA NGUỒN MỞ

> Đây là mục Điều 5 §5 đòi hỏi trực tiếp. Đội kê khai theo **ước lượng trung thực, có bằng chứng
> kiểm chứng được**, không làm đẹp con số.

### VII.1. Bức tranh tổng thể — nói thẳng

**Phần lớn mã nguồn của LiveLift do Claude Code soạn nháp.** Đội không né câu này. Ước lượng
trung thực: **khoảng 90–95% số dòng mã được AI gõ ra đầu tiên.** Nhưng "ai gõ" không phải là
"ai quyết định" — và thể lệ hỏi về **năng lực làm chủ**, không hỏi về số dòng.

**Bằng chứng định lượng (sinh lại được):**

| Chỉ số | Giá trị |
|---|---|
| Commit | 42, trải **14 ngày làm việc riêng biệt** (24/08 → 14/09/2026) |
| Dòng mã | +79.999 / −5.408, chạm 736 lượt file |
| File theo dõi trong git | 322 |
| Hàm test | **890** (58 file) — 993 test nhanh + 16 cổng Monte-Carlo |
| Câu lệnh của đội gửi cho AI | **1.297** |
| Sự cố có truy nguyên nhân gốc | **41** (`docs/incident-log.md`) |

### VII.2. Bảng phân định theo từng thành phần

| Thành phần | Tự xây dựng | AI hỗ trợ | Kế thừa nguồn mở |
|---|---|---|---|
| **Bài toán, giả thuyết, thiết kế thí nghiệm** (switchback 2 tầng, tiền đăng ký, biên độ đo được) | 🟩 **ĐỘI QUYẾT ĐỊNH HOÀN TOÀN** — AI không chọn phương pháp; đội đọc bài báo, quyết định áp dụng/từ chối và ghi lý do | AI tóm tắt tài liệu, giải thích công thức | Ý tưởng thiết kế từ Bojinov et al. 2023 (bài báo, không phải mã) |
| **Ước lượng viên & suy diễn thống kê** (`analysis/`) | 🟩 Đội chọn ước lượng viên, chốt ngưỡng nghiệm thu, **từ chối** hiệu chỉnh Moulton, ra lệnh cấm ánh xạ KuaiLive lên phễu | 🟨 AI viết nháp phần lớn thân hàm | Công thức từ bài báo (§VI.1); `numpy`/`scipy`/`statsmodels` |
| **Bộ gán ngẫu nhiên** (`core/assigner/`) | 🟩 Đội chốt bất biến: ghi propensity chính xác, lưu lịch **trước** phát sóng, seed vào DB | 🟨 AI viết nháp | Thiết kế từ bài báo |
| **API + CSDL + hạ tầng** (`api/`, `dbops/`, `docker/`) | 🟧 Đội chốt hợp đồng API và mô hình dữ liệu | 🟥 **AI viết gần như trọn vẹn** | FastAPI, psycopg, TimescaleDB, Redis, Caddy |
| **Giao diện web** (`web/`) | 🟧 Đội chốt ngôn ngữ sản phẩm ("Phòng điều khiển phát sóng"), luồng wizard, quy tắc **host không được thấy nhánh** | 🟥 **AI viết gần như trọn vẹn** | Next.js, React, Recharts, Tailwind |
| **Bộ lọc PII tiếng Việt** (`ingest/pii/`) | 🟩 Đội định nghĩa "PII trong chat bán hàng VN là gì", chọn thiên lệch **recall hơn precision**, tự gõ danh sách đơn vị hành chính 2 thế hệ | 🟨 AI viết nháp regex | Chỉ `re` chuẩn |
| **Adapter nền tảng** (`ingest/`) | 🟧 Đội tự đo hạn ngạch thật, tự đọc ToS, tự quyết định giữ/bỏ từng đường | 🟨 AI viết nháp + chẩn đoán | Lược đồ ký của Shopee SDK; `yt-dlp`; `httpx` |
| **Bộ phân loại ý định** (`nlp/`) | 🟩 **320 câu dữ liệu do 3 thành viên tự viết**; đội tự gán nhãn mù 200 bình luận thật và **tự công bố F1 0,271** | 🟨 AI viết nháp pipeline | `scikit-learn` |
| **Bộ test (890 hàm)** | 🟩 Đội chốt tiêu chí nghiệm thu & ngưỡng cổng | 🟥 AI viết phần lớn thân test | `pytest` |
| **Kiểm toán đối kháng & sổ sự cố (41 sự cố)** | 🟩🟩 **HOÀN TOÀN CỦA ĐỘI** — đội đóng vai người dùng, đóng vai giám khảo, tìm ra lỗi mà AI không tự thấy | AI sửa sau khi đội chỉ ra | — |
| **Vận hành dữ liệu thật** (chọn 16 buổi, gán nhãn tay, live-fire) | 🟩🟩 **HOÀN TOÀN CỦA ĐỘI** — thao tác người, không tự động hóa được | — | — |
| **Tài liệu (README, HARNESS, PREREGISTRATION, FACT-SHEET)** | 🟩 Đội chốt nội dung, quy tắc, con số | 🟨 AI viết nháp văn bản | — |

🟩 đội chủ đạo · 🟧 chia đôi · 🟨 AI viết nháp, đội sửa & duyệt · 🟥 AI viết gần trọn, đội nghiệm thu

### VII.3. Bằng chứng đội THỰC SỰ làm chủ, không chỉ bấm "chấp nhận"

Bằng chứng mạnh nhất **không phải** là mã chạy được — mà là **những lần đội bắt lỗi của chính AI**.
Lịch sử commit ghi lại nguyên văn (đây là **tài sản** của đội, sinh lại được bằng `git log`):

| Commit | Điều nó chứng minh |
|---|---|
| `e47169e` — *"FATAL x2 tu kiem toan doi khang: sua loi bao 'co y nghia' tren nhieu thuan"* | Đội phát hiện lỗi **báo có ý nghĩa thống kê sai** — lỗi nghiêm trọng nhất một nền tảng thí nghiệm có thể mắc. AI đã viết ra nó; **đội bắt được** |
| `0969b0f` — *"Sua cong thuc MDE: bo 2 hieu chinh khong thuoc thiet ke"* | Đội đọc lại công thức, phát hiện AI áp 2 hiệu chỉnh không thuộc thiết kế, và **gỡ bỏ** |
| `665e444` — *"Cong hieu chuan A/A: thay nguong tuy tien bang kiem dinh nhi thuc chinh xac"* | Đội thay ngưỡng tùy tiện bằng kiểm định thống kê đúng |
| `15745db` — *"Ra soat phuong phap: sua bug phan bo tham chieu"* | Rà soát phương pháp luận chủ động |
| `e2be454` — *"Sua 8 loi tim duoc khi dong vai nguoi dung"* | Đội tự đóng vai người dùng cuối |
| `7c30ffe` — *"Sua 3 loi lo ra khi dung kich ban demo cho hoi dong"* | Diễn tập demo và sửa lỗi lộ ra |
| `fa4d9e4` — *"Kiem toan doi khang dot 2 + 6 goi fix P0"* | Kiểm toán đối kháng có tổ chức, phân loại mức độ |
| `069c49c` — *"Tra loi cau hoi du lieu bang HANH DONG: train that + calibrate that"* | Không nhận vơ: có nghi vấn thì đi đo thật |

**Ba minh chứng khác về năng lực làm chủ:**

1. **Đội biết mô hình của mình DỞ ở đâu và công bố nó.** F1 0,271 trên chat thật là con số đội tự
   đo, tự công bố, tự đặt quy tắc "không bao giờ quote riêng số đẹp 0,870". Một đội chỉ biết bấm
   "chấp nhận" sẽ không bao giờ có con số này.
2. **Đội mã hóa các lệnh CẤM vào chính mã nguồn.** Ví dụ cấm ánh xạ KuaiLive lên phễu mua hàng
   (`analysis/power.py:412`), cấm thẻ mô hình hiển thị khoảng tin cậy (có test giao diện chặn),
   cấm gắn ngôn ngữ thí nghiệm vào phân tích quan sát. Đây là **quyết định phương pháp luận**, chỉ
   có người hiểu bài toán mới đặt ra được.
3. **Sổ sự cố 41 mục** (`docs/incident-log.md`) ghi từng lỗi theo cấu trúc: triệu chứng → **nguyên
   nhân gốc** → cách sửa → **test chặn tái diễn**. Ví dụ sự cố 10/09: hệ thống báo "đủ tín hiệu
   người xem" trong khi thực tế 1.430 dòng đo đều bằng 0 — đội gọi thẳng đây là lỗi **"nhận vơ
   năng lực"** và sửa bằng cách buộc mọi caller phải khai đã đo gì.

### VII.4. ⚠️ Điểm yếu đội tự khai về quyền tác giả

**Cả 42 commit đều mang một danh tính CON NGƯỜI duy nhất:** `LiveLift Team <ngobinhminh2322006@gmail.com>`
(phần đồng tác giả AI thì có đủ 42/42 — xem §I.1).
Lý do: đội làm chung trên **một máy trạm**. Đây **không phải giả mạo lịch sử commit** (thể lệ cấm
điều đó) — lịch sử là thật, tăng dần, trải 14 ngày, có cả commit sửa lỗi của chính mình. Nhưng nó
**không thể hiện được đóng góp riêng của từng thành viên**, và giám khảo có quyền hỏi.
**Cách xử lý đề xuất:** bổ sung một mục "phân công công việc theo thành viên" vào README hoặc
thuyết minh, đối chiếu với các mốc trong `docs/incident-log.md`. **Không** viết lại lịch sử git.

---

## VIII. QUY TRÌNH KIỂM CHỨNG ĐẦU RA AI

> Điều 5 §6 yêu cầu đội giải thích được **quy trình kiểm chứng đầu ra**. Đây là quy trình đội
> **thực sự áp dụng**, được mã hóa thành cổng tự động, không phải mô tả lý thuyết.

### VIII.1. Nguyên tắc nền: kiến trúc để kiểm chứng được

`HARNESS.md` quy định: **mọi logic quyết định là hàm thuần** — nhận dữ liệu, trả dữ liệu, không đọc
CSDL, không đọc đồng hồ, không tự sinh ngẫu nhiên ngoài RNG được truyền vào. I/O nằm ở lớp mỏng bên
ngoài. Hệ quả: **100% logic cốt lõi test được mà không cần hạ tầng** — điều kiện tiên quyết để kiểm
chứng bất kỳ đầu ra nào của AI.

### VIII.2. Tám cổng chất lượng tự động — CI đỏ là không merge

| Cổng | Ngưỡng | Kiểm chứng điều gì |
|---|---|---|
| `pytest -m "not slow"` | 100% pass (993 test) | Hồi quy cơ bản |
| `pytest -m slow` (nightly) | 100% pass (16 cổng Monte-Carlo) | **Thẩm định thống kê trên mô phỏng có tác động biết trước** |
| **Thẩm định ước lượng viên** | bias < 10%; độ phủ KTC 95% ∈ [90%, 98%] | **Cổng quan trọng nhất** — con số sai còn tệ hơn không có số |
| **Cân bằng gán** | 1000 lịch thử, tỷ lệ BẬT ∈ [0,45; 0,55] | Bộ gán ngẫu nhiên không lệch |
| **PII recall** | ≥ 95% từng loại | Tuân thủ Luật 91/2025/QH15 · ⚠️ **thiếu loại `social` — xem §III.2** |
| **Cách ly VLiveBench** | 0 import từ `src/` sang `collectors/` | Bộ thu TikTok hỏng không kéo sập lõi |
| **Quy tắc nguồn con số** | Thẻ từ mô hình **không bao giờ** hiện "khoảng tin cậy" | Chống overclaim ở cấp giao diện |
| `ruff check` + `ruff format --check` + migration up/down/up | 0 lỗi | Nhất quán; CSDL đảo ngược được |

Kết quả A/A thực tế: **bác bỏ 4,5% ở mức danh nghĩa 5%** (p nhị thức = 0,872), **độ phủ KTC 95,5%**.
Nghĩa là ước lượng viên **tự chứng minh** mình không bịa ý nghĩa thống kê.

### VIII.3. Quy trình xử lý lỗi bắt buộc (`HARNESS.md` §3)

1. **Tái hiện tối thiểu** — thu về input nhỏ nhất còn gây lỗi.
2. **Truy nguyên nhân gốc, không vá triệu chứng** — dùng "5 whys" đến khi chạm quyết định thiết kế
   hoặc giả định sai. **Cấm** vá kiểu "thêm `if` chặn giá trị lạ" khi chưa biết giá trị lạ từ đâu.
3. **Test trước, fix sau** — viết test tái hiện (đỏ) → sửa (xanh). Test ở lại vĩnh viễn.
4. **Ghi sổ** — một dòng vào `docs/incident-log.md`.
5. **Hỏi lớp phòng thủ** — lỗi này lọt qua cổng nào? Có cần cổng mới không?

**Riêng dữ liệu thí nghiệm:** khối/phiên hỏng bị đánh dấu loại (`excluded_reason`), **KHÔNG sửa số
liệu**. Không bao giờ "sửa tay" bản ghi thí nghiệm.

### VIII.4. Vòng nghiên cứu → mã nguồn (chống AI bịa công thức)

`HARNESS.md` §4: **phương pháp không được vào code từ trí nhớ.** Bắt buộc: đọc tài liệu gốc → ghi
5–10 dòng vào `docs/research-log.md` (nguồn / điều dùng được / **điều KHÔNG áp dụng được cho bối
cảnh mình** / quyết định) → mọi công thức trong `analysis/` phải có docstring dẫn nguồn **tác giả,
năm, công thức số mấy**. Quy tắc này chính là lý do §VI.1 lập được đầy đủ.

### VIII.5. Kiểm toán đối kháng do người thực hiện

Cổng tự động không bắt được lỗi "đúng cú pháp nhưng sai bản chất". Đội bổ sung 3 vòng người:

| Vòng | Cách làm | Kết quả |
|---|---|---|
| **Đóng vai người dùng** | Chạy hết hành trình như người lạ, không dùng lệnh CLI | Commit `e2be454` — tìm 8 lỗi |
| **Đóng vai giám khảo** | Tự phản biện, soi số nào không đứng vững | `docs/competition/phan-bien-du-kien.md`; FACT-SHEET ra đời sau khi kiểm toán 06/09 phát hiện tài liệu lệch số nhau |
| **Kiểm toán đối kháng có tổ chức** | Rà soát toàn hệ, phân loại theo mức nghiêm trọng | `audit_findings.txt`: **16 phát hiện** — 2 FATAL, 7 SERIOUS, 6 MODERATE, 1 MINOR — mỗi phát hiện có `FILE:` trỏ đúng dòng mã, `WHY:` cơ chế sinh lỗi, `FIX:` cách sửa. Commit `fa4d9e4` (6 gói fix P0), `e47169e` (2 lỗi FATAL) |
| **Sáu giám khảo độc lập** (vòng cuối, 14/09) | Đội tự dựng 6 vai chấm độc lập — phương pháp, kinh doanh, dữ liệu, kỹ thuật, hình thức, **phản biện ác ý** — rồi tự phản biện lại từng phát hiện | Commit `dd66b38` (HEAD): **81 điểm yếu · 43 phán quyết ĐÚNG · 38 MỘT-PHẦN · 0 bị bác hoàn toàn** |

**Một phát hiện tự kiểm toán đáng chú ý** (`audit_findings.txt` #9): *"Không có cổng nào chạy với
carryover > 0, nên các con số bias/coverage đã công bố chỉ đúng dưới giả định KHÔNG có can nhiễu —
đúng cái giả định mà thiết kế switchback sinh ra để nới lỏng."* Đội tự chỉ ra giới hạn ở **chính
trụ cột phương pháp của mình** — và sau đó đã đo bổ sung độ phủ dưới hiệu ứng lưu
(bán rã 0s → 100%; 120s → 84%; 180s → 60%), công bố cả ba con số.

### VIII.6. Chống overclaim ở cấp kiến trúc

Đây là điểm đội tự hào nhất về kiểm soát đầu ra: **một số không hợp lệ không thể hiển thị được**,
chứ không phải "cố gắng không hiển thị":

- Thẻ dự báo từ mô hình **không thể** mang khoảng tin cậy — validator từ chối.
- Màn hình host **không thể** rò nhánh thí nghiệm — dùng model riêng chỉ 4 trường.
- Phân tích từ VOD **không thể** mang ngôn ngữ thí nghiệm — cổng chặn ở `reports.py`.
- Thiếu tín hiệu đầu vào ⇒ **tuyên bố thiếu**, không âm thầm ra số yếu (ma trận 5 tín hiệu → 5 năng lực).
- **Khóa kết quả theo tiền đăng ký** (`RESULTS_FREEZE_UNTIL`), fail-closed.

### VIII.7. Làm sạch đầu ra AI trước khi công bố

Nhật ký phiên Claude Code **không được công bố nguyên trạng**. Đội viết
`scripts/xuat_prompt_log.py` để xuất ra Markdown đọc được **sau khi lọc**: khoá API, token, giá trị
biến môi trường nhạy cảm, email, số điện thoại, số tài khoản, và **handle mạng xã hội có dấu tiếng
Việt** (bộ lọc trong script này **đã sửa lỗi ASCII-only** nêu ở §III.2).
Chạy thử ngày 14/09/2026 trên 3 phiên chính: **185 lần thay thế**, trong đó 92 handle mạng xã hội,
40 email, 15 số điện thoại/MSSV, 17 giá trị biến môi trường.
Kết quả kèm `BAO-CAO-LAM-SACH.md` liệt kê đã thay gì, và **ghi rõ giới hạn**: regex không phải NER,
tên người viết thường không tiền tố vẫn có thể lọt ⇒ **bắt buộc người đọc lại thủ công** trước khi
tải lên Drive.

---

## IX. CAM KẾT CỦA ĐỘI THI

Chúng tôi, đội thi LiveLift, cam kết:

1. **Bản kê khai này trung thực và đầy đủ** theo hiểu biết của chúng tôi tại ngày 14/09/2026.
   Chúng tôi đã chủ động kê khai cả những điểm bất lợi cho mình — cụ thể là **phương thức thu thập
   dữ liệu trái điều khoản dịch vụ YouTube** (§III.2, §IV), **lỗi rò rỉ 53 handle mạng xã hội trong
   dữ liệu đã lưu** (§III.2), **giấy phép KuaiLive còn mâu thuẫn chưa xác minh** (§III.2), **hiệu
   năng mô hình trên chat thật chỉ đạt F1 0,271** (§II.1), và **toàn bộ commit mang một danh tính**
   (§VII.4). Chúng tôi hiểu rằng che giấu nguồn mã, dataset hoặc API là hành vi bị nghiêm cấm theo
   Điều 5 §7 thể lệ.

2. **Chúng tôi hiểu, kiểm chứng được, chỉnh sửa được và chịu trách nhiệm** với toàn bộ sản phẩm —
   kể cả phần do công cụ AI soạn nháp. Bằng chứng là quy trình ở mục VIII, 890 hàm test, 41 sự cố
   có truy nguyên nhân gốc, và những lần chúng tôi phát hiện & sửa lỗi nghiêm trọng do chính công
   cụ AI tạo ra (mục VII.3).

3. **Không có bất kỳ hành vi nào** trong danh sách cấm tại Điều 5: không thi hộ, không thuê làm sản
   phẩm, không để người ngoài làm thay, không sao chép sản phẩm, **không giả mạo Prompt Log, lịch
   sử commit, dữ liệu thử nghiệm hay video demo**.

4. **Về dữ liệu cá nhân:** chúng tôi không tuyên bố đã có sự đồng ý của người bình luận. Cơ sở
   chúng tôi viện dẫn là **khử nhận dạng ngay tại điểm thu thập cộng lợi ích chính đáng cho nghiên
   cứu học thuật phi thương mại**, theo Nghị định 13/2023/NĐ-CP và Luật 91/2025/QH15. Chúng tôi
   không tái phân phối dữ liệu thô, không lưu định danh người bình luận, không xây chuỗi hành vi
   theo từng cá nhân. Lỗi rò rỉ nêu tại §III.2 đang được xử lý theo kế hoạch P0 và chúng tôi sẽ báo
   cáo kết quả khắc phục.

5. **Chúng tôi sẵn sàng trình bày, phản biện và chứng minh trực tiếp** mọi nội dung trong bản kê
   khai này trước Ban Giám khảo, bao gồm chạy lại mọi con số bằng lệnh trên kho mã nguồn.

**Đại diện đội thi**

TP. Hồ Chí Minh, ngày ..... tháng ..... năm 2026

*(Ký, ghi rõ họ tên)*

**Ngô Bình Minh** — Đội trưởng

---

### Phụ lục: lệnh sinh lại các con số trong bản kê khai

```bash
# Phụ thuộc Python + phiên bản chính xác
.venv/Scripts/python -m pip list --format=freeze

# Phụ thuộc JS
cat web/package.json && cat web/package-lock.json

# Thống kê lịch sử commit
git log --format="%an <%ae>" | sort | uniq -c
git log --shortstat --format="" | awk '{f+=$1;i+=$4;d+=$6} END {print f,i,d}'

# Số test
pytest -m "not slow" -q && pytest -m slow -q

# Huấn luyện lại & đo lại bộ phân loại ý định
python -m livelift.nlp.train_intent

# Hiệu chỉnh lại theo KuaiLive
python analysis/calibration/kuailive_calibration.py

# Xuất Prompt Log đã làm sạch (xem trước, không ghi file)
python scripts/xuat_prompt_log.py --kiem-tra
```
