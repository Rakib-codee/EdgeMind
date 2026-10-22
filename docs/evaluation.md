# Research Evaluation — EdgeMind

This document records the experimental comparison of the baseline and
adaptive scheduling policies, including a benchmark-fairness fix, weight
tuning, held-out evaluation, and scenario analysis. All results are from
**simulated** nodes; simulated latency must not be presented as measured
physical network latency.

## Research question

> When network latency and server load vary, can adaptive task
> scheduling reduce task completion latency compared to a static
> rule-based policy?

## Method

- **Runner**: `benchmarks/run_evaluation.py` — identical workloads and
  identical `DynamicEnvironment` evolutions per seed for every policy
  (paired design).
- **Statistics**: per-seed paired differences with deterministic
  bootstrap 95% CIs (10,000 resamples, seed 20241022). A difference is
  treated as meaningful only when its CI excludes zero.
- **Weight tuning**: grid search (`benchmarks/tune_weights.py`) on
  tuning seeds 42–51; selection criterion: highest **overall on-time
  completion rate** (successful and within deadline, over ALL submitted
  tasks), tie-broken by mean latency. Final numbers come from
  **held-out seeds 100–109**, never used during tuning.
- **Scenarios**: `benchmarks/run_scenarios.py` — light (150 tasks),
  moderate (300), heavy (600), and network latency halved/doubled.

## Metric definitions (rejection-aware, current)

| Metric | Population |
| ------ | ---------- |
| accepted_deadline_miss_rate | executed tasks only |
| accepted_success_rate | executed tasks only |
| rejection_rate | all submitted tasks |
| overall_ontime_rate | all submitted; rejected = not on-time |
| overall_success_rate | all submitted; rejected = not successful |
| overall_deadline_failure_rate | 1 − overall_ontime_rate |
| latency mean/median/p95/p99 | executed tasks only |

Rejected-task rows carry structurally empty measurement fields; they
are never treated as zero values.

## Model fixes behind the current results

1. **Execution fairness** (`b8d53d4`): the baseline originally executed
   on static profiles while adaptive executed on dynamic states. Fixed:
   both execute on the observed dynamic node state.
2. **Queue-wait consistency** (`18ab0ff`): the latency estimator charged
   queue wait but simulated execution ignored it, so adaptive's
   estimates overshot actual latency by ~16 ms and it rejected tasks
   that would have finished on time (60% of adaptive-only rejections
   met their deadline when baseline ran them). Execution now models
   `total = network + queue wait + compute`, matching the estimator.
3. **Admission-aware tuning** (`5fd1d4f`): under the corrected model,
   the load penalty became redundant (load is already priced into the
   latency estimate) and only caused extra rejections. Tuned defaults:
   `AdaptiveWeights(load=0, failure=200)`.

## Historical note: benchmark fairness fix

The first evaluation round compared unfairly: the baseline executed
tasks on **static node profiles** (no latency jitter, full compute rate,
constant 1% failure probability) while the adaptive policy executed on
**dynamic node states**. That artifact accounted for adaptive's entire
apparent success-rate deficit and understated its deadline advantage.
It was fixed in `b8d53d4`; the pre-fix raw data is preserved at
`results/raw/evaluation_v1_before_fairness_fix.csv`.

A second round then exposed the rejection-denominator problem: accepted-
task metrics hid that adaptive rejected 26% of submissions vs baseline's
15.7%, making the overall comparison unfavourable to adaptive (overall
deadline failure 27.2% vs 22.7%). Root cause: the estimator charged
queue wait that the executor never simulated — fixed in `18ab0ff`, which
is the model all current results use.

## Final results — held-out seeds 100–109, queue-aware model, tuned policy

n = 10 seeds × 300 tasks per policy. Paired bootstrap 95% CIs.

| Metric | Baseline | Adaptive | Paired diff (95% CI) |
| ------ | -------- | -------- | -------------------- |
| accepted_deadline_miss_rate | 27.28% | 2.34% | **−24.98 pp** [−28.5, −21.3] |
| overall_ontime_rate | 57.77% | 69.37% | **+11.60 pp** [+8.8, +14.0] |
| overall_deadline_failure_rate | 42.23% | 30.63% | **−11.60 pp** [−14.0, −8.9] |
| rejection_rate | 15.70% | 25.80% | +10.10 pp [+8.8, +11.7] |
| accepted_success_rate | 93.59% | 95.73% | +2.13 pp [+1.2, +3.1] |
| overall_success_rate | 78.90% | 71.03% | **−7.87 pp** [−9.6, −6.3] |
| latency_mean_ms | 96.24 ms | 64.61 ms | **−31.76 ms** [−44.1, −17.5] |
| latency_p95_ms | 314.64 ms | 190.44 ms | lower tail for adaptive |

