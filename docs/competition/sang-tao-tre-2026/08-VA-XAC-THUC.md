# 08 — VÁ XÁC THỰC ĐƯỜNG GHI

> **Gói VÁ-XÁC-THỰC · 14/09/2026 · trước khi mở địa chỉ công khai cho hội đồng chấm.**
> Mã: `src/livelift/api/auth.py` · Cổng kiểm thử: `tests/test_bao_ve_ghi.py` ·
> Cấu hình: `.env.example` (`INGEST_TOKEN`, `PUBLIC_DEMO_WRITES`, hai biến trần tần suất).

---

## 1. Chuyện gì hỏng

Kiểm toán ngày 14/09/2026 (ghi ở `04-TRIEN-KHAI.md` §8.3) tìm thấy: **12 trong 15 endpoint ghi
hoàn toàn không có xác thực**. Ba đường còn lại (`comments`, `ticks`, `reactions`) có, nhưng bằng
cách **dán tay `dependencies=[IngestAuth]` lên từng route** — nghĩa là quên dán không tạo ra lỗi
nào, không dòng log nào, không test nào đỏ. Lỗ hổng **im lặng**. Đó đúng là cách 12 endpoint kia
trôi ra ngoài suốt nhiều tuần.

Thiệt hại thật, không phải giả định:

1. `POST /sessions/{id}/end` — người lạ **kết thúc một phiên thí nghiệm đang phát**. `end_ts` là
   một sự thật không ghi đè được, khối đang đo bị cắt giữa chừng: phiên đó mất giá trị khoa học,
   không cứu được bằng bất kỳ thao tác sửa dữ liệu nào (và quy tắc HARNESS §3 cấm sửa tay bản ghi
   thí nghiệm).
2. `POST /sessions/{id}/actions/execute|override` — bắn hoặc ghi đè can thiệp trong phiên của
   người khác, làm sai thẳng bản ghi ngẫu nhiên hoá (propensity đã ghi không còn đúng sự thật).
3. `POST /demo/seed`, `/demo/seed-vang` — mỗi lần gọi sinh hàng nghìn bản ghi; một vòng lặp `curl`
   làm ngập kho.
4. `POST /replays/youtube` — bắt máy chủ chạy `yt-dlp` tải nội dung theo URL người lạ đưa, tối đa
   20.000 bình luận mỗi lần: đòn bẩy khuếch đại tài nguyên trên một VPS 1 vCPU.

---

## 2. Bảng 15 endpoint ghi — trạng thái trước / sau / vì sao chọn mức đó

**Hai mức bảo vệ.** `TOKEN` = luôn đòi `Authorization: Bearer <INGEST_TOKEN>`.
`DEMO` = đòi token, **hoặc** (khi `PUBLIC_DEMO_WRITES=true`) cho qua nhưng chỉ trong phạm vi dữ
liệu MẪU và có trần tần suất.

