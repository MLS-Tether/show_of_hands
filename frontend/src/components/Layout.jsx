import { useCallback, useEffect, useRef, useState } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'
import { SidebarPeekContext } from './SidebarPeekContext'
import { RealtimeProvider } from '../realtime/RealtimeProvider'
import { TutorialProvider } from './tutorial/TutorialProvider'
import { getAdminParentPath, getParentPath } from '../utils/escNavigation'
import { isEscapeClaimed } from '../utils/escapeClaim'
import { isTeacher } from '../utils/auth'
import './Layout.css'

const SIDEBAR_PEEK_DURATION_MS = 750

function Layout() {
  const navigate = useNavigate()
  const location = useLocation()
  const [sidebarHidden, setSidebarHidden] = useState(
    () => localStorage.getItem('sidebar_hidden') === '1'
  )
  const [peeking, setPeeking] = useState(false)
  const peekTimeoutRef = useRef(null)

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
          </SidebarPeekContext.Provider>
        </TutorialProvider>
      </div>
    </RealtimeProvider>
  )
}

export default Layout
