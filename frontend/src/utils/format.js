export function formatPercent(value, digits = 1) {
  if (value == null) return null
  return `${value.toFixed(digits)}%`
}

export function initials(name) {
  if (!name) return '?'
  return name.slice(0, 2).toUpperCase()
}
