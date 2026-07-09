import { useEffect, useState } from 'react'

function formatRemaining(ms) {
  if (ms <= 0) return "0:00"
  const totalSeconds = Math.floor(ms / 1000)
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${minutes}:${String(seconds).padStart(2, '0')}`
}

export default function RoomTimer({ timerEndsAt, isRequester, roomActive, onExtend, extending }) {
  const [remaining, setRemaining] = useState(() => new Date(timerEndsAt).getTime() - Date.now())

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining(new Date(timerEndsAt).getTime() - Date.now())
    }, 1000)
    return () => clearInterval(interval)
  }, [timerEndsAt])

  const expired = remaining <= 0

  return (
    <div className="card" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <div>
        <p className="page-subtitle" style={{ margin: 0 }}>Time remaining</p>
        <h2 style={{ color: expired ? 'var(--color-danger)' : 'var(--color-text)' }}>{formatRemaining(remaining)}</h2>
      </div>
      {isRequester && roomActive && (
        <button className="btn btn-secondary btn-sm" onClick={onExtend} disabled={extending}>
          {extending ? 'Extending…' : '+10 min'}
        </button>
      )}
    </div>
  )
}
