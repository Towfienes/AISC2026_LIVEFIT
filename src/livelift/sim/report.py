"""Pure statistics for the simulation-validation report (gói P2 — SKELETON).

What this module is for
-----------------------
The calibration gates in ``tests/test_sim_validation.py`` answer one question
at a time ("is the A/A rate alpha at the default settings?"). A referee asks a
harder one: *over the grid of worlds the design might actually meet* — with and
without outcome clustering, at zero effect and at the MDE — does the pipeline
stay calibrated everywhere? That is a Simulation-Based Calibration study in the
sense of Talts et al. (arXiv:1804.06788) and Modrák et al. (arXiv:2211.02383),
adapted from a Bayesian rank histogram to the frequentist quantities this
project actually pre-registers:

- **uniformity** of the randomization p-value under the null (Talts' rank
  uniformity, specialised: a valid test has U(0,1) p-values under H0);
- **coverage** of the Fisher confidence interval;
- **bias** of the point estimate against the CRN ground truth.

:func:`sbc_cell` reduces one grid cell to those three verdicts;
:func:`render_report` lays the cells out as a markdown table. Both are pure —
no simulation, no I/O — so they can be unit-tested against hand-made inputs,
including the deliberately broken ones that prove a red cell is reachable
(``tests/test_sim_report.py``).

The module also holds the clustering diagnostics the grid's ICC axis is defined
by — :func:`session_icc`, its cluster-bootstrap SE
:func:`session_icc_bootstrap_se`, and :class:`IccRow` / :func:`render_icc_map`
for the published knob → ICC map. Same rule: pure statistics only. The
simulating half lives in :mod:`livelift.sim.validate` and the one command that
publishes the map is ``analysis/calibration/bang_icc_mo_phong.py``.

SKELETON, deliberately: the shipped grid is 4 cells x ~100 reps so it runs in
minutes on a laptop. The full ~20-cell grid at 1000 reps is pre-registration
week work; nothing here fabricates its numbers.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.stats import kstest, norm

__all__ = [
    "IccRow",
    "SbcCell",
    "dkw_band",
    "ecdf_max_deviation",
    "render_icc_map",
    "render_report",
    "sbc_cell",
    "session_icc",
    "session_icc_bootstrap_se",
    "wilson_interval",
]


# ---------------------------------------------------------------------------
# Clustering diagnostic
# ---------------------------------------------------------------------------


def session_icc(values: Sequence[float], groups: Sequence[object]) -> float:
    """One-way ANOVA intraclass correlation of ``values`` clustered by ``groups``.

    Shrout & Fleiss (1979) ICC(1), the between/within decomposition:

        ICC = (MSB - MSW) / (MSB + (n0 - 1) * MSW)

    with ``n0`` the size correction for unbalanced groups
    ``(N - sum n_i^2 / N) / (k - 1)``. Here the values are BLOCK outcomes and
    the groups are SESSIONS, so this measures exactly the quantity
    ``SimParams.session_click_sigma`` is meant to dial: how much of the variance
    in a block's click rate is a property of the session it sits in.

    Returned RAW, and therefore possibly negative: the ANOVA estimator has no
    lower bound at 0, and a small negative value is the honest reading of "no
    detectable clustering, and here is the sampling noise around it". Clamping
    it silently at 0 would turn noise into a claim. Returns NaN when there are
    fewer than two groups or fewer than two observations per group on average.
    """
    y = np.asarray(list(values), dtype=float)
    g = np.asarray(list(groups), dtype=object)
    if y.size != g.size:
        raise ValueError("values và groups phải cùng độ dài")
    labels, inverse = np.unique(g, return_inverse=True)
    k = len(labels)
    n_total = y.size
    if k < 2 or n_total <= k:
        return float("nan")
    counts = np.bincount(inverse, minlength=k).astype(float)
    sums = np.bincount(inverse, weights=y, minlength=k)
    means = sums / counts
    grand = y.mean()
    ss_between = float(np.sum(counts * (means - grand) ** 2))
    ss_within = float(np.sum((y - means[inverse]) ** 2))
    ms_between = ss_between / (k - 1)
    ms_within = ss_within / (n_total - k)
    n0 = (n_total - np.sum(counts**2) / n_total) / (k - 1)
    denom = ms_between + (n0 - 1) * ms_within
    if denom <= 0:
        return float("nan")
    return float((ms_between - ms_within) / denom)


def session_icc_bootstrap_se(
    values: Sequence[float],
    groups: Sequence[object],
    n_boot: int = 400,
    seed: int = 0,
) -> float:
    """Cluster-bootstrap standard error of :func:`session_icc`.

    Resamples SESSIONS with replacement, never blocks. Blocks inside a session
    are dependent — that dependence is the very quantity being measured — so a
    block-level bootstrap would treat correlated observations as independent and
    report an SE that is too small, which is the failure mode that turns "ICC
    0.048" into a claim it cannot support.

    A session drawn twice enters as two distinct clusters (the labels are
    rebuilt per replicate), which is the standard nonparametric cluster
    bootstrap. Deterministic given ``seed``.

    Returns NaN when there are fewer than two clusters, or when fewer than two
    replicates give a finite ICC — a number that cannot be computed is reported
    as missing rather than as zero uncertainty.
    """
    y = np.asarray(list(values), dtype=float)
    g = np.asarray(list(groups), dtype=object)
    if y.size != g.size:
        raise ValueError("values và groups phải cùng độ dài")
    if n_boot < 2:
        raise ValueError("n_boot phải ≥ 2")
    _labels, inverse = np.unique(g, return_inverse=True)
    k = int(inverse.max()) + 1 if inverse.size else 0
    if k < 2:
        return float("nan")
    index_by_group = [np.flatnonzero(inverse == j) for j in range(k)]
    rng = np.random.default_rng(seed)
    draws: list[float] = []
    for _ in range(n_boot):
        picks = rng.integers(0, k, size=k)
        vals: list[float] = []
        ids: list[int] = []
        for new_id, j in enumerate(picks):
            idx = index_by_group[j]
            vals.extend(y[idx].tolist())
            ids.extend([new_id] * int(idx.size))
        stat = session_icc(vals, ids)
        if np.isfinite(stat):
            draws.append(stat)
    if len(draws) < 2:
        return float("nan")
    return float(np.std(draws, ddof=1))


@dataclass(frozen=True)
class IccRow:
    """One measured point of a heterogeneity-knob → ICC map.

    Every field is a measurement on simulated sessions, never an assumption.
    ``knob`` names the ``SimParams`` field that was swept, because the simulator
    has TWO knobs that move session ICC and a table that did not say which one
    produced it would be unreadable.

    ``mean_within_var`` travels with the ICC on purpose: it is what separates
    the two knobs (the session knob moves whole sessions and leaves
    within-session dispersion alone, per-viewer frailty does the opposite), so a
    reader can tell which mechanism produced a given ICC.
    """

    knob: str
    knob_value: float
    icc: float
    icc_se: float
    mean_y: float
    mean_within_var: float
    n_sessions: int
    n_blocks: int


def render_icc_map(rows: Sequence[IccRow], header: str = "") -> str:
    """Markdown table of a measured knob → ICC map. ``header`` goes in verbatim.

    The swept knob names the first column, taken from the rows themselves rather
    than from a caller-supplied string, so the header cannot disagree with the
    numbers under it.
    """
    lines: list[str] = []
    if header:
        lines.append(header.rstrip())
        lines.append("")
    knobs = {r.knob for r in rows}
    if len(knobs) > 1:
        raise ValueError(f"một bảng chỉ quét MỘT knob, nhận {sorted(knobs)}")
    knob = next(iter(knobs), "knob")
    lines.append(
        f"| `{knob}` | ICC(y) ± SE bootstrap cụm | trung bình y | "
        "phương sai TRONG-phiên | phiên | khối |"
    )
    lines.append("|---:|---|---:|---:|---:|---:|")
    for r in rows:
        lines.append(
            f"| {r.knob_value:.3f} | {_fmt(r.icc, '+.3f')} ± {_fmt(r.icc_se, '.3f')} | "
            f"{_fmt(r.mean_y, '.3f')} | {_fmt(r.mean_within_var, '.4f')} | "
            f"{r.n_sessions} | {r.n_blocks} |"
        )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Building blocks
# ---------------------------------------------------------------------------


def wilson_interval(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion.

    Preferred over the Wald interval throughout this project because the counts
    here are small (100 reps) and the proportions extreme (0.95 coverage): the
    Wald interval for 100/100 is the degenerate [1, 1], which would silently
    turn "we never saw a miss" into "coverage is exactly 100%".
    """
    if n <= 0:
        return float("nan"), float("nan")
    z = float(norm.ppf(1 - (1 - confidence) / 2))
    p_hat = successes / n
    denom = 1 + z**2 / n
    center = (p_hat + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p_hat * (1 - p_hat) / n + z**2 / (4 * n**2)) / denom
    return float(max(0.0, center - half)), float(min(1.0, center + half))


