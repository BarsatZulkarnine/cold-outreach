import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { Dashboard } from './pages/Dashboard'
import { Targets } from './pages/Targets'
import { Outreach } from './pages/Outreach'
import { Settings } from './pages/Settings'

const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', exact: true },
  { to: '/targets', label: 'Targets' },
  { to: '/outreach', label: 'Outreach' },
  { to: '/settings', label: 'Settings' },
]

function Nav() {
  return (
    <nav className="flex items-center gap-1 px-4 py-3 border-b border-gray-800 bg-gray-950">
      <span className="text-white font-bold mr-6 text-sm">Cold Outreach Bot</span>
      {NAV_ITEMS.map(({ to, label, exact }) => (
        <NavLink
          key={to}
          to={to}
          end={exact}
          className={({ isActive }) =>
            `px-3 py-1.5 text-sm rounded transition-colors ${
              isActive
                ? 'bg-gray-800 text-white'
                : 'text-gray-400 hover:text-white hover:bg-gray-900'
            }`
          }
        >
          {label}
        </NavLink>
      ))}
    </nav>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col">
        <Nav />
        <main className="flex-1">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/targets" element={<Targets />} />
            <Route path="/outreach" element={<Outreach />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}
