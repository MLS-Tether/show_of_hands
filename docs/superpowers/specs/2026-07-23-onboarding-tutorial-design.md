# Onboarding Tutorial Overlay — Design

## Summary

A one-time, role-aware guided tour that appears as a modal overlay on top of the real app shell right after a user's first sign-in. It highlights real sidebar/topbar elements with a circle-and-arrow annotation and a floating card, walking the user through the app's core features in a playful, gamified voice ("Quest Map" direction). Replayable anytime from Profile.

This design was originally prototyped as a fully interactive `.dc.html` component in a Claude Design project (imported via the `DesignSync` tool), with three visual directions built out. The user selected **Quest Map** as the direction to ship, with two adjustments: an added Assignments step for students, and `localStorage`-only persistence (no backend change).

## Goals

- Teach a new user the app's core loop in ~30 seconds, without leaving the real app.
- Content adapts to the signed-in role: student, teacher, or admin — same component, different step data.
- Replayable on demand from Profile.
- Zero backend changes.

## Non-goals

- Cross-device/browser persistence of "has seen tutorial" (explicitly deferred — localStorage only, per user decision).
- Supporting the Spotlight or Bottom Coach visual directions (not selected; not built).
- A generic/reusable "product tour engine" for future unrelated features — this is scoped to this one onboarding flow.

## Architecture

### Mounting point

`TutorialProvider` wraps `<Outlet />` inside `Layout.jsx` (`components/Layout.jsx`), not `Dashboard.jsx`. This matters because `isAdmin()` routes straight to `/admin/overview` — a separate component from `Dashboard.jsx` — so mounting inside Dashboard would mean admins never see their tour. `Layout.jsx` wraps every authenticated route (dashboard, admin routes, profile, etc. — confirmed via `App.jsx`'s route tree), so this is the one place that covers all three landing destinations.

### Auto-show logic

On mount, `TutorialProvider` reads `getUserId()` and checks a `localStorage` flag (`utils/tutorial.js`: `hasSeenTutorial(userId)`). If unseen, it auto-activates the tour. Because `Layout` only mounts once per authenticated session start (the `/auth` route sits outside `Layout`), the first `Layout` mount after a fresh login is effectively "on sign in," with no special signal needed from `Auth.jsx`.

The flag is keyed by `user_id` (not global) so multiple accounts sharing a browser each get their own tour once.

### Component tree

```
Layout.jsx
  TutorialProvider              (context: { replay() }, owns step/active state)
    Sidebar / TopBar / Outlet   (real app, untouched except data-tour attrs)
    TutorialOverlay             (renders only when active; portals nothing — absolute-positioned within the shell)
```

`TutorialOverlay` needs a bounding box to compute target positions against. It measures `document.querySelector('.admin-shell')` (the outer div in `Layout.jsx`) via `getBoundingClientRect()`, mirroring the prototype's `containerRef` pattern exactly — just swapping the prototype's fake "app frame" div for the real shell root.

### Step data — `components/tutorial/tutorialSteps.js`

Pure data, no logic. Ported directly from the prototype's `steps()` method, three arrays keyed by role. Each step: `{ badge, title, body, target?, place?, cta? }`. `target` matches a `data-tour` attribute value in the real DOM; steps without `target` (welcome/finish) render centered.

**Student** (7 steps — added Assignments per user decision):
1. Welcome (centered)
2. `nav-sections` — "Join your classes"
3. `nav-assignments` — *(new)* "Stay on top of your work" — "Every assignment you owe lands here, with its due date front and center. Submit before the clock runs out to keep your grade — and your points — safe."
4. `nav-quests` — "Take on quests"
5. `nav-bulletin` — "Ask for help, anonymously"
6. `nav-rooms` — "Team up in study rooms"
7. `topbar-points` — "Watch your points climb"
8. Finish (centered, CTA: "Browse sections")

**Teacher** (5 steps, unchanged from prototype):
1. Welcome → `nav-sections` ("Create your sections") → `nav-quests` ("Assign quests") → `widget-teacher` ("Spot what needs attention") → Finish (CTA: "Browse sections")

**Admin** (6 steps, unchanged from prototype):
1. Welcome → `nav-overview` → `nav-inbox` ("Approve new accounts") → `nav-sections` ("Manage every section") → `nav-users` ("The user directory") → Finish (CTA: "Browse sections")

### Positioning/geometry — ported from prototype

The prototype's `measure()`/`geometry()` methods (in the `.dc.html`'s `Component` class) port over essentially unchanged into `TutorialOverlay.jsx`, adapted from class-component state to hooks:

