"""Demo seeding: simulated finished sessions + a live replay session.

Feeds the Replay Engine (E6-06) and lets the whole stack demo with zero
external dependencies: the simulator generates events with a KNOWN injected
effect, they flow through the same store/report pipeline as real sessions, and
the experiment summary recovers the effect — the finale of the judged demo.
Comment texts include PII-laden samples ON PURPOSE so the demo shows the
scrubber working ([SĐT], [ĐỊA CHỈ] visibly in the feed)."""

from __future__ import annotations

import random
import secrets
from datetime import timedelta
from typing import Any

from fastapi import APIRouter

from livelift.api import service
from livelift.api.schemas import DemoSeedOut, DemoSeedRequest
from livelift.api.service import StoreDep
from livelift.core.assigner import DesignParams
from livelift.core.features import build_ticks
from livelift.ingest.pii import scrub
from livelift.nlp.intent import classify_with_confidence
from livelift.sim.simulator import SimParams, simulate_session

router = APIRouter()

DEMO_PRODUCTS = [
    {
        "product_id": "P-SAP",
        "name": "Sáp thơm để xe hương cà phê",
        "category": "nhà cửa",
        "cost": 18000,
        "price": 45000,
        "stock": 120,
    },
    {
        "product_id": "P-BINH",
        "name": "Bình giữ nhiệt 500ml",
        "category": "nhà cửa",
        "cost": 42000,
        "price": 95000,
        "stock": 80,
    },
    {
        "product_id": "P-KHAN",
        "name": "Set 5 khăn lau đa năng",
        "category": "nhà cửa",
        "cost": 15000,
        "price": 39000,
        "stock": 200,
    },
]

DEMO_COMMENTS = [
    "giá bao nhiêu vậy shop",
    "chốt 1 bình màu đen nha",
    "size này dùng được cho bé không",
    "đắt quá giảm chút đi",
    "freeship không shop ơi",
    "0901234567 chốt cho em 2 hộp",  # PII on purpose — demo the scrubber
    "ship về Gò Vấp bao lâu tới",  # PII on purpose
    "hàng có sẵn không ạ",
    "mua 2 tặng 1 thật không",
    "khi nào tới lượt sản phẩm số 3",
    "chất liệu gì vậy shop",
    "lấy 1 set khăn nha",
    "mắc quá shop ơi",
    "giao COD được không",
    "bình này giữ nhiệt mấy tiếng",
]


