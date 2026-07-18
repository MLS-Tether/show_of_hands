import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../api'
import { useAutoRefresh } from '../utils/autoRefresh'
import { forgetRoom, getMyRooms } from '../utils/roomTracking'
import '../styles/shared-ui.css'
import './StudyRooms.css'

function StudyRooms() {
  const [rooms, setRooms] = useState(null)

  const load = useCallback(() => {
    let cancelled = false
    const tracked = getMyRooms()
    Promise.allSettled(tracked.map((r) => api.get(`/rooms/${r.room_id}`))).then((results) => {
      if (cancelled) return
      const live = []
      results.forEach((r, i) => {
        if (r.status === 'fulfilled') {
          live.push({ ...tracked[i], ...r.value.data })
        } else {
          forgetRoom(tracked[i].room_id)
        }
      })
      setRooms(live)
    })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  const loading = rooms === null

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
