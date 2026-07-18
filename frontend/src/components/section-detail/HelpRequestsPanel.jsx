import { useEffect, useState } from 'react'
import api from '../../api'

function HelpRequestsPanel({ sectionId }) {
  const [helpRequests, setHelpRequests] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .get(`/sections/${sectionId}/help-requests`)
      .then(({ data }) => {
        if (!cancelled) setHelpRequests(data)
      })
      .catch(() => {
        if (!cancelled) setHelpRequests((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [sectionId])

  const loading = helpRequests === null

  return (
    <div>
      <div className="widget-label">help requests</div>
      {loading && <p className="teacher-panel-placeholder">Loading help requests…</p>}
      {!loading && helpRequests.length === 0 && (
        <p className="teacher-panel-placeholder">No help requests.</p>
      )}
      {!loading && helpRequests.length > 0 && (
        <div className="teacher-panel-list">
          {helpRequests.map((hr) => (
            <div className="teacher-panel-row teacher-panel-row-stacked" key={hr.help_request_id}>
              <div className="teacher-panel-row-header">
                <span>{hr.topic}</span>
                <span className="teacher-panel-row-sub">{hr.status}</span>
              </div>
              {hr.description && <p className="teacher-panel-row-sub">{hr.description}</p>}
              <span className="teacher-panel-row-sub">
                {hr.current_size}/{hr.group_size} joined · {hr.duration_minutes} min
              </span>
              {hr.accepted_by.length > 0 && (
                <span className="teacher-panel-row-sub">
                  Accepted by:{' '}
                  {hr.accepted_by
                    .map((a) => `${a.username} (${new Date(a.accepted_at).toLocaleString()})`)
                    .join(', ')}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default HelpRequestsPanel
