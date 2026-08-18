import { useEffect, useState } from 'react'
import { reorderApi, riskApi } from '../api/reorder'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

const urgencyBadge = {
  critical: 'bg-red-100 text-red-700',
  high:     'bg-orange-100 text-orange-700',
  medium:   'bg-yellow-100 text-yellow-700',
  low:      'bg-green-100 text-green-700',
}

export default function ReorderRecommendations() {
  const [data, setData] = useState(null)
  const [deadStock, setDeadStock] = useState(null)
  const [anomalies, setAnomalies] = useState(null)
  const [stockValue, setStockValue] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('reorder')
  const [horizon, setHorizon] = useState(14)
  const [safety, setSafety] = useState(7)
  const [approved, setApproved] = useState({})

  const load = async () => {
    setLoading(true)
    try {
      const [rec, ds, an, sv] = await Promise.all([
        reorderApi.recommendations(horizon, safety),
        riskApi.deadStock(60).catch(() => null),
        riskApi.anomalies(7, 50).catch(() => null),
        riskApi.stockValue().catch(() => null),
      ])
      setData(rec)
      setDeadStock(ds)
      setAnomalies(an)
      setStockValue(sv)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [horizon, safety])

  const handleExport = async () => {
    try {
      const blob = await reorderApi.exportCsv(horizon, safety)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `reorder_recommendations_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) { alert(err.message) }
  }

  const toggleApprove = (id) => {
    setApproved(prev => ({ ...prev, [id]: !prev[id] }))
  }

  if (loading) return <LoadingSpinner message="Calculating recommendations..." />
  if (error) return <ErrorMessage message={error} />

  const reorderItems = data?.recommendations?.filter(r => r.needs_reorder) || []
  const approvedCount = Object.values(approved).filter(Boolean).length

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {[
            ['reorder', `🛒 Orders (${reorderItems.length})`],
            ['dead', `💤 Dead Stock (${deadStock?.total_dead_stock_items || 0})`],
            ['anomalies', `⚡ Anomalies (${anomalies?.total_anomalies || 0})`],
            ['value', '💶 Stock Value'],
          ].map(([t, l]) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'}`}>
              {l}
            </button>
          ))}
        </div>
        {tab === 'reorder' && (
          <div className="flex gap-2 items-center">
            <select className="border rounded-lg px-2 py-1.5 text-sm" value={horizon} onChange={e => setHorizon(+e.target.value)}>
              <option value={7}>7d horizon</option>
              <option value={14}>14d horizon</option>
              <option value={30}>30d horizon</option>
            </select>
            <select className="border rounded-lg px-2 py-1.5 text-sm" value={safety} onChange={e => setSafety(+e.target.value)}>
              <option value={3}>3d safety</option>
              <option value={7}>7d safety</option>
              <option value={14}>14d safety</option>
            </select>
            <button onClick={handleExport} className="bg-green-600 hover:bg-green-700 text-white px-3 py-1.5 rounded-lg text-sm font-medium">Export CSV</button>
          </div>
        )}
      </div>

      {/* Reorder Tab */}
      {tab === 'reorder' && (
        <div className="space-y-4">
          {approvedCount > 0 && (
            <div className="card p-3 bg-green-50 border border-green-200 flex items-center justify-between">
              <span className="text-sm text-green-700 font-medium">{approvedCount} item(s) approved for ordering</span>
              <button onClick={handleExport} className="text-sm bg-green-600 text-white px-3 py-1 rounded hover:bg-green-700">Export Approved</button>
            </div>
          )}
          <div className="card overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['✔', 'Medicine', 'Supplier', 'Stock', 'Daily Avg', 'Predicted', 'Safety', 'Order Qty', 'Days Left', 'Urgency'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {reorderItems.map(r => (
                  <tr key={r.medicine_id} className={`hover:bg-gray-50 ${approved[r.medicine_id] ? 'bg-green-50' : ''}`}>
                    <td className="table-td">
                      <input type="checkbox" checked={!!approved[r.medicine_id]} onChange={() => toggleApprove(r.medicine_id)} className="w-4 h-4 rounded" />
                    </td>
                    <td className="table-td font-medium">{r.medicine_name}</td>
                    <td className="table-td text-sm text-gray-500">{r.supplier || '—'}</td>
                    <td className="table-td font-semibold">{r.current_stock}</td>
                    <td className="table-td">{r.avg_daily_demand}</td>
                    <td className="table-td">{r.predicted_demand}</td>
                    <td className="table-td">{r.safety_stock}</td>
                    <td className="table-td font-bold text-blue-700">{r.recommended_qty}</td>
                    <td className="table-td">
                      <span className={`font-semibold ${r.days_of_stock_remaining <= 3 ? 'text-red-600' : r.days_of_stock_remaining <= 7 ? 'text-orange-600' : 'text-gray-700'}`}>
                        {r.days_of_stock_remaining}d
                      </span>
                    </td>
                    <td className="table-td">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${urgencyBadge[r.urgency]}`}>{r.urgency}</span>
                    </td>
                  </tr>
                ))}
                {!reorderItems.length && (
                  <tr><td colSpan={10} className="table-td text-center py-8 text-gray-400">All medicines are adequately stocked</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Dead Stock Tab */}
      {tab === 'dead' && deadStock && (
        <div className="space-y-4">
          <div className="card p-4 bg-yellow-50 border border-yellow-200">
            <p className="text-sm font-medium text-yellow-800">
              {deadStock.total_dead_stock_items} product(s) with no sales in {deadStock.threshold_days} days — estimated value at risk: €{deadStock.total_value_at_risk.toFixed(2)}
            </p>
          </div>
          <div className="card overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['Medicine', 'Category', 'Supplier', 'On Hand', 'Days Since Sale', 'Last Sale', 'Value at Risk'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {deadStock.items.map(d => (
                  <tr key={d.medicine_id} className="hover:bg-gray-50">
                    <td className="table-td font-medium">{d.medicine_name}</td>
                    <td className="table-td text-sm text-gray-500">{d.category}</td>
                    <td className="table-td text-sm">{d.supplier || '—'}</td>
                    <td className="table-td font-semibold">{d.on_hand_quantity}</td>
                    <td className="table-td text-red-600 font-semibold">{d.days_since_last_sale}d</td>
                    <td className="table-td text-sm">{d.last_sale_date || 'Never'}</td>
                    <td className="table-td font-semibold text-red-600">€{d.value_at_risk.toFixed(2)}</td>
                  </tr>
                ))}
                {!deadStock.items.length && (
                  <tr><td colSpan={7} className="table-td text-center py-8 text-gray-400">No dead stock detected</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Anomalies Tab */}
      {tab === 'anomalies' && anomalies && (
        <div className="space-y-4">
          <div className="card p-4 bg-purple-50 border border-purple-200 flex justify-between items-center">
            <p className="text-sm font-medium text-purple-800">
              {anomalies.spikes} demand spike(s) and {anomalies.drops} demand drop(s) detected (last {anomalies.lookback_days} days vs prior 30-day average)
            </p>
          </div>
          <div className="card overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['Medicine', 'Category', 'Type', 'Recent Avg/Day', 'Baseline Avg/Day', 'Deviation', 'Severity'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {anomalies.anomalies.map(a => (
                  <tr key={a.medicine_id} className="hover:bg-gray-50">
                    <td className="table-td font-medium">{a.medicine_name}</td>
                    <td className="table-td text-sm text-gray-500">{a.category}</td>
                    <td className="table-td">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${a.anomaly_type === 'spike' ? 'bg-red-100 text-red-700' : 'bg-blue-100 text-blue-700'}`}>
                        {a.anomaly_type === 'spike' ? '📈 Spike' : '📉 Drop'}
                      </span>
                    </td>
                    <td className="table-td font-semibold">{a.recent_daily_avg}</td>
                    <td className="table-td">{a.baseline_daily_avg}</td>
                    <td className="table-td">
                      <span className={`font-semibold ${a.deviation_pct > 0 ? 'text-red-600' : 'text-blue-600'}`}>
                        {a.deviation_pct > 0 ? '+' : ''}{a.deviation_pct}%
                      </span>
                    </td>
                    <td className="table-td">
                      <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${a.severity === 'high' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>{a.severity}</span>
                    </td>
                  </tr>
                ))}
                {!anomalies.anomalies.length && (
                  <tr><td colSpan={7} className="table-td text-center py-8 text-gray-400">No demand anomalies detected</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Stock Value Tab */}
      {tab === 'value' && stockValue && (
        <div className="space-y-4">
          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-xs text-gray-500 uppercase font-semibold">Total Inventory Value</p>
              <p className="text-3xl font-bold text-gray-800">€{stockValue.grand_total_value.toLocaleString()}</p>
            </div>
            <div className="text-right">
              <p className="text-xs text-gray-500 uppercase font-semibold">Total Units</p>
              <p className="text-2xl font-bold text-gray-600">{stockValue.grand_total_units.toLocaleString()}</p>
            </div>
          </div>
          <div className="card overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['Category', 'Items', 'Total Units', 'Total Value', '% of Total'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {stockValue.categories.map(c => (
                  <tr key={c.category} className="hover:bg-gray-50">
                    <td className="table-td font-medium">{c.category}</td>
                    <td className="table-td">{c.item_count}</td>
                    <td className="table-td">{c.total_units.toLocaleString()}</td>
                    <td className="table-td font-semibold">€{c.total_value.toLocaleString()}</td>
                    <td className="table-td">
                      <div className="flex items-center gap-2">
                        <div className="flex-1 bg-gray-200 rounded-full h-2 w-20">
                          <div className="bg-blue-500 h-2 rounded-full" style={{ width: `${Math.min(100, (c.total_value / stockValue.grand_total_value) * 100)}%` }} />
                        </div>
                        <span className="text-xs text-gray-500">{((c.total_value / stockValue.grand_total_value) * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
