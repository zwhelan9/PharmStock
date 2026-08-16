import client from './client'

export const salesApi = {
  list: (params = {}) => client.get('/sales/', { params }).then(r => r.data),
  get: (id) => client.get(`/sales/${id}`).then(r => r.data),
  create: (data) => client.post('/sales/', data).then(r => r.data),
  dailySummary: (days = 30, medicineId = null) =>
    client.get('/sales/summary/daily', { params: { days, medicine_id: medicineId } }).then(r => r.data),
  byMedicine: (days = 30) =>
    client.get('/sales/summary/by-medicine', { params: { days } }).then(r => r.data),
}
