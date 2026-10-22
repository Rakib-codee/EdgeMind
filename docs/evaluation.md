# Phase 11 — Research Evaluation

This document records the experimental comparison of the baseline and
adaptive scheduling policies, including ablation and sensitivity
analysis. All results are from **simulated** nodes; simulated latency
must not be presented as measured physical network latency.

## Research question

> When network latency and server load vary, can adaptive task
> scheduling reduce task completion latency compared to a static
> rule-based policy?

## Method

- **Runner**: `benchmarks/run_evaluation.py` — 10 seeds (42–51), 300
  tasks per seed, 5 policy variants → 15,000 rows
  (`results/raw/evaluation.csv`, kept local per `.gitignore`).
- **Fairness**: every variant receives identical task workloads and
  identical `DynamicEnvironment` evolutions per seed (same seeds), so
  comparisons are paired.
- **Variants**:
  - `baseline` — static rule-based node selection
  - `adaptive` — full weighted cost model (latency + load + failure)
  - `adaptive_no_load` — load penalty removed (ablation)
  - `adaptive_no_failure` — failure penalty removed (ablation)
  - `adaptive_latency_only` — latency term only (ablation)
- **Statistics**: per-seed paired differences with a deterministic
  bootstrap 95% CI (10,000 resamples, seed 20241022).
- **Analysis**: `benchmarks/analyze_evaluation.py`.

## Results

### Paired comparison: adaptive − baseline (per seed, n = 10)

| Metric              | Mean diff | 95% CI            | Interpretation              |
| ------------------- | --------- | ----------------- | --------------------------- |
| latency_mean_ms     | +9.82     | [+6.55, +13.60]   | adaptive is slower on average |
| deadline_miss_rate  | −0.0488   | [−0.063, −0.034]  | adaptive misses fewer deadlines |
| success_rate        | −0.0457   | [−0.051, −0.040]  | adaptive fails more often   |

### Aggregate metrics across all seeds

| Variant               | Deadline miss | Success | Mean latency (ms) | p95 (ms) |
| --------------------- | ------------- | ------- | ----------------- | -------- |
| adaptive_no_failure   | 0.0113        | 0.9423  | 46.86             | 126.87   |
| adaptive_latency_only | 0.0144        | 0.9462  | 46.80             | 126.55   |
| adaptive_no_load      | 0.0168        | 0.9470  | 47.41             | 117.42   |
| adaptive              | 0.0206        | 0.9455  | 48.75             | 127.18   |
| baseline              | 0.0696        | 0.9909  | 39.15             | 84.15    |

### Sensitivity: budget tightness

| Variant | Regime | Deadline miss |
| ------- | ------ | ------------- |
| baseline              | loose (budget ≥ ideal local time) | 0.0732 |
| adaptive              | loose                             | 0.0136 |
| baseline              | tight (budget < ideal local time) | 0.0590 |
| adaptive              | tight                             | 0.0444 |

## Findings

1. **The hypothesis is partially supported, with an important
   qualification.** Adaptive scheduling significantly reduces the
   deadline-miss rate (from ~7.0% to ~2.1%, paired CI excludes zero),
   which is the metric deadline-driven systems care about. However, it
   **increases mean latency** (~+10 ms, CI excludes zero) — the adaptive
   policy avoids congested/overloaded nodes even at the cost of
   nominally slower choices, trading raw speed for deadline adherence.

2. **Deadline-miss rate and mean latency can move in opposite
   directions.** A scheduler with a lower mean latency (baseline)
   misses more deadlines because latency variance and risk matter more
   than the average when budgets are tight.

3. **Ablation surprise:** removing the failure-risk penalty
   (`adaptive_no_failure`) yields the *best* deadline-miss rate (1.13%),
   better than the full model (2.06%). The current failure penalty
   appears too aggressive and over-avoids nodes that would still meet
   deadlines. This suggests the default weights need tuning — a
   candidate for future work rather than a claim of optimality.

4. **Success rate slightly favours baseline** (99.1% vs ~94.5%).
   Adaptive's queue/load-aware choices route tasks through states whose
   simulated failure probability is higher at execution time. This
   interaction between the decision-time estimate and execution-time
   outcome deserves further study.

5. **Sensitivity:** adaptive's advantage over baseline exists in both
   tight and loose budget regimes, and is largest under loose budgets
   (5.9× lower miss rate), where there is room to choose safer nodes.

## Reproduction

```sh
python -m benchmarks.run_evaluation --tasks 300 --seeds 10
python -m benchmarks.analyze_evaluation results/raw/evaluation.csv
```

Outputs land in `results/processed/` (per-seed summary, paired
comparison, ablation and sensitivity tables, and plots).

## Limitations

- Nodes are simulated profiles; load and latency evolution follow
  stylised mean-reverting random walks, not real measurements.
- Simulation runtime variance uses a fixed jitter model.
- Policy weights are hand-chosen, not tuned; ablation shows tuning
  matters.
- 10 seeds give modest statistical power; CIs assume per-seed
  independence of the differences.
