import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { mediaUrl } from '../api'
import { useClassRequests, useSchool, useUser, useUsers } from '../queries'
import { getUserId, isAdmin, isTeacher } from '../utils/auth'
import { initials } from '../utils/format'
import { logout } from '../utils/logout'
import { ADMIN_NAV_GROUPS, APP_NAV_ITEMS } from './navConfig'
import './Sidebar.css'

function Sidebar({ className = '' }) {
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

  function handleLogout() {
    logout(navigate)
  }

  const navGroups = admin
    ? ADMIN_NAV_GROUPS
    : [{ label: null, items: APP_NAV_ITEMS.filter((item) => !item.studentOnly || !teacher) }]

  return (
    <nav className={`admin-sidebar ${className}`.trim()} aria-label="Main">
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
