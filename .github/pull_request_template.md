<!-- Mẫu PR của LiveLift. Quy trình đầy đủ: docs/competition/sang-tao-tre-2026/09-PHAN-CONG.md
     Xoá các dòng hướng dẫn trong ngoặc khi điền. Ô nào không áp dụng thì ghi "không áp dụng". -->

## Việc gì

- Người làm (tên thật):
- Mã việc (ví dụ K-06):
- Làn: minh / khanh / tien
- Tóm tắt 1–3 câu:

## Tự viết / AI hỗ trợ / nguồn mở — kê khai theo Điều 5 Thể lệ

- Phần tôi tự viết, hiểu và giải thích được trước hội đồng:
- Phần do AI sinh (công cụ + mô hình + mức độ):
- Phiên Prompt Log (session id, hoặc tên tệp log trên máy tôi):
- Phần kế thừa nguồn mở (thư viện, trích mã, giấy phép):
- [ ] Trailer commit đúng: `Co-Authored-By:` đúng tên mô hình / `AI-Assisted:` / `Co-authored-by:` chỉ cho người thật sự cùng làm
- [ ] **Không có nhãn, dữ liệu, câu mẫu hay số liệu nào do AI tạo mà được ghi là người làm**

## Lệnh đã chạy (bắt buộc — dán dòng tổng kết và `git rev-parse HEAD`)

- [ ] `pytest -m "not slow" -q` →
- [ ] `ruff check . && ruff format --check .` →
- [ ] Nếu chạm `web/`: `cd web && npx tsc --noEmit` →
- [ ] Nếu chạm `core/`, `analysis/`, `sim/`: `pytest -m slow <tệp liên quan>` →
- [ ] Lệnh nghiệm thu chính của việc + kết quả:
- [ ] Đối chứng âm (nếu nghiệm thu yêu cầu): làm hỏng tạm thì test đỏ — dán log, KHÔNG commit bản hỏng
- [ ] Script mới trong `scripts/` có gọi `livelift.console.configure()`
- [ ] CI chưa chạy được → đã dán kết quả test (phương án B)

## Hợp đồng và tệp dùng chung

- [ ] Không đổi hợp đồng C-1…C-12, HOẶC đã gắn nhãn `hop-dong` và ghi hợp đồng nào: ___
- [ ] Mọi tệp trong diff thuộc làn của tôi (`git diff --name-only origin/main...HEAD`)
- [ ] Không thêm migration (đóng băng tới 30/09)
- [ ] `git diff --quiet origin/main -- web/tsconfig.json` (không lọt dòng `.next-*` tự chèn)
- [ ] Route ghi mới (nếu có) đã có hàng trong `BANG_MUC_BAO_VE`

## Số công bố

- [ ] PR này KHÔNG đổi số, HOẶC ghi rõ số nào đổi, tệp nguồn và lệnh sinh lại:
- [ ] Không tự sửa `README.md`, `FACT-SHEET.md`, hằng PROOF — Minh cập nhật trong cửa sổ tích hợp
- [ ] Không gõ tay số vào tài liệu nộp

## Hàng sự cố đề xuất (nếu PR sửa lỗi — KHÔNG tự thêm vào `docs/incident-log.md`)

`| dd/mm/yyyy | triệu chứng | nguyên nhân gốc | cách sửa | cổng mới chặn tái diễn |`

## Giao diện (bắt buộc nếu đổi `web/`)

- [ ] Ảnh chụp trước/sau hoặc trace Playwright đính kèm
- [ ] Nhãn DEMO/THẬT vẫn theo `is_demo`
- [ ] Không ghi đè hay xoá ảnh cũ trong `docs/img/`

## Dữ liệu cá nhân và bí mật

- [ ] Đã dùng `git add <đường dẫn cụ thể>` + `git diff --cached --stat`, KHÔNG dùng `git add -A`
- [ ] Không commit: `.env`, `thong-tin-doi.local.json`, `data/labeling/*`, `data/snapshot/`, `backups/`, bản sao log AI, phiếu đồng ý, giấy xác nhận SV
- [ ] Dữ liệu test chỉ là dữ liệu tổng hợp: không có tên tài khoản, SĐT, MSSV, email thật
- [ ] Nếu tôi là người gán nhãn mù: tôi chưa mở `results.json`/`results.md` trước khi đăng băm nhãn của mình

## Người duyệt

- Làn thuần: Khánh ↔ Tiến. Chạm hợp đồng hoặc tệp của Minh: thêm Minh (cửa sổ 12:00 hoặc 22:00).
- Người duyệt ghi lại lệnh nghiệm thu đã tự chạy:
