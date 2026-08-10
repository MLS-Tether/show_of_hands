import { useSectionGradeDetail } from '../../queries'
import { formatPercent } from '../../utils/format'
import GradeSummary from './GradeSummary'
import '../../pages/Quests.css'

const QUEST_CATEGORY_LABELS = { academic: 'Academic', social: 'Non-academic' }

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

      <div className="widget-label widget-label-spaced">
        quests completed{data ? ` (${data.quest_completions.length})` : ''}
      </div>
      {failed && <p className="teacher-panel-placeholder">Could not load quests.</p>}
      {!failed && !data && <p className="teacher-panel-placeholder">Loading…</p>}
      {data && (
        <>
          <div className="section-detail-grade-summary">
            <span className="section-detail-grade-percentage">{data.total_quest_points}</span>
            <span className="section-detail-grade-letter">pts from quests</span>
          </div>
          {data.quest_completions.length === 0 ? (
            <p className="teacher-panel-placeholder">No quests completed yet.</p>
          ) : (
            <div className="teacher-panel-list">
              {data.quest_completions.map((q) => (
                <div className="teacher-panel-row" key={q.quest_completion_id}>
                  <span>{q.title}</span>
                  <span className="teacher-panel-row-sub">
                    <span className={`quest-card-category quest-card-category-${q.category}`}>
                      {QUEST_CATEGORY_LABELS[q.category] || q.category}
                    </span>
                    {' · '}
                    {q.points_awarded} pts · {new Date(q.completed_at).toLocaleDateString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </>
      )}

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