def ecdf_max_deviation(pvalues: Sequence[float]) -> float:
    """sup_x |F_n(x) - x| for a sample on [0, 1] — the uniform KS statistic.

    Written out rather than taken from scipy so the report can state plainly
    that the "max ECDF deviation" plotted against the band and the "KS
    statistic" quoted next to its p-value are the SAME number used two ways —
    one exact null p-value, one simultaneous graphical band. They are not two
    independent pieces of evidence and must not be counted as such.
    """
    p = np.sort(np.asarray(list(pvalues), dtype=float))
    n = p.size
    if n == 0:
        return float("nan")
    i = np.arange(1, n + 1)
    return float(max(np.max(i / n - p), np.max(p - (i - 1) / n)))


def dkw_band(n: int, confidence: float = 0.95) -> float:
    """Half-width of a SIMULTANEOUS confidence band for an ECDF (DKW/Massart).

    ``eps = sqrt(ln(2/alpha) / (2n))`` — Massart's (1990) tight constant in the
    Dvoretzky–Kiefer–Wolfowitz inequality, valid at every n with no asymptotics.

    Honest caveat, since the brief asks for an Aldor-Noiman band: the
    Aldor-Noiman et al. (2013) simultaneous band is noticeably TIGHTER at small
    n, but its width comes from a simulated calibration constant. Inventing
    that constant here would be exactly the kind of fabricated number this
    project refuses, so the conservative DKW band is used instead and labelled
    as conservative. Consequence: the band alone will rarely fail a cell at
    n≈100; the KS p-value is the sharp instrument, the band is the one a reader
    can draw on an ECDF plot and check by eye.
    """
    if n <= 0:
        return float("nan")
    return float(np.sqrt(np.log(2 / (1 - confidence)) / (2 * n)))


