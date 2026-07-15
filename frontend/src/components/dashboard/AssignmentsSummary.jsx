import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api'
import { formatDueDate } from '../../utils/formatDueDate'
import { useAutoRefresh } from '../../utils/autoRefresh'
import './AssignmentsSummary.css'

function AssignmentsSummary() {
  const navigate = useNavigate()
  const [assignments, setAssignments] = useState(null)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get('/assignments')
      .then(({ data }) => {
        if (cancelled) return
        const now = Date.now()
        const merged = data
          .filter((a) => new Date(a.due_date).getTime() >= now)
          .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
        setAssignments(merged.slice(0, 3))
      })
      .catch(() => {
        if (!cancelled) setAssignments((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

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
