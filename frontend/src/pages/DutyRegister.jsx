import { useEffect, useState } from 'react'
import { dutyRegisterApi } from '../api/cdRegister'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function DutyRegister() {
  const { user } = useAuth()
  const [entries, setEntries] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({ duty_date: new Date().toISOString().slice(0, 10), pharmacist_user_id: '', role: 'pharmacist', start_time: '', end_time: '' })

  const load = () => {
    dutyRegisterApi.list({ limit: 200 })
      .then(setEntries)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await dutyRegisterApi.create({
        ...form,
        pharmacist_user_id: parseInt(form.pharmacist_user_id || user.id),
      })
      setShowCreate(false)
      load()
    } catch (err) { alert(err.message) }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm text-gray-500">Pharmacists on duty — mandatory from 30 June 2026</h2>
        <button onClick={() => setShowCreate(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ Record Duty</button>
      </div>

      <div className="card overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              {['Date', 'Pharmacist', 'Role', 'Start', 'End', 'Entered By', 'Status'].map(h => (
                <th key={h} className="table-th">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {entries.map(entry => (
              <tr key={entry.id} className={`hover:bg-gray-50 ${entry.is_voided ? 'opacity-40' : ''}`}>
                <td className="table-td font-medium">{entry.duty_date}</td>
                <td className="table-td">{entry.pharmacist_name}</td>
                <td className="table-td"><span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">{entry.role}</span></td>
                <td className="table-td text-sm">{entry.start_time || '—'}</td>
                <td className="table-td text-sm">{entry.end_time || '—'}</td>
                <td className="table-td text-xs text-gray-500">{entry.entered_by_username}</td>
                <td className="table-td">
                  {entry.is_correction && <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">Correction</span>}
                  {entry.is_voided && <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">Voided</span>}
                  {!entry.is_correction && !entry.is_voided && <span className="text-xs bg-green-100 text-green-700 px-1.5 py-0.5 rounded">Active</span>}
                </td>
              </tr>
            ))}
            {!entries.length && <tr><td colSpan={7} className="table-td text-center py-8 text-gray-400">No duty entries recorded</td></tr>}
          </tbody>
        </table>
      </div>

      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
            <h2 className="text-lg font-semibold mb-4">Record Pharmacist on Duty</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <input required type="date" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.duty_date} onChange={e => setForm(f => ({ ...f, duty_date: e.target.value }))} />
              <input type="number" placeholder={`User ID (default: you — ${user?.id})`} className="w-full border rounded-lg px-3 py-2 text-sm" value={form.pharmacist_user_id} onChange={e => setForm(f => ({ ...f, pharmacist_user_id: e.target.value }))} />
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
                <option value="pharmacist">Pharmacist</option>
                <option value="superintendent">Superintendent</option>
                <option value="owner">Owner</option>
              </select>
              <div className="grid grid-cols-2 gap-3">
                <input type="time" placeholder="Start" className="border rounded-lg px-3 py-2 text-sm" value={form.start_time} onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))} />
                <input type="time" placeholder="End" className="border rounded-lg px-3 py-2 text-sm" value={form.end_time} onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))} />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg text-sm font-medium">Save</button>
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 border border-gray-300 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
