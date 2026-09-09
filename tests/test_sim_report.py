"""Gói P2: the SBC-style calibration grid and its report.

Two kinds of test here, and the second matters more than the first:

- unit tests of the pure statistics (``session_icc``, ``sbc_cell``,
  ``render_report``) against hand-made inputs;
- an **inverse self-validation**: a known bug is injected into the real
  estimation pipeline and the corresponding grid cell must turn RED, while the
  untouched pipeline turns GREEN. A green-only report proves nothing — it is
  equally consistent with "the pipeline is calibrated" and "the check cannot
  fail". This test is what separates those two.
"""

import numpy as np
import pytest
from scipy.stats import kstest

from livelift.analysis import estimators
from livelift.sim import validate as sim_validate
from livelift.sim.report import (
    dkw_band,
    ecdf_max_deviation,
    render_icc_map,
    render_report,
    sbc_cell,
    session_icc,
    session_icc_bootstrap_se,
    wilson_interval,
)
from livelift.sim.simulator import SimParams

# ---------------------------------------------------------------------------
# session_icc
# ---------------------------------------------------------------------------


def test_session_icc_is_one_when_all_variance_is_between_sessions():
    values = [1.0, 1.0, 1.0, 5.0, 5.0, 5.0, 9.0, 9.0, 9.0]
    groups = ["a", "a", "a", "b", "b", "b", "c", "c", "c"]
    assert session_icc(values, groups) == pytest.approx(1.0)


def test_session_icc_is_near_zero_without_clustering():
    rng = np.random.default_rng(0)
    values = rng.normal(size=600)
    groups = [f"s{i // 6}" for i in range(600)]
    assert abs(session_icc(values, groups)) < 0.10


def test_session_icc_may_be_negative_and_is_not_clamped():
    """The ANOVA estimator has no floor at zero. Clamping would turn sampling
    noise into a claim of "no clustering, exactly"."""
    values = [0.0, 10.0, 0.0, 10.0, 0.0, 10.0]
    groups = ["a", "a", "b", "b", "c", "c"]
    assert session_icc(values, groups) < 0


def test_session_icc_refuses_degenerate_input():
    assert np.isnan(session_icc([1.0, 2.0], ["a", "a"]))  # one group
    assert np.isnan(session_icc([1.0, 2.0], ["a", "b"]))  # one obs per group
    with pytest.raises(ValueError, match="cùng độ dài"):
        session_icc([1.0, 2.0], ["a"])


# ---------------------------------------------------------------------------
# session_icc_bootstrap_se — the SE that makes the published map readable
# ---------------------------------------------------------------------------


def test_bootstrap_se_resamples_whole_sessions_not_blocks():
    """The discriminating test between a CLUSTER bootstrap and a block one.

    On perfectly clustered data (zero within-session variance) every resample of
    whole sessions still has zero within-variance, so every replicate returns
    ICC = 1 exactly and the SE is 0. A bootstrap that resampled BLOCKS would mix
    values across sessions, break the clusters and report a positive SE — which
    is exactly the understated-dependence mistake this function exists to avoid.
    """
    values = [1.0, 1.0, 1.0, 5.0, 5.0, 5.0, 9.0, 9.0, 9.0]
    groups = ["a", "a", "a", "b", "b", "b", "c", "c", "c"]
    assert session_icc(values, groups) == pytest.approx(1.0)
    assert session_icc_bootstrap_se(values, groups, n_boot=50, seed=1) == 0.0


def test_bootstrap_se_is_positive_deterministic_and_shrinks_with_more_sessions():
    rng = np.random.default_rng(3)

    def clustered(n_sessions: int, blocks: int = 6) -> tuple[list[float], list[str]]:
        vals: list[float] = []
        grp: list[str] = []
        for s in range(n_sessions):
            level = rng.normal(0.0, 1.0)
            vals.extend((level + rng.normal(0.0, 1.0, size=blocks)).tolist())
            grp.extend([f"s{s}"] * blocks)
        return vals, grp

    v_small, g_small = clustered(20)
    v_large, g_large = clustered(200)
    se_small = session_icc_bootstrap_se(v_small, g_small, n_boot=200, seed=7)
    se_large = session_icc_bootstrap_se(v_large, g_large, n_boot=200, seed=7)

    assert se_small > 0
    # deterministic given the seed — a published "± SE" must be re-derivable
    assert session_icc_bootstrap_se(v_small, g_small, n_boot=200, seed=7) == se_small
    assert se_large < se_small, (se_small, se_large)


