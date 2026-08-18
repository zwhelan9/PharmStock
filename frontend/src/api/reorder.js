import client from './client'

export const reorderApi = {
  recommendations: (horizonDays = 14, safetyDays = 7) =>
    client.get('/reorder/recommendations', { params: { horizon_days: horizonDays, safety_days: safetyDays } }).then(r => r.data),
  bySupplier: (horizonDays = 14, safetyDays = 7) =>
    client.get('/reorder/by-supplier', { params: { horizon_days: horizonDays, safety_days: safetyDays } }).then(r => r.data),
  exportCsv: (horizonDays = 14, safetyDays = 7) =>
    client.get('/reorder/export', { params: { horizon_days: horizonDays, safety_days: safetyDays }, responseType: 'blob' }).then(r => r.data),
}

export const riskApi = {
  deadStock: (daysThreshold = 60) =>
    client.get('/risk/dead-stock', { params: { days_threshold: daysThreshold } }).then(r => r.data),
  anomalies: (lookbackDays = 7, thresholdPct = 50) =>
    client.get('/risk/anomalies', { params: { lookback_days: lookbackDays, threshold_pct: thresholdPct } }).then(r => r.data),
  stockValue: () =>
    client.get('/risk/stock-value').then(r => r.data),
}
