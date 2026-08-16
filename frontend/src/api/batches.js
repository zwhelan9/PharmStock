import client from './client'

export const batchesApi = {
  list: (params = {}) => client.get('/batches/', { params }).then(r => r.data),
  get: (id) => client.get(`/batches/${id}`).then(r => r.data),
  create: (data) => client.post('/batches/', data).then(r => r.data),
  update: (id, data) => client.patch(`/batches/${id}`, data).then(r => r.data),
  fefo: (medicineId) => client.get(`/batches/medicine/${medicineId}/fefo`).then(r => r.data),
}
