import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import { extractErrorMessage } from '../lib/apiClient'

export default function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await login(username, password)
      navigate(location.state?.from?.pathname || '/sections', { replace: true })
    } catch (err) {
      setError(extractErrorMessage(err, 'Invalid username or password.'))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <h1>Welcome back</h1>
        <p className="page-subtitle">Log in to open your bulletin board and study rooms.</p>

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          <div className="form-field">
            <label htmlFor="username">Username</label>
            <input id="username" value={username} onChange={(e) => setUsername(e.target.value)} required autoFocus />
          </div>
          <div className="form-field">
            <label htmlFor="password">Password</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={submitting} style={{ width: '100%' }}>
            {submitting ? 'Logging in…' : 'Log in'}
          </button>
        </form>

        <div className="auth-switch">
          New here? <Link to="/register">Create an account</Link>
        </div>
      </div>
    </div>
  )
}
