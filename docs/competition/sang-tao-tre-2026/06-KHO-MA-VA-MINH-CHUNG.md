# KHO MÃ NGUỒN & GÓI MINH CHỨNG — TRẠNG THÁI, VIỆC CẦN LÀM, THIẾT KẾ DRIVE

**Phục vụ:** hạng mục 4 (đường dẫn kho lưu trữ mã nguồn) và mục 13 MẪU 3 (link Google Drive:
Prompt Log + minh chứng phát triển + tài liệu kỹ thuật)
**Lập ngày:** 14/09/2026 · **Trạng thái repo khi kiểm:** commit `dd66b38`, nhánh `main`, 42 commit
**Tài liệu liên quan:** [`05-BAN-KE-KHAI.md`](05-BAN-KE-KHAI.md) · [`BRIEF-THE-LE.md`](BRIEF-THE-LE.md)

---

## 0. TÓM TẮT ĐIỀU HÀNH — ba việc chặn nộp

| # | Việc | Vì sao chặn | Ai làm | Thời lượng |
|---|---|---|---|---|
| **P0-1** | ⛔ **Repo đang PRIVATE — giám khảo không mở được** | Hạng mục 4 là "đường dẫn kho lưu trữ mã nguồn". Link tới repo private = **nộp thiếu hạng mục** | Con người (đội trưởng, GitHub) | 2 phút |
| **P0-2** | ⛔ **53 handle mạng xã hội thật còn trong dữ liệu đã lưu** | Dữ liệu cá nhân chưa khử nhận dạng (NĐ 13/2023). Nếu lên Drive = **công bố dữ liệu cá nhân trái phép** | Agent sửa mã + đội chạy lại | 1–2 giờ |
| **P0-3** | ⛔ **Mâu thuẫn lời văn về yt-dlp trong thuyết minh** | Thuyết minh nói yt-dlp "không đưa vào hồ sơ"; thực tế **100% dữ liệu thật** thu bằng nó. Giám khảo đối chiếu ra = nghi ngờ toàn bộ hồ sơ | Con người viết lại | 30 phút |

Các việc còn lại là P1/P2, không chặn nộp.

---

# PHẦN A — TRẠNG THÁI KHO MÃ NGUỒN

## A.1. Thông tin kho

| Hạng mục | Giá trị |
|---|---|
| URL | `https://github.com/bminhnemhoi/AISC2026_LIVEFIT` |
| Chủ sở hữu | `bminhnemhoi` (tài khoản cá nhân của đội trưởng) |
| Nhánh | `main` (nhánh duy nhất) · HEAD `dd66b38`, đồng bộ với `origin/main` |
| **Quyền truy cập** | ⛔ **PRIVATE** |
| Giấy phép | AGPL-3.0-only (`LICENSE`, 34 KB, toàn văn) |
| File theo dõi | 322 · dung lượng ~6,2 MB |
| Commit | 42, trải 14 ngày làm việc (24/08 → 14/09/2026) |
| CI | GitHub Actions (`.github/workflows/ci.yml`), 5 job |

## A.2. ⛔ P0-1 — Repo đang PRIVATE

**Cách kiểm chứng (đã chạy 14/09/2026):**

```
$ curl -s -o /dev/null -w "%{http_code}" https://api.github.com/repos/bminhnemhoi/AISC2026_LIVEFIT
404

$ curl -s -o /dev/null -w "%{http_code}" https://raw.githubusercontent.com/.../main/README.md
404
```

GitHub trả **404 cho người dùng chưa đăng nhập** — đây là cách GitHub báo "private" (không trả 403,
để không lộ sự tồn tại của repo). Lệnh `git ls-remote` từ máy đội **chạy được** chỉ vì máy đó có
credential đã lưu — **đừng dùng phép thử đó để kết luận repo công khai.**

**Hệ quả nếu nộp nguyên trạng:** giám khảo bấm link → trang 404 → hạng mục 4 coi như **không nộp**.
Đây là lỗi vận hành thuần túy, mất điểm oan nhất trong cả hồ sơ.

**Hai phương án:**

| Phương án | Ưu | Nhược | Khuyến nghị |
|---|---|---|---|
| **Chuyển sang Public** | Giám khảo mở được ngay, không cần thao tác; badge CI hiển thị đúng; hợp tinh thần AGPL-3.0 mà đội đã chọn | Mã nguồn lộ công khai | ✅ **CHỌN** — AGPL-3.0 vốn đã là cam kết mở; giữ private trong khi cấp phép AGPL là tự mâu thuẫn |
| Giữ Private + mời giám khảo làm collaborator | Kiểm soát được ai xem | BTC **chưa công bố danh sách tài khoản GitHub của giám khảo**; mời sai/thiếu người = giám khảo vẫn 404; thêm một điểm hỏng ngoài tầm kiểm soát của đội | ❌ Rủi ro cao hơn lợi ích |

**Trước khi chuyển Public phải xong P0-2** (xem A.6) — nhưng tin tốt: **kho mã hiện đã sạch dữ liệu
cá nhân** (kiểm chứng ở A.6), nên hai việc này có thể làm song song.

