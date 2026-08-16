import { useEffect, useState } from 'react'
import { stockApi } from '../api/stock'
import { batchesApi } from '../api/batches'
import { medicinesApi } from '../api/medicines'
import AlertBadge from '../components/AlertBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

const BATCH_EMPTY = {
  medicine_id: '', batch_number: '', supplier_invoice: '', supplier: '',
  quantity_received: '', cost_price: '', purchase_date: '', manufacture_date: '',
  expiry_date: '', notes: '',
}

export default function StockManagement() {
  const [levels, setLevels]         = useState([])
  const [batches, setBatches]       = useState([])
  const [medicines, setMedicines]   = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [tab, setTab]               = useState('levels')    // levels | batches | logs
  const [logs, setLogs]             = useState([])
  const [showBatchForm, setShowBatchForm] = useState(false)
  const [batchForm, setBatchForm]   = useState(BATCH_EMPTY)
  const [saving, setSaving]         = useState(false)
  const [lowOnly, setLowOnly]       = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const [lvl, meds] = await Promise.all([
        stockApi.levels({ low_stock_only: lowOnly }),
        medicinesApi.list(),
      ])
      setLevels(lvl)
      setMedicines(meds)
      if (tab === 'batches') {
        const b = await batchesApi.list({ active_only: true })
        setBatches(b)
      }
      if (tab === 'logs') {
        const l = await stockApi.logs({ limit: 100 })
        setLogs(l)
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [tab, lowOnly])

  const handleBatchSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      await batchesApi.create({
        ...batchForm,
        medicine_id: parseInt(batchForm.medicine_id),
        quantity_received: parseInt(batchForm.quantity_received),
        cost_price: batchForm.cost_price ? parseFloat(batchForm.cost_price) : null,
      })
      setShowBatchForm(false)
      setBatchForm(BATCH_EMPTY)
      load()
    } catch (e) {
      alert(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading && !levels.length) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {[['levels', '📊 Stock Levels'], ['batches', '📦 Batches'], ['logs', '📋 Stock Logs']].map(([t, l]) => (
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
        <div className="flex items-center gap-3">
          {tab === 'levels' && (
            <label className="flex items-center gap-2 text-sm text-gray-600">
              <input type="checkbox" checked={lowOnly} onChange={e => setLowOnly(e.target.checked)} />
              Low stock only
            </label>
          )}
          {tab === 'batches' && (
            <button className="btn-primary" onClick={() => setShowBatchForm(true)}>+ Add Batch</button>
          )}
        </div>
      </div>

      {/* Stock Levels Tab */}
      {tab === 'levels' && (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['Medicine', 'Category', 'Unit', 'Current Stock', 'Reorder Level', 'Reorder Qty', 'Status'].map(h => (
                  <th key={h} className="table-th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {levels.map(l => (
                <tr key={l.medicine_id} className="hover:bg-gray-50">
                  <td className="table-td font-medium">{l.medicine_name}</td>
                  <td className="table-td">{l.category}</td>
                  <td className="table-td text-gray-500">{l.unit}</td>
                  <td className="table-td">
                    <span className={`font-semibold ${l.is_low_stock ? 'text-red-600' : 'text-gray-800'}`}>
                      {l.total_stock.toLocaleString()}
                    </span>
                  </td>
                  <td className="table-td">{l.reorder_level}</td>
                  <td className="table-td">{l.reorder_quantity}</td>
                  <td className="table-td">
                    <AlertBadge
                      type={l.total_stock === 0 ? 'high' : l.is_low_stock ? 'medium' : 'ok'}
                      label={l.total_stock === 0 ? 'Out of Stock' : l.is_low_stock ? 'Low Stock' : 'OK'}
                    />
                  </td>
                </tr>
              ))}
              {!levels.length && (
                <tr><td colSpan={7} className="table-td text-center py-8 text-gray-400">No stock data</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Batches Tab */}
      {tab === 'batches' && (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['Medicine', 'Batch No.', 'Supplier', 'Qty Received', 'Qty Remaining', 'Purchase Date', 'Expiry Date', 'Status'].map(h => (
                  <th key={h} className="table-th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {batches.map(b => {
                const m = medicines.find(m => m.id === b.medicine_id)
                return (
                  <tr key={b.id} className="hover:bg-gray-50">
                    <td className="table-td font-medium">{m?.name ?? `#${b.medicine_id}`}</td>
                    <td className="table-td font-mono text-xs">{b.batch_number}</td>
                    <td className="table-td text-gray-500">{b.supplier ?? '—'}</td>
                    <td className="table-td">{b.quantity_received}</td>
                    <td className="table-td font-semibold">{b.quantity_remaining}</td>
                    <td className="table-td">{b.purchase_date}</td>
                    <td className="table-td">{b.expiry_date}</td>
                    <td className="table-td">
                      <AlertBadge type={b.expiry_status} label={b.expiry_status?.toUpperCase()} />
                    </td>
                  </tr>
                )
              })}
              {!batches.length && (
                <tr><td colSpan={8} className="table-td text-center py-8 text-gray-400">No batches</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Logs Tab */}
      {tab === 'logs' && (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['Date', 'Medicine', 'Type', 'Qty Change', 'Before', 'After', 'Notes'].map(h => (
                  <th key={h} className="table-th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {logs.map(l => (
                <tr key={l.id} className="hover:bg-gray-50">
                  <td className="table-td text-xs text-gray-500">
                    {new Date(l.log_date).toLocaleString()}
                  </td>
                  <td className="table-td font-medium">{l.medicine_name}</td>
                  <td className="table-td">
                    <span className="badge bg-gray-100 text-gray-700">{l.change_type}</span>
                  </td>
                  <td className={`table-td font-semibold ${l.quantity < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {l.quantity > 0 ? '+' : ''}{l.quantity}
                  </td>
                  <td className="table-td">{l.stock_before ?? '—'}</td>
                  <td className="table-td">{l.stock_after ?? '—'}</td>
                  <td className="table-td text-gray-500 max-w-xs truncate">{l.notes ?? '—'}</td>
                </tr>
              ))}
              {!logs.length && (
                <tr><td colSpan={7} className="table-td text-center py-8 text-gray-400">No logs</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Add Batch Modal */}
      {showBatchForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-xl max-h-screen overflow-y-auto">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="font-semibold">Add New Batch</h2>
              <button onClick={() => setShowBatchForm(false)} className="text-gray-400 text-xl">✕</button>
            </div>
            <form onSubmit={handleBatchSubmit} className="p-6 grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Medicine *</label>
                <select
                  required
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none"
                  value={batchForm.medicine_id}
                  onChange={e => setBatchForm(f => ({ ...f, medicine_id: e.target.value }))}
                >
                  <option value="">Select medicine...</option>
                  {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                </select>
              </div>
              {[
                ['batch_number', 'Batch Number *', 'text', true],
                ['supplier_invoice', 'Invoice No.', 'text', false],
                ['supplier', 'Supplier', 'text', false],
                ['quantity_received', 'Quantity Received *', 'number', true],
                ['cost_price', 'Cost Price per Unit (€)', 'number', false],
                ['purchase_date', 'Purchase Date *', 'date', true],
                ['manufacture_date', 'Manufacture Date', 'date', false],
                ['expiry_date', 'Expiry Date *', 'date', true],
              ].map(([key, label, type, required]) => (
                <div key={key}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input
                    required={required}
                    type={type}
                    step={key === 'cost_price' ? '0.0001' : undefined}
                    min={0}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none"
                    value={batchForm[key]}
                    onChange={e => setBatchForm(f => ({ ...f, [key]: e.target.value }))}
                  />
                </div>
              ))}
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Notes</label>
                <textarea rows={2} className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm"
                  value={batchForm.notes}
                  onChange={e => setBatchForm(f => ({ ...f, notes: e.target.value }))} />
              </div>
              <div className="col-span-2 flex justify-end gap-3">
                <button type="button" className="btn-secondary" onClick={() => setShowBatchForm(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : 'Add Batch'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
