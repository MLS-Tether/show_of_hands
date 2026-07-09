import { apiClient } from '../lib/apiClient'

export function login({ username, password }) {
  return apiClient.post('/auth/login', { username, password }).then((res) => res.data)
}

export function register({ username, password, schoolCode, role, email }) {
  return apiClient
    .post('/auth/register', {
      username,
      password,
      school_code: schoolCode,
      role,
      email: email || undefined,
    })
    .then((res) => res.data)
}

export function logout(refreshToken) {
  return apiClient.post('/auth/logout', { refresh_token: refreshToken }).then((res) => res.data)
}
