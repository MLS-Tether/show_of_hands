import { useEffect, useRef } from 'react'

const REFRESH_EVENT = 'sh:refresh'
// Real-time push (notifications WebSocket -> broadcastRefresh) handles the
// instant updates now, so this interval is just a rare safety net for missed
// pushes — not the primary way pages stay fresh. Keep it long.
const DEFAULT_INTERVAL_MS = 180000

// Fired whenever new content is known to exist (e.g. a new notification
// arrived) so every mounted page can refetch immediately instead of waiting
// for its next poll tick.
export function broadcastRefresh() {
  window.dispatchEvent(new Event(REFRESH_EVENT))
}

// Keeps a page's data current without a manual reload: refetches on an
// interval, on tab focus/visibility, and whenever broadcastRefresh() fires.
export function useAutoRefresh(refetch, intervalMs = DEFAULT_INTERVAL_MS) {
  const refetchRef = useRef(refetch)
  refetchRef.current = refetch

  useEffect(() => {
    function run() {
      refetchRef.current()
    }
    function handleVisibility() {
      if (document.visibilityState === 'visible') run()
    }

    const interval = setInterval(run, intervalMs)
    window.addEventListener(REFRESH_EVENT, run)
    window.addEventListener('focus', run)
    document.addEventListener('visibilitychange', handleVisibility)

    return () => {
      clearInterval(interval)
      window.removeEventListener(REFRESH_EVENT, run)
      window.removeEventListener('focus', run)
      document.removeEventListener('visibilitychange', handleVisibility)
    }
  }, [intervalMs])
}
