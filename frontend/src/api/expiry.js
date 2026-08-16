import client from './client'

export const expiryApi = {
  alerts: () => client.get('/expiry/alerts').then(r => r.data),
  logs: (params = {}) => client.get('/expiry/logs', { params }).then(r => r.data),
  createLog: (data) => client.post('/expiry/logs', data).then(r => r.data),
  calendar: (monthsAhead = 3) =>
    client.get('/expiry/calendar', { params: { months_ahead: monthsAhead } }).then(r => r.data),
}
