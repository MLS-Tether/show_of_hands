import { useCallback, useEffect, useRef, useState } from 'react'
import { getAccessToken } from '../../auth/tokenStorage'

const WS_BASE = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000/api'

// Deliberately no reconnect logic — the backend keeps no chat history, a dropped
// connection just means the student re-opens the room page to get a fresh socket.
export function useRoomSocket({ roomId, enabled }) {
  const [messages, setMessages] = useState([])
  const [connectionStatus, setConnectionStatus] = useState('idle') // idle | connecting | open | closed
  const [sessionConfirmationRequired, setSessionConfirmationRequired] = useState(false)
  const [closeCode, setCloseCode] = useState(null)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!enabled || !roomId) return

    const token = getAccessToken()
    const socket = new WebSocket(`${WS_BASE}/rooms/${roomId}/chat?token=${encodeURIComponent(token)}`)
    wsRef.current = socket
    setConnectionStatus('connecting')

    socket.onopen = () => setConnectionStatus('open')

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'session_confirmation_required') {
        setSessionConfirmationRequired(true)
        return
      }
      setMessages((prev) => [...prev, data])
    }

    socket.onclose = (event) => {
      setConnectionStatus('closed')
      setCloseCode(event.code)
    }

    return () => {
      socket.close()
      wsRef.current = null
    }
  }, [roomId, enabled])

  const sendMessage = useCallback((content) => {
    if (wsRef.current?.readyState === WebSocket.OPEN && content.trim()) {
      wsRef.current.send(JSON.stringify({ content }))
    }
  }, [])

  return { messages, connectionStatus, sessionConfirmationRequired, closeCode, sendMessage }
}
