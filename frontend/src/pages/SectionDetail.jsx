import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'
import { useAutoRefresh } from '../utils/autoRefresh'
import { isTeacher } from '../utils/auth'
import TeacherSectionDetail from '../components/section-detail/TeacherSectionDetail'
import '../styles/shared-ui.css'
import './SectionDetail.css'

const STATUS_BADGE_CLASS = {
  active: 'status-active',
  pending_reassignment: 'status-pending',
  archived: 'status-archived',
}

function SectionDetail() {
  if (isTeacher()) return <TeacherSectionDetail />
  return <StudentSectionDetail />
}

function StudentSectionDetail() {
  const { sectionId } = useParams()
  const [section, setSection] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const [loadedSectionId, setLoadedSectionId] = useState(null)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get(`/sections/${sectionId}`)
      .then(({ data }) => {
        if (cancelled) return
        setSection(data)
        setNotFound(false)
        setLoadedSectionId(sectionId)
      })
      .catch(() => {
        if (cancelled) return
        setNotFound(true)
        setLoadedSectionId(sectionId)
      })
    return () => {
      cancelled = true
    }
  }, [sectionId])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  const loading = loadedSectionId !== sectionId

  if (loading) {
    return (
      <section className="section-detail">
        <p className="admin-empty-card">Loading section…</p>
      </section>
    )
  }

  if (notFound) {
    return (
      <section className="section-detail">
        <p className="admin-empty-card">Section not found.</p>
      </section>
    )
  }

  return (
    <section className="section-detail">
      <h1 className="admin-page-h1">{section.class_name}</h1>
      <div className="section-detail-meta">
        <span>{section.teacher_name || 'Unassigned teacher'}</span>
        <span>{section.period}</span>
        <span>
          {section.enrolled_count}/{section.capacity} students
        </span>
        <span className={`admin-status-badge ${STATUS_BADGE_CLASS[section.status] || ''}`}>
          {section.status}
        </span>
        <span>Created {new Date(section.created_at).toLocaleDateString()}</span>
      </div>

      <div className="section-detail-columns">
        <div>
          <div className="widget-label">assignments</div>
          {section.assignments.length === 0 ? (
            <p className="admin-empty-card">No assignments</p>
          ) : (
            <div className="section-detail-list">
              {section.assignments.map((a) => (
                <div className="section-detail-row" key={a.assignment_id}>
                  <span>{a.title}</span>
                  <span className="section-detail-row-sub">
                    {new Date(a.due_date).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div>
          <div className="widget-label">quests</div>
          {section.quests.length === 0 ? (
            <p className="admin-empty-card">No quests</p>
          ) : (
            <div className="section-detail-list">
              {section.quests.map((q) => (
                <div className="section-detail-row" key={q.quest_id}>
                  <span>{q.title}</span>
                  <span className="section-detail-row-sub">{q.category}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

export default SectionDetail
