import { Link, useParams } from 'react-router-dom'
import { useSection, useSectionResources } from '../queries'
import { isTeacher } from '../utils/auth'
import TeacherSectionDetail from '../components/section-detail/TeacherSectionDetail'
import GradeSummary from '../components/section-detail/GradeSummary'
import '../styles/shared-ui.css'
import './SectionDetail.css'

const STATUS_BADGE_CLASS = {
  active: 'status-active',
  pending_reassignment: 'status-pending',
  archived: 'status-archived',
}

function SectionDetail() {
  if (isTeacher()) return <TeacherSectionDetail />
  return <StudentSectionDetail />
}

function domainOf(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return ''
  }
}

function StudentSectionDetail() {
  const { sectionId } = useParams()
  const { data: resources = null } = useSectionResources(sectionId)
  const { data: section = null, isError: notFound } = useSection(sectionId)

  const loading = section === null && !notFound

  if (loading) {
    return (
      <section className="section-detail">
        <p className="admin-empty-card">Loading section…</p>
      </section>
    )
  }

  if (notFound) {
    return (
      <section className="section-detail">
        <p className="admin-empty-card">Section not found.</p>
      </section>
    )
  }

  return (
    <section className="section-detail">
      <h1 className="admin-page-h1">{section.class_name}</h1>
      <div className="section-detail-meta">
        <span>{section.teacher_name || 'Unassigned teacher'}</span>
        <span>{section.period}</span>
        <span>
          {section.enrolled_count}/{section.capacity} students
        </span>
        <span className={`admin-status-badge ${STATUS_BADGE_CLASS[section.status] || ''}`}>
          {section.status}
        </span>
        <span>Created {new Date(section.created_at).toLocaleDateString()}</span>
      </div>

      <div className="section-detail-columns">
        <div>
          <div className="widget-label">my grade</div>
          <GradeSummary sectionId={sectionId} />
        </div>

        <div>
          <div className="widget-label">assignments</div>
          {section.assignments.length === 0 ? (
            <p className="admin-empty-card">No assignments</p>
          ) : (
            <div className="section-detail-list">
              {section.assignments.slice(0, 3).map((a) => (
                <div className="section-detail-row" key={a.assignment_id}>
                  <span>{a.title}</span>
                  <span className="section-detail-row-sub">
                    {new Date(a.due_date).toLocaleDateString()}
                  </span>
                </div>
              ))}
              {section.assignments.length > 3 && (
                <Link to="/assignments" className="section-detail-load-more">
                  Load more
                </Link>
              )}
            </div>
          )}
        </div>

        <div>
          <div className="widget-label">quests</div>
          {section.quests.length === 0 ? (
            <p className="admin-empty-card">No quests</p>
          ) : (
            <div className="section-detail-list">
              {section.quests.slice(0, 3).map((q) => (
                <div className="section-detail-row" key={q.quest_id}>
                  <span>{q.title}</span>
                  <span className="section-detail-row-sub">{q.category}</span>
                </div>
              ))}
              {section.quests.length > 3 && (
                <Link to="/quests" className="section-detail-load-more">
                  Load more
                </Link>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="section-detail-resources">
        <div className="widget-label">resources</div>
        {(!resources || resources.length === 0) && (
          <p className="admin-empty-card">No resources posted yet.</p>
        )}
        {resources && resources.length > 0 && (
          <div className="section-detail-list">
            {resources.map((r) => (
              <a
                className="section-detail-row section-detail-resource-row"
                key={r.resource_id}
                href={r.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <span>
                  {r.title}
                  {r.description && (
                    <div className="section-detail-row-sub">{r.description}</div>
                  )}
                </span>
                <span className="section-detail-resource-domain">{domainOf(r.url)}</span>
              </a>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}

export default SectionDetail
