# Real-Worker Validation Experiment

This document describes the containerized real-worker experiment
(`benchmarks/run_real_experiment.py`), which complements the simulation
pipeline with measured wall-clock execution. It does **not** replace or
modify any simulation results.

## What is measured vs. simulated

All earlier EdgeMind results are simulated. This experiment measures
real quantities:

| Quantity | Source | Clock |
|---|---|---|
| End-to-end latency (`e2e_latency_ms`) | client wall clock at submit vs. response | `time.time()` |
| Queue wait (`queue_wait_ms`) | worker: enqueue → execution start | `time.perf_counter_ns()` |
| Execution duration (`execution_ms`) | worker: execution start → end | `time.perf_counter_ns()` |
| Scheduling overhead (`scheduling_overhead_ms`) | client: policy decision wall time | `time.perf_counter_ns()` |

Monotonic clocks are used for durations so NTP adjustments cannot
distort them; wall-clock timestamps (`submit_ts`, `response_ts`, and the
worker's `queued_at`/`started_at`/`finished_at`) are recorded for
ordering and throughput windows.

## Setup

- `compose.real.yaml` starts three workers from the project image with
  CPU limits: `local` 0.25, `edge` 0.5, `cloud` 1.0 CPUs.
- Each worker (`app/real_worker.py`) executes a deterministic SHA-256
  hash chain whose length is proportional to the task's
  `compute_units`, through a single-slot FIFO queue. At startup each
  worker self-calibrates and reports its measured rate via `/state`.
- **Network latency is not emulated.** All containers share one Docker
  bridge network; adaptive node states use `network_latency_ms = 0`.
  This is a recorded limitation, not an oversight.

## Policies and fairness

- Policies are unchanged from the simulation (`select_target`,
  `select_target_adaptive`).
- Baseline selects from static `DEFAULT_NODES` profiles — its defining
  behavior. Those assumed rates (10/30/100 units/ms) differ from the
  measured container rates, which is part of the comparison.
- Adaptive observes measured compute rates, `network_latency_ms = 0`,
  and `queue_length` = the scheduler's own count of submitted but
  not-yet-completed tasks per worker. Polled worker state is stale
  under burst submission, so the scheduler's outstanding count is the
  accurate queue view at decision time.
- Workload: `generate_tasks` (same generator as the simulation) with
  identical task sequences for both policies within a run. Run order
  alternates AB/BA across runs to reduce order effects.
- Workload budgets are calibrated to simulated node rates, which are
  far higher than throttled container rates. `--budget-scale 5`
  multiplies every `max_latency_ms` uniformly (identical for both
  policies) so deadlines are feasible under real execution speeds. The
  scale factor is recorded in the run manifest.

## Metric definitions and populations

Per (run, policy) — see `benchmarks/analyze_real.py`:

- **submitted**: all tasks generated for the policy in the run.
- **rejected**: no feasible node at decision time; never sent to a
  worker; latency fields are empty (structurally absent, not zero).
- **accepted**: submitted − rejected.
- **successful**: accepted tasks whose execution returned success.
- **on_time**: successful tasks with `e2e_latency_ms <= max_latency_ms`.
- **accepted_deadline_miss_rate**: 1 − on_time/successful.
- **overall_success_rate**: successful / submitted.
- **overall_on_time_rate**: on_time / submitted.
- **Latency statistics** (mean/median/p95): successful executions only.
- **throughput**: accepted / (last response − first submit) per run.
- **failure**: a separate timeout category is not implemented; a task
  either completes (success/failure from the worker) or the request
  fails (recorded in `error`).

## Reproducing

```bash
docker compose -f compose.real.yaml up -d --build
python -m benchmarks.run_real_experiment --tasks 100 --runs 3 --seed 42 --budget-scale 5
python -m benchmarks.analyze_real
docker compose -f compose.real.yaml down
```

Outputs: `results/raw/real_experiment_v1.csv` (raw rows),
`results/raw/real_experiment_v1.manifest.json` (provenance: git commit,
dependency versions, config, checksums),
`results/processed/real_experiment_v1_summary.csv` and
`real_experiment_v1_paired_diffs.csv`. Raw results are gitignored; the
manifest records the code commit and configuration of the run.

## Results (first run set)

Command: `python -m benchmarks.run_real_experiment --tasks 100 --runs 3
--seed 42 --budget-scale 5` (100 tasks per policy per run, 3 runs,
AB/BA order). Measured worker rates on this host: local 1.84, edge
6.71, cloud 14.21 units/ms. Absolute values are host-specific.

Aggregate across runs (mean of run-level values):

| Metric (population) | Baseline | Adaptive | Δ (adaptive − baseline) |
|---|---:|---:|---:|
| Rejection rate (submitted) | 0.0% | 64.0% | +64.0 pp |
| Overall success rate (submitted) | 100% | 36.0% | −64.0 pp |
| Overall on-time rate (submitted) | 18.7% | 21.0% | +2.3 pp |
| Accepted deadline-miss rate (successful) | 80.7% | 41.7% | −39.0 pp |
| Mean e2e latency (successful) | 2026 ms | 1131 ms | −895 ms |
| p95 e2e latency (successful) | 7361 ms | 2900 ms | −4461 ms |
| Mean queue wait (successful) | 1815 ms | 959 ms | −856 ms |
| Mean execution time (successful) | 107 ms | 119 ms | +12 ms |
| Scheduling overhead (all tasks) | 0.005 ms | 0.006 ms | +0.001 ms |

Per-run paired differences are in
`results/processed/real_experiment_v1_paired_diffs.csv`; with 3 runs
they are reported per run, without confidence intervals.

Interpretation, limited to this setup:

- Baseline's static profiles (10/30/100 units/ms) are optimistic
  against the measured container rates (1.8/6.7/14.2), so it rejects
  nothing and overloads the cloud worker; queue wait dominates its
  latency (mean 1.8 s of a 2.0 s e2e mean).
- Adaptive's admission control rejects tasks whose budgets are
  infeasible at measured rates, so its accepted tasks see ~40 pp fewer
  deadline misses and ~45% lower mean latency — the same
  rejection-vs-completion trade-off seen in simulation, now with
  measured wall-clock latency and real queueing.
- Overall on-time completion is roughly equal (within ±5 pp per run):
  the deadline protection is paid for entirely by rejections.
- Scheduling overhead of the adaptive policy is real but negligible on
  this host (~6 µs per decision vs ~5 µs baseline).
- No execution failures occurred in any run; the failure-risk term of
  the adaptive cost function is a modeled penalty, and there are no
  measured real-world failures to validate it against here.

## Limitations

- Three containers on one host are **not** a geographically distributed
  edge–cloud deployment. No wide-area latency, no independent machines.
- Results vary with host load, Docker CPU throttling, OS scheduling,
  and machine configuration; absolute numbers are host-specific.
- The workload's CPU-bound hash chain stresses CPU only — no memory,
  I/O, or network transfer costs.
- With 3 runs, per-run paired differences are reported without
  bootstrap intervals; run-level variability is shown instead of a
  confidence interval.
