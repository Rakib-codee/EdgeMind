# Experiment Protocol — EdgeMind

How the benchmarks and evaluation experiments are run, so results can
be reproduced exactly.

## Workload generation

- Task sizes drawn uniformly from three classes: small (10–100),
  medium (100–1000), large (1000–5000) compute units.
- Latency budget = ideal local compute time × a budget factor drawn
  from {0.5, 1, 2, 5}. Factors below 1 create deadline pressure.
- One workload per seed (`generate_tasks(tasks=300, seed=...)`).

## Fair comparison rules

1. Every policy variant sees the **same task sequence** for a seed.
2. Every variant drives its own `DynamicEnvironment` with the **same
   RNG seed**, so node latency/load evolution is identical.
3. Per-task execution jitter uses a deterministic seed derived from
   `(benchmark seed, task_id)`.
4. Queue drain probability is fixed at 0.3 per tick.

## Experiment matrix

| Experiment | Script | Configuration |
| --- | --- | --- |
| Single-run benchmark | `benchmarks/run_benchmark.py` | 300 tasks, seed 42, baseline vs adaptive |
| Weight tuning | `benchmarks/tune_weights.py` | grid over load × failure weights, tuning seeds 42–51 |
| Research evaluation | `benchmarks/run_evaluation.py` | held-out seeds 100–109 × 300 tasks × 5 variants |
| Scenario benchmark | `benchmarks/run_scenarios.py` | light/moderate/heavy × low/high network latency, held-out seeds |

Tuning seeds and evaluation seeds are disjoint: weights are selected on
42–51 and only *reported* on the held-out seeds 100–109.

Policy variants for evaluation: `baseline`, `adaptive` (default
weights), `adaptive_no_load`, `adaptive_no_failure`,
`adaptive_latency_only`.

## Metrics

- **Task completion latency** — mean, median, p95 of total latency.
- **Deadline-miss rate** — fraction of executed tasks exceeding their
  latency budget.
- **Success rate** — fraction of executed tasks that succeed.
- **Rejection count** — tasks with no feasible target.
- Runtime observation via Prometheus: scheduled/executed/failed
  counters, latency and compute-duration histograms.

## Statistical analysis

- Per-seed paired differences (adaptive − baseline) per metric.
- Bootstrap 95% confidence interval on the mean difference:
  10,000 resamples, deterministic RNG seed 20241022.
- A difference is considered meaningful when its CI excludes zero;
  direction and magnitude are reported, not just significance.

## Reproduction

```sh
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q

python -m benchmarks.run_benchmark
python -m benchmarks.analyze_results results/raw/benchmark_seed42.csv

python -m benchmarks.run_evaluation --tasks 300 --seeds 10
python -m benchmarks.analyze_evaluation results/raw/evaluation.csv
```

Raw CSVs stay local (gitignored); processed summaries and plots land in
`results/processed/`.
