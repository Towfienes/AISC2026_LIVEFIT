"use client";

/**
 * BLINDED host screen (rule L6).
 *
 * Renders ONLY what HostState carries: pinned product name, price, stock, and
 * total elapsed time. No blocks, no ON/OFF assignment, no per-block countdown,
 * no rhythm chart — nothing that could reveal the switchback schedule to the
 * host. Fonts are sized to be readable from ~2 m.
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
      <div className="flex items-center justify-between px-8 pt-6">
        <div className="flex items-center gap-3">
          <span className="text-lg font-bold tracking-tight text-sec">LiveLift</span>
          {connection === "mock" && <DemoBadge />}
        </div>
        <div className="text-right">
          <div className="text-sm uppercase tracking-widest text-mut">Thời gian phát</div>
          <div className="tnum text-6xl font-bold" aria-live="off">
            {host ? fmtClock(host.elapsed_s) : "--:--:--"}
          </div>
        </div>
      </div>

      {/* pinned product — the whole point of the screen */}
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-8 px-12 text-center">
        {host?.product_name ? (
          <>
            <div>
              <div className="mb-3 text-2xl uppercase tracking-[0.3em] text-mut">
                Sản phẩm đang ghim
              </div>
              <h1 className="text-7xl font-extrabold leading-tight tracking-tight 2xl:text-8xl">
                {host.product_name}
              </h1>
            </div>
            <div className="flex items-baseline gap-16">
              <div>
                <div className="mb-1 text-xl uppercase tracking-widest text-mut">Giá</div>
                <div className="tnum text-6xl font-bold text-warn 2xl:text-7xl">
                  {host.price != null ? fmtVnd(host.price) : "—"}
                </div>
              </div>
              <div>
                <div className="mb-1 text-xl uppercase tracking-widest text-mut">Tồn kho</div>
                <div className="tnum text-6xl font-bold 2xl:text-7xl">
                  {host.stock != null ? fmtNumber(host.stock) : "—"}
                </div>
              </div>
            </div>
          </>
        ) : (
          <h1 className="text-5xl font-bold text-mut">
            {connection === "connecting" ? "Đang kết nối…" : "Chưa ghim sản phẩm"}
          </h1>
        )}
      </div>
    </main>
  );
}