def _seed_one_session(
    store: Any,
    rng: random.Random,
    duration_min: int,
    effect: float,
    seed: int,
    start_offset_ago_min: int,
    leave_live: bool = False,
) -> str:
    now = service.now_utc()
    start_ts = now - timedelta(minutes=start_offset_ago_min)
    session = store.create_session(
        {
            "session_id": service.new_id(),
            "platform": "sim" if not leave_live else "replay",
            "title": f"Phiên mô phỏng seed={seed}",
            "mode": "auto",
            "status": "planned",
            "planned_duration_min": duration_min,
            "host_id": "demo",
            "start_ts": None,
            "end_ts": None,
            "design": None,
            "created_at": now,
        }
    )
    session_id = session["session_id"]
    session, blocks = service.schedule_session(store, session, DesignParams(jitter_s=0), seed)
    session = service.start_session(store, session, start_ts)
    schedule = service.rebuild_schedule(session, store.get_blocks(session_id))
    out = simulate_session(schedule, SimParams(treatment_effect=effect), seed)

    horizon_s = duration_min * 60 if not leave_live else (now - start_ts).total_seconds()

    for tick in build_ticks(out.events, duration_min * 60, 30):
        if tick.bucket_start_s > horizon_s:
            break
        store.add_tick(
            session_id,
            {
                "ts_bucket": start_ts + timedelta(seconds=tick.bucket_start_s),
                "viewers": tick.viewers,
                "comment_rate": tick.comment_count * 2.0,  # per minute
                "like_rate": tick.like_count * 2.0,
                "click_count": tick.click_count,
                "pinned_product_id": None,
            },
        )

    products = [p["product_id"] for p in DEMO_PRODUCTS]
    for ev in out.events:
        if ev.ts_offset_s > horizon_s:
            continue
        if ev.kind == "click":
            store.add_click(
                session_id,
                {
                    "click_id": service.new_id(),
                    "block_id": None,
                    "ts": start_ts + timedelta(seconds=ev.ts_offset_s),
                    "product_id": rng.choice(products),
                    "shortlink_code": None,
                    "dedup_hash": None,
                },
            )

    comment_times = [
        e.ts_offset_s for e in out.events if e.kind == "comment" and e.ts_offset_s <= horizon_s
    ]
    for offset in comment_times[:150]:
        text = rng.choice(DEMO_COMMENTS)
        result = scrub(text)
        block = service.block_at_offset(store.get_blocks(session_id), offset)
        intent, intent_confidence = classify_with_confidence(result.text)
        store.add_comment(
            session_id,
            {
                "comment_id": service.new_id(),
                "session_id": session_id,
                "block_id": block["block_id"] if block else None,
                "ts": start_ts + timedelta(seconds=offset),
                "text_scrubbed": result.text,
                "pii_kinds": sorted({m.kind for m in result.matches}),
                "intent_label": intent,
                "intent_confidence": intent_confidence,
                "sentiment": None,
            },
        )

    for i, block in enumerate(store.get_blocks(session_id)):
        if block.get("assignment") != "ON" or block["start_offset_s"] > horizon_s:
            continue
        pin_ts = start_ts + timedelta(seconds=block["start_offset_s"] + 5)
        store.add_intervention(
            session_id,
            {
                "action_id": service.new_id(),
                "block_id": block["block_id"],
                "ts": pin_ts,
                "client_ts": None,
                "action_type": "pin",
                "product_id": products[i % len(products)],
                "source": "model",
                "inner_propensity": 0.5,
                "candidates_json": None,
                "executed": True,
                "override_reason": None,
                "seconds_since_last_switch": 5.0,
            },
        )
        # The demo stands in for the desk, so it must leave the SAME trail a
        # real desk leaves (gói Q3) — otherwise demo sessions quietly exercise
        # the pre-Q3 compliance path and the new one is never seen end to end.
        store.add_exposure_event(
            session_id,
            {
                "block_idx": block["block_index"],
                "event_type": "pin",
                "product_id": products[i % len(products)],
                "ts_utc": pin_ts,
                "ack_latency_ms": None,
                "source": "model",
            },
        )

    if not leave_live:
        store.update_session(
            session_id,
            {"status": "ended", "end_ts": start_ts + timedelta(minutes=duration_min)},
        )
    return session_id


@router.post("/demo/seed", response_model=DemoSeedOut)
def seed_demo(body: DemoSeedRequest, store: StoreDep) -> DemoSeedOut:
    rng = random.Random(4242)
    now = service.now_utc()
    # Shortlink codes must be unique per seed run: re-seeding is a normal user
    # action ("Xem thử ngay" can be clicked repeatedly) and a fixed code would
    # collide with the previous run's link (incident 27/08).
    run_tag = secrets.token_hex(2)
    product_ids = []
    codes = []
    for p in DEMO_PRODUCTS:
        stored = store.create_product({**p, "created_at": now})
        product_ids.append(stored["product_id"])
        link = store.create_shortlink(
            {
                "code": f"demo{run_tag}{len(codes)}",
                "product_id": p["product_id"],
                "session_id": None,
                "target_url": f"https://shop.example/{p['product_id']}",
                "created_at": now,
            }
        )
        codes.append(link["code"])

    session_ids = []
    for i in range(body.n_sessions):
        session_ids.append(
            _seed_one_session(
                store,
                rng,
                duration_min=body.duration_min,
                effect=body.effect,
                seed=1000 + i,
                start_offset_ago_min=(i + 1) * (body.duration_min + 30),
            )
        )
    replay_id = _seed_one_session(
        store,
        rng,
        duration_min=body.duration_min,
        effect=body.effect,
        seed=999,
        start_offset_ago_min=body.duration_min // 2,
        leave_live=True,
    )
    return DemoSeedOut(
        session_ids=session_ids,
        replay_session_id=replay_id,
        product_ids=product_ids,
        shortlink_codes=codes,
    )
