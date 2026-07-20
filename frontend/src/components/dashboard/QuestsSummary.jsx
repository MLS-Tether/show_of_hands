import { useQueries } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import api from '../../api'
import { keys } from '../../queries'
import './QuestsSummary.css'

function QuestsSummary({ sections }) {
  const results = useQueries({
    queries: (sections ?? []).map((s) => ({
      queryKey: keys.sectionQuests(s.section_id),
      queryFn: () => api.get(`/sections/${s.section_id}/quests`).then((r) => r.data),
    })),
  })

  const stillLoading = sections === null || results.some((r) => r.isLoading)
  const quests = stillLoading
    ? null
    : results.filter((r) => r.isSuccess).flatMap((r) => r.data).filter((q) => !q.completed)

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
