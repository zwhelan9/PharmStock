import { useEffect, useState } from 'react'
import { cdRegisterApi, cdAnomaliesApi } from '../api/cdRegister'
import { medicinesApi } from '../api/medicines'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function CDRegister() {
  const [entries, setEntries] = useState([])
  const [anomalies, setAnomalies] = useState(null)
  const [medicines, setMedicines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('register')
  const [showCreate, setShowCreate] = useState(false)
  const [showCorrect, setShowCorrect] = useState(null)
  const [form, setForm] = useState({ transaction_type: 'receipt', medicine_id: '', quantity: '', counterparty_name: '', counterparty_address: '', authority_reference: '', prescriber_name: '', prescriber_reg_number: '' })
  const [correctForm, setCorrectForm] = useState({ correction_reason: '', quantity: '' })

  const load = () => {
    Promise.all([
      cdRegisterApi.listEntries({ limit: 200 }),
      medicinesApi.list(),
      cdAnomaliesApi.get(30).catch(() => null),
    ])
      .then(([e, m, a]) => { setEntries(e); setMedicines(m); setAnomalies(a) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  const handleCreate = async (e) => {
    e.preventDefault()
    try {
      await cdRegisterApi.createEntry({
        ...form,
        medicine_id: parseInt(form.medicine_id),
        quantity: parseInt(form.quantity),
        transaction_date: new Date().toISOString(),
      })
      setShowCreate(false)
      setForm({ transaction_type: 'receipt', medicine_id: '', quantity: '', counterparty_name: '', counterparty_address: '', authority_reference: '', prescriber_name: '', prescriber_reg_number: '' })
      load()
    } catch (err) { alert(err.message) }
  }

  const handleCorrect = async (e) => {
    e.preventDefault()
    try {
      await cdRegisterApi.correctEntry(showCorrect, {
        correction_reason: correctForm.correction_reason,
        quantity: correctForm.quantity ? parseInt(correctForm.quantity) : undefined,
      })
      setShowCorrect(null)
      setCorrectForm({ correction_reason: '', quantity: '' })
      load()
    } catch (err) { alert(err.message) }
  }

  const handleExport = async () => {
    try {
      const blob = await cdRegisterApi.exportCsv()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `cd_register_${new Date().toISOString().slice(0, 10)}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) { alert(err.message) }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} />

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {[['register', `📖 Register (${entries.length})`], ['anomalies', `⚠️ Anomalies (${anomalies?.total_anomalies || 0})`]].map(([t, l]) => (
            <button key={t} onClick={() => setTab(t)} className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'}`}>{l}</button>
          ))}
        </div>
        <div className="flex gap-2">
          <button onClick={handleExport} className="border border-gray-300 px-3 py-1.5 rounded-lg text-sm hover:bg-gray-50">Export CSV</button>
          <button onClick={() => setShowCreate(true)} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">+ New Entry</button>
        </div>
      </div>

      {tab === 'register' && (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['ID', 'Date', 'Type', 'Product', 'Qty', 'Balance', 'Counterparty', 'Prescriber', 'By', 'Status', ''].map(h => (
                  <th key={h} className="table-th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {entries.map(entry => (
                <tr key={entry.id} className={`hover:bg-gray-50 ${entry.is_voided ? 'opacity-40 line-through' : ''}`}>
                  <td className="table-td text-xs text-gray-400">#{entry.id}</td>
                  <td className="table-td text-xs">{entry.transaction_date?.slice(0, 10)}</td>
                  <td className="table-td">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${entry.transaction_type === 'receipt' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                      {entry.transaction_type}
                    </span>
                  </td>
                  <td className="table-td font-medium text-sm">{entry.product_name}</td>
                  <td className="table-td font-semibold">{entry.quantity}</td>
                  <td className="table-td font-bold">{entry.running_balance}</td>
                  <td className="table-td text-xs">{entry.counterparty_name}</td>
                  <td className="table-td text-xs">{entry.prescriber_name || '—'}</td>
                  <td className="table-td text-xs">{entry.entered_by_username}</td>
                  <td className="table-td">
                    {entry.is_correction && <span className="text-xs bg-yellow-100 text-yellow-700 px-1.5 py-0.5 rounded">Correction</span>}
                    {entry.is_voided && <span className="text-xs bg-red-100 text-red-700 px-1.5 py-0.5 rounded">Voided</span>}
                  </td>
                  <td className="table-td">
                    {!entry.is_voided && !entry.is_correction && (
                      <button onClick={() => { setShowCorrect(entry.id); setCorrectForm({ correction_reason: '', quantity: String(entry.quantity) }) }} className="text-xs text-blue-600 hover:underline">Correct</button>
                    )}
                  </td>
                </tr>
              ))}
              {!entries.length && <tr><td colSpan={11} className="table-td text-center py-8 text-gray-400">No CD register entries</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {tab === 'anomalies' && anomalies && (
        <div className="space-y-4">
          {!anomalies.anomalies.length ? (
            <div className="card p-8 text-center text-gray-400">No CD anomalies detected in the last {anomalies.lookback_days} days</div>
          ) : (
            <div className="card overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>{['Type', 'Medicine', 'Severity', 'Detail'].map(h => <th key={h} className="table-th">{h}</th>)}</tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {anomalies.anomalies.map((a, i) => (
                    <tr key={i} className="hover:bg-gray-50">
                      <td className="table-td"><span className="text-xs bg-purple-100 text-purple-700 px-2 py-0.5 rounded">{a.type}</span></td>
                      <td className="table-td font-medium">{a.medicine_name}</td>
                      <td className="table-td"><span className={`text-xs px-2 py-0.5 rounded-full font-medium ${a.severity === 'high' ? 'bg-red-100 text-red-700' : 'bg-yellow-100 text-yellow-700'}`}>{a.severity}</span></td>
                      <td className="table-td text-sm text-gray-600">{a.detail}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Create Entry Modal */}
      {showCreate && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-lg max-h-[90vh] overflow-y-auto">
            <h2 className="text-lg font-semibold mb-4">New CD Register Entry</h2>
            <form onSubmit={handleCreate} className="space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <select required className="border rounded-lg px-3 py-2 text-sm" value={form.transaction_type} onChange={e => setForm(f => ({ ...f, transaction_type: e.target.value }))}>
                  <option value="receipt">Receipt</option>
                  <option value="supply">Supply</option>
                </select>
                <select required className="border rounded-lg px-3 py-2 text-sm" value={form.medicine_id} onChange={e => setForm(f => ({ ...f, medicine_id: e.target.value }))}>
                  <option value="">Select CD...</option>
                  {medicines.filter(m => m.subcategory === 'Controlled' || m.category === 'Opioid Analgesic').map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                  {/* Also show all medicines as fallback */}
                  <optgroup label="All Medicines">
                    {medicines.map(m => <option key={`all-${m.id}`} value={m.id}>{m.name}</option>)}
                  </optgroup>
                </select>
              </div>
              <input required type="number" min="1" placeholder="Quantity" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.quantity} onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))} />
              <input required placeholder="Counterparty name (supplier/patient)" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.counterparty_name} onChange={e => setForm(f => ({ ...f, counterparty_name: e.target.value }))} />
              <input placeholder="Counterparty address" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.counterparty_address} onChange={e => setForm(f => ({ ...f, counterparty_address: e.target.value }))} />
              <input placeholder="Authority/prescription reference" className="w-full border rounded-lg px-3 py-2 text-sm" value={form.authority_reference} onChange={e => setForm(f => ({ ...f, authority_reference: e.target.value }))} />
              <div className="grid grid-cols-2 gap-3">
                <input placeholder="Prescriber name" className="border rounded-lg px-3 py-2 text-sm" value={form.prescriber_name} onChange={e => setForm(f => ({ ...f, prescriber_name: e.target.value }))} />
                <input placeholder="Prescriber reg #" className="border rounded-lg px-3 py-2 text-sm" value={form.prescriber_reg_number} onChange={e => setForm(f => ({ ...f, prescriber_reg_number: e.target.value }))} />
              </div>
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white py-2 rounded-lg text-sm font-medium">Save Entry</button>
                <button type="button" onClick={() => setShowCreate(false)} className="flex-1 border border-gray-300 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Correction Modal */}
      {showCorrect && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-sm">
            <h2 className="text-lg font-semibold mb-4">Correct Entry #{showCorrect}</h2>
            <form onSubmit={handleCorrect} className="space-y-3">
              <textarea required placeholder="Reason for correction *" className="w-full border rounded-lg px-3 py-2 text-sm" rows={2} value={correctForm.correction_reason} onChange={e => setCorrectForm(f => ({ ...f, correction_reason: e.target.value }))} />
              <input type="number" min="1" placeholder="Corrected quantity (optional)" className="w-full border rounded-lg px-3 py-2 text-sm" value={correctForm.quantity} onChange={e => setCorrectForm(f => ({ ...f, quantity: e.target.value }))} />
              <div className="flex gap-2 pt-2">
                <button type="submit" className="flex-1 bg-yellow-600 hover:bg-yellow-700 text-white py-2 rounded-lg text-sm font-medium">Submit Correction</button>
                <button type="button" onClick={() => setShowCorrect(null)} className="flex-1 border border-gray-300 py-2 rounded-lg text-sm">Cancel</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
