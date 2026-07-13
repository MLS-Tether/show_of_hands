import { useEffect, useState } from 'react'
import api from '../api'
import './Quests.css'

const CATEGORY_LABELS = {
  academic: 'Academic',
  social: 'Non-academic',
}

const QUEST_TYPE_LABELS = {
  daily: 'Daily',
  weekly: 'Weekly',
  monthly: 'Monthly',
}

function Quests() {
  const [sections, setSections] = useState(null)
  const [quests, setQuests] = useState(null)
  const [category, setCategory] = useState('all')
  const [completingId, setCompletingId] = useState(null)

  useEffect(() => {
    let cancelled = false
    api
      .get('/sections')
      .then(({ data }) => {
        if (!cancelled) setSections(data)
      })
      .catch(() => {
        if (!cancelled) setSections([])
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (!sections) return
    let cancelled = false
    Promise.allSettled(
      sections.map((s) => api.get(`/sections/${s.section_id}/quests`))
    ).then((results) => {
      if (cancelled) return
      const merged = results.flatMap((r, i) => {
        if (r.status !== 'fulfilled') return []
        const section = sections[i]
        return r.value.data.map((q) => ({ ...q, section_name: section.class_name }))
      })
      merged.sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      setQuests(merged)
    })
    return () => {
      cancelled = true
    }
  }, [sections])

  async function handleComplete(quest) {
    setCompletingId(quest.quest_id)
    try {
      await api.post(`/quests/${quest.quest_id}/complete`)
      setQuests((prev) =>
        prev.map((q) => (q.quest_id === quest.quest_id ? { ...q, completed: true } : q))
      )
    } catch (err) {
      window.alert(err.response?.data?.message || 'Could not complete this quest.')
    } finally {
      setCompletingId(null)
    }
  }

  const loading = sections === null || quests === null
  const rows = loading ? [] : quests.filter((q) => category === 'all' || q.category === category)

  return (
    <section className="quests-page">
      <h1>Quests</h1>
      <div role="tablist" aria-label="Quest category" className="quests-tabs">
        <button
          type="button"
          role="tab"
          aria-selected={category === 'all'}
          className={`quests-tab${category === 'all' ? ' active' : ''}`}
          onClick={() => setCategory('all')}
        >
          All
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={category === 'academic'}
          className={`quests-tab${category === 'academic' ? ' active' : ''}`}
          onClick={() => setCategory('academic')}
        >
          Academic
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={category === 'social'}
          className={`quests-tab${category === 'social' ? ' active' : ''}`}
          onClick={() => setCategory('social')}
        >
          Non-academic
        </button>
      </div>

      {loading && <p className="quests-placeholder">Loading quests…</p>}
      {!loading && rows.length === 0 && <p className="quests-placeholder">No quests to show.</p>}
      {!loading && rows.length > 0 && (
        <div className="quests-grid">
          {rows.map((q) => (
            <div className="quest-card" key={q.quest_id}>
              <div className="quest-card-header">
                <span className="quest-card-title">{q.title}</span>
                <span className={`quest-card-category quest-card-category-${q.category}`}>
                  {CATEGORY_LABELS[q.category] || q.category}
                </span>
              </div>

              <p className="quest-card-description">{q.description}</p>

              <div className="quest-card-meta">
                <span className="quest-card-section">{q.section_name}</span>
                <span className="quest-card-type">{QUEST_TYPE_LABELS[q.quest_type] || q.quest_type}</span>
                <span className="quest-card-points">{q.point_value} pts</span>
              </div>

              {q.completed === true && (
                <span className="quest-card-status quest-card-status-done">Completed</span>
              )}
              {q.completed === false && (
                <button
                  type="button"
                  className="quest-card-complete"
                  disabled={completingId === q.quest_id}
                  onClick={() => handleComplete(q)}
                >
                  {completingId === q.quest_id ? 'Completing…' : 'Mark complete'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}
    </section>
  )
}

export default Quests