- `measure()` — on step change and window resize, finds the current step's `data-tour` target via `querySelector`, computes its rect relative to the shell container.
- `geometry()` — computes: the circle (ellipse) around the target, the SVG arrow path from card to circle (quadratic bezier with a bow), and **collision-aware card placement** — candidate positions are tried in order and the first one that doesn't overlap the highlighted target (plus margin) and stays in-bounds wins. Steps without a target center the card.

This is the most intricate piece of ported logic — it's copied faithfully rather than reimplemented, since it already handles the hard edge cases (target near a screen edge, target very large/small, no target at all).

### Data-tour attribute placement (real DOM changes)

- `Sidebar.jsx`: `APP_NAV_ITEMS` and `ADMIN_NAV_GROUPS` entries each get a new `tour` key (e.g. `{ label: 'My sections', to: '/sections', tour: 'nav-sections' }`), spread onto the `NavLink` as `data-tour={item.tour}`.
- `TopBar.jsx`: the points `<span className="admin-topbar-points">` gets `data-tour="topbar-points"`.
- `TeacherDashboard.jsx`: only the *first* card in `visibleOwnedSections.map(...)` gets `data-tour="widget-teacher"` (`i === 0`).

If a target element doesn't exist (e.g. a teacher with zero sections when the tour reaches `widget-teacher`), `geometry()` falls back to a centered card with no arrow — same graceful behavior as the prototype.

### Visual direction — Quest Map

- Purple radial-gradient wash over the whole shell (not a hard black scrim) — `background: radial-gradient(120% 120% at 30% 30%, rgba(170,59,255,0.06), rgba(170,59,255,0.16))`
- Card: white, 2px solid `var(--accent)` border, purple-tinted shadow, pill-shaped buttons
- Small floating emoji icon (✋) with a gentle bob animation
- Gradient progress bar (not dots) + "Quest X of Y" label above the title
- Circle+arrow SVG in `var(--accent)` pointing from the card to the live target
- All colors pulled from existing CSS variables (`--accent`, `--text-h`, `--text-muted`, etc.) already defined in `index.css` — no new tokens needed; the prototype's hardcoded hex values matched these exactly, confirming it was designed against the real palette.

### Replay flow

`Profile.jsx` gets a "↻ Replay tutorial" button (styled like the prototype's, using `--accent`) that calls `replay()` from `useTutorial()` (the context hook). This resets step to 0 and sets active to true — same state the auto-show path uses, just triggered manually.

## Data flow

No backend calls. All state is client-side: `localStorage` for the seen-flag, React context for the active/step state, live DOM queries (`data-tour`) for positioning. `getUserId()`/`getRole()` (existing `utils/auth.js`) drive which step array loads.

## Error handling / edge cases

- **Target missing from DOM** (e.g. sidebar hidden, zero sections for a teacher): falls back to centered card, no arrow — ported directly from the prototype, not new logic.
- **Window resize mid-tour**: `measure()` re-runs on `resize`, same as the prototype.
- **Sidebar toggled hidden while tour is active**: not explicitly handled by the prototype either; if this causes a visibly broken state in manual testing, the simplest fix is disabling the sidebar-hide toggle while the tour is active — decided during implementation if it comes up.
- **User navigates away mid-tour** (e.g. clicks a real sidebar link while the tour is active): the tour's card is `position: absolute` within the shell, not fixed to a specific page, so it will just re-measure against whatever's on the new page. If the new page's target genuinely isn't part of the current step, this reduces to the "target missing" case above.

## Testing / verification

No frontend automated test suite exists in this repo. Verification is manual, in-browser, across all three roles:
1. Fresh login as a student/teacher/admin test account (or clear the localStorage flag) → tour auto-shows.
2. Step through every step for each role, confirming the circle+arrow lands on the correct real element.
3. Resize the window mid-tour, confirm card repositions without overlapping the target.
4. Click "Skip" partway through, confirm it closes and doesn't reappear on next page load.
5. Complete the tour, click "Browse sections", confirm navigation to `/sections`.
6. From Profile, click "↻ Replay tutorial", confirm it restarts from step 0.
