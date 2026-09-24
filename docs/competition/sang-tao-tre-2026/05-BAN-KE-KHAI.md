<!-- QUOC-HIEU -->

# BẢN KÊ KHAI CÔNG CỤ AI, MÔ HÌNH, DỮ LIỆU, API, THƯ VIỆN VÀ MÃ NGUỒN MỞ

| Hạng mục | Nội dung |
|---|---|
| Cuộc thi | Cuộc thi Sáng tạo trẻ Quốc gia trong lĩnh vực Trí tuệ nhân tạo năm 2026 — Bảng C, đường trường cử |
| Sản phẩm | LiveLift — nền tảng thí nghiệm vận hành cho livestream bán hàng |
| Đội thi | Ngô Bình Minh (đội trưởng) · Lê Xuân Khánh · Ngô Lâm Tiến — Khoa Công nghệ thông tin, Trường Đại học Tôn Đức Thắng |
| Kho mã nguồn (công khai) | https://github.com/bminhnemhoi/AISC2026_LIVEFIT |
| Trạng thái mã nguồn khi kê khai | Nhánh `main` tại commit `390027b` (56 commit, 24/08 → 18/09/2026). Nhánh `tien/aisc-round2` (PR số 1, 2 commit ngày 21/09/2026) đang chờ duyệt, chưa hợp nhất |
| Ngày lập | 25/09/2026 |
| Người soạn | Bản này do tác tử AI (Claude, qua Claude Code) soạn nháp theo yêu cầu của đội trưởng, từ số đếm máy trên kho mã và nhật ký phiên. Ba thành viên đọc, sửa và ký ở mục X |

Các con số đếm bằng máy có lệnh tái lập ở Phụ lục; con số lấy từ tài liệu khác của dự án ghi nguồn tại chỗ. Mục nào đội không kiểm được thì ghi rõ là chưa kiểm, không suy đoán.

## Căn cứ

- **Điều 5 Thể lệ Cuộc thi** (ban hành kèm Kế hoạch số 01-KH/TWĐTN-KHCN ngày 03/7/2026): được dùng LLM, thư viện mở, mô hình huấn luyện sẵn, dữ liệu công khai và API nếu kê khai trung thực, nêu rõ phần đội tự xây dựng, phần do AI tạo ra và phần kế thừa nguồn mở; nghiêm cấm che giấu nguồn mã, dữ liệu, API và giả mạo Prompt Log, lịch sử commit, dữ liệu thử nghiệm, video demo.
- **Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15** (hiệu lực 01/01/2026) và **Nghị định 356/2025/NĐ-CP** ngày 31/12/2025 quy định chi tiết Luật (thay thế Nghị định 13/2023/NĐ-CP).
- **Luật Trí tuệ nhân tạo số 134/2025/QH15** (thông qua 10/12/2025, hiệu lực 01/3/2026) và Nghị định 142/2026/NĐ-CP hướng dẫn thi hành (theo tra cứu ngày 25/09/2026; đội chưa có ý kiến của người có chuyên môn pháp lý).

## Đính chính so với các bản kê khai trước

Bản lập ngày 14/09/2026 có những khẳng định mà chính đội đã phát hiện là sai (công bố đính chính ở commit `af0f00e` ngày 15/09/2026) hoặc bị kiểm toán ngày 25/09/2026 chỉ ra. Bản này thay thế hoàn toàn bản cũ:

| Bản cũ ghi | Sự thật |
|---|---|
| 320 câu mẫu ý định "do 3 thành viên tự viết, không sinh bằng LLM" | Do Claude soạn ngày 01/09/2026 |
| 393 bình luận tập kiểm tra "do người gán tay, gán mù" | Nhãn do tác tử AI (Claude) gán ngày 09/09/2026; chưa có nhãn người |
| macro-F1 0,271 trên 200 bình luận thật | Không tái lập được (tệp nhãn không được lưu) — rút lại. Số chính thức: 0,211 → 0,542, đo lại 25/09 (mục II) |
| A/A bác bỏ 4,5%, độ phủ 95,5% | Không tái lập được. Đo lại 14/09 và 25/09: bác bỏ 3,50% (7/200), độ phủ 96,50% |
| "1.297 câu lệnh của đội" | Bộ xuất cũ tính cả kết quả công cụ là câu lệnh người. Đếm lại: 78 câu lệnh người gõ (mục I.3) |
| Kiểm toán đối kháng và gán nhãn "hoàn toàn của đội" | Các đợt kiểm toán 14, 15, 17 và 25/09 do tác tử AI chạy theo yêu cầu của đội; nhãn do AI gán |
| Căn cứ thu thập dữ liệu: Nghị định 13/2023/NĐ-CP và "lợi ích chính đáng cho nghiên cứu" | Nghị định 13/2023 đã được thay thế trước khi thu dữ liệu; đội không viện dẫn căn cứ xử lý không cần đồng ý (mục IX) |
| Chỉ dùng Claude Code | Thành viên Tiến còn dùng Google Antigravity và OpenAI Codex ngày 21/09/2026 (mục I.1) |

## I. Công cụ AI dùng trong quá trình phát triển

### I.1. Danh mục công cụ