# ---------------------------------------------------------------------------
# One grid cell
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SbcCell:
    """Verdict for one cell of the calibration grid. All fields are measured."""

    label: str
    n_reps: int
    # uniformity of the p-values under the null (checked only where a null holds)
    uniformity_checked: bool
    ks_stat: float
    ks_pvalue: float
    ecdf_max_diff: float
    ecdf_band: float
    uniformity_ok: bool
    # coverage of the Fisher CI
    coverage: float
    coverage_ci_low: float
    coverage_ci_high: float
    coverage_confidence: float
    nominal_coverage: float
    coverage_ok: bool
    # bias of the point estimate against CRN ground truth
    mean_bias: float
    mc_error: float
    relative_bias: float  # NaN when there is no non-zero truth to divide by
    relative_mc_error: float  # NaN likewise
    bias_ok: bool
    # informational, never a gate here
    rejection_rate: float
    truth_scale: float

    @property
    def ok(self) -> bool:
        """Green only when every CHECKED criterion passes."""
        return (
            (self.uniformity_ok or not self.uniformity_checked)
            and self.coverage_ok
            and self.bias_ok
        )

    @property
    def status(self) -> str:
        return "XANH" if self.ok else "ĐỎ"

    def failures(self) -> list[str]:
        """Vietnamese reasons the cell is red — empty when green."""
        out: list[str] = []
        if self.uniformity_checked and not self.uniformity_ok:
            out.append(
                f"p-value không đồng đều (KS D={self.ks_stat:.3f}, p={self.ks_pvalue:.4f}, "
                f"băng DKW {self.ecdf_band:.3f})"
            )
        if not self.coverage_ok:
            out.append(
                f"độ phủ {self.coverage:.1%} lệch mức danh nghĩa {self.nominal_coverage:.0%} "
                f"(Wilson {self.coverage_confidence:.0%}: "
                f"[{self.coverage_ci_low:.1%}, {self.coverage_ci_high:.1%}])"
            )
        if not self.bias_ok:
            if np.isfinite(self.relative_bias):
                out.append(f"lệch tương đối {self.relative_bias:+.1%} vượt ngưỡng")
            else:
                out.append(
                    f"lệch tuyệt đối {self.mean_bias:+.4f} lớn so với sai số MC {self.mc_error:.4f}"
                )
        return out


