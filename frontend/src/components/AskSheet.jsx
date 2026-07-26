import { useEffect, useRef, useState } from 'react'
import { useCreateHelpRequest, useSections } from '../queries'
import './AskSheet.css'

const GROUP_SIZE_OPTIONS = [2, 3, 4, 5]
const DURATION_OPTIONS = [15, 30, 45]

function AskSheet({ open, onClose }) {
  const { data: sections = null } = useSections()
  const createHelpRequest = useCreateHelpRequest(sections)
  const sheetRef = useRef(null)

  const [sectionId, setSectionId] = useState('')
  const [topic, setTopic] = useState('')
  const [groupSize, setGroupSize] = useState(3)
  const [durationMinutes, setDurationMinutes] = useState(30)
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [posted, setPosted] = useState(false)

  const selectedSectionId = sectionId || sections?.[0]?.section_id || ''

  useEffect(() => {
    if (!open) return
    function handleKeyDown(e) {
      // Capture phase, so this always runs before Layout.jsx's page-level
      // Escape-to-go-back handler (a bubble-phase listener) regardless of
      // mount order — closing this sheet should never also navigate away.
      if (e.key !== 'Escape') return
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

  function resetAndClose() {
    setTopic('')
    setGroupSize(3)
    setDurationMinutes(30)
    setError('')
    setPosted(false)
    onClose()
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      await createHelpRequest({ sectionId: selectedSectionId, topic, groupSize, durationMinutes })
      setPosted(true)
      setTimeout(resetAndClose, 1100)
    } catch (err) {
      setError(err.response?.data?.message || 'Could not post request.')
    } finally {
      setSubmitting(false)
    }
  }

  const noSections = sections !== null && sections.length === 0

  return (
    <div
      className={`ask-sheet-backdrop${open ? ' open' : ''}`}
      onMouseDown={handleBackdropClick}
      aria-hidden={!open}
    >
      <div className="ask-sheet" ref={sheetRef} role="dialog" aria-modal="true" aria-label="Ask for help">
        <div className="ask-sheet-handle" />
        <div className="ask-sheet-header">
          <h2>Ask for help</h2>
        </div>

        {posted && <p className="ask-sheet-success">Request posted!</p>}

        {!posted && noSections && (
          <p className="ask-sheet-error">Join a section to ask for help.</p>
        )}

        {!posted && !noSections && (
          <form className="ask-sheet-form" onSubmit={handleSubmit}>
            <label className="ask-sheet-field">
              Section
              <select value={selectedSectionId} onChange={(e) => setSectionId(e.target.value)} required>
                {(sections ?? []).map((s) => (
                  <option key={s.section_id} value={s.section_id}>
                    {s.class_name}
                  </option>
                ))}
              </select>
            </label>
            <label className="ask-sheet-field">
              Topic
              <input value={topic} onChange={(e) => setTopic(e.target.value)} required />
            </label>
            <div className="ask-sheet-field">
              Party size
              <div className="ask-sheet-chip-row">
                {GROUP_SIZE_OPTIONS.map((size) => (
                  <button
                    type="button"
                    key={size}
                    className={`ask-sheet-chip${groupSize === size ? ' selected' : ''}`}
                    onClick={() => setGroupSize(size)}
                  >
                    {size}
                  </button>
                ))}
              </div>
            </div>
            <div className="ask-sheet-field">
              Duration
              <div className="ask-sheet-chip-row">
                {DURATION_OPTIONS.map((min) => (
                  <button
                    type="button"
                    key={min}
                    className={`ask-sheet-chip${durationMinutes === min ? ' selected' : ''}`}
                    onClick={() => setDurationMinutes(min)}
                  >
                    {min} min
                  </button>
                ))}
              </div>
            </div>
            {error && <p className="ask-sheet-error">{error}</p>}
            <button type="submit" className="ask-sheet-submit" disabled={submitting || !selectedSectionId}>
              {submitting ? 'Posting…' : 'Post request'}
            </button>
          </form>
        )}
      </div>
    </div>
  )
}

export default AskSheet
