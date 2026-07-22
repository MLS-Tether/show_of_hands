import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../api'
import Modal from '../components/Modal'
import { useDialog } from '../components/DialogContext'
import { keys, useHelpRequestsBoard, useSections } from '../queries'
import { forgetRoom, getMyHelpRequestIds, getMyRooms, rememberHelpRequestId, rememberRoom } from '../utils/roomTracking'
import '../styles/shared-ui.css'
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
      <button type="submit" className="admin-btn-primary" disabled={submitting}>
        {submitting ? 'Posting…' : 'Post request'}
      </button>
    </form>
  )
}

function EditRequestForm({ hr, onSaved, onCancel }) {
  const [topic, setTopic] = useState(hr.topic)
  const [description, setDescription] = useState(hr.description || '')
  const [groupSize, setGroupSize] = useState(hr.group_size)
  const [durationMinutes, setDurationMinutes] = useState(hr.duration_minutes)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      const { data } = await api.patch(`/help-requests/${hr.help_request_id}`, {
        topic,
        description: description || null,
        group_size: Number(groupSize),
        duration_minutes: Number(durationMinutes),
      })
      onSaved(data)
    } catch (err) {
      setError(err.response?.data?.message || 'Could not save changes.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form className="bulletin-request-form" onSubmit={handleSubmit}>
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
      <div className="bulletin-request-form-row">
        <button type="submit" className="admin-btn-primary" disabled={submitting}>
          {submitting ? 'Saving…' : 'Save changes'}
        </button>
        <button type="button" className="admin-btn-secondary" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}

function BulletinBoard() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const { confirm, alert } = useDialog()
  const [joiningId, setJoiningId] = useState(null)
  const [closingId, setClosingId] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [droppingId, setDroppingId] = useState(null)
  const [editingRequest, setEditingRequest] = useState(null)

  const { data: sections = null } = useSections()
  const { data: requests = null } = useHelpRequestsBoard()

  useEffect(() => {
    if (!requests) return
    const myHelpRequestIds = getMyHelpRequestIds()
    requests
      .filter((hr) => myHelpRequestIds.includes(hr.help_request_id) && hr.room_id)
      .forEach((hr) => rememberRoom({ room_id: hr.room_id, topic: hr.topic }))
  }, [requests])

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

  async function handleCloseRoom(hr) {
    if (!(await confirm('Close this study room for everyone?'))) return

    setClosingId(hr.help_request_id)
    try {
      await api.post(`/rooms/${hr.room_id}/close`)
      forgetRoom(hr.room_id)
      queryClient.setQueryData(keys.helpRequests(), (prev) =>
        (prev || []).map((r) =>
          r.help_request_id === hr.help_request_id ? { ...r, status: 'closed' } : r
        )
      )
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not close the room.')
    } finally {
      setClosingId(null)
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
      queryClient.setQueryData(keys.helpRequests(), (prev) =>
        (prev || []).map((r) =>
          r.help_request_id === hr.help_request_id ? { ...r, room_id: null, status: 'closed' } : r
        )
      )
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not delete the room.')
    } finally {
      setDeletingId(null)
    }
  }

  async function handleDrop(hr) {
    if (!(await confirm('Delete this help request? This cannot be undone.'))) return

    setDroppingId(hr.help_request_id)
    try {
      await api.post(`/help-requests/${hr.help_request_id}/drop`)
      queryClient.setQueryData(keys.helpRequests(), (prev) =>
        (prev || []).filter((r) => r.help_request_id !== hr.help_request_id)
      )
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not delete this help request.')
    } finally {
      setDroppingId(null)
    }
  }

  const loading = sections === null || requests === null
  const myHelpRequestIds = getMyHelpRequestIds()
  const myRoomIds = getMyRooms().map((r) => r.room_id)

  return (
    <section className="bulletin-board">
      <h1 className="admin-page-h1">Bulletin board</h1>

      {!loading && sections.length === 0 && (
        <p className="admin-empty-card">Join a section to see help requests.</p>
      )}

      {loading && <p className="admin-empty-card">Loading help requests…</p>}

      {!loading && sections.length > 0 && (
        <>
          <div className="widget-label">post a help request</div>
          <NewRequestForm
            sections={sections}
            onCreated={(hr) =>
              queryClient.setQueryData(keys.helpRequests(), (prev) => [hr, ...(prev || [])])
            }
          />

          <h2 className="bulletin-board-subheading">Help requests</h2>
          {requests.length === 0 && (
            <p className="admin-empty-card">No help requests yet.</p>
          )}
          {requests.length > 0 && (
            <div className="bulletin-request-list">
              {requests.map((hr) => {
                const isMine = myHelpRequestIds.includes(hr.help_request_id)
                const canJoin = hr.status === 'open' && hr.current_size < hr.group_size && !isMine
                const canOpen = hr.room_id && (isMine || myRoomIds.includes(hr.room_id))
                const canManageUnclaimed = isMine && !hr.room_id && hr.status === 'open' && hr.current_size <= 1
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
                        <button
                          type="button"
                          className="admin-btn-secondary"
                          onClick={() => navigate(`/rooms/${hr.room_id}`)}
                        >
                          Open room
                        </button>
                      )}
                      {canJoin && (
                        <button
                          type="button"
                          className="admin-btn-primary"
                          disabled={joiningId === hr.help_request_id}
                          onClick={() => handleJoin(hr)}
                        >
                          {joiningId === hr.help_request_id ? 'Joining…' : 'Join'}
                        </button>
                      )}
                      {isMine && hr.room_id && hr.status === 'active' && (
                        <button
                          type="button"
                          className="admin-btn-secondary"
                          disabled={closingId === hr.help_request_id}
                          onClick={() => handleCloseRoom(hr)}
                        >
                          {closingId === hr.help_request_id ? 'Closing…' : 'Close room'}
                        </button>
                      )}
                      {isMine && hr.room_id && (
                        <button
                          type="button"
                          className="admin-btn-danger"
                          disabled={deletingId === hr.help_request_id}
                          onClick={() => handleDelete(hr)}
                        >
                          {deletingId === hr.help_request_id ? 'Deleting…' : 'Delete room'}
                        </button>
                      )}
                      {canManageUnclaimed && (
                        <>
                          <button
                            type="button"
                            className="admin-btn-secondary"
                            onClick={() => setEditingRequest(hr)}
                          >
                            Edit
                          </button>
                          <button
                            type="button"
                            className="admin-btn-danger"
                            disabled={droppingId === hr.help_request_id}
                            onClick={() => handleDrop(hr)}
                          >
                            {droppingId === hr.help_request_id ? 'Deleting…' : 'Delete request'}
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          )}
        </>
      )}

      {editingRequest && (
        <Modal onClose={() => setEditingRequest(null)}>
          <h2 className="bulletin-board-subheading">Edit help request</h2>
          <EditRequestForm
            hr={editingRequest}
            onCancel={() => setEditingRequest(null)}
            onSaved={(updated) => {
              queryClient.setQueryData(keys.helpRequests(), (prev) =>
                (prev || []).map((r) =>
                  r.help_request_id === updated.help_request_id ? { ...r, ...updated } : r
                )
              )
              setEditingRequest(null)
            }}
          />
        </Modal>
      )}
    </section>
  )
}

export default BulletinBoard
