import { useEffect, useState } from 'react'
import { cdDestructionApi } from '../api/cdRegister'
import { medicinesApi } from '../api/medicines'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function CDDestruction() {
  const [records, setRecords] = useState([])
  const [medicines, setMedicines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ medicine_id: '', quantity_destroyed: '', witnessed_by_user_id: '', witness_password: '', date_of_destruction: new Date().toISOString().slice(0, 10) })

  const load = () => {
    Promise.all([cdDestructionApi.list(), medicinesApi.list()])
      .then(([r, m]) => { setRecords(r); setMedicines(m) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await cdDestructionApi.create({
        ...form,
        medicine_id: parseInt(form.medicine_id),
        quantity_destroyed: parseInt(form.quantity_destroyed),
        witnessed_by_user_id: parseInt(form.witnessed_by_user_id),
      })
      setShowCreate(false)
      setForm({ medicine_id: '', quantity_destroyed: '', witnessed_by_user_id: '', witness_password: '', date_of_destruction: new Date().toISOString().slice(0, 10) })
      load()
    } catch (err) { alert(err.message) }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-gray-500">Destruction records with digital witness signature</p>
          <p className="text-xs text-gray-400">Witness must re-authenticate to sign off (FR-CD-1.4)</p>
        </div>
        <button onClick={() => setShowCreate(true)} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Record Destruction</button>
      </div>

      <div className="card overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              {['ID', 'Date', 'Product', 'Qty Destroyed', 'Witness', 'Authenticated', 'Signature', 'Created By'].map(h => (
                <th key={h} className="table-th">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {records.map(r => (
              <tr key={r.id} className="hover:bg-gray-50">
                <td className="table-td text-xs text-gray-400">#{r.id}</td>
                <td className="table-td">{r.date_of_destruction}</td>
                <td className="table-td font-medium">{r.product_name}</td>
                <td className="table-td font-bold text-red-600">{r.quantity_destroyed}</td>
                <td className="table-td">{r.witness_name}</td>
                <td className="table-td text-xs">{r.witness_authenticated_at?.slice(0, 16) || '—'}</td>
                <td className="table-td font-mono text-xs text-gray-400">{r.digital_signature_hash?.slice(0, 12)}…</td>
                <td className="table-td text-xs">{r.created_by_username}</td>
              </tr>
            ))}
            {!records.length && <tr><td colSpan={8} className="table-td text-center py-8 text-gray-400">No destruction records</td></tr>}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-2">Record CD Destruction</h2>
            <p className="text-xs text-gray-500 mb-4">The witness must provide their password to authenticate the sign-off</p>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required type="date" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.date_of_destruction} onChange={e => setForm(f => ({ ...f, date_of_destruction: e.target.value }))} />
              <select required className="w-full border rounded-lg px-3 py-2 text-sm" value={form.medicine_id} onChange={e => setForm(f => ({ ...f, medicine_id: e.target.value }))}>
                <option value="">Select controlled drug...</option>
                {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <input required type="number" min="1" placeholder="Quantity to destroy" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.quantity_destroyed} onChange={e => setForm(f => ({ ...f, quantity_destroyed: e.target.value }))} />
              <div className="border-t pt-3 mt-3">
                <p className="text-xs font-semibold text-gray-600 mb-2">Witness Authentication</p>
                <input required type="number" placeholder="Witness User ID" className="w-full border rounded-lg px-3 py-2 text-sm mb-2" value={form.witnessed_by_user_id} onChange={e => setForm(f => ({ ...f, witnessed_by_user_id: e.target.value }))} />
                <input required type="password" placeholder="Witness password (re-authentication)" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.witness_password} onChange={e => setForm(f => ({ ...f, witness_password: e.target.value }))} />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg text-sm font-medium">Confirm Destruction</button>
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 border border-gray-300 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
