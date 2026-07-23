import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import api from '../../api'
import { keys, useSectionQuests } from '../../queries'
import { useDialog } from '../DialogContext'
import '../../styles/shared-ui.css'
import '../../pages/Quests.css'

const CATEGORY_LABELS = { academic: 'Academic', social: 'Non-academic' }
const QUEST_TYPE_LABELS = { daily: 'Daily', weekly: 'Weekly', monthly: 'Monthly' }
const SOCIAL_MULTIPLIER = 1.5

function QuestsPanel({ sectionId }) {
  const { alert } = useDialog()
  const queryClient = useQueryClient()
  const [category, setCategory] = useState('all')
  const [showForm, setShowForm] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [questCategory, setQuestCategory] = useState('academic')
  const [pointValue, setPointValue] = useState(10)
  const [questType, setQuestType] = useState('daily')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState(null)

  const { data: quests = null } = useSectionQuests(sectionId)

  async function handleCreate(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await api.post(`/sections/${sectionId}/quests`, {
        title,
        description,
        category: questCategory,
        point_value: Number(pointValue),
        quest_type: questType,
        assigned_to: 'all',
      })
      setTitle('')
      setDescription('')
      setPointValue(10)
      setShowForm(false)
      queryClient.invalidateQueries({ queryKey: keys.sectionQuests(sectionId) })
      queryClient.invalidateQueries({ queryKey: keys.section(sectionId) })
    } catch (err) {
      setError(err.response?.data?.detail || 'Could not create quest.')
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDelete(quest) {
    setDeletingId(quest.quest_id)
    try {
      await api.delete(`/quests/${quest.quest_id}`)
      queryClient.setQueryData(keys.sectionQuests(sectionId), (prev) =>
        (prev || []).filter((q) => q.quest_id !== quest.quest_id)
      )
      queryClient.invalidateQueries({ queryKey: keys.section(sectionId) })
    } catch (err) {
      if (err.response?.status === 403) {
        await alert("Can't delete a system quest.")
      } else {
        await alert(err.response?.data?.detail || 'Could not delete this quest.')
      }
    } finally {
      setDeletingId(null)
    }
  }

  const loading = quests === null
  const rows = loading ? [] : quests.filter((q) => category === 'all' || q.category === category)
  const storedPoints =
    questCategory === 'social' ? Math.round(Number(pointValue || 0) * SOCIAL_MULTIPLIER) : Number(pointValue || 0)

  return (
    <div className="quests-page">
      <div className="widget-label">quests</div>

      {!showForm && (
        <button
          type="button"
          className="teacher-panel-button teacher-panel-add-toggle"
          onClick={() => setShowForm(true)}
        >
          + new quest
        </button>
      )}

      {showForm && (
        <form className="teacher-panel-form" onSubmit={handleCreate}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Description
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={2} required />
          </label>
          <div className="teacher-panel-form-row">
            <label>
              Category
              <select value={questCategory} onChange={(e) => setQuestCategory(e.target.value)}>
                <option value="academic">Academic</option>
                <option value="social">Non-academic</option>
              </select>
            </label>
            <label>
              Quest type
              <select value={questType} onChange={(e) => setQuestType(e.target.value)}>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </label>
            <label>
              Points
              <input
                type="number"
                min="1"
                value={pointValue}
                onChange={(e) => setPointValue(e.target.value)}
                required
              />
            </label>
          </div>
          {questCategory === 'social' && (
            <p className="teacher-panel-multiplier-hint">
              Non-academic quests get a 1.5x bonus — students will actually receive {storedPoints} pts.
            </p>
          )}
          {error && <p className="teacher-panel-error">{error}</p>}
          <div className="teacher-panel-form-actions">
            <button type="button" className="teacher-panel-button" onClick={() => setShowForm(false)}>
              Cancel
            </button>
            <button type="submit" className="teacher-panel-button" disabled={submitting}>
              {submitting ? 'Creating…' : 'Create'}
            </button>
          </div>
        </form>
      )}

      <div role="tablist" aria-label="Quest category" className="admin-filter-chips">
        {['all', 'academic', 'social'].map((c) => (
          <button
            key={c}
            type="button"
            role="tab"
            aria-selected={category === c}
            className={`admin-chip${category === c ? ' active' : ''}`}
            onClick={() => setCategory(c)}
          >
            {c === 'all' ? 'All' : CATEGORY_LABELS[c]}
          </button>
        ))}
      </div>

      {loading && <p className="admin-empty-card">Loading quests…</p>}
      {!loading && rows.length === 0 && <p className="admin-empty-card">No quests to show.</p>}
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
                <span className="quest-card-type">{QUEST_TYPE_LABELS[q.quest_type] || q.quest_type}</span>
                <span className="quest-card-points">{q.point_value} pts</span>
              </div>
              <button
                type="button"
                className="admin-btn-danger quest-card-complete"
                disabled={deletingId === q.quest_id}
                onClick={() => handleDelete(q)}
              >
                {deletingId === q.quest_id ? 'Deleting…' : 'Delete'}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default QuestsPanel
