# Kho dữ liệu chết giữa phiên live — kịch bản kiểm chứng

*Chạy lại bằng đúng một lệnh:* `.venv/Scripts/python docs/benchmarks/kich-ban-kho-chet.py`
*Gate tự động đi kèm:* `.venv/Scripts/python -m pytest tests/test_kho_chet_giua_phien.py -q`

Ngày đo: **13/09/2026** · Python 3.12.6 · Windows-11-10.0.22631 · gói **D-ĐỘ-BỀN**.

## Câu hỏi

Chiều 13/09/2026 Docker daemon chết trên máy chạy demo. PostgreSQL biến mất
hoàn toàn (không ai nghe cổng 5432), **API vẫn sống**. Với một phiên live 90
phút đang phát, câu hỏi sống còn không phải là "hệ thống có lỗi không" mà là:

1. **Bình luận và lượt nhìn đang thu có mất không?**
2. **Người vận hành có BIẾT là đang mất không**, hay vẫn nhìn thấy màn hình xanh?
3. Sau khi kho sống lại, **có nạp bù được không** mà không nhân đôi dữ liệu?

> **ĐÂY LÀ SỐ ĐO CỦA KỊCH BẢN, KHÔNG PHẢI CỦA MỘT PHIÊN LIVE THẬT.** Kịch bản
> dùng store thật (`InMemoryStore`) bọc trong một lớp cho phép "rút dây" và ném
> đúng lớp lỗi psycopg ném khi mất kết nối, vì Docker trên máy đo đã chết nên
> không dựng lại được PostgreSQL thật. Mọi thứ còn lại là hàng thật: app
> FastAPI thật, `ApiSink` thật, bộ thực thi tự động thật, `spool_replay` thật.
> Hệ quả phải nói rõ: con số thời gian dưới đây chỉ tính **backoff của bộ thu**
> (0,5s + 1,0s), KHÔNG tính thời gian chờ timeout của một kết nối Postgres thật
> — sự cố 13/09 đo được `GET /sessions` treo **30 giây** trước khi trả lỗi, nên
> ngoài đời khoảng cách giữa hai cách làm còn lớn hơn nhiều. Cửa sổ "kho chết"
> trong kịch bản chỉ dài dưới một giây (kịch bản chạy trong vài giây), nên đừng
> đọc mốc giờ trong báo động như thời lượng của một sự cố thật.

## Ba lỗ hổng đã bịt

| # | Trước | Sau | Khóa bằng |
|---|---|---|---|
| 1 | Bộ thu thử đủ 3 vòng cho **mọi** bản ghi kể cả khi kho đã chết → nhịp đọc bình luận nghẽn; 4xx-payload cũng vào spool, gieo bản ghi "độc" làm mọi lần nạp bù sau đó báo thất bại | Sau 2 POST hỏng liên tiếp phía máy chủ → **chế độ spool**: ghi thẳng vào đĩa, 30 giây mới dò lại một lần. 5xx/lỗi mạng/401/404 **luôn** giữ bản ghi; chỉ 400/422 mới bị vứt và bị log ERROR | `test_moi_loi_5xx_deu_vao_spool_khong_bi_vut`, `test_khi_may_chu_hong_lien_tuc_sink_ghi_thang_vao_spool_va_bao_dong`, `test_payload_sai_bi_vut_chu_khong_gieo_ban_ghi_doc_vao_spool` |
| 2 | `POST /comments` trả `500 Internal Server Error` trống rỗng — không ai biết bình luận vừa rồi đã lưu hay chưa | **503** + câu tiếng Việt nói thẳng "CHƯA ĐƯỢC LƯU" + lệnh nạp bù + header `Retry-After` / `X-LiveLift-Storage: down`. Bug thật vẫn nổ nguyên trạng, không bị ngụy trang thành 503 | `test_ghi_binh_luan_khi_kho_chet_tra_503_va_noi_ro_chua_luu`, `test_loi_lap_trinh_that_khong_bi_nguy_trang_thanh_503` |
| 3 | Bộ thực thi tự động nuốt lỗi kho trong `except Exception`, quét tiếp mỗi 5 giây, **im lặng**, để từng khối BẬT trôi qua → báo cáo sẽ đổ lỗi "đội vận hành không tuân thủ" thay vì "cơ sở dữ liệu đã chết" | Vòng quét **DỪNG NGAY** giữa chừng, ghi lại cửa sổ chết, bắn báo động tiếng Việt lên `GET /sessions/{id}/state`; báo động **ở lại** sau khi kho sống lại vì các khối đã trôi qua không ghim bù được | `test_kho_chet_lam_bo_thuc_thi_dung_han_va_khong_ghim_nua`, `test_bao_dong_kho_chet_hien_len_ban_dieu_khien`, `test_sau_khi_kho_song_lai_bo_thuc_thi_chay_tiep_nhung_van_khai_bao_su_co` |

