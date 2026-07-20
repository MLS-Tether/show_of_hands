import { useState } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import { useAssignments } from '../queries'
import { formatDueDate } from '../utils/formatDueDate'
import { isTeacher } from '../utils/auth'
import '../styles/shared-ui.css'
import './Assignments.css'

function Assignments() {
  const navigate = useNavigate()
  const [tab, setTab] = useState('upcoming')
  const { data: rawAssignments = null } = useAssignments()
  // Lazy-initialized once at mount rather than recomputed on every render,
  // which would call the impure Date.now() during render.
  const [now] = useState(() => Date.now())

  // This page's data endpoint is student-only; teachers manage assignments
  // per-section instead, so redirect rather than let them land on a
  // silently-empty, always-403ing list.
  if (isTeacher()) {
    return <Navigate to="/dashboard" replace />
  }

  const loading = rawAssignments === null
  const assignments = loading
    ? { upcoming: [], past: [] }
    : {
        upcoming: rawAssignments
          .filter((a) => new Date(a.due_date).getTime() >= now)
          .sort((a, b) => new Date(a.due_date) - new Date(b.due_date)),
        past: rawAssignments
          .filter((a) => new Date(a.due_date).getTime() < now)
          .sort((a, b) => new Date(b.due_date) - new Date(a.due_date)),
      }
  const rows = loading ? [] : assignments[tab]
  const emptyMessage = tab === 'upcoming' ? 'No upcoming assignments' : 'No past assignments'

  return (
    <section className="assignments-page">
      <h1 className="admin-page-h1">Assignments</h1>
      <div role="tablist" aria-label="Assignment status" className="admin-filter-chips">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'upcoming'}
          className={`admin-chip${tab === 'upcoming' ? ' active' : ''}`}
          onClick={() => setTab('upcoming')}
        >
          Upcoming
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'past'}
          className={`admin-chip${tab === 'past' ? ' active' : ''}`}
          onClick={() => setTab('past')}
        >
          Past
        </button>
      </div>

      {loading && <p className="admin-empty-card">Loading assignments…</p>}
      {!loading && rows.length === 0 && <p className="admin-empty-card">{emptyMessage}</p>}
      {!loading && rows.length > 0 && (
        <div className="assignments-list">
          {rows.map((a) => (
            <button
              type="button"
              key={a.assignment_id}
              className="assignments-row"
              onClick={() => navigate(`/assignments/${a.assignment_id}`)}
            >
              <span className="assignments-row-title">{a.title}</span>
              <span className="assignments-row-meta">
                <span>{formatDueDate(a.due_date)}</span>
                <span className="assignments-row-points">{a.point_value} pts</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}

export default Assignments
