import { useEffect, useState } from 'react'
import api from '../api'
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
  const [data, setData] = useState(null)
  const [page, setPage] = useState(1)
  const [error, setError] = useState(false)

  useEffect(() => {
    const userId = localStorage.getItem('user_id')
    if (!userId) return
    let cancelled = false

    api
      .get(`/users/${userId}/points`, { params: { page, page_size: PAGE_SIZE } })
      .then(({ data }) => {
        if (!cancelled) {
          setData(data)
          setError(false)
        }
      })
      .catch(() => {
        if (!cancelled) setError(true)
      })

    return () => {
      cancelled = true
    }
  }, [page])

  const loading = data === null && !error
  const totalPages = data ? Math.max(1, Math.ceil(data.total_count / data.page_size)) : 1

  return (
    <section className="points-page">
      <h1>Points</h1>

      {loading && <p className="points-placeholder">Loading points…</p>}
      {error && <p className="points-placeholder">Couldn't load points.</p>}

      {data && (
        <>
          <div className="points-balance">
            <span className="points-balance-value">{data.total_points}</span>
            <span className="points-balance-label">total points</span>
          </div>

          {data.transactions.length === 0 && (
            <p className="points-placeholder">No point transactions yet.</p>
          )}

          {data.transactions.length > 0 && (
            <div className="points-list">
              {data.transactions.map((t) => (
                <div className="points-row" key={t.transaction_id}>
                  <span className="points-row-source">
                    {SOURCE_LABELS[t.source] ?? t.source}
                  </span>
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
