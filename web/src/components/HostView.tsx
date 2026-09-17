"use client";

/**
 * BLINDED host screen (rule L6) — v2 "bảng tỷ số sân vận động" (gói DESK-HOST,
 * khoảnh khắc S4 của spec UI-VISUAL + mục f của spec UX-FLOW).
 *
 * Renders ONLY what HostState carries: pinned product name, price, stock, and
 * total elapsed time. No blocks, no ON/OFF assignment, no per-block countdown,
 * no rhythm chart — nothing that could reveal the switchback schedule to the
 * host. Ngoài HostState, màn chỉ nhận cờ ĐƯỜNG TRUYỀN/NHÃN (kết nối, mất kết
 * nối, không tìm thấy phiên trong link, dữ liệu mẫu) — không cờ nào nói gì về
 * khối.
 *
 * LỜI GIẢI THÍCH NGẮN (gói D): câu cũ "Màn hình này cố tình không hiển thị
 * thông tin thí nghiệm…" — với người dẫn đang live, nhắc chữ "thí nghiệm"
 * chính là gợi lại điều màn này muốn giấu. Nay chỉ còn một câu việc-cần-làm.
 *
 * Type: this is the one screen read from ~2 m, so on a wide screen it lives on
 * the display steps of the scale (num-l 56px, num-xl 72px). At 2 m a 72px cap
 * height subtends ≈ 24 arcmin — the ISO 9241-303 comfort band, the same band
 * the desk's 16px body step hits at 70 cm.
 *
 * BỐ CỤC ĐÁP ỨNG (gói D): ở 390×844 màn cũ vỡ — `h-screen overflow-hidden` +
 * khối giữa `flex-1 justify-center` với cỡ chữ CỐ ĐỊNH: nội dung cao hơn
 * khung nên `justify-center` đẩy tràn cả lên trên (nhãn đè mô tả và đồng hồ)
 * lẫn xuống dưới (giá đè chân trang, tồn kho rơi khỏi màn), tên hàng 72px vỡ
 * thành 5 dòng. Nay màn là `min-h-screen` (nội dung dài thì trang dài ra,
 * không bao giờ chồng lấn) và mọi cỡ chữ đi theo thang token, bậc nhỏ ở màn
 * hẹp rồi lên bậc hiển thị bằng tiền tố sm:/lg:/xl: — ở 1366 và TV vẫn là
 * num-xl/num-l như trước.
 *
 * CHUYỂN ĐỘNG: màn vận hành — hiệu ứng CHỈ khi có sự kiện. Đổi sản phẩm ghim
 * → khối tên hàng gắn lại theo key nên `.motion-switch` + Flash chạy đúng một
 * lần (người dẫn liếc là biết CÓ THAY ĐỔI). Không có gì lặp vô hạn ở đây:
 * đèn ĐANG PHÁT thuộc về bàn điều khiển, màn host không biết trạng thái phiên
 * nên không tự nhận đang phát sóng.
 */

import { fmtClock, fmtNumber, fmtVnd } from "@/lib/format";
import type { ConnectionKind, HostState } from "@/lib/types";

import Badge from "./ui/Badge";
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
  /** Link mở màn này mang mã phiên mà máy chủ không có. */
  sessionNotFound?: boolean;
  /** Phiên đang chiếu là dữ liệu mẫu — nhãn bắt buộc. */
  sampleData?: boolean;
}

