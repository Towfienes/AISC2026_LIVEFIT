# Gán mù bằng người — 393 dòng tập test lô 2 (chuẩn bị 25/09/2026)

**Trạng thái 25/09/2026: bảng đã sinh, CHƯA phát, CHƯA có nhãn người nào.** Mọi con
số NLP hiện có vẫn là mức đồng thuận với nhãn tham chiếu do **tác tử AI (Claude)** gán
ngày 09/09/2026 (đính chính 15/09, `docs/incident-log.md`). Việc này mở khoá K-05/T-07
trong `docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md` (mã việc M-04).

## Tệp và nơi để

| Tệp | Ở đâu | Có bình luận? | Phát cho người gán? |
|---|---|---|---|
| `bang-nguoi-gan-1.csv`, `bang-nguoi-gan-2.csv` | `D:/AISC2026/gan-mu-2509/` (ngoài repo) | có (đã lọc PII) | có, mỗi người một bảng |
| `huong-dan-gan-nhan.md` | như trên + bản sao ở thư mục này | không | có |
| `khoa/khoa-gan-mu.csv` (mã mù → uid lô 2) | `D:/AISC2026/gan-mu-2509/khoa/` | không | **không** |
| `khoa/seed-gan-mu.json` (seed bí mật) | `D:/AISC2026/gan-mu-2509/khoa/` | không | **không** |
| `manifest.json` (băm, không có seed) | `D:/AISC2026/gan-mu-2509/` | không | không cần |
| `*.sha256` | thư mục này (trong repo) | không | — |

Hai bảng có **cùng 393 mã mù** nhưng **thứ tự xáo trộn khác nhau**. Bảng chỉ gồm
`stt, ma_dong, binh_luan, nhan, ghi_chu`: không nhãn AI, không dự đoán của mô hình,
không tên buổi, không tầng rút mẫu. Mã cũ `A0019`/`B0304` lộ tầng (A = rút theo dự
đoán, B = ngẫu nhiên) nên không xuất hiện trong bảng. CSV là UTF-8 có BOM, xuống dòng
CRLF để Excel mở đúng tiếng Việt.

Sinh (seed mặc định là **bí mật**, rút từ `secrets`):

```bash
.venv/Scripts/python scripts/gan_mu/tao_bang_gan_mu.py --ra D:/AISC2026/gan-mu-2509
# sinh lại đúng từng byte: thêm --seed <seed_ma_mu trong khoa/seed-gan-mu.json>
```

**Seed giữ bí mật tới khi công bố `kappa.json`**, chỉ nằm ở `khoa/seed-gan-mu.json`
(không phát, không commit); công bố seed cùng kết quả để ai cũng tái lập được bảng và
đối chiếu với băm đã commit. Lý do: danh sách được xáo trộn là `to_label.txt` sắp theo
uid, mọi uid `A…` đứng trước `B…`. Bản sinh đầu tiên (25/09, seed cố định **20260925**
ghi trong mã nguồn) vì vậy cho phép **tính ngược tầng A/B của từng dòng** từ vị trí dòng
hoặc mã mù mà không cần dữ liệu nào — phản biện 25/09 kiểm: đúng **393/393** dòng ở cả hai
bảng. Bộ bảng đó đã bị thay bằng bộ sinh với seed bí mật **trước khi phát**; băm ở thư
mục này là của bộ mới.
Văn bản lấy từ `data/labeling/lot2-da-nguon-10-09/to_label.txt` **sau khi lọc lại PII
ngày 25/09** (`scripts/gan_mu/loc_lai_pii.py`, 57 tên tài khoản → 0).

## Quy trình (thứ tự bắt buộc)

1. **Commit các tệp `*.sha256` ở thư mục này TRƯỚC khi phát bảng.** Băm chứng minh
   bảng và khoá không bị sửa sau khi đã thấy nhãn người.
2. Phát cho mỗi người **một** bảng + `huong-dan-gan-nhan.md`. Không phát thư mục
   `khoa/` (khoá + seed), không phát `data/labeling`. Đề xuất theo `09-PHAN-CONG.md`: bảng 1 → Khánh (K-05),
   bảng 2 → Tiến (T-07). Trưởng nhóm quyết định.
