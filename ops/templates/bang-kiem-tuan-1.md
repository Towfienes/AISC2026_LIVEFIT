# Bảng kiểm tuần 1 (kế hoạch phụ lục D, cập nhật theo nghiên cứu 24/08)

*Rà soát cuối tuần 1 (31/08/2026). Mỗi mục có người phụ trách; mục chưa xong chuyển thành
issue có deadline.*

## Nền tảng & pháp lý

- [ ] **Facebook app đã tạo và để ở Development Mode; đọc được bình luận Live trên Page
      của chính nhóm — KHÔNG cần App Review.** Toàn bộ thành viên nhóm được thêm vai trò
      admin/developer/tester của app và admin của Page Live Lab. Live Lab chạy được ngay
      từ hôm nay. *(Cập nhật nghiên cứu: App Review / Advanced Access chỉ cần cho Page
      đối tác ở tuần 8 — xem mục dưới.)*
- [ ] Hồ sơ Meta App Review (Advanced Access, phục vụ Page **đối tác**) đã chuẩn bị song
      song: Business Verification bắt đầu, screencast + privacy policy nháp; kế hoạch nộp
      trong tháng 9 (timeline thực tế 2–7 ngày sạch, đến ~20 ngày, mỗi lần reject reset
      đồng hồ — budget 4–6 tuần).
- [ ] Page đã lập, thông tin đầy đủ, có thông báo xử lý dữ liệu.
- [ ] YouTube: project Google Cloud tạo xong, API key hoạt động, adapter dự kiến dùng
      `liveChatMessages.streamList` (không polling `list`, không `search.list`).

## Vận hành & hàng hóa

- [ ] Mặt hàng đã chốt, đã đặt lô đầu, có bảng biên lợi nhuận từng SKU.
- [ ] Đã gửi 10 thư mời đối tác dữ liệu (mẫu `ops/templates/thu-moi-doi-tac.md`), có bảng
      theo dõi phản hồi.
- [ ] Phân công đóng gói – giao hàng cho kịch bản ≥8 đơn/phiên (không dồn một người).

## Hạ tầng

- [ ] VPS chạy, `docker compose up` thành công từ máy trắng.
- [ ] Lược đồ CSDL bản đầu, migration `up` → `down` → `up` chạy được trên DB sạch.
- [ ] Backup hằng ngày hoạt động (container `backup` ghi file vào `./backups`).

## Dữ liệu & phân tích

- [ ] Đã tải **KuaiLive** (Zenodo 16565801, kiểm MD5) và **LiveRec/Twitch**; notebook
      phân tích khám phá đã bắt đầu trong `analysis/exploration/`. *(Cập nhật nghiên cứu:
      **bỏ LSEC** — không timestamp tài liệu hóa, không license.)*
- [ ] Bộ 200 bình luận mẫu đã gán nhãn cho bộ kiểm thử PII (`tests/data/pii_comments.jsonl`).
- [ ] Kế hoạch đo t_mix tuần 3 đã viết nháp (impulse response tỷ lệ nhấp sau bỏ ghim).

## Giao diện & quy trình

- [ ] Khung giao diện bàn trung control chạy được trên localhost; route `/host` tách riêng
      và **không chứa thông tin khối** (kiểm bằng mắt + test giao diện).
- [ ] GitHub Projects đã tạo, toàn bộ việc E1–E6 đã thành issue có người phụ trách.
- [ ] Cả nhóm đã đọc `ops/runbooks/quy-trinh-phien.md` và HARNESS.md.
