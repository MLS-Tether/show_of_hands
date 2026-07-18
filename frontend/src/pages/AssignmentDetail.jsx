import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api'
import { useAutoRefresh } from '../utils/autoRefresh'
import { isTeacher } from '../utils/auth'
import { useDialog } from '../components/DialogContext'
import '../styles/shared-ui.css'
import './AssignmentDetail.css'

const STATUS_LABELS = {
  submitted: 'Submitted',
  pending: 'Pending review',
  graded: 'Graded',
}

function formatFullDate(dateStr) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(dateStr))
}

function isUrl(value) {
  return /^https?:\/\//i.test(value || '')
}

function toDatetimeLocalValue(iso) {
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function EditAssignmentForm({ assignment, onSaved, onCancel }) {
  const [title, setTitle] = useState(assignment.title)
  const [description, setDescription] = useState(assignment.description || '')
  const [url, setUrl] = useState(assignment.url || '')
  const [dueDate, setDueDate] = useState(toDatetimeLocalValue(assignment.due_date))
  const [pointValue, setPointValue] = useState(assignment.point_value)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSaving(true)
    try {
      await api.patch(`/assignments/${assignment.assignment_id}`, {
        title,
        description: description || null,
        url: url || null,
        due_date: new Date(dueDate).toISOString(),
        point_value: Number(pointValue),
      })
      onSaved()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save changes.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form className="submission-form" onSubmit={handleSubmit}>
      <label className="submission-form-field">
        Title
        <input value={title} onChange={(e) => setTitle(e.target.value)} required />
      </label>
      <label className="submission-form-field">
        Description
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
      </label>
      <label className="submission-form-field">
        URL (optional)
        <input type="url" value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://…" />
      </label>
      <label className="submission-form-field">
        Due date
        <input type="datetime-local" value={dueDate} onChange={(e) => setDueDate(e.target.value)} required />
      </label>
      <label className="submission-form-field">
        Points
        <input
          type="number"
          min="1"
          value={pointValue}
          onChange={(e) => setPointValue(e.target.value)}
          required
        />
      </label>
      {error && <p className="submission-form-error">{error}</p>}
      <div className="assignment-detail-actions">
        <button type="button" className="admin-btn-secondary" onClick={onCancel} disabled={saving}>
          Cancel
        </button>
        <button type="submit" className="admin-btn-primary" disabled={saving}>
          {saving ? 'Saving…' : 'Save'}
        </button>
      </div>
    </form>
  )
}

function SubmissionForm({ assignmentId, onSubmitted }) {
  const [content, setContent] = useState('')
  const [fileUrl, setFileUrl] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const { data } = await api.post(`/assignments/${assignmentId}/submissions`, {
        content: content || null,
        file_url: fileUrl || null,
      })
      onSubmitted({
        ...data,
        content: content || null,
        file_url: fileUrl || null,
        grade: null,
        finalized_at: null,
      })
    } catch (err) {
      if (err.response?.status === 409) {
        try {
          const { data } = await api.get(`/assignments/${assignmentId}/my-submission`)
          onSubmitted(data)
          return
        } catch {
          // fall through to showing the original error
        }
      }
      setError(err.response?.data?.message || 'Could not submit.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="submission-form" onSubmit={handleSubmit}>
      <label className="submission-form-field">
        Content (optional)
        <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={4} />
      </label>
      <label className="submission-form-field">
        File URL (optional)
        <input value={fileUrl} onChange={(e) => setFileUrl(e.target.value)} />
      </label>
      {error && <p className="submission-form-error">{error}</p>}
      <button type="submit" className="admin-btn-primary" disabled={submitting}>
        {submitting ? 'Submitting…' : 'Submit'}
      </button>
    </form>
  )
}

function SubmissionSummary({ submission }) {
  const [expanded, setExpanded] = useState(false)

  return (
    <div className="submission-summary">
      <button
        type="button"
        className="submission-summary-card"
        onClick={() => setExpanded((e) => !e)}
      >
        <span className={`submission-status submission-status-${submission.status}`}>
          {STATUS_LABELS[submission.status] || submission.status}
        </span>
        <span className="submission-summary-points">{submission.points_awarded} pts</span>
        {submission.grade != null && (
          <span className="submission-summary-grade">Grade: {submission.grade}</span>
        )}
        <span className={`admin-chevron${expanded ? ' rotated' : ''}`}>▾</span>
      </button>

      {expanded && (
        <div className="submission-detail">
          <div className="admin-detail-row">
            <span className="admin-detail-label">Content</span>
            <span>{submission.content || '—'}</span>
          </div>
          <div className="admin-detail-row">
            <span className="admin-detail-label">File</span>
            <span>
              {submission.file_url ? (
                isUrl(submission.file_url) ? (
                  <a href={submission.file_url} target="_blank" rel="noreferrer">
                    {submission.file_url}
                  </a>
                ) : (
                  submission.file_url
                )
              ) : (
                '—'
              )}
            </span>
          </div>
          <div className="admin-detail-row">
            <span className="admin-detail-label">Grade</span>
            <span>{submission.grade != null ? submission.grade : 'Not graded yet'}</span>
          </div>
          <div className="admin-detail-row">
            <span className="admin-detail-label">Points awarded</span>
            <span>{submission.points_awarded}</span>
          </div>
          <div className="admin-detail-row">
            <span className="admin-detail-label">Submitted</span>
            <span>{formatFullDate(submission.submitted_at)}</span>
          </div>
          <div className="admin-detail-row">
            <span className="admin-detail-label">Finalized</span>
            <span>{submission.finalized_at ? formatFullDate(submission.finalized_at) : '—'}</span>
          </div>
        </div>
      )}
    </div>
  )
}

function GradingRow({ submission, onGraded }) {
  const [expanded, setExpanded] = useState(false)
  const [grade, setGrade] = useState(submission.grade ?? '')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const isGraded = submission.status === 'graded'

  async function handleSaveGrade() {
    setError('')
    setSaving(true)
    try {
      const { data } = await api.patch(`/submissions/${submission.submission_id}/grade`, {
        grade: Number(grade),
      })
      onGraded({ ...submission, grade: data.grade, status: data.status })
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not save grade.')
    } finally {
      setSaving(false)
    }
  }

  async function handleFinalize() {
    setError('')
    setSaving(true)
    try {
      const { data } = await api.post(`/submissions/${submission.submission_id}/finalize`)
      onGraded({
        ...submission,
        grade: data.grade,
        status: data.status,
        points_awarded: data.points_awarded,
      })
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not finalize this submission.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="submission-summary">
      <button
        type="button"
        className="submission-summary-card"
        onClick={() => setExpanded((e) => !e)}
      >
        <span>{submission.username}</span>
        <span className={`submission-status submission-status-${submission.status}`}>
          {STATUS_LABELS[submission.status] || submission.status}
        </span>
        <span className="submission-summary-points">{submission.points_awarded} pts</span>
        {submission.grade != null && (
          <span className="submission-summary-grade">Grade: {submission.grade}</span>
        )}
        <span className={`admin-chevron${expanded ? ' rotated' : ''}`}>▾</span>
      </button>

      {expanded && (
        <div className="submission-detail">
          <div className="admin-detail-row">
            <span className="admin-detail-label">Submitted</span>
            <span>{formatFullDate(submission.submitted_at)}</span>
          </div>

          {isGraded ? (
            <div className="admin-detail-row">
              <span className="admin-detail-label">Grade</span>
              <span>
                {submission.grade} — {submission.points_awarded} pts (finalized)
              </span>
            </div>
          ) : (
            <>
              <label className="submission-form-field">
                Grade
                <input
                  type="number"
                  min="0"
                  max="100"
                  value={grade}
                  onChange={(e) => setGrade(e.target.value)}
                />
              </label>
              <p className="grading-hint">
                25% was already awarded on submission. Finalizing adds +75% at grade ≥ 85, +50% at
                grade ≥ 70, or +0% below 70.
              </p>
              {error && <p className="submission-form-error">{error}</p>}
              <button
                type="button"
                className="admin-btn-secondary"
                disabled={saving || grade === ''}
                onClick={handleSaveGrade}
              >
                {saving ? 'Saving…' : 'Save grade'}
              </button>
              <button
                type="button"
                className="admin-btn-primary"
                disabled={saving || submission.grade == null}
                onClick={handleFinalize}
              >
                {saving ? 'Finalizing…' : 'Finalize'}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  )
}

function TeacherAssignmentView({ assignmentId, assignment, onAssignmentChanged }) {
  const navigate = useNavigate()
  const { confirm } = useDialog()
  const [submissions, setSubmissions] = useState(null)
  const [editing, setEditing] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [deleteError, setDeleteError] = useState('')

  const load = useCallback(() => {
    let cancelled = false
    api
      .get(`/assignments/${assignmentId}/submissions`)
      .then(({ data }) => {
        if (!cancelled) setSubmissions(data)
      })
      .catch(() => {
        if (!cancelled) setSubmissions((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [assignmentId])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  function handleGraded(updated) {
    setSubmissions((prev) =>
      prev.map((s) => (s.submission_id === updated.submission_id ? updated : s))
    )
  }

  async function handleDelete() {
    const ok = await confirm('Delete this assignment? This cannot be undone.')
    if (!ok) return
    setDeleteError('')
    setDeleting(true)
    try {
      await api.delete(`/assignments/${assignmentId}`)
      navigate(`/sections/${assignment.section_id}`)
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Could not delete this assignment.')
      setDeleting(false)
    }
  }

  const loading = submissions === null

  return (
    <section className="assignment-detail">
      {editing ? (
        <EditAssignmentForm
          assignment={assignment}
          onCancel={() => setEditing(false)}
          onSaved={() => {
            setEditing(false)
            onAssignmentChanged()
          }}
        />
      ) : (
        <>
          <h1 className="admin-page-h1">{assignment.title}</h1>
          <p className="assignment-detail-due">
            Due {formatFullDate(assignment.due_date)} · {assignment.point_value} pts
          </p>
          {assignment.description && (
            <p className="assignment-detail-description">{assignment.description}</p>
          )}
          {assignment.url && (
            <p className="assignment-detail-description">
              <a href={assignment.url} target="_blank" rel="noreferrer">
                {assignment.url}
              </a>
            </p>
          )}
          <div className="assignment-detail-actions">
            <button type="button" className="admin-btn-secondary" onClick={() => setEditing(true)}>
              Edit
            </button>
            <button type="button" className="admin-btn-danger" disabled={deleting} onClick={handleDelete}>
              {deleting ? 'Deleting…' : 'Delete'}
            </button>
          </div>
          {deleteError && <p className="submission-form-error">{deleteError}</p>}
        </>
      )}

      <div className="widget-label">submissions</div>
      {loading && <p className="admin-empty-card">Loading submissions…</p>}
      {!loading && submissions.length === 0 && (
        <p className="admin-empty-card">No submissions yet.</p>
      )}
      {!loading &&
        submissions.map((s) => (
          <GradingRow key={s.submission_id} submission={s} onGraded={handleGraded} />
        ))}
    </section>
  )
}

function AssignmentDetail() {
  const { assignmentId } = useParams()
  const [assignment, setAssignment] = useState(null)
  const [assignmentFailed, setAssignmentFailed] = useState(false)
  const [submission, setSubmission] = useState(undefined)
  const teacher = isTeacher()

  const load = useCallback(() => {
    let cancelled = false

    api
      .get(`/assignments/${assignmentId}`)
      .then(({ data }) => {
        if (!cancelled) setAssignment(data)
      })
      .catch(() => {
        if (!cancelled) setAssignmentFailed(true)
      })

    if (!teacher) {
      api
        .get(`/assignments/${assignmentId}/my-submission`)
        .then(({ data }) => {
          if (!cancelled) setSubmission(data)
        })
        .catch(() => {
          if (!cancelled) setSubmission((prev) => (prev === undefined ? null : prev))
        })
    }

    return () => {
      cancelled = true
    }
  }, [assignmentId, teacher])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  if (assignmentFailed) {
    return (
      <section className="assignment-detail">
        <p className="admin-empty-card">Assignment not found.</p>
      </section>
    )
  }

  if (!assignment || (!teacher && submission === undefined)) {
    return (
      <section className="assignment-detail">
        <p className="admin-empty-card">Loading assignment…</p>
      </section>
    )
  }

  if (teacher) {
    return (
      <TeacherAssignmentView
        assignmentId={assignmentId}
        assignment={assignment}
        onAssignmentChanged={load}
      />
    )
  }

  return (
    <section className="assignment-detail">
      <h1 className="admin-page-h1">{assignment.title}</h1>
      <p className="assignment-detail-due">
        Due {formatFullDate(assignment.due_date)} · {assignment.point_value} pts
      </p>
      {assignment.description && (
        <p className="assignment-detail-description">{assignment.description}</p>
      )}
      {assignment.url && (
        <p className="assignment-detail-description">
          <a href={assignment.url} target="_blank" rel="noreferrer">
            {assignment.url}
          </a>
        </p>
      )}

      <div className="widget-label">submission</div>
      {submission ? (
        <SubmissionSummary submission={submission} />
      ) : (
        <SubmissionForm assignmentId={assignmentId} onSubmitted={setSubmission} />
      )}
    </section>
  )
}

export default AssignmentDetail
