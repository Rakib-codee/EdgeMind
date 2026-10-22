import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { useApp } from '../state'

function Kpi({ label, value, sub }: { label: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <p className="text-xs uppercase tracking-wide text-zinc-500">{label}</p>
      <p className="mt-1 text-2xl font-bold">{value}</p>
      {sub && <p className="mt-1 text-xs text-zinc-500">{sub}</p>}
    </div>
  )
}

export default function OverviewPage() {
  const { nodes, apiOnline, comparisons } = useApp()

  const executed = comparisons.filter(
    (c) => c.baselineLatency != null || c.adaptiveLatency != null,
  )
  const onTime = executed.filter(
    (c) => c.deadlineMetAdaptive || c.deadlineMetBaseline,
  ).length
  const avgAdaptive =
    executed.length > 0
      ? executed.reduce((s, c) => s + (c.adaptiveLatency ?? 0), 0) /
        executed.filter((c) => c.adaptiveLatency != null).length
      : null

  const chart = comparisons.map((c, i) => ({
    i: i + 1,
    baseline: c.baselineLatency,
    adaptive: c.adaptiveLatency,
  }))

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold">System Overview</h2>
        <p className="text-sm text-zinc-400">
          Live session metrics for the simulated edge–cloud environment.
        </p>
      </header>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Kpi label="API status" value={apiOnline ? 'Online' : 'Offline'} sub="FastAPI backend" />
        <Kpi label="Active nodes" value={String(nodes.length)} sub="local · edge · cloud" />
        <Kpi
          label="Tasks compared"
          value={String(comparisons.length)}
          sub="this browser session"
        />
        <Kpi
          label="Avg adaptive latency"
          value={avgAdaptive != null ? `${avgAdaptive.toFixed(1)} ms` : '—'}
          sub={executed.length ? `${onTime}/${executed.length} deadlines met` : 'no tasks yet'}
        />
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="mb-3 font-semibold text-zinc-200">
          Session latency — baseline vs adaptive
        </h3>
        {chart.length === 0 ? (
          <p className="text-sm text-zinc-500">
            No tasks yet — submit one from the Task Scheduler page.
          </p>
        ) : (
          <ResponsiveContainer width="100%" height={240}>
            <AreaChart data={chart}>
              <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
              <XAxis dataKey="i" tick={{ fill: '#a1a1aa', fontSize: 11 }} />
              <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} unit=" ms" />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }}
              />
              <Area type="monotone" dataKey="baseline" stroke="#71717a" fill="#71717a" fillOpacity={0.25} name="Baseline" />
              <Area type="monotone" dataKey="adaptive" stroke="#6366f1" fill="#6366f1" fillOpacity={0.3} name="Adaptive" />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="mb-3 font-semibold text-zinc-200">Recent decisions</h3>
        {comparisons.length === 0 ? (
          <p className="text-sm text-zinc-500">Nothing yet.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs uppercase text-zinc-500">
                <th className="pb-2">Task</th>
                <th className="pb-2">Baseline</th>
                <th className="pb-2">Adaptive</th>
                <th className="pb-2">Deadline (B / A)</th>
              </tr>
            </thead>
            <tbody>
              {[...comparisons].reverse().slice(0, 8).map((c, i) => (
                <tr key={i} className="border-t border-zinc-800 text-zinc-300">
                  <td className="py-2 font-mono">{c.task}</td>
                  <td className="py-2">
                    {c.baselineTarget}
                    {c.baselineLatency != null && (
                      <span className="text-zinc-500"> · {c.baselineLatency.toFixed(0)} ms</span>
                    )}
                  </td>
                  <td className="py-2">
                    {c.adaptiveTarget}
                    {c.adaptiveLatency != null && (
                      <span className="text-zinc-500"> · {c.adaptiveLatency.toFixed(0)} ms</span>
                    )}
                  </td>
                  <td className="py-2 font-mono">
                    {c.deadlineMetBaseline == null ? '—' : c.deadlineMetBaseline ? '✅' : '❌'}
                    {' / '}
                    {c.deadlineMetAdaptive == null ? '—' : c.deadlineMetAdaptive ? '✅' : '❌'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
