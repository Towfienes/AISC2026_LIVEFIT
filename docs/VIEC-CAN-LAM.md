# Việc cần làm — trạng thái ngày 25/09/2026

*Viết cho đội LiveLift (Minh, Khánh, Tiến). Người phụ trách theo làn trong
`docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md`. Mỗi việc có tiêu chí "xong khi" để không ai
phải đoán. Kết quả chi tiết của đợt kiểm toán nằm ở
`docs/research/2026-09-17-danh-gia-toan-dien-va-lo-trinh-tu-dong.md`.*

*Cập nhật 25/09/2026: thêm lịch AISC'26 vòng 2 và mục "Trạng thái 25/09" (việc đã xong trên nhánh
review, việc chỉ con người làm được, quyết định cần chốt). Các bảng P0/P1/P2 bên dưới giữ từ
18/09, có ghi chú **25/09** ở những việc đã đổi trạng thái. Sự cố và nguyên nhân gốc: `docs/incident-log.md`.*

## Mốc thời gian

| Mốc | Ngày |
|---|---|
| Nộp hồ sơ Sáng tạo trẻ AI (Bảng C, trường cử) | **30/09/2026** |
| Vòng Khu vực — hackathon 2 ngày, 60% điểm | **10–11/10/2026** |
| **AISC'26 vòng 2** — thuyết trình tại UIT, 08:00–16:30; mỗi đội 2 phút chuẩn bị + 15 phút gồm cả hỏi đáp; **poster + mockup giao diện bắt buộc** (thiếu poster thì mất quyền vào vòng 3 và chung kết) | **15/10/2026** |
| Chung kết Sáng tạo trẻ — cải tiến 12 giờ, sản phẩm chạy ổn định ≥ 48 giờ | **20–22/11/2026** |

> **AISC'26 vòng 2 là 15/10/2026 tại UIT** (trang chính thức của BTC, tải về 25/09/2026; kết quả vào
> vòng 2 công bố 25/09). Kế hoạch nội bộ cũ (ngoài kho) ghi "vòng 2 trong 16–30/09" — **sai**. Việc
> AISC (slide, poster, mockup, video demo dự phòng, trang đính chính số cũ của bản vòng 1) xếp sau
> 30/09 và chốt trước 09/10, vì 10–11/10 là hackathon. Chung kết AISC đòi demo có kết nối cơ sở dữ
> liệu — cần Postgres thật và `/health` báo `durable: true` (việc 8).

## Hiện trạng một đoạn

**Ngày 18/09:** sản phẩm đã có bộ thu bình luận chạy nền (bật bằng nút), nguồn Mô phỏng để kiểm thử, nhập đơn hàng
CSV, giao diện v3 đã sửa các lỗi P0/P1, và 1.555 test nhanh + 17 cổng Monte-Carlo + 10 test trình duyệt
đều xanh. **Điểm yếu lớn nhất không nằm ở mã:** chưa có khoá API thật nào, chưa có buổi live thật nào
đi qua đường chính thức, và vẫn **0 phiên thí nghiệm ngẫu nhiên thật**.

**Ngày 25/09:** kiểm toán thử thật trên `main` 390027b tìm ra các lỗi ghi ở sổ sự cố ngày 25/09
(trang kết quả sập khi thiếu KTC, `/health` khai sai bộ phân loại, nhìn trộm kết quả giữa phiên,
phiên chạy thử hiện như phiên thật, 57 tên tài khoản còn trong dữ liệu gán nhãn, bộ xuất Prompt Log
đếm sai 1.297 câu lệnh…). Các bản sửa nằm trên nhánh review, chưa merge. Vẫn **0 phiên thí nghiệm
ngẫu nhiên thật**, chưa có khoá API thật, chưa có nhãn người.

---

## Trạng thái 25/09/2026

### Đã xong trên nhánh review `hoan-thien/ho-so-2509` — chờ trưởng nhóm review và merge

Sáu commit trên `main` 390027b. Chưa merge, nên `main` và kho công khai vẫn là bản cũ.

