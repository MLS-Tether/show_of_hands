import { useEffect, useState } from 'react'
import api from '../../api'
import { formatPercent } from '../../utils/format'

function GradeSummary({ sectionId, studentId }) {
  const [grade, setGrade] = useState(null)
  const [failed, setFailed] = useState(false)
  const [loadedKey, setLoadedKey] = useState(null)

  const key = `${sectionId}:${studentId || 'me'}`

  useEffect(() => {
    let cancelled = false
    const path = studentId
      ? `/sections/${sectionId}/grades/${studentId}`
      : `/sections/${sectionId}/grades/me`
    api
      .get(path)
      .then(({ data }) => {
        if (cancelled) return
        setGrade(data)
        setFailed(false)
        setLoadedKey(key)
      })
      .catch(() => {
        if (cancelled) return
        setFailed(true)
        setLoadedKey(key)
      })
    return () => {
      cancelled = true
    }
  }, [sectionId, studentId, key])

  const loading = loadedKey !== key

  if (loading) {
    return <p className="section-detail-placeholder">Loading grade…</p>
  }

  if (failed) {
    return <p className="section-detail-placeholder">Could not load grade.</p>
  }

  if (grade.percentage == null) {
    return <p className="section-detail-placeholder">No graded submissions yet.</p>
  }

  return (
    <div className="section-detail-grade-summary">
      <span className="section-detail-grade-percentage">{formatPercent(grade.percentage)}</span>
      <span className="section-detail-grade-letter">{grade.letter_grade}</span>
    </div>
  )
}

export default GradeSummary
