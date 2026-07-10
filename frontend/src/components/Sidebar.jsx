import { NavLink } from 'react-router-dom'
import './Sidebar.css'

const NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'My sections', to: '/sections' },
  { label: 'Assignments', to: '/assignments' },
  { label: 'Quests', to: '/quests' },
  { label: 'Bulletin board', to: '/bulletin-board' },
  { label: 'Study rooms', to: '/study-rooms' },
  { label: 'Points', to: '/points' },
]

function Sidebar() {
  return (
    <nav className="sidebar" aria-label="Main">
      {NAV_ITEMS.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

export default Sidebar
