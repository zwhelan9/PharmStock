import client from './client'

export const stockApi = {
  levels: (params = {}) => client.get('/stock/levels', { params }).then(r => r.data),
  logs: (params = {}) => client.get('/stock/logs', { params }).then(r => r.data),
  summary: () => client.get('/stock/summary').then(r => r.data),
}
