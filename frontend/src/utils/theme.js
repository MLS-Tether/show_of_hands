const STORAGE_KEY = 'sh-theme'

export function getTheme() {
  return localStorage.getItem(STORAGE_KEY) || 'light'
}

export function setTheme(theme) {
  localStorage.setItem(STORAGE_KEY, theme)
  document.documentElement.setAttribute('data-theme', theme)
}

export function applyStoredTheme() {
  document.documentElement.setAttribute('data-theme', getTheme())
}
