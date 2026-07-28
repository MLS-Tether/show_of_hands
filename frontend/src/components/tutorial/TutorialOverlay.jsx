import { useEffect, useRef, useState } from 'react'
import './TutorialOverlay.css'

const CARD_WIDTH = 344
const CARD_HEIGHT = 210
const MARGIN = 16
const ARROW_BOW = 22

function clamp(value, lo, hi) {
  return Math.max(lo, Math.min(hi, value))
}

function computeGeometry(rect, containerWidth, containerHeight) {
  const cw = containerWidth
  const ch = containerHeight
  // The card's CSS caps it at `calc(100vw - 32px)` so it never overflows a
  // narrow phone screen; mirror that same cap here so the positioning math
  // reasons about the width the card will actually render at, instead of
  // always assuming the full 344px (which used to leave the card off-center
  // or its arrow missing the card edge on anything narrower than ~375px).
  const cardWidth = Math.min(CARD_WIDTH, Math.max(240, cw - MARGIN * 2))
  const cardHeight = CARD_HEIGHT

  if (!rect) {
    return {
      hasTarget: false,
      cardWidth,
      cardLeft: (cw - cardWidth) / 2,
      cardTop: (ch - cardHeight) / 2 - 8,
    }
  }

  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const rx = rect.width / 2 + 12
  const ry = rect.height / 2 + 9

  const targetBox = { x0: cx - rx - MARGIN, y0: cy - ry - MARGIN, x1: cx + rx + MARGIN, y1: cy + ry + MARGIN }
  const overlapsTarget = (l, t) =>
    !(l + cardWidth < targetBox.x0 || l > targetBox.x1 || t + cardHeight < targetBox.y0 || t > targetBox.y1)
  const inBounds = (l, t) =>
    l >= MARGIN && t >= MARGIN && l + cardWidth <= cw - MARGIN && t + cardHeight <= ch - MARGIN

  const vMid = clamp(cy - cardHeight / 2, MARGIN, ch - cardHeight - MARGIN)
  const hMid = clamp(cx - cardWidth / 2, MARGIN, cw - cardWidth - MARGIN)

  let candidates
  if (cx < cw * 0.5) {
    candidates = [
      [Math.min(cx + rx + 42, cw - cardWidth - MARGIN), vMid],
      [hMid, cy + ry + 28],
      [cw - cardWidth - 18, vMid],
      [hMid, clamp(cy - ry - 28 - cardHeight, MARGIN, ch - cardHeight - MARGIN)],
    ]
  } else {
    candidates = [
      [clamp(cx - rx - 42 - cardWidth, MARGIN, cw - cardWidth - MARGIN), vMid],
      [hMid, cy + ry + 28],
      [18, vMid],
      [hMid, clamp(cy - ry - 28 - cardHeight, MARGIN, ch - cardHeight - MARGIN)],
    ]
  }

  const pick =
    candidates.find(([l, t]) => !overlapsTarget(l, t) && inBounds(l, t)) ||
    candidates.find(([l, t]) => !overlapsTarget(l, t)) ||
    candidates.find(([l, t]) => inBounds(l, t)) ||
    candidates[0]
  const [cardLeft, cardTop] = pick

  const ccx = cardLeft + cardWidth / 2
  const ccy = cardTop + cardHeight / 2
  const angle = Math.atan2(cy - ccy, cx - ccx)
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  const tx = Math.abs(cos) > 1e-3 ? cardWidth / 2 / Math.abs(cos) : 1e9
  const ty = Math.abs(sin) > 1e-3 ? cardHeight / 2 / Math.abs(sin) : 1e9
  const reach = Math.min(tx, ty)
  const sx = ccx + cos * reach + cos * 6
  const sy = ccy + sin * reach + sin * 6
  const ex = cx - (rx + 6) * cos
  const ey = cy - (ry + 6) * sin
  const nx = -sin
  const ny = cos
  const qx = (sx + ex) / 2 + nx * ARROW_BOW
  const qy = (sy + ey) / 2 + ny * ARROW_BOW
  const arrowPath = `M ${sx.toFixed(1)} ${sy.toFixed(1)} Q ${qx.toFixed(1)} ${qy.toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`

  const headAngle = Math.atan2(ey - qy, ex - qx)
  const headSize = 11
  const p1x = ex - headSize * Math.cos(headAngle - 0.5)
  const p1y = ey - headSize * Math.sin(headAngle - 0.5)
  const p2x = ex - headSize * Math.cos(headAngle + 0.5)
  const p2y = ey - headSize * Math.sin(headAngle + 0.5)
  const arrowHead = `${ex.toFixed(1)},${ey.toFixed(1)} ${p1x.toFixed(1)},${p1y.toFixed(1)} ${p2x.toFixed(1)},${p2y.toFixed(1)}`

  return { hasTarget: true, cx, cy, rx, ry, cardWidth, cardLeft, cardTop, arrowPath, arrowHead }
}

