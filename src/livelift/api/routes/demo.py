"""Demo seeding: simulated finished sessions + a live replay session.

Feeds the Replay Engine (E6-06) and lets the whole stack demo with zero
external dependencies: the simulator generates events with a KNOWN injected
effect, they flow through the same store/report pipeline as real sessions, and
the DEMO-scope experiment summary (``/experiment/summary?env=demo``) recovers
the effect — the finale of the judged demo. Comment texts include PII-laden
samples ON PURPOSE so the demo shows the scrubber working ([SĐT], [ĐỊA CHỈ]
visibly in the feed).

IS_DEMO INVARIANT (gói DEMO-THẬT, 12/09/2026): every session born in this
module carries ``is_demo=True`` FROM CREATION — it is sample data, never a
broadcast that happened. That flag is what keeps demo numbers out of every
real scientific output (``/experiment/summary`` default env, NLP label
export) while leaving the sessions fully viewable, labeled, for demos and
practice. ``is_demo`` ≠ ``dry_run``: a dry run is a REAL session declared a
practice run; a demo session is data that was never real. Definitions:
PREREGISTRATION §8.2.

BỘ PHIÊN DEMO VÀNG (:func:`seed_demo_vang`): a deterministic (fixed-seed)
golden set covering ALL THREE result states — clear POSITIVE, NULL (CI
straddles 0), and NOT-ESTIMABLE — so every state of the results screens can
be demoed and screenshotted without waiting for real data, and without ever
glorifying only the pretty outcome (hard rule: all three states get equal
production value). CLI wrapper: ``scripts/seed_demo_vang.py``."""

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
    is_demo: bool = True,
    title: str | None = None,
) -> str:
    """Simulate one full session through the REAL store pipeline.

    ``is_demo`` defaults to True — every route/script in this module seeds
    SAMPLE data and must say so from creation (PREREGISTRATION §8.2). The
    False escape hatch exists ONLY for tests that need simulated stand-ins for
    real sessions to exercise the real-result analysis path; no production
    caller may pass it.
    """
    now = service.now_utc()
    start_ts = now - timedelta(minutes=start_offset_ago_min)
    session = store.create_session(
        {
            "session_id": service.new_id(),
            "platform": "sim" if not leave_live else "replay",
            "title": title or f"Phiên mô phỏng seed={seed}",
            "mode": "auto",
            "status": "planned",
            "planned_duration_min": duration_min,
            "host_id": "demo",
            "start_ts": None,
            "end_ts": None,
            "design": None,
            "created_at": now,
            # Dữ liệu mẫu được đánh dấu TỪ LÚC SINH — không có bước "gắn nhãn
            # sau" nào có thể quên (yêu cầu phản biện: demo không bao giờ lọt
            # vào kết quả thật).
            "is_demo": is_demo,
            "dry_run": False,
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


def _seed_products_and_links(store: Any) -> tuple[list[str], list[str]]:
    """Create the demo product catalog + one measurement shortlink each.

    Shortlink codes must be unique per seed run: re-seeding is a normal user
    action ("Xem thử ngay" can be clicked repeatedly) and a fixed code would
    collide with the previous run's link (incident 27/08). Products upsert, so
    re-running never errors.
    """
    now = service.now_utc()
    run_tag = secrets.token_hex(2)
    product_ids: list[str] = []
    codes: list[str] = []
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
    return product_ids, codes


@router.post("/demo/seed", response_model=DemoSeedOut)
def seed_demo(body: DemoSeedRequest, store: StoreDep) -> DemoSeedOut:
    rng = random.Random(4242)
    product_ids, codes = _seed_products_and_links(store)

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


# ---------------------------------------------------------------------------
# BỘ PHIÊN DEMO VÀNG — tất định, gọi đủ CẢ BA trạng thái kết quả
# ---------------------------------------------------------------------------

#: Seed cố định cho từng phiên vàng. Đổi một seed là đổi bộ demo — chỉ đổi có
#: chủ đích và chạy lại script để cập nhật docs/demo-vang.md.
VANG_DUONG = ((20261, 0.8, 90), (20262, 0.8, 90), (20263, 0.8, 90))
"""Cụm DƯƠNG rõ: hiệu ứng bơm 0.8 (nhấp ×1.8 trong khối BẬT), 90 phút — KTC
từng phiên phải loại 0 về phía dương."""

VANG_NULL = ((20271, 0.0, 90), (20272, 0.0, 90))
"""Cụm NULL: hiệu ứng bơm đúng 0, 90 phút — ước lượng được nhưng KTC phải
chứa 0. Trạng thái này được dàn dựng CÔNG PHU NGANG trạng thái dương (yêu cầu
phản biện khoa học: null là kết cục dễ xảy ra nhất, UI không được chỉ tôn
vinh kết quả đẹp)."""

VANG_THIEU = (20281, 0.0, 15)
"""Phiên CHƯA ĐỦ ĐIỀU KIỆN: 15 phút → 3 khối đo < ngưỡng 4 khối của báo cáo —
estimable=false kèm lý do tiếng Việt, đúng khoảnh khắc "hệ thống DÁM TỪ CHỐI
kết luận" của kịch bản trình giám khảo."""


class DemoVangStateError(RuntimeError):
    """Bộ demo vàng sinh ra KHÔNG đạt đúng trạng thái đã cam kết.

    Fail to đằng fail im: một bộ demo hứa "ba trạng thái" mà lệch trạng thái
    sẽ làm buổi demo kể sai câu chuyện — thà vỡ ngay lúc seed."""


def _trang_thai_ket_qua(kq: Any) -> str:
    """Phân loại một KetQuaThiNghiem vào đúng một trong ba trạng thái demo."""
    if not kq.estimable:
        return "thieu"
    if kq.ci_low is not None and kq.ci_high is not None and kq.ci_low > 0:
        return "duong"
    return "null"


def seed_demo_vang(store: Any) -> dict[str, Any]:
    """Seed bộ phiên DEMO VÀNG tất định (is_demo=True, seed cố định).

    Ba cụm — DƯƠNG rõ / NULL (KTC chứa 0) / CHƯA ĐỦ ĐIỀU KIỆN — để demo và
    chụp ảnh MỌI trạng thái của màn kết quả mà không phải chờ dữ liệu thật.
    Trạng thái của từng phiên được kiểm ngay tại đây qua đúng đường phân tích
    của ``/sessions/{id}/bao-cao`` (:func:`reports._bao_cao_ket_qua`); lệch
    trạng thái ⇒ :class:`DemoVangStateError`, không bao giờ trả về một bộ demo
    kể sai câu chuyện.

    Tất định: cùng seed ⇒ cùng ước lượng/KTC/trạng thái ở mọi lần chạy
    (session_id là UUID nên khác nhau — định danh không phải kết quả).
    CLI: ``python scripts/seed_demo_vang.py`` (ghi docs/demo-vang.md).
    """
    from livelift.api.routes.reports import _bao_cao_ket_qua

    rng = random.Random(20260)
    product_ids, codes = _seed_products_and_links(store)

    nhom: dict[str, list[str]] = {"duong": [], "null": [], "thieu": []}
    offset_ago_min = 18 * 60  # phiên vàng đầu tiên "phát" cách đây 18 giờ

    def _mot_phien(ten_nhom: str, seed: int, effect: float, duration: int, title: str) -> str:
        nonlocal offset_ago_min
        sid = _seed_one_session(
            store,
            rng,
            duration_min=duration,
            effect=effect,
            seed=seed,
            start_offset_ago_min=offset_ago_min,
            title=title,
        )
        offset_ago_min -= duration + 30  # phiên sau gần hiện tại hơn, không chồng lấn
        nhom[ten_nhom].append(sid)
        return sid

    for i, (seed, effect, duration) in enumerate(VANG_DUONG, 1):
        _mot_phien("duong", seed, effect, duration, f"Demo vàng · DƯƠNG rõ #{i}")
    for i, (seed, effect, duration) in enumerate(VANG_NULL, 1):
        _mot_phien("null", seed, effect, duration, f"Demo vàng · NULL (KTC chứa 0) #{i}")
    seed, effect, duration = VANG_THIEU
    _mot_phien("thieu", seed, effect, duration, "Demo vàng · CHƯA ĐỦ ĐIỀU KIỆN")

    ket_qua: dict[str, dict[str, Any]] = {}
    for ten_nhom, sids in nhom.items():
        for sid in sids:
            session = store.get_session(sid)
            kq = _bao_cao_ket_qua(session, store)
            thuc_te = _trang_thai_ket_qua(kq)
            if thuc_te != ten_nhom:
                raise DemoVangStateError(
                    f"Phiên vàng {session.get('title')!r} ({sid}) phải ở trạng thái "
                    f"'{ten_nhom}' nhưng đường phân tích trả về '{thuc_te}' "
                    f"(estimable={kq.estimable}, KTC=[{kq.ci_low}, {kq.ci_high}]). "
                    "Seed/hiệu ứng trong VANG_* cần chỉnh lại — không giao bộ demo lệch."
                )
            ket_qua[sid] = {
                "nhom": ten_nhom,
                "title": session.get("title"),
                "estimable": kq.estimable,
                "n_blocks": kq.n_blocks,
                "estimate": kq.estimate,
                "ci_low": kq.ci_low,
                "ci_high": kq.ci_high,
                "p_value": kq.p_value,
                "message": kq.message,
            }
    return {
        "nhom": nhom,
        "ket_qua": ket_qua,
        "product_ids": product_ids,
        "shortlink_codes": codes,
    }
