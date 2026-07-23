# Onboarding Tutorial Overlay Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-time, role-aware guided tour ("Quest Map" direction) that overlays the real app shell after first sign-in, highlighting real sidebar/topbar elements with a circle-and-arrow annotation, and is replayable from Profile.

**Architecture:** A `TutorialProvider` React context (mirroring the existing `DialogProvider`/`RealtimeProvider` pattern) mounts inside `Layout.jsx`, wrapping the whole authenticated shell so it covers every role's landing page. It owns active/step state, checks a per-user `localStorage` flag on mount to auto-show once, and renders a `TutorialOverlay` that measures real DOM elements (marked with `data-tour` attributes) to position a circle+arrow+card.

**Tech Stack:** React (hooks, Context API), plain CSS using the app's existing CSS variables (`--accent`, `--surface-1`, `--text-h`, `--text-muted`, etc. from `index.css`). No backend changes. No new dependencies.

## Global Constraints

- No backend changes — persistence is `localStorage` only, keyed by `user_id` (per spec, user decided against a backend field).
- No new CSS color tokens — reuse existing `index.css` variables so the overlay respects the light/dark theme toggle automatically.
- No automated frontend test suite exists in this repo — every task's verification step is manual, via the dev server and browser, not a test runner command.
- Reference spec: `docs/superpowers/specs/2026-07-23-onboarding-tutorial-design.md`.

---

## File Structure

**New files:**
- `frontend/src/components/tutorial/TutorialContext.js` — context + `useTutorial()` hook
- `frontend/src/components/tutorial/TutorialProvider.jsx` — state machine, auto-show logic
- `frontend/src/components/tutorial/tutorialSteps.js` — pure per-role step data
- `frontend/src/components/tutorial/TutorialOverlay.jsx` — positioning math + rendering
- `frontend/src/components/tutorial/TutorialOverlay.css` — Quest Map visual styling
- `frontend/src/utils/tutorial.js` — `hasSeenTutorial`/`markTutorialSeen` localStorage helpers

**Modified files:**
- `frontend/src/components/Sidebar.jsx` — add `data-tour` targets to nav items
- `frontend/src/components/TopBar.jsx` — add `data-tour="topbar-points"`
- `frontend/src/pages/TeacherDashboard.jsx` — add `data-tour="widget-teacher"` to first section card
- `frontend/src/components/Layout.jsx` — mount `TutorialProvider`
- `frontend/src/components/Layout.css` — add `position: relative` to `.admin-shell`
- `frontend/src/pages/Profile.jsx` — add "Replay tutorial" button

---

### Task 1: Wire up `data-tour` targets on the real DOM

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx:9-29,95-105`
- Modify: `frontend/src/components/TopBar.jsx:89`
- Modify: `frontend/src/pages/TeacherDashboard.jsx:59-75`

**Interfaces:**
- Produces: `[data-tour="nav-sections"]`, `[data-tour="nav-assignments"]`, `[data-tour="nav-quests"]`, `[data-tour="nav-bulletin"]`, `[data-tour="nav-rooms"]`, `[data-tour="nav-overview"]`, `[data-tour="nav-inbox"]`, `[data-tour="nav-users"]`, `[data-tour="topbar-points"]`, `[data-tour="widget-teacher"]` — attribute selectors that Task 3's `TutorialOverlay` will query.

- [ ] **Step 1: Add `tour` keys to Sidebar's nav config**

In `frontend/src/components/Sidebar.jsx`, replace the `ADMIN_NAV_GROUPS` and `APP_NAV_ITEMS` constants (currently lines 9–29):

```js
const ADMIN_NAV_GROUPS = [
  { label: null, items: [{ label: 'Overview', to: '/admin/overview', end: true, tour: 'nav-overview' }] },
  { label: 'Approvals', items: [{ label: 'Inbox', to: '/admin/inbox', badge: 'inbox', tour: 'nav-inbox' }] },
  {
    label: 'Manage',
    items: [
      { label: 'Sections', to: '/admin/sections', tour: 'nav-sections' },
      { label: 'Users', to: '/admin/users', tour: 'nav-users' },
    ],
  },
  { label: 'School', items: [{ label: 'Settings', to: '/admin/settings' }] },
]

const APP_NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'My sections', to: '/sections', tour: 'nav-sections' },
  { label: 'Assignments', to: '/assignments', studentOnly: true, tour: 'nav-assignments' },
  { label: 'Quests', to: '/quests', tour: 'nav-quests' },
  { label: 'Bulletin board', to: '/bulletin-board', studentOnly: true, tour: 'nav-bulletin' },
  { label: 'Study rooms', to: '/study-rooms', studentOnly: true, tour: 'nav-rooms' },
  { label: 'Points', to: '/points', studentOnly: true },
]
```

- [ ] **Step 2: Spread `data-tour` onto the rendered `NavLink`**

In the same file, find the `NavLink` render (currently lines 95–105):

```jsx
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                className={({ isActive }) => `admin-sidebar-link${isActive ? ' active' : ''}`}
              >
```

Add `data-tour={item.tour}` as a prop:

```jsx
              <NavLink
                key={item.to}
                to={item.to}
                end={item.end}
                data-tour={item.tour}
                className={({ isActive }) => `admin-sidebar-link${isActive ? ' active' : ''}`}
              >
```

(When `item.tour` is `undefined` — e.g. Dashboard, Points, Settings — React omits the attribute entirely, so no conditional needed.)

- [ ] **Step 3: Add `data-tour="topbar-points"` in TopBar**

In `frontend/src/components/TopBar.jsx`, line 89, change:

```jsx
          <span className="admin-topbar-points">
