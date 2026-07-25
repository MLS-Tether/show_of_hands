import { Link, useNavigate } from 'react-router-dom'
import { formatDueDate } from '../../utils/formatDueDate'
import { useSidebarPeek } from '../SidebarPeekContext'

function SectionCard({ section, assignments, quests, dataLoading }) {
  const navigate = useNavigate()
  const peekSidebar = useSidebarPeek()

  function goTo(path) {
    navigate(path)
    peekSidebar()
  }

  return (
    <div className="section-card-wrap">
      <Link to={`/sections/${section.section_id}`} className="section-card">
        <div className="section-card-title">{section.class_name}</div>
        <div className="section-card-sub">{section.period}</div>
      </Link>
      <div className="section-hover-panel" role="group" aria-label={`${section.class_name} upcoming items`}>
        <div className="section-hover-col">
          <div className="section-hover-label">Assignments</div>
          {dataLoading && <div className="section-hover-empty">Loading…</div>}
          {!dataLoading && assignments.length === 0 && (
            <div className="section-hover-empty">No assignments</div>
          )}
          {!dataLoading &&
            assignments.slice(0, 4).map((a) => (
              <button
                type="button"
                key={a.assignment_id}
                className="section-hover-row"
                onClick={() =>
                  goTo(`/assignments?section=${section.section_id}#assignment-${a.assignment_id}`)
                }
              >
                <span className="section-hover-row-title">{a.title}</span>
                <span className="section-hover-row-meta">{formatDueDate(a.due_date)}</span>
              </button>
            ))}
        </div>
        <div className="section-hover-col">
          <div className="section-hover-label">Quests</div>
          {dataLoading && <div className="section-hover-empty">Loading…</div>}
          {!dataLoading && quests.length === 0 && (
            <div className="section-hover-empty">No active quests</div>
          )}
          {!dataLoading &&
            quests.slice(0, 4).map((q) => (
              <button
                type="button"
                key={q.quest_id}
                className="section-hover-row"
                onClick={() => goTo(`/quests?section=${section.section_id}#quest-${q.quest_id}`)}
              >
                <span className="section-hover-row-title">{q.title}</span>
                <span className="section-hover-row-meta">{q.category}</span>
              </button>
            ))}
        </div>
      </div>
    </div>
  )
}

export default SectionCard
