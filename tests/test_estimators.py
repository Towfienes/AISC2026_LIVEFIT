"""Estimator unit tests on synthetic data with known structure (E3-06/07).

Fast checks here; full Monte-Carlo calibration lives in test_sim_validation.py
(marked slow).
"""

import ast
import random
from pathlib import Path

import numpy as np
import pytest

from livelift.analysis.estimators import (
    analyze_outer,
    cuped_adjust,
    diff_in_means,
    ht_effect,
    late_wald,
    ols_fe_lin,
    randomization_test,
    studentized_stat,
)
from livelift.core.assigner.outer import DesignParams, draw_assignments


def _make_data(n_sessions=8, blocks_per=12, tau=0.0, seed=0):
    """Blocks with session random effects; treatment adds tau."""
    rng = np.random.default_rng(seed)
    py_rng = random.Random(seed)
    ys, zs, sids, phases = [], [], [], []
    for s in range(n_sessions):
        sess_effect = rng.normal(0, 0.5)
        ph = ["early", "mid", "late"][0:3] * (blocks_per // 3)
        ph = (ph + ["mid"] * blocks_per)[:blocks_per]
        arms, _ = draw_assignments(ph, py_rng)
        for i in range(blocks_per):
            z = 1 if arms[i] == "ON" else 0
            y = 5.0 + sess_effect + rng.normal(0, 1.0) + tau * z
            ys.append(y)
            zs.append(z)
            sids.append(f"s{s}")
            phases.append(ph[i])
    return np.array(ys), np.array(zs), np.array(sids), phases


def test_diff_and_ht_agree_at_half_propensity():
    y, z, _, _ = _make_data(tau=1.0, seed=1)
    d = diff_in_means(y, z)
    # HT with p=0.5 estimates the same contrast up to arm-imbalance weighting
    h = ht_effect(y, z, 0.5)
    assert d == pytest.approx(1.0, abs=0.5)
    assert h == pytest.approx(d, abs=0.6)


def test_ht_is_algebraically_identical_to_diff_in_means_at_constant_p():
    """Review 06/09: at CONSTANT p the Hájek weights collapse to the plain arm
    means, so ht_effect ≡ diff_in_means (any constant p, not just 0.5). It is
    therefore NOT a second independent estimator and the API report no longer
    publishes it next to the primary number (PREREGISTRATION §5b)."""
    y, z, _, _ = _make_data(tau=1.0, seed=9)
    d = diff_in_means(y, z)
    for p in (0.5, 0.3, 0.7):
        assert ht_effect(y, z, p) == pytest.approx(d, rel=1e-12, abs=1e-12)


def test_studentized_stat_sign_and_scale():
    y = np.array([1.0, 1.1, 0.9, 5.0, 5.2, 4.9])
    z = np.array([0, 0, 0, 1, 1, 1])
    t = studentized_stat(y, z)
    assert t > 5


def test_randomization_test_null_uniform_p():
    """Under the null, p-values should not concentrate near zero."""
    ps = []
    for seed in range(20):
        y, z, sids, phases = _make_data(tau=0.0, seed=seed)
        p, _ = randomization_test(y, z, sids, phases, n_draws=300, seed=seed)
        ps.append(p)
    assert min(ps) > 0.001
    assert sum(p < 0.05 for p in ps) <= 4  # ~1 expected, allow noise


def test_randomization_test_detects_large_effect():
    y, z, sids, phases = _make_data(tau=2.0, seed=3)
    p, _ = randomization_test(y, z, sids, phases, n_draws=500, seed=3)
    assert p < 0.01


def test_analyze_outer_ci_covers_truth():
    y, z, sids, phases = _make_data(tau=1.0, seed=4)
    res = analyze_outer(y, z, sids, phases, n_draws=400, seed=4)
    assert res.ci_low < 1.0 < res.ci_high
    assert res.ci_low < res.estimate < res.ci_high
    assert res.n_blocks == len(y)
    assert res.n_on + res.n_off == len(y)


def test_ols_fe_lin_removes_session_confounding():
    """Session effects correlated with nothing here, but FE must not bias tau."""
    y, z, sids, phases = _make_data(tau=1.5, seed=5)
    cov = np.random.default_rng(5).normal(size=(len(y), 1))
    res = ols_fe_lin(y, z, sids, covariates=cov)
    assert res.estimate == pytest.approx(1.5, abs=0.4)
    assert res.se_cluster > 0
    assert res.n_clusters == 8


def test_late_wald_recovers_effect_under_noncompliance():
    rng = np.random.default_rng(6)
    n = 4000
    z = rng.integers(0, 2, n)
    # 80% compliance in Z=1, 5% always-takers in Z=0
    d = np.where(z == 1, rng.random(n) < 0.8, rng.random(n) < 0.05).astype(int)
    y = 2.0 * d + rng.normal(0, 1, n)
    res = late_wald(y, z, d)
    assert res.first_stage == pytest.approx(0.75, abs=0.05)
    assert res.late == pytest.approx(2.0, abs=0.3)
    assert res.itt == pytest.approx(1.5, abs=0.3)


def test_late_wald_refuses_weak_first_stage():
    rng = np.random.default_rng(7)
    n = 500
    z = rng.integers(0, 2, n)
    d = rng.integers(0, 2, n)  # no relation to z
    y = rng.normal(size=n)
    res = late_wald(y, z, d)
    assert np.isnan(res.late)
    assert not np.isnan(res.itt)


def test_cuped_reduces_variance_with_correlated_covariate():
    rng = np.random.default_rng(8)
    x = rng.normal(size=2000)
    y = 3.0 + 0.8 * x + rng.normal(0, 0.5, 2000)
    y_adj, vr = cuped_adjust(y, x)
    assert vr > 0.5
    assert y_adj.mean() == pytest.approx(y.mean(), abs=1e-9)


def test_cuped_no_variance_no_crash():
    y = np.ones(10)
    x = np.ones(10)
    y_adj, vr = cuped_adjust(y, x)
    assert vr == 0.0
    assert np.allclose(y_adj, y)


# ---------------------------------------------------------------------------
# Audit 30/08 — degenerate designs must be REFUSED, never reported
# ---------------------------------------------------------------------------


def _degenerate(n_on=1, n_off=5, seed=0):
    """A session where one arm has too few blocks to studentize."""
    rng = np.random.default_rng(seed)
    z = np.array([1] * n_on + [0] * n_off)
    y = rng.normal(5.0, 1.0, size=len(z))
    sids = np.array(["s0"] * len(z))
    phases = ["early", "mid", "late"] * len(z)
    return y, z, sids, phases[: len(z)]


def test_single_block_arm_is_not_estimable():
    """FATAL (audit 30/08): with one arm below 2 blocks the studentized
    statistic is NaN. Every NaN comparison is False, so the p-value used to
    collapse to its floor and the Fisher CI to zero width — i.e. pure noise was
    reported as 'p < 0.001, significant'."""
    y, z, sids, phases = _degenerate(n_on=1, n_off=5)
    res = analyze_outer(y, z, sids, phases, n_draws=200, seed=1)
    assert not res.estimable
    assert np.isnan(res.p_value)
    assert np.isnan(res.ci_low)
    assert np.isnan(res.ci_high)
    assert not res.significant
    assert res.reason is not None
    assert "khối" in res.reason


def test_all_one_arm_is_not_estimable():
    y, z, sids, phases = _degenerate(n_on=0, n_off=6)
    res = analyze_outer(y, z, sids, phases, n_draws=200, seed=2)
    assert not res.estimable
    assert not res.significant


def test_significant_is_false_when_a_bound_is_unbounded():
    """An unidentified bound (-inf/+inf) must never read as significance."""
    from livelift.analysis.estimators import RandomizationResult

    res = RandomizationResult(
        estimate=0.5,
        estimate_ht=0.5,
        p_value=0.2,
        ci_low=0.1,
        ci_high=float("inf"),
        n_blocks=10,
        n_on=5,
        n_off=5,
        n_draws=100,
    )
    assert not res.significant


def test_identical_outcomes_do_not_produce_a_spurious_rejection():
    """SERIOUS (audit 30/08): an exact `se == 0` check missed floating-point
    dust, giving t ~ 1e16 and a false rejection. Constant outcomes carry no
    evidence of an effect."""
    y = np.full(12, 3.3)
    z = np.array([1, 0] * 6)
    sids = np.array(["s0"] * 12)
    phases = ["early", "mid", "late"] * 4
    res = analyze_outer(y, z, sids, phases, n_draws=300, seed=3)
    assert res.estimable
    assert not res.significant
    assert res.p_value > 0.05


def test_degenerate_redraws_are_dropped_not_counted_as_zero():
    """Degenerate reference draws (NaN) must leave the reference set, not be
    mapped to 0.0 — counting them as 'not extreme' biases p downward."""
    from livelift.analysis.estimators import _batch_studentized

    y = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    zmat = np.array(
        [
            [1, 1, 1, 0, 0, 0],  # fine
            [1, 0, 0, 0, 0, 0],  # one ON block -> undefined
            [0, 0, 0, 0, 0, 0],  # no ON blocks -> undefined
        ],
        dtype=np.int8,
    )
    t = _batch_studentized(y, zmat)
    assert np.isfinite(t[0])
    assert np.isnan(t[1])
    assert np.isnan(t[2])


# ---------------------------------------------------------------------------
# Review 06/09 — redraws must run the SAVED design, not the default one
# ---------------------------------------------------------------------------


def _phase_counts(zmat, phases, phase):
    idx = [i for i, ph in enumerate(phases) if ph == phase]
    n_on = zmat[:, idx].sum(axis=1)
    return n_on, len(idx) - n_on


def test_redraws_respect_saved_min_per_arm_per_phase():
    """A session persisted with min_per_arm_per_phase=3 must be re-drawn under
    that constraint — redrawing the default (2) builds the reference
    distribution of a design nobody ran."""
    from livelift.analysis.estimators import _redraw_matrix

    phases = ["early"] * 6 + ["mid"] * 6 + ["late"] * 6
    sids = np.array(["s0"] * len(phases))
    params = {"s0": DesignParams(min_per_arm_per_phase=3)}

    zmat = _redraw_matrix(sids, phases, n_draws=200, seed=11, design_params=params)
    for ph in ("early", "mid", "late"):
        n_on, n_off = _phase_counts(zmat, phases, ph)
        assert (n_on >= 3).all(), f"redraw vi phạm ràng buộc ≥3 BẬT ở {ph}"
        assert (n_off >= 3).all(), f"redraw vi phạm ràng buộc ≥3 TẮT ở {ph}"

    # Control: the DEFAULT design (min 2) does violate ≥3 in some redraws, so
    # the assertion above genuinely distinguishes the two designs.
    zmat_default = _redraw_matrix(sids, phases, n_draws=200, seed=11)
    violates = False
    for ph in ("early", "mid", "late"):
        n_on, n_off = _phase_counts(zmat_default, phases, ph)
        violates = violates or bool((n_on < 3).any() or (n_off < 3).any())
    assert violates, "thiết kế mặc định lẽ ra phải vi phạm ≥3 — test mất khả năng phân biệt"


def test_redraws_enforce_transition_balance_of_saved_design():
    """Research 08/09: the default design now carries the transition-balance
    acceptance rule, so every RI redraw must satisfy it too — and a session
    persisted with min_transition_pairs=0 (pre-08/09 design) must be redrawn
    WITHOUT it, or the reference distribution belongs to a design nobody ran."""
    from livelift.analysis.estimators import _redraw_matrix

    phases = ["early"] * 6 + ["mid"] * 6 + ["late"] * 6
    sids = np.array(["s0"] * len(phases))

    def pair_counts(row):
        n_on_on = sum(1 for a, b in zip(row, row[1:], strict=False) if a == b == 1)
        n_off_off = sum(1 for a, b in zip(row, row[1:], strict=False) if a == b == 0)
        return n_on_on, n_off_off

    zmat = _redraw_matrix(sids, phases, n_draws=200, seed=21)
    for row in zmat:
        n_on_on, n_off_off = pair_counts(row.tolist())
        assert n_on_on >= 3, "redraw vi phạm ràng buộc cặp (BẬT,BẬT)"
        assert n_off_off >= 3, "redraw vi phạm ràng buộc cặp (TẮT,TẮT)"
        assert abs(n_on_on - n_off_off) <= 1

    # Control: the pre-08/09 design (no transition constraint) does violate it
    # in some redraws, so the assertion above genuinely distinguishes the two.
    params = {"s0": DesignParams(min_transition_pairs=0)}
    zmat_old = _redraw_matrix(sids, phases, n_draws=200, seed=21, design_params=params)
    violates = any(
        (lambda c: c[0] < 3 or c[1] < 3 or abs(c[0] - c[1]) > 1)(pair_counts(row.tolist()))
        for row in zmat_old
    )
    assert violates, "thiết kế cũ lẽ ra phải vi phạm — test mất khả năng phân biệt"


def test_randomization_test_threads_design_params_over_full_schedule():
    """The reports path (full schedule + analyzed mask) must also redraw under
    the saved per-session design."""
    y, z, sids, phases = _make_data(n_sessions=1, blocks_per=18, tau=0.0, seed=12)
    params = {"s0": DesignParams(min_per_arm_per_phase=3)}
    _, zmat = randomization_test(
        y,
        z,
        sids,
        phases,
        n_draws=100,
        seed=12,
        all_phases=phases,
        all_session_ids=sids,
        analyzed_mask=np.ones(len(y), dtype=bool),
        design_params=params,
    )
    for ph in set(phases):
        n_on, n_off = _phase_counts(zmat, phases, ph)
        required = min(3, phases.count(ph) // 2)
        assert (n_on >= required).all()
        assert (n_off >= required).all()


@pytest.mark.slow
def test_null_false_positive_rate_is_nominal_on_short_sessions():
    """End-to-end guard on the exact scenario the audit used: 30-minute null
    sessions. Before the fix 52% of them were declared significant."""
    from livelift.core.assigner.outer import DesignParams, generate_schedule
    from livelift.core.features import block_frame
    from livelift.sim.simulator import SimParams, simulate_session

    sig = tested = 0
    for seed in range(120):
        sched = generate_schedule(30, DesignParams(), seed)
        out = simulate_session(sched, SimParams(treatment_effect=0.0), seed)
        frame = block_frame(sched, out.events, burn_in_s=60)
        y = np.array([r.y for r in frame])
        z = np.array([r.z for r in frame])
        res = analyze_outer(
            y,
            z,
            np.array(["s0"] * len(y)),
            [r.phase for r in frame],
            n_draws=299,
            seed=seed,
        )
        if not res.estimable:
            continue
        tested += 1
        sig += res.significant
    assert tested >= 30, f"quá ít phiên kiểm định được ({tested})"
    rate = sig / tested
    assert rate <= 0.20, f"tỷ lệ dương tính giả {rate:.1%} — kiểm định sai hiệu chỉnh"


# ---------------------------------------------------------------------------
# Gói P5a (08/09) — tách module: refactor CƠ HỌC, API công khai phải còn nguyên
# ---------------------------------------------------------------------------


def test_moved_symbols_are_the_same_object_from_both_paths():
    """`estimators` chỉ RE-EXPORT, không giữ bản sao.

    Nếu tách nhầm thành hai bản định nghĩa song song thì mọi test hiện có vẫn
    xanh, nhưng sửa một bên sẽ không tới bên kia — kiểu hỏng âm thầm đắt nhất
    của một lần refactor. So sánh danh tính (`is`) bắt đúng chuyện đó.
    """
    from livelift.analysis import adjust, estimators, robust

    assert estimators.cuped_adjust is adjust.cuped_adjust
    assert estimators.ols_fe_lin is robust.ols_fe_lin
    assert estimators.OLSResult is robust.OLSResult


def test_public_api_of_estimators_survives_the_split():
    """Mọi tên công khai trước khi tách vẫn import được từ `estimators`."""
    from livelift.analysis import estimators

    expected = {
        "MIN_BLOCKS_PER_ARM",
        "LATEResult",
        "OLSResult",
        "RandomizationResult",
        "analyze_outer",
        "cuped_adjust",
        "diff_in_means",
        "ht_effect",
        "late_wald",
        "ols_fe_lin",
        "randomization_ci",
        "randomization_test",
        "studentized_stat",
    }
    missing = expected - set(dir(estimators))
    assert not missing, f"API công khai bị mất sau khi tách: {sorted(missing)}"
    assert set(estimators.__all__) == expected


def test_split_moved_only_the_intended_families():
    """Kiểm định chính Ở NGUYÊN `estimators` (giảm rủi ro trước khóa prereg);
    chỉ hiệu chỉnh hiệp biến và phương sai robust được dời đi."""
    from livelift.analysis import estimators

    for fn in (
        estimators.diff_in_means,
        estimators.ht_effect,
        estimators.studentized_stat,
        estimators.randomization_test,
        estimators.randomization_ci,
        estimators.analyze_outer,
        estimators.late_wald,
    ):
        assert fn.__module__ == "livelift.analysis.estimators", (
            f"{fn.__name__} đã bị dời khỏi estimators — P5a chỉ được tách CUPED/OLS"
        )
    assert estimators.cuped_adjust.__module__ == "livelift.analysis.adjust"
    assert estimators.ols_fe_lin.__module__ == "livelift.analysis.robust"
    assert estimators.OLSResult.__module__ == "livelift.analysis.robust"


def test_moved_functions_behave_identically_through_either_path():
    """Refactor cơ học: gọi qua tên cũ và tên mới cho ra CÙNG con số."""
    from livelift.analysis import adjust, estimators, robust

    y, z, sids, _ = _make_data(tau=1.2, seed=31)
    x = np.arange(len(y), dtype=float)  # hiệp biến tất định theo lịch (§5c)

    y_old, vr_old = estimators.cuped_adjust(y, x)
    y_new, vr_new = adjust.cuped_adjust(y, x)
    assert np.array_equal(y_old, y_new)
    assert vr_old == vr_new

    old = estimators.ols_fe_lin(y, z, sids)
    new = robust.ols_fe_lin(y, z, sids)
    assert old == new


def test_carryover_module_is_a_placeholder_only():
    """`carryover.py` mới chỉ là CHỖ ĐẶT cho API dự kiến — chưa cài gì.

    Một hàm carryover xuất hiện ở đây phải đi kèm nghiên cứu + test riêng
    (HARNESS §4), không được lọt vào nhờ một lần refactor.
    """
    from livelift.analysis import carryover

    assert carryover.__all__ == []
    doc = carryover.__doc__ or ""
    for name in ("ht_lag1", "carryover_gate", "impulse_response"):
        assert not hasattr(carryover, name), (
            f"{name} đã được cài đặt — cần nghiên cứu + test riêng, không thuộc P5a"
        )
        assert name in doc, f"docstring phải nêu API dự kiến {name}"


def test_new_modules_never_import_back_from_estimators():
    """Cạnh phụ thuộc chỉ đi MỘT CHIỀU: estimators → {adjust, robust, carryover}.

    Đây đúng là thứ P5a mua được: việc sắp tới (P3 CUPED-mv, P4 wild bootstrap /
    ICS, C2/C3 carryover) sửa module mới mà KHÔNG phải mở lại file chứa kiểm
    định chính. Một `from .estimators import ...` lọt vào ba file này thì vừa
    tạo import vòng, vừa xóa sạch tính cách ly đó — và nó sẽ lọt êm vì mọi test
    khác vẫn xanh. Quét tĩnh bằng `ast` nên bắt được cả import đặt trong thân
    hàm, chỗ mà việc thử `import` lúc chạy test không nhìn thấy.
    """
    src = Path(__file__).resolve().parents[1] / "src" / "livelift" / "analysis"
    for name in ("adjust", "robust", "carryover"):
        path = src / f"{name}.py"
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            targets: list[str] = []
            if isinstance(node, ast.ImportFrom):
                # `from .estimators import x` và `from . import estimators`
                targets.append(node.module or "")
                targets.extend(a.name for a in node.names)
            elif isinstance(node, ast.Import):
                targets.extend(a.name for a in node.names)
            for target in targets:
                assert target.split(".")[-1] != "estimators", (
                    f"{name}.py import ngược về estimators — P5a tách ra chính là "
                    f"để module mới không phụ thuộc file kiểm định chính"
                )
