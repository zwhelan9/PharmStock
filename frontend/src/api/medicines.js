import client from './client'

export const medicinesApi = {
  list: (params = {}) => client.get('/medicines/', { params }).then(r => r.data),
  get: (id) => client.get(`/medicines/${id}`).then(r => r.data),
  create: (data) => client.post('/medicines/', data).then(r => r.data),
  update: (id, data) => client.patch(`/medicines/${id}`, data).then(r => r.data),
  delete: (id) => client.delete(`/medicines/${id}`),
  categories: () => client.get('/medicines/categories/list').then(r => r.data),
}
