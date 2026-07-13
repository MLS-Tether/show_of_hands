import { Link } from 'react-router-dom'
import './SectionsSummary.css'

function SectionsSummary({ sections }) {
  const loading = sections === null

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
            <Link to={`/sections/${s.section_id}`} className="section-card" key={s.section_id}>
              <div className="section-card-title">{s.class_name}</div>
              <div className="section-card-sub">{s.period}</div>
            </Link>
          ))}
        <Link to="/sections" className="join-section-card">
          + join section
        </Link>
      </div>
    </section>
  )
}

export default SectionsSummary
