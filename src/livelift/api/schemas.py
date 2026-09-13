"""Pydantic v2 request/response models for the LiveLift API.

Two hard rules are enforced STRUCTURALLY here, not by convention:

- **E2-04 number-source rule**: any displayed number carries ``source``;
  numbers from a forecast model (``source='forecast'``) must NEVER carry a
  confidence interval — only ``source='experiment'`` numbers may. The
  :class:`ActionCard` validator rejects forecast cards with CI fields.
- **Blinding (L6)**: the host-facing state is its own model
  (:class:`HostState`, ``extra='forbid'``) that simply has no field for block
  boundaries, assignment, or time-remaining-in-block — leaking them through
  the host endpoint is a type error, not a code-review catch.

User-facing strings are Vietnamese; code and docs are English.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Manual override reasons allowed during a live session (hard project rule 5).
ALLOWED_OVERRIDE_REASONS: frozenset[str] = frozenset({"hết hàng", "sai giá", "sự cố kỹ thuật"})

OverrideReason = Literal["hết hàng", "sai giá", "sự cố kỹ thuật"]

Platform = Literal["youtube", "facebook", "tiktok", "replay", "sim"]
SessionMode = Literal["auto", "suggest"]
SessionStatus = Literal["planned", "scheduled", "live", "ended", "cancelled"]
"""Vòng đời phiên. ``cancelled`` = ĐÓNG mà KHÔNG phát sóng (migration 0008).

