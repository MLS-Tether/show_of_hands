import { Link } from 'react-router-dom'
import { useQuestsForSections } from '../../queries'
import './QuestsSummary.css'

function QuestsSummary({ sections }) {
  const sectionIds = (sections ?? []).map((s) => s.section_id)
  const { data: rawQuests, isLoading: questsLoading } = useQuestsForSections(sectionIds)

  const stillLoading = sections === null || (sectionIds.length > 0 && questsLoading)
  const quests = stillLoading ? null : (rawQuests ?? []).filter((q) => !q.completed)

  const loading = quests === null
  const visible = loading ? [] : quests.slice(0, 3)
  const hasMore = !loading && quests.length > 3

  return (
    <section className="quests-summary">
      <div className="widget-label">active quests</div>
      <div className="quests-list">
        {loading && <div className="widget-placeholder">Loading quests…</div>}
        {!loading && quests.length === 0 && (
          <div className="widget-empty">No active quests</div>
        )}
        {!loading &&
          visible.map((q) => (
            <Link
              className="quest-row"
              key={q.quest_id}
              to={`/quests#quest-${q.quest_id}`}
            >
              <span className="quest-title">{q.title}</span>
              <span className="quest-category">{q.category}</span>
            </Link>
          ))}
        {hasMore && (
          <Link to="/quests" className="quest-show-more">
            Show more
          </Link>
        )}
      </div>
    </section>
  )
}

export default QuestsSummary