## Kết quả đo (nguyên văn đầu ra của kịch bản)

```text
==============================================================================
1. Kho còn sống — bình luận vào thẳng cơ sở dữ liệu
==============================================================================
bình luận trong kho: 1

==============================================================================
2. RÚT DÂY giữa phiên (docker stop db) — đường ghi sự kiện nói gì?
==============================================================================
POST /sessions/<id>/comments -> HTTP 503
Retry-After: 5
X-LiveLift-Storage: down
detail:
  KHO DỮ LIỆU KHÔNG PHẢN HỒI — Bình luận này CHƯA ĐƯỢC LƯU. Bộ thu đang giữ bản ghi trong data/spool/78b7fd81-1ff3-4aec-9bd1-f55365e1ad37.jsonl; sau khi kho sống lại hãy nạp bù bằng: python -m livelift.ingest.spool_replay data/spool/78b7fd81-1ff3-4aec-9bd1-f55365e1ad37.jsonl (gửi lại an toàn nhờ khóa idempotency). Trong lúc chờ, số liệu trên bàn điều khiển là THIẾU — hãy dừng phiên hoặc ghi tay, đừng chạy tiếp trong vô vọng.

GET /sessions/<id>/comments -> HTTP 503 (không treo, không 500 trống)

==============================================================================
3. Bộ thu: 20 bình luận tới trong lúc kho chết
==============================================================================
cách cũ  :  30.582 giây cho 20 bình luận, spool 20 bản ghi
cách mới :   3.075 giây cho 20 bình luận, spool 20 bản ghi
nhanh hơn: 9.9×  (mới chỉ tính backoff 0,5s + 1,0s;
           với timeout kết nối Postgres thật, khoảng cách còn lớn hơn nhiều)
sink: spool_mode=True  spooled=20  dropped=0
last_error: máy chủ trả HTTP 503
dòng spool đầu tiên: kind=comment ext_id=chet-0 text='chốt đơn 0'

==============================================================================
4. Bộ thực thi tự động trong lúc kho chết
==============================================================================
step_all() trả về: []  (không ghim gì — đúng)
storage_outage(): active=True error=OperationalError sweeps_blocked=1
exposure_event đã ghi: 0

==============================================================================
5. Người vận hành nhìn thấy gì trên bàn điều khiển?
==============================================================================
GET /sessions/<id>/state?role=operator -> HTTP 200
autopilot.last_error: kho dữ liệu không phản hồi: OperationalError
autopilot.alarm:
  BÁO ĐỘNG: bộ thực thi tự động ĐÃ DỪNG vì kho dữ liệu không phản hồi (từ 16:28:12 UTC, lỗi OperationalError, 1 vòng quét bị bỏ). Không có khối BẬT nào được ghim trong lúc này và cũng KHÔNG ghim bù được. Sửa cơ sở dữ liệu ngay, hoặc dừng phiên — chạy tiếp chỉ tạo thêm khối không tuân thủ. BÁO ĐỘNG: phiên đang phát ở chế độ TỰ ĐỘNG nhưng sau 5.0 phút vẫn CHƯA CÓ hành động ghim nào. Nhánh BẬT chưa hề được can thiệp — tuân thủ = 0 và thí nghiệm sẽ không ước lượng được gì. Kiểm tra bộ thực thi tự động (biến môi trường LIVELIFT_AUTOPILOT) hoặc ghim tay ngay.

==============================================================================
6. Kho sống lại — nạp bù bằng spool_replay
==============================================================================
bình luận trong kho TRƯỚC khi nạp bù: 1
lần 1: thành công=20 thất bại=0 -> bình luận trong kho: 21
lần 2: thành công=20 thất bại=0 -> bình luận trong kho: 21 (không nhân đôi)

==============================================================================
7. Bộ thực thi chạy lại, nhưng sự cố KHÔNG bị xóa khỏi báo cáo
==============================================================================
step_all() sau khi kho sống: 1 hành động
  Tự động ghim sản phẩm SP0 ở khối 5 (BẬT) của phiên 78b7fd81-1ff3-4aec-9bd1-f55365e1ad37, propensity nội tầng 0.333, 3 sản phẩm trong tập chồng lấn.
storage_alarm() vẫn khai báo sự cố:
  CẢNH BÁO: kho dữ liệu đã chết từ 16:28:12 đến 16:28:12 UTC (1 vòng quét bị bỏ, lỗi OperationalError); bộ thực thi tự động đã chạy lại. Các khối BẬT trôi qua trong khoảng đó KHÔNG ghim bù được và sẽ được tính là KHÔNG tuân thủ — ghi rõ lý do này vào nhật ký phiên.
```

