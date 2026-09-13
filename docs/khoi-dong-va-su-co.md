# Khởi động LiveLift và xử lý sự cố

*Viết cho người không chuyên. Không cần biết Next.js, Docker hay PostgreSQL là gì —
chỉ cần gõ đúng lệnh và đọc đúng dòng chữ máy trả về.*

Tất cả lệnh dưới đây gõ trong **PowerShell**, đứng ở thư mục `D:\AISC2026\livelift`.

---

## 1. Một lệnh để bật mọi thứ

```powershell
cd D:\AISC2026\livelift
.venv\Scripts\python scripts\chay_local.py
```

Lệnh này làm trọn sáu việc và **đo** chứ không tin:

| Bước | Việc | Vì sao có bước này |
|---|---|---|
| (a) | Tìm tiến trình đang giữ cổng 3000 / 8000, in **PID + tên**, hỏi trước khi dừng | Ngày 13/09/2026 một tiến trình `next` cũ vẫn giữ cổng 3000 và phục vụ từ thư mục build **đã bị xoá** |
| (b) | Xoá các thư mục build thừa `web/.next-...` (giữ lại `.next` và mọi thư mục vừa được ghi trong 5 phút gần đây — có thể đang có tiến trình khác dùng) | Nhiều tiến trình cùng ghi một thư mục build là nguyên nhân gốc làm trang vỡ |
| (c) | Hỏi PostgreSQL có **thật sự trả lời** không (`SELECT 1`), không thì tự chọn kho RAM và **nói thẳng ra** | Kho chết mà màn hình vẫn xanh là lỗi nguy hiểm nhất trong dự án này |
| (d) | Bật API, đợi `/health` xanh, in luôn `storage_mode` | Để biết dữ liệu đang nằm ở đâu **trước khi** lên sóng |
| (e) | Bật web, đợi trang chủ 200, rồi **tải tệp CSS về cân** | Đúng phép thử mà sự cố "trang vỡ" đã trượt qua |
| (f) | In bảng tóm tắt: địa chỉ mở, chế độ kho, số phiên đang có | Một màn hình duy nhất trả lời "mọi thứ ổn chưa" |

Nhấn **Ctrl+C** để dừng gọn gàng cả hai tiến trình (lệnh này **không** để lại
tiến trình mồ côi — tiến trình mồ côi chính là nửa sau của sự cố 13/09).

Đo ngày 13/09/2026 trên máy chủ dự án: từ lúc gõ lệnh tới lúc bảng tóm tắt hiện
ra mất **15,3 giây** (thư mục build còn nóng), và tệp CSS của máy chủ dev cân
được **63.426 byte**.

### Các cờ hay dùng

| Cờ | Tác dụng |
|---|---|
| `--force` | Dừng luôn tiến trình đang giữ cổng, không hỏi. **Không có cờ này và không có ai để hỏi thì lệnh dừng lại, tuyệt đối không tự giết tiến trình nào.** |
| `--sach` | Xoá luôn thư mục build đang dùng rồi dựng lại từ đầu (dùng khi trang hiển thị lạ) |
| `--kho memory` / `--kho postgres` | Ép chế độ kho, bỏ qua bước tự đo |
| `--bo-qua-web` | Chỉ bật API |
| `--tach` | Kiểm tra xong thì thoát, để API và web chạy tiếp |
| `--thu-roi-thoat` | Chạy trọn vòng kiểm tra rồi **tự tắt cả hai** và thoát (dùng để kiểm nhanh hoặc trong CI) |
| `--cong-web 3100` | Đổi cổng (khi cổng 3000 đang bận mà không muốn dừng nó) |

Mã thoát: `0` mọi thứ xanh · `1` không khởi động được · `2` cổng bị chiếm mà
chưa được phép dừng · `3` web lên nhưng **CSS hỏng**.

---

## 2. Cổng chống "trang vỡ vì thiếu CSS" — chạy TRƯỚC khi demo cho giám khảo

```powershell
.venv\Scripts\python scripts\gate_css_web.py
```

Mất khoảng **1 phút** (đo ngày 13/09/2026: `next build` 51,3 giây, tổng 53,7 giây).
Kết quả đạt in ra một dòng như:

```
ĐẠT — trang chủ 200, /_next/static/css/f721f4d33ce87c2c.css tải được (36.017 byte, có --canvas, --brand)
```