Reading: under the corrected model, adaptive wins deadline compliance
both per accepted task (~11.7× fewer misses) and end-to-end (+11.6 pp
more on-time completions), and is also faster on average, because the
queue-blind baseline sends tasks into congested nodes and pays real
queue wait. Baseline retains one advantage: it accepts and finishes more
tasks overall (overall_success +7.9 pp) — but many of those finish late.
The rejection gap is now honest admission conservatism: with real queue
waits, more deadlines genuinely cannot be met, and adaptive detects that
up front.

These are aggregate statements. Adaptive is not faster in every seed:
on seed 102, for example, adaptive's mean latency is 66.0 ms versus
baseline's 52.4 ms and it rejects more tasks (65 vs 39), while its
on-time completion is still better (73.0% vs 70.7%). Seed 102 is an
illustration of heterogeneity, not a representative seed; per-seed
results are in `results/processed/v2/evaluation_per_seed.csv`.

## Scenario results — held-out seeds 100–109, queue-aware model

Paired difference (adaptive − baseline), 95% CI in brackets:

| Scenario | Accepted miss | Overall on-time | Rejection | Mean latency |
| -------- | ------------- | --------------- | --------- | ------------ |
| moderate | −25.0 pp [−28.5, −21.3] | +11.6 pp [+8.8, +14.0] | +10.1 pp | −31.8 ms [−44.2, −17.6] |
| light | −20.1 pp [−23.8, −16.6] | +7.7 pp [+4.6, +10.4] | +9.6 pp | −22.6 ms [−36.1, −8.7] |
| heavy | −26.8 pp [−29.5, −23.9] | +12.1 pp [+9.2, +15.4] | +10.9 pp | −34.6 ms [−52.2, −19.7] |
| low-latency net | −34.0 pp [−39.1, −28.9] | **+21.8 pp** [+18.5, +25.1] | +11.1 pp | −164.9 ms [−260.6, −88.6] |
| high-latency net | −27.5 pp [−32.8, −22.1] | +12.5 pp [+9.0, +16.2] | +9.1 pp | −45.2 ms [−73.4, −23.4] |

Adaptive improves on-time completion in every scenario, most strongly on
low-latency networks (+21.8 pp) where queue wait dominates total latency
and queue-blind scheduling is most harmful.

## Ablation (held-out seeds, queue-aware model)

| Variant | Accepted miss | Rejection | Overall on-time | Mean latency |
| ------- | ------------- | --------- | --------------- | ------------ |
| adaptive (tuned: load=0, failure=200) | 2.34% | 25.8% | **69.37%** | 64.61 ms |
| adaptive_latency_only (0, 0) | 2.31% | 27.7% | 67.30% | 68.24 ms |
| adaptive_with_load20 (20, 200) | 2.61% | 26.0% | 69.13% | 65.66 ms |
| baseline | 27.28% | 15.7% | 57.77% | 96.24 ms |

The failure-risk term earns its keep (+2.1 pp on-time over
latency-only); the load penalty does not (−0.2 pp, more rejections),
which is why its default is 0.

## Reproduction

```sh
python -m benchmarks.tune_weights --out results/raw/weight_tuning_v2.csv  # tuning seeds 42-51
python -m benchmarks.run_evaluation --first-seed 100 --out results/raw/evaluation_heldout_v2.csv
python -m benchmarks.analyze_evaluation results/raw/evaluation_heldout_v2.csv --out-dir results/processed/v2
python -m benchmarks.run_scenarios --out results/raw/scenarios_v2.csv
python -m benchmarks.analyze_scenarios results/raw/scenarios_v2.csv --out-dir results/processed/v2
```

Original (pre-fix) raw data is preserved in `results/raw/evaluation.csv`,
`evaluation_v1_before_fairness_fix.csv`, `evaluation_heldout.csv`, and
`scenarios.csv`; all current results use the `_v2` files.

## Confirmatory evaluation — 30 fresh seeds (200–229)

Run after weights were frozen, on seeds never used for tuning or prior
evaluation. Raw data: `results/raw/evaluation_confirmatory_v1.csv`
(36,000 rows; SHA-256 provenance in the adjacent manifest) and
`results/raw/scenarios_confirmatory_v1.csv` (99,000 rows); processed
output in `results/processed/confirmatory_v1/`. n = 30 seeds × 300
tasks per policy; paired seed-level percentile bootstrap, 10,000
resamples.

