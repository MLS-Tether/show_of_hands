import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { useAutoRefresh } from '../utils/autoRefresh'
import { getUserId } from '../utils/auth'
import AddSectionForm from '../components/dashboard/AddSectionForm'
import '../styles/shared-ui.css'
import './TeacherDashboard.css'

// Caps how many sections' badge data are fetched at once. Each section costs
// 2 DB connections (enrollment-requests + analytics); firing all sections in
// parallel can exhaust the DB's connection pool once a teacher has more than
// a few sections, so we fetch in small batches instead.
const BADGE_FETCH_CONCURRENCY = 3

async function mapWithConcurrency(items, limit, fn) {
  const results = new Array(items.length)
  let next = 0
  async function worker() {
    while (next < items.length) {
      const i = next++
      results[i] = await fn(items[i], i)
    }
  }
  await Promise.all(Array.from({ length: Math.min(limit, items.length) }, worker))
  return results
}

function TeacherDashboard() {
  const navigate = useNavigate()
  const [sections, setSections] = useState(null)
  const [pending, setPending] = useState({})
  const userId = getUserId()

  const load = useCallback(() => {
    let cancelled = false
    api
      .get('/sections')
      .then(({ data }) => {
        if (cancelled) return
        setSections(data)

        const owned = data.filter((s) => s.teacher_id === userId)

        mapWithConcurrency(owned, BADGE_FETCH_CONCURRENCY, async (s) => {
          try {
            const [enrollmentRequestsRes, analyticsRes] = await Promise.all([
              api.get(`/sections/${s.section_id}/enrollment-requests`),
              api.get(`/sections/${s.section_id}/analytics`),
            ])
            const ungraded = analyticsRes.data.assignments.reduce(
              (sum, a) => sum + (a.submitted_count - a.graded_count),
              0
            )
            return {
              section_id: s.section_id,
              pendingRequests: enrollmentRequestsRes.data.length,
              ungraded,
            }
          } catch {
            return null
          }
        }).then((results) => {
          if (cancelled) return
          const next = {}
          results.forEach((r) => {
            if (r) next[r.section_id] = { pendingRequests: r.pendingRequests, ungraded: r.ungraded }
          })
          setPending(next)
        })
      })
      .catch(() => {
        if (!cancelled) setSections((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [userId])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  const loading = sections === null
  const ownedSections = loading ? [] : sections.filter((s) => s.teacher_id === userId)
  const otherSections = loading ? [] : sections.filter((s) => s.teacher_id !== userId)

  return (
    <section className="teacher-dashboard">
      <h1 className="admin-page-h1">My Sections</h1>

      {loading && <p className="admin-empty-card">Loading sections…</p>}

      {!loading && ownedSections.length === 0 && (
        <p className="admin-empty-card">No sections yet.</p>
      )}
      {!loading && (
        <div className="teacher-dashboard-grid">
          {ownedSections.map((s) => {
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
          <AddSectionForm onCreated={load} />
        </div>
      )}

      {!loading && otherSections.length > 0 && (
        <>
          <h2 className="teacher-dashboard-subheading">Other Sections in Your School</h2>
          <div className="teacher-dashboard-grid">
            {otherSections.map((s) => (
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
          </div>
        </>
      )}
    </section>
  )
}

export default TeacherDashboard
