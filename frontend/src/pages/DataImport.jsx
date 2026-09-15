import { useEffect, useState, useRef } from 'react'
import { integrationApi } from '../api/integration'
import LoadingSpinner from '../components/LoadingSpinner'
import ErrorMessage from '../components/ErrorMessage'

export default function DataImport() {
  const [syncStatus, setSyncStatus] = useState(null)
  const [reconciliation, setReconciliation] = useState(null)
  const [importLogs, setImportLogs] = useState([])
  const [quarantined, setQuarantined] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [tab, setTab] = useState('status')
  const [uploading, setUploading] = useState(false)
  const [uploadResult, setUploadResult] = useState(null)
  const fileRef = useRef(null)

  const load = async () => {
    setLoading(true)
    try {
      const [ss, logs] = await Promise.all([
        integrationApi.syncStatus(),
        integrationApi.importLogs(20),
      ])
      setSyncStatus(ss)
      setImportLogs(logs)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const runReconciliation = async () => {
    try {
      const r = await integrationApi.reconciliation(2.0)
      setReconciliation(r)
      setTab('reconciliation')
    } catch (e) { alert(e.message) }
  }

  const loadQuarantined = async (logId) => {
    try {
      const q = await integrationApi.quarantined(logId)
      setQuarantined(q)
      setTab('quarantined')
    } catch (e) { alert(e.message) }
  }

  const handleUpload = async (type) => {
    const file = fileRef.current?.files?.[0]
    if (!file) { alert('Please select a CSV file'); return }
    if (!file.name.endsWith('.csv')) { alert('Only .csv files are accepted'); return }

    setUploading(true)
    setUploadResult(null)
    try {
      const result = type === 'dispense'
        ? await integrationApi.importDispenseEvents(file)
        : await integrationApi.importStockSnapshot(file)
      setUploadResult(result)
      fileRef.current.value = ''
      load()  // refresh status
    } catch (e) {
      setUploadResult({ status: 'failed', error: e.message })
    } finally {
      setUploading(false)
    }
  }

  if (loading) return <LoadingSpinner />
  if (error) return <ErrorMessage message={error} />

  return (
    <div className="space-y-4">
      {/* Sync Status Banner */}
      {syncStatus && (
        <div className={`card p-4 border ${syncStatus.is_stale ? 'border-red-200 bg-red-50' : 'border-green-200 bg-green-50'}`}>
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{syncStatus.is_stale ? '⚠️' : '✅'}</span>
              <div>
                <p className={`font-semibold ${syncStatus.is_stale ? 'text-red-700' : 'text-green-700'}`}>
                  {syncStatus.is_stale ? 'Data is stale' : 'Data is fresh'}
                </p>
                <p className="text-sm text-gray-600">
                  {syncStatus.last_successful_sync
                    ? `Last sync: ${new Date(syncStatus.last_successful_sync).toLocaleString()} (${syncStatus.hours_since_last_sync}h ago)`
                    : 'No imports recorded yet'}
                </p>
              </div>
            </div>
            <div className="flex gap-4 text-sm text-gray-500">
              <span>{syncStatus.total_imports} imports</span>
              <span>{syncStatus.total_dispense_events} events</span>
              <span>{syncStatus.total_snapshots} snapshots</span>
            </div>
          </div>
        </div>
      )}

      {/* Tabs */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex gap-1 bg-gray-100 p-1 rounded-lg">
          {[
            ['status', '📊 Import History'],
            ['upload', '📤 Upload'],
            ['reconciliation', '🔄 Reconciliation'],
            ['quarantined', '🚫 Quarantined'],
          ].map(([t, l]) => (
            <button key={t} onClick={() => setTab(t)}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-colors ${tab === t ? 'bg-white shadow text-blue-700' : 'text-gray-500 hover:text-gray-700'}`}>
              {l}
            </button>
          ))}
        </div>
        <button onClick={runReconciliation} className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm font-medium">Run Reconciliation</button>
      </div>

      {/* Upload Tab */}
      {tab === 'upload' && (
        <div className="card p-6 space-y-4">
          <h3 className="font-semibold text-gray-800">Import CSV Data</h3>
          <p className="text-sm text-gray-500">Upload a CSV file matching the data contract. Malformed rows will be quarantined, duplicates will be skipped.</p>

          <div className="border-2 border-dashed border-gray-200 rounded-xl p-6 text-center">
            <input ref={fileRef} type="file" accept=".csv" className="mb-4" />
            <div className="flex gap-3 justify-center mt-3">
              <button onClick={() => handleUpload('dispense')} disabled={uploading}
                className="bg-green-600 hover:bg-green-700 disabled:bg-gray-300 text-white px-4 py-2 rounded-lg text-sm font-medium">
                {uploading ? 'Importing...' : 'Import as Dispense Events'}
              </button>
              <button onClick={() => handleUpload('snapshot')} disabled={uploading}
                className="bg-purple-600 hover:bg-purple-700 disabled:bg-gray-300 text-white px-4 py-2 rounded-lg text-sm font-medium">
                {uploading ? 'Importing...' : 'Import as Stock Snapshot'}
              </button>
            </div>
          </div>

          {/* Data contract reference */}
          <div className="bg-gray-50 rounded-lg p-4 mt-4">
            <p className="text-xs font-semibold text-gray-600 mb-2">Expected CSV columns:</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs text-gray-500">
              <div>
                <p className="font-medium text-gray-700 mb-1">Dispense Events:</p>
                <p>event_id, timestamp, product_code, quantity_dispensed, transaction_type</p>
                <p className="text-gray-400 mt-0.5">Optional: pack_size, batch_number, is_controlled_drug</p>
              </div>
              <div>
                <p className="font-medium text-gray-700 mb-1">Stock Snapshot:</p>
                <p>product_code, quantity_on_hand, snapshot_timestamp</p>
                <p className="text-gray-400 mt-0.5">Optional: batch_number, expiry_date</p>
              </div>
            </div>
          </div>

          {/* Upload result */}
          {uploadResult && (
            <div className={`card p-4 border ${uploadResult.status === 'completed' ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
              <p className={`font-semibold ${uploadResult.status === 'completed' ? 'text-green-700' : 'text-red-700'}`}>
                {uploadResult.status === 'completed' ? 'Import completed' : 'Import failed'}
              </p>
              {uploadResult.status === 'completed' && (
                <div className="flex gap-4 mt-2 text-sm">
                  <span className="text-green-600">{uploadResult.processed} processed</span>
                  <span className="text-red-600">{uploadResult.rejected} rejected</span>
                  <span className="text-gray-500">{uploadResult.deduplicated} duplicates skipped</span>
                </div>
              )}
              {uploadResult.error && <p className="text-sm text-red-600 mt-1">{uploadResult.error}</p>}
              {uploadResult.errors?.length > 0 && (
                <div className="mt-2 text-xs text-red-600 max-h-32 overflow-y-auto">
                  {uploadResult.errors.map((e, i) => <p key={i}>Row {e.row}: {e.error}</p>)}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Import History Tab */}
      {tab === 'status' && (
        <div className="card overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-100">
            <thead className="bg-gray-50">
              <tr>
                {['ID', 'Source', 'Type', 'File', 'Status', 'Total', 'OK', 'Rejected', 'Dedup', 'Time'].map(h => (
                  <th key={h} className="table-th">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {importLogs.map(log => (
                <tr key={log.id} className="hover:bg-gray-50 cursor-pointer" onClick={() => log.records_rejected > 0 && loadQuarantined(log.id)}>
                  <td className="table-td text-xs text-gray-400">#{log.id}</td>
                  <td className="table-td text-xs">{log.source}</td>
                  <td className="table-td"><span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">{log.import_type}</span></td>
                  <td className="table-td text-xs font-mono">{log.source_filename || '—'}</td>
                  <td className="table-td">
                    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                      log.status === 'completed' ? 'bg-green-100 text-green-700' :
                      log.status === 'failed' ? 'bg-red-100 text-red-700' :
                      'bg-yellow-100 text-yellow-700'
                    }`}>{log.status}</span>
                  </td>
                  <td className="table-td">{log.total_records}</td>
                  <td className="table-td text-green-600">{log.processed}</td>
                  <td className="table-td text-red-600">{log.rejected > 0 ? log.rejected : ''}</td>
                  <td className="table-td text-gray-400">{log.deduplicated > 0 ? log.deduplicated : ''}</td>
                  <td className="table-td text-xs">{log.started_at?.slice(0, 16)}</td>
                </tr>
              ))}
              {!importLogs.length && <tr><td colSpan={10} className="table-td text-center py-8 text-gray-400">No imports yet — upload a CSV to get started</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* Reconciliation Tab */}
      {tab === 'reconciliation' && reconciliation && (
        <div className="space-y-4">
          <div className="card p-4 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">Tolerance: ±{reconciliation.tolerance_pct}% • Checked: {reconciliation.total_checked} SKUs</p>
              <p className="text-lg font-bold text-gray-800">
                {reconciliation.matches} matches, <span className={reconciliation.discrepancies_count > 0 ? 'text-red-600' : 'text-green-600'}>{reconciliation.discrepancies_count} discrepancies</span>
              </p>
            </div>
          </div>

          {reconciliation.discrepancies_count > 0 ? (
            <div className="card overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-100">
                <thead className="bg-gray-50">
                  <tr>
                    {['Medicine', 'System On-Hand', 'Source On-Hand', 'Difference', '% Diff', 'Snapshot Time'].map(h => (
                      <th key={h} className="table-th">{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-50">
                  {reconciliation.discrepancies.map(d => (
                    <tr key={d.medicine_id} className="hover:bg-red-50">
                      <td className="table-td font-medium">{d.medicine_name}</td>
                      <td className="table-td font-semibold">{d.system_on_hand}</td>
                      <td className="table-td">{d.source_on_hand}</td>
                      <td className="table-td">
                        <span className={`font-bold ${d.difference > 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {d.difference > 0 ? '+' : ''}{d.difference}
                        </span>
                      </td>
                      <td className="table-td text-red-600 font-semibold">{d.difference_pct}%</td>
                      <td className="table-td text-xs">{d.snapshot_timestamp?.slice(0, 16)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : reconciliation.status === 'no_snapshots' ? (
            <div className="card p-8 text-center text-gray-400">No stock snapshots available — import one to run reconciliation</div>
          ) : (
            <div className="card p-8 text-center text-green-600 font-medium">All SKUs within tolerance — no discrepancies found</div>
          )}
        </div>
      )}

      {tab === 'reconciliation' && !reconciliation && (
        <div className="card p-8 text-center text-gray-400">Click "Run Reconciliation" to compare system stock against source snapshots</div>
      )}

      {/* Quarantined Tab */}
      {tab === 'quarantined' && (
        <div className="card overflow-x-auto">
          {!quarantined.length ? (
            <p className="p-8 text-center text-gray-400">No quarantined records {importLogs.some(l => l.records_rejected > 0) ? '— click a rejected import above to view' : ''}</p>
          ) : (
            <table className="min-w-full divide-y divide-gray-100">
              <thead className="bg-gray-50">
                <tr>
                  {['Import #', 'Row', 'Reason', 'Raw Data'].map(h => (
                    <th key={h} className="table-th">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {quarantined.map(q => (
                  <tr key={q.id} className="hover:bg-gray-50">
                    <td className="table-td text-xs">#{q.import_log_id}</td>
                    <td className="table-td">{q.row_number || '—'}</td>
                    <td className="table-td text-sm text-red-600">{q.rejection_reason}</td>
                    <td className="table-td text-xs font-mono max-w-xs truncate">{q.raw_data}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
