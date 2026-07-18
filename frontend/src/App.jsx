import { Routes, Route, Navigate, Outlet } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Sections from './pages/Sections'
import SectionDetail from './pages/SectionDetail'
import Assignments from './pages/Assignments'
import AssignmentDetail from './pages/AssignmentDetail'
import Quests from './pages/Quests'
import BulletinBoard from './pages/BulletinBoard'
import StudyRooms from './pages/StudyRooms'
import RoomDetail from './pages/RoomDetail'
import Points from './pages/Points'
import Profile from './pages/Profile'
import Auth from './pages/Auth'
import AdminOverview from './pages/admin/AdminOverview'
import AdminInbox from './pages/admin/AdminInbox'
import AdminSections from './pages/admin/AdminSections'
import AdminUsers from './pages/admin/AdminUsers'
import AdminSettings from './pages/admin/AdminSettings'
import { isAdmin } from './utils/auth'
import './App.css'

function RequireAdmin() {
  if (!isAdmin()) return <Navigate to="/dashboard" replace />
  return <Outlet />
}

function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <Navigate
            to={
              !localStorage.getItem('access_token')
                ? '/auth'
                : isAdmin()
                  ? '/admin/overview'
                  : '/dashboard'
            }
            replace
          />
        }
      />
      <Route path="/auth" element={<Auth />} />
      <Route element={<Layout />}>
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/sections" element={<Sections />} />
        <Route path="/sections/:sectionId" element={<SectionDetail />} />
        <Route path="/assignments" element={<Assignments />} />
        <Route path="/assignments/:assignmentId" element={<AssignmentDetail />} />
        <Route path="/quests" element={<Quests />} />
        <Route path="/bulletin-board" element={<BulletinBoard />} />
        <Route path="/study-rooms" element={<StudyRooms />} />
        <Route path="/rooms/:roomId" element={<RoomDetail />} />
        <Route path="/points" element={<Points />} />
        <Route path="/profile" element={<Profile />} />
        <Route element={<RequireAdmin />}>
          <Route path="/admin/overview" element={<AdminOverview />} />
          <Route path="/admin/inbox" element={<AdminInbox />} />
          <Route path="/admin/sections" element={<AdminSections />} />
          <Route path="/admin/users" element={<AdminUsers />} />
          <Route path="/admin/settings" element={<AdminSettings />} />
          <Route path="/admin/profile" element={<Profile />} />
        </Route>
      </Route>
    </Routes>
  )
}

export default App
