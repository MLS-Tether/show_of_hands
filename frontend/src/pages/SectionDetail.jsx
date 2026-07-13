import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'
import { useAutoRefresh } from '../utils/autoRefresh'
import './SectionDetail.css'

function SectionDetail() {
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
        <p className="section-detail-placeholder">Loading section…</p>
      </section>
    )
  }

  if (notFound) {
    return (
      <section className="section-detail">
        <p className="section-detail-placeholder">Section not found.</p>
      </section>
    )
  }

  return (
    <section className="section-detail">
      <h1>{section.class_name}</h1>
      <div className="section-detail-meta">
        <span>{section.teacher_name || 'Unassigned teacher'}</span>
        <span>{section.period}</span>
        <span>
          {section.enrolled_count}/{section.capacity} students
        </span>
        <span className="section-detail-status">{section.status}</span>
        <span>Created {new Date(section.created_at).toLocaleDateString()}</span>
      </div>

      <div className="section-detail-columns">
        <div>
          <div className="widget-label">assignments</div>
          {section.assignments.length === 0 ? (
            <p className="section-detail-placeholder">No assignments</p>
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
            <p className="section-detail-placeholder">No quests</p>
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
