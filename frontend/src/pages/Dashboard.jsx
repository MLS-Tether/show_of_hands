import SectionsSummary from '../components/dashboard/SectionsSummary'
import AssignmentsSummary from '../components/dashboard/AssignmentsSummary'
import QuestsSummary from '../components/dashboard/QuestsSummary'
import HelpRequestsSummary from '../components/dashboard/HelpRequestsSummary'
import TeacherDashboard from './TeacherDashboard'
import { useSections } from '../queries'
import { isTeacher } from '../utils/auth'
import './Dashboard.css'

function Dashboard() {
  if (isTeacher()) return <TeacherDashboard />
  return <StudentDashboard />
}

function StudentDashboard() {
  const { data: sections = null } = useSections()

  return (
    <div className="dashboard">
      <SectionsSummary sections={sections} />
      <div className="dashboard-columns">
        <AssignmentsSummary />
        <QuestsSummary sections={sections} />
      </div>
      <HelpRequestsSummary />
    </div>
  )
}

export default Dashboard
