# Topic 2 — Estimation & Inference for Small-Sample Switchback Experiments (LiveLift)

## 1. Recommended estimation pipeline (pre-register this)

**Unit of analysis: the block** (~650 blocks, ~30 sessions × ~21 blocks). Never analyze click-level rows as if independent — DoorDash shows this inflates false positives badly; effective n is the number of blocks, not clicks ([Analyzing Switchback Experiments by Cluster Robust Standard Error, DoorDash Eng Blog, 2019](https://careersatdoordash.com/blog/cluster-robust-standard-error-in-switchback-experiments/)).

**Primary estimator (ITT):** OLS of block-level CTR on ON/OFF assignment with **session fixed effects** + pre-block covariates, cluster-robust SEs by session:

```
ctr_b = α_session + τ·Z_b + β'X_b + ε_b
```

Covariates `X_b` (all measured *before* block start, or from pre-experiment data — never post-treatment): previous-block CTR, session-so-far rolling CTR, concurrent-viewer count at block start, block index within session (time-of-stream), day-of-week, planned product-category slot. Use **Lin (2013)-style full interaction** (demean covariates, interact with treatment) — it never hurts asymptotic precision and is agnostic to model misspecification (Lin, "Agnostic notes on regression adjustments to experimental data," *Annals of Applied Statistics*, 2013; see [empirical comparison of parametric and permutation tests, arXiv:1702.04851](https://arxiv.org/pdf/1702.04851)).

**Primary test:** randomization inference (below). **Primary CI:** cluster-robust (by session) with wild-cluster bootstrap given only ~30 clusters. **Secondary:** IV/LATE (below).

## 2. (a) Randomization inference done correctly

The permutation distribution must equal the **actual randomization distribution** — you re-draw assignments, you do not "shuffle outcomes." This is what makes it exact under serial correlation: under the sharp null (no effect, up to carryover order *m*), potential outcomes are fixed constants, so dependence in outcomes is irrelevant ([Bojinov & Shephard, "Time series experiments and causal estimands: exact randomization tests and trading," *JASA* 114(528), 2019](https://arxiv.org/abs/1706.07840); [Bojinov, Simchi-Levi & Zhao, "Design and Analysis of Switchback Experiments," *Management Science* 69(7), 2023](https://arxiv.org/abs/2009.00148)).

Concretely for LiveLift:

- **Respect stratification:** re-randomize *within session*, exactly as your assignment engine does. If you assign balanced 50/50 per session, redraw balanced permutations per session; if i.i.d. Bernoulli(0.5) per block, redraw i.i.d. per block. Store the RNG scheme so the analysis script can call the same generator. 2,000–10,000 draws.
- **Test statistic:** use the **studentized** coefficient (t-statistic from the FE + covariate regression), not the raw difference. Studentized permutation tests stay asymptotically valid even when the sharp null fails (Romano-style; [arXiv:1702.04851](https://arxiv.org/pdf/1702.04851)).
- **Carryover-robust variant:** under a null of "no effect up to lag m," exclude the first block after each switch (or first 1–2 min of each block) from the statistic and re-randomize identically. Bojinov et al. give a data-driven procedure to pick *m* and show misspecifying it only mildly inflates variance.
- **CI:** invert the randomization test over a grid of constant-effect nulls (τ₀ shift), or fall back to the wild-cluster-bootstrap CI; report both.

## 3. (b) IV / LATE under partial compliance

Your two tiers create two "compliance" gaps: (i) outer tier — an ON block may end up pinning the same product the operator would have pinned; (ii) operators may override. Estimate:

- **First stage:** D_b = "system-recommended product actually pinned ≥x% of block" on Z_b (assignment). **2SLS** with Z as instrument, same session FE + covariates, clustered by session — this recovers LATE for complier blocks (standard encouragement-design logic; [Eggers, IV/LATE lecture notes](https://andy.egge.rs/teaching/causal_inference/CausalInference_w4_IV.pdf)).
- With ~650 blocks and a strong first stage (compliance ≥60%), the instrument won't be weak, but **report the first-stage F and an Anderson–Rubin confidence set anyway** — AR is valid at any instrument strength and costs nothing ([Londschien, "A statistician's guide to weak-instrument-robust inference in IV regression with illustrations in Python," arXiv:2508.12474, 2025](https://arxiv.org/pdf/2508.12474)).
- **Inner tier:** because you log propensities, product-vs-product contrasts should use **Hájek-style IPW / AIPW** with the logged propensities, restricted to blocks in the randomized-overlap set. Keep this exploratory; it's a different estimand.

**Action:** add "recommended product actually pinned (fraction of block)" and "operator override flag" to the block log schema now — the IV analysis is impossible without them.

## 4. (c) Variance reduction — realistic gains

- **CUPED with a lagged-CTR covariate is modest in switchbacks:** the 2026 DoorDash comparative study finds CUPED (pre-period covariate, R²≈0.15) gives only ~10% SE reduction at baseline, but improves sharply when autocorrelation is high (SE ratio 0.62 at ρ=0.9) ([Design-Aware Variance Reduction for Switchback Experiments, arXiv:2606.27662, 2026](https://arxiv.org/html/2606.27662v1)).
- **CUPAC (ML-predicted counterfactual CTR as the covariate) is the sweet spot for you:** with a covariate at R²≈0.5, SE ratio ≈0.50 (≈75% variance reduction, ≈2× smaller MDE), and — critically — **CUPAC stays stable at small cluster counts while doubly-robust/DML estimators degrade below ~50 clusters** from propensity overfitting. With 30 sessions, skip DML-DR; use CUPAC ([arXiv:2606.27662](https://arxiv.org/html/2606.27662v1); [DoorDash CUPAC post, ODSC](https://opendatascience.com/improving-experimental-power-through-cupac/)).
- Industry benchmarks for user-level CUPED (Netflix ~40% variance reduction on engagement; Microsoft ≈ +20% traffic equivalent) are upper bounds; block-level CTR is noisier ([Towards Data Science, covariate adjustment methods](https://towardsdatascience.com/variance-reduction-in-experiments-part-2-covariate-adjustment-methods-f5393f92eb8f/); [GrowthBook CUPED docs](https://docs.growthbook.io/statistics/cuped)).

**Action:** train a small GBM predicting block CTR from pre-block features on **pre-experiment / OFF-only data**, use its prediction as the single CUPAC covariate, and pre-register it. Expect a realistic 20–40% variance reduction (1.1–1.3× MDE improvement) if your predictor reaches R²=0.2–0.4 on held-out blocks.

## 5. (d) Is "MDE ≈ 4·CV/√n_per_arm" sound? — Yes, as a *base case*, but three corrections dominate

Derivation: relative MDE = (z₀.₉₇₅+z₀.₈₀)·√2·CV/√n = 2.80·1.414·CV/√n ≈ **3.96·CV/√n_per_arm**. So the formula is the textbook two-sample approximation at 80% power / 5% two-sided ([J-PAL power calculations](https://www.povertyactionlab.org/resource/power-calculations)) — valid only for **independent, equal-variance blocks**. Corrections, in order of importance:

1. **Compliance dilution (largest):** MDE on the LATE scale = MDE_ITT / (compliance rate). At 60% effective compliance, every MDE in your power table inflates ×1.67. Report both scales.
2. **Session clustering / ICC:** raw pooling gives design effect deff = 1+(m−1)·ICC with m≈21 blocks/session; ICC=0.1 → deff=3, MDE ×1.73. **Session fixed effects + within-session randomization mostly neutralize this** — then replace CV with the *within-session* CV (usually smaller; a gain, not a loss). Your table should be built on within-session residual variance from pilot data.
3. **Residual serial correlation between adjacent blocks:** after FE + covariates, an AR(1) residual ρ_r inflates MDE by ≈√((1+ρ_r)/(1−ρ_r)) in the worst case; at ρ_r=0.2 that's ×1.22. Measure ρ_r in the pilot; longer blocks (15 min) lower it.
4. **Carryover/burn-in loss:** dropping the first minutes after each switch cuts effective n; standard designs suffer T^(−1/3) error scaling under carryover unless burn-in is used ([Hu & Wager, "Switchback Experiments under Geometric Mixing," arXiv:2209.00197, 2022/2024](https://arxiv.org/abs/2209.00197)). Budget ~10% n loss.
5. **CV estimation:** block CTR variance = binomial noise p(1−p)/impressions + between-block variance. Low-viewership blocks have huge CVs — compute CV from Live Lab pilot blocks, and consider impression-weighting or minimum-impression inclusion rules (pre-registered).

Net: a realistic power table row is MDE ≈ 4·CV_within/√n × 1/compliance × √deff_residual ÷ √(1−R²_CUPAC). The CUPAC term can roughly cancel the compliance penalty.

## 6. (e) Carryover sensitivity analysis

- **Lag-augmented regression** (pre-registered diagnostic): add W_{b−1}, W_{b−2} to the primary regression; a significant lagged coefficient signals carryover — DoorDash uses exactly this ([Experiment Rigor for Switchback Experiment Analysis, DoorDash](https://careersatdoordash.com/blog/experiment-rigor-for-switchback-experiment-analysis/)). Also re-estimate τ excluding post-switch burn-in (1, 2, 5 min) and plot τ vs. burn-in length — stability = robustness ([Hu & Wager 2022](https://arxiv.org/abs/2209.00197)).
- Note the warning from the DoorDash 2026 study: under strong carryover, variance-reduced estimators get *confidently wrong* (narrow CIs around biased τ; 38% wrong-sign rejections for DR vs. 11% raw). Run the carryover diagnostics **before** trusting CUPAC CIs ([arXiv:2606.27662](https://arxiv.org/html/2606.27662v1)).
- Use Bojinov et al.'s data-driven selection of carryover order *m* to justify block length ≥ m ([Management Science 2023](https://pubsonline.informs.org/doi/10.1287/mnsc.2022.4583)).

## 7. (f) Python stack

- **Primary OLS:** `statsmodels` `smf.ols(...).fit(cov_type="cluster", cov_kwds={"groups": session_id})`; HAC (`cov_type="HAC"`, Newey–West) as a sensitivity check ([statsmodels get_robustcov_results](https://www.statsmodels.org/stable/generated/statsmodels.regression.linear_model.OLSResults.get_robustcov_results.html)).
- **Few-cluster fix:** with 30 sessions, pair cluster-robust SEs with the **wild cluster bootstrap** (`wildboottest` PyPI package, Rademacher weights, 9,999 reps) for the parametric CI.
- **IV:** `linearmodels.iv.IV2SLS` with `cov_type="clustered", clusters=session_id`; it supports kernel-HAC too ([linearmodels IV docs](https://bashtage.github.io/linearmodels/iv/iv/linearmodels.iv.model.IV2SLS.fit.html)). Anderson–Rubin CIs via **`ivmodels`** (`pip install ivmodels`) ([Londschien 2025](https://arxiv.org/pdf/2508.12474)).
- **Randomization inference:** ~30 lines of numpy — loop: redraw within-session assignment via the production assignment function, refit the FE regression (precompute the FE-demeaned design matrix once for speed), collect t-stats. Don't use generic `scipy.stats.permutation_test` — it can't express your stratified design.
- **CUPAC model:** `lightgbm` or `sklearn.GradientBoostingRegressor`, trained on OFF/pre-period blocks only, cross-fit by session to avoid leakage.

**Single most important changes to the project:** (1) build the power table on within-session CV with the compliance-dilution and burn-in corrections above; (2) log compliance/override and propensities at block grain from day one; (3) make the stratified re-randomization test (studentized, carryover-order-robust) the pre-registered primary inference, with CUPAC-adjusted cluster-robust CIs alongside.