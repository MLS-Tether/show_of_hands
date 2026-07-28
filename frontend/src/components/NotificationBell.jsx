import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import ToastStack from './ToastStack'
import NotificationCountBadge from './NotificationCountBadge'
import api from '../api'
import { keys, useNotifications } from '../queries'
import { useRealtimeToasts } from '../realtime/realtimeContext'
import './NotificationBell.css'

function formatTimestamp(dateStr) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(dateStr))
}

// One route resolver per NotificationTypeEnum value. Each falls back to the
// closest list page when entity_id is null (legacy rows, or types with no
// per-entity id such as class_request_*).
const NOTIFICATION_ROUTES = {
  new_assignment: (n) => (n.entity_id != null ? `/assignments/${n.entity_id}` : '/assignments'),
  assignment_overdue: (n) => (n.entity_id != null ? `/assignments/${n.entity_id}` : '/assignments'),
  new_quest: () => '/quests',
  new_help_request: (n) => (n.entity_id != null ? `/sections/${n.entity_id}` : '/sections'),
  help_request_accepted: (n) => (n.entity_id != null ? `/rooms/${n.entity_id}` : '/study-rooms'),
  section_status: (n) => (n.entity_id != null ? `/sections/${n.entity_id}` : '/sections'),
  new_class_request: () => '/admin/inbox',
  class_request_approved: () => '/sections',
  class_request_rejected: () => '/sections',
  enrollment_approved: (n) => (n.entity_id != null ? `/sections/${n.entity_id}` : '/sections'),
  enrollment_rejected: (n) => (n.entity_id != null ? `/sections/${n.entity_id}` : '/sections'),
  grade_finalization_reminder: (n) => (n.entity_id != null ? `/sections/${n.entity_id}` : '/sections'),
  password_reset_requested: (n) => (n.entity_id != null ? `/admin/users/${n.entity_id}` : '/admin/users'),
  new_unenroll_request: () => '/admin/inbox',
  unenroll_request_approved: (n) => (n.entity_id != null ? `/sections/${n.entity_id}` : '/sections'),
  unenroll_request_rejected: (n) => (n.entity_id != null ? `/sections/${n.entity_id}` : '/sections'),
  removed_from_section: () => '/sections',
}

function NotificationBell() {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const menuRef = useRef(null)
  const { toasts, dismissToast } = useRealtimeToasts()

  const { data: notifications = null } = useNotifications()

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
    queryClient.setQueryData(keys.notifications(), (prev) =>
      (prev || []).map((n) => (n.notification_id === notificationId ? { ...n, is_read: true } : n))
    )
    try {
      await api.patch(`/notifications/${notificationId}/read`)
    } catch {
      // best-effort; a stale read-state will resync next time the list is fetched
    }
  }

  async function markAllRead() {
    queryClient.setQueryData(keys.notifications(), (prev) => (prev || []).map((n) => ({ ...n, is_read: true })))
    try {
      await api.patch('/notifications/read-all')
    } catch {
      // best-effort
    }
  }

  function handleRowClick(notification) {
    if (!notification.is_read) markRead(notification.notification_id)
    setOpen(false)
    const resolveRoute = NOTIFICATION_ROUTES[notification.type]
    const path = resolveRoute ? resolveRoute(notification) : null
    if (path) navigate(path)
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
        <NotificationCountBadge count={unreadCount} />
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
                  <span className="notification-row-text">
                    <span className="notification-message">{n.message}</span>
                    <span className="notification-time">{formatTimestamp(n.created_at)}</span>
                  </span>
                  {NOTIFICATION_ROUTES[n.type] && (
                    <span className="notification-go" aria-hidden="true">
                      Go →
                    </span>
                  )}
                </button>
              ))}
          </div>
        </div>
      )}

      <ToastStack toasts={toasts} onDismiss={dismissToast} />
    </div>
  )
}

export default NotificationBell