function TutorialOverlay({ step, stepIndex, stepCount, onNext, onPrev, onSkip }) {
  const shellRef = useRef(null)
  const [box, setBox] = useState({ width: 0, height: 0, rect: null })

  useEffect(() => {
    shellRef.current = document.querySelector('.admin-shell')
  }, [])

  useEffect(() => {
    function rectFor(shell, shellRect, tourName) {
      // The same data-tour value can exist on both the desktop sidebar link
      // and its mobile tab-bar counterpart at once — querySelectorAll and
      // pick whichever copy is actually visible right now, since the
      // hidden one (display:none at the current breakpoint) still matches
      // the selector but collapses to an all-zero rect.
      const els = shell.querySelectorAll(`[data-tour="${tourName}"]`)
      for (const el of els) {
        const r = el.getBoundingClientRect()
        if (r.width === 0 && r.height === 0) continue
        return { top: r.top - shellRect.top, left: r.left - shellRect.left, width: r.width, height: r.height }
      }
      return null
    }

    function measure() {
      const shell = shellRef.current
      if (!shell) return
      const shellRect = shell.getBoundingClientRect()
      let rect = null
      if (step.target) {
        // On mobile the sidebar (and every nav-* target it holds) is hidden
        // in favor of the bottom tab bar, so fall back to whichever of the
        // step's real target or the tab bar's own copy of it is actually
        // visible right now, and finally to the tab bar's "More" button for
        // items tucked inside that sheet on mobile (e.g. every admin nav
        // item, or "My sections" for students/teachers).
        rect = rectFor(shell, shellRect, step.target) || rectFor(shell, shellRect, 'mobile-more')
      }
      setBox({ width: shellRect.width, height: shellRect.height, rect })
    }
    // Double rAF: waits for the browser to finish the layout pass triggered
    // by the step change (e.g. a newly-mounted target element) before
    // measuring, same as the original prototype this was ported from.
    let raf2 = null
    const raf1 = requestAnimationFrame(() => {
      raf2 = requestAnimationFrame(measure)
    })
    window.addEventListener('resize', measure)
    return () => {
      cancelAnimationFrame(raf1)
      if (raf2 !== null) cancelAnimationFrame(raf2)
      window.removeEventListener('resize', measure)
    }
  }, [step])

  const geo = computeGeometry(box.rect, box.width, box.height)
  const isFirst = stepIndex === 0
  const isLast = stepIndex === stepCount - 1

  return (
    <div className="tutorial-overlay">
      <div className="tutorial-wash" />
      {geo.hasTarget && (
        <svg className="tutorial-svg" width={box.width} height={box.height}>
          <ellipse
            className="tutorial-ellipse"
            cx={geo.cx}
            cy={geo.cy}
            rx={geo.rx}
            ry={geo.ry}
            transform={`rotate(-3 ${geo.cx} ${geo.cy})`}
          />
          <path className="tutorial-arrow-path" d={geo.arrowPath} />
          <polygon className="tutorial-arrow-head" points={geo.arrowHead} />
        </svg>
      )}
      <div className="tutorial-card" style={{ left: geo.cardLeft, top: geo.cardTop, width: geo.cardWidth }}>
        <div className="tutorial-card-header">
          <div className="tutorial-icon">✋</div>
          <div className="tutorial-header-text">
            <div className="tutorial-badge">{step.badge}</div>
            <div className="tutorial-progress-label">
              {isLast ? 'All quests cleared!' : `Quest ${stepIndex} of ${stepCount - 2}`}
            </div>
          </div>
          <button type="button" className="tutorial-skip" onClick={onSkip}>
            Skip
          </button>
        </div>
        <div className="tutorial-title">{step.title}</div>
        <div className="tutorial-body">{step.body}</div>
        <div className="tutorial-progress-track">
          <div
            className="tutorial-progress-fill"
            style={{ width: `${Math.round((stepIndex / (stepCount - 1)) * 100)}%` }}
          />
        </div>
        <div className="tutorial-actions">
          {!isFirst && (
            <button type="button" className="tutorial-back" onClick={onPrev}>
              Back
            </button>
          )}
          <button type="button" className="tutorial-next" onClick={onNext}>
            {isLast ? step.cta : 'Next →'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TutorialOverlay
