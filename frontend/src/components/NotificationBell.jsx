import { useEffect, useRef, useState } from 'react'
import api from '../api'
import './NotificationBell.css'

function formatTimestamp(dateStr) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(dateStr))
}

function NotificationBell() {
  const [notifications, setNotifications] = useState(null)
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    api
      .get('/notifications')
      .then(({ data }) => {
        if (!cancelled) setNotifications(data)
      })
      .catch(() => {
        if (!cancelled) setNotifications([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!open) return
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  const loading = notifications === null
  const unreadCount = (notifications || []).filter((n) => !n.is_read).length

  async function markRead(notificationId) {
    setNotifications((prev) =>
      prev.map((n) => (n.notification_id === notificationId ? { ...n, is_read: true } : n))
    )
    try {
      await api.patch(`/notifications/${notificationId}/read`)
    } catch {
      // best-effort; a stale read-state will resync next time the list is fetched
    }
  }

  async function markAllRead() {
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })))
    try {
      await api.patch('/notifications/read-all')
    } catch {
      // best-effort
    }
  }

  return (
    <div className="notification-bell" ref={menuRef}>
      <button
        type="button"
        className="notification-trigger"
        aria-label="Notifications"
        aria-expanded={open}
        onClick={() => setOpen((o) => !o)}
      >
        <span aria-hidden="true">🔔</span>
        {unreadCount > 0 && <span className="notification-badge">{unreadCount}</span>}
      </button>

      {open && (
        <div className="notification-panel" role="menu">
          <div className="notification-panel-header">
            <span>Notifications</span>
            {unreadCount > 0 && (
              <button type="button" className="notification-mark-all" onClick={markAllRead}>
                Mark all as read
              </button>
            )}
          </div>
          <div className="notification-list">
            {loading && <div className="notification-empty">Loading…</div>}
            {!loading && notifications.length === 0 && (
              <div className="notification-empty">No notifications</div>
            )}
            {!loading &&
              notifications.map((n) => (
                <button
                  type="button"
                  key={n.notification_id}
                  className={`notification-row${n.is_read ? '' : ' unread'}`}
                  onClick={() => markRead(n.notification_id)}
                >
                  <span className="notification-message">{n.message}</span>
                  <span className="notification-time">{formatTimestamp(n.created_at)}</span>
                </button>
              ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default NotificationBell