| # | Endpoint ghi | Trước 14/09 | Sau | Vì sao đúng mức đó |
|---|---|---|---|---|
| 1 | `POST /sessions/{id}/comments` | **có** (`IngestAuth`, dán tay) | `TOKEN` | Đường dữ liệu của bộ thu. Một bình luận giả bơm vào phiên thật là **một điểm dữ liệu sai trong bài báo** — không có "phiên demo nên nghịch cũng được": mức này áp cả trên phiên demo. |
| 2 | `POST /sessions/{id}/ticks` | **có** | `TOKEN` | Như trên — lượt xem là mẫu số của biến kết quả. |
| 3 | `POST /sessions/{id}/reactions` | **có** | `TOKEN` | Như trên (tương tác trả phí, migration 0007). |
| 4 | `POST /replays/youtube` | **KHÔNG** | `TOKEN` | Máy chủ tải nội dung bên ngoài theo URL người gọi đưa. Đây là chi phí CPU/băng thông/ổ đĩa của chủ máy, không phải một nút bấm thử. Giữ đóng kể cả khi chế độ trưng bày đang bật. |
| 5 | `POST /products` | **KHÔNG** | `DEMO` | Wizard phải tạo được sản phẩm thì mới chạy được. Không gắn với phiên nào nên chỉ chặn bằng trần tần suất — danh mục dùng chung là khoảng trống kiến trúc **có sẵn**, ghi ở §6. |
| 6 | `POST /shortlinks` | **KHÔNG** | `DEMO` | Như trên; link đo là một phần của luồng dựng phiên. |
| 7 | `POST /sessions` | **KHÔNG** | `DEMO` — khách không token ⇒ phiên `is_demo=true` | Bản lề của cả thiết kế: giám khảo **tạo được phiên của chính mình**, mà dữ liệu ấy không bao giờ lọt vào kết quả thật. Người vận hành (có token) vẫn tạo phiên THẬT như cũ. |
| 8 | `POST /sessions/{id}/schedule` | **KHÔNG** | `DEMO` | Phiên demo: cho. Phiên THẬT: 403 — bốc lại lịch gán của phiên người khác là phá thiết kế thí nghiệm. |
| 9 | `POST /sessions/{id}/start` | **KHÔNG** | `DEMO` | Như trên. |
| 10 | `POST /sessions/{id}/end` | **KHÔNG** | `DEMO` | **Thiệt hại nguy hiểm nhất** được bịt đúng ở đây: phiên THẬT ⇒ 403, trạng thái không đổi một ly (có test đối chứng). |
| 11 | `POST /sessions/{id}/cancel` | **KHÔNG** | `DEMO` | Như trên. |
| 12 | `POST /sessions/{id}/actions/execute` | **KHÔNG** | `DEMO` | Ghim trên phiên demo của mình: cho, đó chính là thứ đáng xem. Trên phiên thật: 403. |
| 13 | `POST /sessions/{id}/actions/override` | **KHÔNG** | `DEMO` | Như trên. |
| 14 | `POST /demo/seed` | **KHÔNG** | `DEMO` + trần **theo giờ** | Theo định nghĩa chỉ sinh dữ liệu mẫu, nên không cần ranh giới phiên; cái phải chặn là **khối lượng**, và trần theo phút quá lỏng cho một lời gọi sinh hàng nghìn bản ghi. |
| 15 | `POST /demo/seed-vang` | **KHÔNG** | `DEMO` + trần **theo giờ** | Như trên. (Route này còn tự bất biến khi gọi lại — đã có từ trước.) |

> **Một đính chính so với bản kiểm toán ban đầu:** bản kiểm toán ghi "2 endpoint có xác thực".
> Con số đúng là **3** — `reactions` cũng đã tham chiếu `IngestAuth`. Danh sách 12 endpoint không
> được bảo vệ thì chính xác tuyệt đối. Tổng: 15.

**Mọi endpoint ĐỌC vẫn mở** (kể cả `/docs`, `/openapi.json`, `/ws/{id}`). Đó là đánh đổi **có
chủ ý và được viết ra**: mã nguồn phát hành AGPL-3.0 công khai, nên tài liệu API không tiết lộ gì
mà kho mã không có sẵn, và để mở thì giám khảo tự kiểm chứng được. Cổng chỉ chặn
`POST/PUT/PATCH/DELETE`.

---

## 3. Thiết kế, và lý lẽ của từng quyết định

### 3.1 Một cơ chế, gắn ở CẤP ỨNG DỤNG — quên là lỗi an toàn

```python
# src/livelift/api/main.py
app = FastAPI(..., dependencies=[Depends(require_write_auth)])
```

Không phải cấp router, và dứt khoát không phải 15 dòng dán tay. Hệ quả:

- route ghi **nào cũng** đi qua cổng, kể cả route thêm vào ngày mai;
- route ghi quên khai báo mức bảo vệ **rơi về mức ngặt nhất** (`MUC_MAC_DINH = "token"`) — hành vi
  mặc định là từ chối, không phải cho qua;
- cổng kiểm thử `tests/test_bao_ve_ghi.py` đọc **thẳng bảng định tuyến của ứng dụng** và đối chiếu
  với bảng chính sách 15 dòng. Thêm một route ghi mà quên khai báo ⇒ mức `None` ⇒ **đỏ**. Thêm một
  route ghi có khai báo nhưng chưa ai xem xét ⇒ khoá thừa so với bảng chính sách ⇒ cũng **đỏ**:
  mỗi đường ghi mới bắt buộc phải có một con người quyết định nó thuộc mức nào.

