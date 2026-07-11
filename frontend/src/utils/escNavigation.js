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
]

export function getParentPath(pathname) {
  const match = ROUTE_PARENTS.find((r) => r.pattern.test(pathname))
  return match ? match.parent : null
}
