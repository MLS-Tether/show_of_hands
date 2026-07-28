import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAssignments, useQuestsForSections } from '../../queries'
import SectionCard from './SectionCard'
import './SectionsSummary.css'

function SectionsSummary({ sections }) {
  const loading = sections === null
  const sectionIds = (sections ?? []).map((s) => s.section_id)

  const { data: rawAssignments = null } = useAssignments()
  const { data: rawQuests, isLoading: questsLoading } = useQuestsForSections(sectionIds)
  // Lazy-initialized once at mount rather than recomputed on every render,
  // which would call the impure Date.now() during render.
  const [now] = useState(() => Date.now())

  const dataLoading = rawAssignments === null || (sectionIds.length > 0 && questsLoading)

  function assignmentsForSection(sectionId) {
    const all = (rawAssignments ?? []).filter((a) => a.section_id === sectionId)
    const upcoming = all
      .filter((a) => new Date(a.due_date).getTime() >= now)
      .sort((a, b) => new Date(a.due_date) - new Date(b.due_date))
    if (upcoming.length > 0) return upcoming
    // No upcoming assignments for this section — fall back to past-due ones
    // (most recent first) so there's still something to click through to.
    return all
      .filter((a) => new Date(a.due_date).getTime() < now)
      .sort((a, b) => new Date(b.due_date) - new Date(a.due_date))
  }

  function questsForSection(sectionId) {
    return (rawQuests ?? []).filter((q) => q.section_id === sectionId && !q.completed)
  }

  return (
    <section className="sections-summary">
      <div className="widget-label">my sections</div>
      <div className="sections-grid">
        {loading && <div className="widget-placeholder">Loading sections…</div>}
        {!loading && sections.length === 0 && (
          <div className="widget-empty">No sections yet</div>
        )}
        {!loading &&
          sections.map((s) => (
            <SectionCard
              key={s.section_id}
              section={s}
              assignments={assignmentsForSection(s.section_id)}
              quests={questsForSection(s.section_id)}
              dataLoading={dataLoading}
            />
          ))}
        <Link to="/sections" className="join-section-card">
          + join section
        </Link>
      </div>
    </section>
  )
}

export default SectionsSummary