Cổng này dựng **bản build thật** vào một thư mục riêng (`web/.next-gate-css`,
không đụng `.next` của máy chủ dev đang chạy), phục vụ nó, rồi khẳng định bốn
điều: trang chủ trả **200**; HTML có thẻ `<link rel="stylesheet">`; **tải được**
tệp CSS đó về; tệp ấy **lớn hơn 10 KB** và **chứa token thiết kế** `--canvas`,
`--brand`.

Bước "tải tệp về" mới là bước bắt được lỗi: hôm xảy ra sự cố, thẻ `<link>` vẫn
nằm đúng chỗ và trang chủ vẫn trả 200 — chỉ có tệp phía sau nó trả 404.

Cùng phép thử ấy chạy được trong bộ test (cùng mã, đánh dấu `slow`):

```powershell
.venv\Scripts\python -m pytest tests\test_web_css_gate.py -q
```

Bộ test còn có một phép thử **kiểm chứng ngược**: nó dựng bản build lành, xoá
tệp CSS khỏi thư mục build rồi phục vụ lại, và bắt buộc cổng phải **đỏ**. Đo
ngày 13/09/2026: trang lỗi 404 của Next dài 7.083 byte, nên cổng đỏ vì bốn lẽ
độc lập (mã 404, Content-Type là HTML, dưới 10 KB, thiếu token). Một cổng không
tự chứng minh được là nó bắt được lỗi thì chỉ là một dòng xanh vô nghĩa.

**Lịch chạy đề nghị:** một lần sau khi sửa bất cứ thứ gì trong `web/`, và một
lần ngay trước buổi demo.

---

## 3. Bảng tra: triệu chứng → nguyên nhân → lệnh sửa

| Triệu chứng | Nguyên nhân | Lệnh sửa |
|---|---|---|
| **Trang chủ hiện chữ đen trên nền trắng, không màu, không bố cục — đúng nghĩa HTML thô.** Mở Developer Tools (F12) thấy `/_next/static/css/app/layout.css` trả 404 | Nhiều tiến trình `next dev` / `next build` cùng ghi một thư mục `.next` làm hỏng thư mục build (`.next/static/css` rỗng), và/hoặc một tiến trình `next` cũ vẫn giữ cổng 3000 rồi phục vụ từ thư mục đã bị xoá | `.venv\Scripts\python scripts\chay_local.py --force --sach` — dừng tiến trình cũ, xoá sạch thư mục build, dựng lại, rồi **tự kiểm tra CSS**. Xác nhận lại bằng `scripts\gate_css_web.py` |
| **Trang web vẫn "chạy" nhưng hiển thị dữ liệu cũ / lạ, sửa mã không thấy đổi** | Cổng 3000 đang do một tiến trình `next` cũ giữ; máy chủ mới không lên được nhưng trình duyệt vẫn thấy 200 từ tiến trình cũ | `.venv\Scripts\python scripts\chay_local.py --force` (bước (a) in rõ PID + tên trước khi dừng) |
| **Không bật được máy chủ, báo `EADDRINUSE` / `address already in use`** | Cổng 3000 hoặc 8000 đang bị chiếm | Chạy `scripts\chay_local.py` — nó in ngay ai đang giữ cổng. Muốn xem tay: `Get-NetTCPConnection -State Listen -LocalPort 3000` rồi `Get-Process -Id <PID>` |
| **`/health` báo xanh, `storage_mode=postgres`, `durable=true` — nhưng dữ liệu không hề được lưu** | PostgreSQL đã chết (không ai nghe cổng 5432) mà `/health` không hề hỏi cơ sở dữ liệu; nó chỉ đọc lại cấu hình mình được đặt lúc khởi động | Đừng tin `/health` một mình. Chạy `scripts\chay_local.py` — bước (c) **thật sự chạy `SELECT 1`** rồi mới kết luận. Muốn kiểm tay: `Test-NetConnection 127.0.0.1 -Port 5432` |
| **Gọi `GET /sessions` treo rất lâu (đo 30 giây) rồi trả `Internal Server Error`; trang chủ báo "Chưa kết nối được máy chủ" dù API đang sống** | Kho đang đặt là `postgres` nhưng PostgreSQL đã chết; mỗi truy vấn chờ hết thời gian kết nối. Trang chủ dò API bằng `/sessions` với hạn 2,5 giây nên luôn trượt | Chuyển sang kho RAM: `scripts\chay_local.py --kho memory` (đo lại sau khi chuyển: `/sessions` còn 0,016 giây) |
| **`docker` báo lỗi, không bật được PostgreSQL** | Máy chủ Docker (Docker Desktop) đã tắt hẳn | Đây **không** phải lỗi chặn demo. `scripts\chay_local.py` tự chọn kho `memory + ảnh chụp` và nói rõ **dữ liệu nằm trong RAM**. Muốn thử bật lại kho bền vững: `.venv\Scripts\python scripts\bat_postgres.py` (xem `docs/luu-tru-du-lieu.md`) |
| **Thư mục `web/` đầy các thư mục `.next-...` lạ** | Các tiến trình dev/build song song để lại | `scripts\chay_local.py` tự dọn ở bước (b), nhưng **giữ lại** thư mục vừa được ghi trong 5 phút gần đây (có thể đang có người dùng). Xoá tay: `Remove-Item -Recurse -Force web\.next-*` — nhớ giữ `web\.next`, và đừng xoá khi có tác tử khác đang dựng |
| **Test `tests/test_web_css_gate.py` bị bỏ qua (skip)** | Máy chưa cài thư viện web | `cd web; npm install` rồi chạy lại. Cổng **bỏ qua** chứ không giả vờ xanh — thà không biết còn hơn tin nhầm |

