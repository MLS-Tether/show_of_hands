import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api'

function AssignmentsPanel({ sectionId, assignments, onChange }) {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [url, setUrl] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [pointValue, setPointValue] = useState(100)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await api.post(`/sections/${sectionId}/assignments`, {
        title,
        description: description || null,
        url: url || null,
        due_date: new Date(dueDate).toISOString(),
        point_value: Number(pointValue),
      })
      setTitle('')
      setDescription('')
      setUrl('')
      setDueDate('')
      setPointValue(100)
      setShowForm(false)
      onChange?.()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create assignment.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div>
      <div className="widget-label">assignments</div>

      {!showForm && (
        <button
          type="button"
          className="teacher-panel-button teacher-panel-add-toggle"
          onClick={() => setShowForm(true)}
        >
          + new assignment
        </button>
      )}

      {showForm && (
        <form className="teacher-panel-form" onSubmit={handleCreate}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Description (optional)
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
          </label>
          <label>
            URL (optional)
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
            />
          </label>
          <div className="teacher-panel-form-row">
            <label>
              Due date
              <input
                type="datetime-local"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                required
              />
            </label>
            <label>
              Points
              <input
                type="number"
                min="1"
                value={pointValue}
                onChange={(e) => setPointValue(e.target.value)}
                required
              />
            </label>
          </div>
          {error && <p className="teacher-panel-error">{error}</p>}
          <div className="teacher-panel-form-actions">
            <button type="button" className="teacher-panel-button" onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button type="submit" className="teacher-panel-button" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      )}

      {assignments.length === 0 ? (
        <p className="teacher-panel-placeholder">No assignments yet.</p>
      ) : (
        <div className="teacher-panel-list">
          {assignments.map((a) => (
            <button
              type="button"
              className="teacher-panel-row"
              key={a.assignment_id}
              onClick={() => navigate(`/assignments/${a.assignment_id}`)}
            >
              <span>{a.title}</span>
              <span className="teacher-panel-row-sub">
                Due {new Date(a.due_date).toLocaleDateString()}
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default AssignmentsPanel
