"""Post-session data-quality checks (plan §8.3) — pure functions over rows.

Runs at T+30' after every session. ANY failing check pages the team. Checks
never mutate data: a failed block/session gets flagged for exclusion with a
reason, never edited (HARNESS.md §3).

Gói Q5 adds the first two SRM-style checks to the panel (8 checks now):
``assignment_integrity`` (the persisted schedule vs the frame that feeds the
estimator) and ``telemetry_delivery`` (an exact binomial on tick delivery
against the schedule's ON/OFF TIME share). Read the invariant comment above
:func:`check_assignment_integrity` before adding a third: SRM is only ever run
on quantities fixed before, or independent of, the arm — never on viewers,
comments or clicks.
"""

from __future__ import annotations

import random
from bisect import bisect_right
from collections.abc import Iterable
from dataclasses import dataclass

from scipy.stats import binomtest

from livelift.ingest.pii import scrub


@dataclass(frozen=True)
class CheckResult:
    name: str
    passed: bool
    detail: str


# ---------------------------------------------------------------------------
# Compliance VIEW over the append-only event tables (gói Q3, migration 0006)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BlockCompliance:
    """Compliance of ONE measurement block, derived — never stored."""

    block_idx: int
    assignment: str
    exposed: bool
    """A system ('model') pin was recorded inside this block."""
    n_model_pins: int
    n_human_pins: int

    @property
    def compliant(self) -> bool:
        """ON blocks must be exposed; OFF blocks must NOT be.

        The OFF half matters as much as the ON half: a system pin inside an OFF
        block contaminates the control arm, and a first-stage that only counted
        ON blocks would report it as perfect compliance.
        """
        return self.exposed if self.assignment == "ON" else not self.exposed


@dataclass(frozen=True)
class ComplianceView:
    """Derived compliance of a session. Pure function of the two event tables.

    This is a VIEW, not a stored number: nothing here is ever written back into
    ``experiment_block``. ITT is unchanged — the estimand still keys on
    ``assignment`` — and this only feeds the LATE/first-stage reporting and QC
    (PREREGISTRATION §5(d)).
    """

    n_on: int
    n_off: int
    n_on_exposed: int
    n_off_exposed: int
    """OFF blocks that saw a system pin — contamination of the control arm."""
    compliance_rate: float | None
    """Share of ON blocks that were actually exposed; None when no ON block."""
    off_contamination_rate: float | None
    n_unattributed_exposures: int
    """Exposure rows with no block_idx (override outside every block) or whose
    block_idx matches no assignment row. Reported, never silently dropped."""
    per_block: tuple[BlockCompliance, ...]


def derive_compliance(
    assignment_events: list[dict],
    exposure_events: list[dict],
) -> ComplianceView:
    """Compliance per block from assignment_event × exposure_event.

    Separating "assigned" from "exposed" is the point of the split (PlanOut,
    Bakshy/Eckles/Bernstein WWW 2014; Fabijan et al. KDD 2019): the assignment
    rows say what the design demanded, the exposure rows say what the desk did,
    and compliance is the JOIN — no third table can be edited to make the two
    agree.

    Blocks are matched on ``block_idx``. Washout rows (``assignment`` None) are
    excluded: nothing is assigned in a washout, so "compliance" is undefined
    there. Only ``source='model'`` exposures count as system exposure — a human
    override pinning the same product is not the system running the policy
    (that is exactly the non-compliance the LATE estimator instruments for).

    Callers pass ONE design draw's assignment rows (filter by ``design_hash``);
    mixing two draws of the same session would double-count blocks.
    """
    blocks: dict[int, dict] = {}
    for row in assignment_events:
        assignment = row.get("assignment")
        if assignment is None:  # washout — nothing assigned, nothing to comply with
            continue
        blocks[int(row["block_idx"])] = {"assignment": assignment, "model": 0, "human": 0}

    unattributed = 0
    for ev in exposure_events:
        if ev.get("event_type") != "pin":
            continue
        idx = ev.get("block_idx")
        entry = blocks.get(int(idx)) if idx is not None else None
        if entry is None:
            unattributed += 1
            continue
        if ev.get("source") == "model":
            entry["model"] += 1
        else:
            entry["human"] += 1

    per_block = tuple(
        BlockCompliance(
            block_idx=idx,
            assignment=entry["assignment"],
            exposed=entry["model"] > 0,
            n_model_pins=entry["model"],
            n_human_pins=entry["human"],
        )
        for idx, entry in sorted(blocks.items())
    )
    on = [b for b in per_block if b.assignment == "ON"]
    off = [b for b in per_block if b.assignment == "OFF"]
    n_on_exposed = sum(1 for b in on if b.exposed)
    n_off_exposed = sum(1 for b in off if b.exposed)
    return ComplianceView(
        n_on=len(on),
        n_off=len(off),
        n_on_exposed=n_on_exposed,
        n_off_exposed=n_off_exposed,
        compliance_rate=(n_on_exposed / len(on)) if on else None,
        off_contamination_rate=(n_off_exposed / len(off)) if off else None,
        n_unattributed_exposures=unattributed,
        per_block=per_block,
    )


