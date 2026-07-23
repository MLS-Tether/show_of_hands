import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../api'
import { useDialog } from '../components/DialogContext'
import { keys, useSections } from '../queries'
import { getUserId, isTeacher } from '../utils/auth'
import '../styles/shared-ui.css'
import './Sections.css'

function Sections() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { confirm, alert } = useDialog()
  const teacher = isTeacher()
  const userId = getUserId()
  const [requestedIds, setRequestedIds] = useState(() => new Set())

  const { data: sections = null } = useSections()
  const { data: allSections = null } = useSections('all', { enabled: !teacher })

  async function handleEnroll(s) {
    const confirmed = await confirm(`Request to join ${s.class_name} (${s.period})?`)
    if (!confirmed) return

    try {
      await api.post(`/sections/${s.section_id}/enrollment-requests`)
      queryClient.invalidateQueries({ queryKey: keys.sectionEnrollmentRequests(s.section_id) })
      setRequestedIds((prev) => new Set(prev).add(s.section_id))
      await alert('Request sent. A teacher or admin needs to approve it.')
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not send the request.')
    }
  }

  const loading = sections === null
  const allLoading = allSections === null

  const ownedSections = teacher ? (sections || []).filter((s) => s.teacher_id === userId) : sections || []
  const otherTeacherSections = teacher
    ? (sections || []).filter((s) => s.teacher_id !== userId)
    : []

  const enrolledIds = new Set((sections || []).map((s) => s.section_id))
  const browsableSections = (allSections || []).filter((s) => !enrolledIds.has(s.section_id))

  return (
    <section className="sections-page">
      <h1 className="admin-page-h1">My sections</h1>
      {loading && <p className="admin-empty-card">Loading sections…</p>}
      {!loading && ownedSections.length === 0 && (
        <p className="admin-empty-card">
          {teacher ? 'No sections yet.' : "You're not enrolled in any sections yet."}
        </p>
      )}
      {!loading && ownedSections.length > 0 && (
        <div className="sections-list">
          {ownedSections.map((s) => (
            <button
              key={s.section_id}
              type="button"
              className="section-row"
              onClick={() => navigate(`/sections/${s.section_id}`)}
            >
              <span className="section-row-name">{s.class_name}</span>
              <span className="section-row-meta">
                {s.period} · {s.teacher_name || 'Unassigned'}
              </span>
            </button>
          ))}
        </div>
      )}

      {teacher ? (
        <>
          <h2 className="sections-subheading">Other Sections in Your School</h2>
          {loading && <p className="admin-empty-card">Loading sections…</p>}
          {!loading && otherTeacherSections.length === 0 && (
            <p className="admin-empty-card">No other sections in your school.</p>
          )}
          {!loading && otherTeacherSections.length > 0 && (
            <div className="sections-list">
              {otherTeacherSections.map((s) => (
                <div className="section-row section-row-readonly" key={s.section_id}>
                  <span className="section-row-name">{s.class_name}</span>
                  <span className="section-row-meta">
                    {s.period} · {s.teacher_name || 'Unassigned'}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      ) : (
        <>
          <h2 className="sections-subheading">All sections</h2>
          {allLoading && <p className="admin-empty-card">Loading sections…</p>}
          {!allLoading && browsableSections.length === 0 && (
            <p className="admin-empty-card">No other sections to join right now.</p>
          )}
          {!allLoading && browsableSections.length > 0 && (
            <div className="sections-list">
              {browsableSections.map((s) => (
                <button
                  key={s.section_id}
                  type="button"
                  className="section-row"
                  disabled={requestedIds.has(s.section_id)}
                  onClick={() => handleEnroll(s)}
                >
                  <span className="section-row-name">
                    {s.class_name}
                    <span className="section-row-teacher"> · {s.teacher_name || 'Unassigned'}</span>
                  </span>
                  <span className="section-row-meta">
                    {requestedIds.has(s.section_id)
                      ? 'Requested'
                      : `${s.enrolled_count}/${s.capacity} students`}
                  </span>
                </button>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default Sections
