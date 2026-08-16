import { useEffect, useState } from 'react'
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { stockApi } from '../api/stock'
import { salesApi } from '../api/sales'
import { alertsApi } from '../api/alerts'
import StatCard from '../components/StatCard'
import AlertBadge from '../components/AlertBadge'
import LoadingSpinner from '../components/LoadingSpinner'

export default function Dashboard() {
  const [summary, setSummary]   = useState(null)
  const [dailySales, setDailySales] = useState([])
  const [topMeds, setTopMeds]   = useState([])
  const [alerts, setAlerts]     = useState(null)
  const [loading, setLoading]   = useState(true)

  useEffect(() => {
    Promise.all([
      stockApi.summary(),
      salesApi.dailySummary(30),
      salesApi.byMedicine(30),
      alertsApi.all(),
    ]).then(([sum, daily, top, alts]) => {
      setSummary(sum)
      setDailySales(daily.map(d => ({ ...d, date: d.date?.slice(5) })))
      setTopMeds(top.slice(0, 8))
      setAlerts(alts)
    }).finally(() => setLoading(false))
  }, [])

  if (loading) return <LoadingSpinner message="Loading dashboard..." />

  return (
    <div className="space-y-6">
      {/* KPI row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Total Medicines" value={summary?.total_medicines} icon="💊" color="blue" />
        <StatCard label="Low Stock Items" value={summary?.low_stock_count} icon="⚠️" color="yellow"
          sub="Below reorder level" />
        <StatCard label="Expiring Critical" value={summary?.expiring_critical} icon="🚨" color="red"
          sub="Within 30 days" />
        <StatCard label="Stock Value" value={`€${(summary?.total_stock_value || 0).toLocaleString()}`}
          icon="💶" color="green" sub="Active batches" />
      </div>

      {/* Secondary KPIs */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard label="Expiring Warning"  value={summary?.expiring_warning}  icon="⏰" color="orange" sub="31–60 days" />
        <StatCard label="Expiring Watch"    value={summary?.expiring_watch}    icon="👁️" color="purple" sub="61–90 days" />
        <StatCard label="Expired in Stock"  value={summary?.expired_active_batches} icon="🗑️" color="red" sub="Needs removal" />
        <StatCard label="Active Alerts"     value={alerts?.total}              icon="🔔" color="yellow" />
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Daily sales area chart */}
        <div className="card p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Daily Sales — Last 30 Days</h2>
          <ResponsiveContainer width="100%" height={220}>
            <AreaChart data={dailySales}>
              <defs>
                <linearGradient id="salesGrad" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis dataKey="date" tick={{ fontSize: 11 }} />
              <YAxis tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v, n) => [v, n === 'total_qty' ? 'Units sold' : 'Revenue (€)']} />
              <Area type="monotone" dataKey="total_qty" stroke="#3b82f6" fill="url(#salesGrad)" name="total_qty" />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        {/* Top medicines bar chart */}
        <div className="card p-5">
          <h2 className="font-semibold text-gray-700 mb-4">Top Medicines by Sales (30d)</h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={topMeds} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
              <XAxis type="number" tick={{ fontSize: 11 }} />
              <YAxis type="category" dataKey="medicine_name" width={130} tick={{ fontSize: 11 }} />
              <Tooltip />
              <Bar dataKey="total_qty" fill="#3b82f6" radius={[0, 4, 4, 0]} name="Units sold" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Alert feed */}
      <div className="card p-5">
        <h2 className="font-semibold text-gray-700 mb-4">
          Active Alerts
          {alerts?.high_count > 0 && (
            <span className="ml-2 badge bg-red-100 text-red-700">{alerts.high_count} high</span>
          )}
        </h2>
        {!alerts?.alerts?.length ? (
          <p className="text-sm text-gray-400 py-4 text-center">No active alerts — all clear ✓</p>
        ) : (
          <div className="space-y-2 max-h-72 overflow-y-auto">
            {alerts.alerts.slice(0, 20).map((a, i) => (
              <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 border border-gray-100">
                <AlertBadge type={a.severity} label={a.severity.toUpperCase()} />
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-gray-700 leading-snug">{a.message}</p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
