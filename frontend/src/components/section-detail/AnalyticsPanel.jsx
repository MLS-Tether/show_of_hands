import { useEffect, useState } from 'react'
import api from '../../api'

function AnalyticsPanel({ sectionId }) {
  const [analytics, setAnalytics] = useState(null)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    let cancelled = false
    api
      .get(`/sections/${sectionId}/analytics`)
      .then(({ data }) => {
        if (!cancelled) setAnalytics(data)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [sectionId])

  if (failed) {
    return <p className="teacher-panel-placeholder">Could not load analytics.</p>
  }

  if (!analytics) {
    return <p className="teacher-panel-placeholder">Loading analytics…</p>
  }

  const { average_grade, assignments, points_distribution, students_needing_attention } = analytics

  return (
    <div>
      <div className="widget-label">analytics</div>

      <p>
        Section average grade:{' '}
        {average_grade != null ? average_grade.toFixed(1) : 'No graded submissions yet'}
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
                {a.graded_count}/{a.submitted_count} graded · {(a.completion_rate * 100).toFixed(0)}% submitted
                {a.average_grade != null ? ` · avg ${a.average_grade.toFixed(1)}` : ''}
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
          {students_needing_attention.map((s, i) => (
            <div className="teacher-panel-row" key={`${s.user_id}-${s.assignment_id}-${i}`}>
              <span>{s.username}</span>
              <span className="teacher-panel-row-sub">
                {s.reason === 'no_submission'
                  ? `No submission for "${s.assignment_title}"`
                  : `Low grade (${s.grade}) on "${s.assignment_title}"`}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AnalyticsPanel
