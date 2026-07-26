import { useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useTutorial } from './tutorial/TutorialContext'
import { isAdmin } from '../utils/auth'
import { logout } from '../utils/logout'
import { getTheme, setTheme } from '../utils/theme'
import './MoreSheet.css'

function MoreSheet({ open, onClose, groups, inboxCount }) {
  const navigate = useNavigate()
  const admin = isAdmin()
  const { replay } = useTutorial()
  const [theme, setThemeState] = useState(getTheme())
  const sheetRef = useRef(null)

  useEffect(() => {
    if (!open) return
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      // Capture phase, so this always runs before Layout.jsx's page-level
      // Escape-to-go-back handler (a bubble-phase listener) regardless of
      // mount order — closing this sheet should never also navigate away.
      e.stopPropagation()
      onClose()
    }
    document.addEventListener('keydown', handleKeyDown, true)
    return () => document.removeEventListener('keydown', handleKeyDown, true)
  }, [open, onClose])

  function handleBackdropClick(e) {
    if (sheetRef.current && !sheetRef.current.contains(e.target)) {
      onClose()
    }
  }

  function goToProfile() {
    onClose()
    navigate(admin ? '/admin/profile' : '/profile')
  }

  function handleLogout() {
    onClose()
    logout(navigate)
  }

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setThemeState(next)
  }

  // Mirrors TopBar.jsx's handleReplayTutorial — the tour's steps target
  // elements on the user's own landing page, so replaying it from some
  // other page would show the overlay with nothing behind it to point at.
  function handleReplayTutorial() {
    onClose()
    navigate(admin ? '/admin/overview' : '/dashboard')
    replay()
  }

  return (
    <div
      className={`more-sheet-backdrop${open ? ' open' : ''}`}
      onMouseDown={handleBackdropClick}
      aria-hidden={!open}
    >
      <div className="more-sheet" ref={sheetRef} role="dialog" aria-modal="true" aria-label="More">
        <div className="more-sheet-handle" />
        {groups.map((group, i) => (
          <div className="more-sheet-group" key={group.label ?? i}>
            {group.label && <div className="more-sheet-group-label">{group.label}</div>}
            {group.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className="more-sheet-link"
                onClick={onClose}
              >
                <span>{item.label}</span>
                {item.badge === 'inbox' && inboxCount > 0 && (
                  <span className="more-sheet-badge">{inboxCount}</span>
                )}
              </NavLink>
            ))}
          </div>
        ))}

        <div className="more-sheet-divider" />
        <button type="button" className="more-sheet-link more-sheet-button" onClick={toggleTheme}>
          <span>Appearance</span>
          <span className="more-sheet-value">{theme === 'dark' ? 'Dark' : 'Light'}</span>
        </button>
        <button
          type="button"
          className="more-sheet-link more-sheet-button"
          onClick={handleReplayTutorial}
        >
          Replay tutorial
        </button>

        <div className="more-sheet-divider" />
        <button type="button" className="more-sheet-link more-sheet-button" onClick={goToProfile}>
          My profile
        </button>
        <button
          type="button"
          className="more-sheet-link more-sheet-button more-sheet-logout"
          onClick={handleLogout}
        >
          Log out
        </button>
      </div>
    </div>
  )
}

export default MoreSheet