Cái bẫy đã dính khi làm cổng này, ghi lại để người sau không mất buổi chiều: **từ FastAPI 0.141
`app.routes` không còn dàn phẳng** — mỗi `include_router` để lại một nút bọc `_IncludedRouter` giữ
router thật ở `original_router`. Một vòng lặp một tầng trên `app.routes` thấy đúng **0 route ghi**,
nghĩa là cổng kiểm thử viết theo kiểu ấy sẽ **xanh vĩnh viễn mà không kiểm gì cả** — một cổng giả.
`auth._moi_route` vì thế duyệt đệ quy cả cây.

Mức bảo vệ khai báo bằng decorator đặt **ngay trên route** (`@chi_token` / `@cho_phep_demo`), không
phải một bảng tra cứu ở tệp khác: đọc route là thấy chính sách của nó.

### 3.2 Token rỗng ⇒ mở (giữ nguyên quy ước `INGEST_TOKEN`)

Không có bí mật nào thì không có cổng nào. Đây là chế độ phát triển cục bộ, và là điều giữ cho
toàn bộ bộ kiểm thử chạy được mà không phải đính header ở hàng nghìn chỗ. Có test khoá lại đúng
hợp đồng này cho cả 15 endpoint (`test_token_rong_thi_moi_duong_ghi_van_mo`).

### 3.3 Bài toán thật: hội đồng phải dùng thử được

Đây là chỗ khó nhất, và "khoá sạch" là một đáp án **sai**: bản trưng bày bị khoá đường ghi trở
thành ảnh tĩnh — hỏng đúng thứ nó sinh ra để chứng minh (trọng tâm 7). Mở toang thì mất trọng
tâm 8. Hướng đã chọn (và đã tự đánh giá lại):

> **Khách không token được ghi — nhưng chỉ vào dữ liệu MẪU, và dữ liệu của khách SINH RA đã là dữ
> liệu mẫu.**

Điểm then chốt, và cũng là chỗ hướng gợi ý ban đầu chưa đủ: `POST /sessions` **pin cứng
`is_demo=False`**, nên "chỉ cho ghi vào phiên demo" một mình nó sẽ chặn khách ngay ở bước đầu
tiên của wizard — giám khảo không tạo nổi một phiên nào. Lời giải: **máy chủ** đặt cờ theo câu hỏi
"yêu cầu này có chứng minh được mình là người vận hành không?".

| Người gọi | `is_demo` của phiên tạo ra |
|---|---|
| có token đúng, **hoặc** chạy cục bộ (chưa đặt `INGEST_TOKEN`) | `false` — dữ liệu thật, **hành vi cũ, không đổi một ly** |
| không token, đi qua nhờ chế độ trưng bày | `true` — dữ liệu mẫu |

Đây không phải một nhãn dán cho tiện, nó là **sự thật**: không buổi phát nào diễn ra, người tạo là
một khách vãng lai. Ba tính chất được giữ nguyên vẹn:

- **Client vẫn không giả mạo được.** `SessionCreate` không có trường `is_demo` (hợp đồng OpenAPI
  không đổi — có test), và `store._SESSION_WRITE_ONCE` khoá cờ sau khi tạo theo **cả hai chiều**:
  không ai gắn nhãn "mẫu" cho một phiên thật sau khi đã nhìn số, cũng không ai rửa một phiên demo
  thành dữ liệu thật.
- **Dữ liệu của khách không bao giờ vào kết quả khoa học.** Mọi đường gộp kết quả đã tự loại
  `is_demo` từ trước (gói DEMO-THẬT) — loại trừ mang tính **cấu trúc**, không phải một bộ lọc ai
  đó phải nhớ áp.
- **Không đụng một dòng nào** vào logic gán ngẫu nhiên, phân tích, hay khoá tiền đăng ký.

**Vì sao không chọn các hướng khác:**

