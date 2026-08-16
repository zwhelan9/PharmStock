import { useLocation } from 'react-router-dom'

const titles = {
  '/dashboard':   'Dashboard',
  '/medicines':   'Medicines Catalogue',
  '/stock':       'Stock Management',
  '/expiry':      'Expiry Tracking',
  '/predictions': 'Demand Predictions',
  '/sales':       'Sales History',
}

export default function Topbar() {
  const { pathname } = useLocation()
  const title = titles[pathname] || 'Pharmacy System'

  return (
    <header className="h-14 bg-white border-b border-gray-200 flex items-center justify-between px-6 shrink-0">
      <h1 className="text-lg font-semibold text-gray-800">{title}</h1>
      <div className="flex items-center gap-3 text-sm text-gray-500">
        <span>{new Date().toLocaleDateString('en-IE', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</span>
      </div>
    </header>
  )
}
