import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { TutorialContext } from './TutorialContext'
import TutorialOverlay from './TutorialOverlay'
import { getTutorialSteps } from './tutorialSteps'
import { getRole, getUserId, isAdmin } from '../../utils/auth'
import { hasSeenTutorial, markTutorialSeen } from '../../utils/tutorial'

export function TutorialProvider({ children }) {
  const navigate = useNavigate()
  const [active, setActive] = useState(false)
  const [step, setStep] = useState(0)
  const role = getRole()
  const userId = getUserId()
  const steps = getTutorialSteps(role)

  useEffect(() => {
    if (userId && !hasSeenTutorial(userId)) {
      setActive(true)
    }
  }, [userId])

  function finish() {
    markTutorialSeen(userId)
    setActive(false)
  }

  function finishAndBrowseSections() {
    finish()
    navigate(isAdmin() ? '/admin/sections' : '/sections')
  }

  function next() {
    setStep((s) => Math.min(s + 1, steps.length - 1))
  }

  function prev() {
    setStep((s) => Math.max(s - 1, 0))
  }

  function replay() {
    setStep(0)
    setActive(true)
  }

  const isLastStep = step === steps.length - 1

  return (
    <TutorialContext.Provider value={{ replay }}>
      {children}
      {active && (
        <TutorialOverlay
          step={steps[step]}
          stepIndex={step}
          stepCount={steps.length}
          onNext={isLastStep ? finishAndBrowseSections : next}
          onPrev={prev}
          onSkip={finish}
        />
      )}
    </TutorialContext.Provider>
  )
}