| Hướng | Vì sao không |
|---|---|
| Khoá sạch, cấp token riêng cho giám khảo | Phải phát token qua một kênh nào đó, mỗi giám khảo một lần; token dùng chung bị chuyển tiếp là mất sạch tác dụng. Và bản trưng bày phải mở được **ngay khi bấm link**. |
| Mô hình người dùng / `owner_id` trên phiên và sản phẩm | Đúng về lâu dài, và đã có trong lộ trình (`docs/mo-hinh-van-hanh-kol.md` §5 ước lượng 2–3 tuần-người). Không phải thứ làm được an toàn trong một ngày, ngay trước hạn. |
| `write_key` trả về lúc tạo phiên, client giữ | Thực chất là "ownership-lite" nhưng phải sửa hợp đồng web↔API và mọi màn hình. Đổi nhiều, được thêm rất ít so với ranh giới demo/thật. |
| Dựa vào Cloudflare / Caddy cho rate limit | Xem §3.4. |

### 3.4 Giới hạn tần suất — làm ở tầng ứng dụng, và vì sao không dùng Caddy

Đã kiểm tra `docker/Caddyfile` trước: cái vừa được thêm ở đó là **hạn giờ** (`dial_timeout`,
`response_header_timeout`) — chuyện khác hẳn, không phải giới hạn tần suất. Chỉ thị `rate_limit`
**không có trong bản Caddy tiêu chuẩn**: nó là mô-đun bên thứ ba, phải dựng lại ảnh `caddy:2-alpine`
bằng `xcaddy` mới có. Làm ở tầng ứng dụng thì:

- bản triển khai nào cũng được bảo vệ, kể cả khi ai đó chạy `uvicorn` trần không qua Caddy;
- và **chỉ ở đây mới biết yêu cầu có token hay không** — nên bộ thu của chính đội (bắn một bình
  luận mỗi giây suốt 90 phút) **không bao giờ** bị chặn. Trần chỉ áp cho đường ghi MỞ.

| Nhóm | Biến | Mặc định |
|---|---|---|
| Ghi thường | `WRITE_RATE_LIMIT_PER_MIN` | 30 / phút / địa chỉ |
| `/demo/seed`, `/demo/seed-vang` | `DEMO_SEED_RATE_LIMIT_PER_HOUR` | 6 / giờ / địa chỉ |

Đặt `0` để tắt. Trả `429` kèm `Retry-After` và câu tiếng Việt.

Địa chỉ người gọi lấy **phần tử CUỐI** của `X-Forwarded-For`, không phải phần tử đầu: Caddy **nối
thêm** địa chỉ nó thật sự nhận gói tin vào cuối header, nên phần tử cuối là thứ duy nhất người gọi
không tự bịa được. Lấy phần tử đầu thì một dòng `curl` đổi header mỗi lần gọi là trần tần suất
thành đồ trang trí — có test đối chứng đúng chỗ này
(`test_dia_chi_lay_phan_tu_cuoi_cua_x_forwarded_for`).

Bộ đếm sống **theo ứng dụng** (`app.state.gioi_han_ghi`), không phải biến module: hai ứng dụng
trong cùng tiến trình không dùng chung hạn mức của nhau. Trong tiến trình, không cần Redis — quy
mô thí điểm là một tiến trình API; chạy nhiều tiến trình thì mỗi tiến trình giữ hạn riêng (vẫn là
trần, chỉ lỏng hơn theo số tiến trình — nói thẳng để không ai tưởng nó là hạn toàn cục).

### 3.5 Thông báo lỗi

Tiếng Việt, nói được **phải làm gì**, và không một chữ nào về bên trong máy chủ (có test quét
`Traceback`, tên module, tên lớp store, và chính giá trị token trong thân phản hồi).

