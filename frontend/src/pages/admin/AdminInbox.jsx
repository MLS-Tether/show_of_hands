import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api'
import { useDialog } from '../../components/DialogContext'
import { useToast } from '../../components/ToastContext'
import { keys, useClassRequests, useUsers } from '../../queries'
import '../../styles/shared-ui.css'
import './AdminInbox.css'

const FILTERS = [
  { key: 'all', label: 'All' },
  { key: 'teacher', label: 'Teachers' },
  { key: 'admin', label: 'Admins' },
  { key: 'class', label: 'Class requests' },
]

const KIND_BADGE = {
  teacher: { label: 'Teacher signup', className: 'kind-teacher' },
  admin: { label: 'Admin signup', className: 'kind-admin' },
  class: { label: 'Class request', className: 'kind-class' },
}

function formatDate(dateStr) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(new Date(dateStr))
}

function AdminInbox() {
  const [searchParams, setSearchParams] = useSearchParams()
  const filter = searchParams.get('filter') || 'all'
  const { confirm } = useDialog()
  const { showToast } = useToast()
  const queryClient = useQueryClient()

  const [selected, setSelected] = useState([])
  const [expanded, setExpanded] = useState(null)
  const [busy, setBusy] = useState(false)

  const { data: rawUsers = null } = useUsers()
  const { data: rawClassRequests = null } = useClassRequests()

  const items = useMemo(() => {
    if (rawUsers === null || rawClassRequests === null) return null
    const usersById = new Map(rawUsers.map((u) => [u.user_id, u.username]))

    const signupItems = rawUsers
      .filter((u) => u.role !== 'student' && !u.is_verified && !u.rejection_reason)
      .map((u) => ({
        id: `signup-${u.user_id}`,
        entityId: u.user_id,
        kind: u.role,
        title: u.username,
        createdAt: u.created_at,
        role: u.role,
        email: u.email,
        note: u.signup_note,
      }))

    const classItems = rawClassRequests
      .filter((r) => r.status === 'pending')
      .map((r) => ({
        id: `class-${r.class_request_id}`,
        entityId: r.class_request_id,
        kind: 'class',
        title: r.class_name,
        createdAt: r.created_at,
        requestedBy: usersById.get(r.requested_by) || `User #${r.requested_by}`,
        subject: r.subject,
        description: r.description,
        similarClasses: r.similar_classes || [],
      }))

    return [...signupItems, ...classItems]
  }, [rawUsers, rawClassRequests])

  const counts = useMemo(() => {
    const list = items || []
    return {
      all: list.length,
      teacher: list.filter((i) => i.kind === 'teacher').length,
      admin: list.filter((i) => i.kind === 'admin').length,
      class: list.filter((i) => i.kind === 'class').length,
    }
  }, [items])

  const filtered = useMemo(() => {
    const list = items || []
    if (filter === 'all') return list
    return list.filter((i) => i.kind === filter)
  }, [items, filter])

  function patchUser(userId, patch) {
    queryClient.setQueryData(keys.users({}), (prev) =>
      (prev || []).map((u) => (u.user_id === userId ? { ...u, ...patch } : u))
    )
  }

  function patchClassRequest(classRequestId, patch) {
    queryClient.setQueryData(keys.classRequests(), (prev) =>
      (prev || []).map((r) => (r.class_request_id === classRequestId ? { ...r, ...patch } : r))
    )
  }

  function dismissItems(ids) {
    setSelected((prev) => prev.filter((id) => !ids.includes(id)))
    if (expanded && ids.includes(expanded)) setExpanded(null)
  }

  async function approveSignup(item) {
    // Admin signups grant full admin rights — require an explicit
    // confirmation click (not just the ordinary approve button) before
    // sending confirm_role, which the backend independently checks.
    if (item.kind === 'admin') {
      const ok = await confirm(`Grant ${item.title} full admin access?`)
      if (!ok) return
    }
    setBusy(true)
    try {
      await api.patch(`/users/${item.entityId}/verify`, {
        confirm_role: item.kind === 'admin' ? 'admin' : undefined,
      })
      patchUser(item.entityId, { is_verified: true })
      dismissItems([item.id])
      showToast(`Approved ${item.title}`)
    } catch {
      showToast(`Couldn't approve ${item.title}`)
    } finally {
      setBusy(false)
    }
  }

  async function rejectSignup(item) {
    const ok = await confirm(`Reject ${item.title}'s signup?`)
    if (!ok) return
    setBusy(true)
    try {
      await api.patch(`/users/${item.entityId}/reject`, {})
      patchUser(item.entityId, { rejection_reason: 'Rejected by admin' })
      dismissItems([item.id])
      showToast(`Rejected ${item.title}`)
    } catch {
      showToast(`Couldn't reject ${item.title}`)
    } finally {
      setBusy(false)
    }
  }

  async function approveClassRequest(item) {
    setBusy(true)
    try {
      await api.patch(`/class-requests/${item.entityId}`, { status: 'approved' })
      patchClassRequest(item.entityId, { status: 'approved' })
      dismissItems([item.id])
      showToast(`Added to catalog: ${item.title}`)
    } catch {
      showToast(`Couldn't approve ${item.title}`)
    } finally {
      setBusy(false)
    }
  }

  async function declineClassRequest(item) {
    const ok = await confirm(`Decline the class request "${item.title}"?`)
    if (!ok) return
    setBusy(true)
    try {
      await api.patch(`/class-requests/${item.entityId}`, { status: 'rejected' })
      patchClassRequest(item.entityId, { status: 'rejected' })
      dismissItems([item.id])
      showToast(`Declined ${item.title}`)
    } catch {
      showToast(`Couldn't decline ${item.title}`)
    } finally {
      setBusy(false)
    }
  }

  async function bulkApprove() {
    const targets = (items || []).filter((i) => selected.includes(i.id))
    if (targets.length === 0) return

    const adminTargets = targets.filter((i) => i.kind === 'admin')
    if (adminTargets.length > 0) {
      const ok = await confirm(
        `This includes ${adminTargets.length} admin signup(s), which will be granted full admin access. Continue?`
      )
      if (!ok) return
    }

    setBusy(true)
    try {
      await Promise.all(
        targets.map((item) =>
          item.kind === 'class'
            ? api.patch(`/class-requests/${item.entityId}`, { status: 'approved' })
            : api.patch(`/users/${item.entityId}/verify`, {
                confirm_role: item.kind === 'admin' ? 'admin' : undefined,
              })
        )
      )
      targets.forEach((item) =>
        item.kind === 'class'
          ? patchClassRequest(item.entityId, { status: 'approved' })
          : patchUser(item.entityId, { is_verified: true })
      )
      dismissItems(targets.map((i) => i.id))
      showToast(`${targets.length} item${targets.length === 1 ? '' : 's'} approved`)
    } catch {
      showToast('Some items could not be approved')
      queryClient.invalidateQueries({ queryKey: ['users'] })
      queryClient.invalidateQueries({ queryKey: keys.classRequests() })
    } finally {
      setBusy(false)
    }
  }

  async function bulkReject() {
    const targets = (items || []).filter((i) => selected.includes(i.id))
    if (targets.length === 0) return
    const ok = await confirm(`Reject ${targets.length} selected item(s)?`)
    if (!ok) return
    setBusy(true)
    try {
      await Promise.all(
        targets.map((item) =>
          item.kind === 'class'
            ? api.patch(`/class-requests/${item.entityId}`, { status: 'rejected' })
            : api.patch(`/users/${item.entityId}/reject`, {})
        )
      )
      targets.forEach((item) =>
        item.kind === 'class'
          ? patchClassRequest(item.entityId, { status: 'rejected' })
          : patchUser(item.entityId, { rejection_reason: 'Rejected by admin' })
      )
      dismissItems(targets.map((i) => i.id))
      showToast(`${targets.length} item${targets.length === 1 ? '' : 's'} rejected`)
    } catch {
      showToast('Some items could not be rejected')
      queryClient.invalidateQueries({ queryKey: ['users'] })
      queryClient.invalidateQueries({ queryKey: keys.classRequests() })
    } finally {
      setBusy(false)
    }
  }

  function toggleSelect(id) {
    setSelected((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]))
  }

  const loading = items === null

  return (
    <div className="admin-inbox">
      <h1 className="admin-page-h1">Approvals</h1>
      <p className="admin-page-subtitle">Review pending signups and class requests.</p>

      <div className="admin-filter-chips">
        {FILTERS.map((f) => (
          <button
            key={f.key}
            type="button"
            className={`admin-chip${filter === f.key ? ' active' : ''}`}
            onClick={() => setSearchParams(f.key === 'all' ? {} : { filter: f.key })}
          >
            {f.label} <span className="admin-chip-count">{counts[f.key]}</span>
          </button>
        ))}
      </div>

      {selected.length > 0 && (
        <div className="admin-bulk-bar">
          <span>{selected.length} selected</span>
          <div className="admin-bulk-actions">
            <button type="button" className="admin-btn-primary" disabled={busy} onClick={bulkApprove}>
              Approve all
            </button>
            <button
              type="button"
              className="admin-btn-secondary"
              disabled={busy}
              onClick={bulkReject}
            >
              Reject all
            </button>
            <button type="button" className="admin-btn-text" onClick={() => setSelected([])}>
              Clear
            </button>
          </div>
        </div>
      )}

      {!loading && filtered.length === 0 && (
        <div className="admin-empty-card">Nothing waiting on you here.</div>
      )}

      <div className="admin-inbox-list">
        {filtered.map((item) => {
          const isExpanded = expanded === item.id
          const badge = KIND_BADGE[item.kind]
          return (
            <div className={`admin-inbox-card${isExpanded ? ' expanded' : ''}`} key={item.id}>
              <div className="admin-inbox-row">
                <input
                  type="checkbox"
                  className="admin-checkbox"
                  checked={selected.includes(item.id)}
                  onChange={() => toggleSelect(item.id)}
                />
                <button
                  type="button"
                  className="admin-inbox-title-block"
                  onClick={() => setExpanded(isExpanded ? null : item.id)}
                >
                  <div className="admin-inbox-title-line">
                    <span className={`admin-kind-badge ${badge.className}`}>{badge.label}</span>
                    <span className="admin-inbox-title">{item.title}</span>
                  </div>
                  <div className="admin-inbox-subtitle">
                    {item.kind === 'class'
                      ? `Requested by ${item.requestedBy}`
                      : `Requested role: ${item.role}`}
                  </div>
                </button>
                <span className="admin-inbox-time">{formatDate(item.createdAt)}</span>
                <span
                  className={`admin-chevron${isExpanded ? ' rotated' : ''}`}
                  onClick={() => setExpanded(isExpanded ? null : item.id)}
                >
                  ▾
                </span>
              </div>

              {isExpanded && (
                <div className="admin-inbox-panel">
                  {item.kind === 'class' ? (
                    <>
                      <div className="admin-detail-row">
                        <span className="admin-detail-label">Requesting teacher</span>
                        <span>{item.requestedBy}</span>
                      </div>
                      {item.subject && (
                        <div className="admin-detail-row">
                          <span className="admin-detail-label">Subject</span>
                          <span>{item.subject}</span>
                        </div>
                      )}
                      {item.description && (
                        <div className="admin-detail-row">
                          <span className="admin-detail-label">Description</span>
                          <span>{item.description}</span>
                        </div>
                      )}
                      <div className="admin-detail-row">
                        <span className="admin-detail-label">Catalog check</span>
                        <span>
                          {item.similarClasses.length > 0
                            ? `Matches existing: ${item.similarClasses.join(', ')}`
                            : 'No similar classes found'}
                        </span>
                      </div>
                      <div className="admin-detail-row">
                        <span className="admin-detail-label">Submitted</span>
                        <span>{formatDate(item.createdAt)}</span>
                      </div>
                      <div className="admin-inbox-actions">
                        <button
                          type="button"
                          className="admin-btn-primary"
                          disabled={busy}
                          onClick={() => approveClassRequest(item)}
                        >
                          Add to catalog
                        </button>
                        <button
                          type="button"
                          className="admin-btn-secondary"
                          disabled={busy}
                          onClick={() => declineClassRequest(item)}
                        >
                          Decline
                        </button>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="admin-detail-row">
                        <span className="admin-detail-label">Requested role</span>
                        <span>{item.role}</span>
                      </div>
                      {item.email && (
                        <div className="admin-detail-row">
                          <span className="admin-detail-label">Email</span>
                          <span>{item.email}</span>
                        </div>
                      )}
                      <div className="admin-detail-row">
                        <span className="admin-detail-label">Signed up</span>
                        <span>{formatDate(item.createdAt)}</span>
                      </div>
                      {item.note && (
                        <div className="admin-detail-row">
                          <span className="admin-detail-label">Note</span>
                          <span>{item.note}</span>
                        </div>
                      )}
                      <div className="admin-inbox-actions">
                        <button
                          type="button"
                          className="admin-btn-primary"
                          disabled={busy}
                          onClick={() => approveSignup(item)}
                        >
                          Approve signup
                        </button>
                        <button
                          type="button"
                          className="admin-btn-secondary"
                          disabled={busy}
                          onClick={() => rejectSignup(item)}
                        >
                          Reject
                        </button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default AdminInbox
