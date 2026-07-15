// Maps a route to the page Escape should go back to. Ordered most-specific
// first since the first matching pattern wins. Routes with no match (e.g.
// /dashboard itself) mean Escape does nothing there.
const ROUTE_PARENTS = [
  { pattern: /^\/assignments\/[^/]+$/, parent: '/assignments' },
  { pattern: /^\/assignments$/, parent: '/dashboard' },
  { pattern: /^\/sections\/[^/]+$/, parent: '/sections' },
  { pattern: /^\/sections$/, parent: '/dashboard' },
  { pattern: /^\/rooms\/[^/]+$/, parent: '/study-rooms' },
  { pattern: /^\/study-rooms$/, parent: '/dashboard' },
  { pattern: /^\/bulletin-board$/, parent: '/dashboard' },
  { pattern: /^\/quests$/, parent: '/dashboard' },
  { pattern: /^\/points$/, parent: '/dashboard' },
  { pattern: /^\/profile$/, parent: '/dashboard' },
]

// Teachers don't have a student-facing /assignments list to land on (it's
// 403-gated for them) and there's no section id in this URL to route to
// directly, so send them back through history instead of to a fixed parent.
const TEACHER_ROUTE_OVERRIDES = [{ pattern: /^\/assignments\/[^/]+$/, parent: 'BACK' }]

export function getParentPath(pathname, { isTeacher = false } = {}) {
  if (isTeacher) {
    const override = TEACHER_ROUTE_OVERRIDES.find((r) => r.pattern.test(pathname))
    if (override) return override.parent
  }
  const match = ROUTE_PARENTS.find((r) => r.pattern.test(pathname))
  return match ? match.parent : null
}
