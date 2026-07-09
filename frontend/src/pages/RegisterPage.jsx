import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { extractErrorMessage } from '../lib/apiClient'

export default function RegisterPage() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState({ username: '', password: '', schoolCode: '', role: 'student', email: '' })
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const [submitting, setSubmitting] = useState(false)

  function update(field, value) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSuccess('')
    setSubmitting(true)
    try {
      await register(form)
      setSuccess(
        form.role === 'student'
          ? 'Account created. You can log in now.'
          : 'Account created. An admin needs to verify it before you can log in.'
      )
      setTimeout(() => navigate('/login'), 1500)
    } catch (err) {
      setError(extractErrorMessage(err, 'Could not create account.'))
    } finally {
      setSubmitting(false)
    }
  }

  const needsEmail = form.role !== 'student'

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h1>Create account</h1>
        <p className="page-subtitle">Register with your school code.</p>

        {error && <div className="alert alert-error">{error}</div>}
        {success && <div className="alert alert-info">{success}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="username">Username</label>
            <input id="username" value={form.username} onChange={(e) => update('username', e.target.value)} required />
          </div>
          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={form.password}
              onChange={(e) => update('password', e.target.value)}
              required
            />
          </div>
          <div className="form-field">
            <label htmlFor="schoolCode">School code</label>
            <input id="schoolCode" value={form.schoolCode} onChange={(e) => update('schoolCode', e.target.value)} required />
          </div>
          <div className="form-field">
            <label htmlFor="role">Role</label>
            <select id="role" value={form.role} onChange={(e) => update('role', e.target.value)}>
              <option value="student">Student</option>
              <option value="teacher">Teacher</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          {needsEmail && (
            <div className="form-field">
              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={form.email}
                onChange={(e) => update('email', e.target.value)}
                required
              />
            </div>
          )}
          <button className="btn btn-primary" type="submit" disabled={submitting} style={{ width: '100%' }}>
            {submitting ? 'Creating…' : 'Create account'}
          </button>
        </form>

        <div className="auth-switch">
          Already have an account? <Link to="/login">Log in</Link>
        </div>
      </div>
    </div>
  )
}
