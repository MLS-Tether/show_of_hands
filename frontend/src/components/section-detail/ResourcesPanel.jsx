import { useCallback, useEffect, useState } from 'react'
import api from '../../api'
import { useDialog } from '../DialogContext'

function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

function ResourcesPanel({ sectionId }) {
  const { confirm, alert } = useDialog()
  const [resources, setResources] = useState(null)
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState(null)
  const [title, setTitle] = useState('')
  const [url, setUrl] = useState('')
  const [description, setDescription] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get(`/sections/${sectionId}/resources`)
      .then(({ data }) => {
        if (!cancelled) setResources(data)
      })
      .catch(() => {
        if (!cancelled) setResources((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [sectionId])

  useEffect(() => load(), [load])

  function resetForm() {
    setTitle('')
    setUrl('')
    setDescription('')
    setEditingId(null)
    setShowForm(false)
    setError('')
  }

  function startEdit(resource) {
    setEditingId(resource.resource_id)
    setTitle(resource.title)
    setUrl(resource.url)
    setDescription(resource.description || '')
    setError('')
    setShowForm(true)
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    const body = { title, url, description: description || null }
    try {
      if (editingId) {
        await api.patch(`/resources/${editingId}`, body)
      } else {
        await api.post(`/sections/${sectionId}/resources`, body)
      }
      resetForm()
      load()
    } catch (err) {
      setError(err.response?.data?.message || 'Could not save resource.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(resource) {
    const ok = await confirm(`Delete "${resource.title}"?`)
    if (!ok) return
    setDeletingId(resource.resource_id)
    try {
      await api.delete(`/resources/${resource.resource_id}`)
      load()
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not delete resource.')
    } finally {
      setDeletingId(null)
    }
  }

  const loading = resources === null

  return (
    <div>
      <div className="widget-label">resources</div>

      {!showForm && (
        <button
          type="button"
          className="teacher-panel-button teacher-panel-add-toggle"
          onClick={() => setShowForm(true)}
        >
          + new resource
        </button>
      )}

      {showForm && (
        <form className="teacher-panel-form" onSubmit={handleSubmit}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Link
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://…"
              required
            />
          </label>
          <label>
            Description (optional — tell students where this leads)
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} />
          </label>
          {error && <p className="teacher-panel-error">{error}</p>}
          <div className="teacher-panel-form-actions">
            <button type="button" className="teacher-panel-button" onClick={resetForm}>
              Cancel
            </button>
            <button type="submit" className="teacher-panel-button" disabled={submitting}>
              {submitting ? 'Saving…' : editingId ? 'Save' : 'Post'}
            </button>
          </div>
        </form>
      )}

      {loading && <p className="teacher-panel-placeholder">Loading resources…</p>}
      {!loading && resources.length === 0 && (
        <p className="teacher-panel-placeholder">No resources posted yet.</p>
      )}
      {!loading && resources.length > 0 && (
        <div className="teacher-panel-list">
          {resources.map((r) => (
            <div className="teacher-panel-row" key={r.resource_id}>
              <span>
                <a href={r.url} target="_blank" rel="noopener noreferrer">
                  {r.title}
                </a>{' '}
                <span className="teacher-panel-row-sub">{domainOf(r.url)}</span>
                {r.description && <div className="teacher-panel-row-sub">{r.description}</div>}
              </span>
              <span>
                <button type="button" className="teacher-panel-button" onClick={() => startEdit(r)}>
                  Edit
                </button>{' '}
                <button
                  type="button"
                  className="teacher-panel-button"
                  disabled={deletingId === r.resource_id}
                  onClick={() => handleDelete(r)}
                >
                  {deletingId === r.resource_id ? 'Deleting…' : 'Delete'}
                </button>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default ResourcesPanel