## Đọc kết quả

**§3 — không mất bình luận nào, và nhịp thu không sập.** 20/20 bình luận vào
spool, `dropped=0`. Thời gian xử lý 20 bình luận giảm từ **30,582s** xuống
**3,075s** (**9,9×**): hai bản ghi đầu vẫn thử đủ 3 lần (2 × 1,5s backoff = 3,0s),
18 bản ghi sau đi thẳng vào đĩa. Đây là khác biệt giữa "kho chết" và "kho chết
KÉO THEO mất bình luận vì vòng đọc nghẽn".

**§2 và §5 — người vận hành biết, bằng tiếng Việt, kèm việc phải làm.** Ba chỗ
cùng nói một sự thật: mã 503 + `X-LiveLift-Storage: down` trên đường ghi, báo
động trên `/state`, và dòng ERROR trong heartbeat của runner mỗi 60 giây
(`test_heartbeat_cua_runner_het_len_khi_dang_o_che_do_spool`). Thứ tự trong
`alarm` là cố ý: **nguyên nhân (kho chết) đứng trước hậu quả (chưa ghim gì)**,
để người đọc không kết luận nhầm là đội vận hành lười.

**§4 và §7 — bộ thực thi dừng, rồi chạy lại, nhưng không giấu chuyện đã xảy ra.**
`exposure_event = 0` trong lúc kho chết: không có một cú ghim nửa vời nào khi
chưa đọc nổi bảng phơi nhiễm. Sau khi kho sống, ghim tiếp bình thường — nhưng
`storage_alarm()` vẫn khai báo cửa sổ chết, vì các khối BẬT trôi qua trong
khoảng đó là **không tuân thủ thật** và lý do phải đi kèm con số vào báo cáo.

**§6 — nạp bù đủ và không nhân đôi.** 20/20 bản ghi vào kho; chạy lại lệnh nạp
bù lần thứ hai vẫn báo `thành công=20` nhưng số bình luận **không đổi** (21),
nhờ khóa idempotency `(platform, ext_id)` ở tầng store.

## Việc phải làm khi gặp thật

1. Đọc `GET /health` → `storage_mode` / `durable` (gói A-HEALTH ping kho thật).
2. Nếu đường ghi trả **503**: dữ liệu đang vào spool, **không** cần tắt runner.
   Ghi mốc giờ vào `ops/templates/nhat-ky-phien.md`.
3. Quyết định trong 1 phút: sửa kho được ngay thì sửa; không thì **dừng phiên**
   — chạy tiếp chỉ sinh thêm khối BẬT không tuân thủ (xem §7).
4. Kho sống lại → nạp bù: `python -m livelift.ingest.spool_replay data/spool/<mã phiên>.jsonl --api-base http://127.0.0.1:8000`.
   Chạy lại nhiều lần là an toàn. Lệnh trả về khác 0 nghĩa là còn bản ghi chưa vào.
5. Trong báo cáo phiên: chép nguyên văn câu `storage_alarm()` vào phần hạn chế.
   Khoảng trống tuân thủ có nguyên nhân, và nguyên nhân đó phải được viết ra.

## Giới hạn còn lại (chưa bịt trong gói này)

- Kịch bản dùng store giả lập chết, **chưa chạy trên PostgreSQL thật** (Docker
  daemon trên máy đo đã chết). Cần chạy lại đúng kịch bản này với
  `STORE_BACKEND=postgres` + `docker stop livelift-db` khi có Docker trở lại.
- Đường **click** (`/r/{code}` trong `routes/redirect.py`) chưa đi qua
  `storage_guard` — thuộc vùng file của gói khác, ghi làm việc tiếp theo.
- `ApiSink` chưa có trần kích thước file spool: kho chết cả phiên 90 phút thì
  file spool cứ lớn dần. Chưa đo được ngưỡng nguy hiểm nên chưa đặt số.
- Nếu `execute_action` chết **giữa** hai lần ghi (intervention_log xong,
  exposure_event chưa), bộ thực thi không vá được — giao dịch thuộc tầng store.
