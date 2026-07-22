import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAssignments } from '../../queries'
import { formatDueDate } from '../../utils/formatDueDate'
import './AssignmentsSummary.css'

function AssignmentsSummary() {
  const navigate = useNavigate()
  const { data: rawAssignments = null } = useAssignments()
  // Lazy-initialized once at mount rather than recomputed on every render,
  // which would call the impure Date.now() during render.
  const [now] = useState(() => Date.now())

  const loading = rawAssignments === null
  const assignments = loading
    ? []
    : rawAssignments
        .filter((a) => new Date(a.due_date).getTime() >= now)
        .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
  const visible = loading ? [] : assignments.slice(0, 3)
  const hasMore = !loading && assignments.length > 3

  return (
    <section className="assignments-summary">
      <div className="widget-label">upcoming assignments</div>
      <div className="assignments-list">
        {loading && <div className="widget-placeholder">Loading assignments…</div>}
        {!loading && assignments.length === 0 && (
          <div className="widget-empty">No upcoming assignments</div>
        )}
        {!loading &&
          visible.map((a) => (
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
        {hasMore && (
          <Link to="/assignments" className="assignment-show-more">
            Show more
          </Link>
        )}
      </div>
    </section>
  )
}

export default AssignmentsSummary
