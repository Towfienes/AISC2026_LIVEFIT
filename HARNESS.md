# HARNESS.md — Quy trình phát triển LiveLift

Tài liệu này định nghĩa **harness** của dự án: vòng lặp làm việc, các quality gate tự động, quy trình tìm root cause, và cách kiến thức nghiên cứu đi vào mã nguồn. Mọi thành viên và mọi PR đều đi qua harness này — không có ngoại lệ, kể cả khi gấp.

---

## 1. Vòng lặp phát triển (mỗi việc E*-**)

```
   ┌─────────────────────────────────────────────────────────────┐
   │  1. HIỂU     đọc issue + tiêu chí nghiệm thu, hỏi nếu mơ hồ │
   │  2. NGHIÊN CỨU  nếu chạm phương pháp: đọc paper/tài liệu,   │
   │                 ghi 5 dòng tóm tắt vào docs/research-log.md │
   │  3. THIẾT KẾ  viết chữ ký hàm + test TRƯỚC khi viết thân    │
   │  4. LẬP TRÌNH  code nhỏ, thuần (pure) ở lõi, I/O ở rìa      │
   │  5. KIỂM THỬ  pytest cục bộ; module thống kê PHẢI qua       │
   │               thẩm định trên mô phỏng có tác động biết trước │
   │  6. TỰ SOÁT   ruff + mypy + chạy lại từ sạch                │
   │  7. PR        người thứ hai duyệt; CI xanh mới được merge   │
   │  8. NGHIỆM THU  đối chiếu đúng tiêu chí ghi trong issue     │
   └─────────────────────────────────────────────────────────────┘
```

**Nguyên tắc kiến trúc cho testability:** mọi logic quyết định (gán khối, chọn ứng viên, lọc PII, tính đặc trưng, ước lượng) là **hàm thuần** — nhận dữ liệu, trả dữ liệu, không đọc DB, không đọc đồng hồ, không tự sinh ngẫu nhiên ngoài RNG được truyền vào. Nhờ đó test được 100% mà không cần hạ tầng. I/O (DB, Redis, API nền tảng) nằm ở lớp mỏng bên ngoài.

## 2. Quality gates — CI đỏ là không merge

| Gate | Ngưỡng | Vì sao tồn tại |
|---|---|---|
| `pytest -m "not slow"` | 100% pass | hồi quy cơ bản |
| `pytest -m slow` (nightly + trước release) | 100% pass | thẩm định thống kê trên mô phỏng |
| **PII recall** trên `tests/data/pii_comments.jsonl` | ≥ 95% từng loại (SĐT, email, mã đơn, địa chỉ) | quy tắc bất di bất dịch 1.4; luật 91/2025/QH15 |
| **Cân bằng gán**: 1000 lịch sinh thử | tỷ lệ BẬT trong [0.45, 0.55], cân bằng theo giai đoạn | tiêu chí E3-01 |
| **Thẩm định ước lượng viên**: mô phỏng tác động biết trước | bias < 10% tác động; coverage CI 95% trong [90%, 98%] | tiêu chí E3-06/07 — con số sai còn tệ hơn không có số |
| **Cách ly VLiveBench**: quét import | 0 import từ `src/` sang `collectors/` | kiến trúc không phụ thuộc (mục 8.5 mô tả dự án) |
| **Quy tắc nguồn con số** (E2-04): test giao diện | thẻ từ mô hình không bao giờ hiện "khoảng tin cậy" | quy tắc chống overclaim cấp giao diện |
| `ruff check` + `ruff format --check` | 0 lỗi | nhất quán, đọc được |
| Migration | `up` rồi `down` rồi `up` lại thành công trên DB sạch | tiêu chí E1-02 |

## 3. Quy trình lỗi: phát hiện → root cause → fix

Khi có lỗi (test đỏ, số liệu bất thường, sự cố trong phiên):

