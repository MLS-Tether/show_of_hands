import { Navigate, Route, Routes } from 'react-router-dom'
import ProtectedRoute from './auth/ProtectedRoute'
import AppLayout from './layout/AppLayout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import SectionsPickerPage from './pages/SectionsPickerPage'
import BulletinBoardPage from './pages/BulletinBoardPage'
import RoomPage from './pages/RoomPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/sections" replace />} />
          <Route path="/sections" element={<SectionsPickerPage />} />
          <Route path="/sections/:sectionId/bulletin" element={<BulletinBoardPage />} />
          <Route path="/rooms/:roomId" element={<RoomPage />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
