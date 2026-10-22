import Papa from 'papaparse'

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

export interface PolicyBenchmark {
  submitted: number
  rejected: number
  successful: number
  on_time: number
  overall_on_time_rate: number
  completed_miss_rate: number | null
  latency_mean_ms: number | null
  latency_p95_ms: number | null
}

export interface BenchmarkResult {
  tasks: number
  seed: number
  policies: Record<'baseline' | 'adaptive', PolicyBenchmark>
}

const API: string = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function post<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, init)
  if (res.status === 422) throw new Rejected()
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
  return post<Decision>(`/schedule?policy=${policy}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task),
  })
}

export function executeTask(task: TaskInput, policy: string): Promise<ExecutionResult> {
  return post<ExecutionResult>(`/execute?policy=${policy}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(task),
  })
}

export function runBenchmark(tasks: number, seed: number): Promise<BenchmarkResult> {
  return post<BenchmarkResult>(`/benchmark?tasks=${tasks}&seed=${seed}`, { method: 'POST' })
}

/** Load a committed aggregate CSV shipped with the UI (public/data/). */
export function loadCsv<T = Record<string, string>>(name: string): Promise<T[]> {
  return new Promise((resolve, reject) => {
    Papa.parse<T>(`${import.meta.env.BASE_URL}data/${name}`, {
      download: true,
      header: true,
      dynamicTyping: true,
      complete: (r) => resolve(r.data),
      error: reject,
    })
  })
}
