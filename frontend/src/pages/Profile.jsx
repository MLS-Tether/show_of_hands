import { useCallback, useEffect, useState } from 'react'
import api from '../api'
import { useAutoRefresh } from '../utils/autoRefresh'
import './Profile.css'

function formatDate(dateStr) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'long',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(dateStr))
}

function Profile() {
  const [user, setUser] = useState(null)
  const [school, setSchool] = useState(null)
  const [failed, setFailed] = useState(false)

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

  if (failed) {
    return (
      <section className="profile-page">
        <p className="profile-placeholder">Could not load your profile.</p>
      </section>
    )
  }

  if (!user) {
    return (
      <section className="profile-page">
        <p className="profile-placeholder">Loading profile…</p>
      </section>
    )
  }

  return (
    <section className="profile-page">
      <h1>My profile</h1>
      <div className="profile-card">
        <div className="profile-row">
          <span className="profile-row-label">Username</span>
          <span>{user.username}</span>
        </div>
        <div className="profile-row">
          <span className="profile-row-label">Role</span>
          <span className="profile-role">{user.role}</span>
        </div>
        <div className="profile-row">
          <span className="profile-row-label">School</span>
          <span>{school ? school.name : '—'}</span>
        </div>
        <div className="profile-row">
          <span className="profile-row-label">Total points</span>
          <span>{user.total_points}</span>
        </div>
        <div className="profile-row">
          <span className="profile-row-label">Member since</span>
          <span>{formatDate(user.created_at)}</span>
        </div>
      </div>
    </section>
  )
}

export default Profile