| Tình huống | Mã | Câu |
|---|---|---|
| Thiếu/sai token ở mức `TOKEN`, hoặc chế độ trưng bày tắt | 401 | *"Thiếu hoặc sai token ingest — cần header 'Authorization: Bearer <INGEST_TOKEN>'"* — **giữ nguyên văn** câu đã dùng từ trước, vì bộ thu, tài liệu vận hành và test hồi quy đều đang khớp theo nó. |
| Khách không token ghi vào phiên THẬT | 403 | *"Phiên này là dữ liệu THẬT — bản trưng bày công khai chỉ cho thao tác trên phiên DEMO. Hãy tạo phiên của riêng bạn bằng POST /sessions…"* |
| `POST /replays/youtube` không token | 401 | *"Thao tác này cần token ghi. Đây là đường tốn tài nguyên máy chủ (tải và phân tích video theo địa chỉ người gọi đưa) nên bản trưng bày công khai không mở…"* |
| Vượt trần tần suất | 429 + `Retry-After` | *"Bạn đang gửi quá nhanh — bản trưng bày công khai nhận tối đa N lượt ghi mỗi phút từ một địa chỉ…"* |

Hai chi tiết nhỏ nhưng cố ý:

- **Phiên không tồn tại vẫn trả 404, không phải 403.** Biến 404 thành 403 là biến chính cổng xác
  thực thành một máy dò mã phiên (đoán đúng id thì nhận mã lỗi khác) — có test.
- **So sánh token bằng `secrets.compare_digest`**, không phải `!=`: tránh rò rỉ qua thời gian
  phản hồi.
- Nhật ký ghi đủ để truy vết (phương thức, đường dẫn, lý do, địa chỉ) và **không bao giờ ghi token
  người gọi đưa** — nhật ký có thể bị đọc bởi nhiều người hơn số người được biết bí mật.

### 3.6 Một sửa nhỏ ở giao diện, đi kèm

`web/src/components/BatDauVod.tsx` trước đây nuốt lỗi từ máy chủ và luôn in *"kiểm tra lại đường
dẫn video và máy chủ LiveLift"*. Trên bản trưng bày công khai, câu trả lời đúng là *"đường này cần
token ghi"* — in câu cũ là **đổ lỗi cho người dùng về một thứ họ không sai**. Nay thành phần này
hiển thị `detail` tiếng Việt của máy chủ, chuỗi cũ chỉ còn là lưới cuối khi thật sự không nối được.

---

## 4. Nhật ký kiểm thử — lệnh thật, số thật

| # | Lệnh | Kết quả |
|---|---|---|
| 1 | `.venv/Scripts/python -m pytest -m "not slow"` — **TRƯỚC** (14:47) | **1059 passed · 1 skipped · 1 failed** — 1061 thu thập |
| 2 | `.venv/Scripts/python -m pytest -m "not slow"` — **SAU** (15:31, lần chạy cuối, sau khi mọi mã và tài liệu đã xong) | **1154 passed · 1 skipped · 0 failed · 17 deselected** — 1155 thu thập, 219,53 s, **mã thoát 0** |
| 3 | `.venv/Scripts/python -m pytest tests/test_bao_ve_ghi.py` | **88 passed** in 18,05 s |
| 4 | `.venv/Scripts/python -m ruff check .` | `All checks passed!` |
| 5 | `.venv/Scripts/python -m ruff format --check .` | `215 files already formatted` |
| 6 | `.venv/Scripts/python scripts/dong_bo_so_test.py --ghi` | badge README + số trang chủ: **993 → 1155** (badge đã cũ từ trước gói này) |

**Đọc con số cho đúng — 1061 → 1155 là +94, không phải +88.** Có gói khác chạy song song trong cùng
kho lúc đó:

- **+88** là của gói này (`tests/test_bao_ve_ghi.py`);
- **+6** và **−1 test đỏ** là của gói giao diện đang sửa ba trang lỗi
  (`web/src/app/error.tsx` 14:50 · `global-error.tsx` 14:54 · `not-found.tsx` 14:50 ·
  `tests/test_web_design_tokens.py` 14:56 — mốc sửa tệp nằm **giữa** hai lần chạy).

Test đỏ ở lần chạy TRƯỚC là
`tests/test_web_design_tokens.py::test_every_focusable_element_shows_a_focus_ring` (cổng trợ năng
đòi vòng focus trên ba trang lỗi mới). Nó **đã đỏ trước khi** gói này chạm vào bất cứ thứ gì, và
nó xanh trở lại nhờ gói giao diện, **không phải** nhờ gói này. **0 test nào bị gói này làm hỏng.**

**Phân rã 88 test mới trong `tests/test_bao_ve_ghi.py`:**

