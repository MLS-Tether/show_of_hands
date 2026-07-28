import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api'
import { keys, useSectionUnenrollRequests } from '../../queries'

function RosterPanel({ section, sectionId, onSelectStudent }) {
  const queryClient = useQueryClient()
  const students = section.students
  const [requestingId, setRequestingId] = useState(null)
  const [reason, setReason] = useState('')
  const [actingId, setActingId] = useState(null)
  const [error, setError] = useState('')

  const { data: pendingRequests = [] } = useSectionUnenrollRequests(sectionId)
  const pendingByStudent = new Map(pendingRequests.map((r) => [r.student_id, r]))

  async function handleSubmitRequest(studentId) {
    setActingId(studentId)
    setError('')
    try {
      const { data } = await api.post(`/sections/${sectionId}/unenroll-requests`, {
        student_id: studentId,
        reason,
      })
      queryClient.setQueryData(keys.sectionUnenrollRequests(sectionId), (prev) => [...(prev || []), data])
      setRequestingId(null)
      setReason('')
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not submit this request.')
    } finally {
      setActingId(null)
    }
  }

  async function handleCancel(requestId) {
    setActingId(requestId)
    setError('')
    try {
      await api.post(`/unenroll-requests/${requestId}/cancel`)
      queryClient.setQueryData(keys.sectionUnenrollRequests(sectionId), (prev) =>
        (prev || []).filter((r) => r.unenroll_request_id !== requestId)
      )
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not cancel this request.')
    } finally {
      setActingId(null)
    }
  }

  return (
    <div>
      <div className="widget-label">roster</div>
      {students.length === 0 ? (
        <p className="teacher-panel-placeholder">No students enrolled.</p>
      ) : (
        <div className="teacher-panel-list">
          {students.map((s) => {
            const pending = pendingByStudent.get(s.user_id)
            const isRequesting = requestingId === s.user_id
            return (
              <div
                className={`teacher-panel-row${isRequesting ? ' teacher-panel-row-stacked' : ''}`}
                key={s.user_id}
              >
                <div className="teacher-panel-row-header">
                  <button
                    type="button"
                    className="teacher-panel-row-name"
                    onClick={() => onSelectStudent(s)}
                  >
                    {s.username}
                  </button>
                  <div className="teacher-panel-row-actions">
                    {pending ? (
                      <button
                        type="button"
                        className="teacher-panel-button"
                        disabled={actingId === pending.unenroll_request_id}
                        onClick={() => handleCancel(pending.unenroll_request_id)}
                      >
                        Cancel request
                      </button>
                    ) : (
                      !isRequesting && (
                        <button
                          type="button"
                          className="teacher-panel-button"
                          onClick={() => {
                            setRequestingId(s.user_id)
                            setReason('')
                            setError('')
                          }}
                        >
                          Request unenroll
                        </button>
                      )
                    )}
                  </div>
                </div>
                {isRequesting && (
                  <>
                    <textarea
                      className="teacher-panel-textarea"
                      placeholder="Reason for removal…"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                    />
                    <div className="teacher-panel-row-actions">
                      <button
                        type="button"
                        className="teacher-panel-button teacher-panel-accept"
                        disabled={!reason.trim() || actingId === s.user_id}
                        onClick={() => handleSubmitRequest(s.user_id)}
                      >
                        Submit
                      </button>
                      <button type="button" className="teacher-panel-button" onClick={() => setRequestingId(null)}>
                        Cancel
                      </button>
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      )}
      {error && <p className="teacher-panel-error">{error}</p>}
    </div>
  )
}

export default RosterPanel
