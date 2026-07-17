import GradeSummary from './GradeSummary'

function StudentGradeDetail({ sectionId, student }) {
  return (
    <div>
      <p className="teacher-section-back">Press ESC to go back</p>
      <div className="widget-label">{student.username}'s grade</div>
      <GradeSummary sectionId={sectionId} studentId={student.user_id} />
    </div>
  )
}

export default StudentGradeDetail
