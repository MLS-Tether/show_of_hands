import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api'
import { keys, useSection, useSectionAnalytics, useSectionEnrollmentRequests } from '../../queries'
import { useEscapeBack } from '../../utils/useEscapeBack'
import RosterPanel from './RosterPanel'
import StudentGradeDetail from './StudentGradeDetail'
import EnrollmentRequestsPanel from './EnrollmentRequestsPanel'
import AssignmentsPanel from './AssignmentsPanel'
import QuestsPanel from './QuestsPanel'
import HelpRequestsPanel from './HelpRequestsPanel'
import AnalyticsPanel from './AnalyticsPanel'
import ResourcesPanel from './ResourcesPanel'
import '../../styles/shared-ui.css'
import '../../pages/SectionDetail.css'
import './TeacherSectionDetail.css'

const STATUS_BADGE_CLASS = {
  active: 'status-active',
  pending_reassignment: 'status-pending',
  archived: 'status-archived',
}

const CARDS = [
  { key: 'roster', label: 'Roster' },
  { key: 'enrollment-requests', label: 'Enrollment Requests' },
  { key: 'assignments', label: 'Assignments' },
  { key: 'quests', label: 'Quests' },
  { key: 'help-requests', label: 'Help Requests' },
  { key: 'analytics', label: 'Analytics' },
  { key: 'resources', label: 'Resources' },
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
  const queryClient = useQueryClient()
  const [activeCard, setActiveCard] = useState(null)
  const [viewingStudent, setViewingStudent] = useState(null)
  const [editing, setEditing] = useState(false)

  const { data: section = null, isError: notFound } = useSection(sectionId)
  const { data: enrollmentRequests } = useSectionEnrollmentRequests(sectionId)
  const { data: analytics } = useSectionAnalytics(sectionId)

  const pendingRequests = enrollmentRequests?.length ?? 0
  const ungraded = analytics
    ? analytics.assignments.reduce((sum, a) => sum + (a.submitted_count - a.graded_count), 0)
    : 0

  useEscapeBack(() => {
    if (viewingStudent) setViewingStudent(null)
    else setActiveCard(null)
  }, Boolean(activeCard))

  const loading = section === null && !notFound

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
        <span>{section.period}</span>
        <span>
          {section.enrolled_count}/{section.capacity} students
        </span>
        <span className={`admin-status-badge ${STATUS_BADGE_CLASS[section.status] || ''}`}>
          {section.status}
        </span>
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
            queryClient.invalidateQueries({ queryKey: keys.section(sectionId) })
          }}
        />
      )}

      {activeCard ? (
        <div>
          {!viewingStudent && <p className="teacher-section-back">Press ESC to go back</p>}
          {activeCard === 'roster' &&
            (viewingStudent ? (
              <StudentGradeDetail sectionId={sectionId} student={viewingStudent} />
            ) : (
              <RosterPanel section={section} onSelectStudent={setViewingStudent} />
            ))}
          {activeCard === 'enrollment-requests' && <EnrollmentRequestsPanel sectionId={sectionId} />}
          {activeCard === 'assignments' && (
            <AssignmentsPanel sectionId={sectionId} assignments={section.assignments} />
          )}
          {activeCard === 'quests' && <QuestsPanel sectionId={sectionId} />}
          {activeCard === 'help-requests' && <HelpRequestsPanel sectionId={sectionId} />}
          {activeCard === 'analytics' && <AnalyticsPanel sectionId={sectionId} />}
          {activeCard === 'resources' && <ResourcesPanel sectionId={sectionId} />}
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
