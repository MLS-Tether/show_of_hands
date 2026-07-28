import GradeSummary from './GradeSummary'

function StudentGradeDetail({ sectionId, student, onBack }) {
  return (
    <div>
      <button type="button" className="teacher-section-back" onClick={onBack}>
        ← Back
      </button>
      <div className="widget-label">{student.username}'s grade</div>
      <GradeSummary sectionId={sectionId} studentId={student.user_id} />
    </div>
  )
}

export default StudentGradeDetail
