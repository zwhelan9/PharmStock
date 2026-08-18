import client from './client'

export const predictionsApi = {
  forecast: (medicineId, horizon = 30) =>
    client.get(`/predictions/forecast/${medicineId}`, { params: { horizon }, timeout: 60000 }).then(r => r.data),
  forecastAll: (horizon = 30) =>
    client.get('/predictions/forecast/all/summary', { params: { horizon }, timeout: 120000 }).then(r => r.data),
  reorderList: (horizon = 30) =>
    client.get('/predictions/reorder-list', { params: { horizon }, timeout: 120000 }).then(r => r.data),
  history: (medicineId, horizon = 30) =>
    client.get(`/predictions/history/${medicineId}`, { params: { horizon } }).then(r => r.data),
}
