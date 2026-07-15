import { useEffect, useRef } from 'react'
import './Modal.css'

function Modal({ onClose, children }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      // Capture phase, so this always runs before Layout.jsx's page-level
      // Escape-to-go-back handler (a bubble-phase listener) regardless of
      // mount order — closing this modal should never also navigate away.
      e.stopPropagation()
      onClose()
    }
    document.addEventListener('keydown', handleKeyDown, true)
    return () => document.removeEventListener('keydown', handleKeyDown, true)
  }, [onClose])

  function handleBackdropClick(e) {
    if (dialogRef.current && !dialogRef.current.contains(e.target)) {
      onClose()
    }
  }

  return (
    <div className="modal-backdrop" onMouseDown={handleBackdropClick}>
      <div className="modal-dialog" role="dialog" aria-modal="true" ref={dialogRef}>
        <button type="button" className="modal-close" aria-label="Close" onClick={onClose}>
          ×
        </button>
        {children}
      </div>
    </div>
  )
}

export default Modal
