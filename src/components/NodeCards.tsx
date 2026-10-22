import type { NodeState } from '../lib/api'

const ACCENT: Record<string, string> = {
  local: 'border-emerald-500',
  edge: 'border-amber-500',
  cloud: 'border-sky-500',
}

export default function NodeCards({ nodes }: { nodes: NodeState[] }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      {nodes.map((n) => (
        <div
          key={n.name}
          className={`rounded-xl border-l-4 ${ACCENT[n.name] ?? 'border-zinc-500'} bg-zinc-900 p-4 shadow`}
        >
          <div className="flex items-baseline justify-between">
            <h3 className="text-lg font-semibold capitalize text-zinc-100">{n.name}</h3>
            <span className="text-xs text-zinc-400">{n.compute_rate} u/ms</span>
          </div>
          <dl className="mt-3 space-y-1 text-sm text-zinc-300">
            <div className="flex justify-between">
              <dt>network</dt>
              <dd className="font-mono">{n.network_latency_ms.toFixed(1)} ms</dd>
            </div>
            <div className="flex justify-between">
              <dt>load factor</dt>
              <dd className={`font-mono ${n.load_factor > 1.3 ? 'text-red-400' : ''}`}>
                {n.load_factor.toFixed(2)}×
              </dd>
            </div>
            <div className="flex justify-between">
              <dt>queue</dt>
              <dd className={`font-mono ${n.queue_length > 3 ? 'text-red-400' : ''}`}>
                {n.queue_length} tasks
              </dd>
            </div>
          </dl>
        </div>
      ))}
    </div>
  )
}
