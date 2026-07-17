import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import api from '../api'
import NotificationBell from './NotificationBell'
import { useAutoRefresh } from '../utils/autoRefresh'
import { getParentPath } from '../utils/escNavigation'
import { isTeacher } from '../utils/auth'
import './TopBar.css'

function TopBar() {
  const location = useLocation()
  const [points, setPoints] = useState(null)

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

  return (
    <header className="topbar">
      <div className="topbar-logo">
        Show of Hands
        {parentPath && <span className="topbar-esc-hint">Press ESC to go back</span>}
      </div>
      <div className="topbar-actions">
        <NotificationBell />
        <span className="topbar-points">{points === null ? '—' : points} pts</span>
      </div>
    </header>
  )
}

export default TopBar