Nó tồn tại vì ``ended`` có nghĩa "buổi phát đã diễn ra và đã kết thúc". Một
phiên quan sát gõ tay, hay một phiên tạo nhầm, chưa từng lên sóng: gọi nó là
``ended`` sẽ nói dối đúng cái trường mà bộ lọc mẫu phân tích đọc. Trước
migration 0008 những phiên đó không có trạng thái cuối nào và kẹt ở
``planned`` vĩnh viễn (kiem-chung-van-hanh.md §3.3)."""


# ---------------------------------------------------------------------------
# Products & shortlinks
# ---------------------------------------------------------------------------


class ProductIn(BaseModel):
    product_id: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1)
    category: str | None = None
    cost: float = Field(ge=0)
    price: float = Field(ge=0)
    stock: int = Field(ge=0)


class ProductOut(ProductIn):
    margin: float
    created_at: datetime


class ShortlinkIn(BaseModel):
    product_id: str
    session_id: str | None = None
    target_url: str

    @field_validator("target_url")
    @classmethod
    def _http_only(cls, v: str) -> str:
        if not v.startswith(("http://", "https://")):
            raise ValueError("target_url phải bắt đầu bằng http:// hoặc https://")
        return v


class ShortlinkOut(BaseModel):
    code: str
    product_id: str
    session_id: str | None = None
    target_url: str
    created_at: datetime


# ---------------------------------------------------------------------------
# Sessions & schedule
# ---------------------------------------------------------------------------


class SessionCreate(BaseModel):
    platform: Platform
    title: str | None = None
    mode: SessionMode = "auto"
    planned_duration_min: int = Field(ge=5, le=480)
    host_id: str | None = None
    dry_run: bool = False
    """Phiên CHẠY THỬ / tập dượt — bị loại khỏi mẫu phân tích gộp.

    Khai báo ở ĐÂY, lúc tạo phiên, là điều kiện làm nó hợp lệ về liêm chính:
    quyết định trước khi bốc lịch gán và trước khi thấy bất kỳ con số nào.
    Không endpoint nào sửa được cờ này sau đó — một nút "loại phiên này khỏi
    kết quả" bấm được sau khi đọc kết quả không phải quy tắc tiền đăng ký, nó
    là chọn lọc kết quả. Quy tắc đầy đủ: PREREGISTRATION §8.2.

    CỐ Ý KHÔNG có trường ``is_demo`` ở đây (gói DEMO-THẬT): dữ liệu MẪU chỉ
    sinh ra từ máy sinh demo phía server (``/demo/seed``,
    ``scripts/seed_demo_vang.py``) — không đường nào qua ``POST /sessions``
    tạo được một phiên mang nhãn demo, nên cũng không ai dán nhầm (hay dán
    gian) nhãn "dữ liệu mẫu" lên một phiên thật. Muốn tập dượt trên đường ống
    thật thì dùng ``dry_run``."""


class SessionOut(BaseModel):
    session_id: str
    platform: Platform
    title: str | None = None
    mode: SessionMode
    status: SessionStatus
    planned_duration_min: int
    host_id: str | None = None
    start_ts: datetime | None = None
    end_ts: datetime | None = None
    created_at: datetime
    dry_run: bool = False
    """Xem :class:`SessionCreate`. Mặc định False cho phiên tạo trước gói
    C-NHẤT-QUÁN — chúng là phiên thật, và mặc định phải là "tính vào kết quả"
    để không có phiên nào biến mất âm thầm khỏi mẫu."""
    is_demo: bool = False
    """DỮ LIỆU MẪU (gói DEMO-THẬT): phiên máy sinh ra để xem thử/tập demo —
    không có buổi phát nào từng diễn ra sau con số của nó. Khác hẳn
    ``dry_run`` (phiên THẬT chạy thử): ``is_demo`` trả lời "dữ liệu này có
    THẬT không?", ``dry_run`` trả lời "phiên thật này có được TÍNH không?".

    Chỉ máy sinh demo phía server đặt được (``/demo/seed``,
    ``scripts/seed_demo_vang.py``); bất biến sau khi tạo
    (``store._SESSION_WRITE_ONCE``). Phiên demo bị loại khỏi MỌI đầu ra khoa
    học thật (``/experiment/summary`` mặc định, export nhãn NLP) và UI phải
    vẽ nhãn DEMO từ cờ này ở mọi nơi phiên xuất hiện. PREREGISTRATION §8.2."""


class SessionDetail(SessionOut):
    design: dict[str, Any] | None = None


class ScheduleRequest(BaseModel):
    block_min: int = Field(default=5, ge=1, le=60)
    washout_min: int = Field(default=0, ge=0, le=10)
    jitter_s: int = Field(default=30, ge=0, le=120)
    seed: int | None = Field(default=None, ge=0)


class BlockOut(BaseModel):
    block_id: str
    block_index: int
    phase: Literal["early", "mid", "late"]
    assignment: Literal["ON", "OFF"] | None = None
    propensity: float | None = None
    is_washout: bool
    start_offset_s: int
    end_offset_s: int
    start_ts: datetime | None = None
    end_ts: datetime | None = None


class ScheduleOut(BaseModel):
    session_id: str
    status: SessionStatus
    seed: int
    n_redraws: int
    n_on: int
    n_off: int
    blocks: list[BlockOut]
    design_hash: str
    """SHA-256 over (DesignParams, seed) — the design commitment, published
    BEFORE broadcast (gói Q3). Recomputable from `live_session.design`, so a
    reader can verify the design that ran is the design that was announced."""
    realized_min_per_arm_per_phase: int = 0
    """Balance guarantee the layout could actually deliver (see `warning`)."""
    realized_transition_pairs: int = 0
    """Same-arm adjacent-pair guarantee the chain could deliver — 0 means the
    transition constraint was not enforced at all (see `warning`)."""
    warning: str | None = None
    """Vietnamese warning when the schedule cannot meet the design guarantee —
    short sessions silently degrade it, and an operator must be told BEFORE
    going live rather than discovering it in the analysis (audit 30/08)."""


# ---------------------------------------------------------------------------
# State — operator vs host are DISTINCT models (blinding rule L6)
# ---------------------------------------------------------------------------


class PinnedProduct(BaseModel):
    product_id: str
    name: str
    price: float
    stock: int


class OperatorBlockState(BaseModel):
    index: int
    phase: Literal["early", "mid", "late"]
    assignment: Literal["ON", "OFF"] | None = None
    is_washout: bool
    seconds_remaining: float


class AutopilotState(BaseModel):
    """Is the server actually running this auto session, and is it working?

    OPERATOR ONLY — it names block indices and would break host blinding
    (rule L6) if it ever reached :class:`HostState`.
    """

    enabled: bool = False
    """Whether the server-side executor is switched on (LIVELIFT_AUTOPILOT)."""
    last_run_ts: datetime | None = None
    """Heartbeat: when the executor last looked at this session. None = it has
    not run yet for this session (which is itself information)."""
    actions_taken: int = 0
    on_blocks_total: int = 0
    on_blocks_done: int = 0
    """ON blocks that already carry an exposure (system pin or human action)."""
    missed_on_blocks: list[int] = Field(default_factory=list)
    """ON blocks that ended with no action at all — cannot be repaired."""
    last_error: str | None = None
    alarm: str | None = None
    """Vietnamese alarm when a live auto session is producing no treatment.
    Computed from stored exposures, NOT from the heartbeat, so it fires even
    when the executor never started (incident 12/09)."""


class OperatorState(BaseModel):
    """Full experiment view — control-desk operators only."""

    role: Literal["operator"] = "operator"
    session_id: str
    status: SessionStatus
    mode: SessionMode
    elapsed_s: float
    current_block: OperatorBlockState | None = None
    pinned_product: PinnedProduct | None = None
    cards: list[ActionCard] = Field(default_factory=list)
    design_hash: str | None = None
    """Design commitment of this session's schedule; None for sessions with no
    schedule or scheduled before gói Q3. OPERATOR ONLY — never on HostState
    (rule L6: it is a fingerprint of the assignment mechanism)."""
    autopilot: AutopilotState | None = None
    """Executor status for mode='auto'; None for suggest-mode sessions."""
    cards_note: str | None = None
    """Lý do tiếng Việt vì sao ``cards`` rỗng theo THIẾT KẾ (phiên đã kết thúc,
    phiên phân tích video người khác, phiên chưa phát sóng) — None khi phiên
    đang được phép ghim. Phân biệt "không mời thao tác vì không thao tác được"
    với "chưa đủ số liệu để xếp hạng"; hai trạng thái đó đọc giống hệt nhau
    trên một danh sách rỗng không lời."""
    is_demo: bool = False
    """Cờ DỮ LIỆU MẪU của phiên (xem :class:`SessionOut`) — bàn điều khiển vẽ
    nhãn DEMO từ đây. KHÔNG thêm vào :class:`HostState`: màn host bị đóng băng
    ở đúng 4 trường (quy tắc làm mù L6), và người dẫn không cần biết buổi tập
    là demo hay thật để đọc kịch bản."""


class HostState(BaseModel):
    """Host-facing view. BLINDING RULE (L6): the host must not be able to
    infer block boundaries, assignment, or time remaining in a block. This
    model therefore only carries the pinned product, its price/stock, and
    total elapsed time — nothing else can be serialized through it."""

    model_config = ConfigDict(extra="forbid")

    pinned_product: str | None = None  # product display name (Vietnamese)
    price: float | None = None
    stock: int | None = None
    elapsed_s: float = 0.0


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------


def _require_aware(v: datetime | None) -> datetime | None:
    """Hard rule 7: no naive datetimes — an offset-less timestamp would be
    silently interpreted in some machine-local timezone."""
    if v is not None and v.tzinfo is None:
        raise ValueError(
            "ts_utc phải kèm múi giờ (ISO-8601 có offset, ví dụ 2026-09-06T13:05:42+00:00)"
        )
    return v


class CommentIn(BaseModel):
    """One comment from the ingest runner or the dashboard.

    ``platform`` + ``ext_id`` (both set by :class:`livelift.ingest.base.ApiSink`)
    form the idempotency key: re-sending the same comment — runner restart,
    spool replay — must not create a duplicate row. ``ts_utc`` is the platform
    timestamp; when present it is the stored event time (block attribution
    included), so a comment near a block boundary lands in the right block
    even if it reaches the server late. All three are optional so manual
    dashboard posts keep working unchanged.
    """

    text: str = Field(min_length=1, max_length=2000)
    platform: Platform | None = None
    ext_id: str | None = Field(default=None, min_length=1, max_length=128)
    ts_utc: datetime | None = None
    client_ts: datetime | None = None

    @field_validator("ts_utc")
    @classmethod
    def _ts_utc_aware(cls, v: datetime | None) -> datetime | None:
        return _require_aware(v)


class CommentOut(BaseModel):
    """Only scrubbed text ever appears here — raw text is never persisted,
    logged, or returned (hard project rule 1)."""

    comment_id: str
    session_id: str
    block_id: str | None = None
    ts: datetime
    text: str  # scrubbed
    pii_kinds: list[str] = Field(default_factory=list)
    intent: str | None = None
    intent_confidence: float | None = None
    """Top-class probability of the trained intent model (None = keyword
    baseline / old rows). Feeds the active-learning export ordering
    (livelift.nlp.label_llm) — NOT a number for end-user display."""


class TickIn(BaseModel):
    """One viewer snapshot. ``ts_utc`` (optional, sent by ApiSink) is the
    source timestamp: when present the 30s bucket is computed from it instead
    of the arrival time, so a spool-replayed tick lands in its original
    bucket (where the (session, bucket) upsert makes re-sending idempotent).
    """

    viewers: float = Field(ge=0)
    comment_rate: float = Field(default=0.0, ge=0)
    like_rate: float = Field(default=0.0, ge=0)
    ts_utc: datetime | None = None

    @field_validator("ts_utc")
    @classmethod
    def _ts_utc_aware(cls, v: datetime | None) -> datetime | None:
        return _require_aware(v)


class TickOut(BaseModel):
    session_id: str
    ts_bucket: datetime
    viewers: float
    comment_rate: float
    like_rate: float
    click_count: int = 0
    pinned_product_id: str | None = None


ReactionKind = Literal["superchat", "gift", "sticker", "membership", "like"]


class ReactionIn(BaseModel):
    """One paid/visible audience event (migration 0007).

    ``amount``/``currency`` are the PUBLIC purchase string the platform prints
    for every viewer (e.g. Super Chat "50.000 ₫") — not PII. There is NO
    author field on this model by design (hard rule 1): who sent the money is
    never ingested. ``(platform, ext_id)`` is the idempotency key, exactly as
    for comments.
    """

    kind: ReactionKind
    ts_utc: datetime | None = None
    amount: float | None = Field(default=None, ge=0)
    currency: str | None = Field(default=None, min_length=1, max_length=16)
    platform: Platform | None = None
    ext_id: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("ts_utc")
    @classmethod
    def _ts_utc_aware(cls, v: datetime | None) -> datetime | None:
        return _require_aware(v)


class ReactionOut(BaseModel):
    reaction_id: str
    session_id: str
    ts_utc: datetime
    kind: ReactionKind
    amount: float | None = None
    currency: str | None = None
    platform: str | None = None
    ext_id: str | None = None


# ---------------------------------------------------------------------------
# Action cards (E2-04) and interventions
# ---------------------------------------------------------------------------


class ActionCard(BaseModel):
    """A suggested action shown on the control desk.

    E2-04 (hard project rule 2): ``source='forecast'`` numbers must not carry
    a confidence interval; only ``source='experiment'`` numbers may. Enforced
    by the model validator below — a forecast card with CI fields cannot be
    constructed at all.
    """

    model_config = ConfigDict(extra="forbid")

    card_id: str
    action_type: Literal["pin"] = "pin"
    product_id: str
    product_name: str
    headline: str  # Vietnamese, user-facing
    rationale: str  # Vietnamese, user-facing
    source: Literal["forecast", "experiment"]
    estimate: float
    ci_low: float | None = None
    ci_high: float | None = None

    @model_validator(mode="after")
    def _forecast_never_carries_ci(self) -> ActionCard:
        if self.source == "forecast" and (self.ci_low is not None or self.ci_high is not None):
            raise ValueError(
                "E2-04: số liệu từ mô hình dự báo (source='forecast') không được kèm "
                "khoảng tin cậy — chỉ source='experiment' mới được có ci_low/ci_high"
            )
        return self


class ExecuteRequest(BaseModel):
    card_id: str | None = None
    product_id: str | None = None


class CandidateOut(BaseModel):
    product_id: str
    estimate: float
    ci_low: float
    ci_high: float
    in_overlap_set: bool


class ExecuteOut(BaseModel):
    action_id: str
    block_index: int
    action_type: Literal["pin"] = "pin"
    source: Literal["model"] = "model"
    product_id: str
    inner_propensity: float
    randomized: bool
    overlap_set: list[str]
    considered: list[CandidateOut]


class OverrideRequest(BaseModel):
    product_id: str | None = None
    reason: OverrideReason


class OverrideOut(BaseModel):
    action_id: str
    action_type: Literal["pin", "unpin"]
    source: Literal["human"] = "human"
    product_id: str | None = None
    override_reason: OverrideReason
    block_index: int | None = None


# ---------------------------------------------------------------------------
# Reports (experiment source — CI allowed per E2-04)
# ---------------------------------------------------------------------------


class ComplianceStats(BaseModel):
    on_blocks: int
    on_blocks_with_pin: int
    compliance_rate: float | None = None
    override_count: int
    n_interventions: int


class SessionReport(BaseModel):
    session_id: str
    label: str = "kết quả thí nghiệm sơ bộ"
    source: Literal["experiment"] = "experiment"
    is_demo: bool = False
    """Cờ DỮ LIỆU MẪU của phiên (xem :class:`SessionOut`) — báo cáo một phiên
    demo vẫn xem được riêng, nhưng client phải vẽ nhãn DEMO kèm mọi con số."""
    n_blocks: int
    n_on: int
    n_off: int
    diff_in_means: float | None = None
    blocks: list[dict[str, Any]]
    compliance: ComplianceStats


class CauTomTat(BaseModel):
    """Một câu của "tóm tắt 3 câu" (AI-LAYER lớp 0 — analysis/narrate.py).

    Văn xuôi TEMPLATE tất định, không LLM: mọi con số trong ``text`` chép từ
    chính payload chứa nó, ``refs`` là đường dẫn JSON của từng số để UI hover
    ra nguồn. ``badge`` là huy hiệu bằng chứng: ``thi_nghiem`` CHỈ khi số đến
    từ analyze_outer ước lượng được; ``quan_sat`` cho số đếm mô tả;
    ``thieu_du_lieu`` cho tuyên bố thiếu kèm con số cần thêm."""

    text: str
    badge: Literal["thi_nghiem", "quan_sat", "thieu_du_lieu"]
    refs: list[str] = Field(default_factory=list)


class DenominatorCheck(BaseModel):
    """Cổng ICS — mẫu số (viewer-giây) có chịu tác động của can thiệp không?

    Biến kết quả chính là click/1.000 viewer-giây. Phép chia đó chỉ vô hại nếu
    viewer-giây KHÔNG đổi theo nhánh gán. Cổng này chạy đúng kiểm định ngẫu
    nhiên hóa đã tiền đăng ký nhưng lấy MẪU SỐ làm biến kết quả
    (`analysis.robust.ics_gate`).

    Đây là ghi chú PHƯƠNG PHÁP, không phải kiểm tra toàn vẹn dữ liệu: nó KHÔNG
    thuộc bộ SRM §8.1 (§8.1 cấm chạy SRM trên đại lượng hậu can thiệp, và
    viewer-giây đúng là hậu can thiệp). Cờ ĐỎ ở đây không loại khối, không đổi
    con số chính — nó chỉ nói người đọc phải xem kèm estimand mẫu-số-cố-định.
    """

    p_value: float | None = None
    flagged: bool = False
    n_draws: int = 0
    estimate: float | None = None
    """Chênh lệch viewer-giây trung bình BẬT − TẮT (số vận hành, có dấu)."""
    note: str


class ExperimentSummary(BaseModel):
    label: str = "kết quả thí nghiệm"
    source: Literal["experiment"] = "experiment"
    env: Literal["real", "demo"] = "real"
    """Nguồn dữ liệu của bản gộp này (gói DEMO-THẬT). ``real`` (mặc định) —
    KẾT QUẢ THẬT: mọi phiên ``is_demo`` bị loại như ``dry_run``, không có cách
    nào trộn. ``demo`` — bản gộp CHỈ trên dữ liệu mẫu, ``label`` đổi thành
    "kết quả MÔ PHỎNG..."; client phải vẽ nhãn/watermark DEMO và không bao giờ
    trình bày nó như kết quả thật."""
    n_sessions: int
    n_blocks: int
    n_on: int
    n_off: int
    raw_clicks: int | None = None
    """Tổng click ĐÃ GHI của các phiên trong phân tích gộp — số vận hành, kể cả
    click bị gắn cờ không hợp lệ (flag-don't-drop, gói Q1)."""
    valid_clicks: int | None = None
    """Tổng click HỢP LỆ theo bộ quy tắc IAB/GIVT-lite (click_validity) — tập
    con của raw_clicks; chính là nguồn tử số của biến kết quả chính."""
    sessions_excluded: dict[str, int] = Field(default_factory=dict)
    """Lý do (tiếng Việt) -> số phiên bị giữ NGOÀI mẫu gộp theo tiền đăng ký
    §8.2: phiên chưa kết thúc/đã huỷ, phiên phân tích quan sát, phiên chạy thử.

    Công bố con số này là bắt buộc: một phiên bị loại mà không ai thấy thì
    không phân biệt được với một phiên chưa từng tồn tại. Mọi lý do ở đây đều
    quyết định được TRƯỚC khi nhìn bất kỳ kết quả nào."""
    estimate: float | None = None
    # No estimate_ht field: at the outer tier's constant p=0.5 the Hájek/IPW
    # estimate is algebraically identical to `estimate` — publishing both as
    # two "independent" estimators was dishonest (PREREGISTRATION §5b, 06/09).
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    n_draws: int | None = None
    measured_cv: float | None = None
    measured_compliance: float | None = None
    cv_poisson_floor: float | None = None
    """CV the design would still have if every systematic source were
    predicted perfectly — the floor set by click counting noise."""
    reducible_share: float | None = None
    """Fraction of within-session variance that is NOT counting noise: the hard
    ceiling on any covariate-adjustment R². Near zero means variance reduction
    cannot help and only a design change (longer blocks, more viewers) can."""
    power_table: list[dict[str, Any]] = Field(default_factory=list)
    denominator_check: DenominatorCheck | None = None
    """Cờ vận hành gói P3: mẫu số của biến kết quả có dấu hiệu chịu can thiệp
    không. Không phải suy diễn chính — xem :class:`DenominatorCheck`."""
    message: str | None = None  # Vietnamese, set when data is insufficient
    tom_tat_3_cau: list[CauTomTat] = Field(default_factory=list)
    """Tóm tắt 3 câu (kết luận / bằng chứng / việc nên làm) — template tất
    định từ chính các trường của payload này, tôn trọng khóa §7 (trong cửa sổ
    khóa không câu nào chứa ước lượng/KTC/p). Xem :class:`CauTomTat`."""
    estimable: bool = True
    """False when the design cannot be tested at all (an arm below the minimum
    block count) OR when the effect estimate is locked by the pre-registered
    freeze date (§7, RESULTS_FREEZE_UNTIL — `message` says which). Clients
    MUST NOT render an effect, interval or p-value in that case — the fields
    are null and any 'significant' styling is wrong (audit 30/08)."""


class SignalStateOut(BaseModel):
    name: str
    status: Literal["ok", "degraded", "missing"]
    detail: str
    secondary: str | None = None
    """Số PHỤ có nhãn, hiện BÊN CẠNH ``detail`` chứ không thay thế nó.

    Hiện chỉ ``clicks`` dùng: mang tổng nhấp THÔ đi kèm con số hợp lệ, vì
    tiền đăng ký §4.1 bắt buộc báo cáo chuỗi thô song song với chuỗi hợp lệ.
    Nhãn nói rõ đây là đại lượng nào — không ai được nhầm số lớn hơn là số
    mà phân tích đã chạy trên đó."""


class CapabilityOut(BaseModel):
    name: str
    status: Literal["ok", "degraded", "missing"]
    reason: str


class SignalCoverageOut(BaseModel):
    """Which conclusions this session's data can honestly support.

    The answer to "can LiveLift measure any sales video?" is this matrix, not
    a yes: each capability names its required signals, and a missing signal
    downgrades the capability EXPLICITLY instead of silently producing weaker
    numbers."""

    session_id: str
    signals: list[SignalStateOut]
    capabilities: list[CapabilityOut]


# ---------------------------------------------------------------------------
# Báo cáo sau phiên (post-live report)
# ---------------------------------------------------------------------------


class DinhBinhLuan(BaseModel):
    """Đỉnh nhịp bình luận: giá trị + thời điểm (kiểu Feigua timeline)."""

    gia_tri_per_phut: float
    offset_s: float | None = None
    ts: datetime


class NguoiXemTomTat(BaseModel):
    """Chỉ tồn tại khi có điểm đo mang SỐ NGƯỜI XEM THẬT (không đếm tick
    placeholder của phiên replay)."""

    dinh: float
    trung_binh: float
    n_diem_do: int


class ReactionTomTat(BaseModel):
    tong: int
    theo_loai: dict[str, int]
    tong_tien: dict[str, float] = Field(default_factory=dict)
    """currency -> tổng tiền CÔNG KHAI của các sự kiện có amount; sự kiện
    không mang số tiền (membership/gift) không đóng góp — không quy đổi,
    không ước tính."""


class BaoCaoTongQuan(BaseModel):
    """Thẻ số tổng quan. QUY TẮC KHÔNG-BỊA-SỐ: mỗi ô hoặc có giá trị, hoặc
    là None VÀ có lý do tiếng Việt trong ``thieu`` — không bao giờ 0 giả."""

    thoi_luong_s: float | None = None
    tong_binh_luan: int
    dinh_binh_luan: DinhBinhLuan | None = None
    nguoi_xem: NguoiXemTomTat | None = None
    luot_nhap_hop_le: int | None = None
    """Số nhấp HỢP LỆ — biến kết quả chính theo tiền đăng ký §4.1. Đây là con
    số mà `/signals`, bảng khối và ước lượng viên cùng dùng; không màn hình nào
    được khoe một con số khác dưới cùng cái tên "lượt nhấp"."""
    luot_nhap_tho: int | None = None
    """Tổng nhấp ĐÃ GHI, kể cả cú bị gắn cờ không hợp lệ (flag-don't-drop).
    Số PHỤ bắt buộc báo cáo kèm (§4.1) — luôn đứng cạnh số hợp lệ, không bao
    giờ thay chỗ nó."""
    reactions: ReactionTomTat | None = None
    thieu: dict[str, str] = Field(default_factory=dict)


class KhoanhKhacOut(BaseModel):
    """Một spike bình luận/phút trên dòng thời gian — mô tả là câu QUAN SÁT
    có dán nhãn, không bao giờ là câu nhân quả."""

    offset_s: float
    ts: datetime | None = None
    binh_luan_per_phut: float
    nen_per_phut: float
    ty_le: float | None = None
    san_pham_dang_ghim: str | None = None
    mo_ta: str


class PhanBoYDinh(BaseModel):
    tong: int
    dem_theo_nhan: dict[str, int]
    caveat: str
    """BẮT BUỘC: precision của nhãn tự động phụ thuộc tỷ lệ nền từng lớp —
    xem docs/benchmarks/live-fire-da-nguon.md. Client phải hiển thị kèm."""


class KetQuaThiNghiem(BaseModel):
    """Phần nhân quả của báo cáo — CHỈ cho phiên có lịch gán ngẫu nhiên, chạy
    đúng đường analyze_outer đã tiền đăng ký và tôn trọng khóa §7."""

    source: Literal["experiment"] = "experiment"
    khoa: bool = False
    ly_do_khoa: str | None = None
    estimable: bool = False
    n_blocks: int = 0
    n_on: int = 0
    n_off: int = 0
    estimate: float | None = None
    ci_low: float | None = None
    ci_high: float | None = None
    p_value: float | None = None
    n_draws: int | None = None
    message: str | None = None


class BaoCaoOut(BaseModel):
    """Báo cáo sau phiên — mọi con số mang nguồn, mọi khoảng trống được tuyên
    bố qua ma trận tín hiệu, và phiên quan sát không bao giờ mang số nhân quả."""

    session_id: str
    tieu_de: str | None = None
    platform: str
    loai_phien: Literal["thi_nghiem", "quan_sat"]
    nhan: str
    is_demo: bool = False
    """Cờ DỮ LIỆU MẪU của phiên (xem :class:`SessionOut`). Báo cáo phiên demo
    xem được đầy đủ nhưng client phải vẽ nhãn/watermark DEMO — con số mô phỏng
    không bao giờ được trình bày như số đo thật."""
    tong_quan: BaoCaoTongQuan
    tin_hieu: list[SignalStateOut]
    nang_luc: list[CapabilityOut]
    khoanh_khac: list[KhoanhKhacOut] = Field(default_factory=list)
    khoanh_khac_ghi_chu: str | None = None
    phan_bo_y_dinh: PhanBoYDinh
    pii_da_che: dict[str, int] = Field(default_factory=dict)
    ket_qua_thi_nghiem: KetQuaThiNghiem | None = None
    """None cho phiên quan sát — nhãn ``nhan`` nói rõ vì sao."""
    tom_tat_3_cau: list[CauTomTat] = Field(default_factory=list)
    """Tóm tắt 3 câu của phiên (kết luận đúng trạng thái / bằng chứng / việc
    nên làm) — template tất định, phiên quan sát không câu nào nhân quả và
    khóa §7 được tôn trọng y như ``ket_qua_thi_nghiem``."""
    goi_y_chien_thuat: list[str] = Field(default_factory=list)
    """Câu QUAN SÁT có dán nhãn ('— quan sát, chưa kiểm chứng nhân quả');
    tuyệt đối không câu nhân quả cho phiên quan sát."""


# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------


class DemoSeedRequest(BaseModel):
    n_sessions: int = Field(default=3, ge=1, le=20)
    effect: float = Field(default=0.15, ge=-0.9, le=5.0)
    duration_min: int = Field(default=60, ge=30, le=180)


class DemoSeedOut(BaseModel):
    session_ids: list[str]
    replay_session_id: str
    product_ids: list[str]
    shortlink_codes: list[str]


# OperatorState references ActionCard, which is defined further down the
# module — resolve the forward reference explicitly.
OperatorState.model_rebuild()
