import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api'
import { keys, useSectionEnrollmentRequests } from '../../queries'

function EnrollmentRequestsPanel({ sectionId }) {
  const queryClient = useQueryClient()
  const [actingId, setActingId] = useState(null)
  const [error, setError] = useState('')

  const { data: requests = null } = useSectionEnrollmentRequests(sectionId)

  async function handleDecision(requestId, status) {
    setActingId(requestId)
    setError('')
    try {
      await api.patch(`/enrollment-requests/${requestId}`, { status })
      queryClient.setQueryData(keys.sectionEnrollmentRequests(sectionId), (prev) =>
        (prev || []).filter((r) => r.enrollment_request_id !== requestId)
      )
      queryClient.invalidateQueries({ queryKey: ['sections'] })
      queryClient.invalidateQueries({ queryKey: keys.section(sectionId) })
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