def check_block_integrity(scheduled_blocks: list[dict], recorded_blocks: list[dict]) -> CheckResult:
    """Recorded blocks must match the schedule generated BEFORE broadcast.

    Two distinct failures, reported differently because they mean different
    things:
    (a) no schedule was persisted at all -> there is no audit trail, so the
        randomization cannot be verified by anyone (including a judge). This
        must never read as a pass.
    (b) recorded blocks disagree with the schedule -> data loss or tampering.
    """
    if not scheduled_blocks:
        return CheckResult(
            "block_integrity",
            False,
            "KHÔNG có lịch gán lưu trước phiên (design['blocks'] rỗng) — "
            "không thể đối chiếu, mất dấu vết kiểm chứng ngẫu nhiên hóa",
        )
    if len(scheduled_blocks) != len(recorded_blocks):
        return CheckResult(
            "block_integrity",
            False,
            f"số khối lệch: ghi nhận {len(recorded_blocks)}, lịch gán {len(scheduled_blocks)}",
        )
    mismatches = []
    for sched, rec in zip(scheduled_blocks, recorded_blocks, strict=True):
        for key in ("block_index", "assignment", "is_washout"):
            if sched.get(key) != rec.get(key):
                mismatches.append(f"khối {sched.get('block_index')}: {key}")
    return CheckResult(
        "block_integrity",
        not mismatches,
        f"{len(recorded_blocks)} khối khớp lịch gán"
        if not mismatches
        else f"lệch so với lịch gán: {mismatches[:5]}",
    )


def check_assignment_balance(blocks: list[dict], lo: float = 0.4, hi: float = 0.6) -> CheckResult:
    meas = [b for b in blocks if not b.get("is_washout")]
    if not meas:
        return CheckResult("assignment_balance", False, "không có khối đo nào")
    share_on = sum(1 for b in meas if b.get("assignment") == "ON") / len(meas)
    return CheckResult("assignment_balance", lo <= share_on <= hi, f"tỷ lệ BẬT = {share_on:.2f}")


def check_event_continuity(
    tick_timestamps_s: list[float], session_duration_s: float, max_gap_s: float = 60.0
) -> CheckResult:
    """No gap longer than ``max_gap_s`` in the tick stream."""
    if not tick_timestamps_s:
        return CheckResult(
            "event_continuity",
            False,
            "không có dữ liệu người xem — ingest chưa chạy hoặc chưa gửi tick nào",
        )
    ts = sorted(tick_timestamps_s)
    gaps = [b - a for a, b in zip(ts, ts[1:], strict=False)]
    gaps.append(ts[0] - 0.0)
    gaps.append(session_duration_s - ts[-1])
    worst = max(gaps) if gaps else 0.0
    return CheckResult(
        "event_continuity", worst <= max_gap_s, f"khoảng trống lớn nhất = {worst:.0f}s"
    )


ALLOWED_OVERRIDE_REASONS = ("hết hàng", "sai giá", "sự cố kỹ thuật")


