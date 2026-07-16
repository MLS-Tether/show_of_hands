function RosterPanel({ section, onSelectStudent }) {
  const students = section.students

  return (
    <div>
      <div className="widget-label">roster</div>
      {students.length === 0 ? (
        <p className="teacher-panel-placeholder">No students enrolled.</p>
      ) : (
        <div className="teacher-panel-list">
          {students.map((s) => (
            <button
              type="button"
              className="teacher-panel-row"
              key={s.user_id}
              onClick={() => onSelectStudent(s)}
            >
              <span>{s.username}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export default RosterPanel