| Công cụ | Nhà cung cấp | Ai dùng, khi nào | Dùng để làm gì | Bằng chứng |
|---|---|---|---|---|
| **Claude Code** (tiện ích VS Code, phiên bản 2.1.239 → 2.1.281) | Anthropic | Máy trạm của đội trưởng, dùng chung; 5 phiên từ 24/08 đến 25/09/2026 | Viết mã, kiểm thử, tài liệu, hồ sơ; khảo cứu tài liệu (765 lần tìm web, 988 lần đọc trang web); gán nhãn dữ liệu; soạn dữ liệu tổng hợp; chạy các đợt kiểm toán nhiều tác tử; soạn nháp bản kê khai này | Prompt Log (thư mục 01 trên Drive); dòng đồng tác giả trong 56/56 commit trên `main` |
| **Google Antigravity** | Google | Ngô Lâm Tiến, 21/09/2026 | Rà soát mức sẵn sàng cho AISC vòng 2 và rà soát sau khi triển khai | `docs/competition/aisc-round2/ANTIGRAVITY-AUDIT.md`, `POST-IMPLEMENTATION-REVIEW.md` trên nhánh `tien/aisc-round2` (tài liệu tự ghi "thực hiện bởi AI Agent Antigravity") |
| **OpenAI Codex** | OpenAI | Ngô Lâm Tiến, 21/09/2026 | Lập kế hoạch và viết mã: `scripts/round2_demo_check.py` và test, thay đổi trang `/ket-qua`, câu chữ đồng hồ khối — commit `8949963` | `CODEX-IMPLEMENTATION-PLAN.md`, `POST-IMPLEMENTATION-REVIEW.md` trên nhánh `tien/aisc-round2` |
| GitHub Copilot (rà soát PR) | GitHub | Được gọi trên PR số 1 lúc 22:58 ngày 21/09/2026 (giờ Việt Nam; trang PR ghi 15:58 UTC) | Không chạy: GitHub ghi "Copilot stopped work … due to an error — the job was not started because the account is locked due to a billing issue". Không tạo ra nội dung nào | Trang PR số 1 trên GitHub |
| Tabnine (tiện ích gợi ý mã trong VS Code) | Tabnine | Cài trên máy trạm của đội trưởng từ 08/03/2026 | Không tìm thấy bằng chứng dùng cho LiveLift; mọi thay đổi mã trên `main` đi qua Claude Code theo dòng đồng tác giả. Kê khai để minh bạch | Thư mục tiện ích VS Code |

Ghi chú:

- Máy trạm của đội trưởng cũng có cài Google Antigravity. Tìm chuỗi "livelift" và "AISC2026" trong dữ liệu Antigravity dạng văn bản trên máy này cho 0 kết quả; dữ liệu hội thoại của Antigravity lưu dạng nhị phân nên cách tìm này không loại trừ hoàn toàn.
- Hai commit của Tiến (`08be6ae`, `8949963`) không có dòng khai báo AI, dù tài liệu trong chính các commit ghi là do Antigravity và Codex tạo. Đội bổ sung khai báo tại đây, không viết lại lịch sử commit.
- Nhật ký hội thoại Antigravity và Codex nằm trên máy của Tiến; Tiến tự xuất và bổ sung vào Prompt Log (thư mục `01-Prompt-Log/ngoai-claude-code/`). Nếu không xuất được, Tiến ghi rõ lý do tại đó.
- Lê Xuân Khánh chưa có commit nào trong kho. Công cụ AI Khánh dùng cho LiveLift (nếu có) được khai ở mục X.
- Hai tệp ý tưởng và kế hoạch ban đầu đội đưa vào phiên Claude Code đầu tiên ngày 24/08/2026 (`LiveLift-Mo-Ta-Du-An-Ban-Trien-Khai (1).md`, `LiveLift-Ke-Hoach-Trien-Khai.md`) có trên máy trước phiên đó: hệ thống tệp ghi thời điểm tạo 17:07 và 17:08 ngày 24/08/2026, phiên Claude Code đầu tiên bắt đầu lúc 20:42 cùng ngày (giờ Việt Nam). Cách hai tệp này được soạn được khai ở mục X.

### I.2. Mô hình AI nền của Claude Code

| Mô hình (tên ghi trong nhật ký) | Số bản ghi trả lời trong nhật ký | Số commit mang dòng đồng tác giả |
|---|---:|---:|
| Claude Opus 5 (`claude-opus-5`) | 30.050 | 26 (Opus 5, 1M context) + 1 (Opus 5) |
| Claude Fable 5 (`claude-fable-5`) | 6.296 | 29 |
| Claude Opus 5.5 (`claude-opus-5-5`) | 5.292 | 0 (dùng từ 25/09, chưa có commit) |
| Claude Fable 5.1 (`claude-fable-5-1`) | 372 | 0 |

Số bản ghi trả lời đếm trên mọi nhật ký (phiên chính và tác tử con), không tính tin nhắn lỗi tổng hợp. Claude Code ghi mỗi khối văn bản, khối suy luận hay lời gọi công cụ thành một bản ghi riêng, nên đây không phải số lần gọi mô hình (một lần gọi thường sinh nhiều bản ghi). Truy cập qua thuê bao Claude Code của đội trưởng.