def check_intervention_log(interventions: list[dict]) -> CheckResult:
    """Every executed action must be auditable — but the rule differs by source.

    - ``source="model"``: the assignment probability MUST be logged. This is the
      scientific core: without a propensity the action cannot enter any
      off-policy or heterogeneous-effect estimate.
    - ``source="human"``: an operator override is not randomized, so it has NO
      propensity by definition. Requiring one made every legitimate override
      fail the gate (incident 27/08) — a quality gate that cries wolf gets
      ignored. What an override must carry instead is one of the three allowed
      reasons, so non-compliance stays measurable.
    - Every executed row, whatever the source, must name the block it ran in.
    """
    problems: list[str] = []
    for i in interventions:
        if not i.get("executed"):
            continue  # skipped/proposed rows may be partial
        action_id = i.get("action_id", "?")
        source = i.get("source") or ""
        if i.get("block_id") in (None, ""):
            problems.append(f"{action_id}: thiếu block_id")
        if not source:
            problems.append(f"{action_id}: thiếu source")
        elif source == "model" and i.get("inner_propensity") is None:
            problems.append(f"{action_id}: hành động của mô hình thiếu inner_propensity")
        elif source == "human":
            reason = i.get("override_reason")
            if not reason:
                problems.append(f"{action_id}: can thiệp tay thiếu override_reason")
            elif reason not in ALLOWED_OVERRIDE_REASONS:
                problems.append(f"{action_id}: lý do can thiệp không hợp lệ ({reason!r})")
    return CheckResult(
        "intervention_log_complete",
        not problems,
        "đầy đủ" if not problems else f"{len(problems)} vấn đề, ví dụ: {problems[:3]}",
    )


def check_pii_clean(
    scrubbed_texts: Iterable[str], sample_size: int = 50, seed: int = 7
) -> CheckResult:
    """Re-run the scrubber over a random sample of STORED comments; finding any
    phone/address/email in supposedly-scrubbed text is a hard failure."""
    texts = list(scrubbed_texts)
    rng = random.Random(seed)
    sample = rng.sample(texts, min(sample_size, len(texts))) if texts else []
    dirty = 0
    kinds: set[str] = set()
    for t in sample:
        res = scrub(t)
        hard = [m for m in res.matches if m.kind in ("phone", "email", "address", "order")]
        if hard:
            dirty += 1
            kinds |= {m.kind for m in hard}
    return CheckResult(
        "pii_clean",
        dirty == 0,
        f"quét {len(sample)} bình luận; rò rỉ: {dirty}" + (f" ({sorted(kinds)})" if kinds else ""),
    )


def check_order_reconciliation(
    db_order_total: float, platform_report_total: float, tolerance: float = 0.01
) -> CheckResult:
    if platform_report_total <= 0:
        ok = db_order_total == 0
        return CheckResult(
            "order_reconciliation",
            ok,
            "chưa ghi nhận đơn hàng nào cho phiên — chưa đối soát được doanh thu",
        )
    rel = abs(db_order_total - platform_report_total) / platform_report_total
    return CheckResult(
        "order_reconciliation",
        rel <= tolerance,
        f"CSDL={db_order_total:.0f} nền tảng={platform_report_total:.0f} lệch={rel:.1%}",
    )


# ---------------------------------------------------------------------------
# SRM đợt 1 (gói Q5) — hai kiểm tra THUẦN trên dấu vết gán và trên nhịp telemetry
# ---------------------------------------------------------------------------

SRM_ALPHA = 0.005
"""Mức ý nghĩa MỖI kiểm tra thống kê của bộ QC sau phiên.

Bộ QC chạy sau MỌI phiên, nên một α = 0.05 mỗi kiểm tra sẽ báo động giả liên
tục và bị bỏ qua sau vài tuần (đúng cơ chế của sự cố 27/08). Với họ ~10 kiểm
tra, Bonferroni cho α_họ ≈ 10 × 0.005 = 5% — ngân sách được đặt cho cả họ ngay
từ đầu để về sau thêm kiểm tra không phải chỉnh lại ngưỡng đã công bố. Hôm nay
chỉ :func:`check_telemetry_delivery` là kiểm định thống kê thật; phần còn lại
của bộ là kiểm tra tất định.
"""

