import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import api from '../api'
import { useDialog } from '../components/DialogContext'
import { keys, useQuestsForSections, useSections } from '../queries'
import '../styles/shared-ui.css'
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
  const { alert } = useDialog()
  const queryClient = useQueryClient()
  const location = useLocation()
  const { data: sections = null } = useSections()
  const [category, setCategory] = useState('all')
  const [completingId, setCompletingId] = useState(null)

  const highlightId = location.hash.startsWith('#quest-')
    ? location.hash.slice('#quest-'.length)
    : null

  const sectionIds = (sections ?? []).map((s) => s.section_id)
  const { data: rawQuests, isLoading: questsLoading } = useQuestsForSections(sectionIds)

  const stillLoading = sections === null || (sectionIds.length > 0 && questsLoading)
  const quests = stillLoading
    ? null
    : (() => {
        const sectionNameById = new Map(sections.map((s) => [s.section_id, s.class_name]))
        return [...(rawQuests ?? [])]
          .map((q) => ({ ...q, section_name: sectionNameById.get(q.section_id) }))
          .sort((a, b) => new Date(b.created_at) - new Date(a.created_at))
      })()

  useEffect(() => {
    if (!quests || !highlightId) return
    const el = document.getElementById(`quest-${highlightId}`)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }, [quests, highlightId])

  async function handleComplete(quest) {
    setCompletingId(quest.quest_id)
    try {
      await api.post(`/quests/${quest.quest_id}/complete`)
      queryClient.setQueryData(keys.quests(sectionIds), (prev) =>
        (prev || []).map((q) => (q.quest_id === quest.quest_id ? { ...q, completed: true } : q))
      )
      queryClient.invalidateQueries({ queryKey: ['points'] })
    } catch (err) {
      await alert(err.response?.data?.message || 'Could not complete this quest.')
    } finally {
      setCompletingId(null)
    }
  }

  const loading = quests === null
  const rows = loading ? [] : quests.filter((q) => category === 'all' || q.category === category)

  return (
    <section className="quests-page">
      <h1 className="admin-page-h1">Quests</h1>
      <div role="tablist" aria-label="Quest category" className="admin-filter-chips">
        <button
          type="button"
          role="tab"
          aria-selected={category === 'all'}
          className={`admin-chip${category === 'all' ? ' active' : ''}`}
          onClick={() => setCategory('all')}
        >
          All
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={category === 'academic'}
          className={`admin-chip${category === 'academic' ? ' active' : ''}`}
          onClick={() => setCategory('academic')}
        >
          Academic
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={category === 'social'}
          className={`admin-chip${category === 'social' ? ' active' : ''}`}
          onClick={() => setCategory('social')}
        >
          Non-academic
        </button>
      </div>

      {loading && <p className="admin-empty-card">Loading quests…</p>}
      {!loading && rows.length === 0 && <p className="admin-empty-card">No quests to show.</p>}
      {!loading && rows.length > 0 && (
        <div className="quests-grid">
          {rows.map((q) => (
            <div
              className={`quest-card${String(q.quest_id) === highlightId ? ' quest-card-highlight' : ''}`}
              id={`quest-${q.quest_id}`}
              key={q.quest_id}
            >
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
                  className="admin-btn-secondary quest-card-complete"
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
