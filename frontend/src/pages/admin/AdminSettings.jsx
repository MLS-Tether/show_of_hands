import { useCallback, useEffect, useState } from 'react'
import api from '../../api'
import { useToast } from '../../components/ToastContext'
import './admin-shared.css'
import './AdminSettings.css'

function AdminSettings() {
  const { showToast } = useToast()
  const [school, setSchool] = useState(null)
  const [activeUsers, setActiveUsers] = useState(null)
  const [code, setCode] = useState(null)
  const [revealed, setRevealed] = useState(false)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ name: '', district: '', grades: '' })
  const [saving, setSaving] = useState(false)

  const load = useCallback(() => {
    let cancelled = false
    Promise.all([api.get('/schools/me'), api.get('/users')])
      .then(([schoolRes, usersRes]) => {
        if (cancelled) return
        setSchool(schoolRes.data)
        setActiveUsers(usersRes.data.length)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])

  async function toggleReveal() {
    if (!revealed && !code) {
      try {
        const { data } = await api.get('/schools/code')
        setCode(data.school_code)
      } catch {
        showToast("Couldn't load the join code")
        return
      }
    }
    setRevealed((r) => !r)
  }

  async function copyCode() {
    let value = code
    if (!value) {
      try {
        const { data } = await api.get('/schools/code')
        value = data.school_code
        setCode(value)
      } catch {
        showToast("Couldn't load the join code")
        return
      }
    }
    try {
      await navigator.clipboard.writeText(value)
      showToast('Join code copied')
    } catch {
      showToast("Couldn't copy the join code")
    }
  }

  function startEditing() {
    setForm({
      name: school?.name || '',
      district: school?.district || '',
      grades: school?.grades || '',
    })
    setEditing(true)
  }

  async function saveDetails() {
    setSaving(true)
    try {
      const { data } = await api.patch('/schools/me', form)
      setSchool(data)
      setEditing(false)
      showToast('School details saved')
    } catch {
      showToast("Couldn't save school details")
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="admin-settings">
      <h1 className="admin-page-h1">School</h1>
      <p className="admin-page-subtitle">School-level settings.</p>

      <div className="admin-settings-card">
        <div className="admin-settings-card-title">Join code</div>
        <p className="admin-settings-card-desc">
          Share this code with staff to let them join your school. Treat it like a password.
        </p>
        <div className="admin-join-code-row">
          <span className="admin-join-code-chip">
            {revealed && code ? code : '••••–••••–•••'}
          </span>
          <button type="button" className="admin-btn-secondary" onClick={toggleReveal}>
            {revealed ? 'Hide' : 'Reveal'}
          </button>
          <button type="button" className="admin-btn-primary" onClick={copyCode}>
            Copy code
          </button>
        </div>
      </div>

      <div className="admin-settings-card">
        <div className="admin-settings-card-title-row">
          <div className="admin-settings-card-title">School details</div>
          {!editing && (
            <button type="button" className="admin-btn-text" onClick={startEditing}>
              Edit
            </button>
          )}
        </div>

        {!editing ? (
          <>
            <div className="admin-detail-row admin-settings-detail-row">
              <span className="admin-detail-label admin-settings-detail-label">Name</span>
              <span>{school ? school.name : '—'}</span>
            </div>
            <div className="admin-detail-row admin-settings-detail-row">
              <span className="admin-detail-label admin-settings-detail-label">District</span>
              <span>{school?.district || '—'}</span>
            </div>
            <div className="admin-detail-row admin-settings-detail-row">
              <span className="admin-detail-label admin-settings-detail-label">Grades</span>
              <span>{school?.grades || '—'}</span>
            </div>
            <div className="admin-detail-row admin-settings-detail-row">
              <span className="admin-detail-label admin-settings-detail-label">Active users</span>
              <span>{activeUsers ?? '—'}</span>
            </div>
          </>
        ) : (
          <div className="admin-settings-edit-form">
            <label className="admin-settings-field">
              Name
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
              />
            </label>
            <label className="admin-settings-field">
              District
              <input
                type="text"
                value={form.district}
                onChange={(e) => setForm((f) => ({ ...f, district: e.target.value }))}
              />
            </label>
            <label className="admin-settings-field">
              Grades
              <input
                type="text"
                value={form.grades}
                onChange={(e) => setForm((f) => ({ ...f, grades: e.target.value }))}
              />
            </label>
            <div className="admin-settings-edit-actions">
              <button
                type="button"
                className="admin-btn-primary"
                disabled={saving}
                onClick={saveDetails}
              >
                Save
              </button>
              <button type="button" className="admin-btn-text" onClick={() => setEditing(false)}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

export default AdminSettings