| Commit | Nội dung |
|---|---|
| `ba96b73` | API: ghim `scikit-learn==1.9.0`, `/health` nói thật khi mô hình hỏng hoặc đang nạp; khoá kết quả khi phiên chưa kết thúc (chống nhìn trộm, PREREGISTRATION §7); phiên chạy thử có số đếm riêng; Docker (thư mục data ghi được, volume, `.dockerignore`), Caddy (header bảo mật cả ở trang lỗi), `pytest -m db` chọn đúng test |
| `83050d5` | NLP: lọc lại PII dữ liệu gán nhãn (57 → 0 tên tài khoản); mã sinh báo cáo ghi đúng nguồn nhãn (tác tử AI); đo lại C2 = **0,542 [0,478; 0,625]** (số 14/09 là 0,565, đo trước khi lọc); thêm recall nhãn hành động; bảng gán mù cho 2 người (seed bí mật) và script κ |
| `3a2b489` | Web: `/ket-qua` không còn sập khi thiếu KTC; tách phiên chạy thử; con dấu dữ liệu mẫu; số thập phân kiểu vi-VN; đồng bộ README, FACT-SHEET, kịch bản demo |
| `2569555` | Bộ xuất Prompt Log viết lại (đếm lại: **78 câu lệnh người gõ trong 5 phiên**, thay số 1.297 sai); bản kê khai AI viết lại; bộ dựng gói Drive |
| `d10baec` | 5 hình hồ sơ sinh từ mã: switchback, kiến trúc, A/A, MDE, hiệu ứng lưu |
| `94d29aa` | Hồ sơ Bảng C: bộ dựng an toàn (không ghi đè bản nộp, đọc lại XML sau khi dựng), `noi-dung.md` viết lại theo mã, kịch bản 2 video |
| chưa commit (V1) | Đóng gói lại mô hình v2 trên dữ liệu đã lọc (bỏ token sinh từ tên tài khoản) + cổng quét từ vựng artifact; bỏ tên thật trong ví dụ của `labels.py`; loại phiên đã huỷ khỏi số đếm "thật"; không đóng dấu "TÁC ĐỘNG THẬT" trên phiên chạy thử |
| chưa commit (V2) | Sổ sự cố thêm 39 dòng ngày 25/09 (tổng 99); đồng bộ số cũ trong tài liệu (hiệu ứng lưu, MDE, số 0,271 không tái lập được, số 1.297 câu lệnh sai, nguồn nhãn) |

Sau khi merge: chạy `pytest -m "not slow"` tới khi xanh, rồi `scripts/dong_bo_so_test.py --ghi`
(số test trong README, trang chủ, FACT-SHEET, hồ sơ đang là số THU THẬP, chưa ai chạy xanh cả bộ trên
nhánh); đếm lại sổ sự cố cho `noi-dung.md`, `05-BAN-KE-KHAI.md`, `07-KICH-BAN-2-VIDEO.md` (đang ghi
60); dựng lại hồ sơ bằng `dung_ho_so.py` không cờ nháp để Word đếm trang lần cuối.

### Việc chỉ con người làm được — trước 30/09