### I.3. Prompt Log — số đếm lại ngày 25/09/2026

| Phiên | Thời gian (giờ Việt Nam) | Câu lệnh người gõ | Lệnh `/model` | Lời gọi công cụ của Claude | Nhật ký tác tử con |
|---|---|---:|---:|---:|---:|
| `feb901dc` | 24/08 → 03/09/2026 | 21 | 3 | 527 | 99 |
| `3c773cb8` | 06/09 → 14/09/2026 | 41 | 5 | 578 | 179 |
| `3b0c8ccf` | 14/09 → 15/09/2026 | 4 | 0 | 308 | 74 |
| `9b100e02` | 17/09 → 19/09/2026 | 11 | 1 | 306 | 190 |
| `22b800c6` | 25/09/2026 (đang chạy khi đếm) | 1 | 0 | 59 | 25 |
| **Tổng** | | **78** | **9** | **1.778** | **567** |

- "Câu lệnh người gõ" là bản ghi Claude Code đánh dấu do người nhập (`origin.kind = human`), kiểm chéo bằng mã câu lệnh (`promptId`) và bản ghi `last-prompt` trong cùng nhật ký. Nhật ký không ghi thành viên nào ngồi gõ.
- Tính cả tác tử con, Claude đã gọi công cụ **24.957** lần, trong đó 3.376 lần ghi hoặc sửa tệp (Write, Edit). 20 kịch bản điều phối nhiều tác tử cũng do Claude viết.
- System prompt: Claude Code chỉ ghi ảnh chụp system prompt vào nhật ký từ bản 2.1.270 — có ở 3/5 phiên (`3b0c8ccf`, `9b100e02`, `22b800c6`) và được xuất nguyên văn. Hai phiên đầu không có; đội không dựng bản thay thế. Tệp chỉ dẫn quy trình cấp dự án `HARNESS.md` nằm trong kho mã.
- Bản xuất đã che dữ liệu cá nhân và bí mật bằng chính bộ lọc của sản phẩm; quét lại toàn bộ bản xuất bằng cùng bộ lọc: 0 chỗ còn khớp. Bộ lọc dựa trên biểu thức chính quy nên không bảo đảm bắt hết mọi dữ liệu cá nhân. Khối suy luận nội bộ của mô hình và ảnh không xuất; kết quả công cụ cắt bớt có ghi số ký tự.

### I.4. Không dùng

- **Không có lời gọi API mô hình ngôn ngữ nào trong sản phẩm** (tìm `anthropic`, `openai` trong `src/` và `web/src`: 0 kết quả ở mã chạy). Câu tường thuật trong báo cáo sinh từ mẫu câu cố định (`src/livelift/analysis/narrate.py`).
- Không dùng nền tảng no-code/low-code, không dùng mô hình huấn luyện sẵn tải từ HuggingFace (ViSoBERT mới ở lộ trình).
- `src/livelift/nlp/label_llm.py` chỉ chuẩn bị lô dữ liệu để gửi đi gán nhãn; tệp không chứa lời gọi mạng.

## II. Mô hình AI trong sản phẩm

| Hạng mục | Kê khai |
|---|---|
| Tên | Bộ phân loại ý định bình luận tiếng Việt: `intent_clf` (v1, 6 lớp, mặc định) và `intent_clf_v2` (11 lớp, chỉ bật khi đặt `LIVELIFT_INTENT_MODEL=v2`) |
| Kiến trúc | TF-IDF ký tự 2–5-gram và từ 1–2-gram, `LogisticRegression` (scikit-learn). Không dùng trọng số huấn luyện sẵn |
| Mã huấn luyện | `src/livelift/nlp/train_intent.py` và `python -m livelift.nlp.eval_intent` — mã do Claude viết |
| Dữ liệu huấn luyện | v1: 320 câu mẫu do Claude soạn. v2: thêm nhãn 11 lớp do AI gán cho bình luận thật (mục III) |
| Hiệu năng | macro-F1 0,870 chỉ là kiểm định chéo trên 320 câu do AI soạn. Trên 393 bình luận thật của 3 buổi live (chia theo buổi, KTC bootstrap): v1 0,211 [0,172; 0,247] → v2 0,542 [0,478; 0,625], đo lại ngày 25/09/2026 sau khi lọc lại handle trong dữ liệu (số ngày 14/09 trên dữ liệu trước khi lọc là 0,565 [0,491; 0,649]; nguồn: `docs/competition/FACT-SHEET.md`). Nhãn tham chiếu do AI gán, nên đây là mức đồng thuận với nhãn AI, chưa phải độ chính xác so với con người |
| Vai trò | Phụ trợ: "radar ý định" trên bàn trợ live. Không tham gia ước lượng nhân quả |
| Lệch phiên bản đã biết | Tệp mô hình đóng gói bằng scikit-learn 1.9.0; tại `main` 390027b, `pyproject.toml` ghim `<1.8`, nên cài sạch theo `pyproject` thì 5 test NLP đỏ và API lùi về bộ phân loại từ khóa. Phát hiện bởi Tiến ngày 21/09, tái hiện ngày 25/09; bản sửa ghim đúng 1.9.0 nằm trên nhánh hoàn thiện hồ sơ ngày 25/09, chờ trưởng nhóm duyệt |

