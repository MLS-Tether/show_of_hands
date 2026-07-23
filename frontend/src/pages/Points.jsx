import { useState } from 'react'
import { Navigate } from 'react-router-dom'
import { keepPreviousData } from '@tanstack/react-query'
import { usePoints } from '../queries'
import { getUserId, isTeacher } from '../utils/auth'
import '../styles/shared-ui.css'
import './Points.css'

const PAGE_SIZE = 10

const SOURCE_LABELS = {
  assignment: 'Assignment',
  quest: 'Quest',
  help_request: 'Help Request',
}

function formatAwardedAt(dateStr) {
  return new Intl.DateTimeFormat('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  }).format(new Date(dateStr))
}

function Points() {
  const [page, setPage] = useState(1)
  const { data = null, isLoading, isError: error } = usePoints(getUserId(), page, PAGE_SIZE, {
    placeholderData: keepPreviousData,
  })

  // Teachers don't earn points; keep them off this student-only page
  if (isTeacher()) {
    return <Navigate to="/dashboard" replace />
  }

  const loading = isLoading
  const totalPages = data ? Math.max(1, Math.ceil(data.total_count / data.page_size)) : 1

  return (
    <section className="points-page">
      <h1 className="admin-page-h1">Points</h1>

      {loading && <p className="admin-empty-card">Loading points…</p>}
      {error && <p className="admin-empty-card">Couldn't load points.</p>}

      {data && (
        <>
          <div className="points-balance">
            <span className="points-balance-value">{data.total_points}</span>
            <span className="points-balance-label">total points</span>
          </div>

          {data.transactions.length === 0 && (
            <p className="admin-empty-card">No point transactions yet.</p>
          )}

          {data.transactions.length > 0 && (
            <div className="points-list">
              {data.transactions.map((t) => (
                <div className="points-row" key={t.transaction_id}>
                  <span className="points-row-source">
                    {SOURCE_LABELS[t.source] ?? t.source}
                  </span>
                  {t.source_label && (
                    <span className="points-row-label">{t.source_label}</span>
                  )}
                  <span className="points-row-date">{formatAwardedAt(t.awarded_at)}</span>
                  <span className="points-row-amount">+{t.amount}</span>
                </div>
              ))}
            </div>
          )}

          {totalPages > 1 && (
            <div className="points-pagination">
              <button
                type="button"
                className="admin-btn-secondary"
                disabled={page <= 1}
                onClick={() => setPage((p) => p - 1)}
              >
                Previous
              </button>
              <span className="points-pagination-status">
                Page {data.page} of {totalPages}
              </span>
              <button
                type="button"
                className="admin-btn-secondary"
                disabled={page >= totalPages}
                onClick={() => setPage((p) => p + 1)}
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default Points
