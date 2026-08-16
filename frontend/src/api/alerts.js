import client from './client'

export const alertsApi = {
  all: () => client.get('/alerts/').then(r => r.data),
}
