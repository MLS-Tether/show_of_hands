export function formatPercent(value, digits = 1) {
  if (value == null) return null
  return `${value.toFixed(digits)}%`
}
