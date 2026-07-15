import { useCallback, useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import ToastStack from './ToastStack'
import api from '../api'
import { broadcastRefresh, useAutoRefresh } from '../utils/autoRefresh'
import { playNotificationChime } from '../utils/notificationSound'
import { wsUrlWithFreshToken } from '../utils/ws'
import './NotificationBell.css'

// Real-time push does the heavy lifting now (a Postgres trigger fires on
// every notification insert, relayed over this WebSocket) — this is just a
// rare safety net in case the socket was disconnected and missed something.
const FALLBACK_POLL_INTERVAL_MS = 180000
const TOAST_DURATION_MS = 6000
const RECONNECT_DELAY_MS = 3000

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
  const seenIdsRef = useRef(new Set())
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)

  const dismissToast = useCallback((toastId) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId))
  }, [])

  // Handles a notification arriving from either the live WebSocket push or
  // the fallback poll catching something the socket missed — same treatment
  // either way: surface a toast + chime and tell every open page to refresh.
  const showIncoming = useCallback(
    (notification) => {
      if (seenIdsRef.current.has(notification.notification_id)) return
      seenIdsRef.current.add(notification.notification_id)

      setNotifications((prev) => [notification, ...(prev || [])])
      broadcastRefresh()
      playNotificationChime()
      setToasts((prev) => [...prev, { id: notification.notification_id, message: notification.message }])
      setTimeout(() => dismissToast(notification.notification_id), TOAST_DURATION_MS)
    },
    [dismissToast]
  )

  const hasLoadedRef = useRef(false)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get('/notifications')
      .then(({ data }) => {
        if (cancelled) return
        const isFirstLoad = !hasLoadedRef.current
        hasLoadedRef.current = true
        data.forEach((n) => seenIdsRef.current.add(n.notification_id))

        if (isFirstLoad) {
          setNotifications(data)
          return
        }

        // Merge rather than replace: a WS push may have already added a
        // notification locally that this fallback fetch also just returned.
        setNotifications((prev) => {
          const existingIds = new Set((prev || []).map((n) => n.notification_id))
          const missed = data.filter((n) => !existingIds.has(n.notification_id))
          if (missed.length === 0) return prev
          return [...missed, ...(prev || [])]
        })
      })
      .catch(() => {
        if (!cancelled) setNotifications((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load, FALLBACK_POLL_INTERVAL_MS)

  useEffect(() => {
    let unmounted = false

    async function connect() {
      const url = await wsUrlWithFreshToken('/notifications/stream')
      if (unmounted) return
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'new_notification') {
          showIncoming(data.notification)
        }
      }

      ws.onclose = () => {
        if (unmounted) return
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    connect()

    return () => {
      unmounted = true
      clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [showIncoming])

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
