import { useEffect, useState } from 'react'
import { packsApi, dispenseApi } from '../api/packs'
import { medicinesApi } from '../api/medicines'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

const statusBadge = {
  sealed: 'bg-gray-100 text-gray-700',
  open:   'bg-blue-100 text-blue-700',
  empty:  'bg-gray-50 text-gray-400',
}

export default function PackInventory() {
  const [packs, setPacks] = useState([])
  const [medicines, setMedicines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [filter, setFilter] = useState({ medicine_id: '', status: '' })
  const [showCreate, setShowCreate] = useState(false)
  const [showDispense, setShowDispense] = useState(false)
  const [form, setForm] = useState({})
  const [dispenseForm, setDispenseForm] = useState({ medicine_id: '', quantity: '' })

  const load = () => {
    const params = {}
    if (filter.medicine_id) params.medicine_id = filter.medicine_id
    if (filter.status) params.status = filter.status
    packsApi.list(params)
      .then(setPacks)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    medicinesApi.list().then(setMedicines).catch(() => {})
    load()
  }, [])

  useEffect(() => { load() }, [filter.medicine_id, filter.status])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await packsApi.create({
        ...form,
        quantity_received: parseInt(form.quantity_received),
        unit_cost: form.unit_cost ? parseFloat(form.unit_cost) : null,
        is_controlled_drug: form.is_controlled_drug || false,
        medicine_id: parseInt(form.medicine_id),
      })
      setShowCreate(false)
      setForm({})
      load()
    } catch (err) { alert(err.message) }
  }

  const handleDispense = async (e) => {
    e.preventDefault()
    try {
      await dispenseApi.create({
        medicine_id: parseInt(dispenseForm.medicine_id),
        quantity: parseInt(dispenseForm.quantity),
      })
      setShowDispense(false)
      setDispenseForm({ medicine_id: '', quantity: '' })
      load()
    } catch (err) { alert(err.message) }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} />

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-2 items-center flex-wrap">
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={filter.medicine_id} onChange={e => setFilter(f => ({ ...f, medicine_id: e.target.value }))}>
            <option value="">All medicines</option>
            {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
          </select>
          <select className="border border-gray-300 rounded-lg px-3 py-2 text-sm" value={filter.status} onChange={e => setFilter(f => ({ ...f, status: e.target.value }))}>
            <option value="">All statuses</option>
            <option value="sealed">Sealed</option>
            <option value="open">Open</option>
            <option value="empty">Empty</option>
          </select>
        </div>
        <div className="flex gap-2">
          <button onClick={() => setShowDispense(true)} className="bg-green-600 hover:bg-green-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Dispense</button>
          <button onClick={() => setShowCreate(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Receive Delivery</button>
        </div>
      </div>

      {/* Pack table */}
      <div className="card overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              {['ID', 'Medicine', 'Batch #', 'Expiry', 'Received', 'Remaining', 'Status', 'Unit Cost', 'CD'].map(h => (
                <th key={h} className="table-th">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {packs.map(p => (
              <tr key={p.id} className="hover:bg-gray-50">
                <td className="table-td text-gray-400 text-xs">#{p.id}</td>
                <td className="table-td font-medium">{p.medicine_name}</td>
                <td className="table-td font-mono text-xs">{p.batch_number}</td>
                <td className="table-td">{p.expiry_date}</td>
                <td className="table-td">{p.quantity_received}</td>
                <td className="table-td font-semibold">{p.quantity_remaining}</td>
                <td className="table-td">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusBadge[p.status] || ''}`}>{p.status}</span>
                </td>
                <td className="table-td">{p.unit_cost != null ? `€${p.unit_cost.toFixed(2)}` : '—'}</td>
                <td className="table-td">{p.is_controlled_drug ? '💊' : ''}</td>
              </tr>
            ))}
            {!packs.length && (
              <tr><td colSpan={9} className="table-td text-center py-8 text-gray-400">No pack instances found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Create modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">Receive Delivery — New Pack</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <select required className="w-full border rounded-lg px-3 py-2 text-sm" value={form.medicine_id || ''} onChange={e => setForm(f => ({ ...f, medicine_id: e.target.value }))}>
                <option value="">Select medicine...</option>
                {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <input required placeholder="Batch number" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.batch_number || ''} onChange={e => setForm(f => ({ ...f, batch_number: e.target.value }))} />
              <input required type="date" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.expiry_date || ''} onChange={e => setForm(f => ({ ...f, expiry_date: e.target.value }))} />
              <input required type="number" min="1" placeholder="Quantity received" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.quantity_received || ''} onChange={e => setForm(f => ({ ...f, quantity_received: e.target.value }))} />
              <input type="number" step="0.01" placeholder="Unit cost (optional)" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.unit_cost || ''} onChange={e => setForm(f => ({ ...f, unit_cost: e.target.value }))} />
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_controlled_drug || false} onChange={e => setForm(f => ({ ...f, is_controlled_drug: e.target.checked }))} />
                Controlled Drug
              </label>
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg text-sm font-medium">Create Pack</button>
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 border border-gray-300 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Dispense modal */}
      {showDispense && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
            <h2 className="text-lg font-semibold mb-4">Dispense (FEFO)</h2>
            <form onSubmit={handleDispense} className="space-y-3">
              <select required className="w-full border rounded-lg px-3 py-2 text-sm" value={dispenseForm.medicine_id} onChange={e => setDispenseForm(f => ({ ...f, medicine_id: e.target.value }))}>
                <option value="">Select medicine...</option>
                {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <input required type="number" min="1" placeholder="Quantity" className="w-full border rounded-lg px-3 py-2 text-sm" value={dispenseForm.quantity} onChange={e => setDispenseForm(f => ({ ...f, quantity: e.target.value }))} />
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 bg-green-600 hover:bg-green-700 text-white py-2 rounded-lg text-sm font-medium">Dispense</button>
                <button type="button" onClick={() => setShowDispense(false)} className="flex-1 border border-gray-300 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
