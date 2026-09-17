/**
 * Chọn "phiên hiện tại" từ danh sách phiên — `pickCurrentSession` cho bàn trợ
 * live, `pickHostSession` cho màn người dẫn mở không kèm `?session=`.
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

/** Kết quả chọn phiên cho `/host` trơn (không mang `?session=`). */
export interface HostPick {
  /** Phiên nên chiếu; null = không có phiên live nào hợp lệ → màn trống. */
  session: SessionSummary | null;
  /**
   * Số phiên live CÙNG LOẠI với phiên được chọn (cùng thật hoặc cùng mẫu). Từ
   * 2 trở lên là tình huống mơ hồ: màn giữ nguyên phiên đang chiếu và nhắc
   * người trực mở lại bằng link có mã phiên — không tự nhảy phiên.
   */
  liveCount: number;
}

/**
 * Phiên cho màn người dẫn khi link KHÔNG có `?session=`.
 *
 * VÌ SAO KHÔNG DÙNG `pickCurrentSession` (hồi quy gói D, kiểm toán 17/09): chọn
 * lại "phiên live lên sóng gần nhất" ở MỖI lần poll nghĩa là bất kỳ phiên nào
 * lên sóng sau — kể cả phiên mẫu của nút "Xem thử ngay" (`/demo/seed` để một
 * phiên live với start_ts = now − 30 phút) hay phiên khách tự tạo trên bản
 * trưng bày — cướp màn của buổi thật đang phát, và người dẫn giới thiệu nhầm
 * hàng tới hết buổi. Luật chọn nay:
 *   1. Chỉ phiên ĐANG live (hàng ghim của buổi đã xong không bao giờ lên màn).
 *   2. Có phiên THẬT live thì bỏ mọi phiên mẫu (`is_demo`). Chưa có phiên thật
 *      nào thì phiên mẫu được chiếu (có nhãn DEMO) — trừ khi màn này ĐÃ TỪNG
 *      chiếu một phiên thật (`allowDemo=false`): buổi thật xong thì màn trống,
 *      không nhảy sang hàng mẫu.
 *   3. Phiên đang chiếu vẫn còn trong nhóm hợp lệ thì GIỮ NGUYÊN — không đổi
 *      sang phiên mới hơn. Chỉ chọn lại (phiên lên sóng gần nhất) khi phiên
 *      đang chiếu hết live, hoặc khi nó là phiên mẫu và một phiên thật vừa lên
 *      sóng. Nhờ vậy màn mở TRƯỚC giờ phát sóng vẫn tự bắt được phiên vừa bấm
 *      phát (gói D) mà không bị phiên đến sau cướp.
 */
export function pickHostSession(
  list: SessionSummary[],
  shownId: string | null,
  allowDemo = true,
): HostPick {
  const live = list.filter((s) => s.status === "live");
  const real = live.filter((s) => !s.is_demo);
  const pool = real.length > 0 ? real : allowDemo ? live : [];
  const kept = shownId ? pool.find((s) => s.session_id === shownId) : undefined;
  return { session: kept ?? latest(pool), liveCount: pool.length };
}
