import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'
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
      <button type="submit" disabled={submitting}>
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
      </button>

      {expanded && (
        <div className="submission-detail">
          <div className="submission-detail-row">
            <span className="submission-detail-label">Content</span>
            <span>{submission.content || '—'}</span>
          </div>
          <div className="submission-detail-row">
            <span className="submission-detail-label">File</span>
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
          <div className="submission-detail-row">
            <span className="submission-detail-label">Grade</span>
            <span>{submission.grade != null ? submission.grade : 'Not graded yet'}</span>
          </div>
          <div className="submission-detail-row">
            <span className="submission-detail-label">Points awarded</span>
            <span>{submission.points_awarded}</span>
          </div>
          <div className="submission-detail-row">
            <span className="submission-detail-label">Submitted</span>
            <span>{formatFullDate(submission.submitted_at)}</span>
          </div>
          <div className="submission-detail-row">
            <span className="submission-detail-label">Finalized</span>
            <span>{submission.finalized_at ? formatFullDate(submission.finalized_at) : '—'}</span>
          </div>
        </div>
      )}
    </div>
  )
}

function AssignmentDetail() {
  const { assignmentId } = useParams()
  const [assignment, setAssignment] = useState(null)
  const [assignmentFailed, setAssignmentFailed] = useState(false)
  const [submission, setSubmission] = useState(undefined)

  useEffect(() => {
    let cancelled = false

    api
      .get(`/assignments/${assignmentId}`)
      .then(({ data }) => {
        if (!cancelled) setAssignment(data)
      })
      .catch(() => {
        if (!cancelled) setAssignmentFailed(true)
      })

    api
      .get(`/assignments/${assignmentId}/my-submission`)
      .then(({ data }) => {
        if (!cancelled) setSubmission(data)
      })
      .catch(() => {
        if (!cancelled) setSubmission(null)
      })

    return () => {
      cancelled = true
    }
  }, [assignmentId])

  if (assignmentFailed) {
    return (
      <section className="assignment-detail">
        <p className="assignment-detail-placeholder">Assignment not found.</p>
      </section>
    )
  }

  if (!assignment || submission === undefined) {
    return (
      <section className="assignment-detail">
        <p className="assignment-detail-placeholder">Loading assignment…</p>
      </section>
    )
  }

  return (
    <section className="assignment-detail">
      <h1>{assignment.title}</h1>
      <p className="assignment-detail-due">
        Due {formatFullDate(assignment.due_date)} · {assignment.point_value} pts
      </p>
      {assignment.description && (
        <p className="assignment-detail-description">{assignment.description}</p>
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
