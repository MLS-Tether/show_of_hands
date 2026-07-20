import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import NotificationBell from './NotificationBell'
import { usePoints, useSchoolPoints } from '../queries'
import { getUserId, isAdmin, isTeacher } from '../utils/auth'
import { getAdminParentPath, getParentPath } from '../utils/escNavigation'
import { getTheme, setTheme } from '../utils/theme'
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

function TopBar({ sidebarHidden, onToggleSidebar }) {
  const location = useLocation()
  const admin = isAdmin()
  const teacher = isTeacher()
  const [theme, setThemeState] = useState(getTheme())
  const breadcrumb = getBreadcrumb(location.pathname)
  const parentPath = admin
    ? getAdminParentPath(location.pathname)
    : getParentPath(location.pathname, { isTeacher: isTeacher() })

  // Teachers don't earn points, so they get no counter and no fetches
  const { data: schoolPoints } = useSchoolPoints({ enabled: admin && !teacher })
  const { data: userPoints } = usePoints(getUserId(), 1, 20, { enabled: !admin && !teacher })
  const points = teacher ? null : admin ? schoolPoints?.total_points ?? null : userPoints?.total_points ?? null

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setThemeState(next)
  }

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-left">
        <button
          type="button"
          className="admin-topbar-sidebar-toggle"
          onClick={onToggleSidebar}
          aria-pressed={!sidebarHidden}
          aria-label={sidebarHidden ? 'Show sidebar' : 'Hide sidebar'}
          title={sidebarHidden ? 'Show sidebar' : 'Hide sidebar'}
        >
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
            <rect
              x="1.5"
              y="2.5"
              width="13"
              height="11"
              rx="1.5"
              stroke="currentColor"
              strokeWidth="1.2"
            />
            <path d="M6 2.5v11" stroke="currentColor" strokeWidth="1.2" />
            {!sidebarHidden && <rect x="2.6" y="3.6" width="2.5" height="8.8" fill="currentColor" />}
          </svg>
        </button>
        <div className="admin-topbar-breadcrumb">
          {breadcrumb}
          {parentPath && <span className="admin-topbar-esc-hint">Press ESC to go back</span>}
        </div>
      </div>
      <div className="admin-topbar-actions">
        {!teacher && points !== null && (
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
