const ACCESS_TOKEN_KEY = 'sof_access_token'
const REFRESH_TOKEN_KEY = 'sof_refresh_token'
const USER_KEY = 'sof_user'

export function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

export function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

export function getStoredUser() {
  const raw = localStorage.getItem(USER_KEY)
  return raw ? JSON.parse(raw) : null
}

export function setSession({ accessToken, refreshToken, user }) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
  if (refreshToken) localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function setAccessToken(accessToken) {
  localStorage.setItem(ACCESS_TOKEN_KEY, accessToken)
}

export function clearSession() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}
