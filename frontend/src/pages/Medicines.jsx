import { useEffect, useState } from 'react'
import { medicinesApi } from '../api/medicines'
import AlertBadge from '../components/AlertBadge'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

const EMPTY = {
  name: '', generic_name: '', category: '', subcategory: '',
  manufacturer: '', supplier: '', unit: 'Tablet', unit_size: '',
  selling_price: '', reorder_level: 50, reorder_quantity: 200, description: '',
}

export default function Medicines() {
  const [medicines, setMedicines]   = useState([])
  const [categories, setCategories] = useState([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState(null)
  const [search, setSearch]         = useState('')
  const [catFilter, setCatFilter]   = useState('')
  const [showForm, setShowForm]     = useState(false)
  const [editing, setEditing]       = useState(null)
  const [form, setForm]             = useState(EMPTY)
  const [saving, setSaving]         = useState(false)

  const load = () => {
    setLoading(true)
    Promise.all([
      medicinesApi.list({ search: search || undefined, category: catFilter || undefined }),
      medicinesApi.categories(),
    ])
      .then(([meds, cats]) => { setMedicines(meds); setCategories(cats) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(load, [search, catFilter])

  const openCreate = () => { setEditing(null); setForm(EMPTY); setShowForm(true) }
  const openEdit = (m) => {
    setEditing(m.id)
    setForm({ ...m, selling_price: m.selling_price ?? '', unit_size: m.unit_size ?? '' })
    setShowForm(true)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      const payload = {
        ...form,
        selling_price: form.selling_price === '' ? null : parseFloat(form.selling_price),
        reorder_level: parseInt(form.reorder_level),
        reorder_quantity: parseInt(form.reorder_quantity),
      }
      if (editing) await medicinesApi.update(editing, payload)
      else await medicinesApi.create(payload)
      setShowForm(false)
      load()
    } catch (e) {
      alert(e.message)
    } finally {
      setSaving(false)
    }
  }

  if (loading && !medicines.length) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} onRetry={load} />

  return (
    <div className="space-y-4">
      {/* Toolbar */}
      <div className="flex flex-wrap gap-3 items-center justify-between">
        <div className="flex gap-2 flex-wrap">
          <input
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="Search medicines..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
          <select
            className="border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none"
            value={catFilter}
            onChange={e => setCatFilter(e.target.value)}
          >
            <option value="">All categories</option>
            {categories.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <button className="btn-primary" onClick={openCreate}>+ Add Medicine</button>
      </div>

      {/* Table */}
      <div className="card overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-100">
          <thead className="bg-gray-50">
            <tr>
              {['Name', 'Category', 'Unit', 'Supplier', 'Price', 'Stock', 'Reorder Level', 'Status'].map(h => (
                <th key={h} className="table-th">{h}</th>
              ))}
              <th className="table-th">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-50">
            {medicines.map(m => (
              <tr key={m.id} className="hover:bg-gray-50 transition-colors">
                <td className="table-td font-medium text-gray-900">
                  {m.name}
                  {m.expiring_soon_count > 0 && (
                    <span className="ml-2 badge bg-orange-100 text-orange-700 text-xs">
                      {m.expiring_soon_count} exp.
                    </span>
                  )}
                </td>
                <td className="table-td">{m.category}</td>
                <td className="table-td">{m.unit}</td>
                <td className="table-td text-gray-500">{m.supplier ?? '—'}</td>
                <td className="table-td">€{m.selling_price?.toFixed(2) ?? '—'}</td>
                <td className="table-td font-semibold">{m.total_stock ?? 0}</td>
                <td className="table-td">{m.reorder_level}</td>
                <td className="table-td">
                  <AlertBadge
                    type={m.is_low_stock ? 'high' : 'ok'}
                    label={m.is_low_stock ? 'Low Stock' : 'OK'}
                  />
                </td>
                <td className="table-td">
                  <button onClick={() => openEdit(m)} className="text-blue-600 hover:underline text-xs font-medium">
                    Edit
                  </button>
                </td>
              </tr>
            ))}
            {!medicines.length && (
              <tr><td colSpan={9} className="table-td text-center text-gray-400 py-8">No medicines found</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Modal form */}
      {showForm && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-screen overflow-y-auto">
            <div className="p-6 border-b flex items-center justify-between">
              <h2 className="font-semibold text-gray-800">{editing ? 'Edit Medicine' : 'Add Medicine'}</h2>
              <button onClick={() => setShowForm(false)} className="text-gray-400 hover:text-gray-600 text-xl">✕</button>
            </div>
            <form onSubmit={handleSubmit} className="p-6 grid grid-cols-2 gap-4">
              {[
                ['name', 'Name *', true],
                ['generic_name', 'Generic Name', false],
                ['category', 'Category *', true],
                ['subcategory', 'Subcategory', false],
                ['manufacturer', 'Manufacturer', false],
                ['supplier', 'Supplier', false],
                ['unit', 'Unit', false],
                ['unit_size', 'Unit Size', false],
                ['selling_price', 'Selling Price (€)', false],
                ['reorder_level', 'Reorder Level *', true],
                ['reorder_quantity', 'Reorder Qty *', true],
              ].map(([key, label, required]) => (
                <div key={key} className={key === 'name' ? 'col-span-2' : ''}>
                  <label className="block text-xs font-medium text-gray-600 mb-1">{label}</label>
                  <input
                    required={required}
                    type={['selling_price', 'reorder_level', 'reorder_quantity'].includes(key) ? 'number' : 'text'}
                    step={key === 'selling_price' ? '0.01' : undefined}
                    min={0}
                    className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                    value={form[key]}
                    onChange={e => setForm(f => ({ ...f, [key]: e.target.value }))}
                  />
                </div>
              ))}
              <div className="col-span-2">
                <label className="block text-xs font-medium text-gray-600 mb-1">Description</label>
                <textarea
                  rows={2}
                  className="w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none"
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                />
              </div>
              <div className="col-span-2 flex justify-end gap-3 pt-2">
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>Cancel</button>
                <button type="submit" className="btn-primary" disabled={saving}>
                  {saving ? 'Saving...' : editing ? 'Update' : 'Create'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
