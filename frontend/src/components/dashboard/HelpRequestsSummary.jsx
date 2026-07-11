import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import api from '../../api'
import { useDialog } from '../DialogProvider'
import { useAutoRefresh } from '../../utils/autoRefresh'
import { getMyHelpRequestIds, rememberRoom } from '../../utils/roomTracking'
import './HelpRequestsSummary.css'

function HelpRequestsSummary({ sections }) {
  const navigate = useNavigate()
  const { alert } = useDialog()
  const [requests, setRequests] = useState(null)
  const [joiningId, setJoiningId] = useState(null)

  const load = useCallback(() => {
    if (!sections) return undefined
    let cancelled = false
    Promise.allSettled(
      sections.map((s) => api.get(`/sections/${s.section_id}/help-requests`))
    ).then((results) => {
      if (cancelled) return
      const merged = results
        .flatMap((r, i) => {
          if (r.status !== 'fulfilled') return []
          return r.value.data.map((hr) => ({ ...hr, section_id: sections[i].section_id }))
        })
        .filter((h) => h.status === 'open')
      setRequests(merged)
    })
    return () => {
      cancelled = true
    }
  }, [sections])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  async function handleJoin(hr) {
    setJoiningId(hr.help_request_id)
    try {
      const { data } = await api.post(`/help-requests/${hr.help_request_id}/accept`)
      rememberRoom({ room_id: data.room_id, topic: hr.topic })
      navigate(`/rooms/${data.room_id}`)
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not join this request.')
    } finally {
      setJoiningId(null)
    }
  }

  const loading = requests === null
  const myHelpRequestIds = getMyHelpRequestIds()

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
          requests.map((h) => {
            const isMine = myHelpRequestIds.includes(h.help_request_id)
            const canJoin = !isMine && h.current_size < h.group_size
            return (
              <div className="help-request-card" key={h.help_request_id}>
                <div className="help-request-topic">{h.topic}</div>
                <div className="help-request-meta">
                  {h.current_size}/{h.group_size} · {h.duration_minutes} min
                </div>
                {canJoin && (
                  <button
                    type="button"
                    className="help-request-join"
                    disabled={joiningId === h.help_request_id}
                    onClick={() => handleJoin(h)}
                  >
                    {joiningId === h.help_request_id ? 'Joining…' : 'Join'}
                  </button>
                )}
              </div>
            )
          })}
        <Link to="/bulletin-board" className="post-request-card">
          + post request
        </Link>
      </div>
    </section>
  )
}

export default HelpRequestsSummary
