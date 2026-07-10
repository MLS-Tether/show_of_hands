import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { formatDueDate } from '../utils/formatDueDate'
import './Assignments.css'

function Assignments() {
  const navigate = useNavigate()
  const [assignments, setAssignments] = useState(null)
  const [tab, setTab] = useState('upcoming')

  useEffect(() => {
    let cancelled = false
    api
      .get('/sections')
      .then(({ data: sections }) =>
        Promise.allSettled(sections.map((s) => api.get(`/sections/${s.section_id}/assignments`)))
      )
      .then((results) => {
        if (cancelled) return
        const merged = results
          .filter((r) => r.status === 'fulfilled')
          .flatMap((r) => r.value.data)
        const now = Date.now()
        setAssignments({
          upcoming: merged
            .filter((a) => new Date(a.due_date).getTime() >= now)
            .sort((a, b) => new Date(a.due_date) - new Date(b.due_date)),
          past: merged
            .filter((a) => new Date(a.due_date).getTime() < now)
            .sort((a, b) => new Date(b.due_date) - new Date(a.due_date)),
        })
      })
      .catch(() => {
        if (!cancelled) setAssignments({ upcoming: [], past: [] })
      })
    return () => {
      cancelled = true
    }
  }, [])

  const loading = assignments === null
  const rows = loading ? [] : assignments[tab]
  const emptyMessage = tab === 'upcoming' ? 'No upcoming assignments' : 'No past assignments'

  return (
    <section className="assignments-page">
      <h1>Assignments</h1>
      <div role="tablist" aria-label="Assignment status" className="assignments-tabs">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'upcoming'}
          className={`assignments-tab${tab === 'upcoming' ? ' active' : ''}`}
          onClick={() => setTab('upcoming')}
        >
          Upcoming
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'past'}
          className={`assignments-tab${tab === 'past' ? ' active' : ''}`}
          onClick={() => setTab('past')}
        >
          Past
        </button>
      </div>

      {loading && <p className="assignments-placeholder">Loading assignments…</p>}
      {!loading && rows.length === 0 && <p className="assignments-placeholder">{emptyMessage}</p>}
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
