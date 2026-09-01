# Hướng dẫn kiểm thử LiveLift

Mọi lệnh trong tài liệu này đã được chạy thật trên máy và ghi lại kết quả thực tế.
Nếu bạn chạy ra khác, đó là lỗi — báo lại để sửa.

**Cập nhật:** 27/08/2026 · 119 test tự động pass · 5 service Docker

---

## 0. Khởi động (1 lần)

```bash
cd D:\AISC2026\livelift
docker compose up -d
```

Chờ ~20 giây rồi kiểm tra:

```bash
docker compose ps
curl -s http://127.0.0.1:8000/health
```

Kết quả đúng: 5 service `Up`, và `{"status":"ok","store_backend":"postgres"}`.

> **Nếu báo lỗi `failed to connect to the docker API`:** Docker Desktop chưa chạy.
> Mở Docker Desktop, chờ biểu tượng chuyển xanh, chạy lại lệnh trên.

Dừng khi không dùng: `docker compose down` (dữ liệu vẫn giữ nguyên).

---

## 1. Kiểm thử bằng giao diện — không cần biết lệnh

| # | Việc | Làm thế nào | Kết quả đúng |
|---|---|---|---|
| 1.1 | Xem thử toàn hệ thống | Mở http://localhost:3000 → bấm **"Xem thử ngay (30 giây)"** | Tạo dữ liệu mô phỏng rồi tự chuyển sang trang phát lại |
| 1.2 | Xem kết quả khoa học | Bấm **"Kết quả"** trên thanh trên | Tác động ước lượng, KTC 95%, p-value, bảng MDE |
| 1.3 | Bàn điều khiển | Bấm **"Bàn điều khiển"** | 3 vùng: nhịp phiên + dải khối BẬT/TẮT, thẻ hành động, radar bình luận |
| 1.4 | Chú giải thuật ngữ | Rê chuột vào chữ **BẬT** / **TẮT** trên dải khối | Hiện giải thích tiếng Việt |
| 1.5 | Màn hình host | Bấm **"Màn hình host"** | **Chỉ** 4 thông tin cỡ lớn: sản phẩm, giá, tồn kho, thời gian |
| 1.6 | Phân tích video YouTube | Trang chính → ô số 2, dán link live đã kết thúc | Hiện tiến trình rồi mở trang phân tích |

### Về mục 1.5 — vì sao màn hình host "thiếu" thông tin

Đây là **thiết kế có chủ đích**, không phải bug. Nếu người dẫn biết mình đang ở khối
BẬT hay TẮT, họ sẽ vô thức nói năng khác đi, và thí nghiệm không còn đo tác động của
hệ thống nữa mà đo cả tâm lý người dẫn. Kiểm chứng:

```bash
SID=$(curl -s http://127.0.0.1:8000/sessions | python -c "import sys,json;d=json.load(sys.stdin);print([s['session_id'] for s in d if s['status']=='live'][0])")
curl -s "http://127.0.0.1:8000/sessions/$SID/state?role=host"
```

Kết quả đúng: **chỉ** `pinned_product`, `price`, `stock`, `elapsed_s`.
Không có `assignment`, không có `seconds_remaining`.

---

## 2. Kiểm thử luồng thí nghiệm đầy đủ — bằng lệnh

Copy nguyên khối này vào Git Bash:

```bash
cd /d/AISC2026/livelift

# 1. Tạo sản phẩm
curl -s -X POST http://127.0.0.1:8000/products -H 'Content-Type: application/json' \
  -d '{"product_id":"test-1","name":"Ao thun","cost":80000,"price":199000,"stock":50}'

# 2. Tạo phiên
SID=$(curl -s -X POST http://127.0.0.1:8000/sessions -H 'Content-Type: application/json' \
  -d '{"platform":"youtube","mode":"auto","planned_duration_min":60}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["session_id"])')
echo "phiên: $SID"

# 3. BỐC THĂM TRƯỚC KHI PHÁT — nguyên tắc bất di bất dịch
curl -s -X POST "http://127.0.0.1:8000/sessions/$SID/schedule" \
  -H 'Content-Type: application/json' -d '{"seed":7}' | python -m json.tool | head -20

# 4. Bắt đầu phiên
curl -s -X POST "http://127.0.0.1:8000/sessions/$SID/start" -o /dev/null -w "start: %{http_code}\n"

# 5. Gửi người xem + bình luận CÓ số điện thoại (kiểm tra lọc PII)
curl -s -X POST "http://127.0.0.1:8000/sessions/$SID/ticks" \
  -H 'Content-Type: application/json' -d '{"viewers":120}' -o /dev/null
curl -s -X POST "http://127.0.0.1:8000/sessions/$SID/comments" \
  -H 'Content-Type: application/json' -d '{"text":"0901234567 ship ve Go Vap"}'
```

