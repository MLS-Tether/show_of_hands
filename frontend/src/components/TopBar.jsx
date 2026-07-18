import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import api from '../api'
import NotificationBell from './NotificationBell'
import { getUserId, isAdmin, isTeacher } from '../utils/auth'
import { getAdminParentPath, getParentPath } from '../utils/escNavigation'
import { getTheme, setTheme } from '../utils/theme'
import { useAutoRefresh } from '../utils/autoRefresh'
import './TopBar.css'

const BREADCRUMB_RULES = [
  { pattern: /^\/admin\/overview$/, label: 'Overview' },
  { pattern: /^\/admin\/inbox$/, label: 'Approvals · Inbox' },
  { pattern: /^\/admin\/sections$/, label: 'Manage · Sections' },
  { pattern: /^\/admin\/users\/[^/]+$/, label: 'Manage · Users · Student' },
  { pattern: /^\/admin\/users$/, label: 'Manage · Users' },
  { pattern: /^\/admin\/settings$/, label: 'School · Settings' },
  { pattern: /^\/admin\/profile$/, label: 'My profile' },
  { pattern: /^\/dashboard$/, label: 'Dashboard' },
  { pattern: /^\/sections$/, label: 'My sections' },
  { pattern: /^\/sections\/[^/]+$/, label: 'Section detail' },
  { pattern: /^\/assignments$/, label: 'Assignments' },
  { pattern: /^\/assignments\/[^/]+$/, label: 'Assignment detail' },
  { pattern: /^\/quests$/, label: 'Quests' },
  { pattern: /^\/bulletin-board$/, label: 'Bulletin board' },
  { pattern: /^\/study-rooms$/, label: 'Study rooms' },
  { pattern: /^\/rooms\/[^/]+$/, label: 'Study room' },
  { pattern: /^\/points$/, label: 'Points' },
  { pattern: /^\/profile$/, label: 'My profile' },
]

function getBreadcrumb(pathname) {
  const match = BREADCRUMB_RULES.find((r) => r.pattern.test(pathname))
  return match ? match.label : 'Show of Hands'
}

function TopBar() {
  const location = useLocation()
  const admin = isAdmin()
  const [points, setPoints] = useState(null)
  const [theme, setThemeState] = useState(getTheme())
  const breadcrumb = getBreadcrumb(location.pathname)
  const parentPath = admin
    ? getAdminParentPath(location.pathname)
    : getParentPath(location.pathname, { isTeacher: isTeacher() })

  const loadPoints = useCallback(() => {
    let cancelled = false
    const request = admin ? api.get('/schools/points') : api.get(`/users/${getUserId()}/points`)

    request
      .then(({ data }) => {
        if (!cancelled) setPoints(data.total_points)
      })
      .catch(() => {
        if (!cancelled) setPoints((prev) => prev ?? null)
      })

    return () => {
      cancelled = true
    }
  }, [admin])

  useEffect(() => loadPoints(), [loadPoints])
  useAutoRefresh(loadPoints)

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setThemeState(next)
  }

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-breadcrumb">
        {breadcrumb}
        {parentPath && <span className="admin-topbar-esc-hint">Press ESC to go back</span>}
      </div>
      <div className="admin-topbar-actions">
        {points !== null && (
          <span className="admin-topbar-points">
            {points.toLocaleString()} {admin ? 'school pts' : 'pts'}
          </span>
        )}
        <NotificationBell />
        <button type="button" className="admin-topbar-theme" onClick={toggleTheme}>
          {theme === 'dark' ? 'Dark' : 'Light'}
        </button>
      </div>
    </header>
  )
}

export default TopBar