| Nhóm | Test | Khoá lại điều gì |
|---|---|---|
| Cơ chế | `test_bang_dinh_tuyen_that_khop_bang_chinh_sach` | 15 endpoint × mức, đọc thẳng `app.routes` |
| | `test_cong_xac_thuc_gan_o_cap_ung_dung` | gỡ dependency khỏi `create_app` ⇒ đỏ |
| | `test_route_ghi_moi_quen_khai_bao_thi_bo_test_do` | **route ghi mới quên gắn ⇒ đỏ**, và lúc chạy rơi về mức ngặt nhất |
| | `test_moi_endpoint_ghi_deu_co_mot_loi_goi_trong_bo_kiem_thu` | không endpoint nào được "kiểm thử bằng cách bỏ qua" |
| Từng endpoint (×15 mỗi bộ) | `test_khong_token_thi_bi_chan_o_moi_duong_ghi` | hồ sơ khoá sạch: 15/15 trả 401 |
| | `test_co_token_thi_qua_o_moi_duong_ghi` | token đúng ⇒ cổng không chặn |
| | `test_token_sai_bi_tu_choi_giong_het_khong_co_token` | token sai không được ưu ái, phản hồi không lộ token thật |
| | `test_token_rong_thi_moi_duong_ghi_van_mo` | chế độ phát triển cục bộ nguyên vẹn |
| Ranh giới demo/thật | `test_khach_tao_phien_thi_phien_do_la_phien_demo` | khách ⇒ `is_demo=true`; người vận hành ⇒ `false` |
| | `test_khach_chay_tron_wizard_tren_phien_cua_minh` | tạo → lịch gán → phát → ghim → kết thúc, **không một header nào** |
| | `test_khach_khong_cham_duoc_vao_phien_that` (×6 đường) | 403 |
| | `test_phien_that_van_song_sau_khi_khach_thu_ket_thuc` | không chỉ 403 — **trạng thái không đổi một ly** |
| | `test_duong_nap_du_lieu_dong_ke_ca_tren_phien_demo` (×3) | bộ thu không phải đồ chơi |
| | `test_duong_ton_tai_nguyen_dong_ca_trong_che_do_trung_bay` | `/replays/youtube` |
| | `test_ma_phien_khong_ton_tai_van_tra_404_chu_khong_phai_403` | cổng không thành máy dò mã phiên |
| Tần suất | 6 test | trần theo phút, trần theo giờ tách riêng, người có token miễn trừ, `X-Forwarded-For` lấy phần tử cuối, `0` = tắt, cửa sổ trượt mở lại |
| Không lộ / không phá | `test_moi_duong_doc_van_mo_khi_da_bat_xac_thuc` · `test_cau_tu_choi_khong_lo_thong_tin_he_thong` · `test_openapi_khong_them_truong_is_demo_cho_client` | đường đọc, thông báo lỗi, hợp đồng OpenAPI |

---

## 5. Đặt biến môi trường khi triển khai

### 5.1 Bản cho HỘI ĐỒNG CHẤM bấm thử (khuyến nghị)

```bash
# .env trên máy chủ
INGEST_TOKEN=<openssl rand -base64 32>   # BẮT BUỘC. Để trống = tắt xác thực hoàn toàn.
PUBLIC_DEMO_WRITES=true                  # khách bấm thử được, chỉ trên phiên demo
WRITE_RATE_LIMIT_PER_MIN=30
DEMO_SEED_RATE_LIMIT_PER_HOUR=6
```

Giám khảo mở link và: xem mọi phiên, mở bàn điều khiển, bấm "Xem thử ngay" (`/demo/seed`), **tạo
phiên của chính mình và chạy trọn wizard**. Giám khảo **không** kết thúc được phiên thật của đội,
**không** bơm được bình luận giả, **không** bắt được máy chủ tải video.

Trước buổi demo, người vận hành (có token) nên nạp sẵn:

```bash
curl -X POST -H "Authorization: Bearer $INGEST_TOKEN" https://<DOMAIN>/api/demo/seed-vang
# và, nếu muốn trưng bày màn phân tích VOD:
curl -X POST -H "Authorization: Bearer $INGEST_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"url":"https://www.youtube.com/watch?v=<id>"}' \
     https://<DOMAIN>/api/replays/youtube
```