**Kết quả đúng ở bước 3:** 10 khối, `n_on` + `n_off` = 10, tỷ lệ gần 50/50, mỗi khối
có `propensity: 0.5`. Chạy lại cùng `seed` cho ra **đúng lịch cũ** — đây là điều
giám khảo sẽ hỏi: chứng minh ngẫu nhiên hóa không bị can thiệp.

**Kết quả đúng ở bước 5:** bình luận trả về đã bị che:
`"[SĐT] ship ve [ĐỊA CHỈ]"`, `pii_kinds: ["address","phone"]`.
Số điện thoại gốc **không bao giờ** chạm ổ cứng.

### Kiểm tra các quy tắc bảo vệ thí nghiệm

```bash
# Can thiệp tay với lý do KHÔNG hợp lệ -> phải bị từ chối (422)
curl -s -o /dev/null -w "ly do sai: %{http_code}\n" \
  -X POST "http://127.0.0.1:8000/sessions/$SID/actions/override" \
  -H 'Content-Type: application/json' -d '{"reason":"tui thich the"}'

# Lý do hợp lệ -> chấp nhận (200)
curl -s -o /dev/null -w "ly do dung: %{http_code}\n" \
  -X POST "http://127.0.0.1:8000/sessions/$SID/actions/override" \
  -H 'Content-Type: application/json' -d '{"reason":"hết hàng"}'

# Gõ nhầm mã phiên -> 404 tiếng Việt, KHÔNG phải 500
curl -s -o /dev/null -w "id sai: %{http_code}\n" http://127.0.0.1:8000/sessions/nope-123
```

Kết quả đúng: `422` · `200` · `404`.

### Kết thúc và chấm điểm chất lượng dữ liệu

```bash
curl -s -X POST "http://127.0.0.1:8000/sessions/$SID/end" -o /dev/null
.venv/Scripts/livelift-qc.exe --session-id "$SID"
```

Kết quả đúng: **PASS cả 6 mục**.

```
[PASS] block_integrity: 10 khối khớp lịch gán
[PASS] assignment_balance: ON share = 0.50
[PASS] event_continuity: max gap = 3s
[PASS] intervention_log_complete: ok
[PASS] pii_clean: sampled 1; leaks: 0
[PASS] order_reconciliation: platform total is zero
```

`block_integrity` là mục quan trọng nhất: nó đối chiếu lịch bốc thăm **lưu trước khi
phát** với các khối **thực sự đã chạy**. Khớp = ngẫu nhiên hóa không bị sửa giữa chừng.

---

## 3. Kiểm chứng phần khoa học — thứ quyết định giải thưởng

### 3.1 Bộ mô phỏng tự chứng minh ước lượng viên đúng

Tạo phiên ảo có tác động **biết trước**, chạy toàn bộ pipeline, xem hệ thống có tìm
lại đúng con số không:

```bash
.venv/Scripts/livelift-simulate.exe --reps 20 --sessions 5 --effect 0.3 --draws 300
```

Kết quả thật đã chạy (27/08):

```
reps=20 sessions/rep=5
mean estimate      : +0.3117
mean true effect   : +0.3133
relative bias      : -0.5%
95% CI coverage    : 90.0%
rejection rate     : 90.0%
```

Tác động cấy vào là 0.3133, hệ thống tìm lại 0.3117 — **sai lệch 0.5%**.
Đây là bằng chứng "ước lượng viên đã hiệu chỉnh" — mạnh hơn nhiều so với chỉ nói
"chúng em mở một cửa hàng".

Chạy bộ kiểm chứng thống kê đầy đủ (chậm, vài phút):

```bash
.venv/Scripts/python.exe -m pytest tests -m slow -q
```

Ba tiêu chí: A/A giả dương ≈ 5% · sai lệch < 10% · CI coverage 88–99%.

### 3.2 Lịch bốc thăm tái lập được

```bash
.venv/Scripts/livelift-schedule.exe --duration 90 --block 5 --seed 42 --out s1.json
.venv/Scripts/livelift-schedule.exe --duration 90 --block 5 --seed 42 --out s2.json
diff s1.json s2.json && echo "GIONG HET - tai lap duoc"
rm -f s1.json s2.json
```

### 3.3 Toàn bộ test tự động

```bash
.venv/Scripts/python.exe -m pytest tests -m "not slow" -q
```

Kết quả đúng: **119 passed**.

---

## 4. Phân tích video livestream có sẵn

### Làm được gì, không làm được gì — nói thẳng

