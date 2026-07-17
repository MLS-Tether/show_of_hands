import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api from '../api'
import NotificationBell from './NotificationBell'
import { useAutoRefresh } from '../utils/autoRefresh'
import { getParentPath } from '../utils/escNavigation'
import { isTeacher } from '../utils/auth'
import './TopBar.css'

function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [points, setPoints] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  const parentPath = getParentPath(location.pathname, { isTeacher: isTeacher() })

  const loadPoints = useCallback(() => {
    const userId = localStorage.getItem('user_id')
    if (!userId) return undefined
    let cancelled = false

    api
      .get(`/users/${userId}/points`)
      .then(({ data }) => {
        if (!cancelled) setPoints(data.total_points)
      })
      .catch(() => {
        if (!cancelled) setPoints((prev) => prev ?? null)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => loadPoints(), [loadPoints])
  useAutoRefresh(loadPoints)

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  async function handleLogout() {
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

  return (
    <header className="topbar">
      <div className="topbar-logo">
        Show of Hands
        {parentPath && <span className="topbar-esc-hint">Press ESC to go back</span>}
      </div>
      <div className="topbar-actions">
        <NotificationBell />
        <span className="topbar-points">{points === null ? '—' : points} pts</span>
        <div className="topbar-account" ref={menuRef}>
          <button
            type="button"
            className="topbar-avatar"
            aria-label="Account menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          />
          {menuOpen && (
            <div className="topbar-menu" role="menu">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  navigate('/profile')
                }}
              >
                My profile
              </button>
              <button type="button" role="menuitem" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default TopBar
