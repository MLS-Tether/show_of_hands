import { createContext, useCallback, useContext, useRef, useState } from 'react'
import Modal from './Modal'
import './DialogProvider.css'

const DialogContext = createContext(null)

export function DialogProvider({ children }) {
  const [dialog, setDialog] = useState(null)
  const resolverRef = useRef(null)

  const confirm = useCallback((message) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve
      setDialog({ type: 'confirm', message })
    })
  }, [])

  const alert = useCallback((message) => {
    return new Promise((resolve) => {
      resolverRef.current = resolve
      setDialog({ type: 'alert', message })
    })
  }, [])

  function settle(value) {
    resolverRef.current?.(value)
    resolverRef.current = null
    setDialog(null)
  }

  return (
    <DialogContext.Provider value={{ confirm, alert }}>
      {children}
      {dialog && (
        <Modal onClose={() => settle(dialog.type === 'confirm' ? false : undefined)}>
          <p className="dialog-message">{dialog.message}</p>
          <div className="dialog-actions">
            {dialog.type === 'confirm' && (
              <button type="button" className="dialog-button-secondary" onClick={() => settle(false)}>
                Cancel
              </button>
            )}
            <button
              type="button"
              className="dialog-button-primary"
              autoFocus
              onClick={() => settle(dialog.type === 'confirm' ? true : undefined)}
            >
              OK
            </button>
          </div>
        </Modal>
      )}
    </DialogContext.Provider>
  )
}

export function useDialog() {
  const ctx = useContext(DialogContext)
  if (!ctx) throw new Error('useDialog must be used within a DialogProvider')
  return ctx
}
