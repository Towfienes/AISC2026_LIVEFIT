"""MDE calculator: reproduce the plan's base numbers, then verify corrections."""

import pytest

from livelift.analysis.power import (
    PowerInputs,
    Scenario,
    blocks_in_session,
    mde_relative,
    scenario_table,
)


def base(cv, n, **kw):
    defaults = {
        "cv": cv, "n_blocks_total": n, "n_sessions": 30, "compliance": 1.0,
        "icc_session": 0.0, "resid_autocorr": 0.0, "burn_in_share": 0.0,
        "var_reduction_r2": 0.0,
    }
    defaults.update(kw)
    return PowerInputs(**defaults)


def test_reproduces_plan_base_case():
    """Plan doc §7.2: 650 blocks total (325/arm), CV=0.5 -> MDE ≈ 11%."""
    mde = mde_relative(base(cv=0.5, n=650))
    assert mde == pytest.approx(0.11, abs=0.01)


def test_reproduces_plan_cv08_row():
    mde = mde_relative(base(cv=0.8, n=650))
    assert mde == pytest.approx(0.176, abs=0.015)


def test_compliance_dilution_inflates_mde():
    full = mde_relative(base(0.5, 650))
    diluted = mde_relative(base(0.5, 650, compliance=0.5))
    assert diluted == pytest.approx(full * 2, rel=0.01)


def test_cluster_design_effect_inflates_mde():
    no_icc = mde_relative(base(0.5, 650))
    with_icc = mde_relative(base(0.5, 650, icc_session=0.1))
    # m = 650/30 ≈ 21.7 blocks/session -> deff ≈ 3.07 -> ×1.75
    assert with_icc / no_icc == pytest.approx(3.07**0.5, rel=0.02)


def test_variance_reduction_shrinks_mde():
    plain = mde_relative(base(0.5, 650))
    cupac = mde_relative(base(0.5, 650, var_reduction_r2=0.36))
    assert cupac == pytest.approx(plain * 0.8, rel=0.01)


def test_autocorrelation_inflates_mde():
    plain = mde_relative(base(0.5, 650))
    ac = mde_relative(base(0.5, 650, resid_autocorr=0.2))
    assert ac > plain


def test_degenerate_inputs():
    assert mde_relative(base(0.5, 2)) == float("inf")


def test_blocks_in_session_endpoint_double():
    # 90 min, 5-min blocks, doubled endpoints -> 16
    assert blocks_in_session(90, 5, True) == 16
    assert blocks_in_session(90, 5, False) == 18


def test_scenario_table_two_honest_scenarios():
    rows = scenario_table(
        [
            Scenario("không đối tác (tuần 6-11)", n_sessions=18, session_minutes=90, block_min=5),
            Scenario("có đối tác", n_sessions=28, session_minutes=90, block_min=5),
        ]
    )
    assert len(rows) == 6  # 2 scenarios × 3 CVs
    no_partner = [r for r in rows if r["scenario"].startswith("không")]
    partner = [r for r in rows if r["scenario"].startswith("có")]
    for a, b in zip(no_partner, partner, strict=True):
        assert a["mde_relative"] > b["mde_relative"]  # more data -> smaller MDE
    assert all(r["n_blocks_total"] == r["blocks_per_session"] * r["n_sessions"] for r in rows)
