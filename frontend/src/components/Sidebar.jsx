import { NavLink } from 'react-router-dom'
import { isTeacher } from '../utils/auth'
import './Sidebar.css'

const NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'My sections', to: '/sections' },
  { label: 'Assignments', to: '/assignments', studentOnly: true },
  { label: 'Quests', to: '/quests' },
  { label: 'Bulletin board', to: '/bulletin-board', studentOnly: true },
  { label: 'Study rooms', to: '/study-rooms', studentOnly: true },
  { label: 'Points', to: '/points', studentOnly: true },
]

function Sidebar() {
  const teacher = isTeacher()
  const items = NAV_ITEMS.filter((item) => !item.studentOnly || !teacher)

  return (
    <nav className="sidebar" aria-label="Main">
      {items.map((item) => (
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