SRM_INVESTIGATE = (
    "lệch = bug pipeline HOẶC sự cố telemetry, điều tra trước khi tin số "
    "(không sửa, không loại dữ liệu tự động)"
)

# QUY TẮC BẤT DI BẤT DỊCH CỦA CẢ MỤC NÀY — đọc trước khi thêm bất kỳ SRM nào:
#
# TUYỆT ĐỐI KHÔNG chạy SRM trên số người xem, bình luận, hay click. Ba đại lượng
# đó là HẬU CAN THIỆP: nếu chiến lược ghim thực sự có tác động thì nó PHẢI làm
# lệch chúng giữa hai nhánh — đó chính là điều thí nghiệm đi đo. Một "SRM" trên
# chúng sẽ gắn cờ ĐỎ đúng lúc thí nghiệm thành công, và tệ hơn, cám dỗ loại bỏ
# khối theo kết quả. SRM chỉ hợp lệ trên các đại lượng được quyết định TRƯỚC
# hoặc ĐỘC LẬP với nhánh: dấu vết gán, và nhịp giao telemetry theo đồng hồ.


def _normalize_persisted_blocks(rows: Iterable[dict]) -> list[dict]:
    """Đưa `design['blocks']` và `assignment_event` về một hình dạng chung.

    Hai nguồn lịch đã persist có tên cột khác nhau (``block_index`` /
    ``start_offset_s`` với design json; ``block_idx`` / ``block_start_s`` với
    bảng sự kiện) nhưng mang đúng cùng một nội dung. Chuẩn hóa ở một chỗ để hai
    kiểm tra dưới đây không phải biết mình đang đọc nguồn nào.

    Chỉ trả về KHỐI ĐO: washout không được gán gì (assignment None) nên không
    có "chuỗi gán" để đối chiếu và cũng không thuộc mẫu số thời gian ON/OFF.
    """
    out: list[dict] = []
    for r in rows:
        idx = r.get("block_index", r.get("block_idx"))
        assignment = r.get("assignment")
        if idx is None or assignment is None or r.get("is_washout"):
            continue
        out.append(
            {
                "block_index": int(idx),
                "assignment": assignment,
                "start_offset_s": r.get("start_offset_s", r.get("block_start_s")),
                "end_offset_s": r.get("end_offset_s", r.get("block_end_s")),
            }
        )
    return sorted(out, key=lambda r: r["block_index"])


def _sequence(blocks: list[dict]) -> list[tuple[int, str]]:
    return [(b["block_index"], b["assignment"]) for b in blocks]


