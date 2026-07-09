import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import * as authApi from '../api/auth'
import { getAccessToken, getRefreshToken, getStoredUser, setSession, clearSession } from './tokenStorage'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => (getAccessToken() ? getStoredUser() : null))

  useEffect(() => {
    function handleSessionExpired() {
      setUser(null)
    }
    window.addEventListener('sof:session-expired', handleSessionExpired)
    return () => window.removeEventListener('sof:session-expired', handleSessionExpired)
  }, [])

  async function login(username, password) {
    const data = await authApi.login({ username, password })
    const loggedInUser = { user_id: data.user_id, role: data.role }
    setSession({ accessToken: data.access_token, refreshToken: data.refresh_token, user: loggedInUser })
    setUser(loggedInUser)
    return loggedInUser
  }

  async function register(payload) {
    return authApi.register(payload)
  }

  async function logout() {
    const refreshToken = getRefreshToken()
    try {
      if (refreshToken) await authApi.logout(refreshToken)
    } catch {
      // best-effort — still clear the local session even if the server call fails
    }
    clearSession()
    setUser(null)
  }

  const value = useMemo(
    () => ({ user, isAuthenticated: Boolean(user), login, register, logout }),
    [user]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
