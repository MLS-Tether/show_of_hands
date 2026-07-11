import { useCallback, useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import ToastStack from './ToastStack'
import api from '../api'
import { broadcastRefresh, useAutoRefresh } from '../utils/autoRefresh'
import { playNotificationChime } from '../utils/notificationSound'
import './NotificationBell.css'

const POLL_INTERVAL_MS = 8000
const TOAST_DURATION_MS = 6000

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
  const [toasts, setToasts] = useState([])
  const menuRef = useRef(null)
  const seenIdsRef = useRef(null)

  const dismissToast = useCallback((toastId) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId))
  }, [])

  const load = useCallback(() => {
    let cancelled = false
    api
      .get('/notifications')
      .then(({ data }) => {
        if (cancelled) return
        const isFirstLoad = seenIdsRef.current === null
        const newOnes = isFirstLoad ? [] : data.filter((n) => !seenIdsRef.current.has(n.notification_id))
        seenIdsRef.current = new Set(data.map((n) => n.notification_id))
        setNotifications(data)

        if (newOnes.length > 0) {
          // A new notification means something changed elsewhere (a request
          // accepted, an assignment graded, etc.) — reload every open page's
          // data instead of leaving the user to notice the badge and refresh,
          // and surface it immediately as a toast + chime rather than making
          // the student notice the badge on their own.
          broadcastRefresh()
          playNotificationChime()
          const newToasts = newOnes.map((n) => ({ id: n.notification_id, message: n.message }))
          setToasts((prev) => [...prev, ...newToasts])
          newToasts.forEach((t) => {
            setTimeout(() => dismissToast(t.id), TOAST_DURATION_MS)
          })
        }
      })
      .catch(() => {
        if (!cancelled) setNotifications((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [dismissToast])

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

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}

export default NotificationBell
