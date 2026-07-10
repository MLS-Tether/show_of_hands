import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'

const ROLES = ['student', 'teacher', 'admin']

function storeSession(data) {
  localStorage.setItem('access_token', data.access_token)
  localStorage.setItem('refresh_token', data.refresh_token)
  localStorage.setItem('user_id', data.user_id)
  localStorage.setItem('role', data.role)
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
      navigate('/dashboard')
    } catch (err) {
      setError(err.response?.data?.message || 'Login failed.')
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      <label>
        Username
        <input value={username} onChange={(e) => setUsername(e.target.value)} required />
      </label>
      <label>
        Password
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </label>
      {error && <p role="alert">{error}</p>}
      <button type="submit">Log in</button>
    </form>
  )
}

function RegisterForm({ onPendingVerification }) {
  const navigate = useNavigate()
  const [role, setRole] = useState('student')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [email, setEmail] = useState('')
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
      navigate('/dashboard')
    } catch {
      // Account created but not immediately usable (e.g. teacher/admin pending verification).
      onPendingVerification()
    }
  }

  return (
    <>
      <div role="tablist" aria-label="Role">
        {ROLES.map((r) => (
          <button
            key={r}
            type="button"
            role="tab"
            aria-selected={role === r}
            onClick={() => setRole(r)}
          >
            {r[0].toUpperCase() + r.slice(1)}
          </button>
        ))}
      </div>
      <form onSubmit={handleSubmit}>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <label>
          Email (optional)
          <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          School code
          <input value={schoolCode} onChange={(e) => setSchoolCode(e.target.value)} required />
        </label>
        {error && <p role="alert">{error}</p>}
        <button type="submit">Sign up as {role}</button>
      </form>
    </>
  )
}

function Auth() {
  const [mode, setMode] = useState('login')
  const [pendingVerification, setPendingVerification] = useState(false)

  return (
    <section>
      <h1>{mode === 'login' ? 'Log in' : 'Sign up'}</h1>
      <div role="tablist" aria-label="Auth mode">
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'login'}
          onClick={() => setMode('login')}
        >
          Login
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mode === 'register'}
          onClick={() => setMode('register')}
        >
          Register
        </button>
      </div>
      {mode === 'login' && pendingVerification && (
        <p role="status">Account created. It needs admin verification before you can log in.</p>
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
    </section>
  )
}

export default Auth
