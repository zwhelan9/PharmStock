import client from './client'

export const cdRegisterApi = {
  createEntry: (data) => client.post('/cd-register/entries', data).then(r => r.data),
  listEntries: (params = {}) => client.get('/cd-register/entries', { params }).then(r => r.data),
  getEntry: (id) => client.get(`/cd-register/entries/${id}`).then(r => r.data),
  getHistory: (id) => client.get(`/cd-register/entries/${id}/history`).then(r => r.data),
  correctEntry: (id, data) => client.post(`/cd-register/entries/${id}/correct`, data).then(r => r.data),
  getBalance: (medicineId) => client.get(`/cd-register/balance/${medicineId}`).then(r => r.data),
  exportCsv: (params = {}) => client.get('/cd-register/export', { params, responseType: 'blob' }).then(r => r.data),
}

export const dutyRegisterApi = {
  create: (data) => client.post('/duty-register/', data).then(r => r.data),
  list: (params = {}) => client.get('/duty-register/', { params }).then(r => r.data),
  correct: (id, data) => client.post(`/duty-register/${id}/correct`, data).then(r => r.data),
}

export const cdDestructionApi = {
  create: (data) => client.post('/cd-destruction/', data).then(r => r.data),
  list: (params = {}) => client.get('/cd-destruction/', { params }).then(r => r.data),
  get: (id) => client.get(`/cd-destruction/${id}`).then(r => r.data),
}

export const cdAnomaliesApi = {
  get: (lookbackDays = 30) => client.get('/cd-anomalies/', { params: { lookback_days: lookbackDays } }).then(r => r.data),
}
