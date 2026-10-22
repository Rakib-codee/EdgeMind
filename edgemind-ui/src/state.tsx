import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from 'react'
import { getState, type NodeState } from './api'

export interface ComparisonRecord {
  task: string
  baselineLatency: number | null
  adaptiveLatency: number | null
  baselineTarget: string
  adaptiveTarget: string
  deadlineMetBaseline: boolean | null
  deadlineMetAdaptive: boolean | null
  at: Date
}

interface AppState {
  nodes: NodeState[]
  apiOnline: boolean
  nodeHistory: { t: string; [node: string]: number | string }[]
  comparisons: ComparisonRecord[]
  addComparison: (c: ComparisonRecord) => void
}

const Ctx = createContext<AppState | null>(null)

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [nodes, setNodes] = useState<NodeState[]>([])
  const [apiOnline, setApiOnline] = useState(false)
  const [nodeHistory, setNodeHistory] = useState<AppState['nodeHistory']>([])
  const [comparisons, setComparisons] = useState<ComparisonRecord[]>([])

  useEffect(() => {
    let cancelled = false
    const poll = async () => {
      try {
        const s = await getState()
        if (cancelled) return
        setNodes(s)
        setApiOnline(true)
        const t = new Date().toLocaleTimeString()
        setNodeHistory((h) =>
          [
            ...h,
            Object.fromEntries([
              ['t', t],
              ...s.map((n) => [n.name, n.network_latency_ms]),
            ]),
          ].slice(-60),
        )
      } catch {
        if (!cancelled) setApiOnline(false)
      }
    }
    poll()
    const id = setInterval(poll, 2000)
    return () => {
      cancelled = true
      clearInterval(id)
    }
  }, [])

  const addComparison = useCallback(
    (c: ComparisonRecord) => setComparisons((h) => [...h, c].slice(-50)),
    [],
  )

  return (
    <Ctx.Provider value={{ nodes, apiOnline, nodeHistory, comparisons, addComparison }}>
      {children}
    </Ctx.Provider>
  )
}

export function useApp(): AppState {
  const v = useContext(Ctx)
  if (!v) throw new Error('useApp outside provider')
  return v
}
