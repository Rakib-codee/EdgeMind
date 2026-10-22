import { useState } from 'react'
import {
  executeTask,
  Rejected,
  scheduleTask,
  type Decision,
  type ExecutionResult,
} from '../../lib/api'
import DecisionCompare, { type PolicyOutcome } from '../DecisionCompare'
import { useApp } from '../../lib/state'

export default function SchedulerPage() {
  const { addComparison } = useApp()
  const [computeUnits, setComputeUnits] = useState(300)
  const [budget, setBudget] = useState(500)
  const [busy, setBusy] = useState(false)
  const [baseline, setBaseline] = useState<PolicyOutcome | null>(null)
  const [adaptive, setAdaptive] = useState<PolicyOutcome | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function compare() {
    setBusy(true)
    setError(null)
    const task = {
      task_id: `ui-${Date.now()}`,
      compute_units: computeUnits,
      max_latency_ms: budget,
    }
    const run = async (policy: string): Promise<PolicyOutcome> => {
      try {
        const decision = await scheduleTask(task, policy)
        const execution = await executeTask(task, policy)
        return { decision, execution }
      } catch (e) {
        if (e instanceof Rejected) return { decision: e, execution: null }
        throw e
      }
    }
    try {
      const [b, a] = await Promise.all([run('baseline'), run('adaptive')])
      setBaseline(b)
      setAdaptive(a)
      const targetOf = (o: PolicyOutcome) =>
        o.decision instanceof Rejected ? 'rejected' : (o.decision as Decision).selected_target
      const latencyOf = (o: PolicyOutcome) =>
        (o.execution as ExecutionResult | null)?.total_latency_ms ?? null
      addComparison({
        task: `${computeUnits}u / ${budget}ms`,
        baselineLatency: latencyOf(b),
        adaptiveLatency: latencyOf(a),
        baselineTarget: targetOf(b),
        adaptiveTarget: targetOf(a),
        deadlineMetBaseline: b.execution?.deadline_met ?? null,
        deadlineMetAdaptive: a.execution?.deadline_met ?? null,
        at: new Date(),
      })
    } catch {
      setError('Request failed — is the API running?')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold">Task Scheduler</h2>
        <p className="text-sm text-zinc-400">
          Submit a task — both real policies decide live, then execute against the
          same simulated node state.
        </p>
      </header>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <label className="block text-sm text-zinc-300">
            Task size: <span className="font-mono text-zinc-100">{computeUnits} units</span>
            <input
              type="range" min={10} max={2000} step={10} value={computeUnits}
              onChange={(e) => setComputeUnits(Number(e.target.value))}
              className="mt-2 w-full accent-indigo-500"
            />
          </label>
          <label className="block text-sm text-zinc-300">
            Deadline: <span className="font-mono text-zinc-100">{budget} ms</span>
            <input
              type="range" min={50} max={3000} step={50} value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className="mt-2 w-full accent-indigo-500"
            />
          </label>
        </div>
        <button
          onClick={compare}
          disabled={busy}
          className="rounded-lg bg-indigo-600 px-5 py-2 font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {busy ? 'Scheduling…' : '⚡ Run both policies'}
        </button>
        {error && (
          <p className="rounded-lg bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>
        )}
      </div>

      <DecisionCompare baseline={baseline} adaptive={adaptive} />
    </div>
  )
}
