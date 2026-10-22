import type { Decision, ExecutionResult } from '../lib/api'
import { Rejected } from '../lib/api'

export interface PolicyOutcome {
  decision: Decision | Rejected
  execution: ExecutionResult | null
}

function DecisionCard({
  title,
  outcome,
  accent,
}: {
  title: string
  outcome: PolicyOutcome | null
  accent: string
}) {
  if (!outcome) {
    return (
      <div className="rounded-xl border border-zinc-700 bg-zinc-900 p-5 text-zinc-500">
        <h3 className="font-semibold text-zinc-300">{title}</h3>
        <p className="mt-2 text-sm">Submit a task to see this policy's decision.</p>
      </div>
    )
  }
  const { decision, execution } = outcome
  const rejected = decision instanceof Rejected
  return (
    <div className={`rounded-xl border-2 ${accent} bg-zinc-900 p-5 shadow`}>
      <h3 className="font-semibold text-zinc-100">{title}</h3>
      {rejected ? (
        <p className="mt-3 rounded-lg bg-red-950 px-3 py-2 font-mono text-sm text-red-300">
          REJECTED — no node meets the deadline
        </p>
      ) : (
        <>
          <p className="mt-3 text-2xl font-bold capitalize text-zinc-50">
            → {(decision as Decision).selected_target}
          </p>
          <p className="mt-1 text-sm text-zinc-400">
            estimated {(decision as Decision).estimated_latency_ms} ms
          </p>
          {execution && (
            <div className="mt-3 border-t border-zinc-800 pt-3 text-sm text-zinc-300">
              <div className="flex justify-between">
                <span>actual latency</span>
                <span className="font-mono">{execution.total_latency_ms} ms</span>
              </div>
              <div className="flex justify-between">
                <span>deadline</span>
                <span
                  className={`font-mono font-semibold ${
                    execution.deadline_met ? 'text-emerald-400' : 'text-red-400'
                  }`}
                >
                  {execution.deadline_met ? 'MET' : 'MISSED'}
                </span>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

export default function DecisionCompare({
  baseline,
  adaptive,
}: {
  baseline: PolicyOutcome | null
  adaptive: PolicyOutcome | null
}) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      <DecisionCard title="Baseline (static profiles)" outcome={baseline} accent="border-zinc-600" />
      <DecisionCard title="Adaptive (live state + queue)" outcome={adaptive} accent="border-indigo-500" />
    </div>
  )
}
