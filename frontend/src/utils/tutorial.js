const STORAGE_KEY_PREFIX = 'sh-tutorial-seen-'

export function hasSeenTutorial(userId) {
  return localStorage.getItem(STORAGE_KEY_PREFIX + userId) === '1'
}

export function markTutorialSeen(userId) {
  localStorage.setItem(STORAGE_KEY_PREFIX + userId, '1')
}
