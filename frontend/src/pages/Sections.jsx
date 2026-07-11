import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import { useDialog } from '../components/DialogProvider'
import { useAutoRefresh } from '../utils/autoRefresh'
import './Sections.css'

function Sections() {
  const navigate = useNavigate()
  const { confirm, alert } = useDialog()
  const [sections, setSections] = useState(null)
  const [allSections, setAllSections] = useState(null)
  const [requestedIds, setRequestedIds] = useState(() => new Set())

  const loadSections = useCallback(() => {
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

  const loadAllSections = useCallback(() => {
    let cancelled = false
    api
      .get('/sections', { params: { scope: 'all' } })
      .then(({ data }) => {
        if (!cancelled) setAllSections(data)
      })
      .catch(() => {
        if (!cancelled) setAllSections((prev) => prev ?? [])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => loadSections(), [loadSections])
  useEffect(() => loadAllSections(), [loadAllSections])
  useAutoRefresh(loadSections)
  useAutoRefresh(loadAllSections)

  async function handleEnroll(s) {
    const confirmed = await confirm(`Request to join ${s.class_name} (${s.period})?`)
    if (!confirmed) return

    try {
      await api.post(`/sections/${s.section_id}/enrollment-requests`)
      setRequestedIds((prev) => new Set(prev).add(s.section_id))
      await alert('Request sent. A teacher or admin needs to approve it.')
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not send the request.')
    }
  }

  const loading = sections === null
  const allLoading = allSections === null

  const enrolledIds = new Set((sections || []).map((s) => s.section_id))
  const browsableSections = (allSections || []).filter((s) => !enrolledIds.has(s.section_id))

  return (
    <section className="sections-page">
      <h1>My sections</h1>
      {loading && <p className="sections-placeholder">Loading sections…</p>}
      {!loading && sections.length === 0 && (
        <p className="sections-placeholder">You're not enrolled in any sections yet.</p>
      )}
      {!loading && sections.length > 0 && (
        <div className="sections-list">
          {sections.map((s) => (
            <button
              key={s.section_id}
              type="button"
              className="section-row"
              onClick={() => navigate(`/sections/${s.section_id}`)}
            >
              <span className="section-row-name">{s.class_name}</span>
              <span className="section-row-meta">
                {s.period} · {s.teacher_name || 'Unassigned'}
              </span>
            </button>
          ))}
        </div>
      )}

      <h2 className="sections-subheading">All sections</h2>
      {allLoading && <p className="sections-placeholder">Loading sections…</p>}
      {!allLoading && browsableSections.length === 0 && (
        <p className="sections-placeholder">No other sections to join right now.</p>
      )}
      {!allLoading && browsableSections.length > 0 && (
        <div className="sections-list">
          {browsableSections.map((s) => (
            <button
              key={s.section_id}
              type="button"
              className="section-row"
              disabled={requestedIds.has(s.section_id)}
              onClick={() => handleEnroll(s)}
            >
              <span className="section-row-name">
                {s.class_name}
                <span className="section-row-teacher"> · {s.teacher_name || 'Unassigned'}</span>
              </span>
              <span className="section-row-meta">
                {requestedIds.has(s.section_id)
                  ? 'Requested'
                  : `${s.enrolled_count}/${s.capacity} students`}
              </span>
            </button>
          ))}
        </div>
      )}
    </section>
  )
}

export default Sections
