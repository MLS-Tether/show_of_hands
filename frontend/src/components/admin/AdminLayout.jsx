import { useEffect } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import AdminSidebar from './AdminSidebar'
import AdminTopBar from './AdminTopBar'
import { getAdminParentPath } from '../../utils/escNavigation'
import { isEscapeClaimed } from '../../utils/escapeClaim'
import { isAdmin } from '../../utils/auth'
import './AdminLayout.css'

function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      if (isEscapeClaimed()) return
      const parent = getAdminParentPath(location.pathname)
      if (!parent) return
      navigate(parent)
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [location.pathname, navigate])

  if (!isAdmin()) return <Navigate to="/dashboard" replace />

  return (
    <div className="admin-shell">
      <AdminSidebar />
      <div className="admin-main">
        <AdminTopBar />
        <main className="admin-content">
          <div className="admin-content-inner">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default AdminLayout
