export default function ConfirmSessionModal({ open, submitting, result, error, onConfirm, onClose }) {
  if (!open) return null

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.4)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
      }}
    >
      <div className="card" style={{ width: 360 }}>
        {result ? (
          <>
            <h3 style={{ marginBottom: 8 }}>Thanks!</h3>
            <p className="page-subtitle" style={{ marginBottom: 16 }}>
              {result.session_occurred
                ? `${result.points_awarded} points awarded to everyone in the session.`
                : 'No points were awarded since the session didn\'t happen.'}
            </p>
            <button className="btn btn-primary" onClick={onClose} style={{ width: '100%' }}>
              Back to bulletin board
            </button>
          </>
        ) : (
          <>
            <h3 style={{ marginBottom: 8 }}>Did the study session happen?</h3>
            <p className="page-subtitle" style={{ marginBottom: 16 }}>
              This confirms points for everyone who joined. It can only be done once.
            </p>
            {error && <div className="alert alert-error">{error}</div>}
            <div style={{ display: 'flex', gap: 8 }}>
              <button className="btn btn-primary" disabled={submitting} onClick={() => onConfirm(true)}>
                Yes, it happened
              </button>
              <button className="btn btn-secondary" disabled={submitting} onClick={() => onConfirm(false)}>
                No
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
