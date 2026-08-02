import { useEffect, useState } from 'react'
import './BadgesSection.css'

function formatProgress(progress) {
  const isPercent = progress.unit.startsWith('%')
  const current = Math.round(progress.current)
  const target = Math.round(progress.target)
  return isPercent ? `${current}% / ${target}% grade in a section` : `${current} / ${target} ${progress.unit}`
}

function BadgesSection({ badges, featuredItemId, pendingId, onSetFeatured, onClearFeatured }) {
  // Hover alone never fires on touch devices, so tapping the info dot toggles
  // the same tooltip open/closed -- desktop still gets it for free on hover.
  const [openTooltipId, setOpenTooltipId] = useState(null)

  useEffect(() => {
    if (openTooltipId === null) return
    const closeOnOutsideClick = (event) => {
      if (!event.target.closest('.badges-card-tooltip-wrapper')) setOpenTooltipId(null)
    }
    document.addEventListener('click', closeOnOutsideClick)
    return () => document.removeEventListener('click', closeOnOutsideClick)
  }, [openTooltipId])

  if (badges.length === 0) {
    return <p className="admin-empty-card">No badges yet.</p>
  }

  return (
    <div className="badges-grid">
      {badges.map((badge) => {
        const isFeatured = badge.item_id === featuredItemId
        const pending = pendingId === badge.item_id
        const tooltipOpen = openTooltipId === badge.item_id
        return (
          <div className={`badges-card${badge.owned ? '' : ' badges-card-locked'}`} key={badge.item_id}>
            <div
              className={`badges-card-image badges-card-tooltip-wrapper${tooltipOpen ? ' badges-card-tooltip-open' : ''}`}
            >
              <img src={badge.image_url} alt="" />
              {badge.progress && (
                <>
                  <button
                    type="button"
                    className="badges-card-info"
                    aria-label={`Unlock requirement for ${badge.name}`}
                    aria-expanded={tooltipOpen}
                    onClick={(event) => {
                      event.stopPropagation()
                      setOpenTooltipId(tooltipOpen ? null : badge.item_id)
                    }}
                  >
                    i
                  </button>
                  <div className="badges-card-tooltip" role="tooltip">
                    {formatProgress(badge.progress)}
                  </div>
                </>
              )}
            </div>
            <span className="badges-card-title">{badge.name}</span>
            {badge.description && <p className="badges-card-description">{badge.description}</p>}
            <div className="badges-card-footer">
              {!badge.owned ? (
                <span className="badges-card-status badges-card-status-locked">Locked</span>
              ) : isFeatured ? (
                <>
                  <span className="badges-card-status badges-card-status-featured">Featured</span>
                  <button
                    type="button"
                    className="admin-btn-text"
                    disabled={pending}
                    onClick={onClearFeatured}
                  >
                    Remove
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="admin-btn-secondary"
                  disabled={pending}
                  onClick={() => onSetFeatured(badge.item_id)}
                >
                  {pending ? 'Saving…' : 'Set as featured'}
                </button>
              )}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export default BadgesSection
