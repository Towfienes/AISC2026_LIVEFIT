"use client";

/**
 * "/desk" — Bàn trợ live (control desk). OPERATOR screen: it is the one view
 * that is allowed to see the assignment. Nothing here may import HostView,
 * useHost or HostState — the blinding boundary (rule L6) runs along this file.
 *
 * ---------------------------------------------------------------------------
 * LAYOUT (gói DESK-HOST v2 — theo mockup mock_desk.png của spec UI-VISUAL)
 * ---------------------------------------------------------------------------
 * Thứ tự ưu tiên không đổi so với gói UI-2 (đồng hồ khối là căn cước khoa học
 * của bàn, dính đầu màn hình); hình dạng đổi theo mockup đã duyệt:
 *
 *   1. thanh trạng thái v2 — đèn ĐANG PHÁT (ngoại lệ pulse duy nhất), timecode
 *      mono, chọn phiên, chế độ, Kết thúc + ô lỗi dành sẵn; sticky cùng hero;
 *   2. HÀNG HERO (BlockClock v2) — thẻ KHỐI HIỆN TẠI (chữ BẬT/TẮT cỡ hiển thị,
 *      MỘT câu giải thích, đếm ngược "Chuyển khối sau", vòng on-air khi BẬT)
 *      + thẻ LỊCH BẬT/TẮT (dải khối, vạch "đang ở đây", câu ranh giới làm mù);
 *   3. cột trái — KPI: người xem, bình luận/phút, lượt bấm/phút, ý định mua
 *      (radar), tim & quà. Ô nào thiếu nguồn in chip THIẾU + lý do NGUYÊN VĂN
 *      của ma trận tín hiệu — không bao giờ một số 0 giả; khung video ở đáy
 *      cột (bối cảnh phụ trợ, nhường chỗ đầu tiên);
 *   4. cột giữa — biểu đồ NHỊP PHIÊN nhuộm vùng khối BẬT + đường dự báo
 *      nếu-không-can-thiệp + vạch đang-ở-đây (`min-h` sàn để không bao giờ sập
 *      về 4px), dưới là radar + feed bình luận;
 *   5. cột phải — HÀNH ĐỘNG GỢI Ý: thẻ #1 viền gradient là "việc cần làm
 *      ngay", các thẻ sau nhỏ dần; panel TỰ LÁI + cảnh báo im lặng từ backend.
 *
 * When the content no longer fits, the page SCROLLS (the browser scrollbar is
 * the indicator, and the card list adds its own "cuộn để xem hết" line) instead
 * of silently cutting content off. Ở 1920×1080 toàn bàn hiện đủ không cuộn.
 *
 * LIẾC 1 GIÂY Ở 1366×768 (gói C — Bàn trợ live v3): nút hành động của thẻ #1
 * phải nằm trong MÀN HÌNH ĐẦU TIÊN. Ảnh f06 đo được thẻ #1 bắt đầu ở y≈600 và
 * nút "Ghim ngay" nằm dưới mép màn. Ba chỗ ăn chiều cao đã được cắt: câu dẫn
 * của PageHeader (ẩn khi phiên đang phát), StatusBar gãy hai dòng (nay một
 * dòng), hàng hero ~285px (nay hai cột, thẻ lịch cao vừa nội dung). Khung Bộ
 * thu bình luận (gói C7) nằm đầu CỘT GIỮA — thấy được ngay mà không đẩy cột
 * hành động bên phải xuống.
 *
 * First-time-user rules: an empty state instead of a blank screen when no
 * session is running, skeletons instead of a blank screen while connecting,
 * plain-Vietnamese labels, jargon explained in-context via <Term> tooltips.
 */

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import ActionCard, { forecastLacksData } from "@/components/ActionCard";
import BlockClock, { actionLockReason, deriveCurrentBlock } from "@/components/BlockClock";
import CommentFeed from "@/components/CommentFeed";
import CommentRadar from "@/components/CommentRadar";
import IngestPanel from "@/components/IngestPanel";
import LiveVideo from "@/components/LiveVideo";
import RhythmChart from "@/components/RhythmChart";
import SignalTiles, { buildSignalTiles } from "@/components/SignalTiles";
import StatusBar from "@/components/StatusBar";
import PageHeader from "@/components/PageHeader";
import TopNav from "@/components/TopNav";
import Badge from "@/components/ui/Badge";
import Button, { buttonCls } from "@/components/ui/Button";
import Callout from "@/components/ui/Callout";
import Card from "@/components/ui/Card";
import EmptyState from "@/components/ui/EmptyState";
import SectionTitle from "@/components/ui/SectionTitle";
import Skeleton from "@/components/ui/Skeleton";
import { getReactions, getSessionDetail, getSignalCoverage, youtubeVideoId } from "@/lib/api";
import { fmtTimeHCM } from "@/lib/format";
import type {
  ActionCardData,
  ConnectionKind,
  SessionDetail,
  SessionSummary,
  SignalCoverage,
  SignalStateItem,
} from "@/lib/types";
import { DeskCommandError, executeNotice, isNetworkError, useDesk } from "@/lib/useDesk";

