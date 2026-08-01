import { useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../../api'
import Modal from '../../components/Modal'
import ReportCard from '../../components/ReportCard'
import { useToast } from '../../components/ToastContext'
import { useUser, useUserReportCard, useNotificationCountsByEntity } from '../../queries'
import { downloadReportCard, printReportCard } from '../../utils/reportCard'
import NotificationCountBadge from '../../components/NotificationCountBadge'
import '../../styles/shared-ui.css'
import './AdminStudentDetail.css'

function ResetPasswordModal({ studentId, onClose, onSuccess }) {
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    setSaving(true)
    try {
      await api.post('/auth/reset-password', {
        user_id: Number(studentId),
        new_password: newPassword,
      })
      onSuccess()
    } catch (err) {
      setError(err.response?.data?.message || 'Could not reset password.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <Modal onClose={onClose}>
      <div className="admin-settings-card-title">Reset student password</div>
      <form className="admin-settings-edit-form" onSubmit={handleSubmit}>
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
            {saving ? 'Saving…' : 'Reset password'}
          </button>
          <button type="button" className="admin-btn-text" onClick={onClose}>
            Cancel
          </button>
        </div>
      </form>
    </Modal>
  )
}

function AdminStudentDetail() {
  const { studentId } = useParams()
  const { showToast } = useToast()
  const [showResetModal, setShowResetModal] = useState(false)
  const { data: student = null, isError: studentFailed } = useUser(studentId)
  const { data: reportCard = null, isError: reportCardFailed } = useUserReportCard(studentId)
  const notifCounts = useNotificationCountsByEntity()
  const notFound = studentFailed || reportCardFailed

  if (notFound) {
    return (
      <div className="admin-student-detail">
        <p className="admin-empty-card">Student not found.</p>
      </div>
    )
  }

  if (!student || !reportCard) {
    return (
      <div className="admin-student-detail">
        <p className="admin-empty-card">Loading…</p>
      </div>
    )
  }

  return (
    <div className="admin-student-detail">
      <h1 className="admin-page-h1">
        {student.full_name}
        <NotificationCountBadge
          count={notifCounts[`student:${studentId}`]}
          className="notification-count-badge-inline"
        />
      </h1>
      <p className="admin-page-subtitle">Sections, assignments, and quests for this student</p>

      <div className="admin-student-actions">
        <button
          type="button"
          className="admin-btn-secondary"
          onClick={() => downloadReportCard(student, reportCard)}
        >
          Download PDF
        </button>
        <button
          type="button"
          className="admin-btn-secondary"
          onClick={() => printReportCard(student, reportCard)}
        >
          Print
        </button>
        <button type="button" className="admin-btn-secondary" onClick={() => setShowResetModal(true)}>
          Reset password
        </button>
      </div>

      <ReportCard reportCard={reportCard} />

      {showResetModal && (
        <ResetPasswordModal
          studentId={studentId}
          onClose={() => setShowResetModal(false)}
          onSuccess={() => {
            setShowResetModal(false)
            showToast('Password reset')
          }}
        />
      )}
    </div>
  )
}

export default AdminStudentDetail
