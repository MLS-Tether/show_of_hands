import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'
import { getParentPath } from '../utils/escNavigation'
import { isTeacher } from '../utils/auth'
import './Layout.css'

function Layout() {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      const parent = getParentPath(location.pathname, { isTeacher: isTeacher() })
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
    <div className="admin-shell">
      <Sidebar />
      <div className="admin-main">
        <TopBar />
        <main className="admin-content">
          <div className="admin-content-inner">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default Layout