def test_bootstrap_se_refuses_degenerate_input():
    assert np.isnan(session_icc_bootstrap_se([1.0, 2.0], ["a", "a"], n_boot=10))  # one cluster
    with pytest.raises(ValueError, match="cùng độ dài"):
        session_icc_bootstrap_se([1.0, 2.0], ["a"], n_boot=10)
    with pytest.raises(ValueError, match="n_boot"):
        session_icc_bootstrap_se([1.0, 2.0], ["a", "b"], n_boot=1)


# ---------------------------------------------------------------------------
# building blocks
# ---------------------------------------------------------------------------


def test_wilson_interval_is_not_degenerate_at_the_boundary():
    lo, hi = wilson_interval(100, 100)
    assert hi == pytest.approx(1.0)
    assert 0.9 < lo < 1.0, "khoảng Wald sẽ cho [1,1] — đó chính là lý do dùng Wilson"


def test_wilson_interval_brackets_the_point_estimate():
    lo, hi = wilson_interval(95, 100)
    assert lo < 0.95 < hi


def test_ecdf_max_deviation_equals_the_scipy_ks_statistic():
    rng = np.random.default_rng(7)
    sample = rng.random(200)
    assert ecdf_max_deviation(sample) == pytest.approx(kstest(sample, "uniform").statistic)


def test_dkw_band_matches_massart_formula_and_shrinks_with_n():
    assert dkw_band(100) == pytest.approx(np.sqrt(np.log(40) / 200))
    assert dkw_band(1000) < dkw_band(100)


# ---------------------------------------------------------------------------
# sbc_cell
# ---------------------------------------------------------------------------


def _uniform_pvalues(n: int = 100) -> list[float]:
    """Deterministic, near-perfectly uniform p-values (mid-quantiles)."""
    return [(i + 0.5) / n for i in range(n)]


def _coverage_flags(n_covered: int, n: int = 100) -> list[int]:
    return [1] * n_covered + [0] * (n - n_covered)


def test_calibrated_cell_is_green():
    cell = sbc_cell(
        _uniform_pvalues(),
        _coverage_flags(95),
        [0.001] * 100,
        label="hiệu chuẩn tốt",
        truth_scale=1.0,
    )
    assert cell.ok
    assert cell.status == "XANH"
    assert cell.failures() == []
    assert cell.relative_bias == pytest.approx(0.001)


def test_non_uniform_pvalues_turn_the_cell_red():
    """The failure mode of an over-conservative test: p piles up near 1."""
    cell = sbc_cell(
        [0.9 + 0.001 * i for i in range(100)],
        _coverage_flags(95),
        [0.0] * 100,
        label="bảo thủ",
        truth_scale=1.0,
    )
    assert not cell.ok
    assert cell.ks_pvalue < 0.01
    assert cell.ecdf_max_diff > cell.ecdf_band
    assert any("đồng đều" in reason for reason in cell.failures())


def test_broken_coverage_turns_the_cell_red():
    cell = sbc_cell(
        _uniform_pvalues(),
        _coverage_flags(60),
        [0.0] * 100,
        label="phủ hụt",
        truth_scale=1.0,
    )
    assert not cell.ok
    assert any("độ phủ" in reason for reason in cell.failures())


def test_large_relative_bias_turns_the_cell_red():
    cell = sbc_cell(
        _uniform_pvalues(),
        _coverage_flags(95),
        [0.3] * 100,
        label="lệch",
        truth_scale=1.0,
    )
    assert not cell.ok
    assert cell.relative_bias == pytest.approx(0.30)
    assert any("lệch tương đối" in reason for reason in cell.failures())


