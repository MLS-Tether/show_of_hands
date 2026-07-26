function NotificationCountBadge({ count, className = '' }) {
  if (!count || count <= 0) return null
  return <span className={`notification-count-badge ${className}`.trim()}>{count}</span>
}

export default NotificationCountBadge