/**
 * Phần hẹp của `SignalStateOut` (schemas.py): máy chủ gửi `secondary` — số
 * lượt bấm THÔ kèm nhãn, chỉ có khi đã ghi được ít nhất một lượt bấm — nhưng
 * `SignalStateItem` của types.ts (tệp đóng băng) chưa khai trường này.
 */
interface SignalStateWire {
  secondary?: string | null;
}

/**
 * Phiên đã ghi nhận lượt bấm cho mô hình dự báo học chưa (gói C6, sửa phản biện).
 *
 * Đọc từ MA TRẬN TÍN HIỆU, KHÔNG từ `tick.click_count`: máy chủ lưu số đó bằng
 * 0 cho mọi tick của phiên thật (redirect chỉ ghi lượt bấm + phát sự kiện
 * "click", không sửa tick), nên suy từ tick khiến mọi thẻ luôn ghi "chưa đủ
 * dữ liệu để dự báo" rồi nhấp nháy mỗi lần WebSocket báo một lượt bấm.
 *
 * - `ok` ⇒ có lượt bấm hợp lệ ⇒ true.
 * - `degraded` mang HAI nghĩa (signals._clicks_state): có link đo mà chưa ai
 *   bấm (không có số thô `secondary`) ⇒ false; hoặc có lượt bấm hợp lệ nhưng
 *   đa số bị gắn cờ (có `secondary`) ⇒ true.
 * - `missing` (không có link đo, hoặc 0 lượt HỢP LỆ) ⇒ false.
 * - Chưa có ma trận / ma trận không có dòng clicks ⇒ null (chưa biết).
 */
function clicksObservedFrom(signals: SignalCoverage | null): boolean | null {
  const clicks = signals?.signals.find((s) => s.name === "clicks");
  if (!clicks) return null;
  if (clicks.status === "ok") return true;
  if (clicks.status === "degraded") {
    const secondary = (clicks as SignalStateItem & SignalStateWire).secondary;
    return typeof secondary === "string" && secondary.trim().length > 0;
  }
  return false;
}

/**
 * Đường tới báo cáo phiên — CHỈ khi bàn đang nói chuyện với máy chủ thật.
 * Bản xem thử (mock) có phiên mẫu "đã kết thúc" nhưng /bao-cao/[id] chỉ đọc
 * máy chủ: nút nổi bật nhất màn hình sẽ dẫn vào trang lỗi.
 */
function reportHrefFor(connection: ConnectionKind, sessionId: string | null): string | null {
  return connection === "live" && sessionId ? `/bao-cao/${sessionId}` : null;
}

/**
 * Phần hẹp của `SessionOut` (src/livelift/api/schemas.py) mà khung Bộ thu bình
 * luận cần: máy chủ gửi `dry_run` trong mọi phiên, nhưng `SessionSummary` của
 * types.ts (tệp đóng băng) chưa khai trường này.
 */
interface SessionFlagsWire {
  dry_run?: boolean;
  is_demo?: boolean;
}

/**
 * Gói C7: nguồn MÔ PHỎNG chỉ được mời chọn cho phiên CHẠY THỬ (`dry_run`) hoặc
 * phiên DỮ LIỆU MẪU (`is_demo`). Phiên thật mà thu bình luận mô phỏng là trộn
 * dữ liệu giả vào kết quả thật — máy chủ chặn bằng 422, bàn không mời bấm nhầm.
 * Thiếu cờ (máy chủ cũ) nghĩa là KHÔNG cho phép.
 */
function allowsSimulatedSource(session: SessionSummary | null): boolean {
  if (!session) return false;
  const flags = session as SessionSummary & SessionFlagsWire;
  return flags.dry_run === true || flags.is_demo === true;
}

/** Câu của máy chủ thường không có dấu chấm cuối — thêm để nối câu sau cho gọn. */
function sentence(text: string): string {
  const t = text.trim();
  return /[.!?…]$/.test(t) ? t : `${t}.`;
}

/**
 * Câu báo lỗi của một lệnh vận hành (gói C1 — giới hạn #6).
 *
 * `detail` là NGUYÊN VĂN câu máy chủ (409 "Khối TẮT: …", hết hàng…) mà
 * useDesk đã giữ lại. Lời dặn "kiểm tra kết nối" CHỈ đi kèm lỗi mạng thật —
 * bản cũ luôn nối lời dặn đó, đẩy người vận hành đi sửa một đường mạng không
 * hỏng trong khi máy chủ đã nói rõ vì sao từ chối.
 */
function commandAlert(lead: string, e: unknown, ifNetwork: string, otherwise: string): string {
  const network = e instanceof DeskCommandError ? e.network : isNetworkError(e);
  const detail = sentence(e instanceof Error && e.message ? e.message : "Máy chủ không nhận lệnh");
  return `${lead}: ${detail} ${network ? ifNetwork : otherwise}`.trim();
}

/** Clicks landed in the last 60 s — ticks are 30 s buckets, so this is the tail. */
function clicksInLastMinute(
  ticks: { offset_s: number; click_count: number }[],
  nowS: number,
): number | null {
  const recent = ticks.filter((t) => t.offset_s > nowS - 60 && t.offset_s <= nowS);
  if (recent.length === 0) return null;
  return recent.reduce((sum, t) => sum + t.click_count, 0);
}

