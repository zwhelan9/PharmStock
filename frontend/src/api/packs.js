import client from './client'

export const packsApi = {
  list: (params = {}) => client.get('/packs/', { params }).then(r => r.data),
  get: (id) => client.get(`/packs/${id}`).then(r => r.data),
  create: (data) => client.post('/packs/', data).then(r => r.data),
  update: (id, data) => client.patch(`/packs/${id}`, data).then(r => r.data),
  onHand: (medicineId) => client.get(`/packs/medicine/${medicineId}/on-hand`).then(r => r.data),
  expiryAlerts: () => client.get('/packs/expiry-alerts').then(r => r.data),
}

export const dispenseApi = {
  create: (data) => client.post('/dispense/', data).then(r => r.data),
  list: (params = {}) => client.get('/dispense/', { params }).then(r => r.data),
  get: (id) => client.get(`/dispense/${id}`).then(r => r.data),
}

export const writeoffsApi = {
  create: (data) => client.post('/writeoffs/', data).then(r => r.data),
  list: (params = {}) => client.get('/writeoffs/', { params }).then(r => r.data),
  get: (id) => client.get(`/writeoffs/${id}`).then(r => r.data),
  countersign: (id) => client.post(`/writeoffs/${id}/countersign`).then(r => r.data),
  pendingCountersign: () => client.get('/writeoffs/pending-countersign').then(r => r.data),
  report: (startDate, endDate) => client.get('/writeoffs/report', { params: { start_date: startDate, end_date: endDate } }).then(r => r.data),
}
