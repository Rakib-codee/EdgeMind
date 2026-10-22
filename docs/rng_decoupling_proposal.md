# Design Proposal: RNG Stream Decoupling (not implemented)

Status: **proposal only**. No code changes. Implementation requires
explicit approval after review.

## Background

`DynamicEnvironment` uses a single RNG (`env.rng`) for two purposes:
exogenous state evolution (latency/load random walks, `_evolve`) and
queue draining (`_drain_queues` in `benchmarks/run_benchmark.py`).
Queue lengths are policy-dependent, so the two policies consume
different amounts of randomness per tick; after the first queue
difference, their stochastic environment trajectories diverge.

## Options

### A. Current behavior (shared stream)

- Paired task inputs; environment trajectories share the seed and
  dynamics but diverge once queues differ.
- Pros: simple; a closed-loop property — the environment genuinely
  responds to each policy's decisions, which is realistic.
- Cons: exogenous noise (latency spikes, load drift) is not
  bit-identical between policies after divergence, adding variance to
  paired comparisons.

### B. Independent streams per process

Separate RNGs for: (1) exogenous evolution, (2) queue draining,
(3) execution jitter (already independent per task via
`random.Random(f"{seed}-{task_id}")`).

- Pros: exogenous trajectories become bit-identical between policies —
  the strongest form of pairing; paired differences then isolate the
  policy effect more cleanly, reducing variance.
- Cons: changes simulator semantics; all existing raw results become
  non-comparable artifacts of an older simulator version.

### C. Common random numbers (CRN)

Drive exogenous events from a stream keyed only by (seed, tick), so
both policies see identical noise regardless of their decisions.

- Pros: classic variance-reduction technique for comparing policies;
  pairing is exact.
- Cons: same semantic change as B; queue-drain randomness still
  policy-coupled unless draining is also made deterministic
  (e.g., drain probability replaced by a deterministic schedule).

## Fair comparison across simulator versions

If implemented, the change must ship as a new experimental version:

1. Keep current code/results untouched (v2 and confirmatory_v1 remain
   the reference).
2. Implement behind an explicit flag or a new module; document which
   simulator version produced each result file via the manifest.
3. Re-run tuning seeds (42–51) and confirmatory seeds (200–229) under
   the new simulator; report old-vs-new on identical seeds.
4. Only then consider updating defaults, in a separate changeset.

## Risks

- Semantic drift: subtle behavioural differences between simulator
  versions could be mistaken for policy effects.
- Effort vs value: the current design already pairs workloads and
  seeds; divergence adds variance but not bias.

## Recommendation

**Defer.** The audit found no evidence of bias from the shared stream,
and the confirmatory run (n = 30) already detects the reported effects
with comfortable margins. CRN (option C) is the scientifically
strongest upgrade if the paper later needs tighter paired variance, but
it is a simulator-semantics change that should be decided with the
research supervisor, not as an engineering drive-by. Estimated effort:
small (one environment flag + one rerun of the full pipeline).
