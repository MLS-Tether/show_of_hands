import { useEffect, useState } from 'react'
import { Navigate, useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useAssignments, useNotificationCountsByEntity, useSections } from '../queries'
import { formatDueDate } from '../utils/formatDueDate'
import { isTeacher } from '../utils/auth'
import NotificationCountBadge from '../components/NotificationCountBadge'
import '../styles/shared-ui.css'
import './Assignments.css'

// Group a tab's rows by section, in the student's section order, dropping
// sections with nothing to show in this tab. Rows whose section_id doesn't
// match any enrolled section (e.g. a section left after the data loaded)
// still show up, under a trailing "Other" group, instead of disappearing.
function buildSectionGroups(sections, rows) {
  const bySection = new Map()
  rows.forEach((a) => {
    if (!bySection.has(a.section_id)) bySection.set(a.section_id, [])
    bySection.get(a.section_id).push(a)
  })

  const groups = sections
    .map((s) => ({
      key: s.section_id,
      label: `${s.class_name} — ${s.period}`,
      rows: bySection.get(s.section_id) ?? [],
    }))
    .filter((g) => g.rows.length > 0)

  const knownIds = new Set(sections.map((s) => s.section_id))
  const otherRows = rows.filter((a) => !knownIds.has(a.section_id))
  if (otherRows.length > 0) groups.push({ key: 'other', label: 'Other', rows: otherRows })

  return groups
}

function Assignments() {
  const navigate = useNavigate()
  const location = useLocation()
  const [searchParams] = useSearchParams()
  const [tab, setTab] = useState('upcoming')
  const notifCounts = useNotificationCountsByEntity()
  // Tracks which deep-linked assignment we've already auto-selected a tab
  // for, so re-navigating to a different highlighted assignment re-triggers
  // the tab pick without re-running it on every unrelated render.
  const [lastAppliedHighlightId, setLastAppliedHighlightId] = useState(null)
  const { data: rawAssignments = null } = useAssignments()
  const { data: sections = null } = useSections('mine')
  // Lazy-initialized once at mount rather than recomputed on every render,
  // which would call the impure Date.now() during render.
  const [now] = useState(() => Date.now())

  const highlightId = location.hash.startsWith('#assignment-')
    ? location.hash.slice('#assignment-'.length)
    : null

  useEffect(() => {
    if (!highlightId) return
    const el = document.getElementById(`assignment-${highlightId}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [highlightId, tab])

  // This page's data endpoint is student-only; teachers manage assignments
  // per-section instead, so redirect rather than let them land on a
  // silently-empty, always-403ing list.
  if (isTeacher()) {
    return <Navigate to="/dashboard" replace />
  }

  const sectionFilter = searchParams.get('section')

  const loading = rawAssignments === null || sections === null
  const scoped = loading
    ? []
    : sectionFilter
      ? rawAssignments.filter((a) => String(a.section_id) === sectionFilter)
      : rawAssignments
  const assignments = loading
    ? { upcoming: [], past: [] }
    : {
        upcoming: scoped
          .filter((a) => new Date(a.due_date).getTime() >= now)
          .sort((a, b) => new Date(a.due_date) - new Date(b.due_date)),
        past: scoped
          .filter((a) => new Date(a.due_date).getTime() < now)
          .sort((a, b) => new Date(b.due_date) - new Date(a.due_date)),
      }

  // Deep-linking into a specific assignment (e.g. from the dashboard's
  // section hover panel) should land on whichever tab actually contains it —
  // otherwise a past-due-only link would silently show the empty "Upcoming"
  // tab. Adjusted during render (not in an effect) per React's guidance for
  // deriving state from props/URL changes, so it takes effect in the same
  // commit rather than causing an extra render pass.
  if (!loading && highlightId && highlightId !== lastAppliedHighlightId) {
    setLastAppliedHighlightId(highlightId)
    if (assignments.past.some((a) => String(a.assignment_id) === highlightId)) {
      setTab('past')
    } else if (assignments.upcoming.some((a) => String(a.assignment_id) === highlightId)) {
      setTab('upcoming')
    }
  }

  const rows = loading ? [] : assignments[tab]
  const groups = loading ? [] : buildSectionGroups(sections, rows)
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
      {!loading &&
        groups.map((group) => (
          <div className="assignments-group" key={group.key}>
            <div className="widget-label">{group.label}</div>
            <div className="assignments-list">
              {group.rows.map((a) => (
                <button
                  type="button"
                  key={a.assignment_id}
                  id={`assignment-${a.assignment_id}`}
                  className={`assignments-row${
                    String(a.assignment_id) === highlightId ? ' assignments-row-highlight' : ''
                  }`}
                  onClick={() => navigate(`/assignments/${a.assignment_id}`)}
                >
                  <NotificationCountBadge count={notifCounts[`assignment:${a.assignment_id}`]} />
                  <span className="assignments-row-title">{a.title}</span>
                  <span className="assignments-row-meta">
                    <span>{formatDueDate(a.due_date)}</span>
                    <span className="assignments-row-points">{a.point_value} pts</span>
                  </span>
                </button>
              ))}
            </div>
          </div>
        ))}
    </section>
  )
}

export default Assignments