/**
 * True while a scroll container has more content than it shows. Drives the
 * explicit "cuộn để xem hết" line: a 8 px recessive scrollbar is not a strong
 * enough signal on a desk the operator only glances at.
 */
function useIsOverflowing(key: unknown) {
  const ref = useRef<HTMLDivElement | null>(null);
  const [overflowing, setOverflowing] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const check = () => setOverflowing(el.scrollHeight - el.clientHeight > 4);
    check();
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => ro.disconnect();
  }, [key]);
  return { ref, overflowing };
}

/**
 * Mirror of the layout while the first connection is racing.
 *
 * Khung xám không nói được là đang TẢI hay đã HỎNG, nên có thêm một dòng
 * `role="status"`: nó cũng là chỗ trình đọc màn hình biết bàn đang bận.
 */
function DeskSkeleton() {
  return (
    <main className="flex flex-1 flex-col p-3" aria-busy>
      <p role="status" className="mb-2 shrink-0 text-body text-sec">
        Đang kết nối tới máy chủ và tải phiên đang phát… Bàn sẽ hiện ngay khi có dữ liệu, bạn không
        cần tải lại trang.
      </p>
      <div className="mb-3 flex flex-col gap-3">
        <Skeleton className="h-bar shrink-0 rounded-lg" />
        {/* hàng hero v3: thẻ khối hai cột (~11rem) + thẻ lịch cao vừa nội dung */}
        <div className="grid grid-cols-1 items-start gap-3 xl:grid-cols-[minmax(26rem,34rem)_minmax(0,1fr)]">
          <Skeleton className="h-44 rounded-lg" />
          <Skeleton className="h-36 rounded-lg" />
        </div>
      </div>
      <div className="grid flex-1 grid-cols-1 gap-3 xl:grid-cols-[minmax(16rem,19rem)_minmax(0,1fr)_minmax(21rem,25rem)] xl:grid-rows-[minmax(18rem,1fr)_minmax(14rem,auto)]">
        {/* cột KPI */}
        <div className="flex flex-col gap-2.5 xl:col-start-1 xl:row-span-2 xl:row-start-1">
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
          <Skeleton className="h-24 rounded-lg" />
        </div>
        {/* biểu đồ + radar */}
        <Card padding="sm" className="flex min-h-[18rem] flex-col gap-2 xl:col-start-2 xl:row-start-1">
          <Skeleton className="h-4 w-24" />
          <Skeleton className="min-h-[12rem] flex-1" />
        </Card>
        <Card padding="sm" className="flex min-h-[14rem] flex-col gap-2 xl:col-start-2 xl:row-start-2">
          <Skeleton className="h-4 w-40" />
          <Skeleton className="min-h-[6rem] flex-[2]" />
          <div className="flex min-h-[6rem] flex-[3] flex-col gap-1.5 border-t border-hairline pt-2">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-5 w-2/3" />
            <Skeleton className="h-5 w-4/5" />
          </div>
        </Card>
        {/* cột hành động */}
        <Card
          padding="sm"
          className="flex min-h-[14rem] flex-col gap-3 xl:col-start-3 xl:row-span-2 xl:row-start-1"
        >
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-32" />
          <Skeleton className="h-24" />
          <Skeleton className="h-24" />
        </Card>
      </div>
    </main>
  );
}

/**
 * Never a blank screen: friendly guidance when nothing is running (NN/g empty states).
 *
 * Người mở bàn trợ live khi chưa có phiên nào gần như chắc chắn cần TẠO phiên,
 * không phải xem demo — nên nút chính là "Chuẩn bị phiên mới", xem thử là phụ.
 */
function EmptyDesk({
  hasEndedSessions,
  onDemo,
  onShowAnyway,
}: {
  hasEndedSessions: boolean;
  onDemo: () => void;
  onShowAnyway: () => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center">
      <EmptyState
        icon="📭"
        title="Chưa có phiên nào đang chạy"
        hint="Bàn trợ live sẽ hiện nhịp phiên, thẻ gợi ý và bình luận khi một phiên live bắt đầu. Chuẩn bị một phiên mới, hoặc xem thử với dữ liệu mẫu."
        action={
          <>
            <Link href="/chay-phien" className={buttonCls("primary")}>
              Chuẩn bị phiên mới
            </Link>
            <Button variant="ghost" onClick={onDemo}>
              Xem thử với dữ liệu mẫu
            </Button>
            <Link href="/" className={buttonCls("ghost")}>
              Về trang chính
            </Link>
          </>
        }
      />
      {hasEndedSessions && (
        <button
          type="button"
          onClick={onShowAnyway}
          className="focus-ring flex min-h-ctl items-center rounded px-3 text-body text-dim underline decoration-dotted underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-sec"
        >
          Vẫn mở Bàn trợ live với phiên đã kết thúc
        </button>
      )}
    </div>
  );
}

