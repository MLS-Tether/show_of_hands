function RosterPanel({ section }) {
  const students = section.students

  return (
    <div>
      <div className="widget-label">roster</div>
      {students.length === 0 ? (
        <p className="teacher-panel-placeholder">No students enrolled.</p>
      ) : (
        <div className="teacher-panel-list">
          {students.map((s) => (
            <div className="teacher-panel-row" key={s.user_id}>
              <span>{s.username}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default RosterPanel
