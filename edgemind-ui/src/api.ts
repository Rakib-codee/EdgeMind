export interface NodeState {
  name: string
  network_latency_ms: number
  compute_rate: number
  load_factor: number
  queue_length: number
}

export interface Decision {
  task_id: string
  selected_target: string
  estimated_latency_ms: number
  scheduler: string
}

export interface ExecutionResult {
  task_id: string
  target: string
  success: boolean
  network_latency_ms: number
  compute_duration_ms: number
  total_latency_ms: number
  deadline_met: boolean
}

export interface TaskInput {
  task_id: string
  compute_units: number
  max_latency_ms: number
}

const API: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function post<T>(path: string, task: TaskInput, policy: string): Promise<T> {
  const res = await fetch(`${API}${path}?policy=${policy}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task),
  })
  if (res.status === 422) {
    // Scheduler rejection is a legitimate outcome, not an error.
    throw new Rejected()
  }
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}

export class Rejected extends Error {}

export async function getState(): Promise<NodeState[]> {
  const res = await fetch(`${API}/state`)
  if (!res.ok) throw new Error(`API error ${res.status}`)
  return res.json()
}

export function scheduleTask(task: TaskInput, policy: string): Promise<Decision> {
  return post<Decision>('/schedule', task, policy)
}

export function executeTask(task: TaskInput, policy: string): Promise<ExecutionResult> {
  return post<ExecutionResult>('/execute', task, policy)
}