| # | Việc | Ai | Xong khi |
|---|---|---|---|
| N1 | **Review và merge nhánh `hoan-thien/ho-so-2509`**. Không lấy gì từ `tien/aisc-round2` khi PR #1 chưa được duyệt | Minh | `main` chứa các commit; bộ test nhanh xanh trên `main` |
| N2 | **Giấy xác nhận sinh viên** cho cả 3 | Cả 3 | Có bản scan 3 giấy |
| N3 | **Điền thông tin thí sinh** trong `docs/competition/thong-tin-doi.local.json` (ngoài git): xã/phường ×3, SĐT ×2, lớp hành chính ×3 | Cả 3 | `dung_ho_so.py` không còn báo ô ⬜ |
| N4 | **Quay 2 video** (thuyết trình ≤ 5 phút, demo ≤ 5 phút) theo `docs/competition/sang-tao-tre-2026/07-KICH-BAN-2-VIDEO.md`; cả 3 phải xuất hiện. Chỉ quay `/ket-qua?phien=` sau khi bản vá lỗi sập đã vào `main` | Cả 3 | Hai tệp video, mỗi tệp ≤ 5 phút |
| N5 | **Gán mù 393 dòng** — đề xuất Khánh bảng 1, Tiến bảng 2 (trưởng nhóm quyết). Băm các bảng đã commit ở `83050d5`; phát `bang-nguoi-gan-*.csv` + `huong-dan-gan-nhan.md` từ `D:/AISC2026/gan-mu-2509/`, **không** phát thư mục `khoa/`; người gán không mở `results.*`. Hiện CHƯA có nhãn người nào — κ 0,934 trong báo cáo làn NLP chỉ là kiểm đường ống bằng nhãn giả, không trích | Khánh + Tiến | Băm nhãn đăng trước khi chấm; `scripts/tinh_kappa.py --cham-lai` chạy xong; `kappa.json` công bố dù số tăng hay giảm |
| N6 | **Nhật ký Google Antigravity và OpenAI Codex (21/09)** xuất vào `01-Prompt-Log/ngoai-claude-code/` (hoặc ghi lý do vào `GHI-CHU.md`) | Tiến | `xuat_prompt_log.py --quet` ra 0 |
| N7 | **Tải gói Drive và mở quyền.** Ngay trước khi tải: chạy lại `scripts/xuat_prompt_log.py` (phiên đang chạy còn ghi thêm), `ke_khai/dung_ke_khai.py`, `ke_khai/dung_goi_drive.py`; đọc lại Prompt Log bằng mắt; làm theo `HUONG-DAN-TAI-LEN.md` trong gói; mở quyền "Bất kỳ ai có đường liên kết · Người xem"; dán link vào mục 13 hồ sơ | Minh | Link mở được từ cửa sổ ẩn danh; link đã nằm trong PDF |
| N8 | **Ký**: ba người điền cột tự khai của bản kê khai AI (công cụ AI khác; nguồn gốc 2 tệp ý tưởng có trước phiên Claude đầu tiên 24/08) rồi ký → `05-Ban-ke-khai/AI2026_Ban_Ke_Khai_LiveLift_da-ky.pdf`; ký các chỗ ký của hồ sơ | Cả 3 | Bản scan đã ký |
| N9 | **Nộp** tại ai.tainangviet.vn: PDF ≤ 20 trang, 2 video, link kho mã, bản kê khai, giấy xác nhận SV, link Drive | Minh | Có biên nhận trước 30/09 — không để sát giờ |
| N10 | **Khoá API** YouTube và Facebook (việc 1, 2) | Khánh | Như việc 1, 2 |
| N11 | **Gỡ khoá thanh toán GitHub** để Actions chạy (việc 11) | Minh | Badge CI xanh từ một lần chạy thật |
| N12 | **Đặt `cleanupPeriodDays`** trong cài đặt Claude Code (việc 14). Đã sao lưu mới ngày 25/09 (`D:/AISC2026/prompt-log-goc/2026-09-25`, 1.648 tệp, có manifest); phiên đầu tiên (24/08) hết hạn mặc định quanh 04/10 | Minh | Cài đặt có khoá này |

**Chặn bản nộp:** hồ sơ tham chiếu `hinh/h6-nlp.png` (Hình 5) và `hinh/h7-giao-dien.png` (Hình 7);
`dung_ho_so.py` chặn bản nộp tới khi đủ hình. Ngày 25/09: h6 đang được làm trên nhánh (sinh từ
`chi-tiet-hinh.json`, chưa commit); h7 chưa có và chưa ai nhận. Hình 7 là ảnh chụp giao diện nên không được có dữ liệu cá nhân. Bản dựng thử với
ảnh giữ chỗ còn khoảng 10% trống ở trang 20 — hình thật cao hơn thì phải thu nhỏ để giữ ≤ 20 trang.

### Quyết định trưởng nhóm cần chốt trước khi nộp

