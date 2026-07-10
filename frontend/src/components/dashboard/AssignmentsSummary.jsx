import { useEffect, useState } from 'react'
import api from '../../api'
import './AssignmentsSummary.css'

function formatDueDate(dueDateStr) {
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

function AssignmentsSummary({ sections }) {
  const [assignments, setAssignments] = useState(null)

  useEffect(() => {
    if (!sections) return
    let cancelled = false
    Promise.allSettled(
      sections.map((s) => api.get(`/sections/${s.section_id}/assignments`))
    ).then((results) => {
      if (cancelled) return
      const now = Date.now()
      const merged = results
        .filter((r) => r.status === 'fulfilled')
        .flatMap((r) => r.value.data)
        .filter((a) => new Date(a.due_date).getTime() >= now)
        .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
      setAssignments(merged.slice(0, 3))
    })
    return () => {
      cancelled = true
    }
  }, [sections])

  const loading = assignments === null

  return (
    <section className="assignments-summary">
      <div className="widget-label">upcoming assignments</div>
      <div className="assignments-list">
        {loading && <div className="widget-placeholder">Loading assignments…</div>}
        {!loading && assignments.length === 0 && (
          <div className="widget-empty">No upcoming assignments</div>
        )}
        {!loading &&
          assignments.map((a) => (
            <div className="assignment-row" key={a.assignment_id}>
              <span className="assignment-title">{a.title}</span>
              <span className="assignment-due">{formatDueDate(a.due_date)}</span>
            </div>
          ))}
      </div>
    </section>
  )
}

export default AssignmentsSummary
