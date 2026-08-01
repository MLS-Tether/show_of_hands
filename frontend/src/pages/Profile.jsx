import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api, { mediaUrl } from '../api'
import BadgesSection from '../components/BadgesSection'
import CharacterAvatar from '../components/CharacterAvatar'
import Modal from '../components/Modal'
import { useDialog } from '../components/DialogContext'
import { useToast } from '../components/ToastContext'
import { keys, useInventory, useSchool, useShopItems, useUser } from '../queries'
import { getUserId } from '../utils/auth'
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

function ChangePasswordModal({ onClose, onSuccess }) {
  const [oldPassword, setOldPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) {
      setError('New passwords do not match.')
      return
    }
    setSaving(true)
    try {
      await api.post('/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.message || 'Could not change password.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal onClose={onClose}>
      <div className="admin-settings-card-title">Change password</div>
      <form className="admin-settings-edit-form" onSubmit={handleSubmit}>
        <label className="admin-settings-field">
          Current password
          <input
            type="password"
            value={oldPassword}
            onChange={(e) => setOldPassword(e.target.value)}
            required
          />
        </label>
        <label className="admin-settings-field">
          New password
          <input
            type="password"
            minLength={8}
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            required
          />
        </label>
        <label className="admin-settings-field">
          Confirm new password
          <input
            type="password"
            minLength={8}
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            required
          />
        </label>
        {error && (
          <p className="modal-form-error" role="alert">
            {error}
          </p>
        )}
        <div className="admin-settings-edit-actions">
          <button type="submit" className="admin-btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save'}
          </button>
          <button type="button" className="admin-btn-text" onClick={onClose}>
            Cancel
          </button>
        </div>
      </form>
    </Modal>
  )
}

function Profile() {
  const { showToast } = useToast()
  const { confirm } = useDialog()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const userId = getUserId()
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ username: '' })
  const [saving, setSaving] = useState(false)
  const [uploadingPicture, setUploadingPicture] = useState(false)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [deleting, setDeleting] = useState(false)
  const [featuredBadgePending, setFeaturedBadgePending] = useState(null)
  const fileInputRef = useRef(null)

  const { data: user = null, isError: failed } = useUser(userId)
  const { data: school = null } = useSchool()
  const { data: inventory = [] } = useInventory(userId, { enabled: user?.role === 'student' })
  const { data: badges = [] } = useShopItems('badge', { enabled: user?.role === 'student' })

  const equippedAvatarBase = inventory.find((row) => row.item.item_type === 'avatar_base' && row.is_equipped)?.item
  const equippedAccessory = inventory.find((row) => row.item.item_type === 'avatar_accessory' && row.is_equipped)?.item
  const equippedBadges = inventory
    .filter((row) => row.item.item_type === 'badge' && row.is_equipped)
    .map((row) => row.item)

  async function setFeaturedBadge(itemId) {
    setFeaturedBadgePending(itemId)
    try {
      const { data } = await api.patch('/users/me/featured-badge', { item_id: itemId })
      queryClient.setQueryData(keys.user(userId), data)
    } catch (err) {
      showToast(err.response?.data?.message || 'Could not update featured badge.')
    } finally {
      setFeaturedBadgePending(null)
    }
  }

  function startEditing() {
    setForm({ username: user.username })
    setEditing(true)
  }

  async function saveProfile() {
    setSaving(true)
    try {
      const { data } = await api.patch('/users/me', {
        username: form.username.trim(),
      })
      queryClient.setQueryData(keys.user(userId), data)
      setEditing(false)
      showToast('Profile updated')
    } catch (err) {
      showToast(err.response?.data?.message || 'Could not update profile.')
    } finally {
      setSaving(false)
    }
  }

  async function handleResetPasswordClick() {
    const ok = await confirm(
      user.role === 'student'
        ? "Are you sure you want to request a password reset? Your school admin will be notified."
        : 'Are you sure you want to reset your password?'
    )
    if (!ok) return

    if (user.role === 'student') {
      try {
        await api.post('/users/me/request-password-reset')
        showToast('Your admin has been notified.')
      } catch (err) {
        showToast(err.response?.data?.message || 'Could not send request.')
      }
    } else {
      setShowPasswordModal(true)
    }
  }

  async function handleDeleteAccountClick() {
    const ok1 = await confirm('Are you sure you want to delete your account?')
    if (!ok1) return
    const ok2 = await confirm(
      'This cannot be undone. Are you really sure you want to permanently delete your account?'
    )
    if (!ok2) return

    setDeleting(true)
    try {
      await api.delete('/users/me')
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user_id')
      localStorage.removeItem('role')
      navigate('/auth')
    } catch (err) {
      showToast(err.response?.data?.message || 'Could not delete account.')
      setDeleting(false)
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
      queryClient.setQueryData(keys.user(userId), (prev) =>
        prev ? { ...prev, profile_picture_url: data.profile_picture_url } : prev
      )
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
      queryClient.setQueryData(keys.user(userId), (prev) => (prev ? { ...prev, profile_picture_url: null } : prev))
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
      <div className="profile-page-header">
        <h1 className="admin-page-h1">My profile</h1>
        {user.featured_badge && (
          <div className="profile-featured-badge">
            <img src={user.featured_badge.image_url} alt="" />
            <span>{user.featured_badge.name}</span>
          </div>
        )}
      </div>

      <div className="profile-sections">
        {user.role === 'student' && (
          <div>
            <div className="profile-section-label-row">
              <div className="widget-label">my character</div>
              <button
                type="button"
                className="admin-btn-text"
                onClick={() => navigate('/inventory')}
              >
                Customize
              </button>
            </div>
            <div className="profile-card profile-character-card">
              <CharacterAvatar
                avatarBase={equippedAvatarBase}
                avatarAccessory={equippedAccessory}
                badges={equippedBadges}
              />
            </div>
          </div>
        )}

        {user.role === 'student' && (
          <div>
            <div className="widget-label">badges</div>
            <BadgesSection
              badges={badges}
              featuredItemId={user.featured_badge?.item_id ?? null}
              pendingId={featuredBadgePending}
              onSetFeatured={setFeaturedBadge}
              onClearFeatured={() => setFeaturedBadge(null)}
            />
          </div>
        )}

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
                <p className="profile-picture-hint">
                  Your full name can't be changed here — contact an admin if it needs fixing.
                </p>
                <div className="admin-settings-edit-actions">
                  <button
                    type="button"
                    className="admin-btn-primary"
                    disabled={saving || !form.username.trim()}
                    onClick={saveProfile}
                  >
                    Save
                  </button>
                  <button type="button" className="admin-btn-text" onClick={() => setEditing(false)}>
                    Cancel
                  </button>
                  <button type="button" className="admin-btn-danger" onClick={handleResetPasswordClick}>
                    Reset password
                  </button>
                  <button
                    type="button"
                    className="admin-btn-danger"
                    disabled={deleting}
                    onClick={handleDeleteAccountClick}
                  >
                    {deleting ? 'Deleting…' : 'Delete account'}
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>

        {(user.role === 'teacher' || user.role === 'admin') && (
          <div>
            <div className="widget-label">password</div>
            <div className="profile-card">
              <div className="profile-row">
                <span className="profile-row-label">Password</span>
                <button
                  type="button"
                  className="admin-btn-text"
                  onClick={() => setShowPasswordModal(true)}
                >
                  Change password
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {showPasswordModal && (
        <ChangePasswordModal
          onClose={() => setShowPasswordModal(false)}
          onSuccess={() => {
            setShowPasswordModal(false)
            showToast('Password changed')
          }}
        />
      )}

    </section>
  )
}

export default Profile
