import { useQueries } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'
import api from '../api'
import { keys, useSections } from '../queries'
import { getUserId } from '../utils/auth'
import AddSectionForm from '../components/dashboard/AddSectionForm'
import '../styles/shared-ui.css'
import './TeacherDashboard.css'

function TeacherDashboard() {
  const navigate = useNavigate()
  const userId = getUserId()
  const { data: sections = null } = useSections()

  const loading = sections === null
  const ownedSections = loading ? [] : sections.filter((s) => s.teacher_id === userId)

  const badgeResults = useQueries({
    queries: ownedSections.flatMap((s) => [
      {
        queryKey: keys.sectionEnrollmentRequests(s.section_id),
        queryFn: () => api.get(`/sections/${s.section_id}/enrollment-requests`).then((r) => r.data),
      },
      {
        queryKey: keys.sectionAnalytics(s.section_id),
        queryFn: () => api.get(`/sections/${s.section_id}/analytics`).then((r) => r.data),
      },
    ]),
  })

  const pending = {}
  ownedSections.forEach((s, i) => {
    const enrollmentRequests = badgeResults[i * 2]
    const analytics = badgeResults[i * 2 + 1]
    if (!enrollmentRequests?.isSuccess || !analytics?.isSuccess) return
    const ungraded = analytics.data.assignments.reduce(
      (sum, a) => sum + (a.submitted_count - a.graded_count),
      0
    )
    pending[s.section_id] = { pendingRequests: enrollmentRequests.data.length, ungraded }
  })
  const otherSections = loading ? [] : sections.filter((s) => s.teacher_id !== userId)
  const visibleOwnedSections = ownedSections.slice(0, 3)
  const ownedSectionsHasMore = ownedSections.length > 3
  const visibleOtherSections = otherSections.slice(0, 3)
  const otherSectionsHasMore = otherSections.length > 3

  return (
    <section className="teacher-dashboard">
      <h1 className="admin-page-h1">My Sections</h1>

      {loading && <p className="admin-empty-card">Loading sections…</p>}

      {!loading && ownedSections.length === 0 && (
        <p className="admin-empty-card">No sections yet.</p>
      )}
      {!loading && (
        <div className="teacher-dashboard-grid">
          {visibleOwnedSections.map((s) => {
            const badge = pending[s.section_id]
            const badgeCount = badge ? badge.pendingRequests + badge.ungraded : 0
            return (
              <button
                type="button"
                className="teacher-section-card"
                key={s.section_id}
                onClick={() => navigate(`/sections/${s.section_id}`)}
              >
                {badgeCount > 0 && (
                  <span className="teacher-section-card-badge">{badgeCount}</span>
                )}
                <div className="teacher-section-card-title">{s.class_name}</div>
                <div className="teacher-section-card-sub">{s.period}</div>
                <div className="teacher-section-card-meta">
                  {s.enrolled_count}/{s.capacity} students
                </div>
              </button>
            )
          })}
          {ownedSectionsHasMore && (
            <Link to="/sections" className="teacher-section-show-more">
              Show more
            </Link>
          )}
          <AddSectionForm />
        </div>
      )}

      {!loading && otherSections.length > 0 && (
        <>
          <h2 className="teacher-dashboard-subheading">Other Sections in Your School</h2>
          <div className="teacher-dashboard-grid">
            {visibleOtherSections.map((s) => (
              <div className="teacher-section-card teacher-section-card-readonly" key={s.section_id}>
                <div className="teacher-section-card-title">{s.class_name}</div>
                <div className="teacher-section-card-sub">
                  {s.period} · {s.teacher_name || 'Unassigned teacher'}
                </div>
                <div className="teacher-section-card-meta">
                  {s.enrolled_count}/{s.capacity} students
                </div>
              </div>
            ))}
            {otherSectionsHasMore && (
              <Link to="/sections" className="teacher-section-show-more">
                Show more
              </Link>
            )}
          </div>
        </>
      )}
    </section>
  )
}

export default TeacherDashboard
