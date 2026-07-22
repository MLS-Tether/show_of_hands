import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api'

// Axios's default array serialization appends `[]` to the key
// (`section_ids[]=1&section_ids[]=2`), which FastAPI's `List[int] = Query(...)`
// doesn't parse — it expects the key repeated plain (`section_ids=1&section_ids=2`).
function serializeParams(params) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) {
      value.forEach((v) => searchParams.append(key, v))
    } else if (value !== undefined && value !== null) {
      searchParams.append(key, value)
    }
  })
  return searchParams.toString()
}

const api = axios.create({
  baseURL: BASE_URL,
  paramsSerializer: serializeParams,
})

// Profile pictures are stored in Supabase Storage and already come back as
// absolute URLs; older/relative paths fall back to the backend's own origin.
export function mediaUrl(path) {
  if (!path) return null
  if (/^https?:\/\//.test(path)) return path
  return `${BASE_URL.replace(/\/api\/?$/, '')}${path}`
}

function logout() {
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_id')
  localStorage.removeItem('role')
  window.location.assign('/auth')
}

// Dedupes concurrent refreshes into a single call instead of firing one per
// caller that notices the token is stale.
let refreshPromise = null

function refreshAccessToken() {
  const refreshToken = localStorage.getItem('refresh_token')
  if (!refreshToken) return Promise.reject(new Error('No refresh token.'))

  if (!refreshPromise) {
    // Plain axios, not the `api` instance — avoids re-entering these same
    // interceptors for the refresh call itself.
    refreshPromise = axios
      .post(`${BASE_URL}/auth/refresh`, { refresh_token: refreshToken })
      .then(({ data }) => {
        localStorage.setItem('access_token', data.access_token)
        // The refresh token rotates on every use — the server invalidates
        // the one we just presented, so we must persist the new one or the
        // next refresh attempt fails as a reuse.
        localStorage.setItem('refresh_token', data.refresh_token)
        return data.access_token
      })
      .finally(() => {
        refreshPromise = null
      })
  }
  return refreshPromise
}

function decodeJwtExpiryMs(token) {
  try {
    const payloadB64 = token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')
    const padded = payloadB64 + '='.repeat((4 - (payloadB64.length % 4)) % 4)
    const { exp } = JSON.parse(atob(padded))
    return exp ? exp * 1000 : null
  } catch {
    return null
  }
}

const EXPIRY_SKEW_MS = 10000

// Returns a token that's valid for at least a few more seconds, refreshing
// first if the stored one is expired or about to be — used both by the
// request interceptor below and by anything opening a WebSocket, since a
// long-idle tab's access token can go stale with no HTTP request around to
// reactively trigger a refresh (a WS just fails outright, with no retry).
export async function getValidAccessToken() {
  const token = localStorage.getItem('access_token')
  if (!token) return null

  const expiryMs = decodeJwtExpiryMs(token)
  const isExpiringSoon = expiryMs === null || expiryMs - EXPIRY_SKEW_MS <= Date.now()
  if (!isExpiringSoon) return token

  try {
    return await refreshAccessToken()
  } catch {
    return token
  }
}

api.interceptors.request.use(async (config) => {
  const token = await getValidAccessToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config
    const isAuthEndpoint = originalRequest?.url?.startsWith('/auth/')

    if (error.response?.status === 401 && !originalRequest?._retried && !isAuthEndpoint) {
      originalRequest._retried = true
      try {
        const accessToken = await refreshAccessToken()
        originalRequest.headers.Authorization = `Bearer ${accessToken}`
        return api(originalRequest)
      } catch {
        logout()
        return Promise.reject(error)
      }
    }

    if (error.response?.status === 401) {
      logout()
    }
    return Promise.reject(error)
  }
)

export default api
