import { useEffect, useRef } from 'react'
import './Modal.css'

function Modal({ onClose, children }) {
  const dialogRef = useRef(null)

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
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