def sbc_cell(
    pvalues: Sequence[float],
    coverages: Sequence[bool | int],
    biases: Sequence[float],
    *,
    label: str = "",
    truth_scale: float | None = None,
    nominal_coverage: float = 0.95,
    alpha: float = 0.05,
    check_uniformity: bool = True,
    ks_alpha: float = 0.01,
    coverage_confidence: float = 0.99,
    band_confidence: float = 0.95,
    max_relative_bias: float = 0.10,
    bias_z: float = 3.0,
) -> SbcCell:
    """Reduce one grid cell's replications to a green/red verdict.

    Inputs, one entry per replication:

    - ``pvalues`` — the randomization p-value of the replication;
    - ``coverages`` — did the Fisher CI contain the CRN ground truth;
    - ``biases`` — the SIGNED error ``estimate - true effect``.

    ``truth_scale`` is the denominator for the relative bias, normally
    ``mean(|true effect|)`` over the replications. Pass None (or a value at
    numerical zero, which is what a null cell gives) and the relative bias is
    reported as NaN rather than as a division by ~0 — a "-3400% bias" printed
    for a cell whose true effect is 1e-17 is a fabricated number, not a finding.
    In that case the bias criterion becomes "no systematic offset": the mean
    error must sit within ``bias_z`` Monte-Carlo standard errors of zero.

    ``check_uniformity`` must be False wherever no null holds — under a real
    effect the p-values are SUPPOSED to pile up near zero, and testing them for
    uniformity would flag a working pipeline. The three criteria are otherwise
    the pre-registered ones: HARNESS.md §2 asks for bias < 10% of the effect and
    a 95% interval that really covers 95%.

    ``alpha`` is the nominal level the ``rejection_rate`` is counted at; it is
    reported for context (power in an effect cell, false-positive rate in a null
    cell) and never gates the cell — the A/A binomial gate in
    ``tests/test_sim_validation.py`` owns that judgement.

    The two decision thresholds (``ks_alpha``, ``coverage_confidence``) are set
    at the 1% level on purpose, matching the convention the existing calibration
    gates already use. A verdict taken at the 5% level turns red on a PERFECTLY
    calibrated pipeline once per twenty cells, and a 20-cell grid that lights up
    a red square by construction teaches its readers to ignore red squares.

    KNOWN CONSERVATISM of the uniformity check, stated rather than papered over:
    a randomization p-value is discrete (multiples of 1/(draws+1), floored at
    1/(draws+1) by the add-one correction), so it is not exactly U(0,1) even for
    a perfect test. At 200 draws the granularity is 0.005 — far below the
    resolution of a 100-replication KS test — but at very small ``n_draws`` this
    check drifts toward accepting, never toward falsely rejecting.
    """
    p = np.asarray(list(pvalues), dtype=float)
    cov = np.asarray(list(coverages), dtype=float)
    err = np.asarray(list(biases), dtype=float)
    n = int(p.size)
    if not (cov.size == n and err.size == n):
        raise ValueError("pvalues, coverages và biases phải cùng độ dài")
    if n == 0:
        raise ValueError("ô SBC rỗng — không có lần lặp nào để đánh giá")

    finite_p = p[np.isfinite(p)]
    if check_uniformity and finite_p.size < 2:
        raise ValueError("cần ít nhất 2 p-value hữu hạn để kiểm tra tính đồng đều")

    if finite_p.size >= 2:
        ks = kstest(finite_p, "uniform")
        ks_stat, ks_p = float(ks.statistic), float(ks.pvalue)
        d_max = ecdf_max_deviation(finite_p)
        band = dkw_band(finite_p.size, band_confidence)
    else:
        ks_stat = ks_p = d_max = band = float("nan")
    uniformity_ok = bool(check_uniformity and ks_p >= ks_alpha and d_max <= band)

    n_covered = int(np.nansum(cov))
    n_cov_obs = int(np.sum(np.isfinite(cov)))
    coverage = n_covered / n_cov_obs if n_cov_obs else float("nan")
    cov_lo, cov_hi = wilson_interval(n_covered, n_cov_obs, coverage_confidence)
    coverage_ok = bool(cov_lo <= nominal_coverage <= cov_hi)

    mean_bias = float(np.mean(err))
    mc_error = float(np.std(err, ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    scale = abs(float(truth_scale)) if truth_scale is not None else 0.0
    if scale > 1e-9:
        rel_bias = mean_bias / scale
        rel_mc = mc_error / scale
        bias_ok = bool(abs(rel_bias) < max_relative_bias)
    else:
        rel_bias = float("nan")
        rel_mc = float("nan")
        bias_ok = bool(not np.isfinite(mc_error) or abs(mean_bias) <= bias_z * max(mc_error, 1e-15))

    rejection_rate = float(np.mean(finite_p < alpha)) if finite_p.size else float("nan")

    return SbcCell(
        label=label,
        n_reps=n,
        uniformity_checked=check_uniformity,
        ks_stat=ks_stat,
        ks_pvalue=ks_p,
        ecdf_max_diff=d_max,
        ecdf_band=band,
        uniformity_ok=uniformity_ok,
        coverage=coverage,
        coverage_ci_low=cov_lo,
        coverage_ci_high=cov_hi,
        coverage_confidence=coverage_confidence,
        nominal_coverage=nominal_coverage,
        coverage_ok=coverage_ok,
        mean_bias=mean_bias,
        mc_error=mc_error,
        relative_bias=rel_bias,
        relative_mc_error=rel_mc,
        bias_ok=bias_ok,
        rejection_rate=rejection_rate,
        truth_scale=scale,
    )


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _fmt(value: float, spec: str, dash: str = "—") -> str:
    return dash if not np.isfinite(value) else format(value, spec)


def render_report(cells: Sequence[SbcCell], header: str = "") -> str:
    """Markdown table of grid cells, one row each, with a XANH/ĐỎ verdict.

    ``header`` is prepended verbatim — the CLI puts the reproduction command and
    the SKELETON warning there, so a reader of the committed file always knows
    which command produced it and that the grid is not the full one.
    """
    lines: list[str] = []
    if header:
        lines.append(header.rstrip())
        lines.append("")
    conf = cells[0].coverage_confidence if cells else 0.99
    lines.append(
        f"| Ô | reps | Đồng đều p (KS D / p) | D vs băng DKW | Độ phủ (Wilson {conf:.0%}) | "
        "Lệch (tương đối ± MC) | Tỷ lệ bác bỏ | Kết luận |"
    )
    lines.append("|---|---:|---|---|---|---|---:|:--:|")
    for c in cells:
        if c.uniformity_checked:
            unif = f"D={_fmt(c.ks_stat, '.3f')}, p={_fmt(c.ks_pvalue, '.4f')}"
            band = f"{_fmt(c.ecdf_max_diff, '.3f')} / {_fmt(c.ecdf_band, '.3f')}"
        else:
            unif = "không áp dụng (có tác động)"
            band = "—"
        cov = (
            f"{_fmt(c.coverage, '.1%')} "
            f"[{_fmt(c.coverage_ci_low, '.1%')}, {_fmt(c.coverage_ci_high, '.1%')}]"
        )
        if np.isfinite(c.relative_bias):
            bias = f"{c.relative_bias:+.1%} ± {_fmt(c.relative_mc_error, '.1%')}"
        else:
            bias = f"{_fmt(c.mean_bias, '+.4f')} ± {_fmt(c.mc_error, '.4f')} (tuyệt đối)"
        lines.append(
            f"| {c.label} | {c.n_reps} | {unif} | {band} | {cov} | {bias} | "
            f"{_fmt(c.rejection_rate, '.1%')} | **{c.status}** |"
        )

    red = [c for c in cells if not c.ok]
    lines.append("")
    if red:
        lines.append(f"**{len(red)}/{len(cells)} ô ĐỎ:**")
        lines.append("")
        for c in red:
            for reason in c.failures():
                lines.append(f"- `{c.label}`: {reason}")
    else:
        lines.append(f"Tất cả {len(cells)} ô XANH theo tiêu chí đã nêu ở trên.")
    return "\n".join(lines) + "\n"
