"""Carryover / temporal interference diagnostics for the switchback — PLANNED.

Created empty on 2026-09-08 (gói P5a) as the landing site for the carryover
work of the 2026-09-07 programme. NOTHING IS IMPLEMENTED HERE YET, and nothing
imports this module: it exists so that the three carryover functions arrive in
one reviewable file instead of being appended to
:mod:`livelift.analysis.estimators`, which already carries the primary
randomization test and must stay quiet before the week-6 pre-registration
freeze.

Why a separate module at all. The estimand of every function below is
different from the primary one. The primary analysis targets the CONTEMPORANEOUS
effect under the no-carryover assumption baked into the block design (washout +
burn-in). The functions here target the assumption ITSELF — how much of a
block's outcome is explained by the PREVIOUS block's assignment. Mixing the two
in one namespace is how a diagnostic quietly becomes a headline number.

Planned API (signatures are indicative, not frozen; each must go through
HARNESS §4 — read the source, write ``docs/research-log.md``, then the test,
then the body):

``ht_lag1(y, z, session_ids, block_index, p=0.5) -> Lag1Result``
    Horvitz–Thompson / Hájek estimate of the lag-1 dynamic causal effect: the
    contrast between assignment paths that differ only in the PREVIOUS block,
    holding the current block's assignment fixed. Weighting must use the same
    per-block propensities the production assigner actually realized, not a
    nominal 0.5 — under rerandomization the marginal propensity is only
    guaranteed at p=0.5 and the joint law of adjacent blocks is NOT independent
    (adjacent-assignment correlation measured at −0.169; see
    ``cuped_adjust`` docstring). Getting that joint law right is the hard part
    of this function and the reason it is not a one-liner.

``carryover_gate(result, ...) -> QualityCheck``
    Turns the lag-1 estimate into a post-session QC item alongside the existing
    checks in ``core/quality.py``. FLAG, NEVER DROP (HARNESS §3): a detected
    carryover raises a flag with an investigation message and is recorded as a
    limitation; it must not silently exclude blocks, shorten the analysis
    window, or switch the primary estimand. Any exclusion stays a human
    decision written into the analysis appendix.

``impulse_response(y, z, session_ids, block_index, max_lag) -> np.ndarray``
    The lag-0..``max_lag`` profile of dynamic causal effects, i.e. how fast the
    effect of one pinned block decays. Reported as an exploratory figure only;
    its inference (randomization over the same production redraws) is far more
    expensive than the primary test, so it is nightly/offline work, not part of
    ``/experiment/summary``.

Open questions to settle BEFORE writing any body (do not guess in code):
- Which lag-1 estimand the block design can actually identify given the washout
  gap — the washout may already absorb what these functions try to measure, in
  which case the honest output is "not identified here", not a number.
- Whether the reference distribution for a lag-1 statistic can reuse the
  existing ``_redraw_matrix`` output or needs its own path-based redraws.
- Source and formula numbers (Bojinov & Shephard, JASA 2019, is the starting
  point already cited by ``estimators``; the exact estimand definition must be
  read from the paper and summarized in ``docs/research-log.md`` first).

Until then this module deliberately exports nothing.
"""

from __future__ import annotations

__all__: list[str] = []
