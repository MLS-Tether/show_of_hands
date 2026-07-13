import './ToastStack.css'

function ToastStack({ toasts, onDismiss }) {
  if (toasts.length === 0) return null

  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div className="toast" key={t.id} onClick={() => onDismiss(t.id)}>
          <span aria-hidden="true" className="toast-icon">
            🔔
          </span>
          <span className="toast-message">{t.message}</span>
        </div>
      ))}
    </div>
  )
}

export default ToastStack
