"use client";

/**
 * BLINDED host screen (rule L6) — v2 "bảng tỷ số sân vận động" (gói DESK-HOST,
 * khoảnh khắc S4 của spec UI-VISUAL + mục f của spec UX-FLOW).
 *
 * Renders ONLY what HostState carries: pinned product name, price, stock, and
 * total elapsed time. No blocks, no ON/OFF assignment, no per-block countdown,
 * no rhythm chart — nothing that could reveal the switchback schedule to the
 * host. Việc LÀM MÙ là một điểm cộng khoa học và phải là CHỮ NHÌN THẤY ĐƯỢC
 * trên màn (dòng cố định dưới cùng), không phải comment trong code.
 *
 * Type: this is the one screen read from ~2 m, so it lives entirely on the
 * display steps of the scale (num-l 56px, num-xl 72px, tên hàng lên tới 96px).
 * At 2 m a 72px cap height subtends ≈ 24 arcmin — the ISO 9241-303 comfort
 * band, the same band the desk's 16px body step hits at 70 cm.
 *
 * CHUYỂN ĐỘNG: màn vận hành — hiệu ứng CHỈ khi có sự kiện. Đổi sản phẩm ghim
 * → khối tên hàng gắn lại theo key nên `.motion-switch` + Flash chạy đúng một
 * lần (người dẫn liếc là biết CÓ THAY ĐỔI). Không có gì lặp vô hạn ở đây:
 * đèn ĐANG PHÁT thuộc về bàn điều khiển, màn host không biết trạng thái phiên
 * nên không tự nhận đang phát sóng.
 */

import { fmtClock, fmtNumber, fmtVnd } from "@/lib/format";
import type { ConnectionKind, HostState } from "@/lib/types";

import { DemoBadge } from "./StatusBar";
import Flash from "./ui/Flash";

/**
 * Đồng hồ vượt ngưỡng này thì gần như chắc chắn là phiên cũ quên kết thúc
 * (phiên live thật dài 60–120 phút) — hiện thêm một dòng nhắc TĨNH thay vì
 * im lặng chiếu một con số 300+ giờ trông như lỗi. Con số vẫn hiển thị
 * nguyên vẹn: nó là số thật, chỉ cần được giải thích.
 */
const STALE_CLOCK_S = 4 * 3600;

interface Props {
  host: HostState | null;
  connection: ConnectionKind;
  /** Vài lần cập nhật liên tiếp hỏng — trấn an người dẫn thay vì để màn đứng im. */
  degraded?: boolean;
}

