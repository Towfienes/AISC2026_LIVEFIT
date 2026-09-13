/**
 * Chọn "phiên hiện tại" từ danh sách phiên — dùng chung cho bàn trợ live và
 * màn hình người dẫn.
 *
 * VÌ SAO FILE NÀY TỒN TẠI (bug đồng hồ 328:36:29 trên /host, gói DESK-HOST):
 * cả useHost lẫn useDesk từng chọn `list.find(s => s.status === "live")` —
 * phần tử live ĐẦU TIÊN theo thứ tự tạo. Kho postgres bền còn giữ nhiều phiên
 * mô phỏng cũ (29/08) chưa bao giờ được kết thúc, vẫn mang status "live";
 * máy chủ tính elapsed = now − start_ts một cách TRUNG THỰC, nên màn host
 * hiển thị ~328 giờ — con số đúng của một phiên chọn sai. Sửa ở khâu CHỌN:
 * trong các phiên đang live, lấy phiên LÊN SÓNG GẦN NHẤT (start_ts lớn nhất);
 * không có phiên live thì lấy phiên gần nhất nói chung. Không sửa số liệu,
 * không che đồng hồ — chỉ chọn đúng phiên người vận hành đang nghĩ tới.
 *
 * An toàn làm mù (L6): chỉ đọc SessionSummary (không có lịch khối/assignment),
 * nên màn host được phép import.
 */

import type { SessionSummary } from "./types";

/** Epoch ms của start_ts; phiên chưa từng phát sóng xếp cuối. */
function startedAt(s: SessionSummary): number {
  if (!s.start_ts) return Number.NEGATIVE_INFINITY;
  const t = Date.parse(s.start_ts);
  return Number.isFinite(t) ? t : Number.NEGATIVE_INFINITY;
}

function latest(list: SessionSummary[]): SessionSummary | null {
  if (list.length === 0) return null;
  return list.reduce((a, b) => (startedAt(b) > startedAt(a) ? b : a));
}

/**
 * Phiên nên mở mặc định: deep link (nếu có thật trong danh sách) → phiên live
 * MỚI NHẤT → phiên mới nhất nói chung → null khi danh sách rỗng.
 */
export function pickCurrentSession(
  list: SessionSummary[],
  preferredId?: string | null,
): SessionSummary | null {
  if (preferredId) {
    const hit = list.find((s) => s.session_id === preferredId);
    if (hit) return hit;
  }
  return latest(list.filter((s) => s.status === "live")) ?? latest(list);
}