def check_assignment_integrity(
    scheduled_blocks: list[dict],
    analysis_blocks: list[dict] | None,
    assignment_events: list[dict] | None = None,
) -> CheckResult:
    """Lịch ĐÃ LƯU và khối DÙNG TRONG PHÂN TÍCH phải là một.

    ``check_block_integrity`` đối chiếu ``design['blocks']`` với các dòng
    ``experiment_block`` đã ghi. Kiểm tra này nối thêm chân thứ ba, chân quan
    trọng nhất: **khung phân tích thật sự đi vào ước lượng viên**
    (``core.features.block_frame`` → ``blocks_to_dicts``). Giữa hai chân đó còn
    `rebuild_schedule`, bộ lọc washout, và thứ tự sắp xếp — mỗi chỗ đều có thể
    lệch một khối mà không bảng nào kêu.

    Nguồn lịch persist, ưu tiên theo đúng thứ tự của
    :func:`livelift.api.routes.reports._compliance`:

    1. ``assignment_event`` (gói Q3, chỉ-ghi-thêm) khi có — không ai sửa được
       để cho khớp; caller lọc sẵn theo ``design_hash`` của lượt rút đã chạy.
    2. ``design['blocks']`` — dấu vết trong session json, cho phiên tiền-Q3.

    Khi CẢ HAI cùng có, chúng cũng được đối chiếu với nhau: hai nguồn persist
    mà nói khác nhau là một lỗi riêng biệt (một lượt rút bị trộn, hoặc design
    json bị ghi đè sau khi sự kiện đã materialize), và nó phải hiện ra trước
    khi ta đi so với khung phân tích.

    LỆCH BẤT KỲ = FAIL, kèm chi tiết. Không tự sửa, không tự loại: kết quả chỉ
    là CỜ (HARNESS §3).
    """
    sched = _normalize_persisted_blocks(scheduled_blocks or [])
    events = _normalize_persisted_blocks(assignment_events or [])

    if sched and events and _sequence(sched) != _sequence(events):
        diff = [
            f"khối {a[0]}: assignment_event={a[1]} vs design={b[1]}"
            for a, b in zip(_sequence(events), _sequence(sched), strict=False)
            if a != b
        ]
        return CheckResult(
            "assignment_integrity",
            False,
            f"hai nguồn lịch đã lưu mâu thuẫn nhau ({len(events)} vs {len(sched)} khối đo)"
            + (f": {diff[:5]}" if diff else "")
            + f" — {SRM_INVESTIGATE}",
        )

    persisted = events or sched
    source = "assignment_event" if events else "design['blocks']"
    if not persisted:
        return CheckResult(
            "assignment_integrity",
            False,
            "KHÔNG có lịch gán lưu trước phiên (assignment_event và design['blocks'] "
            "đều rỗng) — không có gì để đối chiếu với khung phân tích",
        )
    if analysis_blocks is None:
        return CheckResult(
            "assignment_integrity",
            False,
            "chưa truyền khung phân tích (block_frame) — không đối chiếu được; "
            "im lặng ở đây sẽ đọc như 'khớp'",
        )

    analysis = _normalize_persisted_blocks(analysis_blocks)
    if not analysis:
        return CheckResult(
            "assignment_integrity",
            False,
            f"lịch đã lưu có {len(persisted)} khối đo nhưng khung phân tích rỗng — "
            f"{SRM_INVESTIGATE}",
        )
    if len(analysis) != len(persisted):
        return CheckResult(
            "assignment_integrity",
            False,
            f"số khối đo lệch: khung phân tích {len(analysis)}, {source} "
            f"{len(persisted)} — {SRM_INVESTIGATE}",
        )

    mismatches = [
        f"vị trí {i}: {source}=(khối {p[0]}, {p[1]}) vs phân tích=(khối {a[0]}, {a[1]})"
        for i, (p, a) in enumerate(zip(_sequence(persisted), _sequence(analysis), strict=True))
        if p != a
    ]
    if mismatches:
        return CheckResult(
            "assignment_integrity",
            False,
            f"{len(mismatches)} khối lệch giữa {source} và khung phân tích: "
            f"{mismatches[:5]} — {SRM_INVESTIGATE}",
        )
    return CheckResult(
        "assignment_integrity",
        True,
        f"{len(analysis)} khối đo: chỉ số và chuỗi gán khớp giữa {source} và khung phân tích",
    )


@dataclass(frozen=True)
class TelemetryCounts:
    """Số nhịp telemetry rơi vào khối BẬT / TẮT, kèm mẫu số thời gian."""

    n_on: int = 0
    n_off: int = 0
    on_seconds: float = 0.0
    off_seconds: float = 0.0
    n_outside: int = 0
    """Nhịp không rơi vào khối đo nào (washout, trước khối đầu, sau khối cuối).

    Báo riêng, không bao giờ nhập vào kiểm định: chúng không thuộc mẫu số
    ON/OFF, nhưng biến mất trong im lặng thì lại giấu mất một sự cố ingest."""

    def __add__(self, other: TelemetryCounts) -> TelemetryCounts:
        return TelemetryCounts(
            n_on=self.n_on + other.n_on,
            n_off=self.n_off + other.n_off,
            on_seconds=self.on_seconds + other.on_seconds,
            off_seconds=self.off_seconds + other.off_seconds,
            n_outside=self.n_outside + other.n_outside,
        )

    @property
    def n(self) -> int:
        return self.n_on + self.n_off

    @property
    def expected_on_share(self) -> float | None:
        """Tỷ lệ THỜI GIAN BẬT của lịch đã persist — kỳ vọng đúng của kiểm định.

        KHÔNG phải 0.5: khối biên được nhân đôi (quy tắc 2m, Bojinov et al.
        2023) nên tùy chuỗi gán mà thời gian BẬT lệch khỏi một nửa khá xa, và
        jitter ranh giới còn xê dịch thêm. Lấy 0.5 làm kỳ vọng sẽ biến một lịch
        hoàn toàn hợp lệ thành báo động đỏ.
        """
        total = self.on_seconds + self.off_seconds
        if total <= 0:
            return None
        return self.on_seconds / total