export default function DeskPage() {
  const [demoMode, setDemoMode] = useState(false);
  const [showAnyway, setShowAnyway] = useState(false);
  const [endBusy, setEndBusy] = useState(false);
  /**
   * Lỗi vận hành đang chờ người xử lý. Một ô duy nhất trên StatusBar cho cả
   * lệnh Thực hiện lẫn Kết thúc phiên: hai chỗ báo lỗi khác nhau là hai chỗ có
   * thể bỏ sót.
   */
  const [alert, setAlert] = useState<string | null>(null);
  /**
   * Xác nhận sau một lệnh Thực hiện THÀNH CÔNG mà kết quả khác điều người vận
   * hành vừa bấm (máy chủ bốc thăm công bằng giữa các thẻ ngang nhau — gói C3).
   * Nằm ngay trong cột hành động, cạnh chỗ vừa bấm; người vận hành tự đóng.
   */
  const [notice, setNotice] = useState<string | null>(null);
  /**
   * Deep link `/desk?session=ID` (gói WIZARD, spec UX-FLOW luồng 3): wizard
   * Chuẩn bị phiên chuyển sang đây ngay sau khi bấm "Bắt đầu phát sóng" và
   * bàn phải mở ĐÚNG phiên đó. Đọc bằng window.location (không dùng
   * useSearchParams để trang không phải bọc Suspense — tiền lệ /bat-dau);
   * khởi tạo lười + guard `typeof window` vì trang còn được prerender.
   */
  const [preferredSessionId] = useState<string | null>(() =>
    typeof window === "undefined"
      ? null
      : new URLSearchParams(window.location.search).get("session"),
  );
  const desk = useDesk({ forceMock: demoMode, preferredSessionId });

  const clicksPerMin = useMemo(
    () => clicksInLastMinute(desk.ticks, desk.elapsedS),
    [desk.ticks, desk.elapsedS],
  );
  const cardList = useIsOverflowing(desk.cards.length);

  /**
   * Gói UI-KOL: session detail (video id for the embed), the signal matrix
   * (what this session can honestly measure) and the paid-event count. The
   * matrix is the AUTHORITY for the signal tiles: a tile whose source is
   * missing renders "THIẾU nguồn" with the server's reason — never a fake 0.
   */
  const [videoDetail, setVideoDetail] = useState<SessionDetail | null>(null);
  const [signalCov, setSignalCov] = useState<SignalCoverage | null>(null);
  const [reactionsTotal, setReactionsTotal] = useState<number | null>(null);

  useEffect(() => {
    setVideoDetail(null);
    setSignalCov(null);
    setReactionsTotal(null);
    if (desk.connection !== "live" || !desk.sessionId) return;
    const sid = desk.sessionId;
    let cancelled = false;
    getSessionDetail(sid)
      .then((d) => {
        if (!cancelled) setVideoDetail(d);
      })
      .catch(() => {
        // không tải được chi tiết phiên: khung video hiện trạng thái thiếu
      });
    const pullMatrix = () => {
      getSignalCoverage(sid)
        .then((c) => {
          if (!cancelled) setSignalCov(c);
        })
        .catch(() => {
          // ma trận chưa tải được: ô tín hiệu giữ trạng thái "—", không đoán
        });
      getReactions(sid)
        .then((rs) => {
          if (!cancelled) setReactionsTotal(rs.length);
        })
        .catch(() => {
          // thiếu số đếm thì ô Tim & quà hiện "—" thay vì một số bịa
        });
    };
    pullMatrix();
    // Ma trận đổi chậm (nguồn xuất hiện/mất theo phút) — 30 giây là đủ tươi.
    const timer = setInterval(pullMatrix, 30000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [desk.connection, desk.sessionId]);

  /**
   * Cùng luật không-bịa-số cho lượt bấm: khi ma trận tín hiệu nói phiên KHÔNG
   * có link đo (clicks = missing), tổng click_count của các tick chỉ là chỗ
   * trống — ô KPI phải nhận null (chip THIẾU), không phải một số 0 giả.
   * Chưa có ma trận (mock/đang tải) thì giữ số đo hiện có.
   */
  const clicksUnmeasured =
    signalCov?.signals.some((s) => s.name === "clicks" && s.status === "missing") ?? false;
  const honestClicksPerMin = clicksUnmeasured ? null : clicksPerMin;
  /**
   * Gói C6: dự báo trên thẻ là mô hình LƯỢT BẤM. Phiên chưa ghi nhận lượt bấm
   * nào thì con số đó chỉ là phân phối tiên nghiệm — thẻ ghi "chưa đủ dữ liệu
   * để dự báo". Nguồn là ma trận tín hiệu (xem clicksObservedFrom); chưa có
   * ma trận (bản xem thử, đang tải) thì null — không kết luận.
   */
  const clicksObserved = clicksObservedFrom(signalCov);
  const reportHref = reportHrefFor(desk.connection, desk.sessionId);

  const tiles = useMemo(
    () =>
      buildSignalTiles({
        signals: signalCov,
        connection: desk.connection,
        viewers: desk.viewers,
        ticks: desk.ticks,
        clicksPerMin: honestClicksPerMin,
        reactionsTotal,
        comments: desk.comments,
        nowS: desk.elapsedS,
        ended: desk.session?.status === "ended",
      }),
    [
      signalCov,
      desk.connection,
      desk.viewers,
      desk.ticks,
      honestClicksPerMin,
      reactionsTotal,
      desk.comments,
      desk.elapsedS,
      desk.session,
    ],
  );

  /**
   * Cùng ma trận, cùng luật, áp cho BIỂU ĐỒ NHỊP PHIÊN — khung lớn nhất của
   * bàn. Panel nào không có nguồn thì hiện dải THIẾU kèm lý do của máy chủ,
   * không vẽ đường phẳng ở mức 0 từ tick placeholder.
   */
  const missingReason = (name: string): string | null => {
    const s = signalCov?.signals.find((x) => x.name === name);
    return s && s.status === "missing" ? s.detail : null;
  };
  const viewersMissingReason = missingReason("ticks");
  const clicksMissingReason = missingReason("clicks");
  /**
   * Phiên QUAN SÁT: máy chủ nói không có lịch gán ngẫu nhiên. Hai chỗ trên bàn
   * phải nói thật thay vì hứa hão — đồng hồ khối (không có khối nào để ở
   * "ngoài") và cột thẻ hành động (sẽ KHÔNG BAO GIỜ có thẻ, nên câu "thẻ mới
   * sẽ tự hiện trong vài phút đầu phiên" là một lời hứa sai).
   */
  const observational = missingReason("schedule") != null;

  /**
   * `useDesk.execute` THROWS when the API refuses the command (and rolls the
   * card back out of the executed set). The old call site was
   * `onExecute={() => void desk.execute(c)}`: the rejection went to an unhandled
   * promise, the card quietly un-executed itself, and the operator was never
   * told the pin had not happened.
   *
   * Gói C1 (giới hạn #6): câu lỗi là NGUYÊN VĂN câu của máy chủ (409 "Khối
   * TẮT: …", hết hàng…). Chỉ khi lỗi mạng thật mới dặn "kiểm tra kết nối" —
   * câu cũ luôn nối thêm lời dặn đó, đẩy người vận hành đi sửa mạng không hỏng.
   * Gói C3: lệnh thành công thì ĐỌC kết quả — máy chủ có thể đã bốc thăm và
   * ghim một sản phẩm khác thẻ vừa bấm; nói rõ để không ai ghim tay lại.
   */
  const runCard = (card: ActionCardData) => {
    setAlert(null);
    setNotice(null);
    const sent = desk.execute(card).then((outcome) => setNotice(executeNotice(outcome)));
    sent.catch((e: unknown) => {
      setAlert(
        commandAlert(
          `Không thực hiện được thẻ “${card.headline}”`,
          e,
          "Thẻ đã được trả lại danh sách — kiểm tra kết nối rồi bấm Thực hiện lại.",
          "Thẻ đã được trả lại danh sách.",
        ),
      );
    });
  };

  /**
   * Gói C9: xác nhận hai bước nằm TẠI CHỖ trong StatusBar (EndSessionControl) —
   * tới được đây nghĩa là người vận hành đã bấm "Kết thúc ngay".
   */
  const endSession = () => {
    setEndBusy(true);
    setAlert(null);
    desk
      .endSession()
      .catch((e: unknown) => {
        setAlert(
          commandAlert(
            "Không kết thúc được phiên",
            e,
            "Kiểm tra kết nối rồi bấm Kết thúc phiên lại.",
            // Máy chủ từ chối thì câu của nó đã đủ (vd "Phiên đã ở trạng thái
            // cuối…") — không đoán thêm phiên còn phát hay không.
            "",
          ),
        );
      })
      .finally(() => setEndBusy(false));
  };

  // Lời xác nhận thuộc về đúng một phiên.
  useEffect(() => {
    setNotice(null);
  }, [desk.sessionId]);

  /**
   * Gói C2: khoá nút hành động trong khối TẮT / khoảng trôi / ngoài lịch —
   * đúng ba trường hợp máy chủ trả 409. Bàn trợ live vốn đã hiện BẬT/TẮT cỡ
   * chữ lớn nên khoá ở đây không lộ thêm gì; màn người dẫn không dùng thẻ này.
   */
  const sessionEnded = desk.session?.status === "ended";
  const blockView = deriveCurrentBlock(desk.blocks, desk.currentBlock, desk.elapsedS);
  const cardLock = sessionEnded
    ? null
    : actionLockReason(blockView, desk.blocks.length > 0 || desk.currentBlock != null);
  const onAir = desk.session?.status === "live";
  const sessionClosed = sessionEnded || desk.session?.status === "cancelled";
  /** Gói C7: khung Bộ thu bình luận — máy chủ thật, phiên chưa đóng. */
  const showIngest = desk.connection === "live" && desk.sessionId != null && !sessionClosed;

  const hasLive = desk.sessions.some((s) => s.status === "live");
  const nothingToShow =
    desk.connection !== "connecting" &&
    !showAnyway &&
    (desk.sessionId == null || (desk.connection === "live" && !hasLive));
  /**
   * Gói C4: trạng thái rỗng chỉ dành cho lúc MỞ bàn mà chưa có phiên nào đang
   * phát. Một khi bàn đã hiện, kết thúc phiên (phiên live DUY NHẤT) không được
   * hất người vận hành về "Chưa có phiên nào đang chạy" — đúng lúc đó họ cần
   * hero "ĐÃ KẾT THÚC" và nút "Xem báo cáo phiên".
   */
  const [deskShown, setDeskShown] = useState(false);
  useEffect(() => {
    if (!nothingToShow && desk.sessionId != null) setDeskShown(true);
  }, [nothingToShow, desk.sessionId]);
  const showEmpty = nothingToShow && !(deskShown && desk.sessionId != null);

  const autopilot = desk.autopilot;

  return (
    <div className="flex min-h-screen flex-col bg-page">
      <TopNav />
      {desk.connection === "connecting" ? (
        <DeskSkeleton />
      ) : showEmpty ? (
        <EmptyDesk
          hasEndedSessions={desk.sessions.length > 0}
          onDemo={() => setDemoMode(true)}
          onShowAnyway={() => setShowAnyway(true)}
        />
      ) : (
        <main className="flex flex-1 flex-col p-3">
          {/* PageHeader chuẩn (spec UX-FLOW d1) — bản `sm` một dòng, KHÔNG
              sticky: cuộn đi được, vì trên màn vận hành từng pixel dọc thuộc
              về số liệu. Câu dẫn chỉ hiện khi phiên CHƯA phát (người mới đang
              tìm hiểu); đang phát thì từng pixel dọc thuộc về thẻ hành động. */}
          <PageHeader
            phase="trong"
            size="sm"
            title="Bàn trợ live"
            lead={
              onAir
                ? undefined
                : "Dành cho người ngồi máy (không phải người dẫn): theo dõi nhịp buổi live và bấm khi hệ thống gợi ý."
            }
          />
          {/* Ưu tiên 1 — thanh trạng thái, cảnh báo và ĐỒNG HỒ KHỐI dính đầu
              màn hình: khi trang phải cuộn (1366x768) đây là những thứ người
              vận hành không được phép mất khỏi tầm mắt. */}
          <div className="sticky top-0 z-20 -mx-3 -mt-3 mb-3 flex flex-col gap-3 bg-page px-3 pb-3 pt-3">
            <StatusBar
              connection={desk.connection}
              wsStatus={desk.wsStatus}
              sessions={desk.sessions}
              sessionId={desk.sessionId}
              onSelectSession={desk.setSessionId}
              elapsedS={desk.elapsedS}
              durationS={desk.durationS}
              mode={desk.mode}
              onSetMode={desk.setMode}
              canToggleMode={desk.canToggleMode}
              onEndSession={endSession}
              canEndSession={desk.canEndSession}
              endBusy={endBusy}
              alert={alert}
              onDismissAlert={() => setAlert(null)}
            />

            {/* degraded-data banner: amber, right under the toolbar */}
            {desk.degraded && (
              <Callout tone="warn" className="shrink-0">
                <strong>Dữ liệu suy giảm</strong> — {desk.degraded}. Bàn vẫn chạy với các nguồn còn
                lại.
              </Callout>
            )}

            <BlockClock
              blocks={desk.blocks}
              currentBlock={desk.currentBlock}
              elapsedS={desk.elapsedS}
              durationS={desk.durationS}
              pinnedName={desk.pinned?.name ?? null}
              observational={observational}
              sessionEnded={sessionEnded}
              reportHref={reportHref}
              designHash={desk.designHash}
            />
          </div>

          {/* Lưới 3 cột của mockup: KPI trái, nhịp phiên giữa, hành động phải.
              Các `minmax(...)` là sàn chiều cao — lý do biểu đồ không còn sập
              được về 4px. Dưới xl mọi thứ xếp một cột theo thứ tự ưu tiên
              (hành động trước, KPI, biểu đồ, radar). */}
          <div className="grid flex-1 grid-cols-1 gap-3 xl:grid-cols-[minmax(16rem,19rem)_minmax(0,1fr)_minmax(21rem,25rem)] xl:grid-rows-[minmax(18rem,1fr)_minmax(14rem,auto)]">
            {/* Ưu tiên 2 — cột hành động gợi ý + tự lái */}
            <div className="flex min-h-0 min-w-0 flex-col gap-3 xl:col-start-3 xl:row-span-2 xl:row-start-1">
              <Card as="section" padding="sm" className="flex min-h-[14rem] min-w-0 flex-1 flex-col">
                <SectionTitle
                  className="mb-1.5"
                  meta={
                    desk.mode === "auto" ? (
                      <Badge tone="good" dot>
                        Tự động thực thi
                      </Badge>
                    ) : (
                      <>chế độ gợi ý</>
                    )
                  }
                >
                  Hành động gợi ý
                </SectionTitle>
                {/* Gói C3 — xác nhận khi máy chủ BỐC THĂM / ghim sản phẩm khác
                    thẻ vừa bấm. Ngay cạnh chỗ vừa bấm, HÌNH (ⓘ) + CHỮ, mực
                    thông tin (không phải cảnh báo: lệnh đã thành công), người
                    vận hành tự đóng. */}
                {notice ? (
                  <div
                    role="status"
                    className="mb-2 flex shrink-0 items-start gap-2 rounded-md border border-s1/40 bg-s1/10 px-3 py-2"
                  >
                    <span aria-hidden className="mt-px shrink-0 font-bold text-info-ink">
                      ⓘ
                    </span>
                    <p className="min-w-0 flex-1 text-body leading-snug text-sec">{notice}</p>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => setNotice(null)}
                      aria-label="Đóng xác nhận ghim"
                    >
                      Đóng
                    </Button>
                  </div>
                ) : null}
                {/* Khung cuộn `absolute` trong hộp `relative` — cùng lý do với
                    feed bình luận: nội dung của một lớp absolute không đóng góp
                    chiều cao cho lưới `3fr`/`2fr` cao không xác định, nên 10 thẻ
                    không thể tự kéo dài hàng lưới và đẩy cả trang phải cuộn. */}
                <div className="relative min-h-0 flex-1">
                  <div
                    ref={cardList.ref}
                    className="absolute inset-0 flex flex-col justify-start gap-2 overflow-y-auto pr-1"
                  >
                    {desk.cards.length === 0 ? (
                      <div className="px-2 py-4">
                        <p className="text-body text-sec">
                          {observational
                            ? "Phiên quan sát — không có thẻ hành động."
                            : (desk.cardsNote ?? "Chưa có gợi ý cho thời điểm này.")}
                        </p>
                        <p className="mt-1 text-body leading-snug text-dim">
                          {observational
                            ? "Đây là buổi live của người khác, nạp lại để phân tích: hệ thống không " +
                              "ghim được sản phẩm nào và cũng không có link đo để xếp hạng, nên sẽ " +
                              "không có thẻ nào xuất hiện. Dải tín hiệu và nhịp bình luận bên trái " +
                              "vẫn là số liệu thật của buổi đó."
                            : desk.cardsNote != null
                              ? "Đây là trạng thái theo thiết kế, không phải lỗi tải dữ liệu."
                              : "Thẻ mới sẽ tự hiện khi hệ thống đủ số liệu — thường trong vài phút " +
                                "đầu phiên. Trong lúc đó cứ vận hành như thường lệ; bạn không cần chờ " +
                                "thẻ để ghim sản phẩm."}
                        </p>
                      </div>
                    ) : (
                      desk.cards.map((c, i) => (
                        <ActionCard
                          key={c.card_id}
                          card={c}
                          mode={desk.mode}
                          emphasized={i === 0}
                          executed={desk.executedCardIds.has(c.card_id)}
                          locked={cardLock}
                          noForecastBasis={forecastLacksData(c, desk.cards, { clicksObserved })}
                          peerCount={desk.cards.length}
                          onExecute={() => runCard(c)}
                          onSkip={() => desk.skip(c.card_id)}
                        />
                      ))
                    )}
                  </div>
                </div>
                {/* Gợi ý cuộn là THÔNG TIN, không phải cảnh báo: mực trung tính
                    (bản cũ dùng hổ phách — màu dành cho điều cần lo). */}
                {cardList.overflowing && (
                  <p className="mt-2 shrink-0 text-meta text-dim">
                    <span aria-hidden>↓ </span>Còn thẻ bên dưới — cuộn để xem hết{" "}
                    {desk.cards.length} thẻ.
                  </p>
                )}
                <p className="mt-2 shrink-0 border-t border-hairline pt-2 text-body leading-snug text-dim">
                  {desk.mode === "auto"
                    ? "Chế độ tự động: hệ thống tự ghim thẻ hạng 1 khi đếm ngược về 0."
                    : "Chế độ gợi ý: hệ thống chỉ đề xuất — sản phẩm chỉ được ghim khi bạn bấm Thực hiện."}
                </p>
              </Card>

              {/* Panel TỰ LÁI + CẢNH BÁO IM LẶNG — trạng thái thật của máy chủ
                  cho phiên auto (AutopilotState, operator-only). Cảnh báo tính
                  từ exposure đã lưu, nên nó kêu cả khi executor chưa từng chạy. */}
              {autopilot ? (
                <Card as="section" padding="sm" className="shrink-0">
                  <SectionTitle
                    className="mb-1.5"
                    meta={autopilot.enabled ? "máy chủ đang tự lái" : "bộ tự lái đang tắt"}
                  >
                    Tự lái phía máy chủ
                  </SectionTitle>
                  <div className="flex flex-wrap gap-x-4 gap-y-1 text-meta text-sec">
                    <span>
                      Đã thực hiện{" "}
                      <span className="tnum font-semibold text-ink">{autopilot.actions_taken}</span>{" "}
                      lệnh ghim
                    </span>
                    <span>
                      Khối BẬT có can thiệp{" "}
                      <span className="tnum font-semibold text-ink">
                        {autopilot.on_blocks_done}/{autopilot.on_blocks_total}
                      </span>
                    </span>
                    {/* Gói C11: "Nhịp tim" là thuật ngữ nội bộ — người bán cần
                        biết lần gần nhất máy chủ kiểm tra lịch để tự ghim. */}
                    <span>
                      Kiểm tra gần nhất:{" "}
                      <span className="tnum text-ink">
                        {autopilot.last_run_ts ? fmtTimeHCM(autopilot.last_run_ts) : "chưa chạy lần nào"}
                      </span>
                    </span>
                  </div>
                  {autopilot.missed_on_blocks.length > 0 && (
                    <p className="mt-1.5 text-meta leading-snug text-warn-ink">
                      Khối BẬT đã trôi qua mà không có thao tác nào:{" "}
                      <span className="tnum">
                        {autopilot.missed_on_blocks.map((i) => `#${i + 1}`).join(", ")}
                      </span>{" "}
                      — không sửa lại được, kết quả đo sẽ phản ánh mức pha loãng này.
                    </p>
                  )}
                  {autopilot.alarm ? (
                    <Callout tone="critical" className="mt-2">
                      {autopilot.alarm}
                    </Callout>
                  ) : null}
                  {autopilot.last_error ? (
                    <Callout tone="warn" className="mt-2">
                      Lỗi gần nhất của bộ tự lái: {autopilot.last_error}
                    </Callout>
                  ) : null}
                </Card>
              ) : null}
            </div>

            {/* Ưu tiên 3 — cột KPI trung thực + khung video (bối cảnh phụ trợ,
                nhường chỗ đầu tiên: nằm đáy cột, tự thu gọn dưới xl). */}
            <div className="flex min-w-0 flex-col gap-3 xl:col-start-1 xl:row-span-2 xl:row-start-1">
              <SignalTiles
                tiles={tiles}
                className="min-w-0"
                meta={
                  reportHref ? (
                    <Link
                      href={reportHref}
                      className="focus-ring rounded underline decoration-dotted underline-offset-2 transition-colors duration-short2 ease-emphasized hover:text-ink"
                    >
                      Báo cáo phiên →
                    </Link>
                  ) : undefined
                }
              />
              <LiveVideo
                videoId={youtubeVideoId(videoDetail)}
                platform={desk.session?.platform ?? null}
                defaultCollapsed
                className="min-w-0"
              />
            </div>

            {/* Cột giữa, hàng 1 — BỘ THU BÌNH LUẬN (gói C7) rồi NHỊP PHIÊN.
                Bộ thu đứng ĐẦU cột giữa: ngang tầm mắt với thẻ hành động #1
                nhưng ở cột khác, nên nó không bao giờ đẩy nút Thực hiện xuống
                dưới mép màn 1366×768 (vùng dính phía trên thì có). Chỉ khi nói
                chuyện với máy chủ thật và phiên chưa đóng: bản xem thử không
                có bộ thu, phiên đã đóng thì không còn gì để bật. */}
            <div className="flex min-w-0 flex-col gap-3 xl:col-start-2 xl:row-start-1">
              {showIngest ? (
                <div className="min-w-0 shrink-0">
                  <SectionTitle className="mb-1" meta="đưa bình luận vào radar và feed">
                    Bộ thu bình luận
                  </SectionTitle>
                  <IngestPanel
                    compact
                    sessionId={desk.sessionId}
                    sessionPlatform={desk.session?.platform ?? null}
                    sessionStatus={desk.session?.status ?? null}
                    allowSimulated={allowsSimulatedSource(desk.session)}
                  />
                </div>
              ) : null}

              {/* Ưu tiên 4 — nhịp phiên (chỉ số đầu ra chính của thí nghiệm),
                  nhuộm vùng khối BẬT + vạch đang-ở-đây (mockup, kỹ thuật D4). */}
              <Card
                as="section"
                padding="sm"
                className="flex min-h-[18rem] min-w-0 flex-1 flex-col"
              >
                <SectionTitle className="mb-1.5" meta="gộp theo phút">
                  Nhịp phiên
                </SectionTitle>
                {/* Trạng thái rỗng nằm TRONG RhythmChart: nó biết cần mấy phút
                    số liệu mới vẽ được đường, trang thì không. */}
                <div className="min-h-[12rem] flex-1">
                  <RhythmChart
                    ticks={desk.ticks}
                    viewersMissing={viewersMissingReason}
                    clicksMissing={clicksMissingReason}
                    blocks={desk.blocks}
                    positionS={desk.elapsedS}
                  />
                </div>
              </Card>
            </div>

            {/* Ưu tiên 5 — radar bình luận + feed */}
            <Card
              as="section"
              padding="sm"
              className="flex min-h-[14rem] min-w-0 flex-col xl:col-start-2 xl:row-start-2"
            >
              <SectionTitle className="mb-1.5" meta="5 phút gần nhất">
                Radar bình luận
              </SectionTitle>
              <div className="min-h-[6rem] flex-[2]">
                <CommentRadar comments={desk.comments} nowS={desk.elapsedS} />
              </div>
              <div className="mt-2 flex min-h-[6rem] flex-[3] flex-col border-t border-hairline pt-2">
                <CommentFeed
                  comments={desk.comments}
                  emptyHint={
                    showIngest
                      ? "Bình luận chỉ về khi Bộ thu bình luận đang chạy — xem khung “Bộ thu bình luận”."
                      : undefined
                  }
                />
              </div>
            </Card>
          </div>
        </main>
      )}
    </div>
  );
}