1. **Tái hiện tối thiểu.** Thu nhỏ về input nhỏ nhất còn gây lỗi. Với lỗi dữ liệu phiên: trích `session_id` + khoảng thời gian vào một fixture.
2. **Root cause, không phải triệu chứng.** Trả lời bằng chứng cứ: *cơ chế nào* sinh ra trạng thái sai? Dùng "5 whys" đến khi chạm quyết định thiết kế hoặc giả định sai. Cấm fix kiểu "thêm if chặn giá trị lạ" khi chưa biết giá trị lạ từ đâu ra.
3. **Test trước, fix sau.** Viết test tái hiện lỗi (đỏ) → sửa (xanh). Test đó ở lại vĩnh viễn.
4. **Ghi sổ.** Một dòng vào `docs/incident-log.md`: ngày, triệu chứng, root cause, commit fix. Lỗi trong phiên live ghi thêm vào nhật ký phiên (phụ lục B kế hoạch).
5. **Hỏi lớp phòng thủ.** Lỗi này lọt qua gate nào? Có cần gate mới không?

**Riêng dữ liệu thí nghiệm:** nếu lỗi làm hỏng dữ liệu của khối/phiên đã chạy → khối đó bị đánh dấu loại (`excluded_reason`), KHÔNG sửa số liệu. Quyết định loại ghi vào phụ lục phân tích. Không bao giờ "sửa tay" bản ghi thí nghiệm.

## 4. Vòng nghiên cứu → mã nguồn

Phương pháp không được vào code từ trí nhớ. Đường đi bắt buộc:

1. Đọc paper / tài liệu gốc → tóm tắt 5–10 dòng vào `docs/research-log.md` (mỗi mục: nguồn, điều dùng được, điều KHÔNG áp dụng được cho bối cảnh mình, quyết định).
2. Nếu thay đổi thiết kế thí nghiệm/ước lượng viên: cập nhật thẳng vào thiết kế **trước tuần 6**; sau tuần 6 chỉ được thêm dưới nhãn "phân tích khám phá hậu nghiệm".
3. Mọi công thức trong `analysis/` có docstring dẫn nguồn (tác giả, năm, công thức số mấy).

## 5. Vòng sản phẩm → cải thiện

Sau mỗi phiên live (quy trình mục 6 kế hoạch), ngoài QC dữ liệu tự động:

- **Ghi chú vận hành 3 dòng** của trung control: điều gì vướng tay, thẻ nào bị bỏ qua và vì sao, màn hình thiếu gì.
- Thứ Hai hằng tuần: gom ghi chú → tối đa **2 cải tiến UX nhỏ**/tuần được đưa vào backlog (giới hạn 2 để giai đoạn thí nghiệm ít thay đổi mã — mục tiêu của giai đoạn 2 là dữ liệu, không phải tính năng).
- Thay đổi ảnh hưởng hành vi hệ thống trong khối thí nghiệm (logic thẻ, logic gán) sau tuần 6: **cấm**, trừ lỗi an toàn, và phải ghi vào nhật ký thay đổi thí nghiệm.

## 6. Quy ước mã nguồn

- Nhánh: `<mã-việc>-mô-tả-ngắn` (vd `e3-01-outer-assigner`). `main` luôn chạy được `docker compose up`.
- Commit message: dòng đầu ≤ 72 ký tự, tiếng Việt hoặc Anh nhất quán trong một PR.
- Python: type hints bắt buộc ở API công khai của module; docstring cho mọi hàm thuộc lõi thống kê.
- Seed ngẫu nhiên: mọi RNG nhận seed tường minh; seed của lịch gán lưu vào DB cùng lịch.
- Notebook: chỉ ở `analysis/`; strip output trước khi commit; notebook không chứa logic — logic ở `src/livelift/analysis/`, notebook chỉ gọi và vẽ.
- Múi giờ: DB lưu UTC (`timestamptz`); hiển thị Asia/Ho_Chi_Minh ở tầng UI. Không có datetime naive trong code.

## 7. Định nghĩa hoàn thành (nhắc lại từ kế hoạch §1.3)

Một việc chỉ xong khi: (1) đạt tiêu chí nghiệm thu trong issue, (2) người thứ hai xác nhận, (3) nếu là mã: đã merge vào `main` và `docker compose up` từ máy trắng chạy được, (4) nếu là dữ liệu: qua bộ QC mục 8.3.