---

## 4. Hai câu phải luôn trả lời được trước khi lên sóng

**"Dữ liệu của tôi đang nằm ở đâu?"**

Đọc dòng `Chế độ kho` trong bảng tóm tắt của `chay_local.py`, hoặc:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health | Select-Object storage_mode, durable
```

* `postgres` + `durable=true` — dữ liệu nằm trong cơ sở dữ liệu, khởi động lại
  không mất gì.
* `memory+snapshot` + `durable=false` — **dữ liệu nằm trong RAM**, chỉ được chụp
  lại mỗi 30 giây vào `data/snapshot/livelift-store.json`. Tiến trình chết đột
  ngột thì mất tối đa 30 giây sự kiện cuối. Đủ cho demo và thi đấu; phiên live
  thật thì bật PostgreSQL trước.

**"Trang chủ có CSS không?"**

```powershell
.venv\Scripts\python scripts\gate_css_web.py
```

Đừng thay câu trả lời này bằng việc liếc mắt qua trình duyệt: trình duyệt có bộ
nhớ đệm, và một trang cũ còn trong cache trông y hệt một trang lành.

---

## 5. Luật chống tranh chấp thư mục build

Nguyên nhân gốc của sự cố "trang vỡ" là **hai tiến trình cùng ghi một thư mục
build**. Luật từ đó:

> Mọi tiến trình `next dev` / `next build` chạy song song **phải** đặt biến
> `LIVELIFT_DIST_DIR` riêng.

Tên đang dùng (chép trong `web/next.config.mjs`, đừng trùng nhau):

| Thư mục | Của ai |
|---|---|
| `web/.next` | máy chủ dev gõ tay (`npm run dev`) |
| `web/.next-chay-local` | `scripts/chay_local.py` |
| `web/.next-gate-css` | `scripts/gate_css_web.py` chạy tay |
| `web/.next-gate-css-pytest` | `tests/test_web_css_gate.py` |
| `web/.next-<việc của bạn>` | mọi tiến trình song song khác |

Ví dụ bật một máy chủ dev thứ hai để chụp ảnh kiểm chứng:

```powershell
$env:LIVELIFT_DIST_DIR = ".next-kiemchung"
cd web; npx next dev -p 3100
```

`web/.gitignore` đã bỏ qua `/.next-*`, nên các thư mục tạm không lọt vào git.

---

## 6. Đọc thêm

| Việc | Tài liệu |
|---|---|
| Dữ liệu được lưu thế nào, ảnh chụp hoạt động ra sao | `docs/luu-tru-du-lieu.md` |
| Bật PostgreSQL bằng một lệnh | `scripts/bat_postgres.py`, `docs/luu-tru-du-lieu.md` |
| Toàn bộ sự cố đã gặp và gate sinh ra từ chúng | `docs/incident-log.md` |
| Kịch bản demo | `docs/demo-vang.md` |
