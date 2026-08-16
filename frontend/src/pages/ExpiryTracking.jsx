import { useEffect, useState } from 'react'
import { expiryApi } from '../api/expiry'
import AlertBadge from '../components/AlertBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

const TIER_CONFIG = {
  expired:  { label: 'Expired',       icon: '🗑️',  bg: 'bg-red-50 border-red-200' },
  critical: { label: 'Critical (≤30d)', icon: '🚨', bg: 'bg-orange-50 border-orange-200' },
  warning:  { label: 'Warning (≤60d)', icon: '⚠️', bg: 'bg-yellow-50 border-yellow-200' },
  watch:    { label: 'Watch (≤90d)',   icon: '👁️', bg: 'bg-blue-50 border-blue-200' },
}

export default function ExpiryTracking() {
  const [alerts, setAlerts]     = useState(null)
  const [logs, setLogs]         = useState([])
  const [calendar, setCalendar] = useState({})
  const [loading, setLoading]   = useState(true)
  const [error, setError]       = useState(null)
  const [tab, setTab]           = useState('alerts')   // alerts | logs | calendar

  const load = async () => {
    setLoading(true)
    try {
      const [a, l, c] = await Promise.all([
        expiryApi.alerts(),
        expiryApi.logs({ limit: 100 }),
        expiryApi.calendar(3),
      ])
      setAlerts(a)
      setLogs(l)
      setCalendar(c)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  if (loading) return <LoadingSpinner message="Loading expiry data..." />
  if (error)   return <ErrorMessage message={error} onRetry={load} />

  return (
    <div className="space-y-4">
      {/* Summary row */}
      {alerts && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {Object.entries(TIER_CONFIG).map(([tier, cfg]) => (
            <div key={tier} className={`card border p-4 flex items-center gap-3 ${cfg.bg}`}>
              <span className="text-2xl">{cfg.icon}</span>
              <div>
                <p className="text-xs font-semibold text-gray-500 uppercase">{cfg.label}</p>
                <p className="text-2xl font-bold text-gray-800">{alerts[tier]?.length ?? 0}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Est. loss banner */}
      {alerts?.summary?.total_estimated_loss > 0 && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-center gap-3">
          <span className="text-2xl">💸</span>
          <div>
            <p className="font-semibold text-red-700">Estimated financial exposure</p>
            <p className="text-sm text-red-600">
              €{alerts.summary.total_estimated_loss.toLocaleString()} from expired and critical-tier batches
            </p>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-lg w-fit">
        {[['alerts', '🚨 Expiry Alerts'], ['logs', '📋 Expiry Logs'], ['calendar', '📅 Calendar']].map(([t, l]) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${
              tab === t ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {l}
          </button>
        ))}
      </div>

      {/* Alerts Tab */}
      {tab === 'alerts' && (
        <div className="space-y-6">
          {Object.entries(TIER_CONFIG).map(([tier, cfg]) => {
            const items = alerts?.[tier] ?? []
            if (!items.length) return null
            return (
              <div key={tier}>
                <h3 className="text-sm font-semibold text-gray-600 mb-2 flex items-center gap-2">
                  {cfg.icon} {cfg.label} — {items.length} batch(es)
                </h3>
                <div className="card overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-100">
                    <thead className="bg-gray-50">
                      <tr>
                        {['Medicine', 'Batch No.', 'Category', 'Expiry Date', 'Days Left', 'Qty Remaining', 'Est. Loss', 'Action'].map(h => (
                          <th key={h} className="table-th">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-50">
                      {items.map(b => (
                        <tr key={b.batch_id} className="hover:bg-gray-50">
                          <td className="table-td font-medium">{b.medicine_name}</td>
                          <td className="table-td font-mono text-xs">{b.batch_number}</td>
                          <td className="table-td text-gray-500">{b.category}</td>
                          <td className="table-td">{b.expiry_date}</td>
                          <td className="table-td">
                            <span className={`font-semibold ${b.days_until_expiry < 0 ? 'text-red-600' : b.days_until_expiry <= 30 ? 'text-orange-600' : 'text-yellow-600'}`}>
                              {b.days_until_expiry < 0 ? `${Math.abs(b.days_until_expiry)}d ago` : `${b.days_until_expiry}d`}
                            </span>
                          </td>
                          <td className="table-td">{b.quantity_remaining}</td>
                          <td className="table-td text-red-600 font-medium">
                            {b.estimated_loss > 0 ? `€${b.estimated_loss.toFixed(2)}` : '—'}
                          </td>
                          <td className="table-td">
                            <AlertBadge type={tier} label={tier.toUpperCase()} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )
          })}
          {!Object.values(alerts ?? {}).some(v => Array.isArray(v) && v.length) && (
            <div className="card p-10 text-center text-gray-400">
              <p className="text-4xl mb-3">✅</p>
              <p>No expiry alerts — all batches within acceptable dates</p>
            </div>
          )}
        </div>
      )}

      {/* Logs Tab */}
      {tab === 'logs' && (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['Date', 'Medicine', 'Batch', 'Expiry Date', 'Qty Affected', 'Qty Wasted', 'Est. Loss', 'Action', 'By'].map(h => (
                  <th key={h} className="table-th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {logs.map(l => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="table-td text-xs text-gray-500">{l.action_date}</td>
                  <td className="table-td font-medium">{l.medicine_name}</td>
                  <td className="table-td font-mono text-xs">{l.batch_number}</td>
                  <td className="table-td">{l.expiry_date}</td>
                  <td className="table-td">{l.quantity_affected}</td>
                  <td className="table-td text-red-600">{l.quantity_wasted ?? '—'}</td>
                  <td className="table-td text-red-600">
                    {l.estimated_loss ? `€${l.estimated_loss.toFixed(2)}` : '—'}
                  </td>
                  <td className="table-td">
                    <span className="badge bg-gray-100 text-gray-700">{l.action}</span>
                  </td>
                  <td className="table-td text-gray-500">{l.performed_by ?? '—'}</td>
                </tr>
              ))}
              {!logs.length && (
                <tr><td colSpan={9} className="table-td text-center py-8 text-gray-400">No expiry logs yet</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Calendar Tab */}
      {tab === 'calendar' && (
        <div className="space-y-6">
          {Object.entries(calendar).length === 0 && (
            <div className="card p-10 text-center text-gray-400">No batches expiring in the next 3 months</div>
          )}
          {Object.entries(calendar).sort().map(([month, batches]) => (
            <div key={month}>
              <h3 className="text-sm font-semibold text-gray-600 mb-2">
                📅 {new Date(month + '-01').toLocaleDateString('en-IE', { month: 'long', year: 'numeric' })}
                <span className="ml-2 text-gray-400 font-normal">— {batches.length} batch(es)</span>
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {batches.map(b => (
                  <div key={b.batch_id} className="card p-4 border-l-4 border-yellow-400">
                    <p className="font-medium text-sm text-gray-800">{b.medicine_name}</p>
                    <p className="text-xs text-gray-500 mt-0.5 font-mono">{b.batch_number}</p>
                    <div className="flex items-center justify-between mt-2">
                      <span className="text-xs text-gray-500">Expires: {b.expiry_date}</span>
                      <span className="text-xs font-semibold text-orange-600">{b.days_until_expiry}d left</span>
                    </div>
                    <p className="text-xs text-gray-500 mt-1">Qty: {b.quantity_remaining}</p>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
