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
  clicks      self-hosted redirect hits              (only links we serve)
  orders      order records                          (manual/platform import)

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
    tick_coverage_share: float,  # share of the live window covered by telemetry
    n_comments: int,
    n_clicks: int,
    n_orders: int,
    analysis_only: bool = False,
) -> SignalCoverage:
    """Grade every signal and derive the capability ladder."""
    signals: list[SignalState] = []

    if has_schedule:
        signals.append(SignalState("schedule", "ok", "lịch gán ngẫu nhiên đã lưu trước phiên"))
    elif analysis_only:
        signals.append(
            SignalState(
                "schedule", "missing",
                "video ngoài — không có ngẫu nhiên hóa (không thể can thiệp ngược thời gian)",
            )
        )
    else:
        signals.append(SignalState("schedule", "missing", "chưa sinh lịch gán"))

    if n_ticks == 0:
        signals.append(SignalState("ticks", "missing", "không có dữ liệu người xem theo thời gian"))
    elif tick_coverage_share < 0.8:
        signals.append(
            SignalState(
                "ticks", "degraded",
                f"telemetry chỉ phủ {tick_coverage_share:.0%} thời gian phát — "
                "các khoảng trống bị loại khỏi phân tích",
            )
        )
    else:
        signals.append(
            SignalState("ticks", "ok", f"{n_ticks} điểm đo, phủ {tick_coverage_share:.0%}")
        )

    signals.append(
        SignalState("comments", "ok" if n_comments > 0 else "missing",
                    f"{n_comments} bình luận (đã lọc PII)" if n_comments else "không có bình luận")
    )
    signals.append(
        SignalState("clicks", "ok" if n_clicks > 0 else "missing",
                    f"{n_clicks} lượt nhấp qua link đo" if n_clicks
                    else "không có link đo — nhấp sản phẩm không quan sát được")
    )
    signals.append(
        SignalState("orders", "ok" if n_orders > 0 else "missing",
                    f"{n_orders} đơn ghi nhận" if n_orders
                    else "chưa ghi nhận đơn — không đối soát được doanh thu")
    )

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
    cap("tỷ lệ nhấp sản phẩm", ["clicks", "ticks"],
        "cần link đo tự phục vụ VÀ telemetry người xem trên cùng khoảng thời gian")
    cap("thí nghiệm nhân quả (BẬT/TẮT)", ["schedule", "clicks", "ticks"],
        "chỉ khả thi trên phiên do mình vận hành")
    cap("đối soát doanh thu", ["orders"])

    return SignalCoverage(signals=tuple(signals), capabilities=tuple(caps))
