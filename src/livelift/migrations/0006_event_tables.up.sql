-- Tách assignment / exposure thành hai bảng SỰ KIỆN chỉ-ghi-thêm (gói Q3, 08/09).
--
-- Vì sao tách: cho tới nay "được gán" và "thực sự được phơi nhiễm" nằm chung
-- trong experiment_block + intervention_log — hai bảng CÓ THỂ cập nhật
-- (override_count, compliance_rate, recount click). Trộn ý định thí nghiệm với
-- việc thực thi làm mất khả năng kiểm chứng: không ai chứng minh được lịch gán
-- lúc phát sóng đúng bằng lịch đã sinh. PlanOut (Bakshy, Eckles & Bernstein,
-- WWW 2014) tách "gán" khỏi "phơi nhiễm" đúng vì lý do này; Fabijan et al.
-- (KDD 2019) coi log phơi nhiễm bất biến là điều kiện của tin cậy thí nghiệm.
--
--  * assignment_event : TOÀN BỘ lịch, materialize một lần tại thời điểm sinh
--                       schedule (trước phát sóng). Ý ĐỊNH thí nghiệm.
--  * exposure_event   : điều bàn điều khiển thực sự làm (ghim/bỏ ghim) và biên
--                       khối. THỰC TẾ vận hành.
--
-- CHỈ-GHI-THÊM: tầng ứng dụng không có method update/delete cho hai bảng này
-- (livelift.api.store — cả hai backend). Thu hồi quyền UPDATE/DELETE ở DB role
-- là việc của deploy, không làm trong migration này.
--
-- ITT KHÔNG ĐỔI: estimand vẫn theo assignment (experiment_block). Hai bảng này
-- phục vụ đối chiếu tuân thủ (derive_compliance) và dấu vết kiểm chứng —
-- flag-don't-drop, không bao giờ dùng để sửa dữ liệu khối đã chạy.

CREATE TABLE assignment_event (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id    uuid NOT NULL REFERENCES live_session(session_id) ON DELETE CASCADE,
    block_idx     integer NOT NULL,
    -- NULL cho khối washout (giống experiment_block.assignment)
    assignment    text CHECK (assignment IN ('ON','OFF')),
    block_start_s integer NOT NULL,
    block_end_s   integer NOT NULL,
    -- Lịch được phép SINH LẠI khi phiên còn planned/scheduled, và bảng này
    -- không xóa row cũ; design_hash gắn mỗi row vào đúng lần rút thiết kế của
    -- nó, nếu không hai lần rút sẽ trộn lẫn và tỷ lệ tuân thủ đếm sai.
    design_hash   text NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    CHECK (block_end_s > block_start_s)
);
CREATE INDEX idx_assignment_event_session ON assignment_event (session_id, design_hash, block_idx);

CREATE TABLE exposure_event (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id     uuid NOT NULL REFERENCES live_session(session_id) ON DELETE CASCADE,
    -- NULL khi hành động rơi ngoài mọi khối (override lúc chưa phát/đã kết thúc)
    block_idx      integer,
    event_type     text NOT NULL CHECK (event_type IN ('pin','unpin','block_start','block_end')),
    product_id     text REFERENCES product(product_id),
    ts_utc         timestamptz NOT NULL DEFAULT now(),
    -- Độ trễ từ lúc bàn bấm tới lúc máy chủ ghi nhận; NULL khi client không gửi
    -- client_ts (bàn hiện chưa gửi — xem followups).
    ack_latency_ms integer,
    -- 'system' dành cho hook biên khối (block_start/block_end) của auto-executor.
    source         text NOT NULL CHECK (source IN ('model','human','holdback','system'))
);
CREATE INDEX idx_exposure_event_session_ts ON exposure_event (session_id, ts_utc);