def telemetry_counts(
    scheduled_blocks: list[dict], tick_timestamps_s: Iterable[float]
) -> TelemetryCounts:
    """Đếm nhịp ``session_tick`` theo nhánh, dựa trên lịch ĐÃ PERSIST.

    Mỗi nhịp được quy về khối chứa mốc bắt đầu bucket của nó (đúng cách
    ``features._window_stats`` coi mốc bucket là thời điểm của nhịp). Khối đo
    không chồng lấn nên phép quy là đơn trị.
    """
    blocks = _normalize_persisted_blocks(scheduled_blocks or [])
    usable = [
        b for b in blocks if b["start_offset_s"] is not None and b["end_offset_s"] is not None
    ]
    starts = [float(b["start_offset_s"]) for b in usable]
    spans = [(float(b["end_offset_s"]) - starts[i], b["assignment"]) for i, b in enumerate(usable)]
    on_s = sum(d for d, arm in spans if arm == "ON")
    off_s = sum(d for d, arm in spans if arm != "ON")

    n_on = n_off = n_outside = 0
    for t in tick_timestamps_s:
        ts = float(t)
        i = bisect_right(starts, ts) - 1
        if i < 0 or ts >= float(usable[i]["end_offset_s"]):
            n_outside += 1
        elif usable[i]["assignment"] == "ON":
            n_on += 1
        else:
            n_off += 1
    return TelemetryCounts(
        n_on=n_on, n_off=n_off, on_seconds=on_s, off_seconds=off_s, n_outside=n_outside
    )


