import { useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { loadCsv } from '../api'

interface SeedRow {
  seed: number
  variant: string
  overall_ontime_rate: number
  latency_mean_ms: number
  accepted_deadline_miss_rate: number
}

interface BootRow {
  comparison: string
  metric: string
  n_runs: number
  mean_diff: number
  ci_low: number
  ci_high: number
}

export default function AnalyticsPage() {
  const [perSeed, setPerSeed] = useState<SeedRow[]>([])
  const [boot, setBoot] = useState<BootRow[]>([])
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      loadCsv<SeedRow>('sim_per_seed.csv'),
      loadCsv<BootRow>('real_v2_bootstrap.csv'),
    ])
      .then(([s, b]) => {
        setPerSeed(s)
        setBoot(b)
      })
      .catch(() => setErr('Could not load aggregate data'))
  }, [])

  const base = perSeed.filter((r) => r.variant === 'baseline')
  const adap = perSeed.filter((r) => r.variant === 'adaptive')
  const bySeed = base.map((b) => ({
    seed: b.seed,
    baseline: b.overall_ontime_rate,
    adaptive: adap.find((a) => a.seed === b.seed)?.overall_ontime_rate,
  }))

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold">Research & Benchmark Analytics</h2>
        <p className="text-sm text-zinc-400">
          Committed aggregate results from the reproducible evaluation pipeline.
          Simulation latencies are simulated; real-worker results are measured on
          local Docker containers.
        </p>
      </header>

      {err && <p className="rounded-lg bg-red-950 px-3 py-2 text-sm text-red-300">{err}</p>}

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="mb-1 font-semibold text-zinc-200">
          Overall on-time rate per seed — 30 confirmatory seeds
        </h3>
        <p className="mb-3 text-xs text-zinc-500">
          Seeds 200–229, disjoint from tuning (42–51) and held-out (100–109) sets.
        </p>
        <ResponsiveContainer width="100%" height={260}>
          <LineChart data={bySeed}>
            <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
            <XAxis dataKey="seed" tick={{ fill: '#a1a1aa', fontSize: 11 }} />
            <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} domain={[0, 1]} />
            <Tooltip contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }} />
            <Legend />
            <Line type="monotone" dataKey="baseline" stroke="#71717a" dot={false} />
            <Line type="monotone" dataKey="adaptive" stroke="#6366f1" dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="mb-1 font-semibold text-zinc-200">
          Real-worker paired bootstrap 95% CIs (20 runs)
        </h3>
        <p className="mb-3 text-xs text-zinc-500">
          B−A isolates calibration; C−B isolates queue awareness; C−A is the total effect.
        </p>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-zinc-500">
                <th className="pb-2">Comparison</th>
                <th className="pb-2">Metric</th>
                <th className="pb-2">Mean Δ</th>
                <th className="pb-2">95% CI</th>
              </tr>
            </thead>
            <tbody>
              {boot.map((r, i) => (
                <tr key={i} className="border-t border-zinc-800 text-zinc-300">
                  <td className="py-1.5 font-mono">{r.comparison}</td>
                  <td className="py-1.5">{r.metric}</td>
                  <td className="py-1.5 font-mono">{Number(r.mean_diff).toFixed(4)}</td>
                  <td className="py-1.5 font-mono text-zinc-400">
                    [{Number(r.ci_low).toFixed(4)}, {Number(r.ci_high).toFixed(4)}]
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="mb-3 font-semibold text-zinc-200">Miss-rate difference with CI</h3>
        <ResponsiveContainer width="100%" height={220}>
          <BarChart
            data={boot
              .filter((r) => r.metric === 'completed_deadline_miss_rate')
              .map((r) => ({
                comparison: r.comparison,
                diff: Number((r.mean_diff * 100).toFixed(1)),
              }))}
          >
            <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
            <XAxis dataKey="comparison" tick={{ fill: '#a1a1aa', fontSize: 12 }} />
            <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} unit=" pp" />
            <Tooltip contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }} />
            <Bar dataKey="diff" fill="#6366f1" name="deadline-miss Δ (pp)" />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}
