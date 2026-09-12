"""Signal coverage: which conclusions a session's data can honestly support.

"Can LiveLift measure ANY sales video?" — the honest answer is a MATRIX, not a
yes. Each capability needs specific signals; when a signal is missing the
capability degrades or disappears, and the system must say so instead of
quietly producing weaker numbers. This module is that statement, computed from
the data itself, in Vietnamese, shown wherever results are shown.

Signals:
  schedule    pre-registered randomized block plan   (only our own sessions)
  ticks       viewer telemetry over time             (live API / simulator)
  comments    chat messages, PII-scrubbed            (any source incl. VODs)
  clicks      VALID self-hosted redirect hits        (only links we serve)
  orders      order records                          (manual/platform import)
  reactions   paid/visible audience events           (Super Chat/gift/sticker/
              membership from YouTube chat replay; like has NO source today)

``reactions`` is graded per SOURCE, not per wish: a YouTube chat replay only
carries Super Chat/sticker/membership/gift events IF the stream had any
(measured 11/09/2026 on the 11-replay live-fire corpus: 0 Super Chat, 11 paid
events total — 7 memberships + 4 gift purchases — and 8 of 11 streams had
none); hearts/likes are never in the replay; the live YouTube ingest does not
pump reactions yet; the TikTok source is not operational. Each of those
absences is DECLARED with its reason — the tile shows THIẾU, never a fake 0.

``clicks`` means VALID clicks, the pre-registered primary numerator
(PREREGISTRATION §4.1: a click counts only when
``core.click_validity.classify_click`` left it ``is_valid``). Grading the
signal on the RAW row count made the matrix announce "clicks: ok — 93 lượt
nhấp" and "thí nghiệm nhân quả: ok — đủ tín hiệu" for a session whose report
showed ``clicks: 0`` in every block and ``diff_in_means: null`` — all 93 hits
were flagged bot traffic (measured 11/09/2026,
``docs/benchmarks/kiem-chung-van-hanh.md`` §2.4a). Two screens, two truths,
no explanation. Hence ``n_clicks_valid`` AND ``n_clicks_raw``: the matrix
grades on the same quantity the analysis uses, and carries the raw total
beside it as a LABELLED secondary (``SignalState.secondary``) — §4.1 requires
raw clicks to be reported alongside, never instead.

``ticks`` means VIEWER telemetry, so a tick row only counts when it actually
carries a viewer number. A replay analysis writes one tick per 30 s to carry
the *comment tempo* and fills ``viewers`` with a placeholder 0.0 (YouTube does
not expose concurrent viewers retroactively —
``ingest.youtube_replay.synth_ticks_from_comments``). Counting those rows as
telemetry made the matrix announce "nhịp phiên (người xem theo thời gian): ok"
for a session that has no viewer number at all — measured on the live-fire of
10/09/2026. Hence ``n_ticks_with_viewers``: it is required, not defaulted, so
every caller has to say what it actually measured.

Capability ladder (each row = what unlocks it):
  radar ý định           <- comments
  nhịp phiên             <- ticks
  tỷ lệ nhấp (CTR)       <- clicks + ticks (shared support rule)
  THÍ NGHIỆM nhân quả    <- schedule + clicks + ticks
  đối soát doanh thu     <- orders

Pure functions — no I/O.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["ok", "degraded", "missing"]


@dataclass(frozen=True)
class SignalState:
    name: str
    status: Status
    detail: str  # Vietnamese, user-facing
    secondary: str | None = None
    """A second, LABELLED number shown beside ``detail`` — never instead of it.

    Today only ``clicks`` uses it, to carry the raw click total next to the
    valid one (PREREGISTRATION §4.1 makes raw clicks a mandatory companion
    series). The label says which quantity it is, so a reader can never
    mistake the bigger number for the one the analysis ran on.
    """


@dataclass(frozen=True)
class Capability:
    name: str
    status: Status
    reason: str  # Vietnamese: what it means / what is missing


@dataclass(frozen=True)
class SignalCoverage:
    signals: tuple[SignalState, ...]
    capabilities: tuple[Capability, ...]

    def to_dict(self) -> dict:
        return {
            "signals": [vars(s) for s in self.signals],
            "capabilities": [vars(c) for c in self.capabilities],
        }


def assess(
    *,
    has_schedule: bool,
    n_ticks: int,
    n_ticks_with_viewers: int,
    tick_coverage_share: float,  # share of the live window covered by telemetry
    n_comments: int,
    n_clicks_valid: int,
    n_clicks_raw: int,
    n_orders: int,
    n_reactions: int,
    platform: str | None = None,
    analysis_only: bool = False,
) -> SignalCoverage:
    """Grade every signal and derive the capability ladder.

    ``n_ticks`` counts stored tick rows; ``n_ticks_with_viewers`` counts the
    subset that carries a real concurrent-viewer number. They differ on replay
    analyses, where every row is comment tempo with a placeholder viewer count
    — such a session has NO viewer telemetry and must be graded that way.

    ``n_clicks_valid`` / ``n_clicks_raw`` are the same split, and required for
    the same reason: the capability ladder must be graded on the quantity the
    ANALYSIS uses (valid clicks, PREREGISTRATION §4.1), while the raw total is
    still shown as a labelled secondary. A caller that can only supply one
    number has not decided which one it means.

    ``n_reactions`` counts stored reaction events (Super Chat/gift/sticker/
    membership/like). It is required, not defaulted, for the same reason as
    ``n_ticks_with_viewers``: every caller has to say what it actually
    measured. ``platform`` picks the honest per-source reason when the count
    is zero — a replay with no paid events, a live ingest that does not pump
    them yet, and a dead TikTok source are three different truths.
    """
    signals: list[SignalState] = []

    if has_schedule:
        signals.append(SignalState("schedule", "ok", "lịch gán ngẫu nhiên đã lưu trước phiên"))
    elif analysis_only:
        signals.append(
            SignalState(
                "schedule",
                "missing",
                "video ngoài — không có ngẫu nhiên hóa (không thể can thiệp ngược thời gian)",
            )
        )
    else:
        signals.append(SignalState("schedule", "missing", "chưa sinh lịch gán"))

    viewer_share = (n_ticks_with_viewers / n_ticks) if n_ticks else 0.0
    # Both factors have to hold: telemetry must span the session AND the rows
    # must actually contain a viewer number.
    effective_coverage = tick_coverage_share * viewer_share
    if n_ticks == 0:
        signals.append(SignalState("ticks", "missing", "không có dữ liệu người xem theo thời gian"))
    elif n_ticks_with_viewers == 0:
        signals.append(
            SignalState(
                "ticks",
                "missing",
                f"{n_ticks} điểm đo chỉ có NHỊP BÌNH LUẬN, không điểm nào có số người xem — "
                "video đã kết thúc không còn lộ số người xem đồng thời; "
                "số 0 trong cột người xem là chỗ trống, KHÔNG phải phép đo",
            )
        )
    elif effective_coverage < 0.8:
        detail = (
            f"telemetry chỉ phủ {tick_coverage_share:.0%} thời gian phát — "
            "các khoảng trống bị loại khỏi phân tích"
        )
        if viewer_share < 1.0:
            detail = (
                f"chỉ {n_ticks_with_viewers}/{n_ticks} điểm đo có số người xem "
                f"(phủ {tick_coverage_share:.0%} thời gian phát) — "
                "các khoảng trống bị loại khỏi phân tích"
            )
        signals.append(SignalState("ticks", "degraded", detail))
    else:
        signals.append(
            SignalState(
                "ticks",
                "ok",
                f"{n_ticks_with_viewers} điểm đo có người xem, phủ {tick_coverage_share:.0%}",
            )
        )

    signals.append(
        SignalState(
            "comments",
            "ok" if n_comments > 0 else "missing",
            f"{n_comments} bình luận (đã lọc PII)" if n_comments else "không có bình luận",
        )
    )
    signals.append(_clicks_state(n_clicks_valid, n_clicks_raw))
    signals.append(
        SignalState(
            "orders",
            "ok" if n_orders > 0 else "missing",
            f"{n_orders} đơn ghi nhận"
            if n_orders
            else "chưa ghi nhận đơn — không đối soát được doanh thu",
        )
    )
    signals.append(_reactions_state(n_reactions, platform, analysis_only))

    by = {s.name: s for s in signals}
    caps: list[Capability] = []

    def cap(name: str, needs: list[str], extra_reason: str = "") -> None:
        missing = [n for n in needs if by[n].status == "missing"]
        degraded = [n for n in needs if by[n].status == "degraded"]
        if missing:
            reason = "thiếu " + ", ".join(missing) + (f" — {extra_reason}" if extra_reason else "")
            caps.append(Capability(name, "missing", reason))
        elif degraded:
            caps.append(Capability(name, "degraded", "tín hiệu suy giảm: " + ", ".join(degraded)))
        else:
            caps.append(Capability(name, "ok", "đủ tín hiệu"))

    cap("radar ý định bình luận", ["comments"])
    cap("nhịp phiên (người xem theo thời gian)", ["ticks"])
    cap(
        "tỷ lệ nhấp sản phẩm",
        ["clicks", "ticks"],
        "cần link đo tự phục vụ VÀ telemetry người xem trên cùng khoảng thời gian",
    )
    cap(
        "thí nghiệm nhân quả (BẬT/TẮT)",
        ["schedule", "clicks", "ticks"],
        "chỉ khả thi trên phiên do mình vận hành",
    )
    cap("đối soát doanh thu", ["orders"])

    return SignalCoverage(signals=tuple(signals), capabilities=tuple(caps))


MAX_INVALID_SHARE = 0.5
"""Above this share of flagged clicks the signal is DEGRADED, not ok.

