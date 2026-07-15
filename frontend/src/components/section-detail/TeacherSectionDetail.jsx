import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../../api'
import { useAutoRefresh } from '../../utils/autoRefresh'
import RosterPanel from './RosterPanel'
import EnrollmentRequestsPanel from './EnrollmentRequestsPanel'
import AssignmentsPanel from './AssignmentsPanel'
import QuestsPanel from './QuestsPanel'
import HelpRequestsPanel from './HelpRequestsPanel'
import AnalyticsPanel from './AnalyticsPanel'
import '../../pages/SectionDetail.css'
import './TeacherSectionDetail.css'

const CARDS = [
  { key: 'roster', label: 'Roster' },
  { key: 'enrollment-requests', label: 'Enrollment Requests' },
  { key: 'assignments', label: 'Assignments' },
  { key: 'quests', label: 'Quests' },
  { key: 'help-requests', label: 'Help Requests' },
  { key: 'analytics', label: 'Analytics' },
]

function EditSectionForm({ section, onSaved, onCancel }) {
  const [period, setPeriod] = useState(section.period)
  const [capacity, setCapacity] = useState(section.capacity)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      await api.patch(`/sections/${section.section_id}`, {
        period,
        capacity: Number(capacity),
      })
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save changes.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="teacher-panel-form" onSubmit={handleSubmit}>
      <div className="teacher-panel-form-row">
        <label>
          Period
          <input value={period} onChange={(e) => setPeriod(e.target.value)} required />
        </label>
        <label>
          Capacity
          <input
            type="number"
            min="1"
            value={capacity}
            onChange={(e) => setCapacity(e.target.value)}
            required
          />
        </label>
      </div>
      {error && <p className="teacher-panel-error">{error}</p>}
      <div className="teacher-panel-form-actions">
        <button type="button" className="teacher-panel-button" onClick={onCancel}>
          Cancel
        </button>
        <button type="submit" className="teacher-panel-button" disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </form>
  )
}

function TeacherSectionDetail() {
  const { sectionId } = useParams()
  const [section, setSection] = useState(null)
  const [notFound, setNotFound] = useState(false)
  const [loadedSectionId, setLoadedSectionId] = useState(null)
  const [activeCard, setActiveCard] = useState(null)
  const [editing, setEditing] = useState(false)
  const [pendingRequests, setPendingRequests] = useState(0)
  const [ungraded, setUngraded] = useState(0)

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

    Promise.all([
      api.get(`/sections/${sectionId}/enrollment-requests`),
      api.get(`/sections/${sectionId}/analytics`),
    ])
      .then(([enrollmentRequestsRes, analyticsRes]) => {
        if (cancelled) return
        setPendingRequests(enrollmentRequestsRes.data.length)
        setUngraded(
          analyticsRes.data.assignments.reduce(
            (sum, a) => sum + (a.submitted_count - a.graded_count),
            0
          )
        )
      })
      .catch(() => {
        if (cancelled) return
        setPendingRequests(0)
        setUngraded(0)
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
        <span>{section.period}</span>
        <span>
          {section.enrolled_count}/{section.capacity} students
        </span>
        <span className="section-detail-status">{section.status}</span>
        <span>Created {new Date(section.created_at).toLocaleDateString()}</span>
        {!editing && !activeCard && (
          <button type="button" className="teacher-panel-button" onClick={() => setEditing(true)}>
            Edit
          </button>
        )}
      </div>

      {editing && (
        <EditSectionForm
          section={section}
          onCancel={() => setEditing(false)}
          onSaved={() => {
            setEditing(false)
            load()
          }}
        />
      )}

      {activeCard ? (
        <div>
          <button type="button" className="teacher-section-back" onClick={() => setActiveCard(null)}>
            ← Back
          </button>
          {activeCard === 'roster' && <RosterPanel section={section} />}
          {activeCard === 'enrollment-requests' && (
            <EnrollmentRequestsPanel sectionId={sectionId} onChange={load} />
          )}
          {activeCard === 'assignments' && (
            <AssignmentsPanel sectionId={sectionId} assignments={section.assignments} onChange={load} />
          )}
          {activeCard === 'quests' && <QuestsPanel sectionId={sectionId} />}
          {activeCard === 'help-requests' && <HelpRequestsPanel sectionId={sectionId} />}
          {activeCard === 'analytics' && <AnalyticsPanel sectionId={sectionId} />}
        </div>
      ) : (
        <div className="teacher-section-grid">
          {CARDS.map((c) => {
            const badgeCount =
              c.key === 'enrollment-requests' ? pendingRequests : c.key === 'assignments' ? ungraded : 0
            return (
              <button
                type="button"
                className="teacher-section-card-tile"
                key={c.key}
                onClick={() => setActiveCard(c.key)}
              >
                {badgeCount > 0 && <span className="teacher-section-card-badge">{badgeCount}</span>}
                {c.label}
              </button>
            )
          })}
        </div>
      )}
    </section>
  )
}

export default TeacherSectionDetail
