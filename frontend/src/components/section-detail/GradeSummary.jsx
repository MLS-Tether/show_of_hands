import { useSectionGrades } from '../../queries'
import { formatPercent } from '../../utils/format'

function GradeSummary({ sectionId, studentId }) {
  const { data: grade = null, isError: failed } = useSectionGrades(sectionId, studentId || 'me')

  const loading = grade === null && !failed

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
