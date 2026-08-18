import { useEffect, useState } from 'react'
import { writeoffsApi, packsApi } from '../api/packs'
import { medicinesApi } from '../api/medicines'
import { useAuth } from '../context/AuthContext'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

const REASON_CODES = [
  { value: 'damaged', label: 'Damaged' },
  { value: 'expired', label: 'Expired' },
  { value: 'spillage_contamination', label: 'Spillage / Contamination' },
  { value: 'short_dated_return_to_supplier', label: 'Short-Dated Return' },
  { value: 'dispensing_error', label: 'Dispensing Error' },
  { value: 'theft_loss', label: 'Theft / Loss' },
  { value: 'recall', label: 'Recall' },
]

export default function WriteOffs() {
  const { user } = useAuth()
  const [tab, setTab] = useState('list')
  const [writeoffs, setWriteoffs] = useState([])
  const [pending, setPending] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [showCreate, setShowCreate] = useState(false)
  const [medicines, setMedicines] = useState([])
  const [packs, setPacks] = useState([])
  const [form, setForm] = useState({ pack_instance_id: '', quantity: '', reason_code: '', notes: '' })
  const [selectedMed, setSelectedMed] = useState('')

  // Report state
  const [reportStart, setReportStart] = useState('')
  const [reportEnd, setReportEnd] = useState('')
  const [report, setReport] = useState(null)

  const load = () => {
    Promise.all([
      writeoffsApi.list(),
      writeoffsApi.pendingCountersign().catch(() => []),
    ])
      .then(([wo, p]) => { setWriteoffs(wo); setPending(p) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => {
    medicinesApi.list().then(setMedicines).catch(() => {})
    load()
  }, [])

  useEffect(() => {
    if (selectedMed) {
      packsApi.list({ medicine_id: selectedMed, status: 'open' })
        .then(openPacks => {
          packsApi.list({ medicine_id: selectedMed, status: 'sealed' })
            .then(sealedPacks => setPacks([...openPacks, ...sealedPacks]))
        })
    } else {
      setPacks([])
    }
  }, [selectedMed])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await writeoffsApi.create({
        pack_instance_id: parseInt(form.pack_instance_id),
        quantity: parseInt(form.quantity),
        reason_code: form.reason_code,
        notes: form.notes || null,
      })
      setShowCreate(false)
      setForm({ pack_instance_id: '', quantity: '', reason_code: '', notes: '' })
      setSelectedMed('')
      load()
    } catch (err) { alert(err.message) }
  }

  const handleCountersign = async (id) => {
    if (!confirm('Countersign this write-off?')) return
    try {
      await writeoffsApi.countersign(id)
      load()
    } catch (err) { alert(err.message) }
  }

  const loadReport = async () => {
    if (!reportStart || !reportEnd) return
    try {
      const r = await writeoffsApi.report(reportStart, reportEnd)
      setReport(r)
    } catch (err) { alert(err.message) }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} />

  return (
    <div className="space-y-4">
      {/* Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {[['list', 'Write-Offs'], ['pending', `Pending (${pending.length})`], ['report', 'Cost Report']].map(([t, l]) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'}`}>
              {l}
            </button>
          ))}
        </div>
        <button onClick={() => setShowCreate(true)} className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ New Write-Off</button>
      </div>

      {/* List tab */}
      {tab === 'list' && (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['ID', 'Medicine', 'Pack', 'Qty', 'Reason', 'Value', 'Status', 'Initiated By', 'Date'].map(h => (
                  <th key={h} className="table-th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {writeoffs.map(wo => (
                <tr key={wo.id} className="hover:bg-gray-50">
                  <td className="table-td text-xs text-gray-400">#{wo.id}</td>
                  <td className="table-td font-medium">{wo.medicine_name}</td>
                  <td className="table-td text-xs">Pack #{wo.pack_instance_id}</td>
                  <td className="table-td font-semibold">{wo.quantity}</td>
                  <td className="table-td"><span className="text-xs bg-red-50 text-red-700 px-2 py-0.5 rounded">{wo.reason_code}</span></td>
                  <td className="table-td">{wo.cost_unavailable ? <span className="text-xs text-gray-400">N/A</span> : wo.calculated_value != null ? `€${wo.calculated_value.toFixed(2)}` : '—'}</td>
                  <td className="table-td"><span className={`text-xs px-2 py-0.5 rounded-full font-medium ${wo.status === 'finalised' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>{wo.status}</span></td>
                  <td className="table-td text-xs">{wo.initiated_by_username}</td>
                  <td className="table-td text-xs">{wo.initiated_at?.slice(0, 10)}</td>
                </tr>
              ))}
              {!writeoffs.length && (
                <tr><td colSpan={9} className="table-td text-center py-8 text-gray-400">No write-offs recorded</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {/* Pending countersign tab */}
      {tab === 'pending' && (
        <div className="card overflow-x-auto">
          {!pending.length ? (
            <p className="p-8 text-center text-gray-400">No pending countersigns</p>
          ) : (
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['ID', 'Medicine', 'Qty', 'Reason', 'Initiated By', 'Deadline', 'Action'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {pending.map(wo => (
                  <tr key={wo.id} className="hover:bg-gray-50">
                    <td className="table-td">#{wo.id}</td>
                    <td className="table-td font-medium">{wo.medicine_name}</td>
                    <td className="table-td font-semibold">{wo.quantity}</td>
                    <td className="table-td text-xs">{wo.reason_code}</td>
                    <td className="table-td text-xs">{wo.initiated_by_username}</td>
                    <td className="table-td text-xs">{wo.countersign_deadline?.slice(0, 16)}</td>
                    <td className="table-td">
                      {wo.initiated_by_user_id !== user?.id ? (
                        <button onClick={() => handleCountersign(wo.id)} className="text-xs bg-blue-600 text-white px-3 py-1 rounded hover:bg-blue-700">Countersign</button>
                      ) : (
                        <span className="text-xs text-gray-400">You initiated</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* Report tab */}
      {tab === 'report' && (
        <div className="space-y-4">
          <div className="flex gap-3 items-end flex-wrap">
            <div>
              <label className="text-xs text-gray-500 block mb-1">Start date</label>
              <input type="date" className="border rounded-lg px-3 py-2 text-sm" value={reportStart} onChange={e => setReportStart(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-gray-500 block mb-1">End date</label>
              <input type="date" className="border rounded-lg px-3 py-2 text-sm" value={reportEnd} onChange={e => setReportEnd(e.target.value)} />
            </div>
            <button onClick={loadReport} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Generate Report</button>
          </div>
          {report && (
            <div className="card overflow-x-auto">
              <div className="p-4 border-b border-gray-100 flex justify-between items-center">
                <h3 className="font-medium text-gray-700">Write-Off Cost Report: {report.start_date} to {report.end_date}</h3>
                <div className="text-sm">
                  <span className="text-gray-500">Total: </span>
                  <span className="font-bold text-red-600">{report.grand_total_value != null ? `€${report.grand_total_value.toFixed(2)}` : 'N/A'}</span>
                  <span className="text-gray-400 ml-3">({report.grand_total_quantity} units)</span>
                </div>
              </div>
              <table className="min-w-full divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>
                    {['Reason', 'Medicine', 'Qty', 'Value', 'Count', 'Cost N/A'].map(h => (
                      <th key={h} className="table-th">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {report.rows.map((r, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="table-td text-xs">{r.reason_code}</td>
                      <td className="table-td font-medium">{r.medicine_name}</td>
                      <td className="table-td">{r.total_quantity}</td>
                      <td className="table-td font-semibold">{r.total_value != null ? `€${r.total_value.toFixed(2)}` : '—'}</td>
                      <td className="table-td">{r.count}</td>
                      <td className="table-td text-xs text-gray-400">{r.cost_unavailable_count > 0 ? r.cost_unavailable_count : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Create write-off modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-md">
            <h2 className="text-lg font-semibold mb-4">New Write-Off</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <select className="w-full border rounded-lg px-3 py-2 text-sm" value={selectedMed} onChange={e => { setSelectedMed(e.target.value); setForm(f => ({ ...f, pack_instance_id: '' })) }}>
                <option value="">Select medicine...</option>
                {medicines.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select>
              <select required className="w-full border rounded-lg px-3 py-2 text-sm" value={form.pack_instance_id} onChange={e => setForm(f => ({ ...f, pack_instance_id: e.target.value }))}>
                <option value="">Select pack instance...</option>
                {packs.map(p => <option key={p.id} value={p.id}>#{p.id} — {p.batch_number} (rem: {p.quantity_remaining}, exp: {p.expiry_date})</option>)}
              </select>
              <input required type="number" min="1" placeholder="Quantity" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.quantity} onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))} />
              <select required className="w-full border rounded-lg px-3 py-2 text-sm" value={form.reason_code} onChange={e => setForm(f => ({ ...f, reason_code: e.target.value }))}>
                <option value="">Select reason...</option>
                {REASON_CODES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
              </select>
              <textarea maxLength={500} placeholder="Notes (optional, max 500 chars)" className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} />
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 bg-red-600 hover:bg-red-700 text-white py-2 rounded-lg text-sm font-medium">Submit Write-Off</button>
                <button type="button" onClick={() => { setShowCreate(false); setSelectedMed('') }} className="flex-1 border border-gray-300 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
