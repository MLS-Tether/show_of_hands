import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import api from '../api'
import { keys } from '../queries'
import { forgetRoom, getMyRooms } from '../utils/roomTracking'
import '../styles/shared-ui.css'
import './StudyRooms.css'

function StudyRooms() {
  const tracked = getMyRooms()

  const results = useQueries({
    queries: tracked.map((r) => ({
      queryKey: keys.room(r.room_id),
      queryFn: () => api.get(`/rooms/${r.room_id}`).then((res) => res.data),
      refetchInterval: 20 * 1000,
    })),
  })

  const erroredRoomIds = results.flatMap((r, i) => (r.isError ? [tracked[i].room_id] : []))

  useEffect(() => {
    erroredRoomIds.forEach((id) => forgetRoom(id))
  }, [erroredRoomIds])

  const loading = results.some((r) => r.isLoading)
  const rooms = loading
    ? null
    : results.flatMap((r, i) => (r.isSuccess ? [{ ...tracked[i], ...r.data }] : []))

  return (
    <section className="study-rooms-page">
      <h1 className="admin-page-h1">Study rooms</h1>
      <p className="study-rooms-intro">
        Rooms open automatically when a help request on the{' '}
        <Link to="/bulletin-board">bulletin board</Link> gets accepted. Rooms you've joined show up
        here.
      </p>

      {loading && <p className="admin-empty-card">Loading your rooms…</p>}
      {!loading && rooms.length === 0 && (
        <p className="admin-empty-card">You're not in any study rooms right now.</p>
      )}
      {!loading && rooms.length > 0 && (
        <div className="study-rooms-list">
          {rooms.map((r) => (
            <Link key={r.room_id} to={`/rooms/${r.room_id}`} className="study-room-row">
              <span className="study-room-row-topic">{r.topic || `Room #${r.room_id}`}</span>
              <span className={`study-room-row-status study-room-row-status-${r.status}`}>
                {r.status}
              </span>
            </Link>
          ))}
        </div>
      )}
    </section>
  )
}

export default StudyRooms