> ⚠️ Tôi **không** tự đổi quyền repo. Đây là thao tác con người phải tự bấm, có xác nhận.

## A.3. ⚠️ P1 — Tên kho gõ sai: `AISC2026_LIVEFIT` vs sản phẩm `LiveLift`

Sản phẩm tên **LiveLift** ("nâng" — *lift* — hiệu quả phiên live). Tên kho là `LIVEFIT` — **đảo hai
chữ cái**, đọc ra "live fit" (vừa vặn), nghĩa hoàn toàn khác. README, CITATION, tên gói Python,
toàn bộ tài liệu đều dùng "LiveLift".

**Rủi ro nếu KHÔNG sửa:** giám khảo thấy tên kho lệch tên sản phẩm → nghi "kho này có phải của dự
án đang chấm không?" → mất vài giây tin cậy ngay ở chạm đầu tiên.

**Rủi ro nếu SỬA — đã kiểm, thấp hơn dự kiến:**

- GitHub **tự chuyển hướng vĩnh viễn** URL cũ → URL mới (web, `git clone`, API). Link cũ đã nộp
  vẫn chạy.
- Chỉ **2 file** trong repo nhắc tên kho: `README.md` (badge CI + lệnh clone) và `CITATION.cff`.
  Sửa 3 dòng là xong.
- ⚠️ Rủi ro thật duy nhất: nếu sau này ai đó tạo repo mới trùng tên `AISC2026_LIVEFIT`, chuyển
  hướng sẽ **hỏng**. Xác suất thấp, và đội kiểm soát tài khoản.

**Khuyến nghị:** đổi thành **`livelift`** (hoặc `AISC2026_LIVELIFT`), sửa 3 dòng, rồi **dùng URL
mới trong mọi tài liệu nộp**. Nếu hết thời gian → **giữ nguyên tên và thêm một dòng trong README**:
*"Kho này là mã nguồn của sản phẩm **LiveLift**; tên kho có lỗi gõ, giữ nguyên để không hỏng link
đã công bố."* — Minh bạch còn hơn để giám khảo tự đoán.

## A.4. ✅ Lịch sử commit — đây là TÀI SẢN, không phải thủ tục

Thể lệ (Điều 5 §7) cấm **giả mạo commit history**, và vòng Khu vực yêu cầu **"repo có commit
history thật"**. Lịch sử của đội không chỉ đạt — nó **chứng minh** được nhiều điều.

**Số liệu (sinh lại bằng `git log`):**

| Chỉ số | Giá trị |
|---|---|
| Commit | 42, trải **14 ngày riêng biệt** trong 22 ngày lịch |
| Phân bố | 25/08: 7 · 02/09: 8 · 01/09: 6 · 14/09: 5 · … (nhịp không đều — dấu hiệu làm thật) |
| Dòng | +79.999 / −5.408, chạm 736 lượt file |
| Thông điệp | 100% tiếng Việt không dấu, mô tả **nội dung thật**, dòng đầu ≤ 72 ký tự (đúng `HARNESS.md` §6) |
| Đồng tác giả AI | **42/42 commit** có trailer `Co-Authored-By: Claude …` |

**Lịch sử này chứng minh 4 điều mà không tài liệu nào thay thế được:**

1. **Không giả mạo.** Không có kiểu "1 commit khổng lồ" hay "40 commit trong 1 giờ". Nhịp làm việc
   không đều, có ngày trống — đúng nhịp sinh viên làm dự án thật.
2. **Đội tự bắt lỗi của AI.** Thông điệp commit ghi thẳng: `e47169e` *"FATAL x2 tu kiem toan doi
   khang: sua loi bao 'co y nghia' tren nhieu thuan"*, `0969b0f` *"Sua cong thuc MDE: bo 2 hieu
   chinh khong thuoc thiet ke"*, `e2be454` *"Sua 8 loi tim duoc khi dong vai nguoi dung"*.
   **Một đội chỉ bấm "chấp nhận" không có những commit này.**
3. **Khai báo AI trung thực từ đầu**, ở từng commit, suốt 22 ngày — không phải khai lùi sau khi
   đọc thể lệ.
4. **Có tiến hoá thật.** `5111e48` (nền tảng lõi) → `3f55321` (API) → `b4a...` (web) → `14e93ac`
   (thiết kế lại toàn diện) → `dd66b38` (6 giám khảo độc lập). Đúng đường "bản nháp → hoàn thiện"
   mà mục 13 MẪU 3 đòi hỏi.

**⚠️ Điểm yếu duy nhất:** cả 42 commit mang **một danh tính con người** (`LiveLift Team
<ngobinhminh2322006@gmail.com>`) vì đội làm chung trên một máy. Không phải giả mạo, nhưng **không
thể hiện đóng góp riêng từng thành viên** và giám khảo có quyền hỏi.
**Xử lý: bổ sung mục "phân công theo thành viên" vào README hoặc thuyết minh. TUYỆT ĐỐI KHÔNG viết
lại lịch sử git để "chia lại" tác giả** — đó chính là hành vi bị cấm.

