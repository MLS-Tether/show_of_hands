import { useCallback, useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import api from '../api'
import { broadcastRefresh, useAutoRefresh } from '../utils/autoRefresh'
import './NotificationBell.css'

const POLL_INTERVAL_MS = 8000

function formatTimestamp(dateStr) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(dateStr))
}

function typeLabel(type) {
  const words = type.split('_')
  return words[0][0].toUpperCase() + words[0].slice(1) + ' ' + words.slice(1).join(' ')
}

function NotificationBell() {
  const [notifications, setNotifications] = useState(null)
  const [open, setOpen] = useState(false)
  const [selectedNotification, setSelectedNotification] = useState(null)
  const menuRef = useRef(null)
  const seenIdsRef = useRef(null)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get('/notifications')
      .then(({ data }) => {
        if (cancelled) return
        const ids = new Set(data.map((n) => n.notification_id))
        const isFirstLoad = seenIdsRef.current === null
        const hasNew = !isFirstLoad && data.some((n) => !seenIdsRef.current.has(n.notification_id))
        seenIdsRef.current = ids
        setNotifications(data)
        // A new notification means something changed elsewhere (a request
        // accepted, an assignment graded, etc.) — reload every open page's
        // data instead of leaving the user to notice the badge and refresh.
        if (hasNew) broadcastRefresh()
      })
      .catch(() => {
        if (!cancelled) setNotifications((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load, POLL_INTERVAL_MS)

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

  function handleRowClick(notification) {
    if (!notification.is_read) markRead(notification.notification_id)
    setOpen(false)
    setSelectedNotification(notification)
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
                  onClick={() => handleRowClick(n)}
                >
                  <span className="notification-message">{n.message}</span>
                  <span className="notification-time">{formatTimestamp(n.created_at)}</span>
                </button>
              ))}
          </div>
        </div>
      )}

      {selectedNotification && (
        <Modal onClose={() => setSelectedNotification(null)}>
          <div className="notification-modal-type">{typeLabel(selectedNotification.type)}</div>
          <p className="notification-modal-message">{selectedNotification.message}</p>
          <div className="notification-modal-time">
            {formatTimestamp(selectedNotification.created_at)}
          </div>
        </Modal>
      )}
    </div>
  )
}

export default NotificationBell
