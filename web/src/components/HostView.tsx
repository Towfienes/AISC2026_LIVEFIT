"use client";

/**
 * BLINDED host screen (rule L6).
 *
 * Renders ONLY what HostState carries: pinned product name, price, stock, and
 * total elapsed time. No blocks, no ON/OFF assignment, no per-block countdown,
 * no rhythm chart — nothing that could reveal the switchback schedule to the
 * host.
 *
 * Type: this is the one screen read from ~2 m, so it lives entirely on the
 * display steps of the scale (num-l 56px, num-xl 72px). At 2 m a 72px cap
 * height subtends ≈ 24 arcmin — the ISO 9241-303 comfort band, the same band
 * the desk's 16px body step hits at 70 cm.
 */

import { fmtClock, fmtNumber, fmtVnd } from "@/lib/format";
import type { ConnectionKind, HostState } from "@/lib/types";

import { DemoBadge } from "./StatusBar";

interface Props {
  host: HostState | null;
  connection: ConnectionKind;
}

export default function HostView({ host, connection }: Props) {
  return (
    <main className="flex h-screen flex-col overflow-hidden bg-page text-ink">
      {/* slim chrome: brand + total elapsed only */}
      <div className="flex items-center justify-between border-b border-hairline px-8 pb-4 pt-6">
        <div className="flex items-center gap-3">
          <span className="text-title font-bold tracking-tight text-sec">LiveLift</span>
          {connection === "mock" && <DemoBadge />}
        </div>
        <div className="text-right">
          <div className="text-label uppercase tracking-[0.2em] text-dim">Thời gian phát</div>
          <div className="text-num-l" aria-live="off">
            {host ? fmtClock(host.elapsed_s) : "--:--:--"}
          </div>
        </div>
      </div>

      {/* pinned product — the whole point of the screen */}
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-10 px-12 text-center">
        {host?.product_name ? (
          <>
            <div>
              <div className="mb-4 text-2xl font-medium uppercase tracking-[0.3em] text-dim">
                Sản phẩm đang ghim
              </div>
              <h1 className="text-num-xl leading-tight 2xl:text-8xl">{host.product_name}</h1>
            </div>
            <div className="flex items-baseline gap-16">
              <div>
                <div className="mb-1 text-title uppercase tracking-widest text-dim">Giá</div>
                <div className="text-num-l text-warn-ink 2xl:text-num-xl">
                  {host.price != null ? fmtVnd(host.price) : "—"}
                </div>
              </div>
              <div>
                <div className="mb-1 text-title uppercase tracking-widest text-dim">Tồn kho</div>
                <div className="text-num-l 2xl:text-num-xl">
                  {host.stock != null ? fmtNumber(host.stock) : "—"}
                </div>
              </div>
            </div>
          </>
        ) : (
          <h1 className="text-num-m text-dim">
            {connection === "connecting" ? "Đang kết nối…" : "Chưa ghim sản phẩm"}
          </h1>
        )}
      </div>
    </main>
  );
}
