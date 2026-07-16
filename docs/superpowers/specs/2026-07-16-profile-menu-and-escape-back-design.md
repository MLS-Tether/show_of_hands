# Profile Menu Unification & "Press ESC to go back"

## Context

Student/teacher and admin currently have two different implementations of the same account menu (avatar → dropdown → profile/logout), living in different places (top bar vs. sidebar) with different styling. Separately, the app has a mix of clickable "← Back" buttons (in-page state navigation) and a silent, undiscoverable Escape-key route-back system (`Layout.jsx` + `utils/escNavigation.js`) that only covers student/teacher routes. This work unifies the profile menu to match admin's look/placement everywhere, and makes "press Escape to go back" a visible, universal affordance across student, teacher, and admin — replacing the remaining "← Back" buttons with text hints.

## Part 1 — Profile menu unification

**Goal:** student/teacher account access should look and behave exactly like admin's: bottom-of-sidebar placement, avatar with initials + username + role, dropdown opening upward.

**Changes:**

- `frontend/src/components/Sidebar.jsx`: add a bottom account footer, structurally identical to `AdminSidebar.jsx`'s (lines ~26-91, 123-156):
  - Fetch the current user via `GET /users/{userId}` (using `getUserId()` from `utils/auth`), on mount + `useAutoRefresh`.
  - Render `<div className="sidebar-account">` containing the dropdown menu (`sidebar-menu`, opens **upward**: `bottom: calc(100% + 6px)`) and the footer button (`sidebar-footer`) with `sidebar-avatar` (initials), `sidebar-footer-name`, `sidebar-footer-role`.
  - Reuse the existing click-outside-to-close (`menuRef` + `mousedown` listener) and `handleLogout` logic currently in `TopBar.jsx` — move it here.
- `frontend/src/components/TopBar.jsx`: remove `topbar-account`/`topbar-avatar`/`topbar-menu` and all associated state/handlers (`menuOpen`, `menuRef`, `handleLogout`, the click-outside effect). Keep `NotificationBell` and points display.
- `frontend/src/components/Sidebar.css`: add `.sidebar-account`, `.sidebar-footer`, `.sidebar-avatar`, `.sidebar-footer-text`, `.sidebar-footer-name`, `.sidebar-footer-role`, `.sidebar-menu` (+ button styles), with the same values as `AdminSidebar.css`'s equivalents. Update `.sidebar` to `position: sticky; top: 0; height: 100svh; overflow-y: auto` and wrap the nav links in a `.sidebar-nav` container with `flex: 1` (mirroring `.admin-sidebar` / `.admin-sidebar-nav`) so the footer pins to the bottom.
- `frontend/src/components/TopBar.css`: remove the now-unused `.topbar-account`/`.topbar-avatar`/`.topbar-menu` rules.
- **Cleanup**: extract the duplicated `initials(name)` helper (currently in `AdminSidebar.jsx` and `AdminUsers.jsx`) into `frontend/src/utils/format.js`, and have `AdminSidebar.jsx`, `AdminUsers.jsx`, and the updated `Sidebar.jsx` import it — avoids a third copy.

No backend changes needed (the `GET /users/{id}` endpoint already exists and is used the same way by `AdminSidebar`).

## Part 2 — "Press ESC to go back" everywhere

**Goal:** every place the app currently supports "going back" — whether via a route change or in-page state — shows a visible "Press ESC to go back" hint, and pressing Escape performs the right action without double-firing.

### Two kinds of "back," unified into one visible affordance

1. **Route-level back** — already implemented silently: `Layout.jsx` listens for Escape globally and calls `getParentPath()` (`utils/escNavigation.js`) to navigate to a parent route (e.g. `/sections/:id` → `/sections`). No hint is shown anywhere today.
2. **In-page state back** — three existing "← Back" buttons:
   - `TeacherSectionDetail.jsx` line ~183-191: exits an active card view back to the grid (`setActiveCard(null)`).
   - `StudentGradeDetail.jsx` line ~6-8: exits the student-grade sub-view back to the roster (`onBack` → `setViewingStudent(null)`).
   - `AdminStudentDetail.jsx` line ~54: navigates to `/admin/users` — this is actually a route change done via button instead of the route-map, so it gets folded into category 1 instead of staying a special case.

### Extending the route-level system to admin

- `utils/escNavigation.js`: add `ADMIN_ROUTE_PARENTS = [{ pattern: /^\/admin\/users\/[^/]+$/, parent: '/admin/users' }]` and export `getAdminParentPath(pathname)`, following the exact shape of the existing `getParentPath`.
- `components/admin/AdminLayout.jsx`: add the same Escape `useEffect` + `keydown` listener that `Layout.jsx` has, using `getAdminParentPath`.
- `pages/admin/AdminStudentDetail.jsx`: remove the "← Back to users" button and its `onClick` entirely — Escape now handles it globally.

### Visible hint in the top bar

- `components/TopBar.jsx`: compute `const parentPath = getParentPath(location.pathname, { isTeacher: isTeacher() })`; when truthy, render a small `Press ESC to go back` hint (new `topbar-esc-hint` class) alongside the logo.
- `components/admin/AdminTopBar.jsx`: compute `const parentPath = getAdminParentPath(location.pathname)`; when truthy, render the same hint text next to the breadcrumb.
- The hint is plain text, not a button — it only communicates the existing keyboard affordance.

### In-page state back: hook + collision avoidance

New `utils/escapeClaim.js` — a minimal module-level coordination flag:

```js
let claimed = false
export function claimEscape() { claimed = true }
export function releaseEscape() { claimed = false }
export function isEscapeClaimed() { return claimed }
```

`Layout.jsx` and `AdminLayout.jsx`'s Escape handlers check `isEscapeClaimed()` first and no-op if true — this prevents a single Escape press from both closing an in-page view *and* navigating away from the route, since both listeners are mounted on `document` simultaneously.

New `utils/useEscapeBack.js`:

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

**`TeacherSectionDetail.jsx`** calls this once, with precedence baked into the callback:

```js
useEscapeBack(() => {
  if (viewingStudent) setViewingStudent(null)
  else setActiveCard(null)
}, Boolean(activeCard))
```

- The outer "← Back" button (line ~179-181, currently always shown when `activeCard` is set) is replaced with `Press ESC to go back` text, but only rendered when `!viewingStudent` (so only one hint shows at a time, matching which action Escape will actually perform).
- `StudentGradeDetail.jsx`'s "← Back" button becomes `Press ESC to go back` text — it doesn't need its own `useEscapeBack` call since it's rendered as a child of `TeacherSectionDetail`, which already owns the single Escape listener and calls `onBack` (→ `setViewingStudent(null)`) with the right precedence.

### Testing / verification

- Manual: on `/sections/:id` (teacher), open a card (e.g. Roster) → hint text shown, Escape closes it back to the grid, no unwanted navigation to `/sections`. Click into a student from Roster → hint text shown for that sub-view, Escape returns to roster (not the grid, not `/sections`). With no card open, Escape on `/sections/:id` navigates to `/sections` (existing behavior, now with a visible hint in the TopBar).
- Manual: `/admin/users/:studentId` → hint shown in AdminTopBar, Escape navigates to `/admin/users`.
- Manual: profile menu — as a student and as a teacher, confirm the sidebar footer shows correct username/role/initials, dropdown opens upward, "My profile" and "Log out" both work exactly as before.
- No backend tests needed — this is frontend-only.
