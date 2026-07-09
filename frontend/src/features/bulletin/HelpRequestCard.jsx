import { useNavigate } from 'react-router-dom'

const STATUS_LABEL = {
  open: 'Open',
  active: 'In session',
  closed: 'Closed',
  expired: 'Expired',
}

export default function HelpRequestCard({ helpRequest, mine, busy, onAccept, onDrop }) {
  const navigate = useNavigate()
  const hr = helpRequest
  const canJoin = !mine && hr.status === 'open' && hr.current_size < hr.group_size
  const canDrop = mine && hr.status === 'open'

  return (
    <div className="card" style={{ marginBottom: 12 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 12 }}>
        <div>
          <h3 style={{ marginBottom: 4 }}>{hr.topic}</h3>
          {hr.description && (
            <p style={{ fontSize: '0.88rem', color: 'var(--color-text-muted)', marginBottom: 8 }}>{hr.description}</p>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
          {mine && <span className="badge badge-mine">Yours</span>}
          <span className={`badge badge-${hr.status}`}>{STATUS_LABEL[hr.status] || hr.status}</span>
        </div>
      </div>

      <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: 14 }}>
        {hr.current_size}/{hr.group_size} joined · {hr.duration_minutes} min session
      </p>

      <div style={{ display: 'flex', gap: 8 }}>
        {canJoin && (
          <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => onAccept(hr.help_request_id)}>
            {busy ? 'Joining…' : 'Join'}
          </button>
        )}
        {hr.room_id != null && (
          <button className="btn btn-secondary btn-sm" onClick={() => navigate(`/rooms/${hr.room_id}`)}>
            View room
          </button>
        )}
        {canDrop && (
          <button className="btn btn-danger btn-sm" disabled={busy} onClick={() => onDrop(hr.help_request_id)}>
            {busy ? 'Dropping…' : 'Drop'}
          </button>
        )}
      </div>
    </div>
  )
}
