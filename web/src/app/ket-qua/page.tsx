"use client";

/**
 * "/ket-qua" — the project's headline scientific output.
 *
 * This screen shows `GET /experiment/summary`: the pooled effect of the LiveLift
 * pinning strategy across every finished session, with a 95% confidence
 * interval and a randomization-test p-value.
 *
 * E2-04: these numbers are `source: "experiment"`, so an interval is not only
 * allowed here, it is REQUIRED — a point estimate without one would overclaim.
 * The forecast-sourced numbers on the desk stay interval-free.
 *
 * Design intent: a judge (or a seller) must be able to read the honest answer
 * in ten seconds — including when the honest answer is "not enough data yet".
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { getExperimentSummary } from "@/lib/api";
import { fmtPct } from "@/lib/format";
import type { ExperimentSummary } from "@/lib/types";

/**
 * A permutation test cannot report a p below 1/(draws+1); print that floor
 * honestly instead of a fake-precise number.
 */
function formatP(p: number | null, draws: number | null): string {
  if (p == null) return "—";
  const floor = draws ? 1 / (draws + 1) : null;
  if (floor != null && p <= floor * 1.001) return `p < ${floor.toFixed(4)}`;
  return `p = ${p.toFixed(4)}`;
}

function Stat({
  label,
  value,
  hint,
  tone = "ink",
}: {
  label: string;
  value: string;
  hint?: string;
  tone?: "ink" | "good";
}) {
  return (
    <div className="rounded-lg border border-hairline bg-surface p-3">
      <div className="text-[11px] uppercase tracking-wide text-mut">{label}</div>
      <div
        className={`mt-1 text-2xl font-bold tabular-nums ${
          tone === "good" ? "text-good" : "text-ink"
        }`}
      >
        {value}
      </div>
      {hint ? <div className="mt-1 text-[11px] leading-snug text-sec">{hint}</div> : null}
    </div>
  );
}

