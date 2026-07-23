import './TutorialOverlay.css'

function TutorialOverlay({ step, stepIndex, stepCount, onNext, onPrev, onSkip }) {
  const isFirst = stepIndex === 0
  const isLast = stepIndex === stepCount - 1

  return (
    <div className="tutorial-overlay">
      <div className="tutorial-wash" />
      <div className="tutorial-card">
        <div className="tutorial-card-header">
          <span className="tutorial-badge">{step.badge}</span>
          <button type="button" className="tutorial-skip" onClick={onSkip}>
            Skip
          </button>
        </div>
        <div className="tutorial-title">{step.title}</div>
        <div className="tutorial-body">{step.body}</div>
        <div className="tutorial-actions">
          {!isFirst && (
            <button type="button" className="tutorial-back" onClick={onPrev}>
              Back
            </button>
          )}
          <button type="button" className="tutorial-next" onClick={onNext}>
            {isLast ? step.cta : 'Next'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TutorialOverlay