| Loại link | Phân tích bình luận | Thí nghiệm |
|---|---|---|
| **YouTube VOD live đã xong, còn chat replay** | ✅ Được | ❌ Không |
| YouTube đang live | ✅ Được (cần API key) | ❌ Không (phòng người khác) |
| Facebook của người khác | ❌ Không có đường hợp pháp | ❌ Không |
| Video bán hàng không có chat | ❌ Không có tín hiệu nào | ❌ Không |

**Vì sao video người khác không test được phần thí nghiệm:** thí nghiệm cần quyền
*quyết định* ghim sản phẩm nào vào lúc nào, rồi so sánh với nhánh đối chứng. Video đã
quay xong thì không ai can thiệp ngược thời gian được. Đây là giới hạn logic, không
phải giới hạn của phần mềm.

**Không biết họ bán gì có sao không?** Không. Phần phân tích được (ý định bình luận,
lọc PII, nhịp bình luận) chỉ đọc văn bản bình luận, không cần danh mục sản phẩm.

Kết quả phân tích video ngoài **luôn được dán nhãn "PHÂN TÍCH QUAN SÁT — không phải
thí nghiệm"**. Nếu hệ thống hiện số nhân quả cho dữ liệu quan sát, chính giám khảo sẽ
dùng điều đó để đánh rớt dự án.

### Cách dùng

Trang chính → ô số 2 → dán link → bấm phân tích. Hoặc bằng lệnh:

```bash
JOB=$(curl -s -X POST http://127.0.0.1:8000/replays/youtube \
  -H 'Content-Type: application/json' \
  -d '{"url":"https://www.youtube.com/watch?v=XXXXXXXXXXX"}' \
  | python -c 'import sys,json;print(json.load(sys.stdin)["job_id"])')
curl -s "http://127.0.0.1:8000/replays/jobs/$JOB"
```

**Nếu gặp lỗi "YouTube yêu cầu xác minh không phải bot":** mở `.env`, thêm dòng
`YTDLP_COOKIES_FROM_BROWSER=chrome` (hoặc `edge`/`firefox` — trình duyệt bạn đã đăng
nhập YouTube), rồi `docker compose up -d`. Cookie chỉ được đọc cục bộ, không gửi đi
đâu ngoài chính YouTube.

---

## 5. Bảng khả năng hiện tại — trung thực

### Dùng được ngay trên giao diện
- Xem thử bằng dữ liệu mô phỏng (1 cú bấm)
- Bàn điều khiển 3 vùng, dải khối BẬT/TẮT, thẻ hành động
- Màn hình host làm mù
- Phát lại phiên + phân tích video YouTube
- **Trang kết quả thí nghiệm** (tác động, KTC, p-value, bảng MDE)

### Chỉ dùng được bằng lệnh (chưa có nút)
- Tạo sản phẩm, tạo phiên, bốc lịch gán, bắt đầu/kết thúc phiên
- Tạo link rút gọn để đo lượt bấm
- Chấm chất lượng dữ liệu (`livelift-qc`)

> Đây là hạn chế đã biết: **toàn bộ vòng đời một phiên thí nghiệm vẫn phải chạy bằng
> lệnh.** Giao diện hiện là màn hình xem + demo. Với Live Lab của nhóm thì chấp nhận
> được (kỹ sư ngồi cạnh), nhưng trước khi giao cho nhà bán ngoài thì phải làm nốt.

### Chưa có
- Nhập đơn hàng / doanh thu (bảng `order_event` tồn tại nhưng không có API ghi)
- Mô hình dự báo người xem (Model A — theo kế hoạch tuần 3–4, cần dữ liệu phiên thật)
- Phân loại ý định bằng ViSoBERT (đang dùng baseline từ khóa; cần 2–3k bình luận thật)

---

## 6. Khi gặp lỗi

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| `failed to connect to the docker API` | Docker Desktop chưa chạy | Mở Docker Desktop, chờ xanh |
| Trang web trắng / dữ liệu cũ | Trình duyệt cache | Ctrl+Shift+R |
| Lệnh CLI treo lâu | `.env` dùng `localhost` thay vì `127.0.0.1` | Sửa `.env` (đã sửa sẵn; xem sự cố 27/08) |
| CLI in ra ký tự lạ | Console Windows cp1252 | Không ảnh hưởng dữ liệu; đã ép UTF-8 cho CLI |
| API trả 500 | Lỗi thật | Xem `docker compose logs api --tail 50`, báo lại |

Mọi lỗi đã gặp và cách sửa được ghi tại [docs/incident-log.md](incident-log.md) —
kèm root cause và test chặn tái diễn.
