import { useState } from 'react'

const STATUS_TEXT = {
  idle: '',
  connecting: 'Connecting…',
  open: 'Connected',
  closed: 'Disconnected',
}

export default function ChatPanel({ messages, currentUserId, connectionStatus, onSend }) {
  const [draft, setDraft] = useState('')
  const canSend = connectionStatus === 'open'

  function handleSubmit(e) {
    e.preventDefault()
    if (!draft.trim()) return
    onSend(draft)
    setDraft('')
  }

  return (
    <div className="card" style={{ display: 'flex', flexDirection: 'column', height: 420 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <h3>Chat</h3>
        <span className="page-subtitle">{STATUS_TEXT[connectionStatus]}</span>
      </div>

      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 12 }}>
        {messages.length === 0 && <p className="page-subtitle">No messages yet — chat isn't saved after the room closes.</p>}
        {messages.map((m, i) => (
          <div key={i}>
            <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>
              {m.user_id === currentUserId ? 'You' : m.username}
            </span>
            <span style={{ marginLeft: 8, fontSize: '0.9rem' }}>{m.content}</span>
          </div>
        ))}
      </div>

      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: 8 }}>
        <input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder={canSend ? 'Say something…' : 'Chat unavailable'}
          disabled={!canSend}
          style={{ flex: 1, border: '1px solid var(--color-border)', borderRadius: 8, padding: '8px 10px' }}
        />
        <button className="btn btn-primary btn-sm" type="submit" disabled={!canSend}>
          Send
        </button>
      </form>
    </div>
  )
}
