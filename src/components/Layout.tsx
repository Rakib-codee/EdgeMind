import Link from 'next/link'
import { useRouter } from 'next/router'
import type { ReactNode } from 'react'
import { useApp } from '../lib/state'

const NAV = [
  { to: '/', label: 'Overview', icon: '▦' },
  { to: '/nodes', label: 'Node Monitor', icon: '⛁' },
  { to: '/scheduler', label: 'Task Scheduler', icon: '⚡' },
  { to: '/analytics', label: 'Research Analytics', icon: '📊' },
  { to: '/experiment', label: 'Experiment Control', icon: '⚙' },
]

export default function Layout({ children }: { children: ReactNode }) {
  const { apiOnline } = useApp()
  const router = useRouter()
  return (
    <div className="flex min-h-screen bg-zinc-950 text-zinc-100">
      <aside className="w-56 shrink-0 border-r border-zinc-800 bg-zinc-900/40 p-4 flex flex-col">
        <div className="mb-8">
          <h1 className="text-xl font-bold">EdgeMind</h1>
          <p className="text-xs text-zinc-500">Edge–Cloud Orchestrator</p>
        </div>
        <nav className="space-y-1 flex-1">
          {NAV.map((n) => {
            const isActive = router.pathname === n.to
            return (
              <Link
                key={n.to}
                href={n.to}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-300 font-semibold'
                    : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200'
                }`}
              >
                <span>{n.icon}</span>
                {n.label}
              </Link>
            )
          })}
        </nav>
        <div className="text-xs text-zinc-500 space-y-2">
          <p className="flex items-center gap-2">
            <span
              className={`inline-block h-2 w-2 rounded-full ${apiOnline ? 'bg-emerald-400' : 'bg-red-500'}`}
            />
            API {apiOnline ? 'online' : 'offline'}
          </p>
          <p>
            <a className="underline" href="https://github.com/Rakib-codee/EdgeMind">
              GitHub
            </a>
            {' · '}
            <a className="underline" href="https://edge-cloud-scheduler.streamlit.app">
              Research results
            </a>
          </p>
        </div>
      </aside>
      <main className="flex-1 overflow-y-auto p-6">{children}</main>
    </div>
  )
}
