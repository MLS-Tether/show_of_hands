import { formatPercent } from '../utils/format'
import './ReportCard.css'

const KIND_LABELS = {
  assignment: 'Assignment',
  quest: 'Quest',
}

function ReportCard({ reportCard }) {
  if (reportCard.sections.length === 0) {
    return <p className="admin-empty-card">Not enrolled in any sections.</p>
  }

  return (
    <div className="report-card">
      <div className="report-card-summary-table">
        <div className="report-card-summary-row report-card-summary-header">
          <span>Section</span>
          <span>Period</span>
          <span>Grade</span>
          <span>Letter</span>
        </div>
        {reportCard.sections.map((section) => (
          <div className="report-card-summary-row" key={section.section_id}>
            <span>{section.class_name}</span>
            <span>{section.period}</span>
            <span>{section.percentage != null ? formatPercent(section.percentage) : '—'}</span>
            <span>{section.letter_grade || '—'}</span>
          </div>
        ))}
      </div>

      {reportCard.sections.map((section) => (
        <div className="report-card-section" key={section.section_id}>
          <div className="report-card-section-header">
            <div className="report-card-section-header-main">
              <span className="report-card-section-name">{section.class_name}</span>
              <span className="report-card-section-teacher">{section.teacher_name || 'Unassigned'}</span>
            </div>
            <div className="report-card-section-grade">
              <span>{section.percentage != null ? formatPercent(section.percentage) : '—'}</span>
              <span className="report-card-section-letter">{section.letter_grade || '—'}</span>
            </div>
          </div>

          {section.items.length === 0 ? (
            <p className="admin-empty-card">No assignments or quests yet.</p>
          ) : (
            <div className="report-card-items-table">
              <div className="report-card-items-row report-card-items-header">
                <span>Name</span>
                <span>Type</span>
                <span>Category</span>
                <span>Assigned</span>
                <span>Grade</span>
              </div>
              {section.items.map((item) => (
                <div className="report-card-items-row" key={`${item.kind}-${item.item_id}`}>
                  <span>{item.name}</span>
                  <span>{KIND_LABELS[item.kind] || item.kind}</span>
                  <span>{item.category}</span>
                  <span>{new Date(item.assigned_at).toLocaleDateString()}</span>
                  <span>{item.grade != null ? formatPercent(item.grade) : '—'}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

export default ReportCard
