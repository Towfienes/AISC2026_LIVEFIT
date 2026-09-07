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
SessionStatus = Literal["planned", "scheduled", "live", "ended"]


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
    realized_min_per_arm_per_phase: int = 0
    """Balance guarantee the layout could actually deliver (see `warning`)."""
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
    n_blocks: int
    n_on: int
    n_off: int
    diff_in_means: float | None = None
    blocks: list[dict[str, Any]]
    compliance: ComplianceStats


class ExperimentSummary(BaseModel):
    label: str = "kết quả thí nghiệm"
    source: Literal["experiment"] = "experiment"
    n_sessions: int
    n_blocks: int
    n_on: int
    n_off: int
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
    message: str | None = None  # Vietnamese, set when data is insufficient
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
