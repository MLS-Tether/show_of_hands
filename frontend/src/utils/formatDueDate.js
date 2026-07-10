export function formatDueDate(dueDateStr) {
  const due = new Date(dueDateStr)
  const now = new Date()
  const dueDay = Date.UTC(due.getFullYear(), due.getMonth(), due.getDate())
  const today = Date.UTC(now.getFullYear(), now.getMonth(), now.getDate())
  const diffDays = Math.round((dueDay - today) / 86400000)

  if (diffDays >= 0 && diffDays < 7) {
    const weekday = new Intl.DateTimeFormat('en-US', { weekday: 'short' }).format(due)
    return `due ${weekday.toLowerCase()}`
  }
  return `due ${new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(due)}`
}
