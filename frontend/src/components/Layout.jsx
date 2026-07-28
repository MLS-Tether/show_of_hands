import { useEffect, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'
import { RealtimeProvider } from '../realtime/RealtimeProvider'
import { TutorialProvider } from './tutorial/TutorialProvider'
import { useInventory } from '../queries'
import { getAdminParentPath, getParentPath } from '../utils/escNavigation'
import { isEscapeClaimed } from '../utils/escapeClaim'
import { getUserId, isStudent, isTeacher } from '../utils/auth'
import './Layout.css'

function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarHidden, setSidebarHidden] = useState(
    () => localStorage.getItem('sidebar_hidden') === '1'
  )

  // Shop themes are a student-only cosmetic; teachers/admins never own
  // inventory, so skip the request for them entirely.
  const { data: inventory = [] } = useInventory(getUserId(), { enabled: isStudent() })
  const equippedThemeKey = inventory.find(
    (row) => row.item.item_type === 'theme' && row.is_equipped
  )?.item.theme_key

  // Lives here (rather than on Profile) because Layout wraps every
  // authenticated route via <Outlet> — a theme equipped from the character
  // customizer should recolor the whole app, not just the profile page.
  useEffect(() => {
    document.documentElement.setAttribute('data-shop-theme', equippedThemeKey || '')
    return () => {
      document.documentElement.removeAttribute('data-shop-theme')
    }
  }, [equippedThemeKey])

  function toggleSidebar() {
    setSidebarHidden((hidden) => {
      localStorage.setItem('sidebar_hidden', hidden ? '0' : '1')
      return !hidden
    })
  }

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      if (isEscapeClaimed()) return
      const parent = location.pathname.startsWith('/admin')
        ? getAdminParentPath(location.pathname)
        : getParentPath(location.pathname, { isTeacher: isTeacher() })
      if (!parent) return
      if (parent === 'BACK') {
        navigate(-1)
      } else {
        navigate(parent)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [location.pathname, navigate])

  return (
    <RealtimeProvider>
      <div className="admin-shell">
        <TutorialProvider>
          {!sidebarHidden && <Sidebar />}
          <div className="admin-main">
            <TopBar sidebarHidden={sidebarHidden} onToggleSidebar={toggleSidebar} />
            <main className="admin-content">
              <div className="admin-content-inner">
                <Outlet />
              </div>
            </main>
          </div>
        </TutorialProvider>
      </div>
    </RealtimeProvider>
  )
}

export default Layout