1. **Đồng ý của người bình luận.** Hồ sơ (mục 3.3) tự khai 19.126 bình luận được xử lý khi chưa có sự
   đồng ý của người bình luận; Thể lệ Điều 5 khoản 7–8 cấm xử lý dữ liệu cá nhân khi chưa có đồng ý hợp
   lệ — có nguy cơ bị loại. Phương án: xoá tập 16 buổi trước ngày nộp và ghi đã xoá, hoặc nhờ người hiểu
   luật duyệt. Câu cam kết thời hạn xoá ("chậm nhất 22/11/2026", đánh dấu `<!-- DUYỆT -->`) do tác tử
   soạn — chủ dự án duyệt hoặc đổi ngày.
2. **Mục 11.2 của hồ sơ** tự xếp mức rủi ro thấp vì "không quyết định thay con người", mâu thuẫn với chế
   độ "Tự ghim" mặc định. Nhờ người hiểu luật đọc cùng NĐ 142/2026 Điều 9 khoản 3.
3. **`GET /sessions/{id}/report`** vẫn trả chênh lệch trung bình khi kết quả đang khoá: khoá lại, hay ghi
   rõ là đường nội bộ. Vá xong thì sửa hộp CỔNG 3 của hình 2 (`ve_hinh_ho_so.py --chi h2`, cần Pillow) và
   câu ở mục 5.3, 10 của hồ sơ.
4. **Lịch sử git công khai** còn artifact v2 cũ mang token sinh từ tên tài khoản: viết lại lịch sử hay
   không.
5. **Bản sao lưu `D:/AISC2026/backup-labeling-2509/`** còn nguyên 57 tên tài khoản: xoá sau khi duyệt
   xong; cân nhắc xoá luôn `comments_b519f75c.jsonl` (6.586 dòng, khung đánh giá không đọc).
6. **PREREGISTRATION.md** dòng 311–313 còn ô `<YYYY-MM-DD>`, `<n>` — quyết định phương pháp của đội
   (việc 22), tác tử không điền.

---


## P0 — làm ngay, xong trước 21/09

| # | Việc | Ai | Làm thế nào | Xong khi |
|---|---|---|---|---|
| 1 | Lấy **YouTube API key** | Khánh | `docs/HUONG-DAN-LAY-KHOA-API.md` mục 2 | Trang Bắt đầu ghi YouTube **Sẵn sàng** |
| 2 | Lấy **Facebook Page token** cho Fanpage của nhóm | Khánh | `docs/HUONG-DAN-LAY-KHOA-API.md` mục 3 | `scripts/kiem_tra_facebook.py` ra `KẾT LUẬN: SẴN SÀNG` |
| 3 | Xác minh kênh YouTube phát live, kiểm tra Fanpage đủ điều kiện phát | Tiến | Mục 2.5 và 3.4 của hướng dẫn trên | Bấm được "Phát trực tiếp" trên cả hai |
| 4 | **Buổi phát thử 30 phút** trên YouTube và Fanpage | Cả đội | Mục 7 của hướng dẫn trên | Thu ≥ 98% bình luận kịch bản, SĐT giả hiện `[SĐT]`, đã ghi hạn mức; nhật ký lưu theo `ops/templates/nhat-ky-phien.md` |
| 5 | **Quyết định về các đường không chính thức cũ** (xem mục "Quyết định cần chốt") | Minh | Họp 15 phút | Ghi quyết định vào `docs/incident-log.md` hoặc tài liệu này |

## P1 — trước khi nộp hồ sơ 30/09

