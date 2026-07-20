import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api'
import { keys, useHelpRequestsBoard } from '../../queries'
import { useDialog } from '../DialogContext'
import { getMyHelpRequestIds, rememberRoom } from '../../utils/roomTracking'
import './HelpRequestsSummary.css'

function HelpRequestsSummary() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { alert } = useDialog()
  const [joiningId, setJoiningId] = useState(null)

  const { data: rawRequests = null } = useHelpRequestsBoard()
  const requests = rawRequests === null ? null : rawRequests.filter((h) => h.status === 'open')

  async function handleJoin(hr) {
    setJoiningId(hr.help_request_id)
    try {
      const { data } = await api.post(`/help-requests/${hr.help_request_id}/accept`)
      rememberRoom({ room_id: data.room_id, topic: hr.topic })
      queryClient.invalidateQueries({ queryKey: keys.helpRequests() })
      navigate(`/rooms/${data.room_id}`)
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not join this request.')
    } finally {
      setJoiningId(null)
    }
  }

  const loading = requests === null
  const myHelpRequestIds = getMyHelpRequestIds()
  const visible = loading ? [] : requests.slice(0, 3)
  const hasMore = !loading && requests.length > 3

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
          visible.map((h) => {
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
        {hasMore && (
          <Link to="/bulletin-board" className="help-request-show-more">
            Show more
          </Link>
        )}
        <Link to="/bulletin-board" className="post-request-card">
          + post request
        </Link>
      </div>
    </section>
  )
}

export default HelpRequestsSummary
