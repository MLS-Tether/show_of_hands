import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { getSection } from '../api/sections'
import {
  acceptHelpRequest,
  createHelpRequest,
  dropHelpRequest,
  listHelpRequests,
} from '../api/helpRequests'
import { extractErrorMessage } from '../lib/apiClient'
import { isMine, markMine } from '../features/bulletin/myRequests'
import HelpRequestCard from '../features/bulletin/HelpRequestCard'
import CreateHelpRequestForm from '../features/bulletin/CreateHelpRequestForm'

export default function BulletinBoardPage() {
  const { sectionId } = useParams()
  const navigate = useNavigate()

  const [section, setSection] = useState(null)
  const [helpRequests, setHelpRequests] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [formSubmitting, setFormSubmitting] = useState(false)
  const [busyId, setBusyId] = useState(null)

  function loadHelpRequests() {
    return listHelpRequests(sectionId).then(setHelpRequests)
  }

  useEffect(() => {
    setLoading(true)
    setError('')
    Promise.all([getSection(sectionId), loadHelpRequests()])
      .then(([sectionData]) => setSection(sectionData))
      .catch((err) => setError(extractErrorMessage(err, 'Could not load this bulletin board.')))
      .finally(() => setLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sectionId])

  async function handleCreate(payload) {
    setFormSubmitting(true)
    setError('')
    try {
      const created = await createHelpRequest(sectionId, payload)
      markMine(created.help_request_id)
      setShowForm(false)
      await loadHelpRequests()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not post that help request.'))
    } finally {
      setFormSubmitting(false)
    }
  }

  async function handleAccept(helpRequestId) {
    setBusyId(helpRequestId)
    setError('')
    try {
      const result = await acceptHelpRequest(helpRequestId)
      navigate(`/rooms/${result.room_id}`)
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not join that help request.'))
      setBusyId(null)
    }
  }

  async function handleDrop(helpRequestId) {
    setBusyId(helpRequestId)
    setError('')
    try {
      await dropHelpRequest(helpRequestId)
      await loadHelpRequests()
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not drop that help request.'))
    } finally {
      setBusyId(null)
    }
  }

  if (loading) return <p className="page-subtitle">Loading bulletin board…</p>

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Bulletin board{section ? ` · ${section.class_name}` : ''}</h1>
          <p className="page-subtitle">Post a help request, or join one that's open.</p>
        </div>
        {!showForm && (
          <button className="btn btn-primary" onClick={() => setShowForm(true)}>
            + Post a help request
          </button>
        )}
      </div>

      {error && <div className="alert alert-error">{error}</div>}

      {showForm && (
        <CreateHelpRequestForm
          onSubmit={handleCreate}
          onCancel={() => setShowForm(false)}
          submitting={formSubmitting}
        />
      )}

      {helpRequests.length === 0 ? (
        <div className="empty-state">No open help requests right now. Be the first to post one.</div>
      ) : (
        helpRequests.map((hr) => (
          <HelpRequestCard
            key={hr.help_request_id}
            helpRequest={hr}
            mine={isMine(hr.help_request_id)}
            busy={busyId === hr.help_request_id}
            onAccept={handleAccept}
            onDrop={handleDrop}
          />
        ))
      )}
    </div>
  )
}
