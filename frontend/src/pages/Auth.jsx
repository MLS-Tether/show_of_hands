import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import './Auth.css'

const ROLES = ['student', 'teacher', 'admin']

function storeSession(data) {
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  localStorage.setItem('user_id', data.user_id)
  localStorage.setItem('role', data.role)
}

function homePathForRole(role) {
  return role === 'admin' ? '/admin/overview' : '/dashboard'
}

function LoginForm() {
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      const { data } = await api.post('/auth/login', { username, password })
      storeSession(data)
      navigate(homePathForRole(data.role))
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed.')
    }
  }

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      <label className="auth-field">
        Username
        <input value={username} onChange={(e) => setUsername(e.target.value)} required />
      </label>
      <label className="auth-field">
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      {error && <p className="auth-error" role="alert">{error}</p>}
      <button className="auth-submit" type="submit">Log in</button>
    </form>
  )
}

function RegisterForm({ onPendingVerification }) {
  const navigate = useNavigate()
  const [role, setRole] = useState('student')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
  const [note, setNote] = useState('')
  const [schoolCode, setSchoolCode] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    try {
      await api.post('/auth/register', {
        username,
        password,
        email: email || undefined,
        note: note || undefined,
        school_code: schoolCode,
        role,
      })
    } catch (err) {
      setError(err.response?.data?.message || 'Registration failed.')
      return
    }

    try {
      const { data } = await api.post('/auth/login', { username, password })
      storeSession(data)
      navigate(homePathForRole(data.role))
    } catch {
      // Account created but not immediately usable (e.g. teacher/admin pending verification).
      onPendingVerification()
    }
  }

  return (
    <>
      <div className="auth-role-tabs" role="tablist" aria-label="Role">
        {ROLES.map((r) => (
          <button
            key={r}
            type="button"
            role="tab"
            className="auth-role-tab"
            aria-selected={role === r}
            onClick={() => setRole(r)}
          >
            {r[0].toUpperCase() + r.slice(1)}
          </button>
        ))}
      </div>
      <form className="auth-form" onSubmit={handleSubmit}>
        <label className="auth-field">
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label className="auth-field">
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <label className="auth-field">
          Email (optional)
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        {role !== 'student' && (
          <label className="auth-field">
            Note for the admin (optional)
            <input value={note} onChange={(e) => setNote(e.target.value)} />
          </label>
        )}
        <label className="auth-field">
          School code
          <input value={schoolCode} onChange={(e) => setSchoolCode(e.target.value)} required />
        </label>
        {error && <p className="auth-error" role="alert">{error}</p>}
        <button className="auth-submit" type="submit">Sign up as {role}</button>
      </form>
    </>
  )
}

function Auth() {
  const [mode, setMode] = useState('login')
  const [pendingVerification, setPendingVerification] = useState(false)

  return (
    <section className="auth-page">
      <div className="auth-card">
        <h1 className="auth-h1">{mode === 'login' ? 'Log in' : 'Sign up'}</h1>
        <div className="auth-tabs" role="tablist" aria-label="Auth mode">
          <button
            type="button"
            role="tab"
            className="auth-tab"
            aria-selected={mode === 'login'}
            onClick={() => setMode('login')}
          >
            Login
          </button>
          <button
            type="button"
            role="tab"
            className="auth-tab"
            aria-selected={mode === 'register'}
            onClick={() => setMode('register')}
          >
            Register
          </button>
        </div>
        {mode === 'login' && pendingVerification && (
          <p className="auth-status" role="status">
            Account created. It needs admin verification before you can log in.
          </p>
        )}
        {mode === 'login' ? (
          <LoginForm />
        ) : (
          <RegisterForm
            onPendingVerification={() => {
              setPendingVerification(true)
              setMode('login')
            }}
          />
        )}
      </div>
    </section>
  )
}

export default Auth
