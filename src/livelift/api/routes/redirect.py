"""Self-hosted shortlink redirect — the operational definition of the primary
outcome (research synthesis L5): one click = one request to /r/{code}.

Design constraints:
- NEVER fail the redirect: a viewer following a product link must land on the
  product page even if click logging breaks. Logging is wrapped accordingly.
- No PII: the dedup hash salts client fingerprint with the session id and a
  per-process salt, and the raw fingerprint is never stored (§11.2 — salt
  rotates per session, so the same viewer in two sessions is unlinkable).
- Validity (gói Q1): every click is classified at write time by the pure
  IAB/GIVT-lite rules in :mod:`livelift.core.click_validity` and stored with
  ``is_valid``/``invalid_reason``/``ua_class`` — flagged, never dropped. The
  classification is assignment-blind (request attributes only) and lives
  inside the same try/except as the logging: a bot, a classification error,
  anything — the 302 goes out regardless.
"""

from __future__ import annotations

import hashlib
import logging
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from livelift.api import service
from livelift.api.auth import dia_chi_goi
from livelift.api.service import StoreDep
from livelift.core.click_validity import PriorClick, classify_click

router = APIRouter()
logger = logging.getLogger(__name__)

# Per-process salt component: even with a database dump plus request logs, a
# dedup hash cannot be reversed to a device fingerprint after restart.
_PROCESS_SALT = secrets.token_hex(16)


def _dedup_hash(request: Request, session_id: str | None) -> str:
    # Địa chỉ THẬT của người xem, không phải của Caddy (kiểm toán 17/09/2026):
    # trước đó mọi click sau proxy băm cùng một địa chỉ, nên luật refractory
    # và volume-cap của click_validity gộp mọi người xem thành MỘT người và
    # đánh dấu click hợp lệ của người thứ hai trở đi là vô hiệu.
    client = dia_chi_goi(request)
    ua = request.headers.get("user-agent", "")
    material = f"{_PROCESS_SALT}:{session_id or ''}:{client}:{ua}"
    return hashlib.sha256(material.encode()).hexdigest()[:32]


@router.get("/r/{code}")
def follow_shortlink(code: str, request: Request, store: StoreDep) -> RedirectResponse:
    link = store.get_shortlink(code)
    if link is None:
        raise HTTPException(status_code=404, detail="Link không tồn tại")

    try:
        session_id = link.get("session_id")
        block_id = None
        if session_id:
            session = store.get_session(session_id)
            if session and session.get("status") == "live":
                elapsed = service.elapsed_seconds(session, service.now_utc())
                block = service.block_at_offset(store.get_blocks(session_id), elapsed)
                if block is not None:
                    block_id = block["block_id"]
        now = service.now_utc()
        dedup_hash = _dedup_hash(request, session_id)
        # Validity classification (assignment-blind: request attributes and
        # same-fingerprint history only — see core/click_validity.py).
        # Only THIS fingerprint's history on THIS shortlink is needed, and it
        # is fetched as such: reading every click of the session would make the
        # redirect cost O(clicks-so-far) — slowest during a bot burst.
        priors: list[PriorClick] = []
        if session_id:
            priors = [
                PriorClick(
                    age_s=(now - prior["ts"]).total_seconds(),
                    counted=prior.get("is_valid") is not False,
                    same_block=prior.get("block_id") == block_id,
                )
                for prior in store.list_clicks_for_fingerprint(session_id, dedup_hash, code)
            ]
        is_valid, invalid_reason, ua_class = classify_click(
            request.headers.get("user-agent"),
            request.headers,
            request.method,
            priors,
        )
        row = {
            "click_id": service.new_id(),
            "block_id": block_id,
            "ts": now,
            "product_id": link["product_id"],
            "shortlink_code": code,
            "dedup_hash": dedup_hash,
            "is_valid": is_valid,
            "invalid_reason": invalid_reason,
            "ua_class": ua_class,
        }
        store.add_click(session_id, row)
        if session_id:
            store.publish(
                session_id,
                {
                    "type": "click",
                    "data": {"product_id": link["product_id"], "is_valid": is_valid},
                },
            )
    except Exception:  # noqa: BLE001 — the redirect must always go through
        logger.exception("click logging failed for code=%s", code)

    return RedirectResponse(link["target_url"], status_code=302)
