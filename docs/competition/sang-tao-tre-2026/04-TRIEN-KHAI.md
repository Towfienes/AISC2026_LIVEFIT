# 04 — TRIỂN KHAI, VẬN HÀNH VÀ GIỮ UPTIME 48 GIỜ

*Thực hiện 14/09/2026 trên kho `D:\AISC2026\livelift` tại HEAD `dd66b38` (42 commit, nhánh `main`).
Phạm vi: hạ tầng · triển khai · cấu hình · tài liệu vận hành. KHÔNG chạm logic nghiệp vụ và mô hình
(hai agent khác phụ trách — xem `02-KIEM-TOAN-RUBRIC.md`).*

> **Luật của tài liệu này:** mỗi khẳng định về hệ thống này đều kèm **lệnh đã chạy thật** và
> **kết quả dán nguyên**. Chỗ nào chưa chạy được thì ghi thẳng **"CHƯA KIỂM CHỨNG"** kèm lý do và
> lệnh để kiểm chứng sau. Không có câu nào viết từ trí nhớ.

**Vì sao tài liệu này tồn tại.** `BRIEF-THE-LE.md` §8: *"Sản phẩm phải chạy được trên môi trường
trực tuyến / demo ổn định ít nhất 48 GIỜ trước thời điểm kiểm tra và suốt phiên chấm. Không truy cập
được do lỗi chủ quan → **điểm vận hành có thể bị tính 0**."* Trọng tâm 7 của rubric chấm thẳng
*"khả năng triển khai, mở rộng và duy trì"*. Tính đến hôm nay dự án **chưa có một địa chỉ công khai nào**.

---

## 0. TÓM TẮT ĐIỀU HÀNH

| | Trạng thái |
|---|---|
| Dựng bằng `docker compose up -d` | **CHƯA KIỂM CHỨNG ĐƯỢC trên máy này** — Docker daemon không khởi động (xem §1). Cấu hình đã được soát và sửa; cần một máy có Docker để xác nhận. |
| Đường chạy thay thế (venv, không cần Docker) | **ĐÃ KIỂM CHỨNG, mã thoát 0** — `scripts/chay_local.py` dựng API + web, CSS 63.673 byte, 33 phiên. |
| Địa chỉ công khai | **CHƯA CÓ.** Quy trình dựng đã viết xong tới bước cuối (§4); dừng lại chờ người bấm nút — cần một tài khoản và một tên miền, hai thứ chỉ con người mở được. |
| Phương án hosting khuyến nghị | **Oracle Cloud Always Free, vùng Singapore — 0 đồng, 2 OCPU/12 GB, không ngủ đông, ~35 ms từ TP.HCM.** Dự phòng bắt buộc: Vultr Singapore tính tiền **theo giây** ⇒ **48 giờ chỉ tốn ~17.000 ₫**. Tên miền: đội đủ điều kiện lấy **`.id.vn` MIỄN PHÍ** (Thông tư 64/2025, công dân 18–23 — cả ba bạn 20 tuổi). Chi tiết §3. |
| Bị loại vì ngủ đông | **Render** (ngủ 15 phút + CSDL miễn phí **hết hạn sau 30 ngày rồi xoá**) · **Fly.io** (hết gói miễn phí, bản thử chỉ 2 giờ chạy máy) · **HF Spaces** (Docker Space nay cần PRO 9 USD/th, ngủ sau 48 h, **không có CSDL**) · **Railway Free** (trần 0,5 GB). |
| Chống sập khi demo | **ĐÃ LÀM** — healthcheck cho `api`/`web`/`caddy` (trước đó không có cái nào), trần bộ nhớ, xoay vòng nhật ký, trang lỗi tiếng Việt ở cả 3 lớp. |
| Bảng kiểm một lệnh trước demo | **ĐÃ LÀM VÀ ĐÃ CHẠY** — `scripts/kiem_tra_truoc_demo.py`, 9 đạt / 0 trượt / 2 cảnh báo. |
| Chế độ DEMO an toàn | **ĐÃ KIỂM CHỨNG** — 16 phiên demo, 17 phiên thật, **rò rỉ nhãn cả hai chiều = 0**. |
| Sao lưu | **ĐÃ KIỂM CHỨNG** — 5 bản dump, cả 5 đạt `gzip -t` và mang đúng chữ ký `PGDMP`. |
| Khôi phục | **MỘT NỬA.** Đường ảnh chụp: đã chứng minh bằng phép giết cứng tiến trình (có cả đối chứng âm). Đường `pg_restore`: script đã viết, **chưa chạy được** vì không có Docker/PostgreSQL trên máy này. |
| Bí mật lọt kho mã | **SẠCH** — quét toàn bộ 42 commit, **0 khoá API/token**. `.env` không bị git theo dõi. |
| Lỗ hổng còn lại | **P1 — 12/15 endpoint POST không có xác thực.** Không thuộc phạm vi tôi sửa (logic ứng dụng); đã ghi rõ ở §8 để agent kiểm toán mã xử lý. |

**Ba việc chỉ con người làm được** (chi tiết §12):
1. Mở Docker Desktop bằng quyền quản trị viên rồi chạy lại §2 để xác nhận `docker compose up`.
2. Quyết định nhà cung cấp + đăng ký tài khoản + trỏ tên miền (§3, §4).
3. Quyết định có bịt 12 endpoint ghi trước khi mở ra Internet hay không (§8).

---

## 1. HIỆN TRẠNG ĐO ĐƯỢC

Máy: Windows 11 Pro 10.0.22631 · RAM 15,7 GB · trống C: 17,2 GB, D: 40,4 GB · ảo hoá bật (`HypervisorPresent = True`).

| Thành phần | Đo được | Ghi chú |
|---|---|---|
| Docker CLI | `29.5.3` build `d1c06ef` | Có |
| Docker Compose | `v5.1.4` | Có |
| **Docker daemon** | **KHÔNG CHẠY** | Chi tiết dưới |
| Node / npm | `v24.14.1` / `11.11.0` | Có |
| Python `.venv` | `3.12.6` | `fastapi 0.141.1`, `livelift 0.1.0` (editable) |
| `web/node_modules` | Có, 119 thư mục | Không cần `npm ci` lại |
| PostgreSQL cục bộ | **KHÔNG CÓ** | `psql` không có trên PATH, không có service `*postgres*`, không có `C:\Program Files\PostgreSQL` |
| Bản dựng web | Có | `web/.next-chay-local`, CSS 63.673 byte |

### 1.1. Vì sao Docker không chạy — nguyên nhân gốc, không phải phỏng đoán

Đây là kết luận sau khi bóc từng lớp, không phải "thử lại lần nữa xem sao":

```
$ docker version
Client: Version 29.5.3 … Context: desktop-linux
request returned 500 Internal Server Error for API route and version
http://%2F%2F.%2Fpipe%2FdockerDesktopLinuxEngine/v1.54/version
```

Bóc tiếp:

| Lớp | Kết quả đo | Nghĩa là |
|---|---|---|
| Tiến trình Docker Desktop | 10 tiến trình đang chạy (`com.docker.backend`, `docker-agent`…) | Giao diện đã lên |
| Named pipe `dockerDesktopLinuxEngine` | **CÓ** | Proxy API đã lên |
| WSL distro `docker-desktop` | `Running`, version 2 | Máy ảo đã lên |
| **`dockerd` bên trong WSL** | **KHÔNG CÓ TIẾN TRÌNH NÀO** (`ps -ef \| grep dockerd` rỗng) | **Động cơ chưa bao giờ khởi động** |
| `/var/run/docker.sock` trong WSL | Không tồn tại | Hệ quả của dòng trên |
| `%APPDATA%\Docker\log\vm\dockerd.log` | Không tồn tại | Động cơ chưa từng ghi một dòng log |
| Dịch vụ `com.docker.service` | `Stopped`, StartType `Manual` | **Đây là nút thắt** |
| `Start-Service com.docker.service` | `FAILED: Cannot open com.docker.service service on computer '.'` | Từ chối quyền |
| Phiên hiện tại có quyền quản trị? | **`False`** | Nguyên nhân gốc |

**Kết luận:** động cơ Docker cần dịch vụ đặc quyền `com.docker.service`; dịch vụ ấy chỉ khởi động
được bằng quyền quản trị viên; phiên làm việc này không có quyền đó. Đã đợi tổng cộng **hơn 20 phút**
qua ba vòng thăm dò — không phải chuyện khởi động chậm.

**Cách chữa (người dùng làm, 2 phút):** đóng hẳn Docker Desktop → chuột phải biểu tượng → *Run as
administrator* → đợi biểu tượng chuyển xanh → `docker ps` phải trả về bảng rỗng chứ không phải lỗi 500.

---

## 2. DỰNG TỪ SỐ 0

### 2.1. Đường chính — `docker compose up -d` (CHƯA KIỂM CHỨNG được trên máy này)

Ngăn xếp gồm 7 phân hệ: `db` (TimescaleDB/PG16) · `redis` · `migrate` (chạy một lần) · `api`
(FastAPI) · `web` (Next.js) · `caddy` (cổng vào duy nhất, HTTPS tự động) · `backup` (dump hằng ngày).

Vì không chạy được Docker, tôi **soát tĩnh** thay vì đoán, và sửa những chỗ hỏng tìm được:

| Đã kiểm bằng cách nào | Kết quả |
|---|---|
| Phân tích YAML cả 3 tệp compose bằng `yaml.safe_load` | **Hợp lệ**, 7/7/2 phân hệ |
| Neo YAML `*nhat_ky` bung ra giống hệt nhau ở mọi phân hệ | **Đúng** |
| Biến `STORE_BACKEND=postgres` có mặt trong env của `api` bản prod | **Có** (đây là dòng quyết định dữ liệu sống hay chết — sự cố 25/08) |
| Cân bằng ngoặc `docker/Caddyfile` | 17 mở / 17 đóng |
| Ngoặc nhọn trong trang lỗi Caddy | Chỉ còn đúng một placeholder thật `{err.status_code}` |

> **CHƯA KIỂM CHỨNG và phải làm ngay khi có Docker.** Trước khi tin bất cứ điều gì ở trên:
> ```bash
> docker compose config >/dev/null                                   # compose hợp lệ?
> docker compose run --rm caddy caddy validate --config /etc/caddy/Caddyfile   # Caddyfile hợp lệ?
> ```
> Tôi đã cố ý viết `Caddyfile` bằng cú pháp bảo thủ nhất (bỏ bộ so khớp CEL, bỏ khối `<style>`)
> để giảm rủi ro, nhưng **không có gì thay được một lần `caddy validate` thật**. Nếu lệnh ấy báo
> lỗi: `git checkout -- docker/Caddyfile` là quay về nguyên trạng, ngăn xếp chạy lại như cũ.