## III. Bộ dữ liệu

| # | Bộ dữ liệu | Cách có | Quy mô | Ai tạo nội dung / nhãn | Giấy phép, lưu trữ |
|---|---|---|---|---|---|
| 1 | Bình luận chat replay của VOD YouTube công khai | Tải bằng yt-dlp (không qua API chính thức); lô đo 10/09/2026 | 19.126 bình luận, 16 buổi live, 7 ngành hàng | Người xem thật; dữ liệu QUAN SÁT, không phải thí nghiệm | Điều khoản YouTube không cho phép cách thu này (`robots.txt` chặn `/live_chat`, `/youtubei/`). Đã khử nhận dạng khi nạp; không nằm trong kho mã |
| 2 | Tập kiểm tra ý định | Trích từ (1), 3 buổi | 393 bình luận | Nhãn do tác tử AI (Claude) gán 09/09/2026 | Cục bộ, không trong kho |
| 3 | Lô huấn luyện ý định | Trích từ (1), 1 buổi khác | 1.800 bình luận | Nhãn do Claude gán 14/09/2026; một mô hình, không người duyệt | Chỉ dùng huấn luyện; cục bộ |
| 4 | Câu mẫu ý định | Soạn mới | 320 câu | Claude soạn 01/09/2026 | Trong kho, `src/livelift/nlp/data/intent_dataset.jsonl` |
| 5 | Kịch bản bình luận mô phỏng | Soạn mới | 200 bình luận | Claude soạn 17/09/2026; số điện thoại, địa chỉ đều giả | Trong kho, `src/livelift/ingest/mo_phong_kich_ban.jsonl`; máy chủ chỉ cho dùng trên phiên chạy thử hoặc phiên mẫu |
| 6 | Câu kiểm thử bộ lọc dữ liệu cá nhân | Soạn mới | 95 câu | Claude soạn (commit `5111e48`, 24/08/2026); dữ liệu giả | Trong kho, `tests/data/pii_comments.jsonl` |
| 7 | Dữ liệu mô phỏng | Sinh bằng `src/livelift/sim/`, mọi bộ sinh ngẫu nhiên có seed | Không giới hạn | Mã do Claude viết | Không chứa dữ liệu người thật |
| 8 | KuaiLive (SIGIR 2026, arXiv:2508.05633) | Tải từ Zenodo, bản ghi 16565801 | 1,16 triệu phòng live | Kế thừa | Giấy phép mâu thuẫn: trang dự án và bài báo ghi CC BY-NC-SA 4.0, siêu dữ liệu Zenodo ghi CC BY 4.0 — đội áp dụng điều kiện chặt hơn (phi thương mại, chia sẻ tương tự), chưa liên hệ tác giả. Chỉ dùng hiệu chỉnh 3 tham số mô phỏng; không tái phân phối |
| 9 | Taobao UserBehavior; LSEC (arXiv:2106.03415) | Chỉ lấy con số công bố trong bài báo | — | Kế thừa | Không tải dữ liệu |
| 10 | Bình luận TikTok công khai | Thử bằng thư viện `TikTokLive` (không chính thức) ngày 09/09/2026 | 0 bình luận (bị từ chối 10/10 lần) | — | Mã giữ trong `collectors/tiktok_public/`, cách ly khỏi lõi |

Những điều đội **không** tuyên bố:

- **0 phiên thí nghiệm ngẫu nhiên thật** đã chạy. Mọi con số hiệu chuẩn thống kê đo trên dữ liệu mô phỏng; 19.126 bình luận là dữ liệu quan sát.
- Chưa có nhãn do người gán cho bất kỳ bình luận thật nào.
- Con số "5–15 người xem đồng thời" trong tài liệu dự án là ước tính từ giá quảng cáo (CPM), chưa đo.

## IV. API bên ngoài

| API | Dùng để | Trạng thái thật ngày 25/09/2026 |
|---|---|---|
| YouTube Data API v3 | Đọc chat live trên kênh của chính nhà bán | Mã có (`src/livelift/ingest/youtube.py`, `scripts/kiem_tra_youtube.py`). Chưa có khóa API; 0 cuộc gọi thật |
| Facebook Graph API v25.0 | Đọc bình luận live trên Page của chính nhà bán | Mã có (`src/livelift/ingest/facebook.py`). Chưa có token; 0 cuộc gọi thật |
| Shopee Open Platform v2 (API loại User, sửa 17/09/2026) | Bình luận và số liệu phiên Shopee Live | Mã có (`src/livelift/ingest/shopee.py`). Chưa có mã đối tác; ngày 11/09 chỉ kiểm endpoint tồn tại qua mã lỗi; 0 cuộc gọi thành công |
| TikTok Shop Open API | Số liệu LIVE theo phút, chỉ có sau phiên | Mã có (`src/livelift/ingest/tiktok_shop.py`, `scripts/kiem_tra_tiktok_shop.py`). Chưa có khóa; 0 cuộc gọi thật |
| YouTube qua yt-dlp (không chính thức) | Tải chat replay VOD; thử đọc live | Nguồn của 100% dữ liệu thật (mục III, dòng 1); đường live thử 1 phiên 104 bình luận ngày 09/09. Đường chạy mặc định của sản phẩm là API chính thức |
| TikTok Webcast qua `TikTokLive` (không chính thức) | Thử đọc phòng live công khai | Thất bại 10/10 lần; không được cài trong môi trường chạy |
| API mô hình ngôn ngữ | — | Không có trong mã sản phẩm |

