import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api'
import { useDialog } from '../../components/DialogContext'
import { useToast } from '../../components/ToastContext'
import { useAutoRefresh } from '../../utils/autoRefresh'
import { initials } from '../../utils/format'
import './admin-shared.css'
import './AdminUsers.css'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'student', label: 'Students' },
  { key: 'teacher', label: 'Teachers' },
  { key: 'admin', label: 'Admins' },
]

const ROLE_BADGE = {
  student: { className: 'role-student' },
  teacher: { className: 'role-teacher' },
  admin: { className: 'role-admin' },
}

function formatLastActive(dateStr) {
  if (!dateStr) return 'Never'
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(dateStr))
}

function AdminUsers() {
  const navigate = useNavigate()
  const { confirm } = useDialog()
  const { showToast } = useToast()
  const [users, setUsers] = useState(null)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')

  const load = useCallback(() => {
    let cancelled = false
    api
      .get('/users')
      .then(({ data }) => {
        if (!cancelled) setUsers(data)
      })
      .catch(() => {
        if (!cancelled) setUsers((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  const counts = useMemo(() => {
    const list = users || []
    return {
      all: list.length,
      student: list.filter((u) => u.role === 'student').length,
      teacher: list.filter((u) => u.role === 'teacher').length,
      admin: list.filter((u) => u.role === 'admin').length,
    }
  }, [users])

  const filtered = useMemo(() => {
    const list = users || []
    const byRole = filter === 'all' ? list : list.filter((u) => u.role === filter)
    const q = search.trim().toLowerCase()
    if (!q) return byRole
    return byRole.filter(
      (u) => u.username.toLowerCase().includes(q) || (u.email || '').toLowerCase().includes(q)
    )
  }, [users, filter, search])

  function patchLocal(userId, patch) {
    setUsers((prev) => (prev || []).map((u) => (u.user_id === userId ? { ...u, ...patch } : u)))
  }

  async function deactivate(user) {
    const ok = await confirm(`Deactivate ${user.username}? This revokes their access immediately.`)
    if (!ok) return
    try {
      await api.patch(`/users/${user.user_id}/deactivate`)
      patchLocal(user.user_id, { is_active: false })
      showToast(`Deactivated ${user.username}`)
    } catch {
      showToast(`Couldn't deactivate ${user.username}`)
    }
  }

  async function reactivate(user) {
    try {
      await api.patch(`/users/${user.user_id}/reactivate`)
      patchLocal(user.user_id, { is_active: true })
      showToast(`Reactivated ${user.username}`)
    } catch {
      showToast(`Couldn't reactivate ${user.username}`)
    }
  }

  const loading = users === null

  return (
    <div className="admin-users">
      <h1 className="admin-page-h1">User directory</h1>
      <p className="admin-page-subtitle">Everyone at the school, in one place.</p>

      <div className="admin-users-toolbar">
        <div className="admin-filter-chips">
          {FILTERS.map((f) => (
            <button
              key={f.key}
              type="button"
              className={`admin-chip${filter === f.key ? ' active' : ''}`}
              onClick={() => setFilter(f.key)}
            >
              {f.label} <span className="admin-chip-count">{counts[f.key]}</span>
            </button>
          ))}
        </div>
        <input
          type="search"
          className="admin-user-search"
          placeholder="Search by name or email…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      {!loading && filtered.length === 0 && (
        <div className="admin-empty-card">No users match this filter.</div>
      )}

      <div className="admin-user-list">
        {filtered.map((user) => {
          const isDeactivated = !user.is_active
          const roleBadge = ROLE_BADGE[user.role]
          const isClickable = user.role === 'student'
          return (
            <div
              className={`admin-user-row${isDeactivated ? ' deactivated' : ''}${isClickable ? ' clickable' : ''}`}
              key={user.user_id}
              onClick={isClickable ? () => navigate(`/admin/users/${user.user_id}`) : undefined}
            >
              <div className="admin-user-avatar">{initials(user.username)}</div>
              <div className="admin-user-main">
                <div className="admin-user-name-line">
                  <span className="admin-user-name">{user.username}</span>
                  <span className={`admin-role-badge ${roleBadge.className}`}>{user.role}</span>
                  {isDeactivated && <span className="admin-deactivated-tag">Deactivated</span>}
                </div>
                {user.email && <div className="admin-user-email">{user.email}</div>}
              </div>
              <div className="admin-user-stats">
                <div className="admin-user-points">
                  {user.role === 'student' ? `${user.total_points} pts` : '—'}
                </div>
                <div className="admin-user-last-active">{formatLastActive(user.last_active_at)}</div>
              </div>
              <div className="admin-user-right">
                {!isDeactivated ? (
                  <button
                    type="button"
                    className="admin-btn-secondary admin-btn-danger-text"
                    onClick={(e) => {
                      e.stopPropagation()
                      deactivate(user)
                    }}
                  >
                    Deactivate
                  </button>
                ) : (
                  <button
                    type="button"
                    className="admin-btn-secondary"
                    onClick={(e) => {
                      e.stopPropagation()
                      reactivate(user)
                    }}
                  >
                    Reactivate
                  </button>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default AdminUsers
