// Student help-request responses omit requester identity (by design, for anonymity),
// so the only way to know "this one is mine" is to remember it ourselves after creating it.
const STORAGE_KEY = 'sof_my_help_requests'

function readAll() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {}
  } catch {
    return {}
  }
}

export function markMine(helpRequestId) {
  const all = readAll()
  all[helpRequestId] = true
  localStorage.setItem(STORAGE_KEY, JSON.stringify(all))
}

export function isMine(helpRequestId) {
  return Boolean(readAll()[helpRequestId])
}
