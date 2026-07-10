import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api'
import { formatDueDate } from '../../utils/formatDueDate'
import './AssignmentsSummary.css'

function AssignmentsSummary({ sections }) {
  const navigate = useNavigate()
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
            <button
              type="button"
              className="assignment-row"
              key={a.assignment_id}
              onClick={() => navigate(`/assignments/${a.assignment_id}`)}
            >
              <span className="assignment-title">{a.title}</span>
              <span className="assignment-due">{formatDueDate(a.due_date)}</span>
            </button>
          ))}
      </div>
    </section>
  )
}

export default AssignmentsSummary