## A.5. ✅ Quét bí mật — SẠCH

Đã quét **toàn bộ nội dung 42 commit** (`git log --all -p`) tìm: Google API key (`AIza…`), token
Facebook (`EAA…`), khoá OpenAI/Anthropic (`sk-…`), GitHub PAT (`ghp_…`), khoá AWS (`AKIA…`),
khoá riêng tư PEM.

**Kết quả: 0 phát hiện.** Không có bí mật nào bị commit nhầm.

Kiểm bổ sung:

| Kiểm | Kết quả |
|---|---|
| `.env` có bị theo dõi không? | ✅ **Không** — chỉ `.env.example` và `web/.env.example` vào git |
| `.env` từng xuất hiện trong lịch sử? | ✅ **Chưa bao giờ** |
| `.env` cục bộ có chứa gì? | ✅ **Mọi credential nền tảng đều RỖNG** (`YOUTUBE_API_KEY=`, `FACEBOOK_PAGE_ACCESS_TOKEN=`, …). Chỉ có mật khẩu Postgres dev |
| `.gitignore` | ✅ **Tốt** — chặn `.env`, `*.pem`, `*.key`, `secrets/`, `data/raw/`, `data/sessions/`, `data/snapshot/`, `data/labeling/*`, `backups/`, `web/node_modules/` |

**Kết luận: không có sự cố P0 về bí mật.** Đây là điểm mạnh đáng nêu trong hồ sơ.

## A.6. ⛔ P0-2 — Dữ liệu cá nhân: kho mã SẠCH, nhưng dữ liệu trên đĩa CÓ RÒ RỈ

Đã **mở file dữ liệu ra kiểm trực tiếp**, không tin tài liệu.

### Kết quả quét

| Nơi | Số điện thoại | Email | Handle MXH | Kết luận |
|---|---|---|---|---|
| **Kho mã GitHub** (322 file) | 0 | 0 | 0 | ✅ **SẠCH** |
| `data/snapshot/livelift-store.json` (1,77 tr. ký tự) | 0 | 0 | **0** | ✅ **SẠCH** |
| `data/labeling/lot1-…/comments_*.jsonl` (6.586 dòng) | 0 | 0 | ⛔ **53 (37 duy nhất)** | ❌ **RÒ RỈ** |
| Nhật ký Claude Code (292 file) | có | có | ⛔ **2 file có handle thật** | ❌ **Phải lọc trước khi lên Drive** |

Ví dụ còn nguyên trên đĩa (tên đã che khi đưa vào kho mã — bản gốc là tài khoản thật): `@Cư***`, `@Gi***`, `@Ki***`, `@Ng***`,
`@Ng***`, `@DŨ***`. **Mỗi handle mở thẳng ra một kênh YouTube cụ thể** ⇒ **định
danh trực tiếp một con người** theo Nghị định 13/2023/NĐ-CP.

### Nguyên nhân gốc (đã truy tới dòng mã)

```python
# src/livelift/ingest/pii/patterns.py:198
SOCIAL_HANDLE_RE = re.compile(r"(?<![\w.@])@[A-Za-z0-9_.]{3,32}\b")
#                                        ^^^^^^^^^^^^^^^ CHỈ ASCII, thiếu chữ có dấu và dấu "-"
```

Handle YouTube tiếng Việt gần như luôn có dấu và thường có hậu tố `-xxx` ⇒ **không khớp**.
Thậm chí có trường hợp bộ lọc địa chỉ bắn nhầm vào giữa handle, để lại
`@Bạ***-[ĐỊA CHỈ]i` — vừa lộ tên, vừa hỏng dữ liệu.

### ⚠️ Vì sao cổng chất lượng không bắt được — bài học quan trọng hơn cả lỗi

- `HARNESS.md` §2 quy định cổng "PII recall ≥ 95% **từng loại**", nhưng chỉ liệt kê
  **SĐT · email · mã đơn · địa chỉ** — **KHÔNG có loại "handle mạng xã hội"**.
- Bộ đánh giá `tests/data/pii_comments.jsonl` (95 dòng) có các nhãn
  `phone, email, order, address, name` — **không có nhãn `social`**.
- Test hiện có chỉ kiểm handle **ASCII** (`@hoa_nguyen`, `tiktok.com/@shopcuahoa`).

⇒ **Lỗi lọt vì không ai đo nó**, không phải vì bộ lọc hỏng. Con số "recall ≥95%" đã công bố **vẫn
đúng với 5 loại được đo** — nhưng không bao trùm loại thứ 6.

### Việc phải làm (4 bước, ~1–2 giờ)

1. **Sửa regex** → lớp ký tự Unicode + dấu gạch ngang. Bản đã sửa (kiểm chứng chạy được) nằm
   trong `scripts/xuat_prompt_log.py`:
   `r"(?<![\w.@/])@[A-Za-z0-9À-ỹĐđ][A-Za-z0-9À-ỹĐđ._\-]{2,31}"`
