import { useCallback, useEffect, useState } from 'react'
import api from '../api'
import SectionsSummary from '../components/dashboard/SectionsSummary'
import AssignmentsSummary from '../components/dashboard/AssignmentsSummary'
import QuestsSummary from '../components/dashboard/QuestsSummary'
import HelpRequestsSummary from '../components/dashboard/HelpRequestsSummary'
import { useAutoRefresh } from '../utils/autoRefresh'
import './Dashboard.css'

function Dashboard() {
  const [sections, setSections] = useState(null)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get('/sections')
      .then(({ data }) => {
        if (!cancelled) setSections(data)
      })
      .catch(() => {
        if (!cancelled) setSections((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  return (
    <div className="dashboard">
      <SectionsSummary sections={sections} />
      <div className="dashboard-columns">
        <AssignmentsSummary sections={sections} />
        <QuestsSummary sections={sections} />
      </div>
      <HelpRequestsSummary sections={sections} />
    </div>
  )
}

export default Dashboard
