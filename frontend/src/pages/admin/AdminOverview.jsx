import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api'
import { getUserId } from '../../utils/auth'
import { useAutoRefresh } from '../../utils/autoRefresh'
import './AdminOverview.css'

function greeting() {
  const hour = new Date().getHours()
  if (hour < 12) return 'Good morning'
  if (hour < 18) return 'Good afternoon'
  return 'Good evening'
}

function formattedDate() {
  return new Intl.DateTimeFormat('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  }).format(new Date())
}

function AdminOverview() {
  const navigate = useNavigate()
  const [user, setUser] = useState(null)
  const [school, setSchool] = useState(null)
  const [stats, setStats] = useState(null)

  const load = useCallback(() => {
    let cancelled = false
    Promise.all([
      api.get(`/users/${getUserId()}`),
      api.get('/schools/me'),
      api.get('/users'),
      api.get('/class-requests'),
      api.get('/sections', { params: { scope: 'all' } }),
    ])
      .then(([userRes, schoolRes, usersRes, classRequestsRes, sectionsRes]) => {
        if (cancelled) return
        setUser(userRes.data)
        setSchool(schoolRes.data)

        const pendingSignups = usersRes.data.filter(
          (u) => u.role !== 'student' && !u.is_verified
        ).length
        const pendingClassRequests = classRequestsRes.data.filter(
          (r) => r.status === 'pending'
        ).length
        const activeSections = sectionsRes.data.filter((s) => s.status === 'active').length
        const needTeacher = sectionsRes.data.filter(
          (s) => s.status === 'pending_reassignment'
        ).length

        setStats({
          pendingSignups,
          pendingClassRequests,
          activeSections,
          needTeacher,
          activeUsers: usersRes.data.length,
        })
      })
      .catch(() => {
        if (!cancelled) setStats((prev) => prev ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  const loading = stats === null

  return (
    <div className="admin-overview">
      <h1 className="admin-overview-greeting">
        {greeting()}
        {user ? `, ${user.username}` : ''}
      </h1>
      <p className="admin-overview-subtitle">
        {formattedDate()}
        {school ? ` · Everything below is scoped to ${school.name}.` : '.'}
      </p>

      {!loading && (
        <>
          <section className="admin-overview-section">
            <div className="admin-section-label">Needs your attention</div>
            <div className="admin-attention-grid">
              <button
                type="button"
                className="admin-attention-card"
                onClick={() => navigate('/admin/inbox?filter=teacher')}
              >
                <div className="admin-attention-number">{stats.pendingSignups}</div>
                <div className="admin-attention-link">Review →</div>
                <div className="admin-attention-title">Pending signups awaiting verification</div>
                <div className="admin-attention-detail">
                  Teachers &amp; admins can't log in until approved
                </div>
              </button>
              <button
                type="button"
                className="admin-attention-card"
                onClick={() => navigate('/admin/inbox?filter=class')}
              >
                <div className="admin-attention-number">{stats.pendingClassRequests}</div>
                <div className="admin-attention-link">Review →</div>
                <div className="admin-attention-title">Class requests for the course catalog</div>
                <div className="admin-attention-detail">
                  Teachers proposing new courses to add
                </div>
              </button>
            </div>
          </section>

          <section className="admin-overview-section">
            <div className="admin-section-label">School at a glance</div>
            <div className="admin-stats-grid">
              <div className="admin-stat-tile">
                <div className="admin-stat-number">{stats.activeSections}</div>
                <div className="admin-stat-label">Active sections</div>
              </div>
              <div className="admin-stat-tile">
                <div className="admin-stat-number">{stats.activeUsers}</div>
                <div className="admin-stat-label">Active users</div>
              </div>
              <div className="admin-stat-tile">
                <div className="admin-stat-number">{stats.needTeacher}</div>
                <div className="admin-stat-label">Sections need a teacher</div>
              </div>
            </div>
          </section>

          <section className="admin-overview-section">
            <div className="admin-section-label">Quick actions</div>
            <div className="admin-quick-actions-grid">
              <button
                type="button"
                className="admin-quick-action"
                onClick={() => navigate('/admin/sections')}
              >
                <div className="admin-quick-action-title">Manage sections</div>
                <div className="admin-quick-action-desc">
                  Reassign teachers, change status, archive
                </div>
              </button>
              <button
                type="button"
                className="admin-quick-action"
                onClick={() => navigate('/admin/users')}
              >
                <div className="admin-quick-action-title">User directory</div>
                <div className="admin-quick-action-desc">Browse and manage every account</div>
              </button>
              <button
                type="button"
                className="admin-quick-action"
                onClick={() => navigate('/admin/settings')}
              >
                <div className="admin-quick-action-title">School join code</div>
                <div className="admin-quick-action-desc">Reveal or copy the join code</div>
              </button>
              <button
                type="button"
                className="admin-quick-action"
                onClick={() => navigate('/admin/sections')}
              >
                <div className="admin-quick-action-title">Broadcast a message</div>
                <div className="admin-quick-action-desc">Message a section's students</div>
              </button>
            </div>
          </section>
        </>
      )}
    </div>
  )
}

export default AdminOverview
