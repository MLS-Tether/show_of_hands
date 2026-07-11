import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { useDialog } from '../components/DialogProvider'
import { useAutoRefresh } from '../utils/autoRefresh'
import { forgetRoom, getMyHelpRequestIds, getMyRooms, rememberHelpRequestId, rememberRoom } from '../utils/roomTracking'
import './BulletinBoard.css'

const STATUS_LABELS = {
  open: 'Open',
  active: 'Full',
  closed: 'Closed',
  expired: 'Expired',
}

function NewRequestForm({ sections, onCreated }) {
  const [sectionId, setSectionId] = useState(sections[0]?.section_id ?? '')
  const [topic, setTopic] = useState('')
  const [description, setDescription] = useState('')
  const [groupSize, setGroupSize] = useState(2)
  const [durationMinutes, setDurationMinutes] = useState(30)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const { data } = await api.post(`/sections/${sectionId}/help-requests`, {
        topic,
        description: description || null,
        group_size: Number(groupSize),
        duration_minutes: Number(durationMinutes),
      })
      rememberHelpRequestId(data.help_request_id)
      const section = sections.find((s) => s.section_id === Number(sectionId))
      onCreated({ ...data, section_id: Number(sectionId), section_name: section?.class_name })
      setTopic('')
      setDescription('')
      setGroupSize(2)
      setDurationMinutes(30)
    } catch (err) {
      setError(err.response?.data?.message || 'Could not post request.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="bulletin-request-form" onSubmit={handleSubmit}>
      <label className="bulletin-request-form-field">
        Section
        <select value={sectionId} onChange={(e) => setSectionId(e.target.value)} required>
          {sections.map((s) => (
            <option key={s.section_id} value={s.section_id}>
              {s.class_name}
            </option>
          ))}
        </select>
      </label>
      <label className="bulletin-request-form-field">
        Topic
        <input value={topic} onChange={(e) => setTopic(e.target.value)} required />
      </label>
      <label className="bulletin-request-form-field">
        Description (optional)
        <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
      </label>
      <div className="bulletin-request-form-row">
        <label className="bulletin-request-form-field">
          Group size
          <input
            type="number"
            min={2}
            value={groupSize}
            onChange={(e) => setGroupSize(e.target.value)}
            required
          />
        </label>
        <label className="bulletin-request-form-field">
          Duration (minutes)
          <input
            type="number"
            min={5}
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(e.target.value)}
            required
          />
        </label>
      </div>
      {error && <p className="bulletin-request-form-error">{error}</p>}
      <button type="submit" disabled={submitting}>
        {submitting ? 'Posting…' : 'Post request'}
      </button>
    </form>
  )
}

function BulletinBoard() {
  const navigate = useNavigate()
  const { confirm, alert } = useDialog()
  const [sections, setSections] = useState(null)
  const [requests, setRequests] = useState(null)
  const [joiningId, setJoiningId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)

  const loadSections = useCallback(() => {
    let cancelled = false
    api
      .get('/sections')
      .then(({ data }) => {
        if (!cancelled) setSections(data)
      })
      .catch(() => {
        if (!cancelled) setSections((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => loadSections(), [loadSections])
  useAutoRefresh(loadSections)

  useEffect(() => {
    if (!sections) return
    let cancelled = false
    Promise.allSettled(
      sections.map((s) => api.get(`/sections/${s.section_id}/help-requests`))
    ).then((results) => {
      if (cancelled) return
      const myHelpRequestIds = getMyHelpRequestIds()
      const merged = results.flatMap((r, i) => {
        if (r.status !== 'fulfilled') return []
        const section = sections[i]
        return r.value.data.map((hr) => ({
          ...hr,
          section_id: section.section_id,
          section_name: section.class_name,
        }))
      })
      merged
        .filter((hr) => myHelpRequestIds.includes(hr.help_request_id) && hr.room_id)
        .forEach((hr) => rememberRoom({ room_id: hr.room_id, topic: hr.topic }))
      merged.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      setRequests(merged)
    })
    return () => {
      cancelled = true
    }
  }, [sections])

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

  async function handleDelete(hr) {
    const warning =
      hr.status === 'active'
        ? 'Delete this room? Everyone still connected will be disconnected immediately. This cannot be undone.'
        : 'Delete this room? This cannot be undone.'
    if (!(await confirm(warning))) return

    setDeletingId(hr.help_request_id)
    try {
      await api.delete(`/rooms/${hr.room_id}`)
      forgetRoom(hr.room_id)
      setRequests((prev) =>
        prev.map((r) => (r.help_request_id === hr.help_request_id ? { ...r, room_id: null, status: 'closed' } : r))
      )
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not delete the room.')
    } finally {
      setDeletingId(null)
    }
  }

  const loading = sections === null || requests === null
  const myHelpRequestIds = getMyHelpRequestIds()
  const myRoomIds = getMyRooms().map((r) => r.room_id)

  return (
    <section className="bulletin-board">
      <h1>Bulletin board</h1>

      {!loading && sections.length === 0 && (
        <p className="bulletin-board-placeholder">Join a section to see help requests.</p>
      )}

      {loading && <p className="bulletin-board-placeholder">Loading help requests…</p>}

      {!loading && sections.length > 0 && (
        <>
          <div className="widget-label">post a help request</div>
          <NewRequestForm
            sections={sections}
            onCreated={(hr) => setRequests((prev) => [hr, ...(prev || [])])}
          />

          <h2 className="bulletin-board-subheading">Help requests</h2>
          {requests.length === 0 && (
            <p className="bulletin-board-placeholder">No help requests yet.</p>
          )}
          {requests.length > 0 && (
            <div className="bulletin-request-list">
              {requests.map((hr) => {
                const isMine = myHelpRequestIds.includes(hr.help_request_id)
                const canJoin = hr.status === 'open' && hr.current_size < hr.group_size && !isMine
                const canOpen = hr.room_id && (isMine || myRoomIds.includes(hr.room_id))
                return (
                  <div className="bulletin-request-card" key={hr.help_request_id}>
                    <div className="bulletin-request-card-main">
                      <span className="bulletin-request-card-topic">{hr.topic}</span>
                      <span className="bulletin-request-card-section">{hr.section_name}</span>
                    </div>
                    {hr.description && (
                      <p className="bulletin-request-card-description">{hr.description}</p>
                    )}
                    <div className="bulletin-request-card-meta">
                      <span>
                        {hr.current_size}/{hr.group_size} joined
                      </span>
                      <span>{hr.duration_minutes} min</span>
                      <span className={`bulletin-request-status bulletin-request-status-${hr.status}`}>
                        {STATUS_LABELS[hr.status] || hr.status}
                      </span>
                    </div>
                    <div className="bulletin-request-card-actions">
                      {canOpen && (
                        <button type="button" onClick={() => navigate(`/rooms/${hr.room_id}`)}>
                          Open room
                        </button>
                      )}
                      {canJoin && (
                        <button
                          type="button"
                          disabled={joiningId === hr.help_request_id}
                          onClick={() => handleJoin(hr)}
                        >
                          {joiningId === hr.help_request_id ? 'Joining…' : 'Join'}
                        </button>
                      )}
                      {isMine && hr.room_id && (
                        <button
                          type="button"
                          disabled={deletingId === hr.help_request_id}
                          onClick={() => handleDelete(hr)}
                        >
                          {deletingId === hr.help_request_id ? 'Deleting…' : 'Delete room'}
                        </button>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default BulletinBoard
