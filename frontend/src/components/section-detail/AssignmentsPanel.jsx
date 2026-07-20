import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api'
import AssignmentFitResult from './AssignmentFitResult'

function AssignmentsPanel({ sectionId, assignments, onChange }) {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [url, setUrl] = useState('')
  const [dueDate, setDueDate] = useState('')
  const [pointValue, setPointValue] = useState(100)
  const [category, setCategory] = useState('homework')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [fitResult, setFitResult] = useState(null)
  const [fitLoading, setFitLoading] = useState(false)
  const [fitHidden, setFitHidden] = useState(false)

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
        category,
      })
      setTitle('')
      setDescription('')
      setUrl('')
      setDueDate('')
      setPointValue(100)
      setCategory('homework')
      setShowForm(false)
      setFitResult(null)
      onChange?.()
    } catch (err) {
      setError(err.response?.data?.message || 'Could not create assignment.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleCheckFit() {
    setError('')
    setFitLoading(true)
    setFitResult(null)
    try {
      const { data } = await api.post(`/sections/${sectionId}/assignment-fit`, {
        title,
        description: description || null,
        category,
        point_value: Number(pointValue),
        due_date: dueDate ? new Date(dueDate).toISOString() : new Date().toISOString(),
      })
      setFitResult(data)
    } catch (err) {
      if (err.response?.status === 503) {
        setFitHidden(true)
      } else {
        setError(err.response?.data?.message || 'Could not check fit.')
      }
    } finally {
      setFitLoading(false)
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
            <label>
              Category
              <select value={category} onChange={(e) => setCategory(e.target.value)}>
                <option value="homework">Homework</option>
                <option value="quizzes">Quizzes</option>
                <option value="tests">Tests</option>
              </select>
            </label>
          </div>
          {error && <p className="teacher-panel-error">{error}</p>}
          <div className="teacher-panel-form-actions">
            {!fitHidden && (
              <button
                type="button"
                className="teacher-panel-button"
                disabled={fitLoading || !title}
                onClick={handleCheckFit}
              >
                {fitLoading ? 'Checking…' : 'Check fit'}
              </button>
            )}
            <button type="button" className="teacher-panel-button" onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button type="submit" className="teacher-panel-button" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      )}

      {showForm && fitResult && (
        <AssignmentFitResult sectionId={sectionId} result={fitResult} />
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
