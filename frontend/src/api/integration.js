import client from './client'

export const integrationApi = {
  importDispenseEvents: (file) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/integration/import/dispense-events', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    }).then(r => r.data)
  },
  importStockSnapshot: (file) => {
    const form = new FormData()
    form.append('file', file)
    return client.post('/integration/import/stock-snapshot', form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    }).then(r => r.data)
  },
  syncStatus: () => client.get('/integration/sync-status').then(r => r.data),
  reconciliation: (tolerancePct = 2.0) =>
    client.get('/integration/reconciliation', { params: { tolerance_pct: tolerancePct } }).then(r => r.data),
  importLogs: (limit = 50) => client.get('/integration/import-logs', { params: { limit } }).then(r => r.data),
  quarantined: (importLogId) => {
    const params = importLogId ? { import_log_id: importLogId } : {}
    return client.get('/integration/quarantined', { params }).then(r => r.data)
  },
}
