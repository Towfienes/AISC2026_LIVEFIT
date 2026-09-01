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
 * The estimate + CI is the hero (Tremor-style KPI row); everything else
 * supports it.
 */

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import TopNav from "@/components/TopNav";
import Badge from "@/components/ui/Badge";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import StatTile from "@/components/ui/StatTile";
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

/** Mirrors the hero + tile layout while the summary is loading. */
function ResultSkeleton() {
  return (
    <div aria-busy>
      <div className="mb-3 flex items-center gap-2">
        <Skeleton className="h-5 w-44 rounded-full" />
        <Skeleton className="h-3 w-56" />
      </div>
      <div className="grid gap-3 md:grid-cols-3">
        <Card padding="lg" className="md:col-span-2">
          <Skeleton className="h-3 w-36" />
          <Skeleton className="mt-3 h-14 w-64" />
          <Skeleton className="mt-3 h-3 w-80 max-w-full" />
        </Card>
        <div className="grid gap-3">
          <Card>
            <Skeleton className="h-3 w-24" />
            <Skeleton className="mt-2 h-7 w-28" />
            <Skeleton className="mt-2 h-3 w-40" />
          </Card>
          <Card>
            <Skeleton className="h-3 w-16" />
            <Skeleton className="mt-2 h-7 w-24" />
            <Skeleton className="mt-2 h-3 w-36" />
          </Card>
        </div>
      </div>
      <Skeleton className="mt-3 h-16 w-full" />
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
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        <header className="mb-6">
          <h1 className="text-xl font-bold tracking-tight text-ink">Kết quả thí nghiệm</h1>
          <p className="mt-1 max-w-3xl text-sm leading-relaxed text-sec">
            So sánh các khối <strong className="text-ink">BẬT</strong> (hệ thống điều khiển việc
            ghim sản phẩm) với các khối <strong className="text-ink">TẮT</strong> (đội vận hành
            làm như thường lệ). Vì mỗi khối được bốc thăm ngẫu nhiên từ trước, chênh lệch giữa
            hai nhánh là <strong className="text-ink">tác động thật</strong> của hệ thống, không
            phải trùng hợp thời điểm.
          </p>
        </header>

        {loading ? <ResultSkeleton /> : null}

        {err ? (
          <Callout tone="critical">
            {err}{" "}
            <button
              onClick={() => void load()}
              className="focus-ring rounded underline underline-offset-2 transition-colors duration-150 hover:text-ink"
            >
              Thử lại
            </button>
          </Callout>
        ) : null}

        {data && !enough ? (
          <Card padding="lg">
            <h2 className="text-base font-semibold text-ink">Chưa đủ dữ liệu để kết luận</h2>
            <p className="mt-2 text-sm leading-relaxed text-sec">
              {data.message
                ? data.message
                : `Hiện có ${data.n_sessions} phiên và ${data.n_blocks} khối. Cần chạy thêm phiên có lịch gán ngẫu nhiên thì mới ước lượng được tác động.`}{" "}
              <Link href="/" className="focus-ring rounded underline underline-offset-2">
                Tạo dữ liệu mô phỏng để xem thử
              </Link>
              .
            </p>
          </Card>
        ) : null}

        {data && enough ? (
          <>
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <Badge tone="good" dot>
                Tác động đo được · KTC 95%
              </Badge>
              <span className="text-[11px] text-mut">
                kiểm định dựa trên ngẫu nhiên hóa
                {data.n_draws ? ` · ${data.n_draws.toLocaleString("vi-VN")} lần vẽ lại` : ""}
              </span>
            </div>

            {/* hero: estimate + CI is THE result — everything else supports it */}
            <section className="grid gap-3 md:grid-cols-3">
              <Card padding="lg" className="flex flex-col md:col-span-2">
                <div className="text-[11px] font-medium uppercase tracking-wide text-mut">
                  Tác động ước lượng
                </div>
                <div className="mt-2 flex flex-wrap items-baseline gap-x-4 gap-y-1">
                  <span
                    className={`text-6xl font-semibold tabular-nums tracking-tight ${
                      significant ? "text-good" : "text-ink"
                    }`}
                  >
                    {data.estimate!.toFixed(3)}
                  </span>
                  <span className="tnum text-lg text-sec">
                    KTC 95% [{data.ci_low?.toFixed(3) ?? "—"} …{" "}
                    {data.ci_high?.toFixed(3) ?? "—"}]
                  </span>
                </div>
                <p className="mt-auto pt-3 text-[11px] leading-snug text-sec">
                  nhấp thêm trên mỗi 1000 giây·người xem · giá trị thật nằm trong khoảng này với
                  độ tin cậy 95%
                </p>
              </Card>

              <div className="grid gap-3">
                <StatTile
                  label="Mức ý nghĩa"
                  value={formatP(data.p_value, data.n_draws)}
                  hint={
                    significant
                      ? "khoảng tin cậy không chứa 0 — chênh lệch khó là ngẫu nhiên"
                      : "khoảng tin cậy còn chứa 0 — chưa loại trừ được ngẫu nhiên"
                  }
                />
                <StatTile
                  label="Cỡ mẫu"
                  value={`${data.n_blocks} khối`}
                  hint={`${data.n_sessions} phiên · ${data.n_on} BẬT / ${data.n_off} TẮT`}
                />
              </div>
            </section>

            <Card className="mt-3 text-sm leading-relaxed text-sec">
              <strong className="text-ink">Đọc thế nào:</strong>{" "}
              {significant ? (
                <>
                  khoảng tin cậy nằm hoàn toàn về một phía của 0, nghĩa là chênh lệch giữa hai
                  nhánh khó có thể do may rủi. Đây là bằng chứng thí nghiệm, không phải tương
                  quan.
                </>
              ) : (
                <>
                  khoảng tin cậy vẫn chứa 0, nghĩa là{" "}
                  <strong className="text-ink">chưa kết luận được</strong> hệ thống có tác động
                  hay không. Đây là một kết quả hợp lệ — cần thêm phiên hoặc hiệu ứng lớn hơn mới
                  phát hiện được.
                </>
              )}
            </Card>

            <section className="mt-6">
              <SectionTitle>Cần bao nhiêu dữ liệu để phát hiện được tác động?</SectionTitle>
              <p className="max-w-3xl text-[13px] leading-relaxed text-sec">
                <strong className="text-ink">MDE</strong> (hiệu ứng nhỏ nhất phát hiện được) là
                ngưỡng độ lớn tối thiểu mà thí nghiệm còn nhìn thấy được. MDE 30% nghĩa là: nếu
                hệ thống chỉ cải thiện 10%, cỡ mẫu hiện tại{" "}
                <strong className="text-ink">không đủ để chứng minh</strong> — không phải hệ
                thống vô dụng, mà là chưa đo nổi. Càng nhiều phiên, MDE càng nhỏ.
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
                      <tr
                        key={r.scenario}
                        className="border-t border-hairline transition-colors duration-150 hover:bg-raised/60"
                      >
                        <td className="px-3 py-2 text-ink">{r.scenario}</td>
                        <td className="tnum px-3 py-2 text-right text-sec">{r.n_sessions}</td>
                        <td className="tnum px-3 py-2 text-right text-sec">
                          {r.n_blocks_total}
                        </td>
                        <td className="tnum px-3 py-2 text-right text-sec">{r.cv.toFixed(2)}</td>
                        <td className="tnum px-3 py-2 text-right font-semibold text-ink">
                          {fmtPct(r.mde_relative)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="mt-6 grid gap-3 md:grid-cols-2">
              <StatTile
                label="Hệ số biến thiên đo được (CV)"
                value={data.measured_cv?.toFixed(3) ?? "—"}
                hint="Mức dao động của kết quả giữa các khối. CV càng cao thì càng cần nhiều dữ liệu — bảng MDE ở trên tính bằng chính con số đo được này, không phải giả định."
              />
              <StatTile
                label="Tỷ lệ tuân thủ"
                value={data.measured_compliance != null ? fmtPct(data.measured_compliance) : "—"}
                hint="Tỷ lệ khối BẬT mà hệ thống thực sự được thực thi. Tuân thủ thấp làm loãng ước lượng: con số báo cáo là ITT (theo nhóm được gán), luôn thận trọng."
              />
            </section>

            <p className="mt-6 text-[11px] leading-relaxed text-mut">
              Biến kết quả chính là tỷ lệ nhấp sản phẩm — chỉ báo sớm có tần suất đủ cao để học
              nhanh. Các chỉ số kinh doanh (đơn, GMV, biên lợi nhuận) được theo dõi song song và
              báo cáo riêng như kết quả khám phá; không đánh đồng hai loại.
            </p>
          </>
        ) : null}
      </main>
    </div>
  );
}
