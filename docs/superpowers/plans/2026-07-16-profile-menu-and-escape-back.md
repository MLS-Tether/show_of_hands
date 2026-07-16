# Profile Menu Unification & "Press ESC to go back" Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the student/teacher account menu into the sidebar to match the admin's exact placement/styling, and make "press Escape to go back" a visible, universal affordance across student, teacher, and admin pages — replacing the remaining "← Back" buttons with text hints.

**Architecture:** Two independent pieces sharing one small coordination utility. (1) A profile-menu move: lift the avatar/dropdown/logout block out of `TopBar.jsx` into `Sidebar.jsx`, mirroring `AdminSidebar.jsx`'s structure and CSS. (2) An Escape-to-back system: extend the existing student/teacher-only route-map (`utils/escNavigation.js` + `Layout.jsx`) to cover admin routes too, add a visible hint in both top bars, and convert the three remaining "← Back" buttons (two in `TeacherSectionDetail.jsx`, one in `AdminStudentDetail.jsx`) into either a local Escape hook (`utils/useEscapeBack.js`) or the same route-level system. A tiny shared flag (`utils/escapeClaim.js`) stops a single Escape press from both closing an in-page view and navigating away from the route at the same time.

**Tech Stack:** React 19 + Vite frontend (`frontend/src`), plain CSS per-component files, `react-router-dom` v7. No backend changes. No frontend test runner exists in this repo (`frontend/package.json` has no test script) — verification is `npm run lint`, `npm run build`, and manual browser walkthroughs, matching this project's existing convention.

## Global Constraints

- No new dependencies — everything here is plain React/CSS using patterns already in the codebase.
- Every task must pass `npm run lint` and `npm run build` (run from `frontend/`) before committing.
- Follow existing code style: no comments unless the WHY is non-obvious, functional components, existing CSS variable tokens (`--text-h`, `--text-muted`, `--surface-1`, `--border-strong`, `--bg`, `--shadow`, `--accent`, etc.) — do not invent new tokens.
- Reuse `getUserId()` / `isTeacher()` / `isAdmin()` from `frontend/src/utils/auth.js` and `useAutoRefresh()` from `frontend/src/utils/autoRefresh.js` wherever user/refresh logic is needed — do not reimplement.

---

### Task 1: Extract shared `initials()` helper

**Files:**
- Modify: `frontend/src/utils/format.js`
- Modify: `frontend/src/components/admin/AdminSidebar.jsx:1-24`
- Modify: `frontend/src/pages/admin/AdminUsers.jsx:1-26`

**Interfaces:**
- Produces: `initials(name: string | null | undefined): string` exported from `frontend/src/utils/format.js`, used by Task 6's new `Sidebar.jsx`.

- [ ] **Step 1: Add `initials()` to `utils/format.js`**

Current file:
```js
export function formatPercent(value, digits = 1) {
  if (value == null) return null
  return `${value.toFixed(digits)}%`
}
```

New file:
```js
export function formatPercent(value, digits = 1) {
  if (value == null) return null
  return `${value.toFixed(digits)}%`
}

export function initials(name) {
  if (!name) return '?'
  return name.slice(0, 2).toUpperCase()
}
```

- [ ] **Step 2: Update `AdminSidebar.jsx` to import it instead of defining it locally**

In `frontend/src/components/admin/AdminSidebar.jsx`, change the import block:
```js
import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import api from '../../api'
import { getUserId } from '../../utils/auth'
import { useAutoRefresh } from '../../utils/autoRefresh'
import './AdminSidebar.css'
```
to:
```js
import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import api from '../../api'
import { getUserId } from '../../utils/auth'
import { useAutoRefresh } from '../../utils/autoRefresh'
import { initials } from '../../utils/format'
import './AdminSidebar.css'
```
and delete the local function:
```js
function initials(name) {
  if (!name) return '?'
  return name.slice(0, 2).toUpperCase()
}
```

- [ ] **Step 3: Update `AdminUsers.jsx` the same way**

In `frontend/src/pages/admin/AdminUsers.jsx`, change:
```js
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api'
import { useDialog } from '../../components/DialogContext'
import { useToast } from '../../components/ToastContext'
import { useAutoRefresh } from '../../utils/autoRefresh'
import './admin-shared.css'
import './AdminUsers.css'
```
to:
```js
import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../../api'
import { useDialog } from '../../components/DialogContext'
import { useToast } from '../../components/ToastContext'
import { useAutoRefresh } from '../../utils/autoRefresh'
import { initials } from '../../utils/format'
import './admin-shared.css'
import './AdminUsers.css'
```
and delete the local function:
```js
function initials(name) {
  if (!name) return '?'
  return name.slice(0, 2).toUpperCase()
}
```

