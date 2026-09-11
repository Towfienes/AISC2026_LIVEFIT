# Nhật ký test — hệ thống đã được thử trên những gì

*Một bảng duy nhất, mỗi dòng một lần test. Cập nhật lần cuối: 11/09/2026.*

Câu trả lời một-chỗ-nhìn cho câu hỏi "LiveLift đã chạy qua dữ liệu thật nào,
ở đâu, kết quả ra sao". Chi tiết phương pháp và số liệu đầy đủ nằm ở cột cuối.
Quy ước đọc nhanh:

- **Loại test** — `hiệu chỉnh` (dữ liệu ngoài để chỉnh tham số mô phỏng),
  `cổng mô phỏng` (kiểm định thống kê trên dữ liệu sinh), `live-fire VOD`
  (buổi live ĐÃ kết thúc nạp qua `POST /replays/youtube`), `live-fire ĐANG PHÁT`
  (ingest trực tiếp), `bộ thu thập` (đường thu ngoài YouTube), `tái lập`
  (chạy lại để kiểm tính tất định).
- Mọi phiên replay đều là **quan sát** — không có gán ngẫu nhiên, không sinh
  số nhân quả nào. Hệ thống tự dán nhãn như vậy trên UI và `/signals`.

| Ngày | Nguồn / URL | Loại test | Số liệu chính | Kết quả / phát hiện | Chi tiết |
|---|---|---|---|---|---|
| 02/09 | Bộ dữ liệu KuaiLive (Kuaishou, 21 ngày) | hiệu chỉnh | 1.157.314 phòng shop · 445.575 lượt vào · 14.470 bình luận | Chỉnh `mean_stay_min` 6→10, `comment_rate` 0,25→0,02; tỷ lệ nhấp sản phẩm KHÔNG hiệu chỉnh được từ bộ này | [kuailive-calibration.md](kuailive-calibration.md) |
| 02/09 | VOD kỹ thuật (stream cờ vua, tiếng Anh) | live-fire VOD | — | Lần live-fire đầu tiên: chỉ kiểm được hành vi NGOÀI miền (pipeline không vỡ trên chat không phải mua bán) | ghi chú trong [live-fire-achan.md](live-fire-achan.md) §1 |
| 30/08 | Mô phỏng null 200 phiên | cổng mô phỏng | trước sửa: 52% dương tính giả; sau sửa: **4,5%** (9/200, p=0,872), độ phủ 95,5% | Bắt lỗi FATAL `studentized_stat` NaN → "p<0,001 trên nhiễu thuần"; cổng A/A đổi sang kiểm định nhị thức có răng | `docs/incident-log.md` 30/08 |
| 30/08 | Quét lực thống kê 4 mức tác động × 60 lặp | cổng mô phỏng | MDE báo cáo 30,1% (sai) → **20,1%** (lực 80% đo thật) | 3 lỗi công thức MDE độc lập; thêm `RANDOMIZATION_TEST_MARGIN=1,2` đo được | [order-mde.md](order-mde.md) |
| 09/09 | Lưới SBC + thế giới có ICC cấp phiên | cổng mô phỏng | ICC≈0,05: A/A và coverage vẫn XANH; ô tiêm lỗi → ĐỎ (cổng có răng) | Sửa docstring "session shock sinh ICC" (sai); thêm knob `session_click_sigma` với ánh xạ σ→ICC đo trên 400 phiên | [sim-icc-map.md](sim-icc-map.md) · [sim-validation-report.md](sim-validation-report.md) |
| 08/09 | [ZU_0QJzsR6w](https://www.youtube.com/watch?v=ZU_0QJzsR6w) — Mega Live Achan Shop Hải Phòng (tạp hoá) | live-fire VOD | **6.586** bl / 117 phút · mật độ 56,3/phút · đỉnh 144/phút | Lần đầu chấm bộ phân loại trên chat đúng miền: macro-F1 **0,271** (vs 0,870 bộ biên soạn), precision nhãn hành động **11,0%**, thua baseline `return "khac"`; PII che 588 bl đúng thiết kế → mở bộ nhãn 6→11 lớp, xuất lô 1.800 nhãn | [live-fire-achan.md](live-fire-achan.md) |
| 09/09 | [6ekwo7H_BJU](https://www.youtube.com/watch?v=6ekwo7H_BJU) — buổi live tiếng Việt **ĐANG PHÁT** (~860–1160 người xem) | live-fire ĐANG PHÁT | 104 bình luận + 7 tick người xem qua toàn tuyến thật; trễ giao tin p50 **24,1 s**, p90 37,4 s | Đường yt-dlp chạy được KHÔNG cần API key nhưng **trái ToS YouTube** (robots.txt cấm `/live_chat`) → chỉ dùng dự phòng/kiểm thử; phát hiện + sửa 2 lỗi rò chat thô khi hủy/kill cứng | [../research/2026-09-09-youtube-ytdlp-live.md](../research/2026-09-09-youtube-ytdlp-live.md) |
| 09/09 | 3jVRnXtVvps — luồng bán hàng tiếng Việt vắng khách (1 người xem) | live-fire ĐANG PHÁT | 0 bình luận / 120 s, vẫn có 4 tick người xem | Đường đi đúng với phòng chat rỗng; kiểm chứng kỹ thuật phải dùng phòng đông | cùng tài liệu trên, mục (E) |
| 09/09 | TikTok @quyenleo (Quyền Leo Daily, đang phát) | bộ thu thập | `is_live=True`, lấy được `room_id`; WebSocket bị từ chối **HTTP 400 ở 10/10 lần** → **0 bình luận** | Đường TikTok không chính thức KHÔNG dùng được hôm nay; hồ sơ thi không được phụ thuộc. Phát hiện kèm: lỗ lọt PII mã đơn bắt đầu bằng "ĐH" (chưa sửa) | [tiktok-collector-2026-09.md](tiktok-collector-2026-09.md) |
| 10/09 | [ZU_0QJzsR6w](https://www.youtube.com/watch?v=ZU_0QJzsR6w) — Achan Hải Phòng (chạy lại từ đầu) | tái lập | 6.586 bl — **đúng từng bit** sau 2 ngày, tiến trình khác | Đường tải → lọc PII → phân loại → store là tất định | [live-fire-da-nguon.md](live-fire-da-nguon.md) §3.1 |
| 10/09 | [gT0LDiBta2k](https://www.youtube.com/watch?v=gT0LDiBta2k) — Khai trương Achan Tuyên Quang (tạp hoá) | live-fire VOD | **5.492** bl / 119 phút · đỉnh 126/phút | Precision nhãn hành động (gán mù) **12,3%**, prevalence ý định thật 6,8% — model thổi phồng 3× | [live-fire-da-nguon.md](live-fire-da-nguon.md) |
| 10/09 | [1NMt8BChQrI](https://www.youtube.com/watch?v=1NMt8BChQrI) — "Vừa trả đơn vừa tâm sự" (tạp hoá) | live-fire VOD | **4.079** bl / 106 phút · PII 15,9% | Ca tệ nhất của radar: precision **1,3%** (606 nhãn hành động, ước ~2 đúng) vì chat toàn xã giao/drama — prevalence thật 0,0% | [live-fire-da-nguon.md](live-fire-da-nguon.md) §4 |
| 10/09 | [47oGShxf80A](https://www.youtube.com/watch?v=47oGShxf80A) — Live Sale quần áo giá rẻ | live-fire VOD | **1.567** bl / 349 phút | Ca tốt nhất của radar: precision **67,9%** — chat kiểu "comment mã để chốt" (prevalence thật 48%); chứng minh precision đi theo tỷ lệ nền, không phải model | [live-fire-da-nguon.md](live-fire-da-nguon.md) §4.3 |
| 10/09 | [fhv_rKUeEIc](https://www.youtube.com/watch?v=fhv_rKUeEIc) — Sâm Ngọc Linh (dược liệu) | live-fire VOD | 779 bl / 126 phút · spike **98/phút** · PII 22,2% | Bộ lọc PII phân biệt đúng giá tiền 7 chữ số vs số điện thoại; "tỷ lệ PII cao" hoá ra là spam hotline dán lặp (73 lượt bắt = 26 văn bản) | [live-fire-da-nguon.md](live-fire-da-nguon.md) §7 |
| 10/09 | [d0x0Y-aBe0g](https://www.youtube.com/watch?v=d0x0Y-aBe0g) — Nova đồ mới về (quần áo nữ) | live-fire VOD | 322 bl / 169 phút | Vào được, số liệu ổn định cùng dải với các buổi khác | [live-fire-da-nguon.md](live-fire-da-nguon.md) §2 |
| 10/09 | [MPJktS2rkzk](https://www.youtube.com/watch?v=MPJktS2rkzk) — Đấu giá đá quý | live-fire VOD | 136 bl / 54 phút · **30,9% là chuỗi số trần** (lượt trả giá) | Ca biên: abstain đẩy 40/42 số trần về `khac` (không sinh rác) nhưng hệ thống **mù với live đấu giá** — bỏ sót 31% nội dung giá trị nhất; lời chào vẫn thành `chot_don` tự tin cao | [live-fire-da-nguon.md](live-fire-da-nguon.md) §5.2 |
| 10/09 | 9 buổi thưa: XcMgd74q_LI · z1gfKtekVwk · 3eWncr8DSgk (cây cảnh) · FWILs_jLe6I · HK-s6Y0MgiQ · qXdtBPs29xA · jUMO3oUfVnE · N_53eS6mKWc + [TdLWyV3hNao](https://www.youtube.com/watch?v=TdLWyV3hNao) (0 bl / 715 phút) | live-fire VOD | mỗi buổi 0–69 bl | Mọi endpoint trả 200, không vỡ trên chat cực thưa; buổi RỖNG làm lộ **2 lỗi trung thực** (signals nhận vơ năng lực người xem; job done im lặng) — đã sửa tận gốc kèm test hồi quy | [live-fire-da-nguon.md](live-fire-da-nguon.md) §5–6 |
| 10/09 | tvagwnTvmA4 — metadata báo có `live_chat` nhưng tải về không có | live-fire VOD | job → `error` | Thông báo lỗi tiếng Việt đúng cho từng kiểu hỏng | [live-fire-da-nguon.md](live-fire-da-nguon.md) §1 |
| 10/09 | Cặp ZU_0QJzsR6w ↔ gT0LDiBta2k (cùng shop, 213 văn bản trùng khít) và cặp chạy **song song** 1NMt8BChQrI ‖ fhv_rKUeEIc | cô lập phiên | api=file từng bình luận, extra=0 missing=0, 0 va chạm `comment_id` | Không rò rỉ giữa phiên — nối tiếp lẫn chồng lấn thật sự trong thread pool; kết quả song song trùng từng bit với tuần tự | [live-fire-da-nguon.md](live-fire-da-nguon.md) §3.2–3.3 |
| 10/09 | Gán nhãn tay MÙ 393 dòng (3 buổi mới) | đo radar ý định | precision 4 buổi: **1,3% · 11,0% · 12,3% · 67,9%** · macro-F1 chat thật 0,386 · accuracy 0,785 < baseline "khac" 0,905 | KHÔNG có "độ chính xác của radar" — chỉ có độ chính xác trên một buổi cụ thể, chênh >50 lần theo tỷ lệ nền; 40% chat là xã giao (tái xác nhận trên nguồn độc lập) | [live-fire-da-nguon.md](live-fire-da-nguon.md) §4 |
| 11/09 | 5 buổi tiêu biểu nạp lại vào server mới (Achan HP · Tuyên Quang · Trả đơn · Sâm · Đấu giá) | tái lập | 17.072 bl · mọi chỉ số gộp (phân bố ý định, tự tin, PII, abstain) **khớp đúng** tài liệu 10/09 | Tái lập lần 3, tiến trình thứ 3 — phục vụ xem trực tiếp trên web (cổng 8000/3000) | bảng dưới + [live-fire-da-nguon.md](live-fire-da-nguon.md) |
| 11/09 | [L5_mvE-Hqv4](https://www.youtube.com/watch?v=L5_mvE-Hqv4) — Xả kho **trang sức, đá mỹ nghệ** | live-fire VOD | **255** bl / 138 phút · hành động 16,9% · abstain 67,8% · PII 0,8% | Ngành hàng MỚI thứ 8 đạt ≥100 bl; phân bố ý định (`hoi_gia` 23 · `chot_don` 16) cùng khuôn ~1/6 đã ghi nhận — chưa gán nhãn tay nên KHÔNG phát biểu precision | dòng này |
| 11/09 | [rPXxduKw11s](https://www.youtube.com/watch?v=rPXxduKw11s) + [M7jiumE95yc](https://www.youtube.com/watch?v=M7jiumE95yc) — LIVE SALE 9/9 đầm trung niên (2 buổi cùng shop) | live-fire VOD | 71 bl / 184 phút và 33 bl / 90 phút · `hoi_size` 7/71 (buổi duy nhất ngoài quần áo có hỏi size đáng kể) | Ngành thời trang nữ trung niên vào được; chat thưa (0,4/phút) dù live dài — KOL YouTube ngành này bán chủ yếu qua kênh khác | dòng này |
| 11/09 | [ujsE5WD2fr8](https://www.youtube.com/watch?v=ujsE5WD2fr8) — Xả kho hàng Thái, ship 20k | live-fire VOD | 61 bl / 44 phút · hành động 19,7% (`chot_don` 7 · `van_chuyen` 4) | Mật độ 1,4/phút — buổi nhỏ vận hành sạch | dòng này |
| 11/09 | 4 buổi mỏng: [8tb4w1LW6Qg](https://www.youtube.com/watch?v=8tb4w1LW6Qg) (mỹ phẩm, 2 bl) · [50bhn5QqBvU](https://www.youtube.com/watch?v=50bhn5QqBvU) (quần áo trẻ em, 24 bl) · [nKebm1Q8dGM](https://www.youtube.com/watch?v=nKebm1Q8dGM) (túi xách, 8 bl) · [i0yNvhjTocE](https://www.youtube.com/watch?v=i0yNvhjTocE) (xả kho 11,9 giờ, 9 bl) | live-fire VOD | 43 bl / 4 buổi | 3 ngành hàng MỚI vào được (mỹ phẩm, mẹ&bé, túi xách) nhưng chat quá mỏng để nói gì thêm — tái xác nhận ràng buộc "tìm buổi live Việt chat dày là việc khó" (10/09: chỉ 7/16 buổi đạt ≥100 bl) | dòng này |
| 11/09 | **Khảo sát khả năng 8 nền tảng** — Facebook (5 đường không token) · TikTok (video đã kết thúc) · Shopee Live (web + Open Platform) · Lazada · Zalo · Instagram · TikTok Shop | dò khả năng | FB không token: HTML video công khai 456.173 byte, `og:title` có "2,8 triệu lượt xem" nhưng **0 lần** xuất hiện `"comment_count"` / thân bình luận; `mbasic` **HTTP 400 đã chết**; yt-dlp `comment_count=NA` (extractor FB **không có** `_get_comments`). TikTok: trang hồ sơ chỉ 1.462 byte **trang thử thách WAF**, `/api/comment/list/` trả `status_code 5`; Research API có endpoint bình luận nhưng **Việt Nam không đủ điều kiện** (nguyên văn: US/EEA/UK/Canada/Thụy Sĩ). Shopee web: `/api/v1/session/*` **403**, grep **12,97 MB** bundle JS → 0 endpoint bình luận, 0 `wss://` | **PHÁT HIỆN LỚN: Shopee Open Platform v2 CÓ API bình luận live chính thức, có VN.** Phép thử đối chứng: `/api/v2/livestream/get_latest_comment_list` → `error_param "There is no partner_id"` trong khi đường bịa → **404 `error_not_found`**; ký thử đúng lược đồ → `403 invalid_partner_id`. `get_session_metric` cho **gmv · orders · atc · ccu · peak_ccu** — nền tảng **duy nhất** vừa cho bình luận vừa cho chuyển đổi. Viết adapter + 26 test | [../nen-tang-ho-tro.md](../nen-tang-ho-tro.md) |
| 11/09 | [ZU_0QJzsR6w](https://www.youtube.com/watch?v=ZU_0QJzsR6w) tải lại chat replay bằng yt-dlp 2026.08.19 | tái lập | 10.210.279 byte · **6.965 dòng · 6.963 bản tin chat** | Đường YouTube VOD **vẫn sống** ngày 11/09/2026 (đo lại độc lập, không qua API). Tệp chat thô có tên tác giả → xóa ngay sau khi đếm | [../nen-tang-ho-tro.md](../nen-tang-ho-tro.md) §2.1 |
| 11/09 (tối) | 4 buổi nạp lại vào server DỰNG MỚI: ZU_0QJzsR6w · fhv_rKUeEIc · MPJktS2rkzk · L5_mvE-Hqv4 | tái lập | **6.586 · 779 · 136 · 255** bl — khớp từng con số với 08–11/09 | Tái lập lần **4**, tiến trình thứ 4, sau khi tiến trình uvicorn cũ chết (store in-memory ⇒ mất 13 phiên); đường tải → lọc PII → phân loại → store vẫn tất định | mục "Trạng thái server" bên dưới |
| 11/09 (tối) | Bàn `/desk` + `/bao-cao` chạy trên phiên Achan 6.586 bl THẬT (ảnh 1920×1080 và 1366×768) | kiểm chứng UI | 689 test nhanh xanh · `tsc --noEmit` sạch | Bắt **2 lỗi trung thực trên màn hình** mà gate nguồn không thấy: (1) biểu đồ "Nhịp phiên" vẫn vẽ hai đường PHẲNG ở mức 0 cho `người xem` và `lượt bấm/phút` trong khi thẻ tín hiệu ngay trên nói "THIẾU nguồn" — mâu thuẫn trên cùng một màn hình, xảy ra với **13/13 phiên replay**; (2) đổi phiên dài → phiên ngắn làm radar + feed câm ("Chưa có bình luận nào" trên buổi 6.586 bl) vì mốc nước cao `lastCommentOffset` không reset. Đã sửa cả hai kèm gate hồi quy | `tests/test_web_desk_kol.py` |
| 11/09 (sau đó) | **Đi hết 4 luồng người dùng bằng Chrome headless** trên hệ thống đang sống (web :3000, API :8000 dựng lại): xem thử 30 giây · nạp `ZU_0QJzsR6w` qua UI · chạy trọn một phiên thí nghiệm 90 phút (tạo SP → link SP → tạo phiên → bốc thăm seed 42 → phát sóng → ghim trong khối BẬT → host → kết thúc) · đọc `/ket-qua` + `/bao-cao` | kiểm chứng UI đầu-cuối | 27 ảnh chụp thật · Achan ra **6.586** bl (tái lập lần **5**, tiến trình thứ 5) · 719 test nhanh xanh | Bắt **4 lỗi trung thực/vận hành** chỉ lộ khi bấm tay: (1) `?session=` trên `/replay` bị bỏ qua ⇒ phân tích xong mở **nhầm buổi** (đã ghi 11/09, nay có ảnh chứng); (2) khối TẮT trả 409 kèm câu giải thích đúng nhưng bàn hiện *"Không gửi được lệnh — kiểm tra kết nối API"* — chẩn đoán SAI giữa buổi live; (3) `viewers` không reset khi đổi phiên ⇒ đồng hồ khối in số người xem của **phiên trước** (41) rồi in **0** trong khi ô ngay dưới nói "THIẾU nguồn"; (4) tín hiệu `clicks` ghi *"không có link đo"* dù đã tạo 2 link — thực chất là *chưa có lượt bấm nào* | [../HUONG-DAN-SU-DUNG.md](../HUONG-DAN-SU-DUNG.md) · `tests/test_docs_huong_dan.py` |

## Trạng thái server xem trực tiếp (11/09/2026)

**Tiến trình uvicorn đã chết HAI lần trong ngày.** Lần đầu: tiến trình giữ 13
phiên (17.535 bình luận) tắt trước phiên làm việc tối 11/09 ⇒ mất sạch 13
`session_id`, server dựng lại (tiến trình thứ 4) và nạp lại 4 buổi tiêu biểu —
ra **đúng con số cũ**, tái lập lần 4:

| Video | Buổi | Bình luận | Khớp tài liệu |
|---|---|---:|---|
| `ZU_0QJzsR6w` | Achan Shop Hải Phòng | 6.586 | 08/09 và 10/09 ✔ |
| `fhv_rKUeEIc` | Sâm Ngọc Linh | 779 | 10/09 ✔ |
| `L5_mvE-Hqv4` | Xả kho trang sức | 255 | 11/09 ✔ |
| `MPJktS2rkzk` | Đấu giá đá quý | 136 | 10/09 ✔ |

**Lần thứ hai:** tiến trình thứ 4 cũng đã chết trước phiên viết hướng dẫn sử
dụng (cổng 8000 im, không còn tiến trình python nào) ⇒ **4 buổi trên cũng mất**.
Server dựng lại lần nữa (tiến trình thứ 5) bằng cùng một lệnh:

```
.venv/Scripts/python -m uvicorn livelift.api.main:app --host 127.0.0.1 --port 8000
```

Lần này buổi Achan được nạp **qua đúng nút bấm trên giao diện** (trang chính →
ô số 2 → dán link → *Phân tích*), không dùng script — và vẫn ra **6.586 bình
luận**: tái lập lần **5**, tiến trình thứ **5**, lần đầu qua đường người-dùng
thay vì đường script.

`session_id` cố tình KHÔNG ghi lại ở đây: mỗi lần dựng server là một bộ id
mới, ghi ra sẽ thành một bảng sai ngay lần khởi động sau. Lấy id thật bằng
`GET /sessions`.

> **Bài học lặp lại 2 lần trong 1 ngày:** store in-memory làm mọi phiên demo
> sống không quá một lần tắt tiến trình. Trước buổi trình bày phải dựng bằng
> Postgres (`docker compose up -d`) hoặc nạp lại ngay trước giờ diễn.

Cách xem: mở `http://localhost:3000/replay`, chọn buổi trong dropdown góc trái
(trang mặc định mở phiên đã kết thúc đầu tiên), kéo thanh thời gian để xem
radar + feed ở bất kỳ phút nào; nút **Báo cáo phiên →** góc trên phải mở thẳng
`/bao-cao/<id>` của đúng buổi đang tua (gói UI-KOL). Bàn trợ live `/desk` mở
buổi đã kết thúc qua nút "Vẫn mở bàn điều khiển với phiên đã kết thúc". Lưu ý
đã ghi nhận 11/09: tham số `?session=` trên URL `/replay` hiện **không được
đọc** (`useReplay` luôn chọn phiên ended đầu tiên) — chọn phiên bằng dropdown;
sửa việc này nằm trong danh sách việc tiếp theo.

Store là in-memory: **tắt tiến trình uvicorn là mất các phiên đã nạp** — nạp
lại bằng `scripts/live_fire_da_nguon.py nap <video_id...>` (~10–70 s mỗi buổi).
