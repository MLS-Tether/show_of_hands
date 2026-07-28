import { useCallback, useEffect, useRef, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'
import MobileNav from './MobileNav'
import AskButton from './AskButton'
import { SidebarPeekContext } from './SidebarPeekContext'
import { RealtimeProvider } from '../realtime/RealtimeProvider'
import { TutorialProvider } from './tutorial/TutorialProvider'
import { useInventory } from '../queries'
import { getAdminParentPath, getParentPath } from '../utils/escNavigation'
import { isEscapeClaimed } from '../utils/escapeClaim'
import { getUserId, isStudent, isTeacher } from '../utils/auth'
import './Layout.css'

// Kept slightly longer than the 0.75s CSS animation (see Sidebar.css
// `sidebar-peek` keyframes) so the slide-out always finishes visually
// before React unmounts the peek sidebar, instead of racing it mid-slide.
const SIDEBAR_PEEK_DURATION_MS = 850

function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarHidden, setSidebarHidden] = useState(
    () => localStorage.getItem('sidebar_hidden') === '1'
  )
  const [peeking, setPeeking] = useState(false)
  const peekTimeoutRef = useRef(null)

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

  const peekSidebar = useCallback(() => {
    if (!sidebarHidden) return
    if (peekTimeoutRef.current) clearTimeout(peekTimeoutRef.current)
    setPeeking(true)
    peekTimeoutRef.current = setTimeout(() => setPeeking(false), SIDEBAR_PEEK_DURATION_MS)
  }, [sidebarHidden])

  useEffect(() => {
    return () => {
      if (peekTimeoutRef.current) clearTimeout(peekTimeoutRef.current)
    }
  }, [])

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
          <SidebarPeekContext.Provider value={peekSidebar}>
            {!sidebarHidden && <Sidebar />}
            {sidebarHidden && peeking && <Sidebar className="admin-sidebar-peek" />}
            <div className="admin-main">
              <TopBar sidebarHidden={sidebarHidden} onToggleSidebar={toggleSidebar} />
              <main className="admin-content">
                <div className="admin-content-inner">
                  <Outlet />
                </div>
              </main>
            </div>
            <MobileNav />
            <AskButton />
          </SidebarPeekContext.Provider>
        </TutorialProvider>
      </div>
    </RealtimeProvider>
  )
}

export default Layout
