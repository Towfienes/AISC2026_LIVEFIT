# Q&A kỹ thuật — AISC Round 2

## “Đã có kết quả thí nghiệm thật chưa?”

Chưa. Fact sheet ghi 0 phiên randomized thật. Replay/VOD chứa bình luận thật
nhưng chỉ là quan sát; Demo Vàng là mô phỏng và luôn mang nhãn.

## “Vì sao trang kết quả lại cho xem demo?”

Trang vẫn tải `env=real` mặc định và hiển thị trạng thái chưa đủ thật. CTA chỉ
giúp mở ba trạng thái mẫu để trình bày UX; nó không redirect và không đưa demo
vào pooled real result.

## “Statistical CI coverage có phải code coverage?”

Không. Statistical CI coverage đến từ calibration Monte-Carlo và trả lời KTC
có chứa hiệu ứng thật hay không. Python code coverage đến từ pytest-cov và chỉ
cho biết dòng mã nào được test đi qua.

## “Order ingestion đã có chưa?”

Có endpoint ghi từng đơn và import CSV chống trùng. Chưa có evidence đơn hàng
thật trong fact sheet, nên không claim performance hoặc doanh thu đã kiểm chứng.

## “Background ingest và storage đã làm tới đâu?”

`IngestManager` chạy trong API và có thể được điều khiển từ web. Memory snapshot
có thể lưu/nạp trạng thái cục bộ, nhưng `/health durable=false` vẫn phải được
đọc là không tương đương Postgres. Phiên thật yêu cầu durable Postgres run.

## “Autopilot có tự ghim trên nền tảng không?”

Autopilot nội bộ có scheduler/heartbeat và ghi exposure cho khối BẬT. Không
được nói nó đã production-pin thành công trên mọi nền tảng. Shopee có adapter
`update_show_item`, nhưng việc nối production, credential và live-fire tương
ứng chưa có evidence trong package này.

## “Intent v2 có được bật để demo đẹp hơn không?”

Không. V2 không trở thành mặc định và không train model trong phase này. Fast
suite hiện còn blocker version giữa artifact và scikit-learn; đó là FAIL được
công khai, không phải lý do mở rộng scope.

## “Preflight PASS có nghĩa UI chắc chắn dùng được không?”

Không. Preflight chỉ kiểm reachability và API contract. UI correctness cần
existing browser tests, production build và manual rehearsal riêng.

## “Tại sao chưa tự chạy một pilot thật?”

Credential chính thức, đối tác/người xem và vận hành phiên là human-dependent
P0. Codex không tạo/fake evidence này. Đội nên thử ít nhất một pilot end-to-end
trước Round 2 nếu khả thi; cho tới lúc đó con số vẫn là 0.