| Metric | Baseline | Adaptive | Paired diff (95% CI) |
| ------ | -------- | -------- | -------------------- |
| accepted_deadline_miss_rate | 29.84% | 2.30% | **−27.49 pp** [−30.2, −24.9] |
| overall_ontime_rate | 55.40% | 69.81% | **+14.41 pp** [+12.2, +16.5] |
| overall_deadline_failure_rate | 44.60% | 30.19% | **−14.41 pp** [−16.6, −12.3] |
| rejection_rate | 15.97% | 25.63% | +9.67 pp [+8.1, +11.3] |
| accepted_success_rate | 92.97% | 96.12% | +3.12 pp [+2.5, +3.8] |
| overall_success_rate | 78.12% | 71.48% | −6.64 pp [−8.3, −5.1] |
| latency_mean_ms | 100.78 ms | 61.93 ms | **−38.32 ms** [−47.3, −29.5] |
| latency_p95_ms | 345.29 ms | 182.56 ms | lower tail for adaptive |

The confirmatory run supports the v2 findings with tighter intervals:
all primary CIs exclude zero, and adaptive's on-time advantage holds in
**30/30 seeds** (worst-case diff 0.000). Adaptive's mean latency is
higher in 2 of 30 seeds (209, 229; at most +10.4 ms) — heterogeneity
persists but is rare. The overall_success gap (−6.6 pp) persists by
design: baseline accepts and finishes more tasks, many of them late.

Confirmatory scenario results (paired diff, all CIs exclude zero):

| Scenario | Accepted miss | Overall on-time | Mean latency |
| -------- | ------------- | --------------- | ------------ |
| moderate | −27.5 pp | +14.4 pp [+12.2, +16.6] | −38.3 ms [−47.2, −29.4] |
| light | −26.1 pp | +13.2 pp [+10.8, +15.6] | −33.1 ms [−43.2, −23.5] |
| heavy | −27.1 pp | +13.3 pp [+11.3, +15.3] | −38.6 ms [−46.1, −31.3] |
| low-latency net | −35.4 pp | **+22.4 pp** [+18.6, +25.9] | −168.4 ms [−232.0, −114.2] |
| high-latency net | −29.0 pp | +14.7 pp [+12.4, +17.0] | −51.0 ms [−68.0, −36.1] |

Reproduction:

```sh
python -m benchmarks.run_evaluation --tasks 300 --seeds 30 --first-seed 200 \
  --out results/raw/evaluation_confirmatory_v1.csv
python -m benchmarks.analyze_evaluation results/raw/evaluation_confirmatory_v1.csv \
  --out-dir results/processed/confirmatory_v1
python -m benchmarks.run_scenarios --seeds 30 --first-seed 200 \
  --out results/raw/scenarios_confirmatory_v1.csv
python -m benchmarks.analyze_scenarios results/raw/scenarios_confirmatory_v1.csv \
  --out-dir results/processed/confirmatory_v1
```

## Limitations

- **Simulation-only evidence.** Nodes are simulated profiles with
  stylised mean-reverting dynamics; queue wait uses the same-size
  assumption as the estimator (`app/scheduler/latency.py`). No
  physical edge/cloud infrastructure was measured, and no result here
  is a real-world network measurement.
- **Independent units and CI method.** The confirmatory evaluation uses
  30 fresh seeds (200–229), disjoint from tuning (42–51) and the v2
  held-out seeds (100–109); seed is the independent unit for inference.
  Seed-level percentile-bootstrap CIs at n = 30 are still approximate
  but substantially tighter than the 10-seed v2 run.
- **Per-seed heterogeneity.** Aggregate improvements do not hold in
  every seed (see seed 102 above); per-seed and per-scenario results
  are published alongside aggregates.
- **Stochastic trajectory divergence.** Queue draining draws from the
  environment RNG, and queue lengths are policy-dependent, so the two
  policies consume different amounts of randomness and their stochastic
  trajectories diverge after the first queue difference. Paired task
  inputs therefore do not guarantee identical environment trajectories.
  This is a simulation-semantics caveat, not demonstrated data leakage.
- **Rejected tasks.** Adaptive rejects ~10 pp more tasks than baseline;
  systems that cannot reject work need a retry/defer mechanism instead
  (future work). All overall_* metrics count rejected tasks as neither
  successful nor on-time.
- **Uninstrumented metrics.** Throughput, resource utilization, and
  scheduling overhead are not measured by the current pipeline.
  Execution failures are recorded, but timeouts are not a separate
  outcome category.
- Simulated failures are independent random outcomes; failure does not
  trigger retries, so failure-avoidance shows up in success rate only.
- Weights tuned on 10 seeds; held-out on-time rate (69.4%) is close to
  the tuning-seed value (71.8%), suggesting limited overfitting, but
  more seeds would tighten CIs.