Khóa và token chỉ đọc từ biến môi trường; `.env` bị `.gitignore`. Tại ngày kê khai, `.env` của đội không có khóa nền tảng nào: các trường YouTube, Facebook để trống; chưa có trường Shopee, TikTok Shop. Quét 58 commit trên mọi nhánh ngày 25/09/2026: 0 khóa thật bị commit.

## V. Thư viện và mã nguồn mở

Giấy phép của sản phẩm: **AGPL-3.0-only**. Phiên bản dưới đây là bản đang cài trong môi trường chạy ngày 25/09/2026; giấy phép lấy từ siêu dữ liệu của gói đã cài (Python) và `web/package-lock.json` (JavaScript).

### V.1. Python

| Thư viện | Phiên bản | Giấy phép | Dùng để |
|---|---|---|---|
| numpy | 2.5.2 | BSD-3-Clause (kèm phần 0BSD, MIT, Zlib, CC0-1.0) | Tính toán số cho thống kê và mô phỏng |
| scipy | 1.18.1 | BSD-3-Clause | Phân vị, kiểm định nhị thức |
| pandas | 3.0.5 | BSD-3-Clause | Đọc dữ liệu KuaiLive khi hiệu chỉnh |
| statsmodels | 0.14.6 | BSD-3-Clause | Hồi quy có sai số chuẩn gom cụm |
| scikit-learn | 1.9.0 | BSD-3-Clause | Bộ phân loại ý định (ghim phiên bản: xem mục II) |
| joblib | 1.5.3 | BSD-3-Clause | Lưu và nạp tệp mô hình |
| pydantic / pydantic-settings | 2.13.4 / 2.15.0 | MIT | Lược đồ API, đọc cấu hình |
| fastapi / starlette | 0.141.1 / 1.6.0 | MIT / BSD-3-Clause | Khung API HTTP và WebSocket |
| uvicorn | 0.52.4 | BSD-3-Clause | Máy chủ ASGI |
| psycopg (binary, pool) | 3.3.4 / 3.3.1 | LGPL-3.0-only | Kết nối PostgreSQL |
| redis | 8.1.0 | MIT | Hàng đợi, bộ đệm |
| httpx | 0.28.1 | BSD-3-Clause | Gọi API nền tảng |
| yt-dlp | 2026.8.19 | Unlicense | Tải chat replay (xem cảnh báo mục III, IV) |
| lightgbm | 4.7.0 | MIT | Khai trong nhóm `ml` nhưng không được import |
| underthesea | không cài | GPL-3.0 | Khai trong nhóm `nlp` nhưng không được cài, không được import |
| pytest / pytest-cov | 9.1.1 / 7.1.0 | MIT | Kiểm thử |
| ruff / mypy | 0.16.4 / 2.3.1 | MIT | Kiểm tra mã |
| playwright | 1.63.0 | Apache-2.0 | Kiểm thử trình duyệt |
| hatchling | — | MIT | Đóng gói |
| python-docx | 1.2.0 | MIT | Dựng hồ sơ và bản kê khai (môi trường riêng) |

### V.2. JavaScript (giao diện web)

| Thư viện | Phiên bản khóa | Giấy phép | Dùng để |
|---|---|---|---|
| next | 14.2.32 | MIT | Khung ứng dụng web |
| react / react-dom | 18.3.1 | MIT | Giao diện |
| recharts | 2.15.4 | MIT | Biểu đồ |
| tailwindcss / postcss / autoprefixer | 3.4.17 / 8.4.49 / 10.4.20 | MIT | CSS |
| typescript | 5.6.3 | Apache-2.0 | Kiểm kiểu |
| @types/node, @types/react, @types/react-dom | 20.19.43 / 18.3.12 / 18.3.1 | MIT | Khai báo kiểu |

Toàn bộ 153 gói trong `web/package-lock.json`: 119 MIT, 20 ISC, 6 Apache-2.0, 3 BSD-3-Clause, 1 0BSD, 1 "MIT AND ISC", 1 CC-BY-4.0 (`caniuse-lite`, dữ liệu trình duyệt), 2 gói không ghi trường giấy phép trong lockfile (`busboy`, `streamsearch` — tệp `package.json` của gói ghi MIT). Không dùng bộ giao diện trả phí hay mẫu mua sẵn.

### V.3. Ảnh Docker

| Ảnh | Giấy phép | Dùng để |
|---|---|---|
| `timescale/timescaledb:latest-pg16` | Apache-2.0 (một số tính năng theo Timescale License) | Cơ sở dữ liệu |
| `redis:7-alpine` | BSD-3-Clause | Hàng đợi, bộ đệm |
| `caddy:2-alpine` | Apache-2.0 | Cổng vào HTTPS |
| `python:3.11-slim`, `node:20-alpine` | Giấy phép của Python (PSF) và Node.js (MIT) | Ảnh nền dựng API và web |

