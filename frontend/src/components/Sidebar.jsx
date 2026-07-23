import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import api, { mediaUrl } from '../api'
import { useClassRequests, useSchool, useUser, useUsers } from '../queries'
import { getUserId, isAdmin, isTeacher } from '../utils/auth'
import { initials } from '../utils/format'
import './Sidebar.css'

const ADMIN_NAV_GROUPS = [
  { label: null, items: [{ label: 'Overview', to: '/admin/overview', end: true, tour: 'nav-overview' }] },
  { label: 'Approvals', items: [{ label: 'Inbox', to: '/admin/inbox', badge: 'inbox', tour: 'nav-inbox' }] },
  {
    label: 'Manage',
    items: [
      { label: 'Sections', to: '/admin/sections', tour: 'nav-sections' },
      { label: 'Users', to: '/admin/users', tour: 'nav-users' },
    ],
  },
  { label: 'School', items: [{ label: 'Settings', to: '/admin/settings' }] },
]

const APP_NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'My sections', to: '/sections', tour: 'nav-sections' },
  { label: 'Assignments', to: '/assignments', studentOnly: true, tour: 'nav-assignments' },
  { label: 'Quests', to: '/quests', tour: 'nav-quests' },
  { label: 'Bulletin board', to: '/bulletin-board', studentOnly: true, tour: 'nav-bulletin' },
  { label: 'Study rooms', to: '/study-rooms', studentOnly: true, tour: 'nav-rooms' },
  { label: 'Points', to: '/points', studentOnly: true },
]

function Sidebar() {
  const navigate = useNavigate()
  const admin = isAdmin()
  const teacher = isTeacher()
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  const { data: school = null } = useSchool()
  const { data: user = null } = useUser(getUserId())
  const { data: users = null } = useUsers({}, { enabled: admin })
  const { data: classRequests = null } = useClassRequests({ enabled: admin })

  const inboxCount = admin
    ? (users?.filter((u) => u.role !== 'student' && !u.is_verified).length || 0) +
      (classRequests?.filter((r) => r.status === 'pending').length || 0)
    : null

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  async function handleLogout() {
    const refreshToken = localStorage.getItem('refresh_token')
    try {
      await api.post('/auth/logout', { refresh_token: refreshToken })
    } catch {
      // best-effort: still clear local session and redirect below
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('role')
    navigate('/auth')
  }

  const navGroups = admin
    ? ADMIN_NAV_GROUPS
    : [{ label: null, items: APP_NAV_ITEMS.filter((item) => !item.studentOnly || !teacher) }]

  return (
    <nav className="admin-sidebar" aria-label="Main">
      <div className="admin-sidebar-brand">
        <div className="admin-sidebar-logo">
          Show of Hands{' '}
          <span className="admin-sidebar-pill">
            {admin ? 'Admin' : teacher ? 'Teacher' : 'Student'}
          </span>
        </div>
        {school && <div className="admin-sidebar-school">{school.name}</div>}
      </div>

      <div className="admin-sidebar-nav">
        {navGroups.map((group, i) => (
          <div className="admin-sidebar-group" key={group.label ?? i}>
            {group.label && <div className="admin-sidebar-group-label">{group.label}</div>}
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                data-tour={item.tour}
                className={({ isActive }) => `admin-sidebar-link${isActive ? ' active' : ''}`}
              >
                <span>{item.label}</span>
                {item.badge === 'inbox' && inboxCount > 0 && (
                  <span className="admin-sidebar-badge">{inboxCount}</span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </div>

      {user && (
        <div className="admin-sidebar-account" ref={menuRef}>
          {menuOpen && (
            <div className="admin-sidebar-menu" role="menu">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  navigate(admin ? '/admin/profile' : '/profile')
                }}
              >
                My profile
              </button>
              <button type="button" role="menuitem" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
          <button
            type="button"
            className="admin-sidebar-footer"
            aria-label="Account menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <div className="admin-sidebar-avatar">
              {user.profile_picture_url ? (
                <img src={mediaUrl(user.profile_picture_url)} alt="" className="admin-sidebar-avatar-img" />
              ) : (
                initials(user.username)
              )}
            </div>
            <div className="admin-sidebar-footer-text">
              <div className="admin-sidebar-footer-name">{user.username}</div>
              <div className="admin-sidebar-footer-role">{user.role}</div>
            </div>
          </button>
        </div>
      )}
    </nav>
  )
}

export default Sidebar
