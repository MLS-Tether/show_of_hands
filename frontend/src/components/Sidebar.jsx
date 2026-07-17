import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import api from '../api'
import { getUserId, isTeacher } from '../utils/auth'
import { useAutoRefresh } from '../utils/autoRefresh'
import { initials } from '../utils/format'
import './Sidebar.css'

const NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'My sections', to: '/sections' },
  { label: 'Assignments', to: '/assignments', studentOnly: true },
  { label: 'Quests', to: '/quests' },
  { label: 'Bulletin board', to: '/bulletin-board', studentOnly: true },
  { label: 'Study rooms', to: '/study-rooms', studentOnly: true },
  { label: 'Points', to: '/points', studentOnly: true },
]

function Sidebar() {
  const navigate = useNavigate()
  const teacher = isTeacher()
  const items = NAV_ITEMS.filter((item) => !item.studentOnly || !teacher)

  const [user, setUser] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get(`/users/${getUserId()}`)
      .then(({ data }) => {
        if (!cancelled) setUser(data)
      })
      .catch(() => {
        if (!cancelled) setUser((prev) => prev)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

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
    <nav className="sidebar" aria-label="Main">
      <div className="sidebar-nav">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
          >
            {item.label}
          </NavLink>
        ))}
      </div>

      {user && (
        <div className="sidebar-account" ref={menuRef}>
          {menuOpen && (
            <div className="sidebar-menu" role="menu">
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
          <button
            type="button"
            className="sidebar-footer"
            aria-label="Account menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <div className="sidebar-avatar">{initials(user.username)}</div>
            <div className="sidebar-footer-text">
              <div className="sidebar-footer-name">{user.username}</div>
              <div className="sidebar-footer-role">{user.role}</div>
            </div>
          </button>
        </div>
      )}
    </nav>
  )
}

export default Sidebar
