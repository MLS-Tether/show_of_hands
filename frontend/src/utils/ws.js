import api, { getValidAccessToken } from '../api'

export function wsBaseUrl() {
  return api.defaults.baseURL.replace(/^http/, 'ws')
}

// Refreshes first if the stored access token is expired/expiring — a
// WebSocket has no retry-after-401 path the way REST calls do, so connecting
// with a stale token just fails outright with no self-heal.
//
// The token travels as a WebSocket subprotocol (the `protocols` arg to the
// WebSocket constructor) rather than a `?token=` query param — proxies/CDNs
// commonly log full request URLs by default, and query params also survive
// in browser history. Subprotocols are part of the handshake headers, not
// the URL, so the token doesn't end up in either place.
export async function wsConnectParams(path) {
  const token = await getValidAccessToken()
  return { url: `${wsBaseUrl()}${path}`, protocols: [token] }
}