def check_telemetry_counts(
    counts: TelemetryCounts, alpha: float = SRM_ALPHA, scope: str = "phiên"
) -> CheckResult:
    """Kiểm định nhị thức CHÍNH XÁC trên số nhịp telemetry BẬT vs TẮT.

    Đây là SRM đúng nghĩa của Fabijan et al. (KDD 2019) áp cho thiết kế này:
    tỷ lệ *đơn vị đo* rơi vào hai nhánh phải khớp tỷ lệ mà THIẾT KẾ quy định.
    Đơn vị đo ở đây là nhịp ``session_tick`` — nhịp 30 giây do ĐỒNG HỒ sinh ra,
    không do người xem sinh ra — nên số nhịp trong một khối được quyết định bởi
    độ dài khối và bởi đường ống ingest, chứ không bởi nhánh. Lệch có ý nghĩa
    thống kê ⇒ đường ống mất dữ liệu (hoặc mất theo nhánh), KHÔNG phải "hiệu
    ứng can thiệp".

    Kỳ vọng lấy từ **tỷ lệ thời gian BẬT/TẮT của lịch đã persist**, không phải
    0.5 — xem :attr:`TelemetryCounts.expected_on_share`.

    Kiểm định hai phía, chính xác (``scipy.stats.binomtest``, không xấp xỉ
    chuẩn): với vài trăm nhịp mỗi phiên, xấp xỉ chuẩn ở đuôi α = 0.005 không
    đáng tin.

    Hạn chế đã đo, ghi thẳng ra để không ai đọc quá lời: một phiên 90 phút chỉ
    có ~180 nhịp, nên ở mức mỗi-phiên kiểm định này chỉ bắt được sự cố THÔ (mất
    cỡ một nửa số nhịp của một nhánh). Muốn nhạy với mất mát vài phần trăm phải
    GỘP cả chuỗi phiên: cộng các :class:`TelemetryCounts` rồi gọi lại hàm này
    với ``scope="chuỗi phiên"``. Tính bảo thủ này là cố ý — nhịp telemetry gần
    như tất định, còn phương sai nhị thức thì rộng hơn thế nhiều.

    Cảnh báo cho tương lai: kết luận "độc lập với nhánh" chỉ đúng chừng nào bộ
    ghi tick còn là nhịp đồng hồ. Nếu có ngày tick chỉ được ghi khi có người
    xem, nó thành đại lượng hậu can thiệp và kiểm tra này phải xét lại.
    """
    # Thứ tự chẩn đoán: thiếu MẪU SỐ (lịch không có thời lượng khối) là một lỗi
    # khác hẳn thiếu TỬ SỐ (không nhịp nào rơi vào khối) — báo nhầm cái này
    # thành cái kia sẽ dẫn người điều tra đi sai hướng ngay từ dòng đầu.
    expected = counts.expected_on_share
    if expected is None:
        return CheckResult(
            "telemetry_delivery",
            False,
            f"lịch đã lưu không có thời lượng khối đo ({scope}) — không tính được tỷ lệ "
            f"thời gian BẬT/TẮT làm kỳ vọng; nhịp ngoài khối: {counts.n_outside}",
        )
    if counts.n == 0:
        return CheckResult(
            "telemetry_delivery",
            False,
            f"không nhịp session_tick nào rơi vào khối đo ({scope}); "
            f"ngoài khối: {counts.n_outside} — {SRM_INVESTIGATE}",
        )
    res = binomtest(counts.n_on, counts.n, expected, alternative="two-sided")
    observed = counts.n_on / counts.n
    passed = bool(res.pvalue >= alpha)
    detail = (
        f"{scope}: nhịp BẬT {counts.n_on}/{counts.n} = {observed:.3f}, "
        f"kỳ vọng theo thời gian lịch {expected:.3f}, p = {res.pvalue:.4f} "
        f"(α = {alpha:g}); ngoài khối đo: {counts.n_outside}"
    )
    if not passed:
        detail += f" — {SRM_INVESTIGATE}"
    return CheckResult("telemetry_delivery", passed, detail)


def check_telemetry_delivery(
    scheduled_blocks: list[dict],
    tick_timestamps_s: Iterable[float],
    alpha: float = SRM_ALPHA,
) -> CheckResult:
    """SRM nhịp telemetry cho MỘT phiên (xem :func:`check_telemetry_counts`)."""
    return check_telemetry_counts(telemetry_counts(scheduled_blocks, tick_timestamps_s), alpha)


def run_all(
    scheduled_blocks: list[dict],
    recorded_blocks: list[dict],
    tick_timestamps_s: list[float],
    session_duration_s: float,
    interventions: list[dict],
    scrubbed_texts: Iterable[str],
    db_order_total: float,
    platform_report_total: float,
    analysis_blocks: list[dict] | None = None,
    assignment_events: list[dict] | None = None,
    srm_alpha: float = SRM_ALPHA,
) -> list[CheckResult]:
    """Bộ kiểm tra sau phiên — 8 mục (6 mục gốc + 2 mục SRM đợt 1, gói Q5).

    ``analysis_blocks`` là ``blocks_to_dicts(block_frame(...))`` của chính phiên
    đó; ``assignment_events`` là các dòng ``assignment_event`` đã lọc theo
    ``design_hash`` của lượt rút đã chạy. Cả hai để None chỉ hợp lệ cho caller
    thật sự không có dữ liệu đó — và khi đó ``assignment_integrity`` FAIL với
    lý do rõ ràng, chứ không im lặng đọc thành "khớp".
    """
    return [
        check_block_integrity(scheduled_blocks, recorded_blocks),
        check_assignment_balance(recorded_blocks),
        check_assignment_integrity(scheduled_blocks, analysis_blocks, assignment_events),
        check_event_continuity(tick_timestamps_s, session_duration_s),
        check_telemetry_delivery(scheduled_blocks, tick_timestamps_s, srm_alpha),
        check_intervention_log(interventions),
        check_pii_clean(scrubbed_texts),
        check_order_reconciliation(db_order_total, platform_report_total),
    ]