- [ ] **Step 4: Verify**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both commands exit 0, no "unused variable" or "not defined" errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/utils/format.js frontend/src/components/admin/AdminSidebar.jsx frontend/src/pages/admin/AdminUsers.jsx
git commit -m "Extract shared initials() helper into utils/format.js"
```

---

### Task 2: Add Escape coordination utilities

**Files:**
- Create: `frontend/src/utils/escapeClaim.js`
- Create: `frontend/src/utils/useEscapeBack.js`

**Interfaces:**
- Produces: `claimEscape(): void`, `releaseEscape(): void`, `isEscapeClaimed(): boolean` from `escapeClaim.js` — consumed by Task 3's `Layout.jsx`, Task 4's `AdminLayout.jsx`, and internally by `useEscapeBack.js`.
- Produces: `useEscapeBack(onBack: () => void, active: boolean): void` from `useEscapeBack.js` — consumed by Task 7's `TeacherSectionDetail.jsx`.

- [ ] **Step 1: Create `escapeClaim.js`**

```js
let claimed = false

export function claimEscape() {
  claimed = true
}

export function releaseEscape() {
  claimed = false
}

export function isEscapeClaimed() {
  return claimed
}
```

- [ ] **Step 2: Create `useEscapeBack.js`**

```js
import { useEffect } from 'react'
import { claimEscape, releaseEscape } from './escapeClaim'

export function useEscapeBack(onBack, active) {
  useEffect(() => {
    if (!active) return
    claimEscape()
    function handleKeyDown(e) {
      if (e.key === 'Escape') onBack()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      releaseEscape()
    }
  }, [active, onBack])
}
```

- [ ] **Step 3: Verify**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both exit 0. (These two files aren't imported anywhere yet, so this only checks syntax/lint — behavioral verification happens in Tasks 3, 4, and 7 once they're wired up.)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/escapeClaim.js frontend/src/utils/useEscapeBack.js
git commit -m "Add escapeClaim and useEscapeBack utilities for coordinated Escape handling"
```

---

### Task 3: Extend `escNavigation.js` for admin routes + wire the claim check into `Layout.jsx`

**Files:**
- Modify: `frontend/src/utils/escNavigation.js`
- Modify: `frontend/src/components/Layout.jsx`

