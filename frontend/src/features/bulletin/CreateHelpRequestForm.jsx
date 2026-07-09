import { useState } from 'react'

export default function CreateHelpRequestForm({ onSubmit, onCancel, submitting }) {
  const [topic, setTopic] = useState('')
  const [description, setDescription] = useState('')
  const [groupSize, setGroupSize] = useState(2)
  const [durationMinutes, setDurationMinutes] = useState(20)

  function handleSubmit(e) {
    e.preventDefault()
    onSubmit({ topic, description, groupSize: Number(groupSize), durationMinutes: Number(durationMinutes) })
  }

  return (
    <form className="card" onSubmit={handleSubmit} style={{ marginBottom: 20 }}>
      <h3 style={{ marginBottom: 16 }}>Post a help request</h3>

      <div className="form-field">
        <label htmlFor="topic">Topic</label>
        <input id="topic" value={topic} onChange={(e) => setTopic(e.target.value)} required maxLength={120} />
      </div>

      <div className="form-field">
        <label htmlFor="description">Description (optional)</label>
        <textarea
          id="description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          rows={3}
        />
      </div>

      <div style={{ display: 'flex', gap: 12 }}>
        <div className="form-field" style={{ flex: 1 }}>
          <label htmlFor="groupSize">Group size</label>
          <input
            id="groupSize"
            type="number"
            min={2}
            max={20}
            value={groupSize}
            onChange={(e) => setGroupSize(e.target.value)}
            required
          />
        </div>
        <div className="form-field" style={{ flex: 1 }}>
          <label htmlFor="duration">Duration (minutes)</label>
          <input
            id="duration"
            type="number"
            min={5}
            max={120}
            value={durationMinutes}
            onChange={(e) => setDurationMinutes(e.target.value)}
            required
          />
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-primary" type="submit" disabled={submitting}>
          {submitting ? 'Posting…' : 'Post request'}
        </button>
        <button className="btn btn-ghost" type="button" onClick={onCancel} disabled={submitting}>
          Cancel
        </button>
      </div>
    </form>
  )
}
