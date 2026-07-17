import { useCallback, useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import api from '../../api'
import { formatPercent } from '../../utils/format'
import { downloadReportCard, printReportCard } from '../../utils/reportCard'
import './admin-shared.css'
import './AdminStudentDetail.css'

function AdminStudentDetail() {
  const { studentId } = useParams()
  const [student, setStudent] = useState(null)
  const [grades, setGrades] = useState(null)
  const [notFound, setNotFound] = useState(false)

  const load = useCallback(() => {
    let cancelled = false
    Promise.all([api.get(`/users/${studentId}`), api.get(`/users/${studentId}/grades`)])
      .then(([userRes, gradesRes]) => {
        if (cancelled) return
        setStudent(userRes.data)
        setGrades(gradesRes.data)
      })
      .catch(() => {
        if (cancelled) return
        setNotFound(true)
      })
    return () => {
      cancelled = true
    }
  }, [studentId])

  useEffect(() => load(), [load])

  if (notFound) {
    return (
      <div className="admin-student-detail">
        <p className="admin-empty-card">Student not found.</p>
      </div>
    )
  }

  if (!student || !grades) {
    return (
      <div className="admin-student-detail">
        <p className="admin-empty-card">Loading…</p>
      </div>
    )
  }

  return (
    <div className="admin-student-detail">
      <h1 className="admin-page-h1">{student.username}</h1>
      <p className="admin-page-subtitle">Cumulative grades across all enrolled sections</p>

      <div className="admin-student-actions">
        <button
          type="button"
          className="admin-btn-secondary"
          onClick={() => downloadReportCard(student, grades)}
        >
          Download PDF
        </button>
        <button
          type="button"
          className="admin-btn-secondary"
          onClick={() => printReportCard(student, grades)}
        >
          Print
        </button>
      </div>

      {grades.length === 0 ? (
        <p className="admin-empty-card">Not enrolled in any sections.</p>
      ) : (
        <div className="admin-student-grades-table">
          <div className="admin-student-grades-row admin-student-grades-header">
            <span>Section</span>
            <span>Period</span>
            <span>Grade</span>
            <span>Letter</span>
          </div>
          {grades.map((g) => (
            <div className="admin-student-grades-row" key={g.section_id}>
              <span>{g.class_name}</span>
              <span>{g.period}</span>
              <span>{g.percentage != null ? formatPercent(g.percentage) : '—'}</span>
              <span>{g.letter_grade || '—'}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default AdminStudentDetail
