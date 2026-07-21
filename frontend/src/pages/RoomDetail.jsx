import DailyIframe from '@daily-co/daily-js'
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../api'
import { useDialog } from '../components/DialogContext'
import { useAutoRefresh } from '../utils/autoRefresh'
import { forgetRoom, rememberRoom } from '../utils/roomTracking'
import { wsUrlWithFreshToken } from '../utils/ws'
import '../styles/shared-ui.css'
import './RoomDetail.css'

const STATUS_BADGE_CLASS = {
  active: 'status-active',
  closed: 'status-archived',
  expired: 'status-archived',
}

function formatCountdown(ms) {
  if (ms <= 0) return '0:00'
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

function RoomDetail() {
  const { roomId } = useParams()
  const navigate = useNavigate()
  const { confirm, alert } = useDialog()
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
  const [connectionStatus, setConnectionStatus] = useState('connecting')
  const [videoJoined, setVideoJoined] = useState(false)
  const [videoLoading, setVideoLoading] = useState(false)
  const [videoError, setVideoError] = useState('')
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const reconnectAttemptRef = useRef(0)
  const closingIntentionallyRef = useRef(false)
  const videoContainerRef = useRef(null)
  const callFrameRef = useRef(null)

  const loadRoom = useCallback(() => {
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

  useEffect(() => loadRoom(), [loadRoom])
  // Kicks/leaves/status changes from other members aren't pushed in real
  // time (only chat is) — keep this one on a shorter interval than the app
  // default so room state doesn't feel stale for minutes at a time.
  useAutoRefresh(loadRoom, 20000)

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(timer)
  }, [])

  const activeRoomId = room?.status === 'active' ? room.room_id : null

  useEffect(() => {
    if (!activeRoomId) return
    closingIntentionallyRef.current = false
    reconnectAttemptRef.current = 0
    let cancelled = false

    function connect() {
      setConnectionStatus('connecting')
      wsUrlWithFreshToken(`/rooms/${activeRoomId}/chat`).then((url) => {
        if (cancelled) return
        const ws = new WebSocket(url)
        wsRef.current = ws

        ws.onopen = () => {
          reconnectAttemptRef.current = 0
          setConnectionStatus('open')
        }

        ws.onmessage = (event) => {
          const data = JSON.parse(event.data)
          if (data.type === 'session_confirmation_required') {
            setConfirmPending(true)
            return
          }
          if (data.type === 'room_deleted') {
            forgetRoom(Number(roomId))
            alert('This room was deleted by its creator.').then(() => navigate('/study-rooms'))
            return
          }
          if (data.type === 'timer_extended') {
            setRoom((prev) => (prev ? { ...prev, timer_ends_at: data.timer_ends_at } : prev))
            return
          }
          setMessages((prev) => [...prev, data])
        }

        ws.onerror = () => {
          setConnectionStatus('closed')
        }

        ws.onclose = () => {
          setConnectionStatus('closed')
          if (closingIntentionallyRef.current) return
          const attempt = reconnectAttemptRef.current + 1
          reconnectAttemptRef.current = attempt
          const delay = Math.min(1000 * 2 ** (attempt - 1), 10000)
          reconnectTimeoutRef.current = setTimeout(connect, delay)
        }
      })
    }

    connect()

    return () => {
      closingIntentionallyRef.current = true
      clearTimeout(reconnectTimeoutRef.current)
      cancelled = true
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [activeRoomId, roomId, navigate, alert])

  const leaveVideoCall = useCallback(() => {
    callFrameRef.current?.destroy().catch(() => {})
    callFrameRef.current = null
    setVideoJoined(false)
  }, [])

  // Room going inactive (closed/deleted/navigated away) should always take
  // the call down with it — nothing else tears down the iframe otherwise.
  // The cleanup fires both on unmount and whenever activeRoomId changes
  // (e.g. active -> null when the room closes), so no need to also call
  // this from the effect body itself.
  useEffect(() => {
    return () => leaveVideoCall()
  }, [activeRoomId, leaveVideoCall])

  async function handleJoinVideo() {
    setVideoError('')
    setVideoLoading(true)
    try {
      const { data } = await api.post(`/rooms/${roomId}/video-token`)
      const callFrame = DailyIframe.createFrame(videoContainerRef.current, {
        showLeaveButton: true,
        iframeStyle: { width: '100%', height: '100%', border: '0' },
      })
      callFrame.on('left-meeting', leaveVideoCall)
      callFrameRef.current = callFrame
      await callFrame.join({ url: data.room_url, token: data.token })
      setVideoJoined(true)
    } catch (err) {
      setVideoError(err.response?.data?.message || 'Could not join the video call.')
      callFrameRef.current?.destroy().catch(() => {})
      callFrameRef.current = null
    } finally {
      setVideoLoading(false)
    }
  }

  function handleSend(e) {
    e.preventDefault()
    if (!draft.trim()) return
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setActionError("Not connected to the chat right now — reconnecting, please try again in a moment.")
      return
    }
    setActionError('')
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
    if (!(await confirm('Close this study room for everyone?'))) return
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
    if (!(await confirm('Remove this member from the room?'))) return
    setActionError('')
    try {
      await api.post(`/rooms/${roomId}/kick`, { user_id: userId })
      setRoom((prev) => ({ ...prev, members: prev.members.filter((m) => m.user_id !== userId) }))
    } catch (err) {
      setActionError(err.response?.data?.message || 'Could not remove that member.')
    }
  }

  async function handleDelete() {
    const warning =
      room.status === 'active'
        ? 'Delete this room? Everyone still connected will be disconnected immediately. This cannot be undone.'
        : 'Delete this room? This cannot be undone.'
    if (!(await confirm(warning))) return
    setActionError('')
    try {
      await api.delete(`/rooms/${roomId}`)
      forgetRoom(Number(roomId))
      navigate('/study-rooms')
    } catch (err) {
      setActionError(err.response?.data?.message || 'Could not delete the room.')
    }
  }

  async function handleLeave() {
    if (!(await confirm('Leave this study room?'))) return
    setActionError('')
    try {
      await api.post(`/rooms/${roomId}/leave`)
      wsRef.current?.close()
      forgetRoom(Number(roomId))
      navigate('/study-rooms')
    } catch (err) {
      setActionError(err.response?.data?.message || 'Could not leave the room.')
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
      await alert(err.response?.data?.message || 'Could not confirm the session.')
    }
  }

  const loading = loadedRoomId !== roomId

  if (loading) {
    return (
      <section className="room-detail">
        <p className="admin-empty-card">Loading study room…</p>
      </section>
    )
  }

  if (loadFailed) {
    return (
      <section className="room-detail">
        <p className="admin-empty-card">Room not found, or you're not a member.</p>
      </section>
    )
  }

  const isRequester = room.requester_id === currentUserId
  const remainingMs = new Date(room.timer_ends_at).getTime() - now

  return (
    <section className="room-detail">
      <h1 className="admin-page-h1">Study room #{room.room_id}</h1>
      <div className="room-detail-meta">
        <span className={`admin-status-badge ${STATUS_BADGE_CLASS[room.status] || ''}`}>
          {room.status}
        </span>
        {room.status === 'active' && <span>{formatCountdown(remainingMs)} left</span>}
      </div>

      {actionError && <p className="room-detail-error">{actionError}</p>}

      <div className="room-detail-controls">
        {isRequester && room.status === 'active' && (
          <>
            <button type="button" className="admin-btn-secondary" onClick={handleExtend}>
              +10 min
            </button>
            <button type="button" className="admin-btn-secondary" onClick={handleClose}>
              Close room
            </button>
          </>
        )}
        {isRequester && (
          <button type="button" className="admin-btn-danger" onClick={handleDelete}>
            Delete room
          </button>
        )}
        <button type="button" className="admin-btn-secondary" onClick={handleLeave}>
          Leave room
        </button>
      </div>

      {confirmPending && (
        <div className="room-detail-confirm">
          <p>Did this study session happen?</p>
          <div className="room-detail-confirm-actions">
            <button type="button" className="admin-btn-primary" onClick={() => handleConfirm(true)}>
              Yes
            </button>
            <button type="button" className="admin-btn-secondary" onClick={() => handleConfirm(false)}>
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
              <button type="button" className="admin-btn-text" onClick={() => handleKick(m.user_id)}>
                Kick
              </button>
            )}
          </div>
        ))}
      </div>

      {room.status === 'active' && room.daily_room_url && (
        <>
          <div className="widget-label">video call</div>
          {videoError && <p className="room-detail-error">{videoError}</p>}
          {!videoJoined && (
            <button
              type="button"
              className="admin-btn-secondary room-detail-video-join-btn"
              disabled={videoLoading}
              onClick={handleJoinVideo}
            >
              {videoLoading ? 'Joining…' : 'Join video call'}
            </button>
          )}
          <div
            ref={videoContainerRef}
            className="room-detail-video"
            style={{ display: videoJoined ? 'block' : 'none' }}
          />
        </>
      )}

      <div className="widget-label">chat</div>
      {room.status !== 'active' && (
        <p className="admin-empty-card">Chat is closed for this room.</p>
      )}
      {room.status === 'active' && (
        <>
          {connectionStatus !== 'open' && (
            <p className="room-detail-connection-status">
              {connectionStatus === 'connecting' ? 'Connecting to chat…' : 'Disconnected — reconnecting…'}
            </p>
          )}
          <div className="room-detail-chat">
            {messages.length === 0 && <p className="admin-empty-card">No messages yet.</p>}
            {messages.map((m, i) => (
              <div className="room-detail-message" key={i}>
                <span className="room-detail-message-author">{m.username}</span>
                <span>{m.content}</span>
              </div>
            ))}
          </div>
          <form className="room-detail-chat-form" onSubmit={handleSend}>
            <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Message…" />
            <button type="submit" className="admin-btn-primary">
              Send
            </button>
          </form>
        </>
      )}
    </section>
  )
}

export default RoomDetail
