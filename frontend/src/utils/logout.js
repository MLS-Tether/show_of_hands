import api from '../api'

export async function logout(navigate) {
  const refreshToken = localStorage.getItem('refresh_token')
  try {
    await api.post('/auth/logout', { refresh_token: refreshToken })
  } catch {
    // best-effort: still clear local session and redirect below
  }
  localStorage.removeItem('access_token')
  localStorage.removeItem('refresh_token')
  localStorage.removeItem('user_id')
  localStorage.removeItem('role')
  navigate('/auth')
}
