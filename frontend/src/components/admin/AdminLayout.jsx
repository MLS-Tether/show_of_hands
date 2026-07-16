import { Navigate, Outlet } from 'react-router-dom'
import AdminSidebar from './AdminSidebar'
import AdminTopBar from './AdminTopBar'
import { isAdmin } from '../../utils/auth'
import './AdminLayout.css'

function AdminLayout() {
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
