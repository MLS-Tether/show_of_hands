import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api',
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

function clearSessionAndRedirect() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_id')
  localStorage.removeItem('role')
  window.location.assign('/auth')
}

let refreshPromise = null

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error

    if (response?.status !== 401 || config._retried || config.url === '/auth/refresh') {
      if (response?.status === 401) clearSessionAndRedirect()
      return Promise.reject(error)
    }

    const refreshToken = localStorage.getItem('refresh_token')
    if (!refreshToken) {
      clearSessionAndRedirect()
      return Promise.reject(error)
    }

    try {
      if (!refreshPromise) {
        refreshPromise = api
          .post('/auth/refresh', { refresh_token: refreshToken })
          .finally(() => {
            refreshPromise = null
          })
      }
      const { data } = await refreshPromise
      localStorage.setItem('access_token', data.access_token)
      config._retried = true
      return api(config)
    } catch {
      clearSessionAndRedirect()
      return Promise.reject(error)
    }
  }
)

export default api
