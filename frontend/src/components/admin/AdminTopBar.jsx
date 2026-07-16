import { useLocation } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import api from '../../api'
import NotificationBell from '../NotificationBell'
import { getTheme, setTheme } from '../../utils/theme'
import { useAutoRefresh } from '../../utils/autoRefresh'
import './AdminTopBar.css'

const BREADCRUMBS = {
  '/admin/overview': 'Overview',
  '/admin/inbox': 'Approvals · Inbox',
  '/admin/sections': 'Manage · Sections',
  '/admin/users': 'Manage · Users',
  '/admin/settings': 'School · Settings',
  '/admin/profile': 'My profile',
}

function AdminTopBar() {
  const location = useLocation()
  const [theme, setThemeState] = useState(getTheme())
  const [points, setPoints] = useState(null)
  const breadcrumb = BREADCRUMBS[location.pathname] || 'Admin'

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setThemeState(next)
  }

  const loadPoints = useCallback(() => {
    let cancelled = false
    api
      .get('/schools/points')
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

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-breadcrumb">{breadcrumb}</div>
      <div className="admin-topbar-actions">
        {points !== null && (
          <span className="admin-topbar-points">{points.toLocaleString()} school pts</span>
        )}
        <NotificationBell />
        <button type="button" className="admin-topbar-theme" onClick={toggleTheme}>
          {theme === 'dark' ? 'Dark' : 'Light'}
        </button>
      </div>
    </header>
  )
}

export default AdminTopBar
