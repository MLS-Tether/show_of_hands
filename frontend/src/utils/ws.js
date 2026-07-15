import api, { getValidAccessToken } from '../api'

export function wsBaseUrl() {
  return api.defaults.baseURL.replace(/^http/, 'ws')
}

// Refreshes first if the stored access token is expired/expiring — a
// WebSocket has no retry-after-401 path the way REST calls do, so connecting
// with a stale token just fails outright with no self-heal.
export async function wsUrlWithFreshToken(path) {
  const token = await getValidAccessToken()
  return `${wsBaseUrl()}${path}?token=${encodeURIComponent(token)}`
}
