"""Shared test helpers.

``seed_phien_that_mo_phong`` — simulated stand-ins for REAL sessions.

Before gói DEMO-THẬT, tests that needed "a few ended sessions with data"
called ``POST /demo/seed``. That route now marks everything it creates
``is_demo=True`` (sample data, excluded from every real scientific output),
so a test of the REAL analysis path (``/experiment/summary`` default env, §7
freeze, denominator flag, raw/valid click totals) can no longer ride on it.
This helper runs the SAME simulator/store pipeline with ``is_demo=False`` —
sessions that stand in for real ones, created directly against the store the
app under test owns.

It exists for tests only: the ``is_demo=False`` escape hatch on
``_seed_one_session`` must never be reachable from a production route.
"""

from __future__ import annotations

import random

from livelift.api import service
from livelift.api.routes.demo import DEMO_PRODUCTS, _seed_one_session


def seed_phien_that_mo_phong(
    store,
    n_sessions: int = 3,
    effect: float = 0.5,
    duration_min: int = 40,
    seed0: int = 1000,
) -> list[str]:
    """Seed ``n_sessions`` ended, measured, NON-demo sessions. Returns ids."""
    now = service.now_utc()
    for p in DEMO_PRODUCTS:
        store.create_product({**p, "created_at": now})
    rng = random.Random(4242)
    return [
        _seed_one_session(
            store,
            rng,
            duration_min=duration_min,
            effect=effect,
            seed=seed0 + i,
            start_offset_ago_min=(i + 1) * (duration_min + 30),
            is_demo=False,
            title=f"Phiên thật mô phỏng (test) #{i + 1}",
        )
        for i in range(n_sessions)
    ]
