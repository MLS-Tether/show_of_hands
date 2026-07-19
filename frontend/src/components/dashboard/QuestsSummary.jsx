import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import api from '../../api'
import './QuestsSummary.css'

function QuestsSummary({ sections }) {
  const [quests, setQuests] = useState(null)

  useEffect(() => {
    if (!sections) return
    let cancelled = false
    Promise.allSettled(
      sections.map((s) => api.get(`/sections/${s.section_id}/quests`))
    ).then((results) => {
      if (cancelled) return
      const merged = results
        .filter((r) => r.status === 'fulfilled')
        .flatMap((r) => r.value.data)
        .filter((q) => !q.completed)
      setQuests(merged)
    })
    return () => {
      cancelled = true
    }
  }, [sections])

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