**Interfaces:**
- Consumes: `isEscapeClaimed()` from Task 2's `escapeClaim.js`.
- Produces: `getAdminParentPath(pathname: string): string | null` from `escNavigation.js` — consumed by Task 4's `AdminLayout.jsx` and Task 5's `AdminTopBar.jsx`.
- Produces (unchanged signature, still consumed by Task 5's `TopBar.jsx`): `getParentPath(pathname: string, opts?: { isTeacher?: boolean }): string | null`.

- [ ] **Step 1: Add the admin route map to `escNavigation.js`**

Current file ends with:
```js
export function getParentPath(pathname, { isTeacher = false } = {}) {
  if (isTeacher) {
    const override = TEACHER_ROUTE_OVERRIDES.find((r) => r.pattern.test(pathname))
    if (override) return override.parent
  }
  const match = ROUTE_PARENTS.find((r) => r.pattern.test(pathname))
  return match ? match.parent : null
}
```

Add after it:
```js
const ADMIN_ROUTE_PARENTS = [
  { pattern: /^\/admin\/users\/[^/]+$/, parent: '/admin/users' },
]

export function getAdminParentPath(pathname) {
  const match = ADMIN_ROUTE_PARENTS.find((r) => r.pattern.test(pathname))
  return match ? match.parent : null
}
```

- [ ] **Step 2: Make `Layout.jsx`'s Escape handler respect a claim**

Current file:
```jsx
import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'
import { getParentPath } from '../utils/escNavigation'
import { isTeacher } from '../utils/auth'
import './Layout.css'

function Layout() {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      const parent = getParentPath(location.pathname, { isTeacher: isTeacher() })
      if (!parent) return
      if (parent === 'BACK') {
        navigate(-1)
      } else {
        navigate(parent)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [location.pathname, navigate])

  return (
    <div className="app-shell">
      <TopBar />
      <div className="app-body">
        <Sidebar />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
```

Change the import block and `handleKeyDown`:
```jsx
import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import TopBar from './TopBar'
import Sidebar from './Sidebar'
import { getParentPath } from '../utils/escNavigation'
import { isEscapeClaimed } from '../utils/escapeClaim'
import { isTeacher } from '../utils/auth'
import './Layout.css'

function Layout() {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      if (isEscapeClaimed()) return
      const parent = getParentPath(location.pathname, { isTeacher: isTeacher() })
      if (!parent) return
      if (parent === 'BACK') {
        navigate(-1)
      } else {
        navigate(parent)
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [location.pathname, navigate])

  return (
    <div className="app-shell">
      <TopBar />
      <div className="app-body">
        <Sidebar />
        <main className="app-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

export default Layout
```

- [ ] **Step 3: Verify**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both exit 0.

Manual check (dev server): start `npm run dev`, log in as a student, navigate to `/sections/:id` for an enrolled section, press Escape — still navigates back to `/sections` exactly as before (this confirms the claim check didn't break the existing behavior, since nothing claims Escape yet).

- [ ] **Step 4: Commit**

```bash
git add frontend/src/utils/escNavigation.js frontend/src/components/Layout.jsx
git commit -m "Extend escNavigation with admin route map, respect escape claims in Layout"
```

---

### Task 4: Add the Escape listener to `AdminLayout.jsx`

**Files:**
- Modify: `frontend/src/components/admin/AdminLayout.jsx`

**Interfaces:**
- Consumes: `getAdminParentPath()` from Task 3's `escNavigation.js`, `isEscapeClaimed()` from Task 2's `escapeClaim.js`.

- [ ] **Step 1: Add the listener, mirroring `Layout.jsx`'s pattern**

Current file:
```jsx
import { Navigate, Outlet } from 'react-router-dom'
import AdminSidebar from './AdminSidebar'
import AdminTopBar from './AdminTopBar'
import { isAdmin } from '../../utils/auth'
import './AdminLayout.css'

function AdminLayout() {
  if (!isAdmin()) return <Navigate to="/dashboard" replace />

  return (
    <div className="admin-shell">
      <AdminSidebar />
      <div className="admin-main">
        <AdminTopBar />
        <main className="admin-content">
          <div className="admin-content-inner">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default AdminLayout
```

New file (the `useEffect` hook must run on every render, so it's placed before the `isAdmin()` early return per React's Rules of Hooks):
```jsx
import { useEffect } from 'react'
import { Navigate, Outlet, useLocation, useNavigate } from 'react-router-dom'
import AdminSidebar from './AdminSidebar'
import AdminTopBar from './AdminTopBar'
import { getAdminParentPath } from '../../utils/escNavigation'
import { isEscapeClaimed } from '../../utils/escapeClaim'
import { isAdmin } from '../../utils/auth'
import './AdminLayout.css'

function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  useEffect(() => {
    function handleKeyDown(e) {
      if (e.key !== 'Escape') return
      if (isEscapeClaimed()) return
      const parent = getAdminParentPath(location.pathname)
      if (!parent) return
      navigate(parent)
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [location.pathname, navigate])

  if (!isAdmin()) return <Navigate to="/dashboard" replace />

  return (
    <div className="admin-shell">
      <AdminSidebar />
      <div className="admin-main">
        <AdminTopBar />
        <main className="admin-content">
          <div className="admin-content-inner">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}

export default AdminLayout
```

- [ ] **Step 2: Verify**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both exit 0.

Manual check: log in as `admin_demo`, navigate to `/admin/users/3` (or any existing student id — use the Users list to find one), press Escape. Expected: navigates to `/admin/users`. Then on `/admin/users` itself, press Escape — expected: nothing happens (no parent mapped for that route).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/admin/AdminLayout.jsx
git commit -m "Add Escape-to-back navigation to AdminLayout"
```

---

### Task 5: Show "Press ESC to go back" in both top bars

**Files:**
- Modify: `frontend/src/components/TopBar.jsx`
- Modify: `frontend/src/components/TopBar.css`
- Modify: `frontend/src/components/admin/AdminTopBar.jsx`
- Modify: `frontend/src/components/admin/AdminTopBar.css`

**Interfaces:**
- Consumes: `getParentPath()` and `getAdminParentPath()` from Task 3's `escNavigation.js`.

- [ ] **Step 1: Add the hint to `TopBar.jsx`**

Current file:
```jsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api'
import NotificationBell from './NotificationBell'
import { useAutoRefresh } from '../utils/autoRefresh'
import './TopBar.css'

function TopBar() {
  const navigate = useNavigate()
  const [points, setPoints] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  const loadPoints = useCallback(() => {
    const userId = localStorage.getItem('user_id')
    if (!userId) return undefined
    let cancelled = false

    api
      .get(`/users/${userId}/points`)
      .then(({ data }) => {
        if (!cancelled) setPoints(data.total_points)
      })
      .catch(() => {
        if (!cancelled) setPoints((prev) => prev ?? null)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => loadPoints(), [loadPoints])
  useAutoRefresh(loadPoints)

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  async function handleLogout() {
    const refreshToken = localStorage.getItem('refresh_token')
    try {
      await api.post('/auth/logout', { refresh_token: refreshToken })
    } catch {
      // best-effort: still clear local session and redirect below
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('role')
    navigate('/auth')
  }

  return (
    <header className="topbar">
      <div className="topbar-logo">Show of Hands</div>
      <div className="topbar-actions">
        <NotificationBell />
        <span className="topbar-points">{points === null ? '—' : points} pts</span>
        <div className="topbar-account" ref={menuRef}>
          <button
            type="button"
            className="topbar-avatar"
            aria-label="Account menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          />
          {menuOpen && (
            <div className="topbar-menu" role="menu">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  navigate('/profile')
                }}
              >
                My profile
              </button>
              <button type="button" role="menuitem" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default TopBar
```

Only add the hint in this task (the account menu block is removed in Task 6 — don't touch it here):
```jsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import api from '../api'
import NotificationBell from './NotificationBell'
import { useAutoRefresh } from '../utils/autoRefresh'
import { getParentPath } from '../utils/escNavigation'
import { isTeacher } from '../utils/auth'
import './TopBar.css'

function TopBar() {
  const navigate = useNavigate()
  const location = useLocation()
  const [points, setPoints] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  const parentPath = getParentPath(location.pathname, { isTeacher: isTeacher() })

  const loadPoints = useCallback(() => {
    const userId = localStorage.getItem('user_id')
    if (!userId) return undefined
    let cancelled = false

    api
      .get(`/users/${userId}/points`)
      .then(({ data }) => {
        if (!cancelled) setPoints(data.total_points)
      })
      .catch(() => {
        if (!cancelled) setPoints((prev) => prev ?? null)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => loadPoints(), [loadPoints])
  useAutoRefresh(loadPoints)

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  async function handleLogout() {
    const refreshToken = localStorage.getItem('refresh_token')
    try {
      await api.post('/auth/logout', { refresh_token: refreshToken })
    } catch {
      // best-effort: still clear local session and redirect below
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('role')
    navigate('/auth')
  }

  return (
    <header className="topbar">
      <div className="topbar-logo">
        Show of Hands
        {parentPath && <span className="topbar-esc-hint">Press ESC to go back</span>}
      </div>
      <div className="topbar-actions">
        <NotificationBell />
        <span className="topbar-points">{points === null ? '—' : points} pts</span>
        <div className="topbar-account" ref={menuRef}>
          <button
            type="button"
            className="topbar-avatar"
            aria-label="Account menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          />
          {menuOpen && (
            <div className="topbar-menu" role="menu">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  navigate('/profile')
                }}
              >
                My profile
              </button>
              <button type="button" role="menuitem" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}

export default TopBar
```

- [ ] **Step 2: Add the CSS for the hint**

In `frontend/src/components/TopBar.css`, change:
```css
.topbar-logo {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-h);
}
```
to:
```css
.topbar-logo {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-h);
  display: flex;
  align-items: center;
  gap: 10px;
}

.topbar-esc-hint {
  font-size: 11px;
  font-weight: 400;
  color: var(--text-muted);
}
```

- [ ] **Step 3: Add the hint to `AdminTopBar.jsx`**

Current file:
```jsx
import { useLocation } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import api from '../../api'
import NotificationBell from '../NotificationBell'
import { getTheme, setTheme } from '../../utils/theme'
import { useAutoRefresh } from '../../utils/autoRefresh'
import './AdminTopBar.css'

const BREADCRUMBS = {
  '/admin/overview': 'Overview',
  '/admin/inbox': 'Approvals · Inbox',
  '/admin/sections': 'Manage · Sections',
  '/admin/users': 'Manage · Users',
  '/admin/settings': 'School · Settings',
  '/admin/profile': 'My profile',
}

function AdminTopBar() {
  const location = useLocation()
  const [theme, setThemeState] = useState(getTheme())
  const [points, setPoints] = useState(null)
  const breadcrumb = BREADCRUMBS[location.pathname] || 'Admin'

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setThemeState(next)
  }

  const loadPoints = useCallback(() => {
    let cancelled = false
    api
      .get('/schools/points')
      .then(({ data }) => {
        if (!cancelled) setPoints(data.total_points)
      })
      .catch(() => {
        if (!cancelled) setPoints((prev) => prev ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => loadPoints(), [loadPoints])
  useAutoRefresh(loadPoints)

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-breadcrumb">{breadcrumb}</div>
      <div className="admin-topbar-actions">
        {points !== null && (
          <span className="admin-topbar-points">{points.toLocaleString()} school pts</span>
        )}
        <NotificationBell />
        <button type="button" className="admin-topbar-theme" onClick={toggleTheme}>
          {theme === 'dark' ? 'Dark' : 'Light'}
        </button>
      </div>
    </header>
  )
}

export default AdminTopBar
```

New file:
```jsx
import { useLocation } from 'react-router-dom'
import { useCallback, useEffect, useState } from 'react'
import api from '../../api'
import NotificationBell from '../NotificationBell'
import { getTheme, setTheme } from '../../utils/theme'
import { useAutoRefresh } from '../../utils/autoRefresh'
import { getAdminParentPath } from '../../utils/escNavigation'
import './AdminTopBar.css'

const BREADCRUMBS = {
  '/admin/overview': 'Overview',
  '/admin/inbox': 'Approvals · Inbox',
  '/admin/sections': 'Manage · Sections',
  '/admin/users': 'Manage · Users',
  '/admin/settings': 'School · Settings',
  '/admin/profile': 'My profile',
}

function AdminTopBar() {
  const location = useLocation()
  const [theme, setThemeState] = useState(getTheme())
  const [points, setPoints] = useState(null)
  const breadcrumb = BREADCRUMBS[location.pathname] || 'Admin'
  const parentPath = getAdminParentPath(location.pathname)

  function toggleTheme() {
    const next = theme === 'dark' ? 'light' : 'dark'
    setTheme(next)
    setThemeState(next)
  }

  const loadPoints = useCallback(() => {
    let cancelled = false
    api
      .get('/schools/points')
      .then(({ data }) => {
        if (!cancelled) setPoints(data.total_points)
      })
      .catch(() => {
        if (!cancelled) setPoints((prev) => prev ?? null)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => loadPoints(), [loadPoints])
  useAutoRefresh(loadPoints)

  return (
    <header className="admin-topbar">
      <div className="admin-topbar-breadcrumb">
        {breadcrumb}
        {parentPath && <span className="admin-topbar-esc-hint">Press ESC to go back</span>}
      </div>
      <div className="admin-topbar-actions">
        {points !== null && (
          <span className="admin-topbar-points">{points.toLocaleString()} school pts</span>
        )}
        <NotificationBell />
        <button type="button" className="admin-topbar-theme" onClick={toggleTheme}>
          {theme === 'dark' ? 'Dark' : 'Light'}
        </button>
      </div>
    </header>
  )
}

export default AdminTopBar
```

- [ ] **Step 4: Add the CSS for the admin hint**

In `frontend/src/components/admin/AdminTopBar.css`, change:
```css
.admin-topbar-breadcrumb {
  font-size: 13.5px;
  color: var(--text-muted);
}
```
to:
```css
.admin-topbar-breadcrumb {
  font-size: 13.5px;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 10px;
}

.admin-topbar-esc-hint {
  font-size: 11px;
  color: var(--text-muted);
}
```

- [ ] **Step 5: Verify**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both exit 0.

Manual check: as a student, visit `/dashboard` (no hint expected) then `/sections/:id` (hint expected in the top-left, next to "Show of Hands"). As admin, visit `/admin/users` (no hint) then `/admin/users/:studentId` (hint expected next to the breadcrumb).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/TopBar.jsx frontend/src/components/TopBar.css frontend/src/components/admin/AdminTopBar.jsx frontend/src/components/admin/AdminTopBar.css
git commit -m "Show a Press ESC to go back hint in both top bars"
```

---

### Task 6: Move the profile menu from `TopBar` into `Sidebar`

**Files:**
- Modify: `frontend/src/components/Sidebar.jsx`
- Modify: `frontend/src/components/Sidebar.css`
- Modify: `frontend/src/components/TopBar.jsx`
- Modify: `frontend/src/components/TopBar.css`

**Interfaces:**
- Consumes: `initials()` from Task 1's `utils/format.js`, `getUserId()` from `utils/auth.js`, `useAutoRefresh()` from `utils/autoRefresh.js`.

- [ ] **Step 1: Replace `Sidebar.jsx`**

Current file:
```jsx
import { NavLink } from 'react-router-dom'
import { isTeacher } from '../utils/auth'
import './Sidebar.css'

const NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'My sections', to: '/sections' },
  { label: 'Assignments', to: '/assignments', studentOnly: true },
  { label: 'Quests', to: '/quests' },
  { label: 'Bulletin board', to: '/bulletin-board', studentOnly: true },
  { label: 'Study rooms', to: '/study-rooms', studentOnly: true },
  { label: 'Points', to: '/points', studentOnly: true },
]

function Sidebar() {
  const teacher = isTeacher()
  const items = NAV_ITEMS.filter((item) => !item.studentOnly || !teacher)

  return (
    <nav className="sidebar" aria-label="Main">
      {items.map((item) => (
        <NavLink
          key={item.to}
          to={item.to}
          end={item.end}
          className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
        >
          {item.label}
        </NavLink>
      ))}
    </nav>
  )
}

export default Sidebar
```

New file:
```jsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import api from '../api'
import { getUserId, isTeacher } from '../utils/auth'
import { useAutoRefresh } from '../utils/autoRefresh'
import { initials } from '../utils/format'
import './Sidebar.css'

const NAV_ITEMS = [
  { label: 'Dashboard', to: '/dashboard', end: true },
  { label: 'My sections', to: '/sections' },
  { label: 'Assignments', to: '/assignments', studentOnly: true },
  { label: 'Quests', to: '/quests' },
  { label: 'Bulletin board', to: '/bulletin-board', studentOnly: true },
  { label: 'Study rooms', to: '/study-rooms', studentOnly: true },
  { label: 'Points', to: '/points', studentOnly: true },
]

function Sidebar() {
  const navigate = useNavigate()
  const teacher = isTeacher()
  const items = NAV_ITEMS.filter((item) => !item.studentOnly || !teacher)

  const [user, setUser] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)
  const menuRef = useRef(null)

  const load = useCallback(() => {
    let cancelled = false
    api
      .get(`/users/${getUserId()}`)
      .then(({ data }) => {
        if (!cancelled) setUser(data)
      })
      .catch(() => {
        if (!cancelled) setUser((prev) => prev)
      })
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => load(), [load])
  useAutoRefresh(load)

  useEffect(() => {
    if (!menuOpen) return
    function handleClickOutside(e) {
      if (menuRef.current && !menuRef.current.contains(e.target)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [menuOpen])

  async function handleLogout() {
    const refreshToken = localStorage.getItem('refresh_token')
    try {
      await api.post('/auth/logout', { refresh_token: refreshToken })
    } catch {
      // best-effort: still clear local session and redirect below
    }
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('user_id')
    localStorage.removeItem('role')
    navigate('/auth')
  }

  return (
    <nav className="sidebar" aria-label="Main">
      <div className="sidebar-nav">
        {items.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            className={({ isActive }) => `sidebar-link${isActive ? ' active' : ''}`}
          >
            {item.label}
          </NavLink>
        ))}
      </div>

      {user && (
        <div className="sidebar-account" ref={menuRef}>
          {menuOpen && (
            <div className="sidebar-menu" role="menu">
              <button
                type="button"
                role="menuitem"
                onClick={() => {
                  setMenuOpen(false)
                  navigate('/profile')
                }}
              >
                My profile
              </button>
              <button type="button" role="menuitem" onClick={handleLogout}>
                Log out
              </button>
            </div>
          )}
          <button
            type="button"
            className="sidebar-footer"
            aria-label="Account menu"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((open) => !open)}
          >
            <div className="sidebar-avatar">{initials(user.username)}</div>
            <div className="sidebar-footer-text">
              <div className="sidebar-footer-name">{user.username}</div>
              <div className="sidebar-footer-role">{user.role}</div>
            </div>
          </button>
        </div>
      )}
    </nav>
  )
}

export default Sidebar
```

- [ ] **Step 2: Replace `Sidebar.css`**

Current file:
```css
.sidebar {
  width: 170px;
  flex-shrink: 0;
  border-right: 1px solid var(--border-strong);
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar-link {
  font-size: 14px;
  color: var(--text);
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 6px;
}

.sidebar-link:hover {
  background: var(--surface-1);
}

.sidebar-link.active {
  background: var(--text-h);
  color: var(--bg);
  font-weight: 500;
}
```

New file (note: `.sidebar` gains `position: sticky` + fixed height + `overflow-y: auto`, and a new `.sidebar-nav` wrapper gets `flex: 1` so the account footer pins to the bottom — this mirrors `AdminSidebar.css`'s `.admin-sidebar`/`.admin-sidebar-nav` split exactly. The account-menu block below reuses `var(--surface-1)` for hover backgrounds rather than admin's `var(--surface-2)`, matching the token this file already uses for `.sidebar-link:hover` — same visual effect via this app's existing non-admin surface convention):
```css
.sidebar {
  width: 170px;
  flex-shrink: 0;
  position: sticky;
  top: 0;
  height: 100svh;
  overflow-y: auto;
  border-right: 1px solid var(--border-strong);
  display: flex;
  flex-direction: column;
}

.sidebar-nav {
  flex: 1;
  padding: 14px 10px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.sidebar-link {
  font-size: 14px;
  color: var(--text);
  text-decoration: none;
  padding: 8px 10px;
  border-radius: 6px;
}

.sidebar-link:hover {
  background: var(--surface-1);
}

.sidebar-link.active {
  background: var(--text-h);
  color: var(--bg);
  font-weight: 500;
}

.sidebar-account {
  position: relative;
  border-top: 1px solid var(--border);
}

.sidebar-footer {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: none;
  border: none;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
}

.sidebar-footer:hover {
  background: var(--surface-1);
}

.sidebar-menu {
  position: absolute;
  bottom: calc(100% + 6px);
  left: 18px;
  right: 18px;
  background: var(--bg);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  box-shadow: var(--shadow);
  overflow: hidden;
  z-index: 10;
}

.sidebar-menu button {
  display: block;
  width: 100%;
  text-align: left;
  padding: 9px 14px;
  font-size: 13px;
  color: var(--text);
  background: none;
  border: none;
  cursor: pointer;
}

.sidebar-menu button:hover {
  background: var(--surface-1);
  color: var(--text-h);
}

.sidebar-avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 50%;
  background: var(--surface-1);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--text-h);
}

.sidebar-footer-text {
  min-width: 0;
}

.sidebar-footer-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-h);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.sidebar-footer-role {
  font-size: 11.5px;
  color: var(--text-muted);
  text-transform: capitalize;
}
```

- [ ] **Step 3: Remove the account menu from `TopBar.jsx`**

Starting from the Task 5 version, remove `menuOpen`/`menuRef`/the click-outside effect/`handleLogout`, and simplify the return. Also drop `useRef` and `useNavigate` from the imports since nothing in this file uses them anymore.

New file:
```jsx
import { useCallback, useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import api from '../api'
import NotificationBell from './NotificationBell'
import { useAutoRefresh } from '../utils/autoRefresh'
import { getParentPath } from '../utils/escNavigation'
import { isTeacher } from '../utils/auth'
import './TopBar.css'

function TopBar() {
  const location = useLocation()
  const [points, setPoints] = useState(null)

  const parentPath = getParentPath(location.pathname, { isTeacher: isTeacher() })

  const loadPoints = useCallback(() => {
    const userId = localStorage.getItem('user_id')
    if (!userId) return undefined
    let cancelled = false

    api
      .get(`/users/${userId}/points`)
      .then(({ data }) => {
        if (!cancelled) setPoints(data.total_points)
      })
      .catch(() => {
        if (!cancelled) setPoints((prev) => prev ?? null)
      })

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => loadPoints(), [loadPoints])
  useAutoRefresh(loadPoints)

  return (
    <header className="topbar">
      <div className="topbar-logo">
        Show of Hands
        {parentPath && <span className="topbar-esc-hint">Press ESC to go back</span>}
      </div>
      <div className="topbar-actions">
        <NotificationBell />
        <span className="topbar-points">{points === null ? '—' : points} pts</span>
      </div>
    </header>
  )
}

export default TopBar
```

- [ ] **Step 4: Remove the now-unused rules from `TopBar.css`**

Delete these rules (everything from `.topbar-account` through the end of `.topbar-menu button:hover`):
```css
.topbar-account {
  position: relative;
}

.topbar-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--surface-1);
  border: 1px solid var(--border-strong);
  padding: 0;
  cursor: pointer;
}

.topbar-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 120px;
  background: var(--bg);
  border: 1px solid var(--border-strong);
  border-radius: 6px;
  box-shadow: var(--shadow);
  overflow: hidden;
  z-index: 10;
}

.topbar-menu button {
  display: block;
  width: 100%;
  text-align: left;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--text);
  background: none;
  border: none;
  cursor: pointer;
}

.topbar-menu button:hover {
  background: var(--surface-1);
  color: var(--text-h);
}
```

- [ ] **Step 5: Verify**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both exit 0, no unused-import warnings.

Manual check (dev server, both a student and a teacher login):
1. Confirm the top-right avatar circle is gone from the top bar.
2. Confirm the sidebar now shows an account footer at the very bottom with initials, username, and role, matching the admin's look.
3. Click it — dropdown opens **upward** with "My profile" / "Log out".
4. Click "My profile" — navigates to `/profile`.
5. Click "Log out" — logs out and redirects to `/auth`.
6. Click outside the open dropdown — it closes.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/Sidebar.jsx frontend/src/components/Sidebar.css frontend/src/components/TopBar.jsx frontend/src/components/TopBar.css
git commit -m "Move student/teacher profile menu into the sidebar, matching admin's placement and styling"
```

---

### Task 7: Convert `TeacherSectionDetail`'s and `StudentGradeDetail`'s "← Back" buttons to Escape hints

**Files:**
- Modify: `frontend/src/components/section-detail/TeacherSectionDetail.jsx`
- Modify: `frontend/src/components/section-detail/StudentGradeDetail.jsx`
- Modify: `frontend/src/components/section-detail/TeacherSectionDetail.css`

**Interfaces:**
- Consumes: `useEscapeBack()` from Task 2's `utils/useEscapeBack.js`.

- [ ] **Step 1: Wire `useEscapeBack` into `TeacherSectionDetail.jsx`**

Add the import (alongside the other imports at the top of the file):
```jsx
import { useEscapeBack } from '../../utils/useEscapeBack'
```

Add the hook call right after the existing `useAutoRefresh(load)` line inside `TeacherSectionDetail()`:
```jsx
  useEffect(() => load(), [load])
  useAutoRefresh(load)

  useEscapeBack(() => {
    if (viewingStudent) setViewingStudent(null)
    else setActiveCard(null)
  }, Boolean(activeCard))
```

- [ ] **Step 2: Replace the outer "← Back" button with a hint, and stop passing `onBack` to `StudentGradeDetail`**

Current block:
```jsx
      {activeCard ? (
        <div>
          <button
            type="button"
            className="teacher-section-back"
            onClick={() => {
              setActiveCard(null)
              setViewingStudent(null)
            }}
          >
            ← Back
          </button>
          {activeCard === 'roster' &&
            (viewingStudent ? (
              <StudentGradeDetail
                sectionId={sectionId}
                student={viewingStudent}
                onBack={() => setViewingStudent(null)}
              />
            ) : (
              <RosterPanel section={section} onSelectStudent={setViewingStudent} />
            ))}
```

New block:
```jsx
      {activeCard ? (
        <div>
          {!viewingStudent && <p className="teacher-section-back">Press ESC to go back</p>}
          {activeCard === 'roster' &&
            (viewingStudent ? (
              <StudentGradeDetail sectionId={sectionId} student={viewingStudent} />
            ) : (
              <RosterPanel section={section} onSelectStudent={setViewingStudent} />
            ))}
```

- [ ] **Step 3: Simplify `StudentGradeDetail.jsx`**

Current file:
```jsx
import GradeSummary from './GradeSummary'

function StudentGradeDetail({ sectionId, student, onBack }) {
  return (
    <div>
      <button type="button" className="teacher-section-back" onClick={onBack}>
        ← Back
      </button>
      <div className="widget-label">{student.username}'s grade</div>
      <GradeSummary sectionId={sectionId} studentId={student.user_id} />
    </div>
  )
}

export default StudentGradeDetail
```

New file:
```jsx
import GradeSummary from './GradeSummary'

function StudentGradeDetail({ sectionId, student }) {
  return (
    <div>
      <p className="teacher-section-back">Press ESC to go back</p>
      <div className="widget-label">{student.username}'s grade</div>
      <GradeSummary sectionId={sectionId} studentId={student.user_id} />
    </div>
  )
}

export default StudentGradeDetail
```

- [ ] **Step 4: Update the CSS — it's no longer a clickable button**

In `frontend/src/components/section-detail/TeacherSectionDetail.css`, change:
```css
.teacher-section-back {
  border: none;
  background: none;
  color: var(--text-muted);
  font-size: 13px;
  cursor: pointer;
  padding: 0 0 14px;
}

.teacher-section-back:hover {
  color: var(--text-h);
}
```
to:
```css
.teacher-section-back {
  color: var(--text-muted);
  font-size: 13px;
  margin: 0 0 14px;
}
```

- [ ] **Step 5: Verify**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both exit 0, no "unused prop" or "onBack is not defined" errors.

Manual check (dev server, logged in as `teacher_demo`): open `/sections/1`, click "Roster" — hint text "Press ESC to go back" shown, no clickable button. Press Escape — closes back to the card grid (does **not** navigate to `/sections`). Open "Roster" again, click a student — hint text shown for that sub-view (the outer hint is hidden). Press Escape — returns to the roster (not the grid, not `/sections`). Press Escape again — now closes back to the grid. Press Escape a third time — now navigates to `/sections` (the pre-existing route-level behavior from Task 3, confirming the claim correctly releases once no card is open).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/section-detail/TeacherSectionDetail.jsx frontend/src/components/section-detail/StudentGradeDetail.jsx frontend/src/components/section-detail/TeacherSectionDetail.css
git commit -m "Replace TeacherSectionDetail back buttons with Press ESC to go back hints"
```

---

### Task 8: Remove `AdminStudentDetail`'s "← Back to users" button

**Files:**
- Modify: `frontend/src/pages/admin/AdminStudentDetail.jsx`

**Interfaces:**
- None new — this page's Escape-to-back is now handled globally by Task 4's `AdminLayout.jsx` + Task 3's `getAdminParentPath()`, and the hint is shown by Task 5's `AdminTopBar.jsx`. No replacement UI is added on the page itself (avoids a redundant duplicate hint alongside the one already in the top bar).

- [ ] **Step 1: Remove the button and the now-unused `useNavigate`**

Current top of file:
```jsx
import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import api from '../../api'
import { formatPercent } from '../../utils/format'
import { downloadReportCard, printReportCard } from '../../utils/reportCard'
import './admin-shared.css'
import './AdminStudentDetail.css'

function AdminStudentDetail() {
  const { studentId } = useParams()
  const navigate = useNavigate()
  const [student, setStudent] = useState(null)
```

New top of file:
```jsx
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
```

Current render block:
```jsx
  return (
    <div className="admin-student-detail">
      <button type="button" className="admin-btn-secondary" onClick={() => navigate('/admin/users')}>
        ← Back to users
      </button>

      <h1 className="admin-page-h1">{student.username}</h1>
```

New render block:
```jsx
  return (
    <div className="admin-student-detail">
      <h1 className="admin-page-h1">{student.username}</h1>
```

- [ ] **Step 2: Verify**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both exit 0, no "navigate is not defined" or unused-import errors.

Manual check (dev server, logged in as `admin_demo`): open `/admin/users`, click a student row → lands on `/admin/users/:id` with the "Press ESC to go back" hint visible in the top bar (from Task 5) and no button on the page itself. Press Escape → navigates back to `/admin/users`.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/admin/AdminStudentDetail.jsx
git commit -m "Remove AdminStudentDetail back button, now handled by global Escape navigation"
```

---

### Task 9: Full end-to-end verification pass

**Files:** none (verification only)

- [ ] **Step 1: Static checks**

```bash
cd frontend && npm run lint && npm run build
```
Expected: both exit 0.

- [ ] **Step 2: Start the app**

```bash
cd backend && ENV=development python -m uvicorn main:app --port 8000 &
cd frontend && npm run dev &
```

- [ ] **Step 3: Walk the student flow**

Log in as `student_hero` / `Passw0rd!`. Confirm:
- Sidebar shows an account footer at the bottom with initials "ST", username `student_hero`, role `student`.
- Clicking it opens a dropdown upward with "My profile" and "Log out".
- Navigate to `/sections/1` (an enrolled section) — "Press ESC to go back" appears in the top bar; pressing Escape returns to `/sections`.
- Navigate to `/dashboard` — no hint shown (no parent route).

- [ ] **Step 4: Walk the teacher flow**

Log in as `teacher_demo` / `Passw0rd!`. Confirm:
- Sidebar account footer shows correctly for the teacher.
- Open `/sections/1`, click "Roster" — hint text shown (not a button), Escape closes the card without leaving the page.
- Click a student in the roster — hint text shown for that sub-view, Escape returns to the roster; Escape again returns to the grid; Escape a third time navigates to `/sections`.

- [ ] **Step 5: Walk the admin flow**

Log in as `admin_demo` / `Passw0rd!`. Confirm:
- Sidebar account footer unchanged from before (this task didn't touch `AdminSidebar.jsx`'s markup, only extracted its `initials()` helper in Task 1).
- `/admin/users` → click a student row → `/admin/users/:id` shows the hint in `AdminTopBar`, no on-page button; Escape returns to `/admin/users`.

- [ ] **Step 6: Stop the dev servers**

```bash
pkill -f "uvicorn main:app"
pkill -f vite
```

- [ ] **Step 7: Final commit (if any cleanup was needed during verification)**

Only run this if Step 3-5 surfaced a fix:
```bash
git add -A
git commit -m "Fix issues found during end-to-end verification"
```