Not a filtering rule — nothing is ever dropped (flag-don't-drop, §4.1). It is
a statement about what is left: when most of the traffic on a link is robot
traffic, the handful of surviving clicks is a thin numerator and the reader
should be told before they read an effect off it.
"""


def _clicks_state(n_valid: int, n_raw: int) -> SignalState:
    """Grade clicks on the PRE-REGISTERED primary definition (§4.1).

    ``n_valid`` is the only number the outcome is built from, so it is the
    only number that may drive the status — a matrix that says "ok" on raw
    hits promises an experiment the report then cannot deliver. ``n_raw`` is
    never hidden: it rides along in ``secondary`` with its own label, because
    §4.1 requires the raw series to be reported next to the valid one.
    """
    n_invalid = max(0, n_raw - n_valid)
    secondary = (
        f"số thô: {n_raw} lượt nhấp đã ghi, trong đó {n_invalid} bị gắn cờ KHÔNG hợp lệ "
        "(bot/prefetch/bấm dồn — GIVT-lite). Đây là số phụ bắt buộc báo cáo kèm "
        "(tiền đăng ký §4.1), KHÔNG phải tử số của biến kết quả chính"
        if n_raw
        else None
    )
    if n_raw == 0:
        return SignalState(
            "clicks", "missing", "không có link đo — nhấp sản phẩm không quan sát được"
        )
    if n_valid == 0:
        return SignalState(
            "clicks",
            "missing",
            f"0 lượt nhấp HỢP LỆ trên {n_raw} lượt đã ghi — bộ lọc GIVT-lite gắn cờ toàn bộ "
            "(tiền đăng ký §4.1), nên biến kết quả chính không có tử số nào. "
            "Link đo đang nhận traffic tự động, không phải người xem",
            secondary,
        )
    invalid_share = n_invalid / n_raw
    if invalid_share > MAX_INVALID_SHARE:
        return SignalState(
            "clicks",
            "degraded",
            f"{n_valid} lượt nhấp HỢP LỆ trên {n_raw} lượt đã ghi — "
            f"{invalid_share:.0%} bị gắn cờ không hợp lệ, phần còn lại là một tử số mỏng",
            secondary,
        )
    return SignalState(
        "clicks",
        "ok",
        f"{n_valid} lượt nhấp HỢP LỆ qua link đo (đúng con số biến kết quả chính dùng)",
        secondary,
    )


def _reactions_state(n_reactions: int, platform: str | None, analysis_only: bool) -> SignalState:
    """Grade the reactions signal honestly PER SOURCE.

    When events exist they are counted; when none exist the reason depends on
    which source this session ran on — the number 0 alone would hide whether
    the audience sent nothing or the pipeline cannot see it.
    """
    if n_reactions > 0:
        return SignalState(
            "reactions",
            "ok",
            f"{n_reactions} sự kiện Super Chat/quà/hội viên "
            "(tim/like KHÔNG nằm trong nguồn chat — vắng mặt là thiếu nguồn, không phải 0)",
        )
    if platform == "replay" or analysis_only:
        detail = (
            "chat replay của buổi này không chứa sự kiện Super Chat/quà/hội viên nào — "
            "và YouTube không lưu tim/like vào chat replay; ô trống là THIẾU nguồn, "
            "không phải phép đo bằng 0"
        )
    elif platform == "youtube":
        detail = (
            "đường thu YouTube trực tiếp chưa bơm sự kiện tim/quà/Super Chat "
            "(parser đã có, vòng ingest chưa nối) — hiển thị THIẾU, không hiển thị 0"
        )
    elif platform == "tiktok":
        detail = (
            "nguồn TikTok đang không hoạt động — chưa thu được tim/quà; "
            "schema dùng chung đã sẵn sàng khi nguồn hồi phục"
        )
    else:
        detail = "chưa có nguồn sự kiện tim/quà/Super Chat cho phiên này"
    return SignalState("reactions", "missing", detail)