def test_uniformity_is_skipped_where_no_null_holds():
    """An effect cell has p-values piled at zero BY DESIGN. Testing them for
    uniformity would fail a working pipeline, so the check is opt-out."""
    piled = [0.0005 * i for i in range(100)]
    red = sbc_cell(piled, _coverage_flags(95), [0.0] * 100, truth_scale=1.0)
    green = sbc_cell(
        piled, _coverage_flags(95), [0.0] * 100, truth_scale=1.0, check_uniformity=False
    )
    assert not red.ok
    assert green.ok
    assert green.rejection_rate > 0.5  # still reported, as power


def test_null_cell_reports_absolute_bias_instead_of_dividing_by_zero():
    """truth ≈ 0 has no denominator. A "+3400% bias" printed for a cell whose
    true effect is 1e-17 is a fabricated number, not a finding."""
    cell = sbc_cell(
        _uniform_pvalues(),
        _coverage_flags(95),
        [0.0001 * ((-1) ** i) for i in range(100)],
        label="A/A",
        truth_scale=0.0,
    )
    assert np.isnan(cell.relative_bias)
    assert np.isnan(cell.relative_mc_error)
    assert cell.ok


def test_null_cell_still_catches_a_systematic_offset():
    cell = sbc_cell(
        _uniform_pvalues(),
        _coverage_flags(95),
        [1.0 + 0.0001 * ((-1) ** i) for i in range(100)],
        label="A/A lệch",
        truth_scale=0.0,
    )
    assert not cell.ok
    assert any("tuyệt đối" in reason for reason in cell.failures())


def test_sbc_cell_refuses_inconsistent_or_empty_input():
    with pytest.raises(ValueError, match="cùng độ dài"):
        sbc_cell([0.1, 0.2], [1], [0.0, 0.0])
    with pytest.raises(ValueError, match="rỗng"):
        sbc_cell([], [], [])


# ---------------------------------------------------------------------------
# render_report
# ---------------------------------------------------------------------------


def test_render_report_marks_each_cell_and_lists_the_red_reasons():
    good = sbc_cell(
        _uniform_pvalues(), _coverage_flags(95), [0.0] * 100, label="ô tốt", truth_scale=1.0
    )
    bad = sbc_cell(
        _uniform_pvalues(), _coverage_flags(50), [0.0] * 100, label="ô hỏng", truth_scale=1.0
    )
    text = render_report([good, bad], header="# tiêu đề")

    assert text.startswith("# tiêu đề")
    assert "| ô tốt |" in text
    assert "| ô hỏng |" in text
    assert "**XANH**" in text
    assert "**ĐỎ**" in text
    assert "1/2 ô ĐỎ" in text
    assert "`ô hỏng`: độ phủ" in text
    # a green-only report says so explicitly rather than leaving the reader to
    # infer it from an absent section
    assert "Tất cả 1 ô XANH" in render_report([good])


def test_render_report_labels_the_coverage_confidence_level():
    cell = sbc_cell(
        _uniform_pvalues(),
        _coverage_flags(95),
        [0.0] * 100,
        label="x",
        truth_scale=1.0,
        coverage_confidence=0.99,
    )
    assert "Wilson 99%" in render_report([cell])


def test_render_icc_map_prints_every_measured_column():
    rows = sim_validate.measure_icc_map((0.0, 0.3), n_sessions=8, session_minutes=45, n_boot=25)
    text = render_icc_map(rows, header="# ánh xạ")

    assert text.startswith("# ánh xạ")
    assert "| 0.000 |" in text
    assert "| 0.300 |" in text
    # the column header names the knob that was actually swept — a table that
    # did not say which of the two knobs produced the ICC is unreadable
    assert "| `session_click_sigma` |" in text
    # the two diagnostic columns that separate the knobs must be in the table,
    # not left for the reader to assume
    assert "phương sai TRONG-phiên" in text
    assert "trung bình y" in text


