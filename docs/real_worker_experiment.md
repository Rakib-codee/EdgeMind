# Real-Worker Validation Experiment

This document describes the containerized real-worker experiment
(`benchmarks/run_real_experiment.py`), which complements the simulation
pipeline with measured wall-clock execution. It does **not** replace or
modify any simulation results. All simulation findings remain
simulation-only; everything in this document is a local Docker
measurement.

## What is measured vs. simulated

| Quantity | Source | Clock |
|---|---|---|
| End-to-end latency (`e2e_latency_ms`) | client wall clock at submit vs. response | `time.time()` |
| Queue wait (`queue_wait_ms`) | worker: enqueue → execution start | `time.perf_counter_ns()` |
| Execution duration (`execution_ms`) | worker: execution start → end | `time.perf_counter_ns()` |
| Scheduling decision cost (`scheduling_overhead_ms`) | client: decision call wall time only | `time.perf_counter_ns()` |

Monotonic clocks are used for durations so NTP adjustments cannot
distort them; wall-clock timestamps (`submit_ts`, `response_ts`, and the
worker's `queued_at`/`started_at`/`finished_at`) are recorded for
ordering and throughput windows. `scheduling_overhead_ms` measures only
the decision function — full scheduling latency (client queuing, HTTP
dispatch) is **not** instrumented and is reported as unavailable.

## Setup

- `compose.real.yaml` starts three workers from the project image with
  CPU limits: `local` 0.25, `edge` 0.5, `cloud` 1.0 CPUs.
- Each worker (`app/real_worker.py`) executes a deterministic SHA-256
  hash chain whose length is proportional to the task's
  `compute_units`, through a single-slot FIFO queue. Workers
  self-calibrate at startup and on demand (`POST /calibrate`); the
  runner recalibrates once per run, outside task measurement, and
  records the per-run rates in the CSV.
- **Network latency is not emulated.** All containers share one Docker
  bridge network; calibrated policies use `network_latency_ms = 0`.
  This is a recorded limitation, not an oversight.

## v2: pre-registered fair comparison

The v2 design separates the effect of **rate calibration** from
**queue-aware scheduling**. Registered before data collection
(commit history predates the v2 run).

### Policies and information access

| | A — original baseline | B — calibrated baseline | C — adaptive | D — ablation (exploratory) |
|---|---|---|---|---|
| Placement rule | min est. latency among feasible | min est. latency among feasible (same `select_target` code path) | min cost = latency + 200·failure_risk (frozen `DEFAULT_WEIGHTS`) | C with failure weight 0 |
| Compute rates | static assumed (10/30/100 units/ms) | per-run measured | per-run measured (same values as B) | per-run measured |
| Queue observation | none | none | own outstanding count | own outstanding count |
| Network latency | static assumed (0/8/35 ms) | 0 | 0 | 0 |
| Feasibility check | est ≤ budget, queue = 0 | est ≤ budget, queue = 0 | est ≤ budget, queue-inclusive | as C |

All policies reject tasks whose estimated latency exceeds the budget;
they differ in estimate accuracy and queue inclusion, not in the
existence of admission control. **B − A isolates calibration;
C − B isolates queue awareness + the failure-risk term; C − A is the
total effect.** D is exploratory, runs last in every run under a fixed
order, and is excluded from primary comparisons. No weights were tuned
on v2 data.

### Protocol

- 20 independent runs × 100 tasks per policy. Workload seed =
  500 + run index (fresh range, disjoint from simulation tuning seeds
  42–51, held-out 100–109, confirmatory 200–229, and Phase 3 seed 42).
- Identical task IDs, compute units, and budgets for all policies
  within a run (verified in analysis).
- `--budget-scale 5`, fixed in Phase 3 before v2 and unchanged.
- A/B/C execution order: Latin square over all six permutations
  (run r → permutation r mod 6); D always last.
- Between policy blocks: all in-flight tasks complete, then a 5 s
  cooldown. Warm-up: worker startup calibration + 2 s idle, unmeasured.
- Recorded per run: measured worker rates, host 1-minute load average
  before/after, Docker version, host OS/arch, CPU limits, container
  image IDs, code commit, dependency versions (manifest).

### Primary outcomes (populations fixed in advance)

1. **Overall on-time completion rate** = on-time successful completions
   / all submitted tasks. *(Primary endpoint.)*
2. **Rejection rate** = rejected / all submitted.
3. **Overall success rate** = successful / all submitted.
4. **Completed-task deadline-miss rate** = 1 − on_time/successful.
   Denominator is *successful completions only* (renamed from the v1
   `accepted_deadline_miss_rate`, which overstated its population).
5. **Mean and p95 end-to-end latency**, successful completions only.
6. **Queue wait** (worker monotonic clock: dequeue → execution start)
   and execution duration, successful completions.
7. **Scheduling decision cost** (decision call only), all tasks.

Both pooled task-level descriptives and per-run summaries are reported.
The **run is the only inferential unit**; individual tasks within a run
are not independent.

### Statistical analysis

Paired run-level percentile bootstrap: resample run indices with
replacement, keeping each sampled run's policy values together;
statistic = mean paired difference; 10,000 replicates; seed 20261022
(recorded). With n = 20 runs, percentile intervals are approximate and
can be narrow-biased; per-run values are reported alongside intervals,
and no significance claim is made from point estimates alone. Three
policy pairs × several metrics are reported; the primary endpoint is
the overall on-time rate for C − B, B − A, C − A.

## v1: preliminary Phase 3 results (historical, superseded by v2)

The v1 run set (3 runs, policies A and C only, seed 42 workload,
`results/raw/real_experiment_v1.csv`) is preserved unchanged. Its
findings — adaptive rejects 64%, accepted-task miss rate 41.7% vs
80.7%, mean e2e 1131 ms vs 2026 ms — are **preliminary**: 3 runs
cannot characterize variability, and the A-vs-C comparison confounds
calibration with queue awareness (the exact confound v2 separates).
Treat v1 numbers as motivation for v2, not as conclusions.

## Reproducing

```bash
docker compose -f compose.real.yaml up -d --build
python -m benchmarks.run_real_experiment --tasks 100 --runs 20 --seed 500 --budget-scale 5
python -m benchmarks.analyze_real
docker compose -f compose.real.yaml down
```

Outputs: `results/raw/real_experiment_v2.csv` (raw rows),
`results/raw/real_experiment_v2.manifest.json` (provenance: git commit,
host/Docker metadata, dependency versions, config, checksums),
`results/processed/real_experiment_v2_{summary,paired_diffs,bootstrap}.csv`.
Raw results are gitignored. v1 outputs are never overwritten.

## Limitations

- Three containers on one host are **not** a geographically distributed
  edge–cloud deployment. No wide-area latency, no independent machines.
- Results vary with host load, Docker CPU throttling, OS scheduling,
  and machine configuration; absolute numbers are host-specific.
- Identical task inputs do not guarantee identical runtime
  trajectories: host load drifts between policy blocks within a run;
  counterbalancing, not pairing, mitigates this.
- The workload's CPU-bound hash chain stresses CPU only — no memory,
  I/O, or network transfer costs.
- Worker rates are recalibrated per run but constant within a run.
- No execution failures have been observed in any real run; the
  failure-risk term of the adaptive cost is a modeled penalty with no
  measured real-world failures to validate against.
- Resource utilization and full scheduling latency are not
  instrumented (reported as unavailable).
- n = 20 runs supports approximate intervals, not tight inference;
  p95 per run rests on few tail observations when the successful
  population is small.
