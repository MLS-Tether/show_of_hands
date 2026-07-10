import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Sections from './pages/Sections'
import SectionDetail from './pages/SectionDetail'
import Assignments from './pages/Assignments'
import AssignmentDetail from './pages/AssignmentDetail'
import Quests from './pages/Quests'
import BulletinBoard from './pages/BulletinBoard'
import StudyRooms from './pages/StudyRooms'
import Points from './pages/Points'
import Auth from './pages/Auth'
import './App.css'

function App() {
  return (
    <Routes>
      <Route
        path="/"
        element={
          <Navigate to={localStorage.getItem('access_token') ? '/dashboard' : '/auth'} replace />
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
        <Route path="/points" element={<Points />} />
      </Route>
    </Routes>
  )
}

export default App
