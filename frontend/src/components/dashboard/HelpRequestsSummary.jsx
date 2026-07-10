import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../api'
import './HelpRequestsSummary.css'

function HelpRequestsSummary({ sections }) {
  const [requests, setRequests] = useState(null)

  useEffect(() => {
    if (!sections) return
    let cancelled = false
    Promise.allSettled(
      sections.map((s) => api.get(`/sections/${s.section_id}/help-requests`))
    ).then((results) => {
      if (cancelled) return
      const merged = results
        .filter((r) => r.status === 'fulfilled')
        .flatMap((r) => r.value.data)
        .filter((h) => h.status === 'open')
      setRequests(merged)
    })
    return () => {
      cancelled = true
    }
  }, [sections])

  const loading = requests === null

  return (
    <section className="help-requests-summary">
      <div className="help-requests-header">
        <div className="widget-label">bulletin board — help requests</div>
        <span className="help-requests-tag">anonymous</span>
      </div>
      <div className="help-requests-grid">
        {loading && <div className="widget-placeholder">Loading help requests…</div>}
        {!loading && requests.length === 0 && (
          <div className="widget-empty">No open help requests</div>
        )}
        {!loading &&
          requests.map((h) => (
            <div className="help-request-card" key={h.help_request_id}>
              <div className="help-request-topic">{h.topic}</div>
              <div className="help-request-meta">
                {h.current_size}/{h.group_size} · {h.duration_minutes} min
              </div>
            </div>
          ))}
        <Link to="/bulletin-board" className="post-request-card">
          + post request
        </Link>
      </div>
    </section>
  )
}

export default HelpRequestsSummary
