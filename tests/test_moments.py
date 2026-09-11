"""Spike detector thuần (core.moments) — biên rõ ràng, không suy diễn từ chuỗi ngắn."""

from __future__ import annotations

import pytest

from livelift.core.moments import DEFAULT_WINDOW, detect_comment_spikes


def _flat(n: int, rate: float = 4.0, step: float = 30.0) -> list[tuple[float, float]]:
    return [(i * step, rate) for i in range(n)]


def test_empty_series_has_no_moments():
    assert detect_comment_spikes([]) == []


def test_series_shorter_than_window_declares_nothing():
    """Chuỗi ≤ window không đủ lịch sử làm nền — trả rỗng để caller TUYÊN BỐ
    thiếu, tuyệt đối không hạ ngưỡng để nặn ra khoảnh khắc."""
    assert detect_comment_spikes(_flat(DEFAULT_WINDOW)) == []
    assert detect_comment_spikes(_flat(3)) == []


def test_constant_series_has_no_spikes():
    assert detect_comment_spikes(_flat(40, rate=8.0)) == []


def test_single_clear_spike_detected_with_baseline_and_ratio():
    buckets = _flat(12) + [(360.0, 20.0)]
    moments = detect_comment_spikes(buckets)
    assert len(moments) == 1
    m = moments[0]
    assert m.offset_s == 360.0
    assert m.rate == 20.0
    assert m.baseline == 4.0  # median 10 bucket trước đó
    assert m.ratio == pytest.approx(5.0)


def test_small_absolute_rates_never_flagged():
    """0 → 2 tin/phút là gấp vô hạn lần nền nhưng vô nghĩa: sàn tuyệt đối
    min_rate chặn nhiễu trên phiên vắng."""
    buckets = _flat(15, rate=0.0) + [(450.0, 4.0)]  # 4 < min_rate=6
    assert detect_comment_spikes(buckets) == []


def test_burst_out_of_silence_qualifies_with_ratio_none():
    buckets = _flat(15, rate=0.0) + [(450.0, 12.0)]
    moments = detect_comment_spikes(buckets)
    assert len(moments) == 1
    assert moments[0].baseline == 0.0
    assert moments[0].ratio is None  # không chia cho 0, không bịa tỷ lệ


def test_adjacent_spike_buckets_merge_into_one_moment_at_peak():
    """Một đợt trào 90 giây là MỘT khoảnh khắc (đỉnh), không phải ba dòng."""
    buckets = _flat(12) + [(360.0, 20.0), (390.0, 25.0), (420.0, 18.0), (450.0, 4.0)]
    moments = detect_comment_spikes(buckets)
    assert len(moments) == 1
    assert moments[0].offset_s == 390.0
    assert moments[0].rate == 25.0


def test_peak_first_surge_still_merges_trailing_buckets():
    """Đỉnh đứng ĐẦU đợt trào: các bucket sau vẫn phải nhập vào cùng khoảnh
    khắc (run được nối theo bucket cuối, không theo offset của đỉnh)."""
    buckets = _flat(12) + [(360.0, 30.0), (390.0, 20.0), (420.0, 18.0), (450.0, 4.0)]
    moments = detect_comment_spikes(buckets)
    assert len(moments) == 1
    assert moments[0].offset_s == 360.0
    assert moments[0].rate == 30.0


def test_top_k_limits_and_orders_by_rate():
    buckets = _flat(12)
    # ba spike tách rời nhau bởi các bucket nền
    for base_offset, rate in ((360.0, 20.0), (600.0, 30.0), (900.0, 15.0)):
        buckets.append((base_offset, rate))
        buckets.extend((base_offset + 30.0 * (i + 1), 4.0) for i in range(5))
    moments = detect_comment_spikes(sorted(buckets), top_k=2)
    assert [m.rate for m in moments] == [30.0, 20.0]


def test_unsorted_input_is_sorted_internally():
    buckets = _flat(12) + [(360.0, 20.0)]
    shuffled = list(reversed(buckets))
    assert detect_comment_spikes(shuffled) == detect_comment_spikes(buckets)


def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window"):
        detect_comment_spikes(_flat(20), window=0)


def test_top_k_zero_returns_empty():
    assert detect_comment_spikes(_flat(12) + [(360.0, 20.0)], top_k=0) == []
