import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listSections } from '../api/sections'
import { extractErrorMessage } from '../lib/apiClient'

export default function SectionsPickerPage() {
  const navigate = useNavigate()
  const [sections, setSections] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    listSections()
      .then(setSections)
      .catch((err) => setError(extractErrorMessage(err, 'Could not load sections.')))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div>
      <div className="page-header">
        <div>
          <h1>Choose a section</h1>
          <p className="page-subtitle">Open a section's bulletin board to post or join a help request.</p>
        </div>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {loading && <p className="page-subtitle">Loading sections…</p>}

      {!loading && !error && sections.length === 0 && (
        <div className="empty-state">No sections available at your school yet.</div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))', gap: 16 }}>
        {sections.map((s) => (
          <div className="card" key={s.section_id}>
            <h3>{s.class_name}</h3>
            <p className="page-subtitle" style={{ margin: '4px 0 12px' }}>
              {s.teacher_name ? `${s.teacher_name} · ` : ''}
              {s.period}
            </p>
            <p style={{ fontSize: '0.85rem', color: 'var(--color-text-muted)', marginBottom: 16 }}>
              {s.enrolled_count}/{s.capacity} enrolled
            </p>
            <button className="btn btn-primary" onClick={() => navigate(`/sections/${s.section_id}/bulletin`)}>
              Open bulletin board
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
