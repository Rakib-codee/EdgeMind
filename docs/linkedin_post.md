# LinkedIn Post — EdgeMind Showcase

Copy-paste ready. Full version below; a shorter variant follows.

---

## Version 1 — Full showcase (recommended)

🚀 **I built an Edge–Cloud Workload Orchestrator — and it's live.**

Should a task run on your phone, the nearest edge server, or the cloud?
Static rules get this wrong the moment networks and servers get busy.
So I built **EdgeMind**: an adaptive scheduler that decides execution
targets from real-time latency, load, queue length, and each task's
deadline.

**🔬 The engineering:**
▸ FastAPI backend + **Next.js 16** dashboard, deployed as **one
  Vercel project** (Python serverless + React, no CORS, one URL)
▸ Live 5-page demo — submit a task and watch both policies decide in
  real time
▸ **Real Docker worker testbed** — 3 CPU-limited containers executing
  measured CPU-bound work, not just simulation
▸ 60 automated tests, Prometheus/Grafana monitoring

**📊 The science (the part I'm most proud of):**
▸ On held-out simulation seeds: deadline misses dropped **27.3% → 2.3%**
  (~11.7× fewer), on-time completion **+11.6 pp** (bootstrap 95% CI
  excludes zero)
▸ On real workers, 20 paired runs × 4 policies with run-level bootstrap:
  queue awareness alone delivered **+8.1 pp on-time** [+6.4, +9.6]
▸ Honest finding: worker-rate calibration *alone* actually hurt (−6.9 pp)
  — it concentrated load on the cloud. Isolating that is why ablations
  matter.

Everything is reproducible: tuning/evaluation seed split, ablation
policies, pre-registered primary endpoint, preserved raw data. No
cherry-picked numbers.

🔴 **Live demo:** https://edgemind-eta.vercel.app
📈 Results dashboard: https://edge-cloud-scheduler.streamlit.app
💻 Source: https://github.com/Rakib-codee/EdgeMind

Built this while preparing for graduate study in **Cloud Computing &
Distributed Systems** — applying research methodology to an
end-to-end system, from scheduler design to statistically defensible
evaluation.

Feedback welcome! 👇

#CloudComputing #DistributedSystems #EdgeComputing #FastAPI #NextJS
#SystemDesign #Docker #Research #MastersApplications

---

## Version 2 — Short (~1100 chars)

🚀 Built an **Edge–Cloud Workload Orchestrator** — and it's live.

Static rules pick where a task runs (device / edge / cloud) and get it
wrong when networks and servers get busy. **EdgeMind** schedules
adaptively from latency, load, queue, and deadlines.

Results on held-out seeds: deadline misses **27.3% → 2.3%**, on-time
completion **+11.6pp** (bootstrap CI). On real Docker workers (20 paired
runs), ablation showed queue awareness alone gives **+8.1pp** — while
calibration alone actually *hurt* (−6.9pp). Reported honestly, with CIs,
not cherry-picked numbers.

Stack: FastAPI + Next.js 16 + Docker + Prometheus, 60 tests, one Vercel
deployment.

🔴 Live demo: https://edgemind-eta.vercel.app
💻 Source: github.com/Rakib-codee/EdgeMind

#EdgeComputing #CloudComputing #NextJS #FastAPI

---

## Notes for posting

- Attach screenshots: the Task Scheduler page (live decision comparison)
  and the Research Analytics page (bootstrap CI table) work best.
- The live demo's first request after idle may take ~1s (serverless cold
  start) — that's normal, no need to apologize for it in comments.
- Tagging suggestion: react to comments mentioning the honest-null-result
  part; it's your strongest signal of research maturity.
