import api from '../api'

export function wsBaseUrl() {
  return api.defaults.baseURL.replace(/^http/, 'ws')
}

export function authToken() {
  return localStorage.getItem('access_token')
}