2. **Thêm loại `social`** vào `tests/data/pii_comments.jsonl`, có ca tiếng Việt có dấu + có `-`.
3. **Thêm `social` vào cổng** `HARNESS.md` §2 và test PII recall.
4. **Chạy lại bộ lọc trên dữ liệu ĐÃ LƯU** (`data/labeling/`, CSDL) — sửa mã không tự làm sạch
   dữ liệu cũ. **Bước này quan trọng nhất và dễ quên nhất.**

> Lưu ý phân công: bước 1–3 là sửa mã nghiệp vụ, thuộc agent kiểm toán mã / NLP. Tài liệu này chỉ
> nêu phát hiện, nguyên nhân gốc, và bản vá đã kiểm chứng.

## A.7. ⛔ P0-3 — Mâu thuẫn về yt-dlp giữa mã nguồn và thuyết minh

| Nguồn | Nói gì |
|---|---|
| `docs/competition/thuyet-minh/noi-dung.json` | đường yt-dlp "chỉ dùng kiểm thử kỹ thuật, **không đưa vào hồ sơ dự thi**" |
| Thực tế đo được | **19.126/19.126 bình luận (100%)** thu qua `POST /replays/youtube` → `youtube_replay.py` → **yt-dlp** |

Hai câu này **không thể cùng đúng**. Giám khảo đọc mã 10 phút là thấy.

**Thêm hai điểm phải xử lý trong mã (agent khác làm, nêu ở đây để không sót):**

1. `src/livelift/ingest/youtube_ytdlp.py` (đường **live**) có **30 dòng cảnh báo ToS** rất tử tế.
   `src/livelift/ingest/youtube_replay.py` (đường **VOD** — thứ thật sự sinh ra 100% dữ liệu)
   **không có cảnh báo nào**. Phải bổ sung cảnh báo ngang mức.
2. ⚠️ `youtube_replay.py` có đường `YTDLP_COOKIES_FROM_BROWSER` hướng dẫn nạp **cookie đăng nhập
   YouTube của chính thành viên** để vượt kiểm tra chống bot. Dùng phiên đã đăng nhập để vượt biện
   pháp chống tự động hoá là mức vi phạm **nặng hơn** truy cập ẩn danh, và gắn trách nhiệm vào tài
   khoản cá nhân. **Khuyến nghị: tắt mặc định + cảnh báo rõ ràng khi bật.**

**Lời văn thay thế cho thuyết minh (dùng được ngay):**

> *Toàn bộ 19.126 bình luận dùng trong hồ sơ này được thu từ chat replay của VOD công khai trên
> YouTube bằng công cụ `yt-dlp`. Chúng tôi kê khai rõ: phương thức truy cập này **không được điều
> khoản dịch vụ YouTube cho phép** (robots.txt chặn `/live_chat` và `/youtubei/`), dù không tải
> video và không đọc dữ liệu phi công khai. Chúng tôi chọn kê khai thay vì che giấu. Đường chính
> thức là YouTube Data API v3 — đã cài đặt sẵn trong mã (`ingest/youtube.py`), chỉ chờ API key, và
> là đường duy nhất được dùng cho mọi phiên thí nghiệm từ nay. Chúng tôi không mở rộng quy mô thu
> bằng yt-dlp và không tái phân phối dữ liệu thô.*

## A.8. README — người lạ có clone và chạy được trong 10 phút không?

**Đánh giá: CÓ, đường Docker chạy được** — README thuộc nhóm tốt (18,5 KB, có badge, có mục lục,
có §"Khởi động trong 5 phút", có ảnh chụp màn hình). Nhưng có vài chỗ vấp.

```bash
git clone https://github.com/bminhnemhoi/AISC2026_LIVEFIT.git && cd AISC2026_LIVEFIT
cp .env.example .env        # sửa POSTGRES_PASSWORD
docker compose up -d
```