Các giấy phép trên đều cho phép dùng trong sản phẩm AGPL-3.0; gói GPL-3.0 duy nhất (`underthesea`) không được cài.

## VI. Mã nguồn tham khảo và kế thừa

Không có đoạn mã nào ghi là chép từ kho mã của người khác (tìm các dấu hiệu "copied from", liên kết StackOverflow hoặc GitHub trong `src/`: 0 kết quả; một chỗ ghi "adapted from" là chuyển thể phương pháp từ bài báo). Mã cài đặt công thức do Claude viết, trích nguồn tại chỗ:

| Vị trí trong mã | Nguồn | Kế thừa cái gì |
|---|---|---|
| `core/assigner/outer.py` | Bojinov, Simchi-Levi & Zhao, Management Science 69(7), 2023 (arXiv:2009.00148) | Thiết kế thí nghiệm switchback — nền tảng phương pháp |
| `core/assigner/outer.py`, `core/features.py` | Hu & Wager (arXiv:2209.00197) | Cửa sổ burn-in khi phân tích |
| `analysis/estimators.py`, `analysis/carryover.py` | Bojinov & Shephard, JASA 2019 | Kiểm định ngẫu nhiên hóa khớp thiết kế |
| `analysis/adjust.py` | Deng, Knoblich & Lu, KDD 2018 (arXiv:1803.06336); arXiv:2608.24038; arXiv:2606.27662 | Phương sai delta cho chỉ số tỷ lệ; CUPED nhiều biến; cảnh báo ít cụm |
| `analysis/robust.py` | Lin, Ann. Appl. Stat. 2013; Cameron, Gelbach & Miller, REStat 2008; arXiv:2510.01127 | Hiệu chỉnh hồi quy, sai số chuẩn CR1, kiểm định mẫu số |
| `analysis/power.py` | Công thức MDE của J-PAL; arXiv:2106.03415 | Cỡ hiệu ứng tối thiểu phát hiện được; hệ số khán giả |
| `core/quality.py`, `core/click_validity.py` | Bakshy, Eckles & Bernstein, WWW 2014; Fabijan và cộng sự, KDD 2019 | Kiểm tra chất lượng gán, lệch tỷ lệ mẫu, lọc nhấp chuột bot |
| `sim/report.py` | Talts và cộng sự (arXiv:1804.06788); Modrák và cộng sự (arXiv:2211.02383) | Kiểm định hiệu chuẩn dựa trên mô phỏng, chuyển sang đại lượng tần suất |
| `core/features.py` | Nguyễn và cộng sự, IMCOM 2026 | Đặc trưng nhịp thả tim trước khối |
| `core/moments.py` | Sản phẩm thương mại Feigua | Ý tưởng giao diện đánh dấu "khoảnh khắc" trên dòng thời gian (không có mã của Feigua) |
| `ingest/shopee.py` | SDK TypeScript chính thức của Shopee | Bảng máy chủ theo khu vực và lược đồ ký yêu cầu — đặc tả giao thức, viết lại bằng Python |
| `ingest/youtube_ytdlp.py` | Mã nguồn yt-dlp | Đọc để chẩn đoán độ trễ, không chép |
| `ingest/pii/admin_units.py` | — | Danh sách đơn vị hành chính Việt Nam do Claude soạn (commit `5111e48`), chưa dẫn nguồn chính thức |
| `nlp/labels.py` | Buổi live-fire (dữ liệu mục III, dòng 1) | Vài câu ví dụ trích nguyên văn bình luận thật đã lọc dữ liệu cá nhân, có ghi chú tại chỗ |

Các nguồn tài liệu trên do Claude tìm và đọc trong quá trình phát triển (nhật ký ghi 765 lần tìm web và 988 lần đọc trang web).

## VII. Phân định: đội tự làm, AI tạo ra, kế thừa

### VII.1. Số đo kiểm được

| Chỉ số | Giá trị | Nguồn |
|---|---|---|
| Commit trên `main` | 56 commit trong 17 ngày (24/08 → 18/09/2026), +166.177 / −7.498 dòng | `git log` |
| Commit mang dòng đồng tác giả Claude | **56/56** | `git log --format=%(trailers)` |
| Danh tính tác giả git | Cả 56 commit dùng một danh tính chung "LiveLift Team" | `git log --format=%an` |
| Commit trên nhánh PR số 1 (chưa hợp nhất) | 2 commit của Tiến, 0 dòng khai báo AI; tài liệu trong commit ghi do Antigravity và Codex tạo | `git log origin/tien/aisc-round2` |
| Câu lệnh người gõ cho Claude Code | 78 (5 phiên), thêm 9 lệnh `/model` | Prompt Log, mục I.3 |
| Lời gọi công cụ của Claude | 24.957, trong đó 3.376 lần ghi hoặc sửa tệp | Prompt Log |
| Tác tử con do Claude sinh ra | 567 nhật ký | Prompt Log |

### VII.2. Phân định theo thành phần