export default function KetQuaPage() {
  const [data, setData] = useState<ExperimentSummary | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    setErr(null);
    try {
      setData(await getExperimentSummary());
    } catch {
      setErr("Không đọc được kết quả — kiểm tra máy chủ đã chạy chưa (docker compose up -d).");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // `estimable === false` means the API refused to test this design; treat a
  // missing flag as true only because older payloads predate it.
  const enough =
    data != null &&
    data.estimable !== false &&
    data.n_blocks > 0 &&
    data.estimate != null;
  const significant =
    enough && data.ci_low != null && data.ci_high != null
      ? data.ci_low > 0 || data.ci_high < 0
      : false;

  return (
    <main className="mx-auto max-w-5xl px-4 py-6">
      <header className="mb-5">
        <h1 className="text-xl font-bold text-ink">Kết quả thí nghiệm</h1>
        <p className="mt-1 max-w-3xl text-sm leading-relaxed text-sec">
          So sánh các khối <strong className="text-ink">BẬT</strong> (hệ thống điều khiển việc ghim
          sản phẩm) với các khối <strong className="text-ink">TẮT</strong> (đội vận hành làm như
          thường lệ). Vì mỗi khối được bốc thăm ngẫu nhiên từ trước, chênh lệch giữa hai nhánh là{" "}
          <strong className="text-ink">tác động thật</strong> của hệ thống, không phải trùng hợp
          thời điểm.
        </p>
      </header>

      {loading ? <p className="text-sm text-mut">Đang tải…</p> : null}

      {err ? (
        <div className="rounded-lg border border-critical/40 bg-critical/10 p-4 text-sm text-ink">
          {err}{" "}
          <button onClick={() => void load()} className="underline underline-offset-2">
            Thử lại
          </button>
        </div>
      ) : null}

      {data && !enough ? (
        <div className="rounded-lg border border-hairline bg-surface p-5">
          <h2 className="text-base font-semibold text-ink">Chưa đủ dữ liệu để kết luận</h2>
          <p className="mt-2 text-sm leading-relaxed text-sec">
            {data.message
              ? data.message
              : `Hiện có ${data.n_sessions} phiên và ${data.n_blocks} khối. Cần chạy thêm phiên có lịch gán ngẫu nhiên thì mới ước lượng được tác động.`}{" "}
            <Link href="/" className="underline underline-offset-2">
              Tạo dữ liệu mô phỏng để xem thử
            </Link>
            .
          </p>
        </div>
      ) : null}

      {data && enough ? (
        <>
          <div className="mb-2 flex flex-wrap items-center gap-2">
            <span className="rounded bg-s3/20 px-2 py-0.5 text-[11px] font-semibold text-s3">
              Tác động đo được · KTC 95%
            </span>
            <span className="text-[11px] text-mut">
              kiểm định dựa trên ngẫu nhiên hóa
              {data.n_draws ? ` · ${data.n_draws.toLocaleString("vi-VN")} lần vẽ lại` : ""}
            </span>
          </div>

          <section className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Stat
              label="Tác động ước lượng"
              value={data.estimate!.toFixed(3)}
              tone={significant ? "good" : "ink"}
              hint="nhấp thêm trên mỗi 1000 giây·người xem"
            />
            <Stat
              label="Khoảng tin cậy 95%"
              value={`${data.ci_low?.toFixed(3) ?? "—"} … ${data.ci_high?.toFixed(3) ?? "—"}`}
              hint="giá trị thật nằm trong khoảng này với độ tin cậy 95%"
            />
            <Stat
              label="Mức ý nghĩa"
              value={formatP(data.p_value, data.n_draws)}
              hint={
                significant
                  ? "khoảng tin cậy không chứa 0 — chênh lệch khó là ngẫu nhiên"
                  : "khoảng tin cậy còn chứa 0 — chưa loại trừ được ngẫu nhiên"
              }
            />
            <Stat
              label="Cỡ mẫu"
              value={`${data.n_blocks} khối`}
              hint={`${data.n_sessions} phiên · ${data.n_on} BẬT / ${data.n_off} TẮT`}
            />
          </section>

          <p className="mt-3 rounded-lg border border-hairline bg-surface p-3 text-sm leading-relaxed text-sec">
            <strong className="text-ink">Đọc thế nào:</strong>{" "}
            {significant ? (
              <>
                khoảng tin cậy nằm hoàn toàn về một phía của 0, nghĩa là chênh lệch giữa hai nhánh
                khó có thể do may rủi. Đây là bằng chứng thí nghiệm, không phải tương quan.
              </>
            ) : (
              <>
                khoảng tin cậy vẫn chứa 0, nghĩa là{" "}
                <strong className="text-ink">chưa kết luận được</strong> hệ thống có tác động hay
                không. Đây là một kết quả hợp lệ — cần thêm phiên hoặc hiệu ứng lớn hơn mới phát
                hiện được.
              </>
            )}
          </p>

          <section className="mt-5">
            <h2 className="text-sm font-semibold text-ink">
              Cần bao nhiêu dữ liệu để phát hiện được tác động?
            </h2>
            <p className="mt-1 max-w-3xl text-[13px] leading-relaxed text-sec">
              <strong className="text-ink">MDE</strong> (hiệu ứng nhỏ nhất phát hiện được) là ngưỡng
              độ lớn tối thiểu mà thí nghiệm còn nhìn thấy được. MDE 30% nghĩa là: nếu hệ thống chỉ
              cải thiện 10%, cỡ mẫu hiện tại{" "}
              <strong className="text-ink">không đủ để chứng minh</strong> — không phải hệ thống vô
              dụng, mà là chưa đo nổi. Càng nhiều phiên, MDE càng nhỏ.
            </p>
            <div className="mt-2 overflow-x-auto rounded-lg border border-hairline">
              <table className="w-full min-w-[520px] text-sm">
                <thead className="bg-raised text-[11px] uppercase tracking-wide text-mut">
                  <tr>
                    <th className="px-3 py-2 text-left font-medium">Kịch bản</th>
                    <th className="px-3 py-2 text-right font-medium">Phiên</th>
                    <th className="px-3 py-2 text-right font-medium">Khối</th>
                    <th className="px-3 py-2 text-right font-medium">CV</th>
                    <th className="px-3 py-2 text-right font-medium">MDE</th>
                  </tr>
                </thead>
                <tbody>
                  {data.power_table.map((r) => (
                    <tr key={r.scenario} className="border-t border-hairline">
                      <td className="px-3 py-2 text-ink">{r.scenario}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-sec">{r.n_sessions}</td>
                      <td className="px-3 py-2 text-right tabular-nums text-sec">
                        {r.n_blocks_total}
                      </td>
                      <td className="px-3 py-2 text-right tabular-nums text-sec">
                        {r.cv.toFixed(2)}
                      </td>
                      <td className="px-3 py-2 text-right font-semibold tabular-nums text-ink">
                        {fmtPct(r.mde_relative)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>

          <section className="mt-5 grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border border-hairline bg-surface p-3">
              <div className="text-[11px] uppercase tracking-wide text-mut">
                Hệ số biến thiên đo được (CV)
              </div>
              <div className="mt-1 text-lg font-bold tabular-nums text-ink">
                {data.measured_cv?.toFixed(3) ?? "—"}
              </div>
              <p className="mt-1 text-[11px] leading-snug text-sec">
                Mức dao động của kết quả giữa các khối. CV càng cao thì càng cần nhiều dữ liệu —
                bảng MDE ở trên tính bằng chính con số đo được này, không phải giả định.
              </p>
            </div>
            <div className="rounded-lg border border-hairline bg-surface p-3">
              <div className="text-[11px] uppercase tracking-wide text-mut">Tỷ lệ tuân thủ</div>
              <div className="mt-1 text-lg font-bold tabular-nums text-ink">
                {data.measured_compliance != null ? fmtPct(data.measured_compliance) : "—"}
              </div>
              <p className="mt-1 text-[11px] leading-snug text-sec">
                Tỷ lệ khối BẬT mà hệ thống thực sự được thực thi. Tuân thủ thấp làm loãng ước lượng:
                con số báo cáo là ITT (theo nhóm được gán), luôn thận trọng.
              </p>
            </div>
          </section>

          <p className="mt-5 text-[11px] leading-relaxed text-mut">
            Biến kết quả chính là tỷ lệ nhấp sản phẩm — chỉ báo sớm có tần suất đủ cao để học nhanh.
            Các chỉ số kinh doanh (đơn, GMV, biên lợi nhuận) được theo dõi song song và báo cáo riêng
            như kết quả khám phá; không đánh đồng hai loại.
          </p>
        </>
      ) : null}
    </main>
  );
}
