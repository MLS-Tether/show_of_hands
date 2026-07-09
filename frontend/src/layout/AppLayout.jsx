import { useEffect, useState } from 'react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { getUserPoints } from '../api/points'
import './AppLayout.css'

const NAV_ITEMS = [
  { label: 'Dashboard', enabled: false },
  { label: 'My Sections', to: '/sections', enabled: true },
  { label: 'Assignments', enabled: false },
  { label: 'Quests', enabled: false },
  { label: 'Bulletin Board', to: '/sections', enabled: true, hint: 'pick a section' },
  { label: 'Study Rooms', enabled: false, hint: 'open via a bulletin board request' },
]

export default function AppLayout() {
  const { user, logout } = useAuth()
  const [points, setPoints] = useState(null)

  useEffect(() => {
    if (!user) return
    getUserPoints(user.user_id)
      .then((data) => setPoints(data.total_points))
      .catch(() => setPoints(null))
  }, [user])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="sidebar-brand">Tether</div>
        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) =>
            item.enabled ? (
              <NavLink key={item.label} to={item.to} className="sidebar-link">
                {item.label}
              </NavLink>
            ) : (
              <span key={item.label} className="sidebar-link sidebar-link--disabled" title={item.hint || 'Coming soon'}>
                {item.label}
                <small>{item.hint || 'soon'}</small>
              </span>
            )
          )}
        </nav>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div className="topbar-title">Show of Hands</div>
          <div className="topbar-actions">
            {points !== null && <span className="points-badge">{points} pts</span>}
            <span className="username">{user?.role}</span>
            <button className="btn btn-ghost" onClick={logout}>
              Log out
            </button>
          </div>
        </header>
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
