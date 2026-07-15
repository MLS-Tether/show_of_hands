import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'
import { getParentPath } from '../utils/escNavigation'
import './Layout.css'

function Layout() {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      const parent = getParentPath(location.pathname)
      if (parent) navigate(parent)
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [location.pathname, navigate])

  return (
    <div className="app-shell">
      <TopBar />
      <div className="app-body">
        <Sidebar />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
