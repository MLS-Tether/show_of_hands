import { useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api'
import { useToast } from '../../components/ToastContext'
import { keys, useSections, useUsers } from '../../queries'
import '../../styles/shared-ui.css'
import './AdminSections.css'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'active', label: 'Active' },
  { key: 'pending_reassignment', label: 'Needs teacher' },
  { key: 'archived', label: 'Archived' },
]

const STATUS_BADGE = {
  active: { label: 'Active', className: 'status-active' },
  pending_reassignment: { label: 'Pending reassignment', className: 'status-pending' },
  archived: { label: 'Archived', className: 'status-archived' },
}

const STATUS_OPTIONS = [
  { key: 'active', label: 'Active' },
  { key: 'pending_reassignment', label: 'Needs teacher' },
  { key: 'archived', label: 'Archived' },
]

function AdminSections() {
  const { showToast } = useToast()
  const queryClient = useQueryClient()
  const [filter, setFilter] = useState('all')
  const [expanded, setExpanded] = useState(null)
  const [broadcastFor, setBroadcastFor] = useState(null)
  const [broadcastText, setBroadcastText] = useState('')
  const [busy, setBusy] = useState(false)

  const { data: sections = null } = useSections('all')
  const { data: teachers = [] } = useUsers({ role: 'teacher' })

  const counts = useMemo(() => {
    const list = sections || []
    return {
      all: list.length,
      active: list.filter((s) => s.status === 'active').length,
      pending_reassignment: list.filter((s) => s.status === 'pending_reassignment').length,
      archived: list.filter((s) => s.status === 'archived').length,
    }
  }, [sections])

  const filtered = useMemo(() => {
    const list = sections || []
    if (filter === 'all') return list
    return list.filter((s) => s.status === filter)
  }, [sections, filter])

  function patchLocal(sectionId, patch) {
    queryClient.setQueryData(keys.sections('all'), (prev) =>
      (prev || []).map((s) => (s.section_id === sectionId ? { ...s, ...patch } : s))
    )
    queryClient.invalidateQueries({ queryKey: ['sections', 'mine'] })
    queryClient.invalidateQueries({ queryKey: keys.section(sectionId) })
  }

  async function reassignTeacher(section, teacherId) {
    setBusy(true)
    const body = { teacher_id: teacherId }
    if (section.status === 'pending_reassignment') body.status = 'active'
    try {
      await api.patch(`/sections/${section.section_id}`, body)
      const teacher = teachers.find((t) => t.user_id === teacherId)
      patchLocal(section.section_id, {
        teacher_id: teacherId,
        teacher_name: teacher ? teacher.username : null,
        status: body.status || section.status,
      })
      showToast('Teacher reassigned')
    } catch {
      showToast("Couldn't reassign teacher")
    } finally {
      setBusy(false)
    }
  }

  async function setStatus(section, status) {
    if (status === section.status) return
    setBusy(true)
    try {
      await api.patch(`/sections/${section.section_id}`, { status })
      patchLocal(section.section_id, { status })
      showToast('Status updated')
    } catch {
      showToast("Couldn't update status")
    } finally {
      setBusy(false)
    }
  }

  async function sendBroadcast(section) {
    if (!broadcastText.trim()) return
    setBusy(true)
    try {
      await api.post(`/sections/${section.section_id}/notify`, { message: broadcastText })
      showToast('Message sent')
      setBroadcastFor(null)
      setBroadcastText('')
    } catch {
      showToast("Couldn't send message")
    } finally {
      setBusy(false)
    }
  }

  const loading = sections === null

  return (
    <div className="admin-sections">
      <h1 className="admin-page-h1">Sections</h1>
      <p className="admin-page-subtitle">Manage class sections across the school.</p>

      <div className="admin-filter-chips">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`admin-chip${filter === f.key ? ' active' : ''}`}
            onClick={() => setFilter(f.key)}
          >
            {f.label} <span className="admin-chip-count">{counts[f.key]}</span>
          </button>
        ))}
      </div>

      {!loading && filtered.length === 0 && (
        <div className="admin-empty-card">No sections match this filter.</div>
      )}

      <div className="admin-section-list">
        {filtered.map((section) => {
          const isExpanded = expanded === section.section_id
          const badge = STATUS_BADGE[section.status]
          return (
            <div
              className={`admin-section-card${isExpanded ? ' expanded' : ''}`}
              key={section.section_id}
            >
              <button
                type="button"
                className="admin-section-row"
                onClick={() => setExpanded(isExpanded ? null : section.section_id)}
              >
                <div className="admin-section-row-main">
                  <div className="admin-section-title-line">
                    <span className="admin-section-title">
                      {section.class_name} · {section.period}
                    </span>
                    <span className={`admin-status-badge ${badge.className}`}>{badge.label}</span>
                  </div>
                  <div className="admin-section-meta">
                    {section.teacher_name || 'Unassigned'} · {section.enrolled_count}/
                    {section.capacity} students
                  </div>
                </div>
                <span className={`admin-chevron${isExpanded ? ' rotated' : ''}`}>▾</span>
              </button>

              {isExpanded && (
                <div className="admin-section-panel">
                  <div className="admin-control-group">
                    <div className="admin-control-label">Assigned teacher</div>
                    <select
                      className="admin-teacher-select"
                      value={section.teacher_id || ''}
                      disabled={busy}
                      onChange={(e) =>
                        reassignTeacher(
                          section,
                          e.target.value ? Number(e.target.value) : null
                        )
                      }
                    >
                      <option value="">Unassigned</option>
                      {teachers.map((t) => (
                        <option key={t.user_id} value={t.user_id}>
                          {t.username}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="admin-control-group">
                    <div className="admin-control-label">Status</div>
                    <div className="admin-segmented">
                      {STATUS_OPTIONS.map((opt) => (
                        <button
                          key={opt.key}
                          type="button"
                          disabled={busy}
                          className={`admin-segment${section.status === opt.key ? ' active' : ''}`}
                          onClick={() => setStatus(section, opt.key)}
                        >
                          {opt.label}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="admin-section-actions-row">
                    <button
                      type="button"
                      className="admin-btn-secondary"
                      onClick={() =>
                        setBroadcastFor(broadcastFor === section.section_id ? null : section.section_id)
                      }
                    >
                      Broadcast to students
                    </button>
                    <button
                      type="button"
                      className="admin-btn-danger"
                      disabled={busy || section.status === 'archived'}
                      onClick={() => setStatus(section, 'archived')}
                    >
                      Archive section
                    </button>
                  </div>

                  {broadcastFor === section.section_id && (
                    <div className="admin-broadcast-composer">
                      <div className="admin-broadcast-title">
                        Message all {section.enrolled_count} students in {section.class_name}
                      </div>
                      <textarea
                        className="admin-broadcast-textarea"
                        value={broadcastText}
                        onChange={(e) => setBroadcastText(e.target.value)}
                        placeholder="Write a message…"
                      />
                      <div className="admin-broadcast-actions">
                        <button
                          type="button"
                          className="admin-btn-primary"
                          disabled={busy || !broadcastText.trim()}
                          onClick={() => sendBroadcast(section)}
                        >
                          Send
                        </button>
                        <button
                          type="button"
                          className="admin-btn-text"
                          onClick={() => {
                            setBroadcastFor(null)
                            setBroadcastText('')
                          }}
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default AdminSections
