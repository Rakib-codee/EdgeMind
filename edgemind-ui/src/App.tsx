import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  executeTask,
  getState,
  scheduleTask,
  Rejected,
  type NodeState,
} from './api'
import DecisionCompare, { type PolicyOutcome } from './components/DecisionCompare'
import NodeCards from './components/NodeCards'

interface HistoryPoint {
  task: string
  baseline: number | null
  adaptive: number | null
}

export default function App() {
  const [nodes, setNodes] = useState<NodeState[]>([])
  const [apiError, setApiError] = useState<string | null>(null)
  const [computeUnits, setComputeUnits] = useState(300)
  const [budget, setBudget] = useState(500)
  const [busy, setBusy] = useState(false)
  const [baseline, setBaseline] = useState<PolicyOutcome | null>(null)
  const [adaptive, setAdaptive] = useState<PolicyOutcome | null>(null)
  const [history, setHistory] = useState<HistoryPoint[]>([])

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const s = await getState()
        if (!cancelled) {
          setNodes(s)
          setApiError(null)
        }
      } catch {
        if (!cancelled) setApiError('Cannot reach the EdgeMind API')
      }
    }
    poll()
    const id = setInterval(poll, 2000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  async function compare() {
    setBusy(true)
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
      setHistory((h) =>
        [
          ...h,
          {
            task: `${computeUnits}u/${budget}ms`,
            baseline: b.execution?.total_latency_ms ?? null,
            adaptive: a.execution?.total_latency_ms ?? null,
          },
        ].slice(-12),
      )
    } catch {
      setApiError('Request failed — is the API running?')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-zinc-100">
      <div className="mx-auto max-w-5xl px-4 py-8 space-y-8">
        <header>
          <h1 className="text-3xl font-bold">EdgeMind — Live Scheduling Demo</h1>
          <p className="mt-1 text-sm text-zinc-400">
            Adaptive edge–cloud task scheduling. Both policies below are the real
            algorithms from the repo; the environment is simulated live by the API.
          </p>
          {apiError && (
            <p className="mt-2 rounded-lg bg-red-950 px-3 py-2 text-sm text-red-300">
              {apiError}
            </p>
          )}
        </header>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-zinc-200">
            Live node state <span className="text-xs text-zinc-500">(polls /state every 2 s)</span>
          </h2>
          <NodeCards nodes={nodes} />
        </section>

        <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-4">
          <h2 className="text-lg font-semibold text-zinc-200">Submit a task</h2>
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
        </section>

        <section>
          <h2 className="mb-3 text-lg font-semibold text-zinc-200">Decisions</h2>
          <DecisionCompare baseline={baseline} adaptive={adaptive} />
        </section>

        {history.length > 0 && (
          <section className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <h2 className="mb-3 text-lg font-semibold text-zinc-200">
              Actual latency — your session history
            </h2>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={history}>
                <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
                <XAxis dataKey="task" tick={{ fill: '#a1a1aa', fontSize: 11 }} />
                <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} unit=" ms" />
                <Tooltip
                  contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }}
                  labelStyle={{ color: '#e4e4e7' }}
                />
                <Legend />
                <Bar dataKey="baseline" fill="#71717a" name="Baseline" />
                <Bar dataKey="adaptive" fill="#6366f1" name="Adaptive" />
              </BarChart>
            </ResponsiveContainer>
          </section>
        )}

        <footer className="border-t border-zinc-800 pt-4 text-xs text-zinc-500">
          EdgeMind — research project ·{' '}
          <a className="underline" href="https://github.com/Rakib-codee/EdgeMind">source</a>{' '}
          ·{' '}
          <a className="underline" href="https://edge-cloud-scheduler.streamlit.app">
            results dashboard
          </a>
        </footer>
      </div>
    </div>
  )
}