export default function HostView({
  host,
  connection,
  degraded = false,
  sessionNotFound = false,
  sampleData = false,
}: Props) {
  const staleClock = host != null && host.elapsed_s >= STALE_CLOCK_S;
  const lowStock = host?.stock != null && host.stock > 0 && host.stock < 10;
  return (
    <main className="relative flex min-h-screen flex-col overflow-x-hidden bg-page text-ink">
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
      <header className="relative flex flex-wrap items-start justify-between gap-x-6 gap-y-3 border-b border-hairline px-4 pb-3 pt-4 sm:gap-x-8 sm:px-8 sm:pb-4 sm:pt-6">
        <div className="flex min-w-0 flex-1 basis-56 flex-col gap-1">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
            <span aria-hidden className="logo-mark" />
            <span className="font-display text-strong font-bold tracking-tight text-ink sm:text-title">
              Màn người dẫn · LiveLift
            </span>
            {sampleData || connection === "mock" ? (
              <Badge tone="warn">DEMO — dữ liệu mẫu</Badge>
            ) : null}
          </div>
          {/* Một câu TĨNH, không lộ lịch BẬT/TẮT và không nhắc tới thí nghiệm. */}
          <p className="text-body leading-snug text-sec">Chỉ hiện sản phẩm cần giới thiệu ngay.</p>
        </div>
        <div className="shrink-0 text-right">
          <div className="text-label uppercase tracking-[0.2em] text-dim">Thời gian phát</div>
          <div className="text-num-s sm:text-num-m lg:text-num-l" aria-live="off">
            {host ? fmtClock(host.elapsed_s) : "--:--:--"}
          </div>
          {staleClock ? (
            <p className="mt-1 flex max-w-[22rem] items-start justify-end gap-1.5 text-meta leading-snug text-warn-ink">
              <span aria-hidden>⚠</span>
              <span>
                Đồng hồ đã chạy hơn 4 giờ — nhiều khả năng một phiên cũ chưa được kết thúc. Nhờ
                người trực bàn trợ live kiểm tra.
              </span>
            </p>
          ) : null}
        </div>
      </header>

      {/* pinned product — the whole point of the screen. key = tên sản phẩm:
          đổi hàng ghim là khối gắn lại → quét vào MỘT lần + nháy nền.
          KHÔNG min-h-0: khối này được phép cao hơn phần còn lại của màn (trang
          dài ra) — thà cuộn còn hơn chữ đè lên đầu/chân màn. */}
      <section className="relative flex flex-1 flex-col items-center justify-center gap-6 px-4 py-6 text-center sm:gap-8 sm:px-8 sm:py-8 lg:gap-10 lg:px-12">
        {host?.product_name ? (
          <div
            key={host.product_name}
            className="motion-switch relative flex w-full flex-col items-center gap-6 sm:gap-8 lg:gap-10"
          >
            <Flash
              value={host.product_name}
              className="-inset-x-2 -inset-y-3 rounded-lg sm:-inset-x-10 sm:-inset-y-6"
            />
            <div className="relative w-full">
              <div className="mb-2 text-label uppercase tracking-[0.12em] text-dim sm:mb-4 sm:text-title sm:tracking-[0.3em]">
                Sản phẩm đang ghim — giới thiệu ngay
              </div>
              {/* Tên hàng là CHỮ, không phải số — font display (Space Grotesk),
                  không rơi vào JetBrains Mono của bậc num-xl. Tên dài xuống
                  dòng giữa chữ nếu cần, không bao giờ tràn ngang. */}
              <h1 className="font-display text-num-m leading-tight [overflow-wrap:anywhere] sm:text-num-l xl:text-num-xl">
                {host.product_name}
              </h1>
            </div>
            <div className="relative flex flex-wrap items-baseline justify-center gap-x-10 gap-y-4 sm:gap-x-16 sm:gap-y-6">
              <div>
                <div className="mb-1 text-label uppercase tracking-widest text-dim sm:text-title">
                  Giá
                </div>
                <div className="text-num-m text-warn-ink sm:text-num-l 2xl:text-num-xl">
                  {host.price != null ? fmtVnd(host.price) : "—"}
                </div>
              </div>
              <div>
                <div className="mb-1 text-label uppercase tracking-widest text-dim sm:text-title">
                  Tồn kho
                </div>
                <div
                  className={`text-num-m sm:text-num-l 2xl:text-num-xl ${lowStock ? "text-warn-ink" : ""}`}
                >
                  {host.stock != null ? fmtNumber(host.stock) : "—"}
                </div>
                {lowStock ? (
                  <div className="mt-1 flex items-center justify-center gap-1.5 text-body font-semibold text-warn-ink sm:text-strong">
                    <span aria-hidden>⚠</span>
                    sắp hết — hối khách chốt
                  </div>
                ) : null}
              </div>
            </div>
          </div>
        ) : (
          <div className="flex max-w-[52rem] flex-col items-center gap-3 sm:gap-4">
            <h1 className="font-display text-num-s leading-tight text-sec sm:text-num-m 2xl:text-num-l">
              {connection === "connecting"
                ? "Đang kết nối…"
                : sessionNotFound
                  ? "Không tìm thấy phiên trong link"
                  : "Chưa ghim sản phẩm"}
            </h1>
            {connection !== "connecting" && (
              <p className="text-body leading-snug text-dim sm:text-strong">
                {sessionNotFound
                  ? "Nhờ người trực bàn trợ live mở lại màn người dẫn từ bàn."
                  : "Cứ nói chuyện tự nhiên — khi cần giới thiệu sản phẩm, tên hàng sẽ hiện thật to ở đây."}
              </p>
            )}
          </div>
        )}
      </section>

      {/* chân màn: trạng thái đường truyền (một chiều, không lộ gì) */}
      <footer className="relative flex min-h-[3.25rem] items-center justify-center border-t border-hairline px-4 py-3 text-center sm:px-8">
        {degraded ? (
          <p className="motion-enter flex items-center gap-2 text-body font-semibold text-warn-ink sm:text-strong">
            <span aria-hidden>⚠</span>
            Mất kết nối tới máy chủ — cứ tiếp tục nói chuyện, màn sẽ tự nối lại.
          </p>
        ) : (
          <p className="text-meta text-dim">
            Kéo cửa sổ này sang màn phụ/TV trước mặt người dẫn · bấm F11 để toàn màn hình
          </p>
        )}
      </footer>
    </main>
  );
}
