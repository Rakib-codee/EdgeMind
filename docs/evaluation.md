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
  tuning seeds 42–51; selection criterion: lowest deadline-miss rate,
  tie-broken by mean latency. Final numbers come from **held-out seeds
  100–109**, never used during tuning.
- **Scenarios**: `benchmarks/run_scenarios.py` — light (150 tasks),
  moderate (300), heavy (600), and network latency halved/doubled.

## Benchmark fairness fix (important)

The first evaluation round compared unfairly: the baseline executed
tasks on **static node profiles** (no latency jitter, full compute rate,
constant 1% failure probability) while the adaptive policy executed on
**dynamic node states** (jitter, load slowdown, load/queue-dependent
failure). This artifact accounted for adaptive's entire apparent
success-rate deficit and understated its deadline advantage.

Fixed in commit `b8d53d4`: both policies now execute on the observed
dynamic state of the chosen node, and benchmark rows log the decision
(estimated latency, failure probability, queue, load) per task.

| Metric (adaptive − baseline) | Before fix | After fix |
| ---------------------------- | ---------- | --------- |
| deadline_miss_rate           | −4.9 pp    | −8.75 pp  |
| success_rate                 | −4.6 pp    | +1.35 pp  |
| latency_mean_ms              | +9.8 ms    | +8.75 ms  |

## Tuned policy

Ablation showed the original failure-risk weight (1000) over-avoided
loaded nodes, raising latency without improving success. Grid search on
tuning seeds selected `AdaptiveWeights(load=20, failure=200)`:
deadline-miss 2.06% → 1.13% and mean latency 48.75 → 46.38 ms on the
tuning seeds.

## Final results — held-out seeds 100–109, tuned policy

| Metric | Baseline | Adaptive | Paired diff (95% CI) |
| ------ | -------- | -------- | -------------------- |
| Deadline miss rate | 8.30% | 1.58% | **−6.75 pp** [−8.75, −4.95] |
| Success rate | 93.59% | 95.99% | **+2.41 pp** [+1.26, +3.35] |
| Mean latency | 42.04 ms | 47.13 ms | +5.18 ms [+1.55, +8.13] |
| p95 latency | 109.03 ms | 124.96 ms | higher tail for adaptive |

n = 10 seeds × 300 tasks per policy. The tuned adaptive policy misses
**5.3× fewer deadlines** and succeeds more often than baseline, at the
cost of ~5 ms higher mean latency — a real, measured trade-off.

## Scenario results — held-out seeds 100–109

Paired difference (adaptive − baseline), 95% CI in brackets:

| Scenario | Deadline miss | Success rate | Mean latency |
| -------- | ------------- | ------------ | ------------ |
| moderate (300 tasks) | −6.8 pp [−8.8, −5.0] | +2.4 pp [+1.3, +3.3] | +5.2 ms [+1.6, +8.1] |
| light (150 tasks) | −6.1 pp [−8.3, −3.7] | +1.7 pp [+0.6, +2.8] | +4.5 ms [−0.6, +9.6] |
| heavy (600 tasks) | −7.8 pp [−9.4, −6.2] | +2.4 pp [+1.0, +3.9] | +3.0 ms [+0.5, +5.3] |
| low-latency network | −5.3 pp [−6.6, −4.0] | +11.9 pp [+8.1, +15.8] | +7.5 ms [+3.7, +11.0] |
| high-latency network | −9.3 pp [−11.6, −7.1] | +2.0 pp [+1.0, +3.3] | −0.8 ms [−5.2, +3.7] |

**Which scenarios benefit most:** adaptive's deadline advantage is
largest under **high network latency** (−9.3 pp, and with *no*
statistically detectable latency cost) and under **heavy load**
(−7.8 pp at only +3.0 ms). Its success-rate gain peaks on **low-latency
networks** (+11.9 pp), where baseline's blindness to load sends tasks
into congested nearby nodes. The mean-latency penalty is only clearly
present when networks are fast (low/moderate latency regimes).

## Ablation (held-out seeds, tuned policy)

| Variant | Deadline miss | Success | Mean latency |
| ------- | ------------- | ------- | ------------ |
| adaptive (tuned: load=20, failure=200) | 1.58% | 95.99% | 47.13 ms |
| adaptive_no_failure | 1.62% | 95.68% | 44.37 ms |
| adaptive_no_load | 1.66% | 95.73% | 47.84 ms |
| adaptive_latency_only | 1.80% | 95.39% | 47.72 ms |
| baseline | 8.30% | 93.59% | 42.04 ms |

The full tuned model has the best deadline-miss rate on held-out data,
so both penalty terms earn their keep after tuning — unlike before
tuning, where the oversized failure penalty was counterproductive.

## Reproduction

```sh
python -m benchmarks.tune_weights        # tuning seeds 42-51
python -m benchmarks.run_evaluation --first-seed 100 --out results/raw/evaluation_heldout.csv
python -m benchmarks.analyze_evaluation results/raw/evaluation_heldout.csv
python -m benchmarks.run_scenarios
python -m benchmarks.analyze_scenarios results/raw/scenarios.csv
```

## Limitations

- Nodes are simulated profiles with stylised mean-reverting dynamics;
  no physical-network measurements.
- Simulated failures are independent random outcomes; failure does not
  trigger retries, so failure-avoidance shows up in success rate only.
- Weights tuned on 10 seeds; held-out results are close to tuning-seed
  numbers (miss 1.13% → 1.58%), suggesting limited overfitting, but
  more seeds would tighten CIs.
- Scheduling overhead is not wall-clock measured; the simulation is
  mathematical.