3. Người gán làm độc lập, không dùng AI, không trao đổi với nhau cho tới khi cả hai đã
   nộp (quy tắc ghi trong hướng dẫn).
4. Khi nhận bảng đã gán: băm SHA-256 từng tệp và **đăng băm** (issue hoặc commit)
   trước khi chạy bước 5.
5. Chạy `scripts/tinh_kappa.py` (lệnh ở cuối). Công bố `kappa.json` + `kappa.md` **dù
   số tăng hay giảm**.

Kiểm băm (Git Bash):

```bash
cd D:/AISC2026/gan-mu-2509 && sha256sum bang-nguoi-gan-1.csv bang-nguoi-gan-2.csv huong-dan-gan-nhan.md khoa/khoa-gan-mu.csv
cat D:/AISC2026/livelift/docs/benchmarks/intent-eval/gan-mu/*.sha256
```

## Quy tắc đọc kết quả — chốt TRƯỚC khi có nhãn người

Chốt ngày 25/09/2026, cùng lúc với `scripts/tinh_kappa.py`, để không ai chọn cách tính
sau khi đã biết số:

1. **Con số chính:** Cohen κ người–người trên toàn bộ dòng cả hai cùng gán hợp lệ, kèm
   KTC95 bootstrap theo dòng (2.000 lần, seed 2026). Diễn giải theo thang Landis & Koch
   (1977) chỉ để đọc, không phải ngưỡng đạt/trượt.
2. κ người–AI tính **riêng cho từng người** (nhãn AI = `gold.txt` lô 2), không gộp.
3. **Chấm lại B0–C2:** tham chiếu CHÍNH là tập dòng hai người **đồng ý** với nhau. In
   kèm điểm theo từng người, và điểm theo nhãn AI trên **đúng tập dòng đó**, để so cặp.
4. Mặc định `--nhan-train ai`: dự đoán y hệt lần chạy công bố (hàm chung
   `eval_intent.predict_out_of_fold`), chỉ đổi nhãn dùng để CHẤM. `--nhan-train nguoi`
   là phân tích phụ: nhãn train lô 2 được thay bằng nhãn của **chính tham chiếu đang
   chấm** (tham chiếu người → nhãn người; hai tham chiếu "AI, …" → vẫn là nhãn AI), chỉ
   trên các dòng có trong tham chiếu đó. Phải ghi rõ khi trích.
5. Bảng còn dòng trống, nhãn ngoài 11 lớp hoặc mã dòng lạ thì script **dừng** (mã thoát
   2) và nêu mã dòng. Không tự bỏ dòng.
6. C3 không chấm lại: cấu hình từ chối trả lời tự chọn ngưỡng đã bị loại (03-NLP §6.2).

```bash
.venv/Scripts/python scripts/tinh_kappa.py \
    --bang1 <bảng người 1 đã gán> --bang2 <bảng người 2 đã gán> \
    --khoa  D:/AISC2026/gan-mu-2509/khoa/khoa-gan-mu.csv --cham-lai
```

Script đọc được CSV lưu từ Excel bằng dấu `,` hoặc `;`, UTF-8 (có/không BOM) hoặc
cp1258; nhãn điền bằng mã (`hoi_gia`) hoặc số 1–11.

## Giới hạn đã biết trước

- 193/393 dòng thuộc tầng rút theo **dự đoán của mô hình v1**, nên giàu nhãn hành động
  một cách nhân tạo; người gán không biết dòng nào thuộc tầng nào (điều này chỉ đúng khi
  seed còn bí mật — xem mục seed ở trên). Con số vận hành đọc ở
  tầng ngẫu nhiên (200 dòng).
- Hai người gán đều là thành viên đội, không phải người gán độc lập bên ngoài.
- Hướng dẫn giữ quy tắc định trước của lô 2 "ca mơ hồ → chọn lớp hành động" để người
  và AI được so trên cùng luật; quy tắc này làm mọi con số nghiêng về phía có lợi cho
  mô hình.
