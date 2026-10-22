import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import NodeCards from '../NodeCards'
import { useApp } from '../../lib/state'

export default function NodeMonitorPage() {
  const { nodes, nodeHistory } = useApp()

  return (
    <div className="space-y-6">
      <header>
        <h2 className="text-2xl font-bold">Edge–Cloud Node Monitor</h2>
        <p className="text-sm text-zinc-400">
          Live state of the simulated execution nodes (polls the API every 2 s).
        </p>
      </header>

      <NodeCards nodes={nodes} />

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="mb-3 font-semibold text-zinc-200">Network latency over time</h3>
        {nodeHistory.length < 2 ? (
          <p className="text-sm text-zinc-500">Collecting samples…</p>
        ) : (
          <ResponsiveContainer width="100%" height={260}>
            <LineChart data={nodeHistory}>
              <CartesianGrid stroke="#3f3f46" strokeDasharray="3 3" />
              <XAxis dataKey="t" tick={{ fill: '#a1a1aa', fontSize: 10 }} />
              <YAxis tick={{ fill: '#a1a1aa', fontSize: 11 }} unit=" ms" />
              <Tooltip
                contentStyle={{ background: '#18181b', border: '1px solid #3f3f46' }}
              />
              <Line type="monotone" dataKey="local" stroke="#34d399" dot={false} />
              <Line type="monotone" dataKey="edge" stroke="#fbbf24" dot={false} />
              <Line type="monotone" dataKey="cloud" stroke="#38bdf8" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-5">
        <h3 className="mb-3 font-semibold text-zinc-200">Load & queue detail</h3>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase text-zinc-500">
              <th className="pb-2">Node</th>
              <th className="pb-2">Compute rate</th>
              <th className="pb-2">Load factor</th>
              <th className="pb-2">Queue</th>
              <th className="pb-2">Network</th>
            </tr>
          </thead>
          <tbody>
            {nodes.map((n) => (
              <tr key={n.name} className="border-t border-zinc-800 text-zinc-300">
                <td className="py-2 capitalize font-semibold">{n.name}</td>
                <td className="py-2 font-mono">{n.compute_rate} u/ms</td>
                <td className="py-2 font-mono">{n.load_factor.toFixed(2)}×</td>
                <td className="py-2 font-mono">{n.queue_length}</td>
                <td className="py-2 font-mono">{n.network_latency_ms.toFixed(1)} ms</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
