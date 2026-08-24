"""Tick aggregation and block-outcome construction (E1-06)."""

from livelift.core.assigner.outer import DesignParams, generate_schedule
from livelift.core.features import Event, block_frame, build_ticks


def test_build_ticks_counts_and_carry_forward():
    events = [
        Event("viewer_count", 0, value=50),
        Event("comment", 5),
        Event("comment", 40),
        Event("like", 10),
        Event("click", 65, product_id="P1"),
        Event("viewer_count", 70, value=80),
        Event("pin", 20, product_id="P9"),
    ]
    ticks = build_ticks(events, session_duration_s=120, tick_s=30)
    assert len(ticks) == 4
    assert ticks[0].comment_count == 1
    assert ticks[0].like_count == 1
    assert ticks[0].viewers == 50
    assert ticks[1].comment_count == 1
    assert ticks[1].viewers == 50  # carried forward
    assert ticks[2].click_count == 1
    assert ticks[2].viewers == 80
    assert ticks[0].pinned_product_id == "P9"  # pin at 20s lands in bucket 0
    assert ticks[3].pinned_product_id == "P9"  # carried forward


def test_out_of_range_events_ignored():
    events = [Event("comment", -5), Event("comment", 999)]
    ticks = build_ticks(events, session_duration_s=60, tick_s=30)
    assert sum(t.comment_count for t in ticks) == 0


def test_block_frame_shapes_and_burn_in():
    schedule = generate_schedule(60, DesignParams(jitter_s=0), seed=1)
    # constant 100 viewers, one click every 10s
    events = [Event("viewer_count", t, value=100.0) for t in range(0, 3600, 30)]
    events += [Event("click", t + 0.5) for t in range(0, 3600, 10)]
    frame = block_frame(schedule, events, burn_in_s=60)
    assert len(frame) == len(schedule.measurement_blocks)
    for r in frame:
        # uniform click stream: y ≈ (0.1 click/s) / (100 viewers) * 1000 = 1.0
        assert 0.8 <= r.y <= 1.2, r
        assert r.exposure_viewer_s > 0
        assert r.assignment in ("ON", "OFF")
        assert r.z in (0, 1)
    # burn-in shrinks the analysis window: exposure < full block exposure
    full = block_frame(schedule, events, burn_in_s=0)
    assert frame[1].exposure_viewer_s < full[1].exposure_viewer_s


def test_block_frame_pre_covariates():
    schedule = generate_schedule(60, DesignParams(jitter_s=0), seed=2)
    events = [Event("viewer_count", t, value=60.0) for t in range(0, 3600, 30)]
    events += [Event("comment", t) for t in range(0, 3600, 6)]  # 10 comments/min
    frame = block_frame(schedule, events, burn_in_s=30)
    # skip the first block (no pre-window)
    for r in frame[1:]:
        assert 50 <= r.pre_viewers <= 70
        assert 8 <= r.pre_comment_rate <= 12


def test_zero_exposure_block_has_zero_outcome():
    schedule = generate_schedule(30, DesignParams(jitter_s=0, endpoint_double=False), seed=3)
    frame = block_frame(schedule, [], burn_in_s=0)
    assert all(r.y == 0.0 and r.exposure_viewer_s == 0.0 for r in frame)
