import { useState } from 'react'
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
import { runBenchmark, type BenchmarkResult } from '../../lib/api'

export default function ExperimentPage() {
  const [tasks, setTasks] = useState(100)
  const [seed, setSeed] = useState(42)
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<BenchmarkResult | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function run() {
    setBusy(true)
    setError(null)
    try {
      setResult(await runBenchmark(tasks, seed))
    } catch {
      setError('Benchmark request failed — is the API running?')
    } finally {
      setBusy(false)
    }
  }

  const chart = result
    ? (['baseline', 'adaptive'] as const).map((p) => ({
        policy: p,
        'on-time rate': result.policies[p].overall_on_time_rate,
        'miss rate (completed)': result.policies[p].completed_miss_rate ?? 0,
      }))
    : []

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold">Experiment Control Panel</h2>
        <p className="text-sm text-zinc-400">
          Run a paired mini-benchmark live on the API. Deterministic: same seed →
          same result. Uses the same workload generator as the research pipeline.
        </p>
      </header>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5 space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          <label className="block text-sm text-zinc-300">
            Tasks: <span className="font-mono text-zinc-100">{tasks}</span>
            <input
              type="range" min={10} max={500} step={10} value={tasks}
              onChange={(e) => setTasks(Number(e.target.value))}
              className="mt-2 w-full accent-indigo-500"
            />
          </label>
          <label className="block text-sm text-zinc-300">
            Random seed
            <input
              type="number" min={0} max={999999} value={seed}
              onChange={(e) => setSeed(Number(e.target.value))}
              className="mt-2 w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-1.5 font-mono text-zinc-100"
            />
          </label>
        </div>
        <button
          onClick={run}
          disabled={busy}
          className="rounded-lg bg-indigo-600 px-5 py-2 font-semibold text-white hover:bg-indigo-500 disabled:opacity-50"
        >
          {busy ? 'Running…' : '▶ Run paired benchmark'}
        </button>
        {error && (
          <p className="rounded-lg bg-red-950 px-3 py-2 text-sm text-red-300">{error}</p>
        )}
      </div>

      {result && (
        <>
          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <h3 className="mb-3 font-semibold text-zinc-200">
              Results — {result.tasks} tasks, seed {result.seed}
            </h3>
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase text-zinc-500">
                  <th className="pb-2">Metric</th>
                  <th className="pb-2">Baseline</th>
                  <th className="pb-2">Adaptive</th>
                </tr>
              </thead>
              <tbody>
                {(
                  [
                    ['submitted', 'Submitted'],
                    ['rejected', 'Rejected'],
                    ['successful', 'Successful'],
                    ['on_time', 'On time'],
                    ['overall_on_time_rate', 'Overall on-time rate'],
                    ['completed_miss_rate', 'Miss rate (completed)'],
                    ['latency_mean_ms', 'Mean latency (ms)'],
                    ['latency_p95_ms', 'p95 latency (ms)'],
                  ] as const
                ).map(([key, label]) => (
                  <tr key={key} className="border-t border-zinc-800 text-zinc-300">
                    <td className="py-1.5">{label}</td>
                    <td className="py-1.5 font-mono">
                      {result.policies.baseline[key] ?? '—'}
                    </td>
                    <td className="py-1.5 font-mono">
                      {result.policies.adaptive[key] ?? '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chart}>
                <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
                <XAxis dataKey="policy" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
                <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} domain={[0, 1]} />
                <Tooltip contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }} />
                <Legend />
                <Bar dataKey="on-time rate" fill="#34d399" />
                <Bar dataKey="miss rate (completed)" fill="#f87171" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </>
      )}
    </div>
  )
}
