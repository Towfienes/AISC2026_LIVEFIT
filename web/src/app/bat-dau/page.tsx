"use client";

/**
 * "/bat-dau" — GÓI WIZARD.
 *
 * Câu hỏi chủ dự án hỏi đi hỏi lại: "Tôi mở phiên live bất kỳ của nền tảng nào
 * cũng được và sử dụng sản phẩm — có làm được không? Hiện tại nếu dùng thì
 * dùng như nào?" Câu trả lời vốn nằm trong docs/nen-tang-ho-tro.md và
 * docs/mo-hinh-van-hanh-kol.md, còn SẢN PHẨM thì không nói gì: người dùng mở
 * trang chủ ra không biết mình làm được gì với buổi live của mình. Đây là
 * khoảng trống trải nghiệm lớn nhất, và trang này tồn tại để lấp đúng nó.
 *
 * BA QUYẾT ĐỊNH THIẾT KẾ
 *
 * 1. BA CÂU HỎI, BẤM LÀ XONG. Không gõ chữ, không thuật ngữ. Ba câu là đủ để
 *    định vị một ô duy nhất trong ma trận 5 x 2 x 2 — thêm câu thứ tư là bắt
 *    người dùng trả giá cho sự chính xác họ không cần.
 * 2. KẾT QUẢ DỨT KHOÁT, KHÔNG HỨA HÃO. Mỗi tổ hợp có ba khối cố định: làm được
 *    gì NGAY (kèm nút bấm thẳng tới đó), cần gì để lên mức cao hơn (kèm thời
 *    gian ước tính và tài liệu có sẵn trong repo), và không làm được gì kèm lý
 *    do. Tổ hợp nào không làm được thì nói thẳng rồi chỉ đường thay thế gần
 *    nhất — TikTok không được tô hồng thành "sắp có".
 * 3. TRẠNG THÁI NẰM TRÊN URL. Mỗi tổ hợp là một đường dẫn chia sẻ được
 *    (?cua=…&nen=…&khi=…), nên một câu trả lời gửi cho đồng đội là một cái
 *    link, không phải một đoạn mô tả "bấm cái này rồi bấm cái kia".
 *
 * Trang này KHÔNG gọi thêm đường API nào ngoài những gì api.ts đã có.
 */

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import TopNav from "@/components/TopNav";
import BatDauVod from "@/components/BatDauVod";
import Badge, { type BadgeTone } from "@/components/ui/Badge";
import { buttonCls } from "@/components/ui/Button";
import Card from "@/components/ui/Card";
import SectionTitle from "@/components/ui/SectionTitle";
import StatusMark, { type StatusShape } from "@/components/ui/StatusMark";
import { listSessions } from "@/lib/api";
import {
  LEVEL_META,
  LEVEL_ORDER,
  OWNERS,
  OWNER_LABEL,
  PLATFORMS,
  PLATFORM_LABEL,
  PLATFORM_NOTE,
  THREE_REQUIREMENTS,
  WHENS,
  WHEN_LABEL,
  outcomeFor,
  parseQuery,
  type Action,
  type Level,
  type Owner,
  type Platform,
  type When,
} from "@/lib/batdau";

type ApiProbe = "checking" | "ok" | "down";

const LEVEL_TONE: Record<Level, BadgeTone> = {
  khong: "critical",
  "quan-sat": "neutral",
  "de-xuat": "violet",
  "thi-nghiem": "good",
};

/** Bậc thang ba mức — thứ tự đọc từ thấp lên cao. */
const LADDER: Level[] = ["quan-sat", "de-xuat", "thi-nghiem"];

// ---------------------------------------------------------------------------
// Mảnh giao diện dùng lại trong trang
// ---------------------------------------------------------------------------

function Choice({
  selected,
  onClick,
  title,
  note,
}: {
  selected: boolean;
  onClick: () => void;
  title: string;
  note?: string;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={
        "focus-ring flex min-h-ctl flex-col items-start justify-center gap-0.5 " +
        "rounded-md border px-4 py-2 text-left transition-colors duration-short2 ease-emphasized " +
        (selected
          ? "border-s1 bg-s1/15 text-ink"
          : "border-hairline bg-raised text-sec hover:border-white/20 hover:text-ink")
      }
    >
      <span className="flex items-center gap-1.5 text-body font-semibold">
        <span aria-hidden className={selected ? "text-info-ink" : "text-mut"}>
          {selected ? "✓" : "○"}
        </span>
        {title}
      </span>
      {note ? <span className="text-meta leading-snug text-dim">{note}</span> : null}
    </button>
  );
}

