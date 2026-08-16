import { useEffect, useState } from 'react'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend
} from 'recharts'
import { salesApi } from '../api/sales'
import { medicinesApi } from '../api/medicines'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

const SALE_EMPTY = {
  medicine_id: '', quantity: '', unit_price: '',
  prescription_ref: '', is_prescription: false,
  served_by: '', notes: '',
}

export default function SalesHistory() {
  const [sales, setSales]           = useState([])
  const [daily, setDaily]           = useState([])
  const [byMed, setByMed]           = useState([])
  const [medicines, setMedicines]   = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [days, setDays]             = useState(30)
  const [medFilter, setMedFilter]   = useState('')
  const [tab, setTab]               = useState('charts')
  const [showForm, setShowForm]     = useState(false)
  const [form, setForm]             = useState(SALE_EMPTY)
  const [saving, setSaving]         = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [s, d, bm, meds] = await Promise.all([
        salesApi.list({ medicine_id: medFilter || undefined, limit: 100 }),
        salesApi.dailySummary(days, medFilter || null),
        salesApi.byMedicine(days),
        medicinesApi.list(),
      ])
      setSales(s)
      setDaily(d.map(r => ({ ...r, date: r.date?.slice(5) })))
      setByMed(bm.slice(0, 10))
      setMedicines(meds)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [days, medFilter])

  const handleSaleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await salesApi.create({
        ...form,
        medicine_id: parseInt(form.medicine_id),
        quantity: parseInt(form.quantity),
        unit_price: form.unit_price ? parseFloat(form.unit_price) : null,
        is_prescription: Boolean(form.is_prescription),
      })
      setShowForm(false)
      setForm(SALE_EMPTY)
      load()
    } catch (e) {
      alert(e.message)
    } finally {
      setSaving(false)
    }
  }

  const totalRevenue = sales.reduce((s, r) => s + (r.total_price ?? 0), 0)
  const totalUnits   = sales.reduce((s, r) => s + r.quantity, 0)

  if (loading && !sales.length) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <div className="flex gap-2 flex-wrap items-center">
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={days}
            onChange={e => setDays(parseInt(e.target.value))}
          >
            {[7, 14, 30, 60, 90].map(d => <option key={d} value={d}>Last {d} days</option>)}
          </select>
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm"
            value={medFilter}
            onChange={e => setMedFilter(e.target.value)}
          >
            <option value="">All medicines</option>
            {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
            {[['charts', '📊 Charts'], ['table', '📋 Transactions']].map(([t, l]) => (
              <button key={t} onClick={() => setTab(t)}
                className={`px-3 py-1 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow text-blue-700' : 'text-gray-500'}`}>
                {l}
              </button>
            ))}
          </div>
        </div>
        <button className="btn-primary" onClick={() => setShowForm(true)}>+ Record Sale</button>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        <div className="card p-4">
          <p className="text-xs text-gray-500 uppercase font-semibold">Transactions</p>
          <p className="text-2xl font-bold text-gray-800 mt-1">{sales.length}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-gray-500 uppercase font-semibold">Units Sold</p>
          <p className="text-2xl font-bold text-blue-600 mt-1">{totalUnits.toLocaleString()}</p>
        </div>
        <div className="card p-4">
          <p className="text-xs text-gray-500 uppercase font-semibold">Total Revenue</p>
          <p className="text-2xl font-bold text-green-600 mt-1">€{totalRevenue.toFixed(2)}</p>
        </div>
      </div>

      {/* Charts Tab */}
      {tab === 'charts' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="card p-5">
            <h2 className="font-semibold text-gray-700 mb-4">Daily Units Sold</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={daily}>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="total_qty" fill="#3b82f6" radius={[3, 3, 0, 0]} name="Units sold" />
              </BarChart>
            </ResponsiveContainer>
          </div>
          <div className="card p-5">
            <h2 className="font-semibold text-gray-700 mb-4">Top 10 Medicines by Volume</h2>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={byMed} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" horizontal={false} />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="medicine_name" width={140} tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="total_qty" fill="#10b981" radius={[0, 3, 3, 0]} name="Units" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {/* Table Tab */}
      {tab === 'table' && (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['Date', 'Medicine', 'Qty', 'Unit Price', 'Total', 'Batch', 'Served By', 'Rx'].map(h => (
                  <th key={h} className="table-th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {sales.map(s => (
                <tr key={s.id} className="hover:bg-gray-50">
                  <td className="table-td text-xs text-gray-500">
                    {new Date(s.sale_date).toLocaleString('en-IE')}
                  </td>
                  <td className="table-td font-medium">{s.medicine_name}</td>
                  <td className="table-td font-semibold">{s.quantity}</td>
                  <td className="table-td">€{s.unit_price?.toFixed(2) ?? '—'}</td>
                  <td className="table-td font-medium text-green-700">
                    €{s.total_price?.toFixed(2) ?? '—'}
                  </td>
                  <td className="table-td text-xs font-mono text-gray-400">
                    #{s.batch_id ?? '—'}
                  </td>
                  <td className="table-td text-gray-500">{s.served_by ?? '—'}</td>
                  <td className="table-td">
                    {s.is_prescription ? (
                      <span className="badge bg-purple-100 text-purple-700">Rx</span>
                    ) : (
                      <span className="badge bg-gray-100 text-gray-500">OTC</span>
                    )}
                  </td>
                </tr>
              ))}
              {!sales.length && (
                <tr><td colSpan={8} className="table-td text-center py-8 text-gray-400">No sales records</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Record Sale Modal */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="font-semibold">Record Sale</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 text-xl">✕</button>
            </div>
            <form onSubmit={handleSaleSubmit} className="p-6 space-y-4">
              <div>
                <label className="block text-xs font-medium text-gray-600 mb-1">Medicine *</label>
                <select required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={form.medicine_id}
                  onChange={e => setForm(f => ({ ...f, medicine_id: e.target.value }))}>
                  <option value="">Select medicine...</option>
                  {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
              {[
                ['quantity', 'Quantity *', 'number', true],
                ['unit_price', 'Unit Price (€)', 'number', false],
                ['prescription_ref', 'Prescription Ref', 'text', false],
                ['served_by', 'Served By', 'text', false],
              ].map(([key, label, type, required]) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input required={required} type={type} min={0} step={key === 'unit_price' ? '0.01' : undefined}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                    value={form[key]}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))} />
                </div>
              ))}
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_prescription}
                  onChange={e => setForm(f => ({ ...f, is_prescription: e.target.checked }))} />
                Prescription required
              </label>
              <div className="flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : 'Record Sale'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
