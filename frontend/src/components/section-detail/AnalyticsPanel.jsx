import { useState } from 'react'
import { useSectionAnalytics } from '../../queries'
import { formatPercent } from '../../utils/format'

function AnalyticsPanel({ sectionId }) {
  const [attentionPage, setAttentionPage] = useState(1)
  const { data: analytics = null, isError: failed } = useSectionAnalytics(sectionId, attentionPage)

  if (failed) {
    return <p className="teacher-panel-placeholder">Could not load analytics.</p>
  }

  if (!analytics) {
    return <p className="teacher-panel-placeholder">Loading analytics…</p>
  }

  const {
    average_grade,
    assignments,
    points_distribution,
    students_needing_attention,
    attention_total_pages,
  } = analytics

  return (
    <div>
      <div className="widget-label">analytics</div>

      <p>
        Section average grade:{' '}
        {average_grade != null ? formatPercent(average_grade) : 'No graded submissions yet'}
      </p>
      <p>
        Points distribution — min {points_distribution.min ?? '—'}, max {points_distribution.max ?? '—'}, median{' '}
        {points_distribution.median ?? '—'}
      </p>

      <div className="widget-label widget-label-spaced">
        per-assignment completion
      </div>
      {assignments.length === 0 ? (
        <p className="teacher-panel-placeholder">No assignments yet.</p>
      ) : (
        <div className="teacher-panel-list">
          {assignments.map((a) => (
            <div className="teacher-panel-row" key={a.assignment_id}>
              <span>{a.title}</span>
              <span className="teacher-panel-row-sub">
                {a.graded_count}/{a.submitted_count} graded · {formatPercent(a.completion_rate * 100, 0)} submitted
                {a.average_grade != null ? ` · avg ${formatPercent(a.average_grade)}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}

      <div className="widget-label widget-label-spaced">
        needs attention
      </div>
      {students_needing_attention.length === 0 ? (
        <p className="teacher-panel-placeholder">No flagged students.</p>
      ) : (
        <div className="teacher-panel-list">
          {students_needing_attention.map((student) => (
            <div className="teacher-panel-group" key={student.user_id}>
              <div className="teacher-panel-row-heading">{student.username}</div>
              {student.issues.map((issue, i) => (
                <div className="teacher-panel-row teacher-panel-row-nested" key={`${issue.assignment_id}-${i}`}>
                  <span className="teacher-panel-row-sub">
                    {issue.reason === 'no_submission'
                      ? `No submission for "${issue.assignment_title}"`
                      : `Low grade (${formatPercent(issue.grade)}) on "${issue.assignment_title}"`}
                  </span>
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {attention_total_pages > 1 && (
        <div className="teacher-panel-pagination">
          <button
            type="button"
            className="admin-btn-text"
            disabled={attentionPage <= 1}
            onClick={() => setAttentionPage((p) => p - 1)}
          >
            Previous
          </button>
          <span className="teacher-panel-pagination-label">
            Page {attentionPage} of {attention_total_pages}
          </span>
          <button
            type="button"
            className="admin-btn-text"
            disabled={attentionPage >= attention_total_pages}
            onClick={() => setAttentionPage((p) => p + 1)}
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}

export default AnalyticsPanel