| # | Vấn đề | Mức | Cách sửa (1 dòng) |
|---|---|---|---|
| 1 | `cp` **không có** trong PowerShell mặc định, mà repo là Windows-first ở mọi chỗ khác | P1 | Thêm `Copy-Item .env.example .env` cho Windows |
| 2 | `docker compose up` **fail cứng** nếu không sửa `POSTGRES_PASSWORD` (`docker-compose.yml` dùng `${POSTGRES_PASSWORD:?…}`) — README chỉ ghi trong comment cuối dòng | P1 | Tách thành bước riêng, in đậm |
| 3 | Chạy **ngoài Docker** sau `cp .env.example .env` sẽ dính `STORE_BACKEND=memory`: kho RAM **có ảnh chụp 30 giây** (mặc định bật — `store_snapshot_enabled=True` trong `config.py`, `STORE_SNAPSHOT_ENABLED=true` trong `.env.example`, có từ commit `e2be454` ngày 12/09). Tắt có trật tự thì chụp lần cuối, không mất gì; tiến trình chết đột ngột thì **mất tối đa ~30 giây** dữ liệu cuối. Chỉ Postgres (đường Docker) mới bền vững. Sự cố FATAL 11/09 (mất 13 phiên + 17.535 bình luận) xảy ra **trước** khi có ảnh chụp — chính nó là lý do thêm ảnh chụp | P2 *(bản lập 14/09 ghi P0 và "mất sạch dữ liệu khi khởi động lại" — sai, ảnh chụp đã bật mặc định từ 12/09; đính chính 17/09/2026)* | Thêm một dòng nói rõ mức mất tối đa + trỏ `docs/luu-tru-du-lieu.md` |
| 4 | Không có **bước xác minh**. `docker-compose.yml` tự ghi "kiểm tra: `curl /health` → `durable: true`" nhưng README không nhắc | P1 | Thêm 1 dòng `curl` cuối quickstart |
| 5 | Chiếm cổng 80/443 vô điều kiện — máy có IIS/Skype sẽ fail | P2 | Ghi chú + trỏ `docker-compose.dev-ports.yml` |
| 6 | `scripts/chay_local.py` (bộ khởi động 1 lệnh) và `Makefile` **không xuất hiện trong README** | P2 | Thêm vào mục phát triển |
| 7 | ~30 biến môi trường trong `.env.example` không được README nhắc — người lạ dựng được hệ thống nhưng **không nạp được dữ liệu từ nền tảng nào** | P1 | Thêm bảng "muốn nạp dữ liệu thật cần gì" |

**Ưu tiên:** sửa #2 (chặn fail khởi động), rồi #1, #4, #7, rồi #3 (nói đúng mức mất tối đa của chế độ memory). *Đính chính 17/09/2026: bản 14/09 xếp #3 lên đầu vì tưởng chế độ memory mất sạch dữ liệu khi khởi động lại — ảnh chụp 30 giây đã bật mặc định từ 12/09.*

## A.9. ✅ Những thứ đã đạt chuẩn — không cần đụng

| Hạng mục | Trạng thái |
|---|---|
| `LICENSE` | ✅ AGPL-3.0-only toàn văn. Phù hợp (dịch vụ qua mạng), tương thích mọi phụ thuộc (BSD/MIT/Apache/Unlicense) |
| `CITATION.cff` | ✅ Có, hợp lệ CFF 1.2.0. ⚠️ Chỉ ghi `LiveLift Team`, chưa có tên 3 thành viên — nên bổ sung |
| `CONTRIBUTING.md` | ✅ Có, trỏ `HARNESS.md` là "luật", kèm checklist trước PR |
| `HARNESS.md` | ✅ Hợp đồng quy trình — **đóng vai "System Prompt" cấp dự án** cho hồ sơ |
| `.github/workflows/ci.yml` | ✅ 5 job: lint · test+coverage · isolation · web build · nightly slow |
| `.gitignore` | ✅ Đầy đủ, có chú thích tiếng Việt giải thích **vì sao** từng mục bị chặn |
| `web/package-lock.json` | ✅ Đã commit ⇒ build JS tái lập được |
| Bộ test | ✅ 890 hàm test / 58 file |
| `PREREGISTRATION.md` | ✅ 41 KB — tài liệu tiền đăng ký, hiếm thấy ở cấp sinh viên, **nên khoe** |
| Ảnh minh chứng | ✅ 27 ảnh chụp màn hình trong `docs/img/` theo 4 hành trình người dùng |

---

# PHẦN B — GÓI MINH CHỨNG GOOGLE DRIVE (mục 13 MẪU 3)

## B.1. Mục 13 đòi hỏi chính xác những gì

> *"Link Google Drive chứa **lịch sử câu lệnh (Prompt Log)**, ảnh minh chứng quá trình phát triển
> **từ bản nháp → hoàn thiện**, tài liệu kỹ thuật, mã nguồn. **Phải mở quyền truy cập trước khi
> nộp.**"* — `BRIEF-THE-LE.md` mục 3
>
> Vòng Khu vực bổ sung: *"**Prompt Log đầy đủ gồm System Prompt và toàn bộ conversation history**"*

## B.2. ✅ Nguyên liệu đã có sẵn trên máy

