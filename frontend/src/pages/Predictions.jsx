import { useEffect, useState } from 'react'
import {
  ComposedChart, Line, Area, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend, ReferenceLine
} from 'recharts'
import { predictionsApi } from '../api/predictions'
import { medicinesApi } from '../api/medicines'
import AlertBadge from '../components/AlertBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function Predictions() {
  const [medicines, setMedicines]     = useState([])
  const [reorderList, setReorderList] = useState([])
  const [selected, setSelected]       = useState(null)
  const [forecast, setForecast]       = useState(null)
  const [horizon, setHorizon]         = useState(30)
  const [loading, setLoading]         = useState(true)
  const [chartLoading, setChartLoading] = useState(false)
  const [error, setError]             = useState(null)
  const [tab, setTab]                 = useState('overview')  // overview | detail

  useEffect(() => {
    Promise.all([medicinesApi.list(), predictionsApi.reorderList(30)])
      .then(([meds, rl]) => { setMedicines(meds); setReorderList(rl) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  const loadForecast = (medicineId, h = horizon) => {
    if (!medicineId) return
    setChartLoading(true)
    predictionsApi.forecast(medicineId, h)
      .then(setForecast)
      .catch(e => alert(e.message))
      .finally(() => setChartLoading(false))
  }

  const handleMedicineSelect = (id) => {
    setSelected(parseInt(id))
    loadForecast(parseInt(id), horizon)
    setTab('detail')
  }

  const handleHorizonChange = (h) => {
    setHorizon(h)
    if (selected) loadForecast(selected, h)
  }

  if (loading) return <LoadingSpinner message="Running forecasts..." />
  if (error)   return <ErrorMessage message={error} />

  const chartData = forecast?.daily_breakdown?.map(d => ({
    date: d.forecast_date?.slice(5),
    predicted: Math.round(d.predicted_quantity),
    lower: Math.round(d.lower_bound),
    upper: Math.round(d.upper_bound),
  })) ?? []

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {[['overview', '📊 Reorder Overview'], ['detail', '🔍 Medicine Detail']].map(([t, l]) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'}`}>
              {l}
            </button>
          ))}
        </div>

        {tab === 'detail' && (
          <div className="flex gap-2 items-center flex-wrap">
            <select
              className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
              value={selected ?? ''}
              onChange={e => handleMedicineSelect(e.target.value)}
            >
              <option value="">Select medicine...</option>
              {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
            <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
              {[7, 14, 30].map(h => (
                <button key={h} onClick={() => handleHorizonChange(h)}
                  className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${horizon === h ? 'bg-white shadow text-blue-700' : 'text-gray-500'}`}>
                  {h}d
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Overview Tab */}
      {tab === 'overview' && (
        <div className="space-y-4">
          <div className="card p-4 bg-yellow-50 border border-yellow-200">
            <p className="text-sm font-medium text-yellow-800">
              ⚠️ {reorderList.length} medicine(s) require reordering based on 30-day demand forecast
            </p>
          </div>
          <div className="card overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['Medicine', 'Current Stock', 'Predicted Demand (30d)', 'Days Until Stockout', 'Action'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {reorderList.map(r => (
                  <tr key={r.medicine_id} className="hover:bg-gray-50">
                    <td className="table-td font-medium">{r.medicine_name}</td>
                    <td className="table-td font-semibold">{r.current_stock}</td>
                    <td className="table-td">{Math.round(r.total_predicted)}</td>
                    <td className="table-td">
                      {r.days_until_stockout != null ? (
                        <span className={`font-semibold ${r.days_until_stockout <= 7 ? 'text-red-600' : 'text-orange-600'}`}>
                          {r.days_until_stockout}d
                        </span>
                      ) : (
                        <span className="text-gray-400">—</span>
                      )}
                    </td>
                    <td className="table-td">
                      <button
                        className="text-blue-600 text-xs font-medium hover:underline"
                        onClick={() => handleMedicineSelect(r.medicine_id)}
                      >
                        View Forecast →
                      </button>
                    </td>
                  </tr>
                ))}
                {!reorderList.length && (
                  <tr><td colSpan={5} className="table-td text-center py-8 text-gray-400">
                    All medicines have sufficient stock for the forecast period ✓
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Detail Tab */}
      {tab === 'detail' && (
        <div className="space-y-4">
          {!selected && (
            <div className="card p-12 text-center text-gray-400">
              Select a medicine above to view its demand forecast
            </div>
          )}

          {selected && chartLoading && <LoadingSpinner message="Running forecast model..." />}

          {selected && forecast && !chartLoading && (
            <>
              {/* Summary cards */}
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="card p-4">
                  <p className="text-xs text-gray-500 uppercase font-semibold">Current Stock</p>
                  <p className="text-2xl font-bold text-gray-800 mt-1">{forecast.current_stock}</p>
                </div>
                <div className="card p-4">
                  <p className="text-xs text-gray-500 uppercase font-semibold">Predicted {horizon}d Demand</p>
                  <p className="text-2xl font-bold text-blue-600 mt-1">{Math.round(forecast.total_predicted)}</p>
                </div>
                <div className="card p-4">
                  <p className="text-xs text-gray-500 uppercase font-semibold">Days Until Stockout</p>
                  <p className={`text-2xl font-bold mt-1 ${forecast.days_until_stockout ? 'text-red-600' : 'text-green-600'}`}>
                    {forecast.days_until_stockout ? `${forecast.days_until_stockout}d` : 'Safe ✓'}
                  </p>
                </div>
                <div className="card p-4">
                  <p className="text-xs text-gray-500 uppercase font-semibold">Reorder Needed</p>
                  <p className="mt-1">
                    <AlertBadge
                      type={forecast.reorder_recommended ? 'high' : 'ok'}
                      label={forecast.reorder_recommended ? 'YES — Order Now' : 'NO — Sufficient'}
                    />
                  </p>
                </div>
              </div>

              {/* Forecast chart */}
              <div className="card p-5">
                <h2 className="font-semibold text-gray-700 mb-1">{forecast.medicine_name} — {horizon}-Day Demand Forecast</h2>
                <p className="text-xs text-gray-400 mb-4">
                  Model: {forecast.daily_breakdown[0]?.model_used} |
                  Confidence: {forecast.daily_breakdown[0]?.confidence_score != null
                    ? `${(forecast.daily_breakdown[0].confidence_score * 100).toFixed(0)}%`
                    : 'N/A'}
                </p>
                <ResponsiveContainer width="100%" height={280}>
                  <ComposedChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Area
                      type="monotone" dataKey="upper" fill="#dbeafe" stroke="none"
                      name="Upper bound" legendType="none"
                    />
                    <Area
                      type="monotone" dataKey="lower" fill="#ffffff" stroke="none"
                      name="Lower bound" legendType="none"
                    />
                    <Line
                      type="monotone" dataKey="predicted" stroke="#3b82f6" strokeWidth={2}
                      dot={false} name="Predicted demand"
                    />
                    {forecast.days_until_stockout && (
                      <ReferenceLine
                        x={chartData[forecast.days_until_stockout - 1]?.date}
                        stroke="#ef4444" strokeDasharray="4 4"
                        label={{ value: 'Stockout', fill: '#ef4444', fontSize: 11 }}
                      />
                    )}
                  </ComposedChart>
                </ResponsiveContainer>
              </div>

              {/* Daily breakdown table */}
              <div className="card overflow-x-auto">
                <div className="px-5 py-3 border-b border-gray-100">
                  <h3 className="font-medium text-gray-700 text-sm">Daily Breakdown</h3>
                </div>
                <table className="min-w-full divide-y divide-gray-100">
                  <thead className="bg-gray-50">
                    <tr>
                      {['Date', 'Predicted Units', 'Lower', 'Upper', 'Confidence'].map(h => (
                        <th key={h} className="table-th">{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-50">
                    {forecast.daily_breakdown.map((d, i) => (
                      <tr key={i} className="hover:bg-gray-50">
                        <td className="table-td">{d.forecast_date}</td>
                        <td className="table-td font-semibold text-blue-700">{Math.round(d.predicted_quantity)}</td>
                        <td className="table-td text-gray-500">{Math.round(d.lower_bound)}</td>
                        <td className="table-td text-gray-500">{Math.round(d.upper_bound)}</td>
                        <td className="table-td">
                          <div className="flex items-center gap-2">
                            <div className="flex-1 bg-gray-200 rounded-full h-1.5 w-16">
                              <div
                                className="bg-blue-500 h-1.5 rounded-full"
                                style={{ width: `${(d.confidence_score ?? 0) * 100}%` }}
                              />
                            </div>
                            <span className="text-xs text-gray-500">
                              {d.confidence_score != null ? `${(d.confidence_score * 100).toFixed(0)}%` : '—'}
                            </span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  )
}
