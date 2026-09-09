"""IAB-style valid-click classification (GIVT-lite) — flag, never drop.

The primary outcome counts only VALID clicks; invalid ones are flagged with a
reason and kept forever (flag-don't-drop). Five pre-registered rules
(PREREGISTRATION §4.1):

1. ``givt_ua``     — the user-agent matches the General Invalid Traffic list
                     of known robots/spiders (IAB Click Measurement Guidelines
                     2009, §invalid-traffic; the "GIVT-lite" regex below).
2. ``prefetch``    — browser prefetch/prerender/preview headers: the request
                     was issued by the browser speculatively, not by a person
                     (``Sec-Purpose`` containing prefetch/prerender,
                     ``X-Moz: prefetch``, ``X-Purpose: preview``).
3. ``non_get``     — only GET requests count as clicks.
4. ``refractory``  — a counted click with the same ``dedup_hash`` on the same
                     shortlink happened less than τ seconds earlier (default
                     τ = 10 s; sensitivity τ ∈ {5, 30, 60} re-run via
                     :func:`recount_click_validity`).
5. ``volume_cap``  — more than M counted clicks per (dedup_hash, shortlink,
                     block) (default M = 5): slow-drip automation that spaces
                     clicks beyond τ (Fabijan et al., KDD 2019 — bot traffic
                     distorts online-experiment metrics and must be filtered
                     by pre-registered, treatment-blind rules).

ASSIGNMENT-BLINDNESS INVARIANT: every rule uses ONLY request attributes —
user-agent, headers, HTTP method, and the timing/identity of earlier requests
with the same dedup fingerprint. No function in this module receives (or may
ever receive) the block assignment, arm, or propensity; a validity rule that
could see the assignment could manufacture an effect. A test asserts the
signatures stay clean (tests/test_click_validity.py::test_assignment_blindness).

Everything here is pure: no clocks, no I/O, no RNG.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any

REFRACTORY_TAU_S = 10.0
"""Primary refractory window τ (seconds). Pre-registered; sensitivity {5, 30, 60}."""

VOLUME_CAP = 5
"""Max counted clicks per (dedup_hash, shortlink, block) before flagging."""

INVALID_REASONS = ("givt_ua", "prefetch", "non_get", "refractory", "volume_cap")

REQUEST_ONLY_REASONS = frozenset({"givt_ua", "prefetch", "non_get"})
"""Reasons decided purely from request attributes that are NOT persisted (the
raw user-agent and headers are never stored — §11.2), so a recount keeps these
verdicts as-is instead of pretending it could re-derive them."""

# GIVT-lite: known robots/spiders/tools by user-agent substring (IAB 2009 uses
# a maintained robots list; this is the self-hosted, auditable subset).
_GIVT_UA_RE = re.compile(
    r"bot\b|crawler|spider|headless|curl|wget|python-requests|python-urllib"
    r"|scrapy|phantomjs|selenium|playwright|puppeteer|httpclient|libwww"
    r"|okhttp|go-http-client|java/|feedfetcher|mediapartners|slurp|facebookexternalhit",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PriorClick:
    """An earlier click with the SAME (dedup_hash, shortlink) as the one being
    classified — request-level history only, no assignment information.

    ``age_s``     : seconds elapsed between that click and the current one.
    ``counted``   : whether that click was itself valid (counted) — the
                    refractory window anchors on counted clicks, so a burst
                    collapses to exactly one counted click per τ.
    ``same_block``: whether it fell in the same schedule block (block identity
                    only — used for the volume cap denominator, never the arm).
    """

    age_s: float
    counted: bool = True
    same_block: bool = True


def classify_ua(ua: str | None) -> str:
    """Coarse user-agent class: 'givt' | 'browser' | 'unknown'."""
    if ua is None or not ua.strip():
        return "unknown"
    return "givt" if _GIVT_UA_RE.search(ua) else "browser"


def _header_lookup(headers: Mapping[str, str]) -> dict[str, str]:
    return {str(k).lower(): str(v) for k, v in headers.items()}


def _timing_verdict(
    prior_clicks_same_hash: Sequence[PriorClick],
    tau_s: float,
    volume_cap: int,
) -> str | None:
    """Shared timing rules (refractory + volume cap) over request history."""
    for prior in prior_clicks_same_hash:
        if prior.counted and 0.0 <= prior.age_s < tau_s:
            return "refractory"
    counted_in_block = sum(1 for p in prior_clicks_same_hash if p.counted and p.same_block)
    if counted_in_block >= volume_cap:
        return "volume_cap"
    return None


def classify_click(
    ua: str | None,
    headers: Mapping[str, str],
    method: str,
    prior_clicks_same_hash: Sequence[PriorClick] = (),
    *,
    tau_s: float = REFRACTORY_TAU_S,
    volume_cap: int = VOLUME_CAP,
) -> tuple[bool, str | None, str]:
    """Classify one click at write time → ``(is_valid, invalid_reason, ua_class)``.

    Inputs are request attributes ONLY (see module docstring for the
    assignment-blindness invariant). First failing rule wins, in the order
    givt_ua → prefetch → non_get → refractory → volume_cap. ``ua_class`` is
    always returned, even for valid clicks, so the population of user agents
    stays auditable without ever storing the raw string.
    """
    ua_class = classify_ua(ua)
    if ua_class == "givt":
        return False, "givt_ua", ua_class

    h = _header_lookup(headers)
    sec_purpose = h.get("sec-purpose", "").lower()
    if (
        "prefetch" in sec_purpose
        or "prerender" in sec_purpose
        or h.get("x-moz", "").lower() == "prefetch"
        or h.get("x-purpose", "").lower() == "preview"
    ):
        return False, "prefetch", ua_class

    if method.upper() != "GET":
        return False, "non_get", ua_class

    timing = _timing_verdict(prior_clicks_same_hash, tau_s, volume_cap)
    if timing is not None:
        return False, timing, ua_class

    return True, None, ua_class


def _ts_seconds(ts: Any) -> float:
    """Normalize a row timestamp (datetime or numeric seconds) to seconds."""
    if isinstance(ts, datetime):
        return ts.timestamp()
    return float(ts)


def recount_click_validity(
    clicks: Sequence[Mapping[str, Any]],
    tau_s: float = REFRACTORY_TAU_S,
    volume_cap: int = VOLUME_CAP,
) -> list[dict[str, Any]]:
    """Re-run the validity classification over a session's full click history.

    Serves the T+30' post-session reconciliation and the pre-registered τ
    sensitivity (τ ∈ {5, 30, 60}): pure function — takes the stored
    ``click_event`` rows (dicts with ``click_id``, ``ts``, ``dedup_hash``,
    ``shortlink_code``, ``block_id``, ``is_valid``, ``invalid_reason``),
    replays the TIMING rules (refractory, volume cap) in timestamp order, and
    returns the rows whose verdict changed as
    ``{"click_id", "is_valid", "invalid_reason"}`` — the caller applies them
    (rows are updated, NEVER deleted: flag-don't-drop).

    Verdicts from request-only rules (``givt_ua``, ``prefetch``, ``non_get``)
    are kept as stored: the raw user-agent/headers are never persisted (§11.2),
    so those rules cannot honestly be re-derived here. Rows without a
    ``dedup_hash`` carry no fingerprint and are left valid by the timing rules.
    Assignment-blind like everything in this module: rows are grouped by
    (dedup_hash, shortlink_code) and block IDENTITY only — the arm is neither
    read nor accepted.
    """
    ordered = sorted(clicks, key=lambda r: _ts_seconds(r["ts"]))
    # counted click history per (dedup_hash, shortlink): [(ts_s, block_id)]
    counted: dict[tuple[str, Any], list[tuple[float, Any]]] = {}
    changes: list[dict[str, Any]] = []

    for row in ordered:
        stored_valid = row.get("is_valid") is not False
        stored_reason = row.get("invalid_reason")

        if not stored_valid and stored_reason in REQUEST_ONLY_REASONS:
            continue  # sticky: cannot be recomputed from stored rows

        dedup_hash = row.get("dedup_hash")
        if dedup_hash is None:
            new_valid, new_reason = True, None
        else:
            key = (str(dedup_hash), row.get("shortlink_code"))
            ts_s = _ts_seconds(row["ts"])
            block_id = row.get("block_id")
            priors = [
                PriorClick(age_s=ts_s - prior_ts, counted=True, same_block=prior_block == block_id)
                for prior_ts, prior_block in counted.get(key, [])
            ]
            reason = _timing_verdict(priors, tau_s, volume_cap)
            new_valid, new_reason = reason is None, reason
            if new_valid:
                counted.setdefault(key, []).append((ts_s, block_id))

        if new_valid != stored_valid or new_reason != stored_reason:
            changes.append(
                {
                    "click_id": row.get("click_id"),
                    "is_valid": new_valid,
                    "invalid_reason": new_reason,
                }
            )
    return changes
