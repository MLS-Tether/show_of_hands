const ROOMS_KEY = 'my_study_rooms'
const HELP_REQUEST_IDS_KEY = 'my_help_request_ids'

export function getMyRooms() {
  try {
    return JSON.parse(localStorage.getItem(ROOMS_KEY)) || []
  } catch {
    return []
  }
}

export function rememberRoom({ room_id, topic }) {
  const rooms = getMyRooms()
  const existing = rooms.find((r) => r.room_id === room_id)
  const merged = { room_id, topic: topic || existing?.topic || null }
  const rest = rooms.filter((r) => r.room_id !== room_id)
  localStorage.setItem(ROOMS_KEY, JSON.stringify([merged, ...rest].slice(0, 20)))
}

export function forgetRoom(roomId) {
  const rooms = getMyRooms().filter((r) => r.room_id !== roomId)
  localStorage.setItem(ROOMS_KEY, JSON.stringify(rooms))
}

export function getMyHelpRequestIds() {
  try {
    return JSON.parse(localStorage.getItem(HELP_REQUEST_IDS_KEY)) || []
  } catch {
    return []
  }
}

export function rememberHelpRequestId(helpRequestId) {
  const ids = getMyHelpRequestIds()
  if (ids.includes(helpRequestId)) return
  localStorage.setItem(HELP_REQUEST_IDS_KEY, JSON.stringify([helpRequestId, ...ids].slice(0, 50)))
}
