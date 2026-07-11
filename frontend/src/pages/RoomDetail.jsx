import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../api'
import { forgetRoom, rememberRoom } from '../utils/roomTracking'
import './RoomDetail.css'

function formatCountdown(ms) {
  if (ms <= 0) return '0:00'
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function wsUrlFor(roomId) {
  const wsBase = api.defaults.baseURL.replace(/^http/, 'ws')
  const token = localStorage.getItem('access_token')
  return `${wsBase}/rooms/${roomId}/chat?token=${encodeURIComponent(token)}`
}

function RoomDetail() {
  const { roomId } = useParams()
  const currentUserId = Number(localStorage.getItem('user_id'))

  const [room, setRoom] = useState(null)
  const [loadFailed, setLoadFailed] = useState(false)
  const [loadedRoomId, setLoadedRoomId] = useState(null)
  const [messages, setMessages] = useState([])
  const [draft, setDraft] = useState('')
  const [now, setNow] = useState(() => Date.now())
  const [confirmPending, setConfirmPending] = useState(false)
  const [confirmResult, setConfirmResult] = useState(null)
  const [actionError, setActionError] = useState('')
  const wsRef = useRef(null)

  useEffect(() => {
    let cancelled = false
    api
      .get(`/rooms/${roomId}`)
      .then(({ data }) => {
        if (cancelled) return
        setRoom(data)
        setLoadFailed(false)
        setLoadedRoomId(roomId)
        rememberRoom({ room_id: data.room_id })
      })
      .catch(() => {
        if (cancelled) return
        setLoadFailed(true)
        setLoadedRoomId(roomId)
      })
    return () => {
      cancelled = true
    }
  }, [roomId])

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const activeRoomId = room?.status === 'active' ? room.room_id : null

  useEffect(() => {
    if (!activeRoomId) return
    const ws = new WebSocket(wsUrlFor(activeRoomId))
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'session_confirmation_required') {
        setConfirmPending(true)
        return
      }
      setMessages((prev) => [...prev, data])
    }

    return () => {
      ws.close()
      wsRef.current = null
    }
  }, [activeRoomId])

  function handleSend(e) {
    e.preventDefault()
    if (!draft.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return
    wsRef.current.send(JSON.stringify({ content: draft }))
    setMessages((prev) => [
      ...prev,
      { user_id: currentUserId, username: 'You', content: draft, sent_at: new Date().toISOString() },
    ])
    setDraft('')
  }

  async function handleExtend() {
    setActionError('')
    try {
      const { data } = await api.post(`/rooms/${roomId}/extend`)
      setRoom((prev) => ({ ...prev, timer_ends_at: data.timer_ends_at }))
    } catch (err) {
      setActionError(err.response?.data?.message || 'Could not extend the room.')
    }
  }

  async function handleClose() {
    if (!window.confirm('Close this study room for everyone?')) return
    setActionError('')
    try {
      await api.post(`/rooms/${roomId}/close`)
      setRoom((prev) => ({ ...prev, status: 'closed' }))
      forgetRoom(Number(roomId))
    } catch (err) {
      setActionError(err.response?.data?.message || 'Could not close the room.')
    }
  }

  async function handleKick(userId) {
    if (!window.confirm('Remove this member from the room?')) return
    setActionError('')
    try {
      await api.post(`/rooms/${roomId}/kick`, { user_id: userId })
      setRoom((prev) => ({ ...prev, members: prev.members.filter((m) => m.user_id !== userId) }))
    } catch (err) {
      setActionError(err.response?.data?.message || 'Could not remove that member.')
    }
  }

  async function handleConfirm(sessionOccurred) {
    try {
      const { data } = await api.post(`/help-requests/${room.help_request_id}/confirm`, {
        session_occurred: sessionOccurred,
      })
      setConfirmPending(false)
      setConfirmResult(data.points_awarded)
    } catch (err) {
      window.alert(err.response?.data?.message || 'Could not confirm the session.')
    }
  }

  const loading = loadedRoomId !== roomId

  if (loading) {
    return (
      <section className="room-detail">
        <p className="room-detail-placeholder">Loading study room…</p>
      </section>
    )
  }

  if (loadFailed) {
    return (
      <section className="room-detail">
        <p className="room-detail-placeholder">Room not found, or you're not a member.</p>
      </section>
    )
  }

  const isRequester = room.requester_id === currentUserId
  const remainingMs = new Date(room.timer_ends_at).getTime() - now

  return (
    <section className="room-detail">
      <h1>Study room #{room.room_id}</h1>
      <div className="room-detail-meta">
        <span className={`room-detail-status room-detail-status-${room.status}`}>{room.status}</span>
        {room.status === 'active' && <span>{formatCountdown(remainingMs)} left</span>}
      </div>

      {actionError && <p className="room-detail-error">{actionError}</p>}

      {isRequester && room.status === 'active' && (
        <div className="room-detail-controls">
          <button type="button" onClick={handleExtend}>
            +10 min
          </button>
          <button type="button" onClick={handleClose}>
            Close room
          </button>
        </div>
      )}

      {confirmPending && (
        <div className="room-detail-confirm">
          <p>Did this study session happen?</p>
          <div className="room-detail-confirm-actions">
            <button type="button" onClick={() => handleConfirm(true)}>
              Yes
            </button>
            <button type="button" onClick={() => handleConfirm(false)}>
              No
            </button>
          </div>
        </div>
      )}
      {confirmResult != null && (
        <p className="room-detail-confirm-result">
          {confirmResult > 0
            ? `Session confirmed — ${confirmResult} points awarded.`
            : 'Session marked as not happened.'}
        </p>
      )}

      <div className="widget-label">members</div>
      <div className="room-detail-members">
        {room.members.map((m) => (
          <div className="room-detail-member" key={m.user_id}>
            <span>
              {m.username}
              {m.user_id === room.requester_id ? ' (requester)' : ''}
            </span>
            {isRequester && m.user_id !== currentUserId && (
              <button type="button" onClick={() => handleKick(m.user_id)}>
                Kick
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="widget-label">chat</div>
      {room.status !== 'active' && (
        <p className="room-detail-placeholder">Chat is closed for this room.</p>
      )}
      {room.status === 'active' && (
        <>
          <div className="room-detail-chat">
            {messages.length === 0 && (
              <p className="room-detail-placeholder">
                No messages yet. Chat history isn't saved — messages sent before you joined won't
                appear.
              </p>
            )}
            {messages.map((m, i) => (
              <div className="room-detail-message" key={i}>
                <span className="room-detail-message-author">{m.username}</span>
                <span>{m.content}</span>
              </div>
            ))}
          </div>
          <form className="room-detail-chat-form" onSubmit={handleSend}>
            <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Message…" />
            <button type="submit">Send</button>
          </form>
        </>
      )}
    </section>
  )
}

export default RoomDetail