Phiên phân tích sinh ra **đọc được công khai**, nên tính năng vẫn trưng bày được đầy đủ dù đường
ghi của nó đóng.

### 5.2 Máy chủ chạy thí nghiệm THẬT

```bash
INGEST_TOKEN=<chuỗi ngẫu nhiên mạnh>
PUBLIC_DEMO_WRITES=false                 # khoá sạch: mọi đường ghi đòi token
```

Bộ thu (`python -m livelift.ingest.runner`) và `spool_replay` tự đọc `INGEST_TOKEN` từ `.env` và
đính header — không phải làm gì thêm. `scripts/live_fire_da_nguon.py` nay cũng vậy.

### 5.3 Máy mình / bộ kiểm thử

Không đặt gì. `INGEST_TOKEN` rỗng ⇒ không có cổng nào, hành vi y như trước.

### 5.4 Bảng kiểm trước khi mở link

- [ ] `INGEST_TOKEN` **có giá trị** trên máy chủ (`docker compose exec api env | grep INGEST_TOKEN`)
- [ ] `PUBLIC_DEMO_WRITES` đúng hồ sơ đang dùng
- [ ] Thử bằng tay: `curl -X POST https://<DOMAIN>/api/sessions/<id-phien-that>/end` ⇒ **403**
- [ ] Thử bằng tay: `curl -X POST https://<DOMAIN>/api/replays/youtube -d '{"url":"https://x"}' -H 'Content-Type: application/json'` ⇒ **401**
- [ ] Thử bằng tay: `curl -X POST https://<DOMAIN>/api/sessions -H 'Content-Type: application/json' -d '{"platform":"youtube","planned_duration_min":90}'` ⇒ **200** và phiên trả về có `"is_demo": true`
- [ ] `.env` **không** nằm trong git (`git ls-files --error-unmatch .env` phải thất bại)

---

## 6. Rủi ro còn lại — cái gì vẫn hở, và vì sao chưa đóng

