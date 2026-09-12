# Lưu trữ dữ liệu — ba chế độ, chọn cái nào, và rủi ro thật

*Viết sau sự cố 11/09/2026. Mọi con số dưới đây đều đo được trên máy này ngày
12/09/2026, không có số nào ước lượng.*

## Chuyện đã xảy ra

Lúc **13:05:53 ngày 11/09/2026** tiến trình API khởi động lại. **13 phiên live
thật và 17.535 bình luận biến mất vĩnh viễn.** Không phải lỗi ai bấm nhầm, không
có bản sao nào để lấy lại: kho đang chạy `store_backend=memory`, tức toàn bộ dữ
liệu nằm trong RAM của đúng tiến trình đó. Sau đó còn mất thêm một lần nữa.
Chi tiết kiểm kê: `docs/benchmarks/kiem-chung-van-hanh.md` mục 0.

Đặt vào sản phẩm thật: **một KOL live 90 phút, máy chủ restart ở phút 89 là mất
trắng cả buổi.** Không chấp nhận được — và cũng không có gì báo trước, vì trước
ngày 12/09 không một endpoint nào nói ra là hệ thống đang ở chế độ mất dữ liệu.

---

## Ba chế độ

| Chế độ | Dữ liệu sống ở đâu | Restart thì sao | Cần gì |
|---|---|---|---|
| **`memory` trần** | RAM | **MẤT SẠCH** | không cần gì |
| **`memory` + ảnh chụp** | RAM, đổ ra tệp JSON định kỳ | mất tối đa **một chu kỳ** (mặc định 30 giây) | một thư mục ghi được |
| **`postgres`** | PostgreSQL | **không mất gì** | Docker (hoặc một Postgres sẵn có) |

Chọn nhanh:

- **Phiên live thật, có tiền/có KOL/có dữ liệu vào bài báo → `postgres`.** Không
  có ngoại lệ. Đây là chế độ duy nhất chịu được mất điện, OOM-kill, hay một lần
  `Ctrl+C` nhầm.
- **Demo, thi đấu, máy không cài được Docker → `memory` + ảnh chụp.** Mặc định
  đã BẬT sẵn. Chấp nhận mất tối đa 30 giây sự kiện cuối, không mất cả phiên.
- **`memory` trần → chỉ dùng khi chạy test tự động**, nơi dữ liệu vốn nên biến
  mất. Muốn tắt ảnh chụp ở chỗ khác thì phải biết mình đang đánh đổi cái gì.

---

## Bật `postgres` (đường chính)

Một lệnh làm hết — dựng container, chờ healthy, chạy migrate, in ra biến môi
trường còn thiếu:

```bash
.venv/Scripts/python scripts/bat_postgres.py
```

Hoặc làm tay:

```bash
docker compose up -d db          # .env phải có POSTGRES_PASSWORD
.venv/Scripts/livelift-migrate up
export STORE_BACKEND=postgres    # PowerShell: $env:STORE_BACKEND = "postgres"
export DATABASE_URL='postgresql://livelift:<mật khẩu>@127.0.0.1:5432/livelift'
.venv/Scripts/python -m uvicorn livelift.api.main:app --port 8000
```

> **Cái bẫy đã dính một lần (sự cố 25/08/2026):** đặt `DATABASE_URL` là **chưa
> đủ**. `DATABASE_URL` chỉ nói cơ sở dữ liệu ở *đâu*; `STORE_BACKEND` mới quyết
> định *có dùng hay không*. Thiếu biến thứ hai thì API chạy hoàn toàn bình
> thường và vẫn giữ mọi thứ trong RAM. Nay `build_store()` ghi một dòng cảnh
> báo tiếng Việt vào log đúng tình huống đó, nhưng đừng dựa vào log — hãy đo:

```bash
curl -s http://127.0.0.1:8000/health
# {"status":"ok","store_backend":"postgres","storage_mode":"postgres","durable":true,...}
```

Trong Docker thì `docker-compose.yml` đã đặt sẵn `STORE_BACKEND: postgres` cho
cả `api` lẫn `migrate`; lớp thứ ba là dịch vụ `backup`, mỗi ngày 02:00 đổ một
bản dump đã **xác minh đọc được** vào `./backups/` và giữ 14 ngày.

