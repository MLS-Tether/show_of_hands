import { useCallback, useEffect, useRef, useState } from 'react'
import api, { mediaUrl } from '../api'
import { useToast } from '../components/ToastContext'
import { useAutoRefresh } from '../utils/autoRefresh'
import { initials } from '../utils/format'
import '../styles/shared-ui.css'
import './Profile.css'

const ALLOWED_PICTURE_TYPES = ['image/jpeg', 'image/png']

function formatDate(dateStr) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(dateStr))
}

function Profile() {
  const { showToast } = useToast()
  const [user, setUser] = useState(null)
  const [school, setSchool] = useState(null)
  const [failed, setFailed] = useState(false)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ username: '', full_name: '' })
  const [saving, setSaving] = useState(false)
  const [uploadingPicture, setUploadingPicture] = useState(false)
  const fileInputRef = useRef(null)

  const load = useCallback(() => {
    const userId = localStorage.getItem('user_id')
    if (!userId) return undefined
    let cancelled = false

    api
      .get(`/users/${userId}`)
      .then(({ data }) => {
        if (!cancelled) setUser(data)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })

    api
      .get('/schools/me')
      .then(({ data }) => {
        if (!cancelled) setSchool(data)
      })
      .catch(() => {
        if (!cancelled) setSchool((prev) => prev ?? null)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  function startEditing() {
    setForm({ username: user.username, full_name: user.full_name || '' })
    setEditing(true)
  }

  async function saveProfile() {
    setSaving(true)
    try {
      const { data } = await api.patch('/users/me', {
        username: form.username.trim(),
        full_name: form.full_name.trim(),
      })
      setUser(data)
      setEditing(false)
      showToast('Profile updated')
    } catch (err) {
      showToast(err.response?.data?.message || 'Could not update profile.')
    } finally {
      setSaving(false)
    }
  }

  function handlePictureButtonClick() {
    fileInputRef.current?.click()
  }

  async function handlePictureSelected(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return

    // A fast client-side check for a quicker error — the backend re-validates
    // the actual file bytes regardless, since a content-type/extension is
    // trivial to spoof.
    if (!ALLOWED_PICTURE_TYPES.includes(file.type)) {
      showToast('Only JPEG and PNG images are allowed.')
      return
    }

    setUploadingPicture(true)
    const body = new FormData()
    body.append('file', file)
    try {
      const { data } = await api.post('/users/me/profile-picture', body)
      setUser((prev) => (prev ? { ...prev, profile_picture_url: data.profile_picture_url } : prev))
      showToast('Profile picture updated')
    } catch (err) {
      showToast(err.response?.data?.message || 'Could not upload image.')
    } finally {
      setUploadingPicture(false)
    }
  }

  async function handleRemovePicture() {
    setUploadingPicture(true)
    try {
      await api.delete('/users/me/profile-picture')
      setUser((prev) => (prev ? { ...prev, profile_picture_url: null } : prev))
      showToast('Profile picture removed')
    } catch (err) {
      showToast(err.response?.data?.message || 'Could not remove image.')
    } finally {
      setUploadingPicture(false)
    }
  }

  if (failed) {
    return (
      <section className="profile-page">
        <p className="admin-empty-card">Could not load your profile.</p>
      </section>
    )
  }

  if (!user) {
    return (
      <section className="profile-page">
        <p className="admin-empty-card">Loading profile…</p>
      </section>
    )
  }

  return (
    <section className="profile-page">
      <h1 className="admin-page-h1">My profile</h1>

      <div className="profile-sections">
        <div>
          <div className="widget-label">profile picture</div>
          <div className="profile-card profile-picture-card">
            <div className="profile-picture-avatar">
              {user.profile_picture_url ? (
                <img
                  src={mediaUrl(user.profile_picture_url)}
                  alt=""
                  className="profile-picture-avatar-img"
                />
              ) : (
                initials(user.full_name || user.username)
              )}
            </div>
            <div className="profile-picture-actions">
              <input
                ref={fileInputRef}
                type="file"
                accept="image/png, image/jpeg"
                className="profile-picture-input"
                onChange={handlePictureSelected}
              />
              <button
                type="button"
                className="admin-btn-secondary"
                disabled={uploadingPicture}
                onClick={handlePictureButtonClick}
              >
                {uploadingPicture ? 'Uploading…' : 'Change photo'}
              </button>
              {user.profile_picture_url && (
                <button
                  type="button"
                  className="admin-btn-text"
                  disabled={uploadingPicture}
                  onClick={handleRemovePicture}
                >
                  Remove photo
                </button>
              )}
              <p className="profile-picture-hint">JPEG or PNG, up to 5MB.</p>
            </div>
          </div>
        </div>

        <div>
          <div className="profile-section-label-row">
            <div className="widget-label">account details</div>
            {!editing && (
              <button type="button" className="admin-btn-text" onClick={startEditing}>
                Edit
              </button>
            )}
          </div>
          <div className="profile-card">
            {!editing ? (
              <>
                <div className="profile-row">
                  <span className="profile-row-label">Username</span>
                  <span>{user.username}</span>
                </div>
                <div className="profile-row">
                  <span className="profile-row-label">Full name</span>
                  <span>{user.full_name || '—'}</span>
                </div>
                <div className="profile-row">
                  <span className="profile-row-label">Role</span>
                  <span className="profile-role">{user.role}</span>
                </div>
                <div className="profile-row">
                  <span className="profile-row-label">School</span>
                  <span>{school ? school.name : '—'}</span>
                </div>
                {user.role !== 'teacher' && (
                  <div className="profile-row">
                    <span className="profile-row-label">Total points</span>
                    <span>{user.total_points}</span>
                  </div>
                )}
                <div className="profile-row">
                  <span className="profile-row-label">Member since</span>
                  <span>{formatDate(user.created_at)}</span>
                </div>
              </>
            ) : (
              <div className="admin-settings-edit-form">
                <label className="admin-settings-field">
                  Username
                  <input
                    type="text"
                    maxLength={30}
                    value={form.username}
                    onChange={(e) => setForm((f) => ({ ...f, username: e.target.value }))}
                  />
                </label>
                <label className="admin-settings-field">
                  Full name
                  <input
                    type="text"
                    maxLength={100}
                    value={form.full_name}
                    onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))}
                  />
                </label>
                <div className="admin-settings-edit-actions">
                  <button
                    type="button"
                    className="admin-btn-primary"
                    disabled={saving || !form.username.trim() || !form.full_name.trim()}
                    onClick={saveProfile}
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
      </div>
    </section>
  )
}

export default Profile
