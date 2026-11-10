/** Application shell: header, navigation, live latency, and the three views. */

import { lazy, Suspense, useEffect, useState } from 'react'
import { Skeleton } from './components/ui'
import { useApiStats } from './hooks'
import Detective from './pages/detective'
import Project from './pages/project'
import { useApp, type View } from './state'

const Risk = lazy(() => import('./pages/risk'))

const VIEWS: { id: View; label: string }[] = [
  { id: 'detective', label: 'Trend Detective' },
  { id: 'risk', label: 'Risk Lab' },
  { id: 'project', label: 'Project' },
]

function Logo() {
  return (
    <svg viewBox="0 0 64 64" aria-hidden>
      <defs><linearGradient id="lg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stopColor="#3fd4a2" /><stop offset="1" stopColor="#3987e5" /></linearGradient></defs>
      <circle cx="32" cy="32" r="28" fill="#0b0d10" stroke="url(#lg)" strokeWidth="4" />
      <path d="M12 36 Q22 20 32 32 T52 26" fill="none" stroke="url(#lg)" strokeWidth="4" strokeLinecap="round" />
      <circle cx="46" cy="27" r="4" fill="#e66767" />
    </svg>
  )
}

/** Root component: shell, navigation, and the page for the selected view. */
export default function App() {
  const { state, patch } = useApp()
  const stats = useApiStats()
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    document.title = `TerraPulse · ${VIEWS.find((v) => v.id === state.view)!.label}`
  }, [state.view])

  const share = async () => {
    try {
      await navigator.clipboard.writeText(window.location.href)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* clipboard may be unavailable; the address bar already holds the link */
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-inner">
          <div className="brand"><Logo />TerraPulse</div>
          <nav className="nav" aria-label="Main">
            {VIEWS.map((v) => (
              <button key={v.id} aria-current={state.view === v.id ? 'page' : undefined} onClick={() => patch({ view: v.id })}>{v.label}</button>
            ))}
          </nav>
          <div className="header-right">
            <span className="latency" title="Server processing time of the last request, and instant answers served from the browser cache">
              API <b>{stats.lastServerMs ?? '–'} ms</b> · {stats.cacheHits} instant
            </span>
            <button className="btn small" onClick={share}>{copied ? 'Link copied ✓' : 'Share this view'}</button>
          </div>
        </div>
        <nav className="mobile-nav" aria-label="Main (mobile)">
          {VIEWS.map((v) => (
            <button key={v.id} aria-current={state.view === v.id ? 'page' : undefined} onClick={() => patch({ view: v.id })}>{v.label}</button>
          ))}
        </nav>
      </header>
      <main className="main">
        {state.view === 'detective' && <Detective />}
        {state.view === 'risk' && <Suspense fallback={<Skeleton height={400} />}><Risk /></Suspense>}
        {state.view === 'project' && <Project />}
      </main>
      <footer className="footer">
        TerraPulse · Trend Detective tests Earth-system trends for any place; Risk Lab forecasts drought and simulates wildfire. Open satellite-based data.
      </footer>
    </div>
  )
}
