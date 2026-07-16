import { useCallback, useRef, useState } from 'react'
import ToastStack from './ToastStack'
import { ToastContext } from './ToastContext'

const TOAST_DURATION_MS = 2600

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([])
  const nextIdRef = useRef(0)

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const showToast = useCallback(
    (message) => {
      const id = nextIdRef.current++
      setToasts((prev) => [...prev, { id, message }])
      setTimeout(() => dismiss(id), TOAST_DURATION_MS)
    },
    [dismiss]
  )

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <ToastStack toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}