| Thành phần | Đội tự làm | AI tạo ra | Kế thừa |
|---|---|---|---|
| Ý tưởng, bài toán, mục tiêu dự thi | Đưa ra ý tưởng và hai tệp mô tả, kế hoạch ban đầu (nguồn gốc khai ở mục X); đặt mục tiêu và yêu cầu qua 78 câu lệnh | Phân tích, góp ý, đề xuất phương pháp, lập kế hoạch chi tiết | Thiết kế switchback từ bài báo (mục VI) |
| Mã nguồn: lõi thống kê, API, cơ sở dữ liệu, web, nạp dữ liệu, bộ lọc dữ liệu cá nhân, NLP | Yêu cầu, chọn hướng khi Claude đưa phương án, chấp nhận kết quả | Claude viết gần như toàn bộ (mọi commit trên `main` có dòng đồng tác giả Claude); phần của Tiến trên PR số 1 do Codex viết | Thư viện mục V; công thức từ bài báo mục VI |
| Kiểm thử và cổng chất lượng | Đặt yêu cầu "test đỏ trước, xanh sau" trong quy trình | Claude viết test và chạy | pytest, Playwright |
| Kiểm toán, sổ sự cố | Yêu cầu kiểm toán, quyết định sửa gì | Các đợt kiểm toán nhiều tác tử do Claude chạy; sổ sự cố do Claude ghi | — |
| Dữ liệu và nhãn | Quyết định dùng và cách dùng | Nhãn 393 + 1.800 dòng; 320 câu mẫu; 200 bình luận mô phỏng; 95 câu kiểm thử | Bình luận VOD công khai (qua yt-dlp); KuaiLive |
| Tài liệu và hồ sơ dự thi | Đọc, sửa, chịu trách nhiệm, ký | Claude soạn nháp, kể cả bản kê khai này | — |
| Việc ngoài kho mã (phỏng vấn nhà bán, quay video, gán nhãn thủ công, xác minh kênh) | Chưa có bằng chứng trong kho mã tại ngày kê khai; thành viên nào đã làm thì tự khai kèm bằng chứng | — | — |

Đội không có phép đo tách số dòng mã do người gõ khỏi số dòng AI gõ, nên không nêu tỷ lệ phần trăm. Theo dòng đồng tác giả và nhật ký, có thể nói thẳng: phần mã và tài liệu trong kho do AI tạo ra; phần của đội là đặt bài toán, ra yêu cầu, lựa chọn, duyệt, vận hành công cụ và chịu trách nhiệm.

## VIII. Quy trình kiểm chứng đầu ra AI

- Quy trình cấp dự án `HARNESS.md`: logic quyết định là hàm thuần, kiểm thử được không cần hạ tầng; mỗi lỗi phải có test tái hiện trước khi sửa và một dòng trong sổ sự cố.
- Bộ kiểm thử (theo `docs/competition/FACT-SHEET.md`, 25/09/2026): 1.919 test thu thập trên nhánh hoàn thiện hồ sơ — 1.892 test nhanh, 17 test chậm (13 mô phỏng/thống kê, 1 đánh giá NLP, 3 dựng CSS), 10 test trình duyệt. Số thu thập không phải số đã chạy. Lần chạy gần nhất đều trên `main` 390027b: 17/17 test chậm đạt, 10/10 test trình duyệt đạt, bộ nhanh 1.800 đạt · 3 bỏ qua · 0 lỗi (1.803 test, bản sao sạch, scikit-learn 1.9.0).
- Hiệu chuẩn thống kê (trên mô phỏng, 200 lần lặp A/A): tỷ lệ bác bỏ 3,50% (7/200), p nhị thức 0,4168; độ phủ khoảng tin cậy 95% là 96,50%. Tái lập đúng từng chữ số ngày 25/09/2026.
- Sổ sự cố `docs/incident-log.md`: 60 sự cố có nguyên nhân gốc (đếm 25/09/2026).
- Các ràng buộc chống nói quá nằm trong mã: thẻ dự báo từ mô hình không mang khoảng tin cậy; màn hình người dẫn không thấy nhánh thí nghiệm; phân tích VOD không mang ngôn ngữ thí nghiệm; nhãn DEMO/THẬT do máy chủ quyết định.
- Các lỗi đã biết còn mở tại ngày kê khai được ghi trong sổ sự cố và báo cáo kiểm toán, không lược đi.

## IX. Dữ liệu cá nhân và trách nhiệm pháp lý