| Nguyên liệu | Có? | Ở đâu | Quy mô |
|---|---|---|---|
| Prompt Log | ✅ | `C:\Users\Admin\.claude\projects\d--AISC2026\` | **3 phiên chính · ≈3.059 lượt · ≈1.297 câu lệnh của đội** + 289 nhật ký tiến trình con · **191 MB** |
| Ảnh phát triển | ✅ Một phần | `docs/img/` | 27 ảnh, 2,5 MB — nhưng là ảnh **bản hoàn thiện**, thiếu "bản nháp" |
| Tài liệu kỹ thuật | ✅ Rất đầy đủ | `docs/` | **74 file** — 13 benchmark, 12 nghiên cứu, 6 hồ sơ thi, 4 runbook/template |
| Mã nguồn | ✅ | Repo | 322 file, 6,2 MB |
| **System Prompt** | ⚠️ Một phần | — | Xem B.3 |

**Kết luận: đội có thừa nguyên liệu.** Việc còn lại là **làm sạch và sắp xếp**, không phải tạo mới.

## B.3. ⚠️ Vấn đề "System Prompt" — nói thật, đừng bịa

Thể lệ đòi "Prompt Log đầy đủ **gồm System Prompt**". Thực tế:

- **System prompt của nhà cung cấp Claude Code KHÔNG được lưu trong nhật ký phiên** (đã kiểm: 57
  bản ghi `type: system` đều là log lỗi mạng, không phải nội dung prompt) và **đội không có quyền
  truy cập**.
- **Không có `CLAUDE.md` và không có thư mục `.claude/`** trong repo.

**⚠️ Cách xử lý — quan trọng:** **KHÔNG bịa ra một "system prompt" rồi nộp.** Đó đúng là "giả mạo
Prompt Log" mà Điều 5 §7 cấm, và là rủi ro loại đội. Thay vào đó, nộp một ghi chú trung thực:

> *System prompt của nhà cung cấp Claude Code không được lưu trong nhật ký phiên và đội không có
> quyền truy cập — chúng tôi không nộp thứ mình không có và không dựng bản thay thế. Thay vào đó,
> chỉ dẫn cấp dự án mà mọi phiên làm việc đều được trỏ vào là `HARNESS.md` (đính kèm), cùng toàn bộ
> 1.297 câu lệnh nguyên văn của đội.*

Điều này biến một thiếu sót thành **bằng chứng về tính trung thực** — đúng thứ Điều 5 §6 đo.

## B.4. Cấu trúc thư mục Drive đề xuất

Thiết kế theo nguyên tắc: **giám khảo mở là hiểu ngay, không phải đi tìm.** Mỗi thư mục có một
`README` giải thích nó chứng minh điều gì.

```
LiveLift — AISC'26 Sáng tạo trẻ Quốc gia/
│
├── 00-DOC-TRUOC.pdf                     ⭐ MỞ FILE NÀY TRƯỚC (1 trang)
│      Bản đồ gói minh chứng · link repo · 5 con số chốt ·
│      3 điều đội tự khai là hạn chế
│
├── 01-HO-SO-DU-THI/
│      ├── Tai-lieu-du-an.pdf                    (MẪU 3, ≤20 trang)
│      ├── 05-BAN-KE-KHAI.pdf                    (bản kê khai công cụ AI)
│      └── Giay-xac-nhan-sinh-vien.pdf           ← trường cấp
│
├── 02-PROMPT-LOG/                       ⭐ HẠNG MỤC BẮT BUỘC
│      ├── 00-DOC-TRUOC.md                       Cách đọc · phạm vi · điều đã lọc
│      ├── GHI-CHU-SYSTEM-PROMPT.md              ⚠️ Giải thích trung thực (B.3)
│      ├── HARNESS.md                            "System Prompt" cấp dự án
│      ├── BAO-CAO-LAM-SACH.md                   Đã thay gì, bao nhiêu lần
│      ├── phien--feb901dc.md                    24/08→03/09 · 584 câu lệnh
│      ├── phien--3c773cb8.md                    06/09→14/09 · 680 câu lệnh
│      ├── phien--3b0c8ccf.md                    14/09 · 33 câu lệnh
│      └── tien-trinh-con/                       289 nhật ký subagent (tuỳ chọn)
│
├── 03-MINH-CHUNG-PHAT-TRIEN/            ⭐ "bản nháp → hoàn thiện"
│      ├── 00-DOC-TRUOC.md
│      ├── a-lich-su-commit/
│      │     ├── git-log-day-du.txt              git log --stat, 42 commit
│      │     ├── git-log-mot-dong.txt            42 dòng, đọc 1 phút
│      │     └── dong-tac-gia-AI.txt             Chứng minh 42/42 khai báo AI
│      ├── b-anh-man-hinh/
│      │     ├── 01-ban-nhap/                    ⚠️ CẦN DỰNG — xem B.6
│      │     └── 02-ban-hoan-thien/              27 ảnh từ docs/img/
│      ├── c-so-su-co/
│      │     ├── incident-log.md                 41 sự cố: root cause + gate
│      │     └── audit_findings.txt              16 phát hiện kiểm toán đối kháng
│      └── d-tien-hoa-tai-lieu/
│            └── FACT-SHEET.md                   Bộ số chuẩn duy nhất
│
├── 04-TAI-LIEU-KY-THUAT/
│      ├── README.pdf · HARNESS.pdf · PREREGISTRATION.pdf
│      ├── benchmarks/                           13 file — SỐ ĐO
│      ├── research/                             12 file — sổ nghiên cứu
│      └── ops/                                  Runbook vận hành phiên
│
├── 05-MA-NGUON/
│      ├── LINK-REPO.txt                         ⭐ URL GitHub (PHẢI public)
│      └── livelift-dd66b38.zip                  Bản đóng băng, phòng repo lỗi
│
└── 06-VIDEO/
       ├── Video-thuyet-trinh.mp4                ≤5 phút
       └── Video-demo.mp4                        ≤5 phút
