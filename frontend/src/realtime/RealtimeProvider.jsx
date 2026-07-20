import { useEffect, useRef, useState, useCallback } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { keys } from '../queries'
import { playNotificationChime } from '../utils/notificationSound'
import { wsUrlWithFreshToken } from '../utils/ws'
import { invalidateForEvent } from './invalidations'
import { RealtimeContext } from './realtimeContext'

const RECONNECT_DELAY_MS = 3000
const TOAST_DURATION_MS = 6000

// Owns the single /notifications/stream WebSocket for the whole app (moved
// out of NotificationBell, which previously opened its own). Two message
// types arrive on it: new_notification (pushes straight into the
// notifications query cache + surfaces a toast) and data_event (an entity
// changed somewhere the user has access to — mapped to cache invalidations
// via invalidateForEvent). Mount once, near the root of the authenticated
// app shell.
export function RealtimeProvider({ children }) {
  const queryClient = useQueryClient()
  const [toasts, setToasts] = useState([])
  const wsRef = useRef(null)
  const reconnectTimerRef = useRef(null)
  const seenIdsRef = useRef(new Set())
  const hasConnectedOnceRef = useRef(false)

  const dismissToast = useCallback((toastId) => {
    setToasts((prev) => prev.filter((t) => t.id !== toastId))
  }, [])

  useEffect(() => {
    let unmounted = false

    async function connect() {
      const url = await wsUrlWithFreshToken('/notifications/stream')
      if (unmounted) return
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        // A prior connection existed and just dropped/reconnected — cover
        // whatever events were missed during the gap with a one-shot
        // refetch-everything instead of trying to replay them individually.
        if (hasConnectedOnceRef.current) {
          queryClient.invalidateQueries()
        }
        hasConnectedOnceRef.current = true
      }

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.type === 'new_notification') {
          const notification = data.notification
          if (seenIdsRef.current.has(notification.notification_id)) return
          seenIdsRef.current.add(notification.notification_id)

          queryClient.setQueryData(keys.notifications(), (prev) =>
            prev ? [notification, ...prev] : prev
          )
          playNotificationChime()
          setToasts((prev) => [...prev, { id: notification.notification_id, message: notification.message }])
          setTimeout(() => dismissToast(notification.notification_id), TOAST_DURATION_MS)
        } else if (data.type === 'data_event') {
          invalidateForEvent(queryClient, data.event)
        }
      }

      ws.onclose = () => {
        if (unmounted) return
        reconnectTimerRef.current = setTimeout(connect, RECONNECT_DELAY_MS)
      }
    }

    connect()

    return () => {
      unmounted = true
      clearTimeout(reconnectTimerRef.current)
      wsRef.current?.close()
      wsRef.current = null
    }
  }, [queryClient, dismissToast])

  return (
    <RealtimeContext.Provider value={{ toasts, dismissToast }}>
      {children}
    </RealtimeContext.Provider>
  )
}
