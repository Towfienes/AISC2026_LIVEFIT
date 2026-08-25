"""Self-hosted shortlink redirect — the operational definition of the primary
outcome (research synthesis L5): one click = one request to /r/{code}.

Design constraints:
- NEVER fail the redirect: a viewer following a product link must land on the
  product page even if click logging breaks. Logging is wrapped accordingly.
- No PII: the dedup hash salts client fingerprint with the session id and a
  per-process salt, and the raw fingerprint is never stored (§11.2 — salt
  rotates per session, so the same viewer in two sessions is unlinkable).
"""

from __future__ import annotations

import hashlib
import logging
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from livelift.api import service
from livelift.api.service import StoreDep

router = APIRouter()
logger = logging.getLogger(__name__)

# Per-process salt component: even with a database dump plus request logs, a
# dedup hash cannot be reversed to a device fingerprint after restart.
_PROCESS_SALT = secrets.token_hex(16)


def _dedup_hash(request: Request, session_id: str | None) -> str:
    client = request.client.host if request.client else ""
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
        row = {
            "click_id": service.new_id(),
            "block_id": block_id,
            "ts": service.now_utc(),
            "product_id": link["product_id"],
            "shortlink_code": code,
            "dedup_hash": _dedup_hash(request, session_id),
        }
        store.add_click(session_id, row)
        if session_id:
            store.publish(
                session_id,
                {"type": "click", "data": {"product_id": link["product_id"]}},
            )
    except Exception:  # noqa: BLE001 — the redirect must always go through
        logger.exception("click logging failed for code=%s", code)

    return RedirectResponse(link["target_url"], status_code=302)
