import { NavLink } from 'react-router-dom'
import clsx from 'clsx'

const nav = [
  { to: '/dashboard',        label: 'Dashboard',           icon: '🏠' },
  { to: '/medicines',        label: 'Medicines',           icon: '💊' },
  { to: '/inventory',        label: 'Inventory',           icon: '📦' },
  { to: '/sales',            label: 'Sales History',       icon: '🧾' },
  { to: '/forecasting',      label: 'Forecasting & Reorder', icon: '📈' },
  { to: '/writeoffs',        label: 'Write-Offs',          icon: '🗑️' },
  { to: '/expiry',           label: 'Expiry Tracking',     icon: '⏰' },
  { to: '/controlled-drugs', label: 'Controlled Drugs',    icon: '🔒' },
  { to: '/data-import',      label: 'Data Import',         icon: '📥' },
]

export default function Sidebar() {
  return (
    <aside className="w-60 bg-blue-900 text-white flex flex-col shrink-0">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-blue-800">
        <div className="flex items-center gap-2">
          <span className="text-2xl">💊</span>
          <div>
            <p className="font-bold text-sm leading-tight">PharmStock</p>
            <p className="text-blue-300 text-xs">Prediction System</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        {nav.map(({ to, label, icon }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              clsx(
                'flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors',
                isActive
                  ? 'bg-blue-700 text-white'
                  : 'text-blue-200 hover:bg-blue-800 hover:text-white'
              )
            }
          >
            <span className="text-base">{icon}</span>
            {label}
          </NavLink>
        ))}
      </nav>

      <div className="px-5 py-4 border-t border-blue-800 text-xs text-blue-400">
        v1.0.0 — DCU Pharmacy
      </div>
    </aside>
  )
}
