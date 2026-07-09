import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { closeRoom, extendRoom, getRoom, kickMember } from '../api/rooms'
import { confirmHelpRequest } from '../api/helpRequests'
import { extractErrorMessage } from '../lib/apiClient'
import { useRoomSocket } from '../features/rooms/useRoomSocket'
import MembersList from '../features/rooms/MembersList'
import RoomTimer from '../features/rooms/RoomTimer'
import ChatPanel from '../features/rooms/ChatPanel'
import ConfirmSessionModal from '../features/rooms/ConfirmSessionModal'

export default function RoomPage() {
  const { roomId } = useParams()
  const { user } = useAuth()
  const navigate = useNavigate()

  const [room, setRoom] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [extending, setExtending] = useState(false)
  const [busyMemberId, setBusyMemberId] = useState(null)

  const [confirmOpen, setConfirmOpen] = useState(false)
  const [confirmSubmitting, setConfirmSubmitting] = useState(false)
  const [confirmResult, setConfirmResult] = useState(null)
  const [confirmError, setConfirmError] = useState('')

  const refreshRoom = useCallback(() => {
    return getRoom(roomId)
      .then(setRoom)
      .catch((err) => setError(extractErrorMessage(err, 'Could not load this room.')))
  }, [roomId])

  useEffect(() => {
    setLoading(true)
    refreshRoom().finally(() => setLoading(false))
  }, [refreshRoom])

  const isRequester = room && user && room.requester_id === user.user_id
  const roomActive = room?.status === 'active'

  const { messages, connectionStatus, sessionConfirmationRequired, sendMessage } = useRoomSocket({
    roomId,
    enabled: roomActive,
  })

  useEffect(() => {
    if (sessionConfirmationRequired) setConfirmOpen(true)
  }, [sessionConfirmationRequired])

  async function handleExtend() {
    setExtending(true)
    setError('')
    try {
      const updated = await extendRoom(roomId)
      setRoom((r) => ({ ...r, timer_ends_at: updated.timer_ends_at }))
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not extend the timer.'))
    } finally {
      setExtending(false)
    }
  }

  async function handleKick(userId) {
    if (!window.confirm('Remove this member from the room?')) return
    setBusyMemberId(userId)
    setError('')
    try {
      await kickMember(roomId, userId)
      await refreshRoom()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not remove that member.'))
    } finally {
      setBusyMemberId(null)
    }
  }

  async function handleCloseRoom() {
    if (!window.confirm('Close this study room for everyone?')) return
    setError('')
    try {
      await closeRoom(roomId)
      await refreshRoom()
      setConfirmOpen(true)
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not close the room.'))
    }
  }

  async function handleConfirmSession(sessionOccurred) {
    setConfirmSubmitting(true)
    setConfirmError('')
    try {
      const result = await confirmHelpRequest(room.help_request_id, sessionOccurred)
      setConfirmResult(result)
    } catch (err) {
      setConfirmError(extractErrorMessage(err, 'Could not record the session outcome.'))
    } finally {
      setConfirmSubmitting(false)
    }
  }

  function closeModalAndLeave() {
    setConfirmOpen(false)
    navigate('/sections')
  }

  if (loading) return <p className="page-subtitle">Loading room…</p>
  if (error && !room) return <div className="alert alert-error">{error}</div>
  if (!room) return null

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Study room</h1>
          <p className="page-subtitle">
            {room.status === 'active' ? 'Session in progress' : 'This room has closed'}
          </p>
        </div>
        {isRequester && roomActive && (
          <button className="btn btn-danger" onClick={handleCloseRoom}>
            Close room
          </button>
        )}
        {isRequester && !roomActive && (
          <button className="btn btn-secondary" onClick={() => setConfirmOpen(true)}>
            Report session outcome
          </button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16, alignItems: 'start' }}>
        <ChatPanel messages={messages} currentUserId={user.user_id} connectionStatus={connectionStatus} onSend={sendMessage} />

        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <RoomTimer
            timerEndsAt={room.timer_ends_at}
            isRequester={isRequester}
            roomActive={roomActive}
            onExtend={handleExtend}
            extending={extending}
          />
          <MembersList
            members={room.members}
            currentUserId={user.user_id}
            requesterId={room.requester_id}
            isRequester={isRequester}
            roomActive={roomActive}
            busyUserId={busyMemberId}
            onKick={handleKick}
          />
        </div>
      </div>

      <ConfirmSessionModal
        open={confirmOpen}
        submitting={confirmSubmitting}
        result={confirmResult}
        error={confirmError}
        onConfirm={handleConfirmSession}
        onClose={closeModalAndLeave}
      />
    </div>
  )
}
