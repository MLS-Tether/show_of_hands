import { apiClient } from '../lib/apiClient'

export function getUserPoints(userId) {
  return apiClient.get(`/users/${userId}/points`).then((res) => res.data)
}