```

**Quyền chia sẻ:** đặt ở thư mục gốc — *"Bất kỳ ai có đường liên kết" → **Người xem***.
Đừng đặt "Người chỉnh sửa" (ai cũng xoá được) và đừng đặt quyền theo từng file (sót một file là
giám khảo gặp "Yêu cầu quyền truy cập").
**Kiểm chứng bắt buộc:** mở link bằng **cửa sổ ẩn danh, không đăng nhập Google** — đây là cách
duy nhất biết chắc quyền đã mở.

## B.5. ✅ Script xuất Prompt Log — đã viết và đã chạy thử

`scripts/xuat_prompt_log.py` — chuyển nhật ký JSONL thô thành Markdown đọc được, **có làm sạch**.

```bash
# Xem trước: đếm số lần thay thế, KHÔNG ghi file
python scripts/xuat_prompt_log.py --kiem-tra

# Xuất thật
python scripts/xuat_prompt_log.py --ra D:/AISC2026/prompt-log-cong-bo

# Kèm 289 nhật ký tiến trình con (dung lượng lớn)
python scripts/xuat_prompt_log.py --ra <thư-mục> --kem-subagent
```

**Nó lọc gì:**

| Nhóm | Bắt gì |
|---|---|
| Bí mật | Google API key · token Facebook · khoá OpenAI/Anthropic · GitHub PAT · AWS · khoá PEM · giá trị của 11 biến môi trường nhạy cảm (giữ tên biến, xoá giá trị) |
| Dữ liệu cá nhân đội | Danh sách chặn tường minh: 3 email thành viên, SĐT đội trưởng, 3 MSSV |
| Dữ liệu cá nhân người xem | **Handle MXH có dấu tiếng Việt + dấu gạch ngang** (bản đã sửa lỗi ASCII-only) · email · SĐT VN · số tài khoản |

**Kết quả chạy thử 14/09/2026** (3 phiên chính, 3.059 lượt):

| Loại | Số lần thay |
|---|---:|
| Handle mạng xã hội | 92 |
| MSSV | 21 |
| Email | 40 (18 + 22 theo danh sách chặn) |
| Giá trị biến môi trường | 17 |
| Số điện thoại | 15 (9 + 6 theo danh sách chặn) |
| **Tổng** | **185** |

**Script còn làm:** bỏ khối suy luận nội bộ của mô hình (không thuộc Prompt Log), cắt kết quả công
cụ còn 800 ký tự (để file đọc được), **giữ NGUYÊN VĂN mọi câu lệnh của đội**, sinh
`BAO-CAO-LAM-SACH.md` liệt kê đã thay gì + **ghi rõ giới hạn** (regex không phải NER).

> ⚠️ **Script không thay thế người đọc.** Bộ lọc thiên về recall nhưng tên người viết thường không
> có tiền tố (`"chào chị hương"`) vẫn có thể lọt. **Bắt buộc đọc lại tay** vài file bất kỳ — nhất
> là các file `subagent--*` — trước khi tải lên.

## B.6. ⚠️ Thiếu hụt duy nhất: ảnh "bản nháp"

Mục 13 đòi ảnh minh chứng **"từ bản nháp → hoàn thiện"**. `docs/img/` có 27 ảnh nhưng **toàn ảnh
bản hoàn thiện** — không có ảnh giao diện thời kỳ đầu.

**Tin tốt: có thể dựng lại thật, không cần bịa.** Lịch sử git đầy đủ ⇒ checkout lại commit cũ,
chạy, chụp màn hình:

```bash
git checkout b4aa594   # 25/08 — web bản trung control đầu tiên
cd web && npm ci && npm run dev     # chụp màn hình
git checkout 8d65e8e   # 01/09 — trước khi nâng chuẩn UI
git checkout 14e93ac   # 12/09 — sau thiết kế lại toàn diện
git checkout main      # QUAY VỀ
```

Ba mốc này minh hoạ đúng "nháp → hoàn thiện", và **là ảnh thật của mã thật**, không dàn dựng.

⚠️ Nhớ `git checkout main` khi xong. ⚠️ Ảnh chụp phải là **dữ liệu DEMO**, không phải dữ liệu phiên
thật — dùng `python scripts/seed_demo_vang.py`.

---

# PHẦN C — DANH SÁCH VIỆC CON NGƯỜI PHẢI TỰ LÀM

Những việc dưới đây **không agent nào làm thay được** — cần tài khoản, chữ ký, hoặc quyết định của đội.

## C.1. ⛔ Chặn nộp — làm trước

| # | Việc | Ai | Thời lượng |
|---|---|---|---|
| 1 | **Chuyển repo GitHub sang Public** (Settings → General → Danger Zone). Kiểm bằng **cửa sổ ẩn danh** | Đội trưởng | 2 phút |
| 2 | **Chạy lại bộ lọc PII trên dữ liệu đã lưu** sau khi mã được sửa, xác nhận 0 handle còn sót | Đội | 30 phút |
| 3 | **Sửa câu mâu thuẫn về yt-dlp** trong thuyết minh — dùng lời văn ở A.7 | Đội | 30 phút |
| 4 | **Xuất Prompt Log + ĐỌC LẠI TAY** rồi tải lên Drive | Đội | 2 giờ |
| 5 | **Mở quyền Drive** → "Bất kỳ ai có link · Người xem", kiểm bằng cửa sổ ẩn danh | Đội trưởng | 5 phút |
| 6 | **Xin Giấy xác nhận sinh viên** từ ĐH Tôn Đức Thắng | Cả 3 thành viên | 1–3 ngày ⚠️ |
| 7 | **Ký tên** vào bản kê khai và tài liệu dự án (bản in/scan) | Đội trưởng | 10 phút |

## C.2. ⚠️ Quyết định đội phải tự chốt (tôi không quyết thay)

| # | Quyết định | Khuyến nghị của tôi |
|---|---|---|
| 1 | **Đổi tên repo** `AISC2026_LIVEFIT` → `livelift`? | **Nên** — rủi ro thấp (GitHub tự chuyển hướng), chỉ sửa 3 dòng. Hết giờ thì giữ nguyên + ghi chú minh bạch trong README |
| 2 | **Có upload 289 nhật ký tiến trình con không?** (191 MB) | **Nên upload** — thể lệ đòi "toàn bộ conversation history". Thiếu thì giải thích rõ lý do trong `00-DOC-TRUOC.md`. Nếu upload: **2 file có handle thật, phải lọc kỹ** |
| 3 | **Xin `YOUTUBE_API_KEY` ngay?** | **Nên** — miễn phí, ~10 phút, không cần app review. Có key ⇒ tuyên bố được "đường chính thức đã sẵn sàng", làm nhẹ hẳn vấn đề yt-dlp |
| 4 | **Liên hệ tác giả KuaiLive xác minh giấy phép?** | **Nên gửi 1 email** — giấy phép đang mâu thuẫn CC BY-NC-SA vs CC BY. Có thư trả lời là bằng chứng cầu thị; chưa có thì giữ phương án thận trọng (coi là NC) |
| 5 | **Viết mục "phân công theo thành viên"?** | **Nên** — 42/42 commit một danh tính là điểm giám khảo chắc chắn hỏi |
| 6 | **Đường tự do (20/9) hay trường cử (30/9)?** | **Trường cử** — bỏ qua hẳn một vòng loại + thêm 10 ngày. Nhưng đòi Giấy xác nhận SV ⇒ **việc C.1 #6 phải khởi động hôm nay** |

## C.3. Nên làm nếu còn thời gian (P1/P2)

| # | Việc | Lợi ích |
|---|---|---|
| 1 | Sửa README theo bảng A.8 (ưu tiên #2 fail-khởi-động; #3 chỉ cần nói đúng mức mất tối đa ~30 giây của chế độ memory — *đính chính 17/09/2026: bản 14/09 ghi "ưu tiên #3 mất-dữ-liệu"*) | Người lạ chạy được thật trong 10 phút |
| 2 | Dựng ảnh "bản nháp" theo B.6 (3 mốc commit) | Đáp đúng chữ "bản nháp → hoàn thiện" của mục 13 |
| 3 | Bổ sung tên 3 thành viên vào `CITATION.cff` | Ghi nhận tác giả đầy đủ |
| 4 | Bổ sung dẫn nguồn cho `admin_units.py` | Đóng nốt lỗ hổng dẫn nguồn cuối cùng |
| 5 | Gỡ `underthesea` khỏi `pyproject.toml` (khai báo thừa, không dùng) | Bản kê khai khớp 100% với mã |
| 6 | Tạo `docs/DAO-DUC-VA-DU-LIEU.md` gom nội dung pháp lý đang rải rác | Trọng tâm đánh giá #8 (an toàn, đạo đức AI) |

---

## Phụ lục — lệnh kiểm chứng lại mọi khẳng định trong tài liệu này

```bash
# Quyền repo (chạy ở nơi KHÔNG có credential GitHub)
curl -s -o /dev/null -w "%{http_code}\n" https://api.github.com/repos/bminhnemhoi/AISC2026_LIVEFIT
# 404 = private · 200 = public

# Quét bí mật trong toàn bộ lịch sử
git log --all -p | grep -inE "AIza[0-9A-Za-z_-]{20,}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|BEGIN .*PRIVATE KEY"

# Khai báo đồng tác giả AI (phải ra 42)
git log --format="%b" | grep -ci "co-authored-by: claude"

# Lịch sử commit thật
git log --format="%ad" --date=short | sort | uniq -c

# Handle MXH còn sót trong dữ liệu đã lưu (phải ra 0 sau khi sửa)
python -c "import json,re; rows=[json.loads(l) for l in open('data/labeling/lot1-achan-b519f75c/comments_b519f75c.jsonl',encoding='utf-8')]; h=re.compile(r'@[\wÀ-ỹ][\wÀ-ỹ.\-]{2,}'); print(sum(len(h.findall(r['text_scrubbed'])) for r in rows))"

# Prompt Log — xem trước, không ghi file
python scripts/xuat_prompt_log.py --kiem-tra

# Bộ test
pytest -m "not slow" -q
```
