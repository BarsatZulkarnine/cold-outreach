import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Dashboard } from './pages/Dashboard'
import { Targets } from './pages/Targets'
import { Outreach } from './pages/Outreach'
import { Settings } from './pages/Settings'
import { ToastProvider } from './components/Toast'
import { fetchPersona } from './api/client'

// ─── Icons ───────────────────────────────────────────────────────────────────

function IconGrid() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0">
      <path d="M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zm0 8a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zm6-6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zm0 8a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z" />
    </svg>
  )
}

function IconList() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0">
      <path fillRule="evenodd" d="M3 4a1 1 0 000 2h14a1 1 0 100-2H3zm0 4a1 1 0 000 2h14a1 1 0 100-2H3zm0 4a1 1 0 000 2h14a1 1 0 100-2H3z" clipRule="evenodd" />
    </svg>
  )
}

function IconMail() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0">
      <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z" />
      <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z" />
    </svg>
  )
}

function IconCog() {
  return (
    <svg viewBox="0 0 20 20" fill="currentColor" className="w-4 h-4 shrink-0">
      <path fillRule="evenodd" d="M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z" clipRule="evenodd" />
    </svg>
  )
}

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: IconGrid, exact: true },
  { to: '/targets', label: 'Targets', icon: IconList },
  { to: '/outreach', label: 'Outreach', icon: IconMail },
  { to: '/settings', label: 'Settings', icon: IconCog },
]

function Sidebar() {
  const [personaName, setPersonaName] = useState<string>('')

  useEffect(() => {
    fetchPersona().then((p) => setPersonaName(p.short_name)).catch(() => {})
  }, [])

  return (
    <aside className="w-52 shrink-0 flex flex-col border-r border-gray-800 bg-gray-950">
      <div className="px-5 pt-6 pb-4 border-b border-gray-800">
        <div className="text-white font-bold text-sm tracking-wide">Cold Outreach</div>
        {personaName && (
          <div className="text-xs text-gray-500 mt-1">
            Sending as <span className="text-gray-400">{personaName}</span>
          </div>
        )}
      </div>

      <nav className="flex flex-col gap-0.5 p-3 flex-1">
        {NAV_ITEMS.map(({ to, label, icon: Icon, exact }) => (
          <NavLink
            key={to}
            to={to}
            end={exact}
            className={({ isActive }) =>
              `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                isActive
                  ? 'bg-gray-800 text-white'
                  : 'text-gray-500 hover:text-gray-200 hover:bg-gray-900'
              }`
            }
          >
            <Icon />
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-gray-800">
        <div className="text-xs text-gray-700">Melbourne, AU</div>
      </div>
    </aside>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <ToastProvider>
        <div className="flex h-screen bg-gray-950 text-white font-mono overflow-hidden">
          <Sidebar />
          <main className="flex-1 overflow-y-auto">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/targets" element={<Targets />} />
              <Route path="/outreach" element={<Outreach />} />
              <Route path="/settings" element={<Settings />} />
            </Routes>
          </main>
        </div>
      </ToastProvider>
    </BrowserRouter>
  )
}
