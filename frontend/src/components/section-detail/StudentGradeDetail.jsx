import { useSectionGradeDetail } from '../../queries'
import { formatPercent } from '../../utils/format'
import GradeSummary from './GradeSummary'

function dueDateClass(assignment) {
  const due = new Date(assignment.due_date)
  if (assignment.submitted_at) {
    return new Date(assignment.submitted_at) <= due ? 'grade-detail-date-on-time' : 'grade-detail-date-late'
  }
  return due < new Date() ? 'grade-detail-date-late' : ''
}

function StudentGradeDetail({ sectionId, student, onBack }) {
  const { data, isError: failed } = useSectionGradeDetail(sectionId, student.user_id)

  return (
    <div>
      <button type="button" className="teacher-section-back" onClick={onBack}>
        ← Back
      </button>
      <div className="widget-label">{student.username}'s grade</div>
      <GradeSummary sectionId={sectionId} studentId={student.user_id} />

      <div className="widget-label widget-label-spaced">assignments</div>
      {failed && <p className="teacher-panel-placeholder">Could not load assignments.</p>}
      {!failed && !data && <p className="teacher-panel-placeholder">Loading…</p>}
      {data && (
        data.assignments.length === 0 ? (
          <p className="teacher-panel-placeholder">No assignments yet.</p>
        ) : (
          <div className="teacher-panel-list">
            {data.assignments.map((a) => (
              <div className="teacher-panel-row" key={a.assignment_id}>
                <span>{a.title}</span>
                <span className="teacher-panel-row-sub">
                  {a.category} · due{' '}
                  <span className={dueDateClass(a)}>{new Date(a.due_date).toLocaleDateString()}</span> ·{' '}
                  {a.status === 'graded' ? formatPercent(a.grade) : a.status.replace('_', ' ')}
                </span>
              </div>
            ))}
          </div>
        )
      )}

      <div className="widget-label widget-label-spaced">study rooms</div>
      {data && (
        data.study_rooms.length === 0 ? (
          <p className="teacher-panel-placeholder">No study rooms created.</p>
        ) : (
          <div className="teacher-panel-list">
            {data.study_rooms.map((r) => (
              <div className="teacher-panel-row" key={r.room_id}>
                <span>{r.topic}</span>
                <span className="teacher-panel-row-sub">
                  {r.status} · {new Date(r.created_at).toLocaleString()} · {r.members.length} member(s)
                </span>
              </div>
            ))}
          </div>
        )
      )}
    </div>
  )
}

export default StudentGradeDetail
