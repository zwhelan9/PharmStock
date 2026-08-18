import client from './client'

export const authApi = {
  login: (username, password) => {
    const form = new URLSearchParams()
    form.append('username', username)
    form.append('password', password)
    return client.post('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    }).then(r => r.data)
  },
  me: () => client.get('/auth/me').then(r => r.data),
  updateMe: (data) => client.patch('/auth/me', data).then(r => r.data),

  // Admin only
  listUsers: () => client.get('/auth/users').then(r => r.data),
  createUser: (data) => client.post('/auth/users', data).then(r => r.data),
  updateUser: (id, data) => client.patch(`/auth/users/${id}`, data).then(r => r.data),
  deleteUser: (id) => client.delete(`/auth/users/${id}`),
}