def test_render_icc_map_refuses_to_mix_two_knobs_in_one_table():
    """A single table has a single first column. Mixing σ rows and frailty rows
    would print both under one heading and invite exactly the wrong reading."""
    rows = sim_validate.measure_icc_map((0.0,), n_sessions=6, session_minutes=45, n_boot=10)
    rows += sim_validate.measure_icc_map(
        (1.0,), knob="click_frailty_cv", n_sessions=6, session_minutes=45, n_boot=10
    )
    with pytest.raises(ValueError, match="MỘT knob"):
        render_icc_map(rows)


def test_measure_icc_row_refuses_a_knob_that_is_not_a_heterogeneity_knob():
    """Sweeping ``treatment_effect`` here would print a table labelled ICC that
    is really measuring the arm contrast."""
    with pytest.raises(ValueError, match="knob phải thuộc"):
        sim_validate.measure_icc_row(0.3, knob="treatment_effect", n_sessions=2)


# ---------------------------------------------------------------------------
# measure_icc_map — the σ → ICC map is a MEASUREMENT, so it needs a command
# ---------------------------------------------------------------------------


def test_icc_map_rows_share_one_world_so_only_the_knob_differs():
    """Every row re-uses ``master_seed``, hence the same session seeds.

    ``measurable`` depends on exposure (viewer-seconds) alone, and no click-side
    knob touches the world stream, so the number of analysed blocks must be
    IDENTICAL across rows. If it ever differs, the rows are being compared
    across different worlds and the map measures seed luck as well as the knob.
    """
    rows = sim_validate.measure_icc_map(
        (0.0, 0.06, 0.3), n_sessions=10, session_minutes=45, n_boot=20
    )
    assert [r.knob_value for r in rows] == [0.0, 0.06, 0.3]
    assert {r.knob for r in rows} == {"session_click_sigma"}
    assert len({r.n_blocks for r in rows}) == 1, [r.n_blocks for r in rows]
    assert len({r.n_sessions for r in rows}) == 1


def test_icc_map_moves_icc_without_moving_the_level_or_within_dispersion():
    """What the knob is FOR, measured on a small map rather than asserted.

    A large σ is used so 30 sessions suffice: the analytic expectation is
    ICC ≈ σ²/(σ² + within-CV²) and within-CV² ≈ 0.085, so σ=0.3 predicts ≈ 0.5
    against a baseline near 0.01. Level and within-session dispersion must stay
    put — those are the two ways a mean-1 knob can silently go wrong.
    """
    off, on = sim_validate.measure_icc_map((0.0, 0.3), n_sessions=30, session_minutes=60, n_boot=20)
    assert on.icc > off.icc + 0.15, (off.icc, on.icc)
    assert on.mean_y == pytest.approx(off.mean_y, rel=0.10)
    assert on.mean_within_var == pytest.approx(off.mean_within_var, rel=0.30)


def test_frailty_map_over_disperses_blocks_where_the_session_knob_does_not():
    """Both knobs travel the same ``measure_icc_row`` path and must still be
    told apart by the column the published table prints for exactly that
    purpose. Frailty raises the WITHIN-session variance; the σ row above does
    not. Level stays at 1 for both — they are mean-1 knobs."""
    off, frail = sim_validate.measure_icc_map(
        (0.0, 1.5), knob="click_frailty_cv", n_sessions=30, session_minutes=60, n_boot=20
    )
    assert frail.knob == "click_frailty_cv"
    assert frail.mean_within_var > off.mean_within_var * 1.15, (
        off.mean_within_var,
        frail.mean_within_var,
    )
    assert frail.mean_y == pytest.approx(off.mean_y, rel=0.10)


# ---------------------------------------------------------------------------
# ValidationResult -> cell wiring
# ---------------------------------------------------------------------------