---

## Ảnh chụp cho chế độ `memory` (đường dự phòng)

Mặc định **BẬT**. Cấu hình trong `.env`:

```ini
STORE_SNAPSHOT_ENABLED=true
STORE_SNAPSHOT_PATH=data/snapshot/livelift-store.json   # tương đối theo thư mục chạy
STORE_SNAPSHOT_INTERVAL_S=30
```

Cách nó làm việc — ba thời điểm, thiếu cái nào cũng hỏng:

1. **Lúc khởi động** — có tệp thì nạp lại toàn bộ, và ghi ra log tiếng Việt
   khôi phục được bao nhiêu: `Đã KHÔI PHỤC kho từ ảnh chụp …: 13 phiên, 17535
   bình luận, 2340 tick, 0 lượt nhấp.`
2. **Mỗi `STORE_SNAPSHOT_INTERVAL_S` giây** — chỉ ghi khi kho **có thay đổi**
   (đếm bằng bộ đếm phiên bản nội bộ), nên phiên đang im lặng không làm đĩa quay.
   Đường ghi của request (`POST /comments`) **không đụng tệp nào**.
3. **Lúc tắt có trật tự** — chụp lần cuối, nên tắt bằng `Ctrl+C` thì không mất gì.

Ghi **nguyên tử**: ghi ra tệp tạm cùng thư mục → `flush` + `fsync` → `os.replace`.
Tệp đích vì thế luôn là bản **cũ nguyên vẹn** hoặc bản **mới trọn vẹn**, không bao
giờ là bản cụt. Hỏng giữa chừng thì tệp tạm bị xoá, không để lại rác.

Tệp hỏng (đĩa lỗi, phiên bản cũ) **không** làm chết API và **không** bị ghi đè:
nó được đổi tên thành `livelift-store.json.hong-<thời-điểm>` để còn mổ xẻ, API
khởi động với kho rỗng và ghi rõ lý do vào log.

### Giá phải trả — đo thật, đúng quy mô đã mất

Dựng lại đúng quy mô của sự cố (13 phiên / 17.535 bình luận / 2.340 tick):

| Phép đo | Kết quả (trung vị 5 lần) |
|---|---|
| Tuần tự hoá — phần **khoá vòng lặp sự kiện** | **107 ms** |
| Tuần tự hoá + ghi đĩa trọn vẹn | 242 ms |
| Kích thước tệp | 6,30 MB |
| Nạp lại lúc khởi động | 102 ms |
| Dữ liệu khớp sau khôi phục | **100% mọi bảng** |

Đọc bảng này cho đúng: mỗi 30 giây có **một nhịp ~107 ms** vòng lặp sự kiện bận
tuần tự hoá (phần ghi đĩa đã đẩy sang luồng khác). Ở quy mô live thật thì không
ai thấy, nhưng đây **là** một cái giá, không phải "miễn phí". Nếu phiên lớn hơn
nữa thì tăng `STORE_SNAPSHOT_INTERVAL_S` — hoặc, đúng hơn, chuyển sang Postgres.

---

## Ảnh chụp KHÔNG phải Postgres

Nói thẳng, vì chỗ này rất dễ tự ru ngủ:

- Ảnh chụp là **một tệp trên cùng cái máy**. Hỏng ổ đĩa là mất cả tệp lẫn RAM.
- Cửa sổ mất mát là **có thật**: chết đột ngột giữa hai chu kỳ thì mất mọi sự
  kiện trong chu kỳ đó. `/health` trả `durable: false` cho chế độ này **là cố ý**.
- Không có bản sao theo ngày, không có phục hồi theo thời điểm. Postgres có
  (`./backups/`, dump đã xác minh, giữ 14 ngày).

Vì vậy `/health` ở chế độ ảnh chụp vẫn nói: *"Đủ cho demo và thi đấu; phiên live
thật vẫn nên chạy `STORE_BACKEND=postgres`."*

---

## Hỏi `/health` thay vì đoán

```bash
curl -s http://127.0.0.1:8000/health
```