export default function HostView({ host, connection, degraded = false }: Props) {
  const staleClock = host != null && host.elapsed_s >= STALE_CLOCK_S;
  return (
    <main className="relative flex h-screen flex-col overflow-hidden bg-page text-ink">
      {/* Đèn studio G1 — lớp nền tĩnh rất nhẹ, không phải hiệu ứng. */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(1100px 460px at 50% -12%, rgba(124,108,255,0.14), transparent 60%)",
        }}
      />

      {/* slim chrome: brand + purpose + total elapsed only */}
      <div className="relative flex flex-wrap items-start justify-between gap-x-8 gap-y-3 border-b border-hairline px-8 pb-4 pt-6">
        <div className="flex min-w-0 flex-col gap-1">
          <div className="flex items-center gap-3">
            <span aria-hidden className="logo-mark" />
            <span className="font-display text-title font-bold tracking-tight text-ink">
              Màn hình người dẫn · LiveLift
            </span>
            {connection === "mock" && <DemoBadge />}
          </div>
          {/* Tự giải thích (spec UX-FLOW f): mục đích của màn — và điểm cộng
              khoa học của việc LÀM MÙ — phải là chữ nhìn thấy được. Câu này
              TĨNH, không lộ lịch BẬT/TẮT. */}
          <p className="max-w-[46rem] text-body leading-snug text-sec">
            Chỉ hiện sản phẩm cần giới thiệu ngay. Màn hình này cố tình không hiển thị thông tin
            thí nghiệm để không ảnh hưởng cách bạn nói — cứ trò chuyện tự nhiên.
          </p>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-label uppercase tracking-[0.2em] text-dim">Thời gian phát</div>
          <div className="text-num-l" aria-live="off">
            {host ? fmtClock(host.elapsed_s) : "--:--:--"}
          </div>
          {staleClock ? (
            <p className="mt-1 max-w-[22rem] text-meta leading-snug text-warn-ink">
              Đồng hồ đã chạy hơn 4 giờ — nhiều khả năng một phiên cũ chưa được kết thúc. Nhờ người
              trực bàn trợ live kiểm tra.
            </p>
          ) : null}
        </div>
      </div>

      {/* pinned product — the whole point of the screen. key = tên sản phẩm:
          đổi hàng ghim là khối gắn lại → quét vào MỘT lần + nháy nền. */}
      <div className="relative flex min-h-0 flex-1 flex-col items-center justify-center gap-10 px-12 text-center">
        {host?.product_name ? (
          <div key={host.product_name} className="motion-switch relative flex flex-col items-center gap-10">
            <Flash value={host.product_name} className="-inset-x-10 -inset-y-6 rounded-lg" />
            <div className="relative">
              <div className="mb-4 text-2xl font-medium uppercase tracking-[0.3em] text-dim">
                Sản phẩm đang ghim — giới thiệu ngay
              </div>
              {/* Tên hàng là CHỮ, không phải số — font display (Space Grotesk),
                  không rơi vào JetBrains Mono của bậc num-xl. */}
              <h1 className="font-display text-num-xl leading-tight 2xl:text-8xl">
                {host.product_name}
              </h1>
            </div>
            <div className="relative flex flex-wrap items-baseline justify-center gap-x-16 gap-y-6">
              <div>
                <div className="mb-1 text-title uppercase tracking-widest text-dim">Giá</div>
                <div className="text-num-l text-warn-ink 2xl:text-num-xl">
                  {host.price != null ? fmtVnd(host.price) : "—"}
                </div>
              </div>
              <div>
                <div className="mb-1 text-title uppercase tracking-widest text-dim">Tồn kho</div>
                <div
                  className={`text-num-l 2xl:text-num-xl ${
                    host.stock != null && host.stock > 0 && host.stock < 10 ? "text-warn-ink" : ""
                  }`}
                >
                  {host.stock != null ? fmtNumber(host.stock) : "—"}
                </div>
                {host.stock != null && host.stock > 0 && host.stock < 10 ? (
                  <div className="mt-1 text-strong font-semibold text-warn-ink">
                    sắp hết — hối khách chốt
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex max-w-[52rem] flex-col items-center gap-4">
            <h1 className="font-display text-num-m leading-tight text-sec 2xl:text-num-l">
              {connection === "connecting" ? "Đang kết nối…" : "Chưa ghim sản phẩm"}
            </h1>
            {connection !== "connecting" && (
              <p className="text-strong leading-snug text-dim">
                Cứ nói chuyện tự nhiên. Khi có sản phẩm cần giới thiệu, tên hàng sẽ hiện THẬT TO ở
                đây.
              </p>
            )}
          </div>
        )}
      </div>

      {/* chân màn: trạng thái đường truyền (một chiều, không lộ gì) */}
      <div className="relative flex min-h-[3.25rem] items-center justify-center border-t border-hairline px-8 py-3">
        {degraded ? (
          <p className="motion-enter text-strong font-semibold text-warn-ink">
            Mất kết nối tới máy chủ — cứ tiếp tục nói chuyện, màn sẽ tự nối lại.
          </p>
        ) : (
          <p className="text-meta text-dim">
            Kéo cửa sổ này sang màn phụ/TV trước mặt người dẫn · bấm F11 để toàn màn hình
          </p>
        )}
      </div>
    </main>
  );
}