### 2.2. Đường thay thế — ĐÃ KIỂM CHỨNG, mã thoát 0

Kho đã sẵn `scripts/chay_local.py`: một lệnh, không cần Docker, dùng `.venv` + kho `memory + ảnh chụp`.

```
$ .venv/Scripts/python scripts/chay_local.py --force --thu-roi-thoat

== (a) Cổng đang bị ai giữ? ==
  ! Cổng 8000 (API) đang bị giữ bởi PID 38196 — python
    ✓ Đã dừng PID 38196
  ! Cổng 3000 (web) đang bị giữ bởi PID 32996 — node
    ✓ Đã dừng PID 32996
== (c) Kho dữ liệu — đo, không đoán ==
  ! KHÔNG có PostgreSQL (không ai nghe 127.0.0.1:5432). Tự chọn kho memory + ảnh chụp…
== (d) API ==
  ✓ /health xanh — storage_mode=memory+snapshot durable=False
== (e) Web + phép thử CSS (sự cố 13/09) ==
  ✓ Trang chủ trả 200 (thư mục build web/.next-chay-local)
  ✓ CSS tải được: /_next/static/css/app/layout.css — 63,673 byte, có --canvas, --brand
== (f) Tóm tắt ==
  Số phiên đang có          33  (thật 17 · demo 16)
  Mọi phép thử ĐẠT.

[exited with code 0]
```

**Hạn chế phải nói rõ** — đường này **KHÔNG bền vững**: `durable=False`, dữ liệu nằm trong RAM,
chỉ được chụp ra `data/snapshot/livelift-store.json` mỗi 30 giây. Mất tối đa 30 giây sự kiện cuối
nếu tiến trình chết đột ngột. **Đủ cho một buổi demo trước hội đồng; KHÔNG đủ cho phiên live thật.**
Ứng dụng không hỗ trợ SQLite — chỉ có `memory` và `postgres` — nên không có đường thứ ba.

---

## 3. SO SÁNH PHƯƠNG ÁN HOSTING

### 3.1. Bộ lọc: bốn điều kiện, thiếu một là loại

Thể lệ §8 biến một tiêu chí kỹ thuật bình thường thành tiêu chí **loại**:

1. **KHÔNG NGỦ ĐÔNG.** Đây là tử huyệt. Một dịch vụ ngủ sau 15 phút không ai truy cập sẽ **chắc chắn**
   đang ngủ khi hội đồng mở link — vì hội đồng mở nó lúc không ai dùng. "Chỉ chậm 1 phút thôi" vẫn là
   một sản phẩm không truy cập được tại thời điểm kiểm tra.
2. **Có PostgreSQL** chạy liên tục, không hết hạn giữa chừng.
3. **Có HTTPS.**
4. **Chạy được nhiều tuần**, không chỉ vài ngày dùng thử.

### 3.2. Phát hiện làm thay đổi cả bài toán: không cần mua cả tháng

Cả đề bài lẫn phản xạ thông thường đều hỏi "bao nhiêu tiền **một tháng**". Nhưng **DigitalOcean và
Vultr tính tiền theo giây** (DigitalOcean chính thức chuyển sang tính theo giây, tối thiểu 60 giây,
từ 01/01/2026). Thứ đội cần là **48 giờ ổn định quanh buổi chấm**, không phải một tháng:

| Máy | Giá niêm yết | **Giá thật cho 48 giờ** |
|---|---|---|
| Vultr `vc2-1c-2gb` Singapore (1 vCPU / 2 GB) | 10 USD/tháng | **~0,67 USD ≈ 17.000 ₫** |
| DigitalOcean 2 GB Singapore (SGP1) | 12 USD/tháng | **~0,80 USD ≈ 21.000 ₫** |

**Mười bảy nghìn đồng** cho cả đội, rẻ hơn một tô phở. Câu "đội sinh viên không ngân sách" vì thế
không còn là ràng buộc thật — cái đắt ở đây là **rủi ro**, không phải tiền. Và đây cũng là lý do
phương án trả tiền đáng được xét ngang hàng chứ không bị loại từ vòng gửi xe.

### 3.3. Bảng so sánh

*Số liệu tra ngày 14/09/2026 trên trang chính chủ (chi tiết nguồn §3.8). Tỷ giá 1 USD = 26.000 ₫
(Wise giữa thị trường 25.980 ngày 14/09/2026).*

| # | Phương án | Chi phí thật | **Ngủ đông?** | RAM | PostgreSQL | Độ trễ từ TP.HCM | Độ khó |
|---|---|---|---|---|---|---|---|
| 1 | **Oracle Cloud Always Free** (ARM A1, Singapore) | **0 ₫ vĩnh viễn** | **KHÔNG** | **12 GB**, 2 OCPU | Tự chạy trong compose | **~35 ms** | Khó |
| 2 | **Vultr `vc2-1c-2gb`** Singapore | 10 USD/th · **17.000 ₫ cho 48 h** | KHÔNG | 2 GB | Tự chạy | **~35 ms** | Dễ |
| 3 | **DigitalOcean 2 GB** SGP1 | 12 USD/th · **21.000 ₫ cho 48 h** | KHÔNG | 2 GB | Tự chạy | **~35 ms** | Dễ |
| 4 | **VNPT Cloud SMC03** — dùng thử | **0 ₫ trong 7 ngày** | KHÔNG | **4 GB**, 2 vCPU | Tự chạy | **~5–15 ms** | Dễ |
| 5 | BizFly Gói 4 (trả tháng) | 240.000 ₫/tháng | KHÔNG | 4 GB | Tự chạy | ~5–15 ms | Dễ |
| 6 | Hetzner CPX12 Singapore | 17,99 USD/th (~483.000 ₫) | KHÔNG | 2 GB | Tự chạy | ~35 ms | Dễ |
| 7 | **Render** miễn phí | 0 ₫ | **CÓ — ngủ sau 15 phút, dậy ~1 phút** | 512 MB | **Hết hạn sau 30 ngày rồi XOÁ** | — | Dễ |
| 8 | **Railway** gói Free | 0 ₫ (1 USD tín dụng/th) | Không ép ngủ | **Trần 0,5 GB** | Trả phí | — | Dễ |
| 9 | **Fly.io** | **Không còn gói miễn phí** | Máy thử tự dừng sau 5 phút | — | Postgres từ 38 USD/th | ~35 ms | TB |
| 10 | **Hugging Face Spaces** miễn phí | Docker Space **cần PRO 9 USD/th** | **CÓ** — ngủ sau 48 h | 16 GB | **KHÔNG CÓ** | — | Khó |
| 11 | **Cloudflare Free** (lớp biên) | **0 ₫** | — | — | — | PoP tại VN | Dễ |

### 3.4. Loại — và vì sao (mỗi dòng một lý do đủ để loại một mình)

- **Render** — dịch vụ web miễn phí **ngủ sau đúng 15 phút** không có lưu lượng, dậy mất ~1 phút. Và
  PostgreSQL miễn phí **hết hạn 30 ngày sau khi tạo**, thêm 14 ngày ân hạn rồi **xoá cả dữ liệu**.
  Từ nay tới Chung kết (20–22/11) dài hơn 30 ngày ⇒ CSDL chết **trước** buổi chấm.
- **Fly.io** — **không còn gói miễn phí**. Bản dùng thử là *"2 giờ chạy máy **hoặc** 7 ngày, cái nào
  tới trước"*. 2 giờ không thể phủ 48 giờ. Postgres có quản lý từ 38 USD/tháng.
- **Hugging Face Spaces** — ba rào chắn độc lập: (a) tạo Docker Space **bắt buộc tài khoản PRO
  9 USD/tháng**; (b) hệ tệp không bền và tính năng lưu trữ bền **đã bị gỡ**; (c) chỉ cho ra cổng
  80/443/8080 ⇒ **không nối được PostgreSQL ngoài ở cổng 5432**. Dùng được cho **demo riêng phần mô
  hình NLP**, không dùng được cho cả hệ thống.
- **Railway Free** — trần cứng **0,5 GB RAM**, không chứa nổi ngăn xếp 2 GB; tín dụng 1 USD/tháng
  không đủ 48 giờ. Gói Hobby 5 USD chạy được nhưng **bắt buộc thẻ trả sau**.
- **Hetzner** — dòng rẻ nổi tiếng (CX/CAX ~4–6 EUR) **chỉ có ở châu Âu**, hiện **đang báo hết hàng**,
  và cách TP.HCM **217–239 ms**. Bản Singapore (CPX12) là **lựa chọn Singapore ĐẮT NHẤT** trong bảng
  và chỉ kèm 0,5 TB lưu lượng. Giá Hetzner đã tăng **hai lần** trong năm 2026.

### 3.5. Sửa một hiểu nhầm về Oracle — và nói rõ rủi ro thật

Ban đầu tôi định cảnh báo rằng "Oracle thu hồi máy bỏ không" là mối đe doạ cho buổi demo. **Đọc kỹ
tài liệu chính thức thì không phải vậy** — và tôi sửa lại cho đúng, vì đây là chỗ dễ khuyên sai:

> *"Oracle will deem … instances as idle if, **during a 7-day period**, the following are true:
> CPU utilization for the 95th percentile is less than 20%; Network utilization is less than 20%;
> Memory utilization is less than 20%."*

Cả **ba** điều kiện phải đúng **đồng thời** suốt **7 ngày liền**. Một buổi demo 48 giờ **không thể**
kích hoạt chính sách này. Đây là quy tắc **thu hồi tài nguyên bỏ hoang**, không phải đồng hồ ngủ đông.

**Rủi ro thật của Oracle nằm ở chỗ khác, và nó nghiêm trọng hơn:** ngày **15/06/2026 Oracle đã CẮT
ĐÔI** hạn mức Always Free ARM — từ 4 OCPU/24 GB xuống **2 OCPU/12 GB** — **không thông báo công khai**
(chỉ sửa tài liệu), rồi **tự động chấm dứt** những máy vượt hạn mức từ **18/08/2026**. Nhiều người
dùng phản ánh **mất luôn cả ổ đĩa khởi động và dữ liệu**. Bài học không phải "máy sẽ bị thu hồi vì
rảnh", mà là **"nhà cung cấp có thể đổi luật dưới chân mình với rất ít thông báo"**.