| `storage_mode` | `durable` | Nghĩa là |
|---|---|---|
| `postgres` | `true` | restart không mất gì |
| `memory+snapshot` | `false` | mất tối đa một chu kỳ; `snapshot.last_saved_at` cho biết lần ghi gần nhất |
| `memory` | `false` | **NGUY HIỂM** — restart là mất sạch; `storage_warning` nói thẳng điều đó |

Trường `snapshot.restored_at_startup` đếm từng bảng đã khôi phục lúc khởi động —
đây là cách trả lời câu hỏi *"lần restart vừa rồi có mất gì không?"* mà ngày
11/09 phải ngồi đếm tay mới biết.

---

## Đừng tin, hãy đo

```bash
# giết CỨNG tiến trình API rồi bật lại, đếm xem còn gì
.venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend postgres
.venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend memory --interval 3
.venv/Scripts/python scripts/kiem_chung_ben_vung.py --backend memory --no-snapshot   # đối chứng ÂM
```

Script mở cổng riêng (mặc định 8099) nên **không đụng** API thật ở cổng 8000.
Nó không tắt lịch sự — nó gọi `TerminateProcess`/`SIGKILL`, đúng như một tiến
trình chết giữa chừng; tắt lịch sự sẽ luôn "đạt" và ta sẽ tự lừa mình.

Kết quả đo ngày 12/09/2026, mỗi lượt nạp 25 bình luận qua HTTP rồi giết cứng:

| Chế độ | Sau khi bật lại | Kết luận |
|---|---|---|
| `postgres` | phiên **CÒN**, 25/25 bình luận | ĐẠT |
| `memory` + ảnh chụp (3 s) | phiên **CÒN**, 25/25 bình luận | ĐẠT |
| `memory` không ảnh chụp | phiên **MẤT**, 0 bình luận | ĐẠT (đúng dự đoán) |

Dòng cuối là **đối chứng âm** và nó quan trọng ngang hai dòng trên: nó tái hiện
đúng sự cố 11/09 theo yêu cầu, chứng minh phép thử này có răng chứ không phải
lúc nào cũng xanh.

### Cửa sổ mất mát — đo bằng số, không hứa suông

Phép thử ở trên dừng nạp rồi mới giết, nên nó không trả lời được câu hỏi thật:
*giết CỨNG giữa lúc bình luận đang đổ vào thì mất bao nhiêu?* Đo riêng: chu kỳ
chụp **5 giây**, nạp liên tục **45 giây** với nhịp đo được **17,4 bình luận/giây**,
rồi `TerminateProcess` ngay giữa dòng chảy.

| Phép đo | Kết quả |
|---|---|
| Đã gửi | 783 bình luận |
| Còn lại sau khi bật lại | **760** (97,1%) |
| Mất | **23 bình luận = 1,3 giây dữ liệu** |
| Trần lý thuyết (một chu kỳ) | 5 giây → **trong trần** |

Đây là cái giá đúng như thiết kế: mất **giây**, không mất **buổi**. So với ngày
11/09 — mất 13 phiên và 17.535 bình luận — đó là khác biệt giữa một vết xước và
một buổi live bốc hơi.

Cổng hồi quy tự động: `tests/test_store_snapshot.py` (24 test — khôi phục đủ mọi
bảng, mốc thời gian giữ đúng kiểu, ghi nguyên tử, không rác, bản cũ không đè được
bản mới, tắt được, `/health` phải cảnh báo, và hai cổng cấu trúc chặn lỗi tương
lai). Đã kiểm chứng **7 lỗi tiêm vào đều làm đỏ đúng test tương ứng** — cổng có
răng, không phải cổng luôn xanh.

---

## Việc chưa làm

- Ảnh chụp ghi **toàn bộ** trạng thái mỗi chu kỳ. Với phiên rất lớn (nhiều chục
  nghìn bình luận) nên đổi sang ghi thêm dạng nhật ký (JSONL append) để hết hẳn
  nhịp 107 ms. Chưa cần ở quy mô hiện tại.
- Chưa có cảnh báo trên giao diện web khi `durable: false` — dữ liệu đã sẵn ở
  `/health`, phần hiển thị thuộc gói khác.
- `./backups/` đang nằm trên cùng máy với cơ sở dữ liệu. Trên VPS thật phải
  mount vào một thư mục được đồng bộ đi nơi khác (đã ghi trong `docker-compose.yml`).