| # | Rủi ro | Mức | Vì sao chưa đóng / cách giảm nhẹ |
|---|---|---|---|
| 1 | **Không có khái niệm chủ sở hữu.** `POST /products` và `/shortlinks` không gắn với phiên nào, nên khách của bản trưng bày thêm được sản phẩm vào **danh mục dùng chung toàn hệ thống** — và sản phẩm đó có thể xuất hiện trong thẻ gợi ý của bàn điều khiển thật. | Trung bình | Khoảng trống kiến trúc **có sẵn từ trước**, không do tầng này sinh ra (đã ghi ở `docs/mo-hinh-van-hanh-kol.md` §5, ước lượng 2–3 tuần-người cho mô hình người dùng + `owner_id` + lọc theo chủ ở mọi truy vấn). Giảm nhẹ hiện tại: trần tần suất. **Nếu đang chạy thí nghiệm thật trên cùng máy chủ ⇒ đặt `PUBLIC_DEMO_WRITES=false`.** |
| 2 | **WebSocket `/ws/{id}` không kiểm origin, không token.** | Thấp–Trung bình | Nó chỉ **đọc** luồng sự kiện, đúng hạng với mọi endpoint đọc khác (đang cố ý mở). Nhưng nó bỏ qua cả `CORSMiddleware` — trang web bất kỳ mở được socket tới máy chủ này. Đóng đúng cách cần kiểm `Origin` lúc `accept()`; chưa làm vì nằm ngoài phạm vi "đường ghi". |
| 3 | **Bộ xử lý 503 trả nguyên văn lỗi driver** (`main.py`, trường `cause`). | Thấp | Cố ý để gỡ rối, nhưng lộ chi tiết nội bộ ra Internet. Đề xuất: bỏ trường `cause` khi `LIVELIFT_ENV=prod`. Không sửa trong gói này vì nó không phải lỗ hổng xác thực và đang nằm trong phần việc của gói triển khai. |
| 4 | **Trần tần suất theo tiến trình, theo địa chỉ.** | Thấp | Chạy nhiều worker ⇒ trần lỏng theo số worker. Người có nhiều địa chỉ (botnet, VPN xoay vòng) vẫn qua được. Lớp đúng cho chuyện đó là Cloudflare/WAF trước VPS — **vẫn nên đặt**, hai lớp không thừa. |
| 5 | **Một token dùng chung cho cả đội.** | Trung bình | Không thu hồi được cho một người; lộ là phải đổi cho tất cả và khởi động lại bộ thu. Đúng hạng với quy mô thí điểm; mô hình người dùng ở mục 1 là lời giải thật. |
| 6 | **Khách làm ngập kho bằng phiên demo** (trong trần 30/phút). | Thấp | Phiên demo không vào kết quả thật nên thiệt hại là dung lượng và độ lộn xộn của danh sách, không phải tính hợp lệ khoa học. `scripts/don_phien_demo_trung.py` dọn được. Muốn chặt hơn: hạ `WRITE_RATE_LIMIT_PER_MIN`. |
| 7 | **Mọi endpoint ĐỌC mở hoàn toàn**, kể cả bàn điều khiển của phiên thật. | Trung bình | Đánh đổi có chủ ý cho bản trưng bày AGPL (xem §2). Hệ quả cần nói thẳng: **việc làm mù người dẫn hiện chỉ được bảo vệ ở cấp kiểu dữ liệu** (`HostState` không có trường khối), không có tầng quyền nào chặn người dẫn tự mở `/desk`. Đã ghi ở `docs/research/2026-09-11-vi-the-va-lo-trinh.md`. |
| 8 | `PUBLIC_DEMO_WRITES` **mặc định `true`**. | Thấp | Đánh đổi có chủ ý, ghi rõ ở đây và trong `.env.example`: bán kính thiệt hại bị chặn **bằng cấu trúc** (khách không chạm được phiên thật, không chạm được đường nạp dữ liệu, không chạm được `/replays/youtube`), còn một bản trưng bày bị khoá sạch thì hỏng đúng thứ nó sinh ra để chứng minh. Máy chạy thí nghiệm thật phải đặt `false` — đã đưa vào bảng kiểm §5.4 và runbook. |

---

## 7. Tệp đã đổi

| Tệp | Việc |
|---|---|
| `src/livelift/api/auth.py` | **MỚI** — cơ chế: mức bảo vệ, dependency, giới hạn tần suất, thông báo lỗi |
| `src/livelift/api/main.py` | gắn `dependencies=[Depends(require_write_auth)]`; bộ đếm tần suất theo ứng dụng |
| `src/livelift/config.py` | `PUBLIC_DEMO_WRITES`, `WRITE_RATE_LIMIT_PER_MIN`, `DEMO_SEED_RATE_LIMIT_PER_HOUR`; ghi lại vai trò `INGEST_TOKEN` |
| `src/livelift/api/routes/events.py` | bỏ `IngestAuth` dán tay ⇒ `@chi_token` (hành vi không đổi) |
| `src/livelift/api/routes/sessions.py` | `@cho_phep_demo` ×7; `is_demo` do máy chủ quyết theo `ghi_khong_token` |
| `src/livelift/api/routes/actions.py` | `@cho_phep_demo` ×2 |
| `src/livelift/api/routes/demo.py` | `@cho_phep_demo` ×2 |
| `src/livelift/api/routes/replays.py` | `@chi_token` |
| `scripts/live_fire_da_nguon.py` | đính token khi API đích có đặt |
| `web/src/components/BatDauVod.tsx` | hiển thị `detail` tiếng Việt của máy chủ thay vì nuốt đi |
| `tests/test_bao_ve_ghi.py` | **MỚI** — 88 test |
| `.env.example` · `ops/runbooks/quy-trinh-phien.md` · `docs/mo-hinh-van-hanh-kol.md` · `04-TRIEN-KHAI.md` §8.3 | tài liệu vận hành |
| `docs/incident-log.md` | một hàng theo HARNESS §3 (sự cố thứ 44) |
| `README.md` · `web/src/app/page.tsx` | số sự cố 43 → 44; số test đồng bộ bằng `scripts/dong_bo_so_test.py --ghi` |