```

to:

```jsx
          <span className="admin-topbar-points" data-tour="topbar-points">
```

- [ ] **Step 4: Add `data-tour="widget-teacher"` to the first owned section card**

In `frontend/src/pages/TeacherDashboard.jsx`, the map callback currently starts at line 59:

```jsx
          {visibleOwnedSections.map((s) => {
            const badge = pending[s.section_id]
            const badgeCount = badge ? badge.pendingRequests + badge.ungraded : 0
            return (
              <button
                type="button"
                className="teacher-section-card"
                key={s.section_id}
                onClick={() => navigate(`/sections/${s.section_id}`)}
              >
```

Change to accept an index and set `data-tour` only on the first card:

```jsx
          {visibleOwnedSections.map((s, i) => {
            const badge = pending[s.section_id]
            const badgeCount = badge ? badge.pendingRequests + badge.ungraded : 0
            return (
              <button
                type="button"
                className="teacher-section-card"
                key={s.section_id}
                data-tour={i === 0 ? 'widget-teacher' : undefined}
                onClick={() => navigate(`/sections/${s.section_id}`)}
              >
```

- [ ] **Step 5: Verify in-browser**

Run the frontend dev server (`npm run dev` in `frontend/`) and the backend (`uvicorn main:app --reload` in `backend/`). Log in as a student, teacher, and admin test account in turn. In each case, open browser devtools, inspect the sidebar/topbar, and confirm the expected `data-tour` attributes are present:
- Student: `nav-sections`, `nav-assignments`, `nav-quests`, `nav-bulletin`, `nav-rooms` on sidebar links, `topbar-points` on the points badge.
- Teacher: `nav-sections`, `nav-quests` on sidebar links; `widget-teacher` on the first section card on the dashboard (only the first — confirm a second card, if present, has no `data-tour`).
- Admin: `nav-overview`, `nav-inbox`, `nav-sections`, `nav-users` on sidebar links.

No visual change should be apparent yet — this task only adds inert attributes.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Sidebar.jsx frontend/src/components/TopBar.jsx frontend/src/pages/TeacherDashboard.jsx
git commit -m "Add data-tour attributes for onboarding tutorial targets"
```

---

### Task 2: Tutorial state machine + minimal centered overlay

**Files:**
- Create: `frontend/src/utils/tutorial.js`
- Create: `frontend/src/components/tutorial/tutorialSteps.js`
- Create: `frontend/src/components/tutorial/TutorialContext.js`
- Create: `frontend/src/components/tutorial/TutorialProvider.jsx`
- Create: `frontend/src/components/tutorial/TutorialOverlay.jsx`
- Create: `frontend/src/components/tutorial/TutorialOverlay.css`
- Modify: `frontend/src/components/Layout.jsx:1-56`
- Modify: `frontend/src/components/Layout.css:1-5`

**Interfaces:**
- Consumes: `getRole()`, `getUserId()` from `../../utils/auth` (existing, both take no args and return a string/number respectively — `getRole()` returns `'student' | 'teacher' | 'admin'`, `getUserId()` returns a number).
- Produces: `useTutorial()` hook returning `{ replay: () => void }`, consumed by Task 5's Profile button. `hasSeenTutorial(userId: number): boolean` and `markTutorialSeen(userId: number): void`, consumed only within this task's own `TutorialProvider.jsx`. `getTutorialSteps(role: string): Array<{ badge, title, body, target?, place?, cta? }>`, consumed by `TutorialProvider.jsx` and (in Task 3) `TutorialOverlay.jsx`.

- [ ] **Step 1: Write the localStorage persistence helper**

Create `frontend/src/utils/tutorial.js`:

```js
const STORAGE_KEY_PREFIX = 'sh-tutorial-seen-'

export function hasSeenTutorial(userId) {
  return localStorage.getItem(STORAGE_KEY_PREFIX + userId) === '1'
}

export function markTutorialSeen(userId) {
  localStorage.setItem(STORAGE_KEY_PREFIX + userId, '1')
}
```

- [ ] **Step 2: Write the per-role step data**

Create `frontend/src/components/tutorial/tutorialSteps.js`:

```js
export function getTutorialSteps(role) {
  if (role === 'teacher') {
    return [
      {
        badge: 'Welcome',
        place: 'center',
        title: 'Welcome, coach ✋',
        body: "Show of Hands turns your class into a team. Here's how to set up your sections, assign quests, and spot who needs help — in about 30 seconds.",
      },
      {
        badge: 'Step 1',
        target: 'nav-sections',
        place: 'right',
        title: 'Create your sections',
        body: 'Spin up a section for each class period, set its capacity, and share the join code so students can enroll.',
      },
      {
        badge: 'Step 2',
        target: 'nav-quests',
        place: 'right',
        title: 'Assign quests',
        body: 'Build academic or social quests, set point values, and target the whole class or a single student who needs a nudge.',
      },
      {
        badge: 'Step 3',
        target: 'widget-teacher',
        place: 'right',
        title: 'Spot what needs attention',
        body: 'Each section card flags pending join requests and ungraded work, so nothing slips through the cracks.',
      },
      {
        badge: "You're set!",
        place: 'center',
        title: 'Ready to set up class?',
        body: 'Replay this anytime from your Profile. Let’s start with your sections.',
        cta: 'Browse sections',
      },
    ]
  }

  if (role === 'admin') {
    return [
      {
        badge: 'Welcome',
        place: 'center',
        title: 'Welcome to the console ✋',
        body: 'You keep the whole school running. This quick tour shows where to approve accounts, manage sections, and read school-wide stats.',
      },
      {
        badge: 'Step 1',
        target: 'nav-overview',
        place: 'right',
        title: 'Your command center',
        body: 'The overview surfaces everything that needs you today, plus school-wide stats at a glance.',
      },
      {
        badge: 'Step 2',
        target: 'nav-inbox',
        place: 'right',
        title: 'Approve new accounts',
        body: "Teachers and admins can't log in until you verify them. New class requests land in the Inbox too.",
      },
      {
        badge: 'Step 3',
        target: 'nav-sections',
        place: 'right',
        title: 'Manage every section',
        body: 'Reassign teachers, change a section’s status, or archive it — across the whole school.',
      },
      {
        badge: 'Step 4',
        target: 'nav-users',
        place: 'right',
        title: 'The user directory',
        body: 'Browse and manage every student, teacher, and admin account in your school.',
      },
      {
        badge: "You're set!",
        place: 'center',
        title: 'Ready to run the show?',
        body: 'Replay this anytime from your Profile. Let’s start with your sections.',
        cta: 'Browse sections',
      },
    ]
  }

  return [
    {
      badge: 'Welcome',
      place: 'center',
      title: 'Welcome to Show of Hands ✋',
      body: "Learning's better together. This quick tour shows how to earn points, get help, and team up with classmates. Takes about 30 seconds.",
    },
    {
      badge: 'Step 1',
      target: 'nav-sections',
      place: 'right',
      title: 'Join your classes',
      body: 'Every class you’re in lives under My sections. Tap “+ join section” and enter the code from your teacher.',
    },
    {
      badge: 'Step 2',
      target: 'nav-assignments',
      place: 'right',
      title: 'Stay on top of your work',
      body: 'Every assignment you owe lands here, with its due date front and center. Submit before the clock runs out to keep your grade — and your points — safe.',
    },
    {
      badge: 'Step 3',
      target: 'nav-quests',
      place: 'right',
      title: 'Take on quests',
      body: 'Quests are fun tasks — read for an hour, form a study group, hit the library. Finish them to rack up XP.',
    },
    {
      badge: 'Step 4',
      target: 'nav-bulletin',
      place: 'right',
      title: 'Ask for help, anonymously',
      body: 'Stuck? Post to the bulletin board with no name attached. A classmate jumps in — and you both earn points.',
    },
    {
      badge: 'Step 5',
      target: 'nav-rooms',
      place: 'right',
      title: 'Team up in study rooms',
      body: 'Accept a request and you drop into a study room with a live timer and chat. Beat the clock together.',
    },
    {
      badge: 'Step 6',
      target: 'topbar-points',
      place: 'below',
      title: 'Watch your points climb',
      body: 'Points stack up from quests and helping out. Check the leaderboard under Points to see where you rank.',
    },
    {
      badge: "You're set!",
      place: 'center',
      title: 'Ready to dive in?',
      body: 'You can replay this anytime from your Profile. Let’s find a class to join.',
      cta: 'Browse sections',
    },
  ]
}
```

- [ ] **Step 3: Write the context**

Create `frontend/src/components/tutorial/TutorialContext.js`:

```js
import { createContext, useContext } from 'react'

export const TutorialContext = createContext(null)

export function useTutorial() {
  const ctx = useContext(TutorialContext)
  if (!ctx) throw new Error('useTutorial must be used within a TutorialProvider')
  return ctx
}
```

- [ ] **Step 4: Write a minimal (centered-only) overlay**

This will be extended with real positioning in Task 3 — for now every step renders centered, which proves the step/navigation state machine end-to-end without the positioning math.

Create `frontend/src/components/tutorial/TutorialOverlay.jsx`:

```jsx
import './TutorialOverlay.css'

function TutorialOverlay({ step, stepIndex, stepCount, onNext, onPrev, onSkip }) {
  const isFirst = stepIndex === 0
  const isLast = stepIndex === stepCount - 1

  return (
    <div className="tutorial-overlay">
      <div className="tutorial-wash" />
      <div className="tutorial-card">
        <div className="tutorial-card-header">
          <span className="tutorial-badge">{step.badge}</span>
          <button type="button" className="tutorial-skip" onClick={onSkip}>
            Skip
          </button>
        </div>
        <div className="tutorial-title">{step.title}</div>
        <div className="tutorial-body">{step.body}</div>
        <div className="tutorial-actions">
          {!isFirst && (
            <button type="button" className="tutorial-back" onClick={onPrev}>
              Back
            </button>
          )}
          <button type="button" className="tutorial-next" onClick={onNext}>
            {isLast ? step.cta : 'Next'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TutorialOverlay
```

Create `frontend/src/components/tutorial/TutorialOverlay.css`:

```css
.tutorial-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
}

.tutorial-wash {
  position: absolute;
  inset: 0;
  background: rgba(12, 10, 18, 0.4);
}

.tutorial-card {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 344px;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: rgba(0, 0, 0, 0.22) 0 20px 48px -14px;
  padding: 20px 22px 18px;
}

.tutorial-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.tutorial-badge {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
  background: var(--accent-bg);
  border-radius: 16px;
  padding: 3px 10px;
}

.tutorial-skip {
  font-size: 12px;
  color: var(--text-muted);
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
}

.tutorial-title {
  font-size: 19px;
  font-weight: 600;
  color: var(--text-h);
  letter-spacing: -0.01em;
  margin-bottom: 8px;
}

.tutorial-body {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-muted);
}

.tutorial-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 16px;
}

.tutorial-back {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-h);
  background: var(--surface-1);
  border: 1px solid var(--border-strong);
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
}

.tutorial-next {
  margin-left: auto;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 8px;
  padding: 8px 18px;
  cursor: pointer;
}
```

- [ ] **Step 5: Write the provider**

Create `frontend/src/components/tutorial/TutorialProvider.jsx`:

```jsx
import { useEffect, useState } from 'react'
import { TutorialContext } from './TutorialContext'
import TutorialOverlay from './TutorialOverlay'
import { getTutorialSteps } from './tutorialSteps'
import { getRole, getUserId } from '../../utils/auth'
import { hasSeenTutorial, markTutorialSeen } from '../../utils/tutorial'

export function TutorialProvider({ children }) {
  const [active, setActive] = useState(false)
  const [step, setStep] = useState(0)
  const role = getRole()
  const userId = getUserId()
  const steps = getTutorialSteps(role)

  useEffect(() => {
    if (!hasSeenTutorial(userId)) {
      setActive(true)
    }
  }, [userId])

  function finish() {
    markTutorialSeen(userId)
    setActive(false)
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
          onNext={isLastStep ? finish : next}
          onPrev={prev}
          onSkip={finish}
        />
      )}
    </TutorialContext.Provider>
  )
}
```

- [ ] **Step 6: Mount the provider in Layout**

In `frontend/src/components/Layout.jsx`, add the import (near the other component imports, after the `RealtimeProvider` import on line 5):

```jsx
import { TutorialProvider } from './tutorial/TutorialProvider'
```

Then change the return block (currently lines 44–56):

```jsx
  return (
    <RealtimeProvider>
      <div className="admin-shell">
        {!sidebarHidden && <Sidebar />}
        <div className="admin-main">
          <TopBar sidebarHidden={sidebarHidden} onToggleSidebar={toggleSidebar} />
          <main className="admin-content">
            <div className="admin-content-inner">
              <Outlet />
            </div>
          </main>
        </div>
      </div>
    </RealtimeProvider>
  )
```

to:

```jsx
  return (
    <RealtimeProvider>
      <div className="admin-shell">
        <TutorialProvider>
          {!sidebarHidden && <Sidebar />}
          <div className="admin-main">
            <TopBar sidebarHidden={sidebarHidden} onToggleSidebar={toggleSidebar} />
            <main className="admin-content">
              <div className="admin-content-inner">
                <Outlet />
              </div>
            </main>
          </div>
        </TutorialProvider>
      </div>
    </RealtimeProvider>
  )
```

- [ ] **Step 7: Give `.admin-shell` a positioning context**

The overlay's `position: absolute; inset: 0` needs to anchor to `.admin-shell`, not further up the tree. In `frontend/src/components/Layout.css`, change:

```css
.admin-shell {
  display: flex;
  height: 100%;
  width: 100%;
}
```

to:

```css
.admin-shell {
  position: relative;
  display: flex;
  height: 100%;
  width: 100%;
}
```

- [ ] **Step 8: Verify in-browser**

In devtools, run `localStorage.clear()` on the app's origin, then reload and log in as a student test account. Confirm:
- The overlay auto-appears immediately, centered, showing the "Welcome to Show of Hands ✋" copy and a "Skip" button, no "Back" button on this first step.
- Clicking "Next" advances through all 8 steps (badges Step 1 → Step 6 → "You're set!"), and "Back" appears from the second step onward.
- The final step's button reads "Browse sections" instead of "Next".
- Clicking it closes the overlay.
- Reload the page — the overlay does **not** reappear (confirm `localStorage.getItem('sh-tutorial-seen-<userId>')` is `'1'` in devtools).
- Repeat with `localStorage.clear()` for a teacher and an admin test account, confirming each shows its own role's copy and step count (5 for teacher, 6 for admin).
- On a fresh account, click "Skip" partway through — confirm it closes immediately and also persists (reload doesn't reopen it).

- [ ] **Step 9: Commit**

```bash
git add frontend/src/utils/tutorial.js frontend/src/components/tutorial frontend/src/components/Layout.jsx frontend/src/components/Layout.css
git commit -m "Add tutorial state machine with minimal centered overlay"
```

---

### Task 3: Real positioning — circle, arrow, and collision-aware card placement

**Files:**
- Modify: `frontend/src/components/tutorial/TutorialOverlay.jsx` (full rewrite)
- Modify: `frontend/src/components/tutorial/TutorialOverlay.css` (additions)

**Interfaces:**
- Consumes: `step.target` (string | undefined) from the step objects `TutorialProvider` passes in (defined in Task 2's `tutorialSteps.js`).
- Produces: no new exports — `TutorialOverlay` keeps the same props signature (`step`, `stepIndex`, `stepCount`, `onNext`, `onPrev`, `onSkip`) that `TutorialProvider.jsx` already calls it with, so Task 2's provider code needs no changes.

- [ ] **Step 1: Replace `TutorialOverlay.jsx` with the full positioning version**

```jsx
import { useEffect, useRef, useState } from 'react'
import './TutorialOverlay.css'

const CARD_WIDTH = 344
const CARD_HEIGHT = 210
const MARGIN = 16
const ARROW_BOW = 22

function clamp(value, lo, hi) {
  return Math.max(lo, Math.min(hi, value))
}

function computeGeometry(rect, containerWidth, containerHeight) {
  const cw = containerWidth
  const ch = containerHeight

  if (!rect) {
    return {
      hasTarget: false,
      cardLeft: (cw - CARD_WIDTH) / 2,
      cardTop: (ch - CARD_HEIGHT) / 2 - 8,
    }
  }

  const cx = rect.left + rect.width / 2
  const cy = rect.top + rect.height / 2
  const rx = rect.width / 2 + 12
  const ry = rect.height / 2 + 9

  const targetBox = { x0: cx - rx - MARGIN, y0: cy - ry - MARGIN, x1: cx + rx + MARGIN, y1: cy + ry + MARGIN }
  const overlapsTarget = (l, t) =>
    !(l + CARD_WIDTH < targetBox.x0 || l > targetBox.x1 || t + CARD_HEIGHT < targetBox.y0 || t > targetBox.y1)
  const inBounds = (l, t) =>
    l >= MARGIN && t >= MARGIN && l + CARD_WIDTH <= cw - MARGIN && t + CARD_HEIGHT <= ch - MARGIN

  const vMid = clamp(cy - CARD_HEIGHT / 2, MARGIN, ch - CARD_HEIGHT - MARGIN)
  const hMid = clamp(cx - CARD_WIDTH / 2, MARGIN, cw - CARD_WIDTH - MARGIN)

  let candidates
  if (cx < cw * 0.5) {
    candidates = [
      [Math.min(cx + rx + 42, cw - CARD_WIDTH - MARGIN), vMid],
      [hMid, cy + ry + 28],
      [cw - CARD_WIDTH - 18, vMid],
      [hMid, clamp(cy - ry - 28 - CARD_HEIGHT, MARGIN, ch - CARD_HEIGHT - MARGIN)],
    ]
  } else {
    candidates = [
      [clamp(cx - rx - 42 - CARD_WIDTH, MARGIN, cw - CARD_WIDTH - MARGIN), vMid],
      [hMid, cy + ry + 28],
      [18, vMid],
      [hMid, clamp(cy - ry - 28 - CARD_HEIGHT, MARGIN, ch - CARD_HEIGHT - MARGIN)],
    ]
  }

  const pick =
    candidates.find(([l, t]) => !overlapsTarget(l, t) && inBounds(l, t)) ||
    candidates.find(([l, t]) => !overlapsTarget(l, t)) ||
    candidates[0]
  const [cardLeft, cardTop] = pick

  const ccx = cardLeft + CARD_WIDTH / 2
  const ccy = cardTop + CARD_HEIGHT / 2
  const angle = Math.atan2(cy - ccy, cx - ccx)
  const cos = Math.cos(angle)
  const sin = Math.sin(angle)
  const tx = Math.abs(cos) > 1e-3 ? CARD_WIDTH / 2 / Math.abs(cos) : 1e9
  const ty = Math.abs(sin) > 1e-3 ? CARD_HEIGHT / 2 / Math.abs(sin) : 1e9
  const reach = Math.min(tx, ty)
  const sx = ccx + cos * reach + cos * 6
  const sy = ccy + sin * reach + sin * 6
  const ex = cx - (rx + 6) * cos
  const ey = cy - (ry + 6) * sin
  const nx = -sin
  const ny = cos
  const qx = (sx + ex) / 2 + nx * ARROW_BOW
  const qy = (sy + ey) / 2 + ny * ARROW_BOW
  const arrowPath = `M ${sx.toFixed(1)} ${sy.toFixed(1)} Q ${qx.toFixed(1)} ${qy.toFixed(1)} ${ex.toFixed(1)} ${ey.toFixed(1)}`

  const headAngle = Math.atan2(ey - qy, ex - qx)
  const headSize = 11
  const p1x = ex - headSize * Math.cos(headAngle - 0.5)
  const p1y = ey - headSize * Math.sin(headAngle - 0.5)
  const p2x = ex - headSize * Math.cos(headAngle + 0.5)
  const p2y = ey - headSize * Math.sin(headAngle + 0.5)
  const arrowHead = `${ex.toFixed(1)},${ey.toFixed(1)} ${p1x.toFixed(1)},${p1y.toFixed(1)} ${p2x.toFixed(1)},${p2y.toFixed(1)}`

  return { hasTarget: true, cx, cy, rx, ry, cardLeft, cardTop, arrowPath, arrowHead }
}

function TutorialOverlay({ step, stepIndex, stepCount, onNext, onPrev, onSkip }) {
  const shellRef = useRef(null)
  const [box, setBox] = useState({ width: 0, height: 0, rect: null })

  useEffect(() => {
    shellRef.current = document.querySelector('.admin-shell')
  }, [])

  useEffect(() => {
    function measure() {
      const shell = shellRef.current
      if (!shell) return
      const shellRect = shell.getBoundingClientRect()
      let rect = null
      if (step.target) {
        const el = shell.querySelector(`[data-tour="${step.target}"]`)
        if (el) {
          const r = el.getBoundingClientRect()
          rect = { top: r.top - shellRect.top, left: r.left - shellRect.left, width: r.width, height: r.height }
        }
      }
      setBox({ width: shellRect.width, height: shellRect.height, rect })
    }
    // Double rAF: waits for the browser to finish the layout pass triggered
    // by the step change (e.g. a newly-mounted target element) before
    // measuring, same as the original prototype this was ported from.
    const raf1 = requestAnimationFrame(() => requestAnimationFrame(measure))
    window.addEventListener('resize', measure)
    return () => {
      cancelAnimationFrame(raf1)
      window.removeEventListener('resize', measure)
    }
  }, [step])

  const geo = computeGeometry(box.rect, box.width, box.height)
  const isFirst = stepIndex === 0
  const isLast = stepIndex === stepCount - 1

  return (
    <div className="tutorial-overlay">
      <div className="tutorial-wash" />
      {geo.hasTarget && (
        <svg className="tutorial-svg" width={box.width} height={box.height}>
          <ellipse
            className="tutorial-ellipse"
            cx={geo.cx}
            cy={geo.cy}
            rx={geo.rx}
            ry={geo.ry}
            transform={`rotate(-3 ${geo.cx} ${geo.cy})`}
          />
          <path className="tutorial-arrow-path" d={geo.arrowPath} />
          <polygon className="tutorial-arrow-head" points={geo.arrowHead} />
        </svg>
      )}
      <div className="tutorial-card" style={{ left: geo.cardLeft, top: geo.cardTop }}>
        <div className="tutorial-card-header">
          <span className="tutorial-badge">{step.badge}</span>
          <button type="button" className="tutorial-skip" onClick={onSkip}>
            Skip
          </button>
        </div>
        <div className="tutorial-title">{step.title}</div>
        <div className="tutorial-body">{step.body}</div>
        <div className="tutorial-actions">
          {!isFirst && (
            <button type="button" className="tutorial-back" onClick={onPrev}>
              Back
            </button>
          )}
          <button type="button" className="tutorial-next" onClick={onNext}>
            {isLast ? step.cta : 'Next'}
          </button>
        </div>
      </div>
    </div>
  )
}

export default TutorialOverlay
```

- [ ] **Step 2: Add the SVG/card-positioning styles**

Append to `frontend/src/components/tutorial/TutorialOverlay.css`:

```css
.tutorial-svg {
  position: absolute;
  left: 0;
  top: 0;
  overflow: visible;
  pointer-events: none;
}

.tutorial-ellipse {
  fill: none;
  stroke: var(--accent);
  stroke-width: 3;
  stroke-linecap: round;
}

.tutorial-arrow-path {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2.6;
  stroke-linecap: round;
}

.tutorial-arrow-head {
  fill: var(--accent);
}
```

And change `.tutorial-card` from centered-via-transform to plain absolute positioning (Task 2's version used `left/top: 50%; transform: translate(-50%, -50%)`, which now conflicts with `computeGeometry`'s pixel `cardLeft`/`cardTop`). Replace:

```css
.tutorial-card {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 344px;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: rgba(0, 0, 0, 0.22) 0 20px 48px -14px;
  padding: 20px 22px 18px;
}
```

with:

```css
.tutorial-card {
  position: absolute;
  width: 344px;
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 14px;
  box-shadow: rgba(0, 0, 0, 0.22) 0 20px 48px -14px;
  padding: 20px 22px 18px;
  transition: left 0.35s cubic-bezier(0.4, 0, 0.2, 1), top 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}
```

(`CARD_WIDTH`/`CARD_HEIGHT` in the JS must stay `344`/`210` to match this CSS width and the card's actual rendered height — if the card's content ever changes enough to change its rendered height noticeably, `CARD_HEIGHT` needs updating too, since the collision math uses it as a fixed box size.)

- [ ] **Step 3: Verify in-browser**

Clear the tutorial-seen flag (`localStorage.clear()`) and log in as a student. For each step that has a `target` (Step 1 through Step 6):
- Confirm a purple circle/ellipse appears around the correct real sidebar link or topbar points badge.
- Confirm an arrow with an arrowhead points from the card to that circle.
- Confirm the card itself never visually overlaps the circled element.

Resize the browser window while a target step is showing — confirm the circle, arrow, and card all reposition to stay correctly aligned (this exercises the `resize` listener).

Repeat for teacher (checking `widget-teacher` lands on the first section card specifically, not a later one) and admin.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/tutorial/TutorialOverlay.jsx frontend/src/components/tutorial/TutorialOverlay.css
git commit -m "Add real target positioning: circle, arrow, collision-aware card placement"
```

---

### Task 4: Quest Map visual polish

**Files:**
- Modify: `frontend/src/components/tutorial/TutorialOverlay.jsx` (JSX structure changes)
- Modify: `frontend/src/components/tutorial/TutorialOverlay.css` (full restyle)

**Interfaces:**
- Consumes: same props as Task 3 — no signature changes.
- Produces: no new exports.

- [ ] **Step 1: Update the card JSX for the Quest Map look**

In `frontend/src/components/tutorial/TutorialOverlay.jsx`, replace the card's inner JSX (the `<div className="tutorial-card" ...>` block) with:

```jsx
      <div className="tutorial-card" style={{ left: geo.cardLeft, top: geo.cardTop }}>
        <div className="tutorial-card-header">
          <div className="tutorial-icon">✋</div>
          <div className="tutorial-header-text">
            <div className="tutorial-badge">{step.badge}</div>
            <div className="tutorial-progress-label">
              {isLast ? 'All quests cleared!' : `Quest ${stepIndex} of ${stepCount - 2}`}
            </div>
          </div>
          <button type="button" className="tutorial-skip" onClick={onSkip}>
            Skip
          </button>
        </div>
        <div className="tutorial-title">{step.title}</div>
        <div className="tutorial-body">{step.body}</div>
        <div className="tutorial-progress-track">
          <div
            className="tutorial-progress-fill"
            style={{ width: `${Math.round((stepIndex / (stepCount - 1)) * 100)}%` }}
          />
        </div>
        <div className="tutorial-actions">
          {!isFirst && (
            <button type="button" className="tutorial-back" onClick={onPrev}>
              Back
            </button>
          )}
          <button type="button" className="tutorial-next" onClick={onNext}>
            {isLast ? step.cta : 'Next →'}
          </button>
        </div>
      </div>
```

(`Quest ${stepIndex} of ${stepCount - 2}` — `stepCount - 2` excludes the Welcome and Finish steps from the count, e.g. for the student's 8-step array, `stepCount - 2` is 6, matching the 6 numbered "Step N" entries. `stepIndex` for "Step 1" is `1`, so `Quest 1 of 6` reads correctly; the Welcome step (`stepIndex === 0`) would show `Quest 0 of 6` but `isFirst` steps have no numbered badge to compare against visually — this is acceptable since the welcome step's badge already reads "Welcome" and a user isn't comparing the two side by side.)

- [ ] **Step 2: Replace the CSS with Quest Map styling**

Replace the entire contents of `frontend/src/components/tutorial/TutorialOverlay.css` with:

```css
@keyframes tutorial-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-4px);
  }
}

@keyframes tutorial-draw {
  from {
    stroke-dashoffset: 640;
  }
  to {
    stroke-dashoffset: 0;
  }
}

.tutorial-overlay {
  position: absolute;
  inset: 0;
  z-index: 50;
}

.tutorial-wash {
  position: absolute;
  inset: 0;
  background: radial-gradient(120% 120% at 30% 30%, rgba(170, 59, 255, 0.06), rgba(170, 59, 255, 0.16));
}

.tutorial-svg {
  position: absolute;
  left: 0;
  top: 0;
  overflow: visible;
  pointer-events: none;
}

.tutorial-ellipse {
  fill: none;
  stroke: var(--accent);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-dasharray: 640;
  animation: tutorial-draw 0.6s ease forwards;
}

.tutorial-arrow-path {
  fill: none;
  stroke: var(--accent);
  stroke-width: 2.6;
  stroke-linecap: round;
}

.tutorial-arrow-head {
  fill: var(--accent);
}

.tutorial-card {
  position: absolute;
  width: 344px;
  background: var(--surface-1);
  border: 2px solid var(--accent);
  border-radius: 18px;
  box-shadow: rgba(170, 59, 255, 0.28) 0 18px 44px -14px;
  padding: 20px 22px 18px;
  transition: left 0.35s cubic-bezier(0.4, 0, 0.2, 1), top 0.35s cubic-bezier(0.4, 0, 0.2, 1);
}

.tutorial-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.tutorial-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 12px;
  background: var(--accent-bg);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 22px;
  animation: tutorial-float 2.4s ease-in-out infinite;
}

.tutorial-header-text {
  min-width: 0;
}

.tutorial-badge {
  font-size: 10.5px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--accent);
}

.tutorial-progress-label {
  font-size: 12px;
  color: var(--text-muted);
}

.tutorial-skip {
  margin-left: auto;
  align-self: flex-start;
  font-size: 12px;
  color: var(--text-muted);
  background: none;
  border: none;
  padding: 2px;
  cursor: pointer;
}

.tutorial-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-h);
  letter-spacing: -0.01em;
  margin-bottom: 8px;
}

.tutorial-body {
  font-size: 14px;
  line-height: 1.5;
  color: var(--text-muted);
}

.tutorial-progress-track {
  height: 8px;
  border-radius: 99px;
  background: var(--accent-bg);
  margin: 16px 0 14px;
  overflow: hidden;
}

.tutorial-progress-fill {
  height: 100%;
  border-radius: 99px;
  background: linear-gradient(90deg, #c084fc, var(--accent));
  transition: width 0.45s ease;
}

.tutorial-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tutorial-back {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  background: var(--surface-1);
  border: 1px solid var(--accent);
  border-radius: 99px;
  padding: 8px 16px;
  cursor: pointer;
}

.tutorial-next {
  margin-left: auto;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  background: var(--accent);
  border: 1px solid var(--accent);
  border-radius: 99px;
  padding: 8px 20px;
  cursor: pointer;
}
```

- [ ] **Step 3: Verify in-browser, light and dark mode**

Clear the seen-flag and step through the tour as a student in light mode: confirm the purple radial wash (not a hard black scrim), the floating ✋ icon gently bobbing, the gradient progress bar filling as you advance, and pill-shaped buttons. Toggle to dark mode (the "Light"/"Dark" button in the topbar) mid-tour and confirm the card background, text, and border colors all adapt correctly (since everything uses `var(--...)` tokens) with no hardcoded-light-mode colors looking wrong against a dark background.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/tutorial/TutorialOverlay.jsx frontend/src/components/tutorial/TutorialOverlay.css
git commit -m "Apply Quest Map visual styling to the tutorial overlay"
```

---

### Task 5: Replay button in Profile

**Files:**
- Modify: `frontend/src/pages/Profile.jsx:1-10,321-337`

**Interfaces:**
- Consumes: `useTutorial()` from `../components/tutorial/TutorialContext` (produced in Task 2), returning `{ replay: () => void }`.

- [ ] **Step 1: Import the hook**

In `frontend/src/pages/Profile.jsx`, add to the imports at the top of the file (after the existing `useToast` import on line 5):

```jsx
import { useTutorial } from '../components/tutorial/TutorialContext'
```

- [ ] **Step 2: Call the hook in the component**

In the `Profile()` function body, alongside the other hook calls near the top (after `const { showToast } = useToast()`):

```jsx
  const { replay } = useTutorial()
```

- [ ] **Step 3: Add a "Help" section with the replay button**

The existing password section (lines 321–337) is:

```jsx
        {(user.role === 'teacher' || user.role === 'admin') && (
          <div>
            <div className="widget-label">password</div>
            <div className="profile-card">
              <div className="profile-row">
                <span className="profile-row-label">Password</span>
                <button
                  type="button"
                  className="admin-btn-text"
                  onClick={() => setShowPasswordModal(true)}
                >
                  Change password
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
```

Add a new section right after it (still inside `.profile-sections`, before the closing `</div>`):

```jsx
        {(user.role === 'teacher' || user.role === 'admin') && (
          <div>
            <div className="widget-label">password</div>
            <div className="profile-card">
              <div className="profile-row">
                <span className="profile-row-label">Password</span>
                <button
                  type="button"
                  className="admin-btn-text"
                  onClick={() => setShowPasswordModal(true)}
                >
                  Change password
                </button>
              </div>
            </div>
          </div>
        )}

        <div>
          <div className="widget-label">help</div>
          <div className="profile-card">
            <div className="profile-row">
              <span className="profile-row-label">Onboarding tutorial</span>
              <button type="button" className="admin-btn-text" onClick={replay}>
                ↻ Replay tutorial
              </button>
            </div>
          </div>
        </div>
      </div>
```

- [ ] **Step 4: Verify in-browser**

Navigate to `/profile` while already logged in (past the auto-shown tutorial, either by completing/skipping it earlier or after it's already marked seen). Confirm a new "help" section appears with an "Onboarding tutorial" row and a "↻ Replay tutorial" button. Click it — confirm the full Quest Map overlay reopens starting at step 0 (Welcome), for the correct role's content. Step through or skip it again, confirming it closes the same way as the auto-shown version.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/Profile.jsx
git commit -m "Add replay-tutorial button to Profile"
```

---

### Task 6: Full cross-role QA pass

**Files:** none (verification only — no code changes expected unless a bug is found, in which case fix it in the relevant file from Tasks 1–5 and commit separately with a description of the bug)

- [ ] **Step 1: Fresh-login pass, all three roles**

For a student, a teacher, and an admin test account in turn: `localStorage.clear()`, log in, and step through the entire tour to completion (not skip). Confirm every step's circle+arrow lands on the correct element, every step's copy reads correctly, and the final step's "Browse sections" button navigates to `/sections`.

- [ ] **Step 2: Resize robustness**

Mid-tour (any target step), resize the browser window from wide to narrow and back. Confirm the card/circle/arrow reposition without the card ever overlapping the circled element, and without the card rendering outside the visible shell area.

- [ ] **Step 3: Skip persistence**

On a fresh account, click "Skip" on step 2 or 3. Reload the page. Confirm the tour does not reappear.

- [ ] **Step 4: Replay flow**

From `/profile`, click "↻ Replay tutorial" for each of the three roles. Confirm it restarts at step 0 every time, regardless of whether the auto-shown tour was previously completed or skipped.

- [ ] **Step 5: Missing-target fallback**

For a teacher test account with zero owned sections (or temporarily delete/hide their sections to test this), replay the tutorial and advance to the `widget-teacher` step. Confirm it falls back to a centered card with no arrow/circle, rather than erroring or rendering incorrectly.

- [ ] **Step 6: Dark mode pass**

Toggle dark mode, then run through the tour once more for any one role. Confirm no hardcoded-light colors appear (card, text, buttons should all look correct against the dark shell).

- [ ] **Step 7: Sidebar-hidden-mid-tour check**

Start a tour on any role, then click the "Hide sidebar" toggle button (top-left of the topbar) while a sidebar-targeting step (e.g. "Join your classes") is showing. Observe what happens to the circle/arrow/card.

If it breaks visibly (e.g. the circle/arrow point at empty space where the sidebar used to be, or the card jumps somewhere nonsensical) rather than gracefully falling back to a centered card, apply this fix: in `frontend/src/components/Layout.jsx`, find the `toggleSidebar` function and disable it while the tour is active by checking `useTutorial()`'s state. This requires `TutorialContext`'s value to also expose whether a tour is currently active — change `frontend/src/components/tutorial/TutorialProvider.jsx`'s context value from:

```jsx
    <TutorialContext.Provider value={{ replay }}>
```

to:

```jsx
    <TutorialContext.Provider value={{ replay, active }}>
```

Then in `frontend/src/components/Layout.jsx`, import `useTutorial` from `./tutorial/TutorialContext`, call `const { active: tutorialActive } = useTutorial()` — but note `useTutorial()` can only be called from a component *inside* `TutorialProvider`, and `Layout.jsx` itself renders `TutorialProvider`, so it can't consume its own context. Instead, guard the toggle button's `onClick` from within `Sidebar.jsx`/`TopBar.jsx` (both already render as children of `TutorialProvider`) rather than `Layout.jsx`: pass a `disabled={tutorialActive}` prop through to the sidebar-toggle `<button>` in `TopBar.jsx`, sourcing `tutorialActive` from `useTutorial()` called inside `TopBar.jsx` itself. Only make this change if Step 7's observation actually shows a visible break — if the fallback already looks acceptable, leave it as-is per YAGNI.

- [ ] **Step 8: Navigate-away-mid-tour check**

Start a tour on any role, and while a step targeting a sidebar link is showing, click a *different* real sidebar link (one not currently highlighted) to navigate to a new page mid-tour. Confirm the overlay and card remain visible and don't crash or throw a console error — the card should just continue pointing at the same `data-tour` target if it still exists on the new page (most nav items are always present regardless of route), or fall back to centered if it doesn't.

- [ ] **Step 9: Final commit**

If Steps 1–8 surfaced no bugs, there's nothing to commit here. If any bug was found and fixed during this task, commit it separately with a message describing the specific bug (e.g. `git commit -m "Fix tutorial card overlapping target on narrow viewports"`), scoped to just the files that changed for that fix.
