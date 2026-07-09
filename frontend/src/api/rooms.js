import { apiClient } from '../lib/apiClient'

export function getRoom(roomId) {
  return apiClient.get(`/rooms/${roomId}`).then((res) => res.data)
}

export function extendRoom(roomId) {
  return apiClient.post(`/rooms/${roomId}/extend`).then((res) => res.data)
}

export function closeRoom(roomId) {
  return apiClient.post(`/rooms/${roomId}/close`).then((res) => res.data)
}

export function kickMember(roomId, userId) {
  return apiClient.post(`/rooms/${roomId}/kick`, { user_id: userId }).then((res) => res.data)
}
