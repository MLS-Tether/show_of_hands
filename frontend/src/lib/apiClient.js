import axios from 'axios'
import { getAccessToken, getRefreshToken, setAccessToken, clearSession } from '../auth/tokenStorage'

const baseURL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api'

export const apiClient = axios.create({ baseURL })

apiClient.interceptors.request.use((config) => {
  const token = getAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let refreshPromise = null

function refreshAccessToken() {
  if (!refreshPromise) {
    const refreshToken = getRefreshToken()
    if (!refreshToken) {
      return Promise.reject(new Error('No refresh token available.'))
    }
    refreshPromise = axios
      .post(`${baseURL}/auth/refresh`, { refresh_token: refreshToken })
      .then((res) => {
        setAccessToken(res.data.access_token)
        return res.data.access_token
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const { config, response } = error
    const isAuthEndpoint = config?.url?.includes('/auth/login') || config?.url?.includes('/auth/refresh')

    if (response?.status === 401 && !config._retried && !isAuthEndpoint) {
      config._retried = true
      try {
        const newToken = await refreshAccessToken()
        config.headers.Authorization = `Bearer ${newToken}`
        return apiClient(config)
      } catch (refreshError) {
        clearSession()
        window.dispatchEvent(new Event('sof:session-expired'))
        return Promise.reject(refreshError)
      }
    }

    return Promise.reject(error)
  }
)

export function extractErrorMessage(error, fallback = 'Something went wrong.') {
  return error?.response?.data?.message || fallback
}