def test_run_validation_exposes_the_per_replication_vectors():
    """Aggregates cannot be tested for uniformity — the raw vectors must travel
    with the summary, one entry per replication."""
    res = sim_validate.run_validation(
        n_reps=3,
        n_sessions_per_rep=2,
        session_minutes=30,
        sim_params=SimParams(treatment_effect=0.0),
        n_draws=40,
        master_seed=5,
    )
    for vec in (res.p_values, res.coverage_flags, res.errors, res.truths, res.estimates):
        assert len(vec) == 3
    assert res.ci_coverage == pytest.approx(sum(res.coverage_flags) / 3)
    assert res.errors == tuple(e - t for e, t in zip(res.estimates, res.truths, strict=True))


def test_untestable_replication_counts_as_a_coverage_miss_not_a_free_pass():
    """``estimable=False`` gives a NaN p and a NaN interval. The p is excluded
    from the uniformity check (it carries no information), but the coverage flag
    is 0: "no interval" is a miss, never a silent success."""
    res = sim_validate.ValidationResult(
        n_reps=4,
        n_sessions_per_rep=1,
        mean_estimate=0.0,
        mean_true_effect=0.0,
        relative_bias=0.0,
        ci_coverage=0.75,
        rejection_rate=0.0,
        p_values=(0.2, 0.6, float("nan"), 0.9),
        coverage_flags=(1, 1, 0, 1),
        errors=(0.0, 0.0, 0.0, 0.0),
        truths=(0.0, 0.0, 0.0, 0.0),
        estimates=(0.0, 0.0, 0.0, 0.0),
    )
    cell = res.to_cell("ô có lần không ước lượng được", check_uniformity=True)
    assert cell.n_reps == 4
    assert cell.coverage == pytest.approx(0.75)
    assert cell.truth_scale == 0.0
    assert np.isnan(cell.relative_bias)


def test_default_grid_pairs_every_icc_with_every_effect():
    specs = sim_validate.default_grid(sigmas=(0.0, 0.06), effects=(0.0, 0.3))
    assert len(specs) == 4
    assert [s.sim_params.session_click_sigma for s in specs] == [0.0, 0.0, 0.06, 0.06]
    assert [s.sim_params.treatment_effect for s in specs] == [0.0, 0.3, 0.0, 0.3]
    # uniformity is only expected where the sharp null actually holds
    assert [s.uniformity_expected for s in specs] == [True, False, True, False]


# ---------------------------------------------------------------------------
# Inverse self-validation — the report must be able to go red on a real bug
# ---------------------------------------------------------------------------


_SELF_CHECK_SPEC = sim_validate.GridSpec(
    label="tự thẩm định A/A",
    sim_params=SimParams(treatment_effect=0.0),
    n_reps=40,
    n_sessions_per_rep=3,
    session_minutes=60,
    n_draws=200,
    master_seed=31337,
)


@pytest.mark.slow
def test_intact_pipeline_gives_a_green_cell():
    """Positive control for the test below: same seed, same cell, no injection."""
    cell = sim_validate.run_grid_cell(_SELF_CHECK_SPEC)
    assert cell.ok, f"{cell.label}: {cell.failures()}"


@pytest.mark.slow
def test_injected_statistic_mismatch_gives_a_red_cell(monkeypatch):
    """Known bug: the OBSERVED statistic loses its studentization while the
    reference draws keep theirs.

    This is the realistic shape of a "turn off studentization" mistake — the two
    code paths that must agree stop agreeing — and it is the version that is
    actually detectable here. Dropping studentization on BOTH sides would not
    be: a randomization test is exact under the sharp null for any statistic, so
    an A/A cell would stay uniform and the injection would prove nothing.

    With only the observed side de-studentized, |t_obs| is on the scale of a
    click-rate difference (~0.01) while the reference draws are on the t scale
    (~1), so almost every draw looks more extreme and the p-values pile up at 1.
    The cell must go RED on uniformity.
    """
    monkeypatch.setattr(estimators, "studentized_stat", estimators.diff_in_means)

    cell = sim_validate.run_grid_cell(_SELF_CHECK_SPEC)

    assert not cell.ok, "lỗi đã tiêm mà ô vẫn XANH — cổng SBC không có răng"
    assert not cell.uniformity_ok
    assert cell.ks_pvalue < 0.01
    assert any("đồng đều" in reason for reason in cell.failures())
