import { useState } from 'react'
import { isAdmin, isTeacher } from '../utils/auth'
import AskSheet from './AskSheet'
import './AskButton.css'

function AskButton() {
  const [open, setOpen] = useState(false)

  // Asking for help is a student-only concept (teachers/admins have no
  // Bulletin board route at all — see navConfig.js's `studentOnly` items).
  if (isTeacher() || isAdmin()) return null

  return (
    <>
      <button type="button" className="ask-button" onClick={() => setOpen(true)}>
        <span className="ask-button-icon" aria-hidden="true">
          +
        </span>
        Ask
      </button>
      <AskSheet open={open} onClose={() => setOpen(false)} />
    </>
  )
}

export default AskButton
