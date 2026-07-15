import { useEffect, useState } from 'react'
import api from '../../api'
import './AddSectionForm.css'

function AddSectionForm({ onCreated }) {
  const [expanded, setExpanded] = useState(false)
  const [classes, setClasses] = useState(null)
  const [classId, setClassId] = useState('')
  const [period, setPeriod] = useState('')
  const [capacity, setCapacity] = useState(30)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const [showClassRequest, setShowClassRequest] = useState(false)
  const [newClassName, setNewClassName] = useState('')
  const [classRequestError, setClassRequestError] = useState('')
  const [classRequestMessage, setClassRequestMessage] = useState('')
  const [requestingClass, setRequestingClass] = useState(false)

  useEffect(() => {
    if (!expanded || classes !== null) return
    let cancelled = false
    api
      .get('/classes')
      .then(({ data }) => {
        if (cancelled) return
        setClasses(data)
        if (data.length > 0) setClassId(String(data[0].class_id))
      })
      .catch(() => {
        if (!cancelled) setClasses((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [expanded, classes])

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await api.post('/sections', {
        class_id: Number(classId),
        period,
        capacity: Number(capacity),
      })
      setPeriod('')
      setCapacity(30)
      setExpanded(false)
      onCreated?.()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create this section.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRequestClass(e) {
    e.preventDefault()
    setClassRequestError('')
    setClassRequestMessage('')
    setRequestingClass(true)
    try {
      await api.post('/class-requests', { class_name: newClassName })
      setClassRequestMessage('Request submitted — an admin will review it.')
      setNewClassName('')
    } catch (err) {
      setClassRequestError(err.response?.data?.detail || 'Could not submit this request.')
    } finally {
      setRequestingClass(false)
    }
  }

  if (!expanded) {
    return (
      <button
        type="button"
        className="teacher-section-card add-section-card"
        onClick={() => setExpanded(true)}
      >
        + new section
      </button>
    )
  }

  const loadingClasses = classes === null

  return (
    <div className="add-section-form">
      <form onSubmit={handleCreate}>
        <label>
          Class
          {loadingClasses ? (
            <span className="add-section-hint">Loading classes…</span>
          ) : classes.length === 0 ? (
            <span className="add-section-hint">No classes available yet — request one below.</span>
          ) : (
            <select value={classId} onChange={(e) => setClassId(e.target.value)} required>
              {classes.map((c) => (
                <option key={c.class_id} value={c.class_id}>
                  {c.name}
                </option>
              ))}
            </select>
          )}
        </label>
        <div className="add-section-form-row">
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
        {error && <p className="add-section-error">{error}</p>}
        <div className="add-section-actions">
          <button type="button" onClick={() => setExpanded(false)}>
            Cancel
          </button>
          <button type="submit" disabled={submitting || loadingClasses || !classes?.length}>
            {submitting ? 'Creating…' : 'Create section'}
          </button>
        </div>
      </form>

      <button
        type="button"
        className="add-section-request-toggle"
        onClick={() => setShowClassRequest((v) => !v)}
      >
        Don't see your subject? Request a new class
      </button>

      {showClassRequest && (
        <form className="add-section-request-form" onSubmit={handleRequestClass}>
          <label>
            Class name
            <input value={newClassName} onChange={(e) => setNewClassName(e.target.value)} required />
          </label>
          {classRequestError && <p className="add-section-error">{classRequestError}</p>}
          {classRequestMessage && <p className="add-section-success">{classRequestMessage}</p>}
          <button type="submit" disabled={requestingClass}>
            {requestingClass ? 'Submitting…' : 'Request class'}
          </button>
        </form>
      )}
    </div>
  )
}

export default AddSectionForm
