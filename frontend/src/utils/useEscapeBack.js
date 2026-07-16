import { useEffect } from 'react'
import { claimEscape, releaseEscape } from './escapeClaim'

export function useEscapeBack(onBack, active) {
  useEffect(() => {
    if (!active) return
    claimEscape()
    function handleKeyDown(e) {
      if (e.key === 'Escape') onBack()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      releaseEscape()
    }
  }, [active, onBack])
}
