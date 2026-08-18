import { useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const titles = {
  '/dashboard':   'Dashboard',
  '/medicines':   'Medicines Catalogue',
  '/stock':       'Stock Management',
  '/expiry':      'Expiry Tracking',
  '/predictions': 'Demand Predictions',
  '/sales':       'Sales History',
}

const roleBadge = {
  admin:  'bg-purple-100 text-purple-700',
  staff:  'bg-blue-100 text-blue-700',
  viewer: 'bg-gray-100 text-gray-600',
}

export default function Topbar() {
  const { pathname } = useLocation()
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const title = titles[pathname] || 'Pharmacy System'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      <h1 className="text-lg font-semibold text-gray-800">{title}</h1>

      <div className="flex items-center gap-4">
        <span className="text-sm text-gray-400 hidden sm:block">
          {new Date().toLocaleDateString('en-IE', { weekday: 'short', month: 'short', day: 'numeric' })}
        </span>

        {user && (
          <div className="flex items-center gap-3">
            <div className="text-right hidden sm:block">
              <p className="text-sm font-medium text-gray-700 leading-none">{user.full_name || user.username}</p>
              <span className={`text-xs px-1.5 py-0.5 rounded font-medium ${roleBadge[user.role] || roleBadge.viewer}`}>
                {user.role}
              </span>
            </div>
            <div className="w-8 h-8 rounded-full bg-blue-600 flex items-center justify-center text-white text-sm font-bold">
              {(user.full_name || user.username)[0].toUpperCase()}
            </div>
            <button
              onClick={handleLogout}
              className="text-sm text-gray-500 hover:text-red-600 transition-colors px-2 py-1 rounded hover:bg-red-50"
              title="Sign out"
            >
              Sign out
            </button>
          </div>
        )}
      </div>
    </header>
  )
}