| # | Việc | Ai | Làm thế nào | Xong khi |
|---|---|---|---|---|
| 6 | **Đồng bộ số liệu trong hồ sơ** — `noi-dung.md` §7.3 còn ghi 1.174 test và 47 sự cố | Minh | Sửa thành 1.555 test nhanh + 17 cổng Monte-Carlo + 10 test trình duyệt, 58 sự cố; thêm bộ thu nền, nhập đơn CSV, kết quả buổi phát thử; chạy `scripts/dong_bo_so_test.py --xem-truoc` và `scripts/do_lai_so_hieu_chuan.py --kiem`; dựng lại bằng `.venv-docx/Scripts/python docs/competition/sang-tao-tre-2026/dung_ho_so.py`. **25/09:** việc này đổi — `noi-dung.md` đã viết lại (`94d29aa`); sau khi merge dùng số do `dong_bo_so_test.py --ghi` sinh ra thay cho các số ở trên; sổ sự cố nay có 99 hàng | PDF ≤ 20 trang, không còn ô ⬜, số khớp README |
| 7 | **Chụp lại ảnh** trong `docs/HUONG-DAN-SU-DUNG.md` — ảnh hiện là giao diện 11/09 | Tiến | Chạy local, chụp lại các bước có thay đổi (trang chủ, wizard bước 2–4, Bàn trợ live, màn người dẫn, phát lại, báo cáo) | Không còn ảnh cũ mâu thuẫn chữ hướng dẫn |
| 8 | **Chạy thật `docker compose up` trọn ngăn xếp** (có `web` + `caddy`) với Postgres | Tiến + Minh | `docs/luu-tru-du-lieu.md`, `docs/competition/sang-tao-tre-2026/04-TRIEN-KHAI.md` (đọc hộp đính chính 25/09). Cho Docker Desktop đủ RAM trước — ngày 25/09 nó chết vì hết bộ nhớ, không phải vì thiếu quyền quản trị. Sửa `.env` cục bộ: `NEXT_PUBLIC_API_URL=http://localhost/api`. Sau đó chạy `DATABASE_URL=postgresql://…@127.0.0.1:5432/livelift pytest -m db tests/test_store_contract.py` (từ 25/09 tham số postgres mang dấu `db`; thiếu `DATABASE_URL` thì lệnh chọn **0 test**, mã thoát 5 — đó KHÔNG phải xanh) | `/health` báo `durable: true` và `intent_backend: tfidf_logreg`; lệnh `pytest -m db` chạy > 0 test và xanh trên Postgres |
| 9 | **Địa chỉ công khai HTTPS** cho link đo | Tiến | `04-TRIEN-KHAI.md` §4 (Oracle Cloud Free hoặc VPS theo giờ, tên miền `.id.vn`) | Điện thoại ngoài mạng nhà bấm được `https://<tên-miền>/r/<mã>` |
| 10 | **Giao diện web gửi được token** — bản công khai đặt `INGEST_TOKEN` thì nút bật bộ thu và nhập đơn đang bị từ chối | Minh + Tiến | Tối thiểu: ô nhập mã người vận hành lưu trong phiên trình duyệt, gắn header `Authorization` cho các lệnh ghi | Bản công khai khoá được đường ghi mà người vận hành vẫn dùng đủ nút |
| 11 | **Bật lại GitHub Actions** — CI chưa từng chạy được bước nào | Minh | Kiểm tra thanh toán/giới hạn ở Settings → Billing của tài khoản GitHub. Lưu ý: trước bản ghim `scikit-learn==1.9.0` (25/09) CI dù chạy được cũng đỏ 5 test NLP vì cài 1.7.2 | Badge CI xanh từ một lần chạy thật |
| 12 | **Lọc lại dữ liệu gán nhãn** bằng bộ lọc handle mới rồi đo lại mô hình ý định | Khánh | `python -m livelift.nlp.eval_intent` sau khi lọc `data/labeling/`. **25/09: xong trên nhánh review** (`83050d5`): 57 → 0 tên tài khoản, C2 = 0,542 [0,478; 0,625]; còn đóng gói lại v2 (V1, đang làm) | Sự cố 15/09 về handle có dấu chuyển sang ĐÓNG |
| 13 | **Hai người gán nhãn lại tập kiểm tra**, đo độ đồng thuận κ | Khánh + Tiến | Bảng xáo trộn, gán mù, không mở `results.json` trước. **25/09:** bảng đã sinh với seed bí mật, băm commit ở `83050d5` — xem N5 | Có số κ người–người thay cho nhãn do tác tử AI gán |
| 14 | **Giữ transcript làm Prompt Log** — Claude Code tự xoá sau 30 ngày | Khánh | Đặt `cleanupPeriodDays` trong cài đặt Claude Code; sao lưu thư mục transcript. **25/09:** đã sao lưu mới, `cleanupPeriodDays` VẪN chưa đặt — xem N12 | Transcript từ 24/08 vẫn còn đủ |
| 15 | **Phiên thí nghiệm thật đầu tiên có khán giả** (nếu có shop đối tác đồng ý) | Cả đội | Tầng 3 trong tài liệu đánh giá mục 4; lịch gán sinh và niêm phong trước giờ phát | Có ≥ 1 phiên đủ điều kiện vào mẫu phân tích; nếu không kịp thì hồ sơ nói thẳng 0 phiên |