- Đội **không** tuyên bố đã có sự đồng ý của người bình luận trong 19.126 bình luận và **không** viện dẫn căn cứ xử lý dữ liệu không cần sự đồng ý. Dữ liệu này chỉ dùng offline để đánh giá mô hình, đã khử nhận dạng tại điểm nạp (không lưu tên hay mã kênh người bình luận), không phát hành lại, không nằm trong kho mã. Đội sẽ xóa dữ liệu này khi Ban Tổ chức hoặc cơ quan có thẩm quyền yêu cầu.
- Kiểm tra ngày 14/09/2026 từng phát hiện handle mạng xã hội còn sót trong dữ liệu gán nhãn cục bộ do bộ lọc cũ chỉ nhận ký tự ASCII. Bộ lọc đã sửa ngày 15/09; ngày 25/09 quét lại còn 57 handle và đã lọc lại tại chỗ bằng đúng hàm của sản phẩm, quét lại ra 0 (`data/labeling/README.md`).
- Trên sản phẩm, nhà bán chỉ đọc phiên của chính mình qua API chính thức; phiên thí điểm có khán giả chỉ chạy khi có văn bản đồng ý của shop đối tác.
- Prompt Log nộp kèm đã che email, số điện thoại, mã số sinh viên của thành viên và handle của người xem; nhật ký gốc không tải lên.
- Theo Luật Trí tuệ nhân tạo 134/2025/QH15, đội tự đánh giá LiveLift ở mức rủi ro thấp: hệ thống không sinh nội dung, không tương tác trực tiếp với người xem, không ra quyết định thay con người. Đội sẽ đánh giá lại trước khi thêm trợ lý hội thoại hay gợi ý bằng giọng nói.


## X. Cam kết và chữ ký

Chúng tôi, ba thành viên đội thi LiveLift, cam kết:

1. Bản kê khai này trung thực và đầy đủ theo hiểu biết của chúng tôi tại ngày ký, kể cả những điểm bất lợi: dữ liệu thật thu bằng yt-dlp trái điều khoản YouTube, nhãn dữ liệu do AI gán, phần lớn mã và tài liệu do AI tạo ra, lịch sử commit dùng một danh tính chung, và các khẳng định sai trong bản kê khai cũ đã đính chính ở trên.
2. Chúng tôi hiểu, kiểm chứng được, chỉnh sửa được, vận hành được và chịu trách nhiệm với toàn bộ sản phẩm, kể cả phần do công cụ AI tạo ra, và sẵn sàng trình bày, chạy lại mọi con số trước Ban Giám khảo.
3. Chúng tôi không thi hộ, không thuê làm, không để người ngoài làm thay, không sao chép sản phẩm, không giả mạo Prompt Log, lịch sử commit, dữ liệu thử nghiệm hay video demo, và không che giấu nguồn mã, dữ liệu, API.
4. Nếu phát hiện thiếu sót trong bản kê khai, chúng tôi bổ sung ngay và báo Ban Tổ chức.

Mỗi thành viên tự ghi vào cột thứ ba các công cụ AI khác đã dùng cho LiveLift ngoài những gì kê ở mục I (ghi "không" nếu không dùng), và nguồn gốc hai tệp ý tưởng, kế hoạch ban đầu nếu mình tham gia soạn.

TP. Hồ Chí Minh, ngày ...... tháng ...... năm 2026

<!-- BANG-KY -->

| Họ và tên | Vai trò | Công cụ AI khác đã dùng cho LiveLift, nguồn gốc tệp ý tưởng ban đầu (tự ghi) | Chữ ký |
|---|---|---|---|
| Ngô Bình Minh | Đội trưởng | | |
| Lê Xuân Khánh | Thành viên | | |
| Ngô Lâm Tiến | Thành viên | Google Antigravity, OpenAI Codex (21/09/2026) — theo tài liệu trên nhánh `tien/aisc-round2`; bổ sung: | |

## Phụ lục — lệnh tái lập các con số

```
# Prompt Log: đếm câu lệnh người gõ theo phiên (không ghi tệp)
python scripts/xuat_prompt_log.py --kiem-tra --sao-luu D:/AISC2026/prompt-log-goc/2026-09-15
# Xuất Prompt Log đã làm sạch, rồi quét lại (phải ra 0)
python scripts/xuat_prompt_log.py --ra D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE/01-Prompt-Log
python scripts/xuat_prompt_log.py --quet D:/AISC2026/GOI-DRIVE-SANG-TAO-TRE/01-Prompt-Log
# Commit, dòng đồng tác giả, danh tính
git rev-list --count main
git log main --format="%(trailers:key=Co-Authored-By,valueonly)" | sort | uniq -c
git log --all --format="%an" | sort | uniq -c
git log main --shortstat --format="" | awk '{i+=$4; d+=$6} END {print i, d}'
# Quét khóa bí mật trên mọi commit của mọi nhánh (chỉ ra chuỗi giả dùng trong test)
git grep -I -o -E "AIza[0-9A-Za-z_-]{30,}|EAA[A-Za-z0-9]{60,}|sk-ant-[A-Za-z0-9_-]{30,}|gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}" $(git rev-list --all)
# Thư viện Python và giấy phép đã cài; gói JavaScript theo lockfile
python -m pip list --format=freeze
node -e "const p=require('./web/package-lock.json').packages; console.log(Object.keys(p).length-1)"
# Số test, hiệu chuẩn, sổ sự cố
python scripts/dong_bo_so_test.py --xem-truoc
python scripts/do_lai_so_hieu_chuan.py --kiem
grep -cE '^\| [0-9]{2}/[0-9]{2}/[0-9]{4} ' docs/incident-log.md
# Đánh giá bộ phân loại ý định
python -m livelift.nlp.eval_intent
# Dựng lại bản kê khai này (DOCX + PDF)
.venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/ke_khai/dung_ke_khai.py
```
