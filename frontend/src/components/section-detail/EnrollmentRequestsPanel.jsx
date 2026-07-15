import { useCallback, useEffect, useState } from 'react'
import api from '../../api'

function EnrollmentRequestsPanel({ sectionId, onChange }) {
  const [requests, setRequests] = useState(null)
  const [actingId, setActingId] = useState(null)
  const [error, setError] = useState('')

  const load = useCallback(() => {
    let cancelled = false
    api
      .get(`/sections/${sectionId}/enrollment-requests`)
      .then(({ data }) => {
        if (!cancelled) setRequests(data)
      })
      .catch(() => {
        if (!cancelled) setRequests((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [sectionId])

  useEffect(() => load(), [load])

  async function handleDecision(requestId, status) {
    setActingId(requestId)
    setError('')
    try {
      await api.patch(`/enrollment-requests/${requestId}`, { status })
      setRequests((prev) => prev.filter((r) => r.enrollment_request_id !== requestId))
      onChange?.()
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not update this request.')
    } finally {
      setActingId(null)
    }
  }

  const loading = requests === null

  return (
    <div>
      <div className="widget-label">enrollment requests</div>
      {loading && <p className="teacher-panel-placeholder">Loading requests…</p>}
      {!loading && requests.length === 0 && (
        <p className="teacher-panel-placeholder">No pending requests.</p>
      )}
      {!loading && requests.length > 0 && (
        <div className="teacher-panel-list">
          {requests.map((r) => (
            <div className="teacher-panel-row" key={r.enrollment_request_id}>
              <span>{r.username}</span>
              <div className="teacher-panel-row-actions">
                <button
                  type="button"
                  className="teacher-panel-button teacher-panel-accept"
                  disabled={actingId === r.enrollment_request_id}
                  onClick={() => handleDecision(r.enrollment_request_id, 'accepted')}
                >
                  Accept
                </button>
                <button
                  type="button"
                  className="teacher-panel-button"
                  disabled={actingId === r.enrollment_request_id}
                  onClick={() => handleDecision(r.enrollment_request_id, 'rejected')}
                >
                  Deny
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
      {error && <p className="teacher-panel-error">{error}</p>}
    </div>
  )
}

export default EnrollmentRequestsPanel