function Question({
  n,
  label,
  wide,
  children,
}: {
  n: string;
  label: string;
  /** Câu 5 lựa chọn (nền tảng) cần lưới rộng hơn câu nhị phân. */
  wide?: boolean;
  children: React.ReactNode;
}) {
  return (
    <div className="border-t border-hairline pt-4 first:border-t-0 first:pt-0">
      <h3 className="flex items-center gap-2 text-strong text-ink">
        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-hairline bg-raised text-meta font-bold text-sec">
          {n}
        </span>
        {label}
      </h3>
      <div
        className={
          "mt-2 grid gap-2 " +
          (wide ? "sm:grid-cols-3 lg:grid-cols-5" : "sm:grid-cols-2")
        }
      >
        {children}
      </div>
    </div>
  );
}

/** Bậc thang năng lực: mỗi mức mang một HÌNH DẠNG và một chữ, không chỉ màu. */
function Ladder({ level, ceiling }: { level: Level; ceiling: Level }) {
  return (
    <div className="flex flex-wrap gap-2">
      {LADDER.map((step) => {
        const reached = LEVEL_ORDER[level] >= LEVEL_ORDER[step];
        const reachable = !reached && LEVEL_ORDER[ceiling] >= LEVEL_ORDER[step];
        const shape: StatusShape = reached ? "on" : reachable ? "drift" : "off";
        const word = reached ? "đạt hôm nay" : reachable ? "đạt sau khi chuẩn bị" : "không tới được";
        return (
          <span
            key={step}
            className={
              "flex items-center gap-2 rounded-md border px-3 py-1.5 " +
              (reached
                ? "border-s7/50 bg-s7/15"
                : reachable
                  ? "border-hairline bg-raised"
                  : "border-hairline bg-transparent")
            }
          >
            <StatusMark shape={shape} size={12} />
            <span className={reached ? "text-body font-semibold text-ink" : "text-body text-sec"}>
              {LEVEL_META[step].name}
            </span>
            <span className="text-meta text-dim">{word}</span>
          </span>
        );
      })}
    </div>
  );
}

function ActionButton({ action, apiUp }: { action: Action; apiUp: boolean }) {
  if (action.kind === "vod") return <BatDauVod label={action.label} apiUp={apiUp} />;
  return (
    <Link href={action.href} className={`${buttonCls("primary")} mt-3`}>
      {action.label}
    </Link>
  );
}

function Bullets({ items }: { items: string[] }) {
  return (
    <ul className="mt-2 space-y-1.5">
      {items.map((b, i) => (
        <li key={i} className="flex gap-2 text-body leading-relaxed text-sec">
          <span aria-hidden className="shrink-0 text-mut">
            •
          </span>
          <span>{b}</span>
        </li>
      ))}
    </ul>
  );
}

function ResultBlock({
  glyph,
  glyphCls,
  title,
  children,
}: {
  glyph: string;
  glyphCls: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-hairline pt-4">
      <h3 className="flex items-center gap-2 text-label uppercase text-dim">
        <span aria-hidden className={`text-strong ${glyphCls}`}>
          {glyph}
        </span>
        {title}
      </h3>
      <div className="mt-2">{children}</div>
    </section>
  );
}

// ---------------------------------------------------------------------------
// Trang
// ---------------------------------------------------------------------------