## P0b — việc mới từ đợt nghiên cứu 18/09 (TikTok, YouTube, thị trường)

*Nguồn: `docs/research/2026-09-17-tiktok-duong-chinh-thuc.md`,
`docs/research/2026-09-17-youtube-kiem-thu-chinh-thuc.md`,
`docs/research/2026-09-17-thi-truong-trung-quoc-an-do-va-bai-bao-moi.md`.*

| # | Việc | Ai | Làm thế nào | Xong khi |
|---|---|---|---|---|
| 24 | **Chạy `scripts/kiem_tra_youtube.py` ngay sau khi có API key** (việc 1) | Khánh | `.venv\Scripts\python scripts\kiem_tra_youtube.py --video <link buổi live>` | In `SẴN SÀNG`; ghi lại giá quota thật của `liveChatMessages.list` (1 hay 5 đơn vị) vào `docs/research/2026-09-17-youtube-kiem-thu-chinh-thuc.md` |
| 25 | **Tắt Dual stream khi phát thử YouTube** | Tiến | Trong YouTube Studio, chọn phát ngang, không bật luồng dọc | Link đo trong chat bấm được ở mọi thiết bị; ghi kết quả vào nhật ký phiên |
| 26 | **Đo lại hai câu hỏi còn mở của YouTube khi có key**: video Không công khai có đọc được chat không, buổi Sắp phát có `activeLiveChatId` trước giờ không | Khánh | Chạy công cụ kiểm tra với hai loại video | Ghi câu trả lời có bằng chứng vào tài liệu YouTube |
| 27 | **Xin Account Manager cho shop TikTok Shop** (điều kiện bắt buộc để đăng ký seller developer) | Minh | Gửi ticket "Account Manager eligibility review" ở Help Center của Seller Center | Có phản hồi bằng văn bản; nếu bị từ chối thì ghi vào tài liệu và chuyển sang đường xuất CSV |
| 28 | **Đọc điều khoản TikTok Shop trước khi dựa vào dữ liệu API cho hồ sơ** | Minh | Mục 8 của tài liệu TikTok: điều 2.7(g) cấm dùng dữ liệu người dùng cuối "for your own purposes", mục 4 coi dữ liệu là thông tin mật của TikTok | Quyết định ghi rõ: dùng API cho vận hành, còn số liệu công bố lấy từ tệp shop tự xuất, hoặc xin văn bản cho phép |
| 29 | **Tạo shop thử TikTok Shop (sandbox, có Việt Nam)** để chạy `scripts/kiem_tra_tiktok_shop.py` | Khánh | Partner Center → test shop; lưu ý shop thử có thể không có dữ liệu LIVE | Script chạy tới bước gọi API thật, dù dữ liệu rỗng |
| 30 | **Đưa các phương pháp đã chọn từ Trung Quốc vào hồ sơ và sản phẩm** | Minh | Bảng "phương pháp → áp dụng" trong tài liệu thị trường: ưu tiên chuẩn hoá theo người-xem-giây, phân tách theo nguồn lưu lượng, cảnh báo ngưỡng theo phút | Hồ sơ nêu được ít nhất 2 phương pháp có dẫn nguồn quốc tế |

## P2 — sau 30/09, cho hackathon và chung kết

