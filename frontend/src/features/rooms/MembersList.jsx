export default function MembersList({ members, currentUserId, requesterId, isRequester, roomActive, busyUserId, onKick }) {
  return (
    <div className="card">
      <h3 style={{ marginBottom: 12 }}>Members</h3>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: 8 }}>
        {members.map((m) => (
          <li key={m.user_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span>
              {m.username}
              {m.user_id === requesterId && (
                <span className="badge badge-mine" style={{ marginLeft: 6 }}>
                  Requester
                </span>
              )}
              {m.user_id === currentUserId && (
                <span style={{ color: 'var(--color-text-muted)', fontSize: '0.8rem' }}> (you)</span>
              )}
            </span>
            {isRequester && roomActive && m.user_id !== currentUserId && (
              <button
                className="btn btn-ghost btn-sm"
                disabled={busyUserId === m.user_id}
                onClick={() => onKick(m.user_id)}
              >
                Remove
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