export default function BatDauPage() {
  const [owner, setOwner] = useState<Owner | null>(null);
  const [platform, setPlatform] = useState<Platform | null>(null);
  const [when, setWhen] = useState<When | null>(null);
  const [api, setApi] = useState<ApiProbe>("checking");

  // Đọc lựa chọn từ URL sau khi hydrate (không dùng useSearchParams để trang
  // không phải nằm trong Suspense — trạng thái ở đây là của người dùng, không
  // phải của router).
  useEffect(() => {
    const q = parseQuery(window.location.search);
    if (q.owner) setOwner(q.owner);
    if (q.platform) setPlatform(q.platform);
    if (q.when) setWhen(q.when);
  }, []);

  // Ghi ngược lên URL để mỗi tổ hợp là một link chia sẻ được.
  useEffect(() => {
    const q = new URLSearchParams();
    if (owner) q.set("cua", owner);
    if (platform) q.set("nen", platform);
    if (when) q.set("khi", when);
    const qs = q.toString();
    window.history.replaceState(null, "", qs ? `?${qs}` : window.location.pathname);
  }, [owner, platform, when]);

  useEffect(() => {
    let cancelled = false;
    listSessions(2500)
      .then(() => !cancelled && setApi("ok"))
      .catch(() => !cancelled && setApi("down"));
    return () => {
      cancelled = true;
    };
  }, []);

  const pick = useCallback((p: Platform, o: Owner, w: When) => {
    setPlatform(p);
    setOwner(o);
    setWhen(w);
  }, []);

  const answered = [owner, platform, when].filter(Boolean).length;
  const outcome = owner && platform && when ? outcomeFor(platform, owner, when) : null;
  const apiUp = api === "ok";

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      <main className="mx-auto flex w-full max-w-4xl flex-1 flex-col gap-6 px-6 py-10">
        <header>
          <h1 className="text-num-m font-extrabold leading-tight tracking-tight text-ink">
            Tôi có một buổi live — dùng được gì?
          </h1>
          <p className="mt-2 max-w-2xl text-body leading-relaxed text-sec">
            Trả lời ba câu hỏi, mỗi câu bấm một lần. Bạn nhận lại câu trả lời dứt khoát cho{" "}
            <strong className="text-ink">đúng buổi live của mình</strong>: làm được gì ngay, cần gì
            để lên mức cao hơn, và cái gì không làm được — kèm lý do thật.
          </p>
        </header>

        {/* ---- ba câu hỏi ---------------------------------------------- */}
        <Card as="section" padding="lg" className="flex flex-col gap-4">
          <Question n="1" label="Buổi live này là của ai?">
            {OWNERS.map((o) => (
              <Choice
                key={o}
                selected={owner === o}
                onClick={() => setOwner(o)}
                title={OWNER_LABEL[o]}
                note={
                  o === "toi"
                    ? "Kênh, Fanpage hoặc shop do bạn quản trị"
                    : "Buổi live bạn chỉ xem, không điều khiển được"
                }
              />
            ))}
          </Question>

          <Question n="2" label="Nền tảng nào?" wide>
            {PLATFORMS.map((p) => (
              <Choice
                key={p}
                selected={platform === p}
                onClick={() => setPlatform(p)}
                title={PLATFORM_LABEL[p]}
                note={PLATFORM_NOTE[p]}
              />
            ))}
          </Question>

          <Question n="3" label="Buổi live đang phát hay đã kết thúc?">
            {WHENS.map((w) => (
              <Choice
                key={w}
                selected={when === w}
                onClick={() => setWhen(w)}
                title={WHEN_LABEL[w]}
                note={
                  w === "dang-phat"
                    ? "Đang lên sóng ngay bây giờ"
                    : "Đã phát xong, giờ xem lại"
                }
              />
            ))}
          </Question>

          {answered > 0 && (
            <div className="flex items-center justify-between gap-3 border-t border-hairline pt-3">
              <span className="text-meta text-dim">Đã chọn {answered}/3 câu.</span>
              <button
                type="button"
                onClick={() => {
                  setOwner(null);
                  setPlatform(null);
                  setWhen(null);
                }}
                className="focus-ring min-h-tap rounded-md px-2.5 py-1 text-meta font-semibold text-sec transition-colors duration-short2 ease-emphasized hover:bg-raised hover:text-ink"
              >
                Đặt lại
              </button>
            </div>
          )}
        </Card>

        {/* ---- kết quả cho đúng tổ hợp đã chọn -------------------------- */}
        {outcome && platform && owner && when ? (
          <Card as="section" padding="lg" className="flex flex-col gap-4">
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <Badge tone={LEVEL_TONE[outcome.level]} dot>
                  {outcome.level === "khong"
                    ? "Hôm nay: không làm được"
                    : `Hôm nay đạt: ${LEVEL_META[outcome.level].name}`}
                </Badge>
                {LEVEL_ORDER[outcome.ceiling] > LEVEL_ORDER[outcome.level] ? (
                  <Badge tone="warn">
                    Trần sau khi chuẩn bị: {LEVEL_META[outcome.ceiling].name}
                  </Badge>
                ) : null}
                <span className="text-meta text-dim">
                  {PLATFORM_LABEL[platform]} · {OWNER_LABEL[owner].toLowerCase()} ·{" "}
                  {WHEN_LABEL[when].toLowerCase()}
                </span>
              </div>
              <p className="mt-3 text-title leading-snug text-ink">{outcome.headline}</p>
              <div className="mt-3">
                <Ladder level={outcome.level} ceiling={outcome.ceiling} />
              </div>
            </div>

            {/* Tổ hợp không làm được gì thì khối này KHÔNG được đeo dấu ✓ xanh:
                một dấu tích xanh đặt trên câu "không gì cả" là tín hiệu sai.
                Nó đổi thành mũi tên chỉ đường thay thế. */}
            <ResultBlock
              glyph={outcome.level === "khong" ? "→" : "✓"}
              glyphCls={outcome.level === "khong" ? "text-info-ink" : "text-good-ink"}
              title={
                outcome.level === "khong"
                  ? "Làm được gì ngay bây giờ — và đường thay thế gần nhất"
                  : "Làm được gì ngay bây giờ"
              }
            >
              <p className="text-body leading-relaxed text-sec">{outcome.now.body}</p>
              {outcome.now.bullets ? <Bullets items={outcome.now.bullets} /> : null}
              {outcome.now.action ? (
                <ActionButton action={outcome.now.action} apiUp={apiUp} />
              ) : null}
            </ResultBlock>

            <ResultBlock glyph="↑" glyphCls="text-warn-ink" title="Cần gì để lên mức cao hơn">
              {outcome.upgrade.time ? (
                <p className="mb-2 flex flex-wrap items-center gap-2">
                  <Badge tone="warn">Ước tính: {outcome.upgrade.time}</Badge>
                  {outcome.upgrade.doc ? (
                    <span className="text-meta text-dim">
                      Hướng dẫn có sẵn trong repo:{" "}
                      <span className="rounded bg-raised px-1 py-0.5 text-sec">
                        {outcome.upgrade.doc}
                      </span>
                    </span>
                  ) : null}
                </p>
              ) : (
                <p className="mb-2">
                  <Badge tone="critical">Không có đường lên từ tổ hợp này</Badge>
                </p>
              )}
              <p className="text-body leading-relaxed text-sec">{outcome.upgrade.body}</p>
              {outcome.upgrade.bullets ? <Bullets items={outcome.upgrade.bullets} /> : null}
              {outcome.upgrade.action ? (
                <ActionButton action={outcome.upgrade.action} apiUp={apiUp} />
              ) : null}
            </ResultBlock>

            <ResultBlock glyph="✕" glyphCls="text-crit-ink" title="Không làm được gì, và vì sao">
              <ul className="space-y-3">
                {outcome.blocked.map((b, i) => (
                  <li key={i}>
                    <p className="text-body font-semibold text-ink">{b.label}</p>
                    <p className="mt-0.5 text-body leading-relaxed text-sec">{b.why}</p>
                  </li>
                ))}
              </ul>
            </ResultBlock>
          </Card>
        ) : (
          <Card as="section" padding="lg">
            <p className="text-body leading-relaxed text-sec">
              Chọn đủ ba câu ở trên để nhận câu trả lời. Mỗi tổ hợp có một câu trả lời riêng —
              20 tổ hợp, 20 câu trả lời khác nhau. Chưa muốn chọn thì xem thẳng bảng toàn cảnh
              bên dưới.
            </p>
          </Card>
        )}

        {/* ---- ma trận đầy đủ ------------------------------------------ */}
        <section>
          <SectionTitle meta="Bấm vào một ô để xem câu trả lời đầy đủ">
            Toàn cảnh: 5 nền tảng × của ai × khi nào
          </SectionTitle>
          <Card padding="none" className="overflow-x-auto">
            <table className="w-full min-w-[46rem] border-collapse text-left">
              <thead>
                <tr className="border-b border-hairline">
                  <th scope="col" className="px-3 py-2 text-meta font-semibold text-dim">
                    Nền tảng
                  </th>
                  {OWNERS.map((o) =>
                    WHENS.map((w) => (
                      <th
                        key={`${o}-${w}`}
                        scope="col"
                        className="px-3 py-2 text-meta font-semibold text-dim"
                      >
                        {OWNER_LABEL[o]}
                        <br />
                        <span className="font-normal">{WHEN_LABEL[w].toLowerCase()}</span>
                      </th>
                    )),
                  )}
                </tr>
              </thead>
              <tbody>
                {PLATFORMS.map((p) => (
                  <tr key={p} className="border-b border-hairline last:border-b-0">
                    <th
                      scope="row"
                      className="px-3 py-2 text-body font-semibold text-ink"
                    >
                      {PLATFORM_LABEL[p]}
                    </th>
                    {OWNERS.map((o) =>
                      WHENS.map((w) => {
                        const cell = outcomeFor(p, o, w);
                        const active = platform === p && owner === o && when === w;
                        const climbs = LEVEL_ORDER[cell.ceiling] > LEVEL_ORDER[cell.level];
                        return (
                          <td key={`${p}-${o}-${w}`} className="p-1.5 align-top">
                            <button
                              type="button"
                              onClick={() => pick(p, o, w)}
                              aria-pressed={active}
                              className={
                                "focus-ring flex min-h-tap w-full flex-col items-start gap-1 " +
                                "rounded-md border px-2.5 py-2 text-left transition-colors " +
                                "duration-short2 ease-emphasized " +
                                (active
                                  ? "border-s1 bg-s1/15"
                                  : "border-transparent hover:border-white/20 hover:bg-raised")
                              }
                            >
                              <Badge
                                tone={LEVEL_TONE[cell.level]}
                                mark={cell.level === "khong" ? "off" : "on"}
                                className="whitespace-nowrap"
                              >
                                {LEVEL_META[cell.level].short}
                              </Badge>
                              {climbs ? (
                                <span className="whitespace-nowrap text-meta text-dim">
                                  ↑ {LEVEL_META[cell.ceiling].short}
                                </span>
                              ) : null}
                            </button>
                          </td>
                        );
                      }),
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
          <p className="mt-2 text-meta leading-relaxed text-dim">
            Huy hiệu là mức đạt được <strong className="text-sec">hôm nay</strong>; mũi tên ↑ là
            trần đạt tới được <strong className="text-sec">sau khi chuẩn bị xong</strong> (bấm vào
            ô để biết chuẩn bị những gì và mất bao lâu). “Hôm nay” nghĩa là với đúng những gì repo
            đang có: chưa có khoá YouTube, chưa có Page token Facebook, chưa có danh tính Shopee.
            Mọi ô trong bảng đều có bằng chứng trong docs/nen-tang-ho-tro.md — đã thử thật, hoặc
            tài liệu chính thức, hoặc “không thể” kèm lý do.
          </p>
        </section>

        {/* ---- ba mức năng lực ----------------------------------------- */}
        <section>
          <SectionTitle>Ba mức năng lực, nói cho gọn</SectionTitle>
          <div className="grid gap-3 md:grid-cols-3">
            {LADDER.map((l) => (
              <Card key={l} padding="md" className="flex flex-col gap-2">
                <Badge tone={LEVEL_TONE[l]} dot>
                  {LEVEL_META[l].name}
                </Badge>
                <p className="text-strong text-ink">{LEVEL_META[l].oneLiner}</p>
                <p className="text-body leading-relaxed text-sec">{LEVEL_META[l].what}</p>
                <p className="mt-auto border-t border-hairline pt-2 text-meta leading-relaxed text-dim">
                  <strong className="text-sec">Cần gì:</strong> {LEVEL_META[l].needs}
                </p>
              </Card>
            ))}
          </div>
        </section>

        {/* ---- ba thứ bắt buộc của một thí nghiệm thật ------------------ */}
        <section>
          <SectionTitle meta="Thiếu một trong ba là hệ thống tuyên bố THIẾU, không bịa số">
            Một thí nghiệm nhân quả thật cần đúng ba thứ
          </SectionTitle>
          <div className="grid gap-3 md:grid-cols-3">
            {THREE_REQUIREMENTS.map((r) => (
              <Card key={r.n} padding="md" className="flex flex-col gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full border border-hairline bg-raised text-meta font-bold text-sec">
                  {r.n}
                </span>
                <p className="text-strong text-ink">{r.title}</p>
                <p className="text-body leading-relaxed text-sec">{r.body}</p>
              </Card>
            ))}
          </div>
        </section>

        <footer className="mt-auto flex flex-col items-start gap-2 border-t border-hairline pt-4 text-meta text-dim sm:flex-row sm:items-center sm:justify-between">
          <span>
            Nguồn của mọi kết luận trên trang này: docs/nen-tang-ho-tro.md và
            docs/mo-hinh-van-hanh-kol.md (đo ngày 10–11/09/2026).
          </span>
          <Link
            href="/"
            className="focus-ring shrink-0 rounded transition-colors duration-short2 ease-emphasized hover:text-sec"
          >
            Về trang chính
          </Link>
        </footer>
      </main>
    </div>
  );
}