| # | Việc | Ghi chú |
|---|---|---|
| 16 | Đăng ký **Shopee Open Platform** và gọi thật lần đầu | Chốt vùng Việt Nam; `HUONG-DAN-LAY-KHOA-API.md` mục 4 |
| 17 | Nối `update_show_item` của Shopee vào bộ thực thi tự động, tự làm mới token 4 giờ | Shopee là nền tảng duy nhất ghim được qua API |
| 18 | Bộ nối **TikTok Shop** hậu kiểm số liệu LIVE theo phút | Mục 5 của hướng dẫn khoá |
| 19 | Tự phát hiện buổi live bắt đầu: webhook Facebook `live_videos`, RSS + `videos.list` của YouTube; chuyển YouTube sang `liveChatMessages.streamList` | Giảm hạn mức, bớt thao tác tay |
| 20 | **Đăng nhập và tách dữ liệu theo người bán**; kết nối nền tảng bằng OAuth thay cho `.env` | ~2–3 tuần-người; điều kiện để nhiều người bán dùng chung |
| 21 | Khoá tư vấn Postgres để bộ thu và bộ thực thi chạy an toàn với nhiều worker | Hiện chỉ an toàn một tiến trình |
| 22 | Khoá **PREREGISTRATION.md** sau 5 phiên thăm dò, chốt độ dài khối | Điều kiện để công bố kết luận nhân quả |
| 23 | Bộ đồ nghề hackathon + diễn tập 8 giờ trên dữ liệu thô | Vòng Khu vực chiếm 60% điểm |
| 31 | Nối bộ nối TikTok Shop vào báo cáo phiên (đối chiếu GMV/đơn theo khối) | `src/livelift/ingest/tiktok_shop.py` đã có `gop_theo_khoi`; cần đường ghi và nhãn nguồn |
| 32 | Chuyển YouTube sang `liveChatMessages.streamList` (đẩy tin, ít lượt gọi hơn) | Giá quota của streamList chưa được công bố; đo sau khi có key |
| 33 | Đổi auth_code lấy token và tự làm mới token TikTok Shop | Hiện làm tay theo mục 5.2 của hướng dẫn khoá |

---

## Quyết định cần chốt

**Các đường đọc dữ liệu không chính thức còn trong kho.** Ngày 17/09/2026 đội quyết định **không** phát
triển hướng đọc bình luận kiểu người xem (lý do ở `docs/HUONG-DAN-LAY-KHOA-API.md` mục 0.1). Kho vẫn
còn ba thứ thuộc loại này, cần chốt giữ hay gỡ:

| Thành phần | Đang dùng cho | Khuyến nghị |
|---|---|---|
| `collectors/tiktok_public/` (TikTokLive + Euler Stream) | Bằng chứng phép đo 09/09: TikTok chặn 10/10 lần | Gỡ mã, giữ báo cáo đo `docs/benchmarks/tiktok-collector-2026-09.md` |
| Backend `INGEST_YOUTUBE_BACKEND=ytdlp` cho live | Dự phòng khi chưa có API key | Gỡ sau khi có YouTube API key (việc 1) |
| Phân tích VOD YouTube qua yt-dlp (`/replays/youtube`, Luồng 2 của hướng dẫn) | 19.126 bình luận live-fire, demo "phân tích buổi đã kết thúc" | Quyết định riêng: giữ thì ghi rõ là **quan sát, nguồn không chính thức** ở mọi nơi trình bày; gỡ thì phải thay số liệu trong hồ sơ |

**Chủ dự án đã chốt ngày 18/09/2026: GIỮ cả ba** cho tới khi có khoá chính thức chạy được, vì chưa chắc
xin được API TikTok. Tài liệu và giao diện phải tiếp tục ghi rõ chúng là nguồn không chính thức.

**Không làm (đã chốt):** tiện ích trình duyệt đọc bình luận, Playwright/Selenium mở trang live, WebSocket
dịch ngược, nhận dạng chữ từ màn hình, dịch vụ cào trả phí (Apify, ScrapeCreators, EnsembleData), SerpAPI
làm nguồn bình luận.
