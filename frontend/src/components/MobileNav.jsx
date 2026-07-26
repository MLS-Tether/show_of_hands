import { useState } from 'react'
import { NavLink } from 'react-router-dom'
import { useClassRequests, useUsers } from '../queries'
import { isAdmin, isTeacher } from '../utils/auth'
import { ADMIN_NAV_GROUPS, APP_NAV_ITEMS } from './navConfig'
import MoreSheet from './MoreSheet'
import './MobileNav.css'

const MOBILE_PRIMARY_PATHS = ['/dashboard', '/assignments', '/quests', '/bulletin-board']

const ICONS = {
  '/dashboard': '⌂',
  '/assignments': '📝',
  '/quests': '🎯',
  '/bulletin-board': '📌',
}

// The bulletin-board nav item reads "Requests" here only — the page itself
// keeps its "Bulletin board" heading, and the desktop sidebar link is
// unchanged; this is purely a compact mobile-tab label.
const MOBILE_LABELS = {
  '/bulletin-board': 'Requests',
}

function MobileNav() {
  const admin = isAdmin()
  const teacher = isTeacher()
  const [moreOpen, setMoreOpen] = useState(false)

  const { data: users = null } = useUsers({}, { enabled: admin })
  const { data: classRequests = null } = useClassRequests({ enabled: admin })
  const inboxCount = admin
    ? (users?.filter((u) => u.role !== 'student' && !u.is_verified).length || 0) +
      (classRequests?.filter((r) => r.status === 'pending').length || 0)
    : null

  let primaryItems = []
  let sheetGroups

  if (admin) {
    sheetGroups = ADMIN_NAV_GROUPS
  } else {
    const filtered = APP_NAV_ITEMS.filter((item) => !item.studentOnly || !teacher)
    primaryItems = filtered.filter((item) => MOBILE_PRIMARY_PATHS.includes(item.to))
    const secondaryItems = filtered.filter((item) => !MOBILE_PRIMARY_PATHS.includes(item.to))
    sheetGroups = [{ label: null, items: secondaryItems }]
  }

  return (
    <>
      <nav className="mobile-nav" aria-label="Main">
        {primaryItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `mobile-nav-tab${isActive ? ' active' : ''}`}
          >
            <span className="mobile-nav-icon" aria-hidden="true">
              {ICONS[item.to]}
            </span>
            <span className="mobile-nav-label">{MOBILE_LABELS[item.to] || item.label}</span>
          </NavLink>
        ))}
        <button
          type="button"
          className={`mobile-nav-tab mobile-nav-more${moreOpen ? ' active' : ''}`}
          aria-expanded={moreOpen}
          onClick={() => setMoreOpen((open) => !open)}
        >
          <span className="mobile-nav-icon" aria-hidden="true">
            ⋯
          </span>
          <span className="mobile-nav-label">{admin ? 'Menu' : 'More'}</span>
        </button>
      </nav>
      <MoreSheet
        open={moreOpen}
        onClose={() => setMoreOpen(false)}
        groups={sheetGroups}
        inboxCount={inboxCount}
      />
    </>
  )
}

export default MobileNav