Ngoài ra Oracle cần **thẻ tín dụng/ghi nợ quốc tế không phải thẻ trả trước, không phải thẻ PIN**
(thẻ Visa debit của Techcombank/TPBank/VPBank thường được; **MoMo và thẻ ảo thì không**), vùng nhà
(home region) **chọn một lần không đổi được** — phải chọn Singapore, và máy ARM A1 hay báo hết chỗ.

### 3.6. KHUYẾN NGHỊ

> **Chính: Oracle Cloud Always Free, vùng nhà Singapore** — 2 OCPU / 12 GB ARM, **0 đồng vĩnh viễn**,
> không ngủ đông, ~35 ms từ TP.HCM, chạy trọn ngăn xếp `docker compose` kể cả PostgreSQL và Redis.
> **Dựng NGAY, đừng đợi tuần thi** — khâu chậm là xác minh tài khoản và chờ máy ARM có chỗ.
>
> **Dự phòng bắt buộc: 17.000 ₫.** Vì rủi ro "đổi luật" ở §3.5 là thật, phải có đường lùi. Vultr
> `vc2-1c-2gb` Singapore tính tiền theo giây ⇒ **48 giờ tốn ~17.000 ₫**. Dựng thử một lần trước mốc
> T-48 giờ, xác nhận chạy được, rồi xoá. Khi cần thật thì dựng lại trong 15 phút.
>
> **Lớp biên: Cloudflare gói miễn phí** đặt trước bất kể chọn máy nào.

**Vì sao VPS mà không phải PaaS**, ngoài chuyện ngủ đông: kho mã **đã có sẵn** `docker-compose.yml`
7 phân hệ và một `Caddyfile` tự xin chứng chỉ. Trên VPS, toàn bộ công sức ấy chạy nguyên xi bằng một
lệnh. Trên PaaS phải xé ngăn xếp thành từng dịch vụ riêng, mua CSDL riêng, dựng lại định tuyến —
nhiều việc hơn, nhiều chỗ hỏng hơn, mà vẫn không giải quyết được chuyện ngủ đông. **Tận dụng Caddy
sẵn có là phương án ít rủi ro nhất.**

**Nếu không có thẻ quốc tế:** **VNPT Cloud gói SMC03 (2 vCPU / 4 GB) cho dùng thử 7 ngày miễn phí**,
đặt tại Việt Nam (~5–15 ms), SLA 99,99 %, thanh toán nội địa. Bảy ngày phủ thừa 48 giờ.

**Cloudflare gói miễn phí** cho **đúng một** quy tắc giới hạn tốc độ (khoá theo IP, cửa sổ cố định
10 giây, chặn 10 giây, chỉ khớp theo Path). Thô, nhưng đủ dựng một lá chắn ngoài cho `POST /api/*`
**mà không phải đụng một dòng mã nào** — đúng lỗ hổng §8.3 mà tôi không được phép tự sửa. Kèm theo là
chống DDoS không giới hạn và giấu IP thật của máy chủ.

> **BẪY KỸ THUẬT phải biết trước khi bật Cloudflare.** Cloudflare cắt TLS ở biên, nên thử thách
> **TLS-ALPN-01 KHÔNG hoạt động** sau đám mây cam — mà đó lại là thứ Caddy thử theo mặc định. Cổng 80
> vẫn được proxy nên HTTP-01 vẫn chạy. **Cách sạch nhất:** đặt chế độ SSL/TLS **"Full (strict)"** và
> dùng **chứng chỉ Cloudflare Origin CA** (miễn phí ở mọi gói), ghim thẳng vào Caddy:
> ```
> tls /duong/dan/cert.pem /duong/dan/key.pem
> ```
> Làm vậy thì **ACME không chạy nữa** — không phụ thuộc cổng 80, không có chuyện gia hạn 90 ngày
> hỏng giữa kỳ thi. Người xem vẫn nhận chứng chỉ Universal SSL miễn phí ở biên.

### 3.7. Tên miền — đội này đủ điều kiện lấy MIỄN PHÍ một tên miền thật

Đây là phát hiện đáng giá nhất của phần khảo sát, và nó **trúng đúng đội này**:

> **Thông tư 64/2025/TT-BTC, Điều 3** (ban hành 30/06/2025): *"Kể từ ngày Thông tư này có hiệu lực
> thi hành đến hết ngày **31 tháng 12 năm 2026**: **Công dân Việt Nam có độ tuổi từ đủ 18 đến 23**
> đăng ký sử dụng tên miền **'id.vn'** thực hiện nộp phí **từ năm thứ 03 trở đi**."*

Cả ba thành viên sinh năm 2006 → **20 tuổi** → **đúng khoảng 18–23**. Chính sách còn hiệu lực tới
**31/12/2026**, tức là còn hiệu lực suốt kỳ thi. Đăng ký qua `guongmatso.tenmien.vn`, cần **eKYC bằng
CCCD** + ảnh chân dung trực tiếp, mỗi công dân một tên miền. Nhà đăng ký: Mắt Bão, BKNS, iNET, Nhân
Hoà, PA Việt Nam, TinoHost, VinaHost, ESC, GMO.

Hơn hẳn mọi lựa chọn khác: là **tên miền thật** (không phải tên miền phụ đi mượn), miễn phí hợp pháp,
trông chuyên nghiệp trước hội đồng, và **không phụ thuộc vào việc GitHub Student Pack có duyệt kịp hay không**.

**Dự phòng 5 phút: DuckDNS** (`<tên>.duckdns.org`) — miễn phí, đăng nhập bằng Google/GitHub, và quan
trọng là **`duckdns.org` nằm trong Public Suffix List**, nên mỗi tên miền phụ có **hạn ngạch chứng chỉ
Let's Encrypt riêng** (50 chứng chỉ/tuần). Có mô-đun Caddy chính thức `caddy-dns/duckdns` nếu cần
thử thách DNS-01 (dùng khi mạng chặn cổng 80 — chuyện hay gặp ở ký túc xá và mạng gia đình Việt Nam).

> **TRÁNH `nip.io` và `sslip.io`** — **không** nằm trong Public Suffix List, nên **mọi người dùng
> chung một hạn ngạch**. Tháng 02/2026 sslip.io đã chạm trần: *"too many certificates (50000) already
> issued for 'sslip.io' in the last 168h"*.
>
> **Không dùng được:** tên miền `.me` miễn phí của Namecheap trong GitHub Student Pack (ưu đãi giới
> hạn theo quốc gia, không có Việt Nam). **Freenom (.tk/.ml/.ga/.cf) đã chết** như một lựa chọn miễn
> phí từ 2024.

**Về GitHub Student Pack:** vẫn tồn tại, nhưng **DigitalOcean đã RỜI chương trình từ 01/08/2026 và
mọi tín dụng — kể cả đã nhận — đều hết hạn**. Bất kỳ hướng dẫn nào bảo dùng 200 USD DigitalOcean đều
đã cũ. Ưu đãi đám mây còn dùng được: **Azure for Students 100 USD, không cần thẻ tín dụng**. Đăng ký
song song, **nhưng đừng xây kế hoạch dựa vào nó** — khâu duyệt năm 2026 đã siết, thường chờ 20+ ngày.
Lưu ý: *không bắt buộc email `.edu`* — ảnh thẻ sinh viên **có ghi ngày còn hiệu lực** là đủ; nhưng nếu
đã có sinh viên TDTU được duyệt bằng email trường thì người sau **bắt buộc** phải dùng email trường.

### 3.8. Nguồn

Toàn bộ số liệu tra ngày **14/09/2026** trên trang chính chủ:

- Oracle hạn mức Always Free + nguyên văn chính sách thu hồi máy rảnh:
  [docs.oracle.com — Free Tier](https://docs.oracle.com/iaas/Content/FreeTier/freetier.htm)
- Oracle cắt đôi hạn mức 15/06/2026, chấm dứt máy vượt hạn từ 18/08/2026:
  [InfoQ (07/2026)](https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/)
- Render ngủ 15 phút, Postgres miễn phí hết hạn 30 ngày:
  [Render docs — free tier](https://unanswered.io/guide/render-free-tier-details) ·
  [Render pricing](https://kuberns.com/blogs/render-pricing/)
- Cloudflare gói Free có **1** quy tắc giới hạn tốc độ, cửa sổ 10 giây:
  [Cloudflare WAF — rate limiting](https://developers.cloudflare.com/waf/rate-limiting-rules/) ·
  [tham số](https://developers.cloudflare.com/waf/rate-limiting-rules/parameters/)
- DigitalOcean rời GitHub Student Pack 01/08/2026:
  [aistudentdiscount](https://aistudentdiscount.com/digitalocean-github-student-developer-pack-credits/) ·
  [education.github.com/pack](https://education.github.com/pack)
- Caddy + DuckDNS (DNS-01): [caddy-dns/duckdns](https://github.com/caddy-dns/duckdns)
- Tên miền `.id.vn` miễn phí cho công dân 18–23: Thông tư 64/2025/TT-BTC Điều 3 ·
  chương trình [guongmatso.tenmien.vn](https://guongmatso.tenmien.vn)
- Độ trễ TP.HCM → Singapore 35,41 ms: ma trận ping [WonderNetwork](https://wondernetwork.com/pings)
- Giá Vultr: lấy từ **API công khai của chính Vultr** (`api.vultr.com/v2/plans`) vì trang giá HTML
  trả HTTP 403 · Giá DigitalOcean: [trang giá chính chủ](https://www.digitalocean.com/pricing/droplets)

> **CHƯA XÁC MINH ĐƯỢC** (ghi ra thay vì lấp liếm): trang tiếp thị của Oracle chặn truy cập tự động
> (HTTP 403) nên mọi số Oracle ở trên lấy từ `docs.oracle.com`; việc nâng lên Pay-As-You-Go có chặn
> được thu hồi hay không (diễn đàn đồn nhiều, **tài liệu Oracle không nói**); "thu hồi" là dừng hay
> xoá hẳn; danh sách quốc gia được Oracle/Azure chấp nhận có Việt Nam hay không; `tdtu.edu.vn` có nằm
> trong danh sách miền học thuật của GitHub hay không; giới hạn số tên miền mỗi tài khoản DuckDNS;
> hình thức thanh toán của VNPT Cloud/BizFly.

## 4. QUY TRÌNH TRIỂN KHAI TỪNG BƯỚC

*Mỗi bước có một **phép thử** đi kèm. Không đạt thì dừng lại sửa, đừng đi tiếp — một bước hỏng
mà bỏ qua sẽ hiện ra ở bước thứ năm dưới dạng một lỗi không liên quan gì.*

**Tôi đã chuẩn bị mọi thứ tới đây và DỪNG LẠI.** Các bước dưới cần một tài khoản, một thẻ thanh toán
và một tên miền — ba thứ chỉ con người mở được. Tôi không tự đăng ký dịch vụ, không tự mua gì, và
không đẩy gì lên Internet.

### Bước 0 — Trước khi thuê máy (làm trên máy mình, 10 phút)

Việc đầu tiên là xoá cái vết "chưa từng chạy thật" ở §12 (rủi ro số 1):

```bash
# Mở Docker Desktop bằng QUYỀN QUẢN TRỊ trước (xem §1.1)
docker ps                                  # phải ra bảng rỗng, KHÔNG phải lỗi 500
docker compose config >/dev/null           # compose hợp lệ?
docker compose run --rm caddy caddy validate --config /etc/caddy/Caddyfile
docker compose up -d --build
docker compose ps                          # mọi phân hệ healthy, migrate exited (0)
curl -s http://localhost/api/health         # "durable": true
python scripts/kiem_tra_truoc_demo.py --goc http://localhost
docker compose down                        # KHÔNG có -v
```

> **Phép thử:** `kiem_tra_truoc_demo.py` trả **mã thoát 0**, và `/health` báo `"durable": true`
> (trên máy mình hiện tại nó báo `false` vì không có Postgres — qua Docker thì phải thành `true`).
> Nếu `caddy validate` báo lỗi: `git checkout -- docker/Caddyfile` rồi báo lại, đừng sửa mò.

### Bước 1 — Lấy máy

Ubuntu 24.04 LTS, **≥ 2 GB RAM** (khuyến nghị 4 GB — xem bảng trần bộ nhớ ở §5.2), vùng
**Singapore**. Bật khoá SSH, tắt đăng nhập bằng mật khẩu.

Theo §3.6: **Oracle Always Free** là đường chính. Hai chỗ hay vấp, biết trước thì đỡ mất buổi:

- **Vùng nhà (home region) chọn một lần, KHÔNG đổi được** → chọn **Singapore** ngay khi tạo tài khoản.
  Máy Always Free chỉ tồn tại ở vùng nhà.
- **Hai lớp tường lửa phải mở cả hai**, và đây là chỗ gần như ai cũng vấp lần đầu:
  (a) *Security List / NSG* của VCN — thêm luật vào `0.0.0.0/0` cổng TCP 80 và 443;
  (b) **tường lửa trong máy** — ảnh Ubuntu của Oracle có sẵn luật `iptables`, phải mở thêm rồi lưu
  bằng `netfilter-persistent`. Mở mỗi lớp (a) rồi ngồi đoán vì sao trang không lên là kịch bản kinh điển.
- Máy ARM A1 hay báo *"Out of host capacity"* — thử lại nhiều lần hoặc đổi Availability Domain.

> **Phép thử:** `ssh <user>@<ip>` vào được mà không hỏi mật khẩu, **và** từ máy khác
> `curl -v http://<ip>` không bị treo (chứng tỏ cổng 80 đã thông **cả hai** lớp tường lửa).
> Chưa thông cổng 80 thì đừng sang bước 2.

### Bước 2 — Trỏ tên miền

Tạo bản ghi `A` từ tên miền về IP của máy chủ. Tên miền lấy ở đâu: xem §3.7 — đội **đủ điều kiện
lấy `.id.vn` miễn phí** (Thông tư 64/2025, công dân 18–23); dự phòng 5 phút là DuckDNS.

> **Phép thử:** `dig +short <tên-miền>` trả về **đúng** IP của máy chủ. Chưa đúng thì **đừng** sang
> bước 4 — Caddy sẽ xin chứng chỉ thất bại và Let's Encrypt **có giới hạn số lần thử** (5 lần hỏng
> xác thực mỗi giờ), hỏng nhiều lần là bị khoá.
>
> **Nếu mạng chặn cổng 80** (ký túc xá, mạng gia đình Việt Nam hay bị): thử thách HTTP-01 **không
> chạy được**. Đường thoát là DNS-01 với mô-đun `caddy-dns/duckdns`, hoặc dùng chứng chỉ Cloudflare
> Origin CA như §3.6 — cách sau bỏ hẳn ACME nên không cần cổng 80 chút nào.

### Bước 3 — Cài Docker và lấy mã nguồn

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER && exit      # đăng nhập lại cho nhóm có hiệu lực
git clone https://github.com/bminhnemhoi/AISC2026_LIVEFIT.git livelift && cd livelift
```

> **Phép thử:** `docker compose version` chạy được **mà không cần `sudo`**.

### Bước 4 — Viết `.env` (bước dễ sai nhất)

```bash
cp .env.example .env && nano .env
```

Bảy dòng phải đúng — sai một dòng là hỏng theo kiểu khó chẩn đoán:

| Biến | Giá trị | Sai thì sao |
|---|---|---|
| `POSTGRES_PASSWORD` | chuỗi ngẫu nhiên mạnh (`openssl rand -base64 24`) | compose **từ chối khởi động** (fail-closed — đúng) |
| `DOMAIN` | `livelift.example.com` (**không** kèm `https://`) | Caddy không xin được chứng chỉ |
| `LIVELIFT_ENV` | `prod` | — |
| `NEXT_PUBLIC_API_URL` | `https://<tên-miền>/api` | **Trình duyệt gọi sai địa chỉ API, trang trắng** |
| `NEXT_PUBLIC_PUBLIC_API_BASE` | `https://<tên-miền>` | Shortlink `/r/` in ra sai địa chỉ |
| `CORS_ORIGINS` | `https://<tên-miền>` | Trình duyệt bị chặn nếu tách tên miền |
| `INGEST_TOKEN` | chuỗi ngẫu nhiên mạnh (`openssl rand -base64 32`) | **Để trống là tắt xác thực cho cả 15 endpoint ghi** (§8.3) |
| `PUBLIC_DEMO_WRITES` | `true` cho bản cho giám khảo · `false` cho máy chạy thí nghiệm thật | `true`: khách bấm thử được trên phiên demo; `false`: khoá sạch đường ghi |

> **Cái bẫy đã dính một lần:** hai biến `NEXT_PUBLIC_*` được **nhúng vào bundle LÚC BUILD**. Sửa
> `.env` xong mà không dựng lại `web` thì bundle cũ vẫn trỏ về `localhost`. Bước 5 đã có `--build`
> nên không sao, nhưng **mỗi lần đổi hai biến ấy về sau đều phải `docker compose build web` lại**.

### Bước 5 — Dựng

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

> **Phép thử:** `docker compose ps` — mọi phân hệ `healthy`, `migrate` ở trạng thái `exited (0)`.
> `migrate` không `exited (0)` thì `api` sẽ **không bao giờ khởi động** (`depends_on:
> service_completed_successfully`) — đọc `docker compose logs migrate`.

### Bước 6 — Kiểm chứng công khai

```bash
curl -s https://<tên-miền>/api/health        # "durable": true, "storage_ok": true
curl -X POST https://<tên-miền>/api/demo/seed-vang    # nạp dữ liệu mẫu
python scripts/kiem_tra_truoc_demo.py --goc https://<tên-miền> --khat-khe
```

> **Phép thử:** mã thoát **0** ở chế độ `--khat-khe`. Ở đây **không còn** hai cảnh báo của §5.4:
> `durable` phải `true` (đã có Postgres) và header bảo mật phải đủ (đã có Caddy). Còn cảnh báo nào
> tức là một trong hai thứ ấy chưa thật sự hoạt động.

### Bước 7 — Chốt lại

1. Ghim ảnh bằng digest (hướng dẫn ngay trong `docker-compose.prod.yml`).
2. Chạy thử khôi phục: `python scripts/khoi_phuc_sao_luu.py` → dán kết quả vào §9.
3. Bật Cloudflare (gói miễn phí): trỏ nameserver, bật proxy (đám mây cam), đặt SSL/TLS
   **Full (strict)**, tạo **chứng chỉ Origin CA** và ghim vào Caddy (§3.6 — làm vậy ACME không chạy
   nữa, hết lo cổng 80 và hết lo gia hạn giữa kỳ thi), rồi thêm **một** quy tắc giới hạn tốc độ
   cho `POST /api/*`.
4. Đăng ký UptimeRobot (miễn phí) trỏ vào `https://<tên-miền>/api/health`, 5 phút/lần.
5. **Dựng thử đường dự phòng 17.000 ₫** (§3.6): tạo một máy Vultr Singapore, chạy hết Bước 3–6 trên
   đó, xác nhận lên được, rồi **xoá máy**. Mục đích không phải để nó chạy, mà để biết chắc 15 phút
   dựng lại là làm được — lúc cần thì không còn thời gian học.
6. Mở link bằng **4G điện thoại**, không phải wifi phòng.

Từ lúc bước 7 xong, đồng hồ 48 giờ bắt đầu chạy — và §11 nói rõ: **không ai được đụng vào máy chủ nữa**.

---

## 5. CHỐNG SẬP KHI DEMO

### 5.1. Healthcheck — trước hôm nay `api`, `web`, `caddy` KHÔNG có cái nào

Đây là lỗ hổng thật: `restart: unless-stopped` chỉ dựng lại container khi **tiến trình thoát**.
Một tiến trình **treo** (còn sống, không trả lời) thì Docker không biết, và `docker compose ps` vẫn
hiện `Up` — đúng kiểu hỏng khó chịu nhất giữa buổi chấm.

| Phân hệ | Healthcheck | Ghi chú thiết kế |
|---|---|---|
| `db` | `pg_isready` | có sẵn |
| `redis` | `redis-cli ping` | có sẵn |
| **`api`** | **MỚI** — `python -c urllib…/health` | Ảnh `python:3.11-slim` **không có curl/wget**, nên dùng chính Python |
| **`web`** | **MỚI** — `node -e http.get('/')` | Ảnh `node:20-alpine` cũng không có curl |
| **`caddy`** | **MỚI** — `wget http://127.0.0.1:2019/config/` | Hỏi **admin API của chính Caddy**, không hỏi cổng 80 |

Hai quyết định thiết kế đáng nói, vì làm ngược lại sẽ gây hại:

**(a) Healthcheck của `api` cố ý KHÔNG phán xét kho dữ liệu.** `/health` luôn trả 200 kể cả khi
suy giảm. Nếu để healthcheck đỏ khi PostgreSQL chết thì Docker sẽ đánh dấu `api` unhealthy — nhưng
khởi động lại `api` **không sửa được** một cơ sở dữ liệu chết, chỉ tạo vòng lặp restart và làm mất
luôn trang báo lỗi tiếng Việt. Sức khoẻ kho là việc của `/health.durable` và của bảng kiểm §5.4.

**(b) Healthcheck của `caddy` hỏi admin API chứ không hỏi cổng 80.** Cổng 80 phản ánh sức khoẻ của
`api`/`web` phía sau: `web` chết là `wget` nhận 503 và Caddy bị đánh dấu unhealthy **oan**, trong khi
nó đang làm đúng việc của mình là phục vụ trang lỗi. Cổng 2019 chỉ nghe trong container, không ra ngoài.

### 5.2. Trần tài nguyên và xoay vòng nhật ký — `docker-compose.prod.yml` (MỚI)

Hai thứ này quyết định máy chủ sống hay chết sau 48 giờ, và đều **chưa có** trước hôm nay.

**Xoay vòng nhật ký.** Mặc định Docker ghi nhật ký `json-file` **không giới hạn**. Một phiên live
sinh hàng nghìn dòng; chạy vài tuần là ổ đĩa VPS đầy, và **khi ổ đầy thì PostgreSQL dừng ghi trước
khi có ai kịp nhận ra**. Đây là cách chết âm thầm hay gặp nhất của máy chủ demo dài ngày — và nó rơi
đúng vào chữ "lỗi chủ quan" của thể lệ. Nay: `max-size 10m` × `max-file 3` × 7 phân hệ ⇒ trần cứng ~180 MB.

**Trần bộ nhớ.** Không có trần thì một rò rỉ bộ nhớ ăn hết RAM và OOM-killer của Linux chọn nạn nhân
theo điểm số — thường là PostgreSQL, phân hệ đắt nhất. Có trần thì container gây chuyện tự chết một
mình và `restart: unless-stopped` dựng lại.

| Phân hệ | Trần (VPS 4 GB) | Gợi ý cho VPS 2 GB |
|---|---|---|
| `db` | 1 g | 768 m |
| `api` | 768 m | 512 m |
| `web` | 384 m | 320 m |
| `backup` | 256 m | 192 m |
| `redis` | 192 m (`maxmemory 150mb`, `allkeys-lru`) | 128 m (`maxmemory 96mb`) |
| `caddy` | 128 m | 96 m |
| **Tổng** | **~2,7 GB** | **~2,0 GB** |

> Con số là **điểm khởi đầu có căn cứ, chưa phải số đo**. Sau 24 giờ chạy thật phải `docker stats`
> rồi siết lại cho khớp. Ghi rõ ở đây để không ai tưởng đây là kết quả đo.

`redis` đặt `maxmemory` **thấp hơn** trần container để nó tự dọn khoá cũ theo LRU thay vì bị
OOM-killer bắn chết — redis ở đây là bộ đệm, kho bền vững là PostgreSQL.

### 5.3. Trang lỗi tử tế thay vì vết ngăn xếp — ba lớp

Trước hôm nay `web/src/app/` **không có** `error.tsx`, `global-error.tsx` hay `not-found.tsx`. Một
lỗi render bất kỳ rơi xuống màn hình mặc định của Next: bản dev in **nguyên vết ngăn xếp** (đường dẫn
tệp, tên hàm nội bộ), bản prod in một trang tiếng Anh trống trơn. Cả hai đều không được phép hiện ra
trước hội đồng, và vết ngăn xếp còn là rò rỉ thông tin (trọng tâm 8).

| Lớp | Tệp | Bắt cái gì |
|---|---|---|
| Cổng vào | `docker/Caddyfile` → `handle_errors` | `api`/`web` chết hoặc đang khởi động lại (502/503) |
| Gốc ứng dụng | `web/src/app/global-error.tsx` (MỚI) | Lỗi trong chính `layout.tsx` |
| Từng trang | `web/src/app/error.tsx` (MỚI) | Lỗi render của một trang |
| Đường dẫn lạ | `web/src/app/not-found.tsx` (MỚI) | 404, kể cả shortlink đã hết hạn |

Chi tiết đáng nói:

- **Trang lỗi của Caddy tự tải lại sau 10 giây** (`<meta http-equiv="refresh">`), nên khi container
  hồi phục thì màn hình tự trở lại — hội đồng không phải bấm gì.
- **`global-error.tsx` không dùng một lớp Tailwind nào.** Nếu lỗi xảy ra trước khi CSS kịp nạp
  (đúng kịch bản sự cố 13/09: `.next/static/css` rỗng, `layout.css` trả 404) thì lớp Tailwind vô
  dụng. Toàn bộ màu và khoảng cách đặt thẳng bằng `style` nội tuyến, lấy đúng token của `globals.css`.
- **Trang lỗi của Caddy cũng không có khối `<style>`.** Caddy thay thế placeholder `{...}` **ngay cả
  bên trong heredoc**, nên một khai báo CSS thông thường sẽ bị đọc nhầm thành placeholder và trang
  lỗi hỏng đúng lúc cần nó nhất.
- Người dùng chỉ thấy `error.digest` — mã băm do Next sinh, tra được trong log máy chủ mà **không
  tiết lộ gì về mã nguồn**.

### 5.4. Bảng kiểm một lệnh — `scripts/kiem_tra_truoc_demo.py` (MỚI)

Kho đã có `chay_local.py` (khởi động), `gate_css_web.py` (CSS), `kiem_chung_ben_vung.py` (bền vững)
— mỗi cái soi một mảnh. Cái còn thiếu là một lệnh **hỏi một hệ thống ĐANG CHẠY** đúng những câu mà
giám khảo sẽ vô tình kiểm hộ trong 5 phút đầu. Script này không làm lại việc của ba cái kia.

13 phép thử, trong đó **11 chạy ở mọi lần**: API trả lời · kho bền vững · kho đang trả lời · trang có
dữ liệu để xem · nhãn DEMO/THẬT · trang chủ · CSS · tuyến shortlink `/r/` · header bảo mật · sao lưu ·
bí mật ngoài kho mã. Hai phép thử còn lại chỉ hiện khi có nghĩa: **tốc độ** (chỉ báo khi trang chủ
chậm hơn 1500 ms) và **HTTPS** (chỉ khi kiểm một địa chỉ công khai bằng `--goc`).

Mỗi phép thử nói ba điều: **đo được gì · ngưỡng nào · sửa ra sao**. Cái gì không đo được thì báo
**KHÔNG ĐO ĐƯỢC**, không báo ĐẠT.

```
$ .venv/Scripts/python scripts/kiem_tra_truoc_demo.py

-- Máy chủ API --
  ✓ API trả lời: /health trả 200 sau 12 ms
  ! Kho bền vững: storage_mode=memory+snapshot, durable=FALSE — dữ liệu nằm trong RAM
  ✓ Kho đang trả lời: storage_ok=true, ping 0 ms
-- Dữ liệu và nhãn DEMO/THẬT --
  ✓ Trang có dữ liệu để xem: 33 phiên trong kho (thật 17 · demo 16)
  ✓ Nhãn DEMO/THẬT: mode=mixed — giao diện hiện 'THẬT + DEMO', từng phiên có nhãn riêng
-- Giao diện web --
  ✓ Trang chủ: trả 200 sau 84 ms, 17,943 byte
  ✓ CSS của trang chủ: 63,673 byte qua 1 tệp, có --canvas, --brand
-- Tuyến đo lường --
  ✓ Tuyến shortlink /r/: mã lạ trả 404 đúng như mong đợi (tuyến sống)
-- Bảo mật và vận hành --
  ! Header bảo mật: thiếu X-Content-Type-Options, X-Frame-Options, Referrer-Policy
  ✓ Sao lưu cơ sở dữ liệu: livelift-2026-09-13.dump.gz — 2,039,315 byte, 27.8 giờ tuổi (5 bản)
  ✓ Bí mật ngoài kho mã: .env không bị git theo dõi (đã có trong .gitignore)

  9 đạt · 0 trượt · 2 cảnh báo · 0 không đo được
  SẴN SÀNG LÊN SÓNG.
[exit 0]
```

Hai cảnh báo đều **đúng và mong đợi** trên đường chạy không-Docker: không có PostgreSQL, và không có
Caddy nên không có header bảo mật. Chạy qua `docker compose` thì cả hai biến mất.

Ba đường hỏng cũng đã thử thật, vì một bảng kiểm không bao giờ báo đỏ thì vô dụng:

| Tình huống | Mã thoát | Hành vi |
|---|---|---|
| `--khat-khe` (cảnh báo ⇒ chặn) | **1** | Liệt kê đúng 2 cảnh báo thành lỗi chặn |
| API chết (`--api http://127.0.0.1:9099`) | **2** | Một câu tiếng Việt, dừng sớm |
| Địa chỉ gõ sai (`…:9!`) | **2** | Một câu tiếng Việt — **không** vết ngăn xếp |
| Web chết, API sống | **1** | Chỉ đúng `web` là thủ phạm |

> Đường "địa chỉ gõ sai" lúc đầu **đổ nguyên vết ngăn xếp** `http.client.InvalidURL` — đúng cái mà
> script sinh ra để ngăn. Nguyên nhân: `InvalidURL` là con của `ValueError`, **không** phải `OSError`,
> nên lọt qua mọi nhánh bắt lỗi. Đã sửa bằng hằng số `LOI_MANG` dùng chung và một lưới bắt-tất ở
> `__main__`. Ghi lại ở đây vì đây đúng là loại lỗi mà bảng kiểm tồn tại để chống.

---

## 6. CHẾ ĐỘ DEMO AN TOÀN

Hội đồng sẽ mở link lúc **không có buổi live nào**. Hai rủi ro ngược chiều, phải chặn cả hai:
trang **trống trơn** (không có gì để xem) và **dữ liệu mô phỏng bị hiểu nhầm thành thật**
(Điều 5 thể lệ cấm, và trung thực là thứ đội này đem đi thi).

Cơ chế đã có sẵn trong kho và **chắc chắn về mặt cấu trúc** — tôi kiểm chứ không xây lại:

| Lớp | Bằng chứng đo được |
|---|---|
| Cột CSDL | `live_session.is_demo boolean NOT NULL DEFAULT false` (migration `0009_is_demo.up.sql`) |
| Bất biến | `_SESSION_WRITE_ONCE` trong `api/store.py:167` chứa `is_demo` — ghi một lần, không sửa được |
| **Client không giả mạo được** | `SessionCreate` có `['platform','title','mode','planned_duration_min','host_id','dry_run']` — **không có `is_demo`**; Pydantic bỏ qua trường thừa |
| API vẫn công khai nhãn | `SessionOut` **có** `is_demo` |
| Tách đúng | `/sessions?env=demo` → 16 phiên, **0 phiên thiếu `is_demo=true`**; `/sessions?env=real` → 17 phiên, **0 phiên bị gán nhầm demo** |
| Nhãn trên giao diện | HTML trang chủ do máy chủ dựng chứa `DEMO` ×3, `mô phỏng` ×3, `PHIÊN THẬT` ×1 — **hiện trước cả khi JavaScript chạy** |
| Mặc định an toàn | `ModeChip.tsx:11-13` — `/health` thiếu `mode` hoặc không gọi được ⇒ rơi về nhãn **DEMO**, không bao giờ tự nhận "THẬT" |
| Kết quả thật tự loại demo | `/experiment/summary` lọc `is_demo == demo`, mặc định `env=real` |

```
$ curl -s http://127.0.0.1:8000/health   (trích)
  mode        = "mixed"
  mode_counts = {"demo": 16, "real": 17}
  mode_note   = "Kho đang chứa CẢ dữ liệu mẫu (16 phiên demo) lẫn dữ liệu thật (17 phiên)
                 — giao diện phải dán nhãn từng phiên; kết quả thật vẫn tự loại demo."
```

**Việc phải làm trước buổi chấm:** nạp bộ demo vàng để trang không trống —
`curl -X POST http://<địa-chỉ>/api/demo/seed-vang` (idempotent: đã có thì trả về bộ sẵn có, không
nhân đôi). Bộ này gồm 6 phiên phủ cả ba trạng thái kết quả (dương rõ · null · chưa đủ điều kiện),
seed cố định, và **tự kiểm chứng** — sai trạng thái là ném `DemoVangStateError`.

---

## 7. SAO LƯU VÀ KHÔI PHỤC

### 7.1. Sao lưu — đã có, đã kiểm

`docker/backup.sh` chạy trong phân hệ `backup`, mỗi ngày một lần lúc `${BACKUP_HOUR:-02}:00`, ghi
`livelift-YYYY-MM-DD.dump.gz`, dọn bản cũ hơn `${RETENTION_DAYS:-14}` ngày. Script đã tự xác minh
**trước khi** đặt tên chính thức (`gzip -t` + `pg_restore --list`), dùng `set -euo pipefail` để một
`pg_dump` chết không bị `gzip` vui vẻ che mất, và **thoát với mã lỗi** khi hỏng để `restart:
unless-stopped` làm số lần restart hiện lên trong `docker ps` thay vì im lặng ghi một bản dump hỏng.

Kiểm chứng thật trên 5 bản đang có:

```
$ for f in livelift-*.dump.gz; do gzip -t "$f" && gunzip -c "$f" | head -c 5; done

livelift-2026-08-30.dump.gz    307,966 B   gzip OK   PGDMP
livelift-2026-09-02.dump.gz    308,805 B   gzip OK   PGDMP
livelift-2026-09-03.dump.gz    958,201 B   gzip OK   PGDMP
livelift-2026-09-04.dump.gz    958,199 B   gzip OK   PGDMP
livelift-2026-09-13.dump.gz  2,039,315 B   gzip OK   PGDMP
```

5/5 nén còn nguyên và mang đúng chữ ký định dạng custom của PostgreSQL.

### 7.2. Khôi phục — `scripts/khoi_phuc_sao_luu.py` (MỚI)

**Trước hôm nay kho có đường sao lưu mà KHÔNG có đường khôi phục.** Thư mục `backups/` có 5 bản dump
và không một dòng nào nói phải làm gì với chúng. Một bản sao lưu chưa bao giờ được đổ ngược vào một
cơ sở dữ liệu thì mới là *một tệp đọc được*, chưa phải *một lưới an toàn*.

Script mặc định **không đụng vào dữ liệu đang chạy**: tạo một CSDL trống riêng
(`livelift_thu_khoi_phuc`), `pg_restore` vào đó, **đếm số dòng 13 bảng ở cả hai bên và in thành hai
cột cạnh nhau**, rồi xoá CSDL tạm. Chỉ `--that` mới đổ vào CSDL thật, và khi đó bắt gõ đúng chuỗi
`KHOI PHUC THAT`. Mọi lệnh postgres chạy trong container `db` qua `docker compose exec`, nên máy vận
hành không cần cài PostgreSQL client.

> **CHƯA KIỂM CHỨNG.** Không chạy được trên máy này vì không có Docker (§1) và không có PostgreSQL.
> Script đã được kiểm đến giới hạn có thể: `ruff check` sạch, `--help` đúng, và **đường hỏng đã thử
> thật** — không có Docker thì nó trả mã 2 kèm một câu tiếng Việt chứ không đổ vết ngăn xếp:
> ```
> $ python scripts/khoi_phuc_sao_luu.py --chi-xac-minh
>   ✕ Không gọi được docker compose: TimeoutExpired…
>     → Cần Docker đang chạy và đã `docker compose up -d db`.
>   [exit 2]
> ```
> Bước bắt buộc khi có Docker: `python scripts/khoi_phuc_sao_luu.py` và dán kết quả vào §9.

### 7.3. Khôi phục đường ảnh chụp — ĐÃ CHỨNG MINH, có đối chứng âm

Đường `memory + ảnh chụp` thì chứng minh được ngay, và đã chứng minh — bằng cách làm **đúng cái đã
xảy ra ngày 11/09/2026** (13 phiên live thật + 17.535 bình luận biến mất): nạp dữ liệu qua API,
**giết cứng** tiến trình (không chạy hàm tắt máy nào), bật lại, đếm.

```
$ python scripts/kiem_chung_ben_vung.py --backend memory --interval 3
   đã nạp: 25 bình luận · 1 tick
   GIẾT CỨNG tiến trình (không chạy hàm tắt máy — đúng như sự cố thật)
   sau khi bật lại: phiên CÒN · 25 bình luận · 1 tick
   KẾT LUẬN: ĐẠT                                                        [exit 0]

$ python scripts/kiem_chung_ben_vung.py --backend memory --no-snapshot   # ĐỐI CHỨNG ÂM
   sau khi bật lại: phiên MẤT · 0 bình luận · 0 tick
   DỰ ĐOÁN: dữ liệu phải MẤT (chứng minh phép thử có răng).
   KẾT LUẬN: ĐẠT                                                        [exit 0]
```

Đối chứng âm là phần đáng giá: nó chứng minh phép thử **biết phát hiện mất dữ liệu**, nên kết quả
"còn nguyên" ở trên không phải do phép thử mù.

Và một lần nữa ở quy mô thật, tình cờ trong lúc thử chống sập (§9): giết API khi đang có **33 phiên**
— sau khi bật lại, **đủ 33 phiên (17 thật + 16 demo)**.

---

## 8. BẢO MẬT TỐI THIỂU TRƯỚC KHI MỞ RA INTERNET

### 8.1. Bí mật — SẠCH, không có P0

Quét toàn bộ **42 commit** (mọi blob, mọi commit) tìm `AIza…`, `EAA…`, `sk-…`, `ghp_…`, `xox[baprs]-`,
`-----BEGIN … PRIVATE KEY-----`: **0 kết quả**.

| Kiểm | Kết quả |
|---|---|
| `.env` có bị git theo dõi? | **KHÔNG** — `git ls-files --error-unmatch .env` → `did not match any file(s)` |
| Tệp `env` được theo dõi | Chỉ `.env.example` và `web/.env.example` |
| `YOUTUBE_API_KEY`, `FACEBOOK_*`, `SHOPEE_*`, `INGEST_TOKEN` trong lịch sử | Tất cả **rỗng hoặc placeholder** |
| `POSTGRES_PASSWORD` trong compose | `${POSTGRES_PASSWORD:?…}` — **fail-closed**, không có giá trị mặc định |
| Bí mật thật trên máy này | Chỉ **một** mật khẩu PostgreSQL cục bộ; mọi khoá nền tảng đều rỗng |

**Không có gì phải thu hồi.** Một điểm nhỏ nên vá: `.gitignore` có `web/.next/` nhưng **không khớp**
`web/.next-chay-local/` — hôm nay chưa lọt gì, nhưng luật hẹp hơn vẻ ngoài của nó.

### 8.2. Đã siết ở lớp hạ tầng (việc của tôi)

| Biện pháp | Nơi | Trạng thái |
|---|---|---|
| HTTPS tự động (Let's Encrypt) | `Caddyfile`, biến `DOMAIN` | Có sẵn, cần tên miền thật |
| `X-Content-Type-Options: nosniff` | `Caddyfile` | **MỚI** |
| `X-Frame-Options: DENY` | `Caddyfile` | **MỚI** |
| `Referrer-Policy: strict-origin-when-cross-origin` | `Caddyfile` | **MỚI** |
| `Permissions-Policy` (tắt camera/mic/định vị) | `Caddyfile` | **MỚI** |
| HSTS 1 năm | `Caddyfile` | **MỚI** — an toàn đặt vô điều kiện: RFC 6797 §8.1 buộc trình duyệt **bỏ qua** HSTS nhận qua HTTP, nên không "khoá nhầm" `localhost` |
| Xoá `Server`, `X-Powered-By` | `Caddyfile` | **MỚI** |
| Hạn giờ `dial 5s` / `response_header 30s` cho API | `Caddyfile` | **MỚI** — lưới cuối khi tiến trình `api` treo hẳn. Cố ý **không** đặt cho `/ws/*`: WebSocket phải mở suốt phiên 90 phút |
| `CORS_ORIGINS` được tài liệu hoá | `.env.example` | **MỚI** — biến này được `main.py:67` đọc nhưng **chưa từng có trong `.env.example`**, nên một bản triển khai thật sẽ im lặng giữ mặc định `localhost` |
| Không publish cổng `api`/`web` ra ngoài | `docker-compose.yml` | Có sẵn — chỉ `caddy` mở 80/443 |

### 8.3. ĐÃ VÁ ngày 14/09/2026 — hồ sơ đầy đủ: `08-VA-XAC-THUC.md`

> **Trạng thái: ĐÃ XỬ LÝ.** Mục này giữ nguyên văn phần phát hiện để đọc được lịch sử; phần
> "đã vá thế nào" nằm ngay bên dưới. Thiết kế, bảng 15 endpoint và nhật ký kiểm thử:
> **`docs/competition/sang-tao-tre-2026/08-VA-XAC-THUC.md`**.

**Phát hiện gốc (14/09, trước khi vá):**

> **12 trong 15 endpoint POST hoàn toàn không có xác thực.** Chỉ 3 endpoint
> (`comments`, `ticks`, `reactions`) tham chiếu `IngestAuth`, và cơ chế ấy **fail-open**:
> `ingest_token` mặc định rỗng ⇒ *tắt kiểm tra hoàn toàn*, mà `INGEST_TOKEN` lại **vắng mặt** trong
> `.env` hiện tại.
>
> Nguy hiểm nhất, xếp theo mức độ:
> 1. `POST /sessions/{id}/actions/execute` và `/actions/override` — người lạ có thể **bắn hoặc ghi đè
>    can thiệp đang chạy**, tức là làm hỏng thẳng việc gán ngẫu nhiên của thí nghiệm.
> 2. `POST /sessions/{id}/start|end|cancel` — điều khiển vòng đời phiên giữa lúc live.
> 3. `POST /demo/seed`, `/demo/seed-vang` — bơm dữ liệu hàng loạt.
> 4. `POST /replays/youtube` — kích hoạt tải `yt-dlp` ra ngoài; **không có rate limit** ở bất kỳ lớp
>    nào nên đây là đòn bẩy khuếch đại tài nguyên.
> 5. WebSocket `accept()` không kiểm origin, không token.
>
> Ngoài ra: bộ xử lý 503 trả **nguyên văn lỗi driver** (`main.py:100`, trường `cause`) cho mọi người
> gọi — cố ý để gỡ lỗi, nhưng lộ chi tiết nội bộ ra ngoài Internet.

**Đã vá thế nào (14/09/2026, gói VÁ-XÁC-THỰC):**

1. **Một cơ chế duy nhất, gắn ở cấp ứng dụng.** `src/livelift/api/auth.py::require_write_auth` được
   truyền vào `FastAPI(dependencies=[...])`, nên nó chạy cho **mọi** route — kể cả route thêm sau
   này. Không còn 12 chỗ dán tay. Route ghi nào quên khai báo mức bảo vệ thì **rơi về mức ngặt
   nhất** (đòi token) và `tests/test_bao_ve_ghi.py` chuyển đỏ: quên là lỗi an toàn, không im lặng.
2. **Hai mức, chia theo thiệt hại thật.** `comments`/`ticks`/`reactions` và `replays/youtube` luôn
   đòi token. 11 endpoint còn lại chấp nhận khách **không token trong phạm vi DEMO**: khách tạo
   được phiên của chính mình (máy chủ ghi `is_demo=true`, không bao giờ vào kết quả thật) và chạy
   trọn wizard trên phiên ấy, nhưng **không chạm được vào phiên THẬT** (403). Bật/tắt bằng
   `PUBLIC_DEMO_WRITES`.
3. **Rate limit có thật, ở tầng ứng dụng.** `WRITE_RATE_LIMIT_PER_MIN` (mặc định 30) và
   `DEMO_SEED_RATE_LIMIT_PER_HOUR` (mặc định 6), chỉ áp cho yêu cầu không token. Cố ý **không**
   dựa vào Caddy: chỉ thị `rate_limit` không có trong ảnh `caddy:2-alpine`, nó là mô-đun bên thứ
   ba phải dựng lại ảnh mới có. Cloudflare (khuyến nghị cũ) vẫn nên đặt thêm — hai lớp, không thừa.

**Còn hở, đã ghi sổ và CHƯA vá** (xem `08-VA-XAC-THUC.md` §rủi ro còn lại):
- WebSocket `/ws/{id}` `accept()` không kiểm origin, không token — nó chỉ **đọc** luồng sự kiện.
- Bộ xử lý 503 vẫn trả nguyên văn lỗi driver (`main.py`, trường `cause`) — nên bỏ khi
  `LIVELIFT_ENV=prod`.
- Danh mục sản phẩm dùng chung toàn hệ thống (không có khái niệm chủ sở hữu) — khoảng trống kiến
  trúc có sẵn, cần mô hình người dùng mới đóng được.

`/docs` và `/openapi.json` **cố ý để mở**: mã nguồn phát hành AGPL-3.0 công khai trên GitHub, nên
tài liệu API không tiết lộ gì mà kho mã không có sẵn, và để mở thì giám khảo tự kiểm chứng API được.
Đây là đánh đổi có chủ ý, **không phải sơ suất** — và nay nó đã đứng **sau** lớp vá ở trên.

---

## 9. NHẬT KÝ KIỂM CHỨNG

Mọi dòng dưới đây là lệnh đã chạy thật hôm nay, kết quả dán nguyên.

| # | Lệnh | Kết quả | Mã thoát |
|---|---|---|---|
| 1 | `docker version` | `500 Internal Server Error` — daemon chết (§1.1) | 1 |
| 2 | `wsl -d docker-desktop ps \| grep dockerd` | **rỗng** — động cơ chưa từng khởi động | — |
| 3 | `Start-Service com.docker.service` | `Cannot open … service` — không có quyền quản trị | 1 |
| 4 | `node --version` / `npm --version` | `v24.14.1` / `11.11.0` | 0 |
| 5 | `.venv/Scripts/python --version` | `Python 3.12.6` | 0 |
| 6 | `python scripts/chay_local.py --force --thu-roi-thoat` | Mọi phép thử ĐẠT; CSS 63.673 B; 33 phiên | **0** |
| 7 | `python scripts/kiem_tra_truoc_demo.py` | 9 đạt · 0 trượt · 2 cảnh báo | **0** |
| 8 | `… --khat-khe` | 2 cảnh báo ⇒ chặn, liệt kê đúng | 1 |
| 9 | `… --api http://127.0.0.1:9099` | "không nối được", dừng sớm | 2 |
| 10 | `… --api "http://127.0.0.1:9!"` | Câu tiếng Việt, **không vết ngăn xếp** | 2 |
| 11 | `… --web http://127.0.0.1:9099` | Chỉ đúng `web` là thủ phạm | 1 |
| 12 | `python scripts/kiem_chung_ben_vung.py --backend memory --interval 3` | 25 bình luận **còn nguyên** sau khi giết cứng | **0** |
| 13 | `… --no-snapshot` (đối chứng âm) | Dữ liệu **mất đúng như dự đoán** | **0** |
| 14 | `gzip -t` + chữ ký trên 5 bản dump | **5/5** `gzip OK` + `PGDMP` | 0 |
| 15 | `python scripts/khoi_phuc_sao_luu.py --chi-xac-minh` | Mã 2 + câu tiếng Việt (không có Docker) | 2 |
| 16 | `curl /sessions?env=demo` | 16 phiên, **0** thiếu `is_demo=true` | 0 |
| 17 | `curl /sessions?env=real` | 17 phiên, **0** bị gán nhầm demo | 0 |
| 18 | `curl /openapi.json` → `SessionCreate` | **Không có** `is_demo` ⇒ client không giả mạo được | 0 |
| 19 | Giết tiến trình API rồi tải trang chủ | **HTTP 200**, 17.218 B, **0** `Traceback`, **0** `Internal Server Error`, rơi về nhãn DEMO | 0 |
| 20 | Bật lại rồi đếm | **33 phiên (17 thật + 16 demo)** — đủ | 0 |
| 21 | `npx next build` (có 3 trang lỗi mới) | `✓ Compiled successfully`, thêm tuyến `/_not-found` | 0 |
| 22 | `ruff check` 2 script mới | `All checks passed!` | **0** |
| 23 | `yaml.safe_load` 3 tệp compose | Hợp lệ; neo `*nhat_ky` bung giống hệt nhau | 0 |
| 24 | Quét bí mật toàn bộ 42 commit | **0** khoá/token | 0 |
| 25 | `git ls-files --error-unmatch .env` | `did not match any file(s)` — sạch | 1 *(đúng)* |
| 26 | `pytest tests/test_infra_public.py tests/test_khoi_dong_sach.py` *(trước khi thêm gate)* | **53 passed** — sửa hạ tầng không làm hỏng gate sẵn có | 0 |
| 27 | `pytest tests/test_infra_public.py` *(sau khi thêm 10 gate)* | **20 passed** (10 cũ + 10 mới) | **0** |
| 28 | `ruff check tests/test_infra_public.py` | `All checks passed!` | 0 |
| 29 | Đối chứng âm cho gate ngoặc nhọn: nhét CSS vào trang lỗi | Gate **bắt được** `['{margin:0}']`; tệp thật im lặng | 0 |

**Chưa kiểm chứng được, và vì sao:** `docker compose up -d` · `caddy validate` · `pg_restore` thật ·
HTTPS/chứng chỉ thật · header bảo mật qua Caddy · đo `docker stats` để siết trần bộ nhớ.
Tất cả đều chặn bởi **một** nguyên nhân duy nhất: Docker daemon không khởi động được vì thiếu quyền
quản trị (§1.1). Không có cái nào chặn bởi lỗi trong cấu hình.

---

## 10. BẢNG KIỂM TRƯỚC DEMO

**T-48 giờ — dựng và để chạy**

- [ ] Mở Docker Desktop bằng **quyền quản trị**, `docker ps` trả bảng rỗng (không phải lỗi 500)
- [ ] `docker compose config >/dev/null` — hợp lệ
- [ ] `docker compose run --rm caddy caddy validate --config /etc/caddy/Caddyfile` — hợp lệ
- [ ] `.env` trên máy chủ: `POSTGRES_PASSWORD` mạnh · `DOMAIN=<tên miền>` · `LIVELIFT_ENV=prod` ·
      `NEXT_PUBLIC_API_URL=https://<tên miền>/api` · `NEXT_PUBLIC_PUBLIC_API_BASE=https://<tên miền>` ·
      `CORS_ORIGINS=https://<tên miền>` · **`INGEST_TOKEN=<chuỗi ngẫu nhiên mạnh>`** ·
      `PUBLIC_DEMO_WRITES=true` (bản cho giám khảo) hoặc `false` (máy chạy thí nghiệm thật)
- [ ] `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
- [ ] `docker compose ps` — mọi phân hệ `healthy`, `migrate` đã `exited (0)`
- [ ] `curl https://<tên miền>/api/health` — `"durable": true` **và** `"storage_ok": true`
- [ ] Nạp demo: `curl -X POST https://<tên miền>/api/demo/seed-vang`
- [ ] Ghim ảnh bằng digest (hướng dẫn trong `docker-compose.prod.yml`)
- [ ] Cloudflare: proxy bật · SSL/TLS **Full (strict)** · chứng chỉ **Origin CA** đã ghim vào Caddy ·
      **một** quy tắc giới hạn tốc độ cho `POST /api/*` (§3.6)
- [ ] `python scripts/kiem_tra_truoc_demo.py --goc https://<tên miền> --khat-khe` → **mã thoát 0**
- [ ] Đăng ký giám sát ngoài (UptimeRobot miễn phí) trỏ vào `/api/health`, 5 phút/lần
- [ ] **Đã diễn tập đường dự phòng** (§3.6 Bước 7.5): dựng thử trên máy thứ hai, xác nhận lên được,
      rồi xoá — để biết chắc 15 phút dựng lại là làm được

**T-24 giờ**

- [ ] Bảng kiểm lại, vẫn mã thoát 0
- [ ] `docker stats --no-stream` — không phân hệ nào chạm trần bộ nhớ
- [ ] `df -h` — đĩa dưới 70 %
- [ ] `python scripts/khoi_phuc_sao_luu.py` — diễn tập khôi phục, dán kết quả vào §9
- [ ] Giám sát ngoài chưa báo gián đoạn lần nào

**T-1 giờ**

- [ ] `python scripts/kiem_tra_truoc_demo.py --goc https://<tên miền> --khat-khe` → 0
- [ ] Mở bằng **mạng 4G điện thoại** (không phải wifi phòng) — trang lên, có nhãn DEMO
- [ ] Bấm thử một shortlink `/r/{mã}` — chuyển hướng đúng
- [ ] Chứng chỉ HTTPS còn hạn > 7 ngày
- [ ] Mở sẵn một tab `docker compose logs -f` trên máy trực

**Nếu sập giữa buổi chấm** *(thứ tự này, không đảo)*

1. `docker compose ps` — phân hệ nào không `healthy`?
2. `docker compose restart <phân hệ>` — **một** phân hệ thôi, đừng `down`
3. Vẫn hỏng: `docker compose up -d --force-recreate <phân hệ>`
4. Trong lúc đó trang lỗi Caddy đang tự tải lại mỗi 10 giây — hội đồng không thấy màn hình vỡ
5. **Không bao giờ** `docker compose down -v` — cờ `-v` xoá sạch volume, tức là xoá cơ sở dữ liệu

---

## 11. KẾ HOẠCH GIỮ UPTIME 48 GIỜ

Bốn kiểu chết, xếp theo xác suất thật, kèm lớp đã chặn:

| # | Kiểu chết | Xác suất | Đã chặn bằng | Còn lại |
|---|---|---|---|---|
| 1 | **Đĩa đầy vì nhật ký** | Cao nếu không chặn | Xoay vòng nhật ký, trần ~180 MB (§5.2) | Kiểm `df -h` mốc T-24 |
| 2 | **OOM-killer bắn PostgreSQL** | Trung bình | Trần bộ nhớ từng phân hệ + `redis maxmemory` (§5.2) | Siết lại sau 24 h bằng `docker stats` |
| 3 | **Một phân hệ treo (còn sống, không trả lời)** | Trung bình | Healthcheck mới cho `api`/`web`/`caddy` (§5.1) | Docker **không** tự restart container unhealthy — xem dưới |
| 4 | **Tiến trình chết hẳn** | Thấp | `restart: unless-stopped` (đã có sẵn) | — |

**Về (3) — một điểm phải nói thật.** Healthcheck của Docker **chỉ đánh dấu** trạng thái, nó **không**
tự khởi động lại container unhealthy. Có hai cách vá, và tôi cố ý **không** chọn cách tự động:

- *Cách tự động:* thêm phân hệ `autoheal` (`willfarrell/autoheal`). Nhưng nó cần **gắn docker socket**,
  và một container có docker socket là một container có **quyền root trên máy chủ** — gắn `:ro` cũng
  không cứu được, vì hạn chế đó không chặn được các lệnh POST của Docker API. Đổi một lỗ hổng leo
  thang đặc quyền lấy một tiện ích, trên một máy chủ sắp mở ra Internet với 12 endpoint chưa xác
  thực (§8.3), là một món hời tồi.
- *Cách đã chọn:* **giám sát ngoài** (UptimeRobot gói miễn phí, 5 phút/lần, trỏ vào `/api/health`)
  + người trực có sẵn lệnh ở §10. Nó bắt được cả những kiểu chết mà autoheal mù — đứt mạng, DNS hỏng,
  chứng chỉ hết hạn, VPS bị nhà cung cấp treo.

**Nhịp trực 48 giờ.** Ba thành viên chia ca, mỗi người một buổi/ngày, mỗi lần 2 phút: mở link bằng
4G, chạy bảng kiểm §5.4, liếc `docker stats` và `df -h`. Ghi một dòng vào `docs/incident-log.md`.
Ca đêm không cần người thức — giám sát ngoài gửi thông báo, và `restart: unless-stopped` lo phần còn lại.

**Không đụng vào máy chủ trong 48 giờ đó.** Không `git pull`, không `--build`, không "sửa nốt cái
này cho đẹp". Mọi thay đổi phải xong **trước** mốc T-48. Cách hỏng phổ biến nhất của một hệ thống
đang chạy tốt là có người sửa nó.

---

## 12. RỦI RO CÒN LẠI

| # | Rủi ro | Mức | Ai xử lý | Việc cụ thể |
|---|---|---|---|---|
| 1 | **Chưa từng chạy `docker compose up` thành công** | **CAO** | Người dùng | Mở Docker bằng quyền quản trị, chạy §2.1 và §10 khối T-48. Đây là rủi ro lớn nhất của cả tài liệu: mọi thứ ở §5 đều **soát tĩnh**, chưa qua lửa. |
| 2 | **`Caddyfile` chưa được `caddy validate`** | **CAO** | Người dùng | Một lệnh ở §10. Hỏng thì `git checkout -- docker/Caddyfile` là về nguyên trạng. |
| 3 | **12 endpoint POST không xác thực** | **CAO** | Agent kiểm toán mã | §8.3. Phải quyết **trước** khi link ra công khai. |
| 4 | Chưa có tài khoản hosting và tên miền | CAO | Người dùng | §3.6 chọn sẵn phương án, §4 có từng bước — cần thẻ/tài khoản, tôi dừng đúng trước bước đó |
| 4b | Nhà cung cấp "miễn phí" có thể đổi luật với rất ít thông báo (Oracle đã cắt đôi hạn mức giữa năm 2026) | TRUNG BÌNH | Người dùng | Dựng thử đường dự phòng 17.000 ₫ **trước** mốc T-48 rồi xoá, để khi cần dựng lại trong 15 phút (§3.6) |
| 4c | Đăng ký `.id.vn` miễn phí cần eKYC bằng CCCD và chỉ còn hiệu lực tới 31/12/2026 | THẤP | Người dùng | Làm sớm; dự phòng DuckDNS mất 5 phút (§3.7) |
| 5 | `pg_restore` chưa diễn tập thật | TRUNG BÌNH | Người dùng | `python scripts/khoi_phuc_sao_luu.py` sau khi có Docker |
| 6 | Trần bộ nhớ là ước lượng, chưa phải số đo | TRUNG BÌNH | Người trực | `docker stats` sau 24 h rồi siết |
| 7 | Thẻ ảnh còn trôi (`latest-pg16`, `2-alpine`) | TRUNG BÌNH | Người trực | Ghim digest — hướng dẫn trong `docker-compose.prod.yml` |
| 8 | Không có rate limit ở bất kỳ lớp nào | TRUNG BÌNH | Người dùng | Cloudflare miễn phí (§3) — không phải sửa mã |
| 9 | `.gitignore` không khớp `web/.next-chay-local/` | THẤP | Agent kiểm toán mã | Đổi `web/.next/` → `web/.next*/` |
| 10 | 503 trả nguyên văn lỗi driver | THẤP | Agent kiểm toán mã | Bỏ trường `cause` khi `LIVELIFT_ENV=prod` |

---

## 13. TỆP ĐÃ THÊM / SỬA

**Thêm mới**

| Tệp | Vai trò |
|---|---|
| `docker-compose.prod.yml` | Lớp phủ prod: xoay vòng nhật ký + trần bộ nhớ + `LIVELIFT_ENV=prod` + hướng dẫn ghim digest |
| `scripts/kiem_tra_truoc_demo.py` | Bảng kiểm một lệnh trước khi lên sóng (§5.4) |
| `scripts/khoi_phuc_sao_luu.py` | Khôi phục + **chứng minh** bản sao lưu dùng được (§7.2) |
| `web/src/app/error.tsx` | Ranh giới lỗi cấp trang |
| `web/src/app/global-error.tsx` | Ranh giới lỗi cấp gốc, không phụ thuộc CSS |
| `web/src/app/not-found.tsx` | Trang 404 tiếng Việt |
| `docs/competition/sang-tao-tre-2026/04-TRIEN-KHAI.md` | Tài liệu này |

**Sửa**

| Tệp | Sửa gì |
|---|---|
| `docker-compose.yml` | Thêm healthcheck cho `api`, `web`, `caddy` (trước đó không có cái nào) |
| `docker/Caddyfile` | Header bảo mật · nén · hạn giờ API · trang lỗi tiếng Việt tự tải lại |
| `.env.example` | Tài liệu hoá `CORS_ORIGINS` — biến được mã đọc nhưng chưa từng được ghi ra |
| `tests/test_infra_public.py` | **+10 gate hồi quy** khoá lại đúng những gì gói này thêm (dưới) |

**Mười gate hồi quy mới** (chạy cùng `pytest`, **không cần Docker**) — để lần sau có người vô tình gỡ
một healthcheck hay nhét CSS vào trang lỗi Caddy thì CI chặn ngay, thay vì hội đồng phát hiện hộ:

`test_api_web_caddy_deu_co_healthcheck` · `test_healthcheck_khong_dung_cong_cu_ma_anh_khong_co`
(chặn việc gọi `curl` trong ảnh không có curl) · `test_caddy_healthcheck_hoi_admin_api_khong_hoi_cong_80` ·
`test_caddyfile_co_header_bao_mat_va_trang_loi` · `test_trang_loi_caddy_khong_co_ngoac_nhon_ngoai_placeholder_that` ·
`test_prod_overlay_xoay_vong_nhat_ky_va_chan_bo_nho` · `test_prod_overlay_giu_store_backend_postgres` ·
`test_web_co_du_ba_trang_loi` · `test_global_error_khong_phu_thuoc_tailwind` ·
`test_env_example_tai_lieu_hoa_cors_origins`

Gate ngoặc nhọn đã được kiểm bằng **đối chứng âm**: nhét thử một khai báo CSS vào trang lỗi thì gate
bắt được (`['{margin:0}']`); trên tệp thật thì im lặng. Nó có răng.

**Không đụng tới:** mọi tệp trong `src/livelift/` (logic nghiệp vụ và mô hình — phân công của hai
agent khác), `README.md`, và mọi script sẵn có.
