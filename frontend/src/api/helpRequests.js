import { apiClient } from '../lib/apiClient'

export function listHelpRequests(sectionId) {
  return apiClient.get(`/sections/${sectionId}/help-requests`).then((res) => res.data)
}

export function createHelpRequest(sectionId, { topic, description, groupSize, durationMinutes }) {
  return apiClient
    .post(`/sections/${sectionId}/help-requests`, {
      topic,
      description: description || undefined,
      group_size: groupSize,
      duration_minutes: durationMinutes,
    })
    .then((res) => res.data)
}

export function acceptHelpRequest(helpRequestId) {
  return apiClient.post(`/help-requests/${helpRequestId}/accept`).then((res) => res.data)
}

export function dropHelpRequest(helpRequestId) {
  return apiClient.post(`/help-requests/${helpRequestId}/drop`).then((res) => res.data)
}

export function confirmHelpRequest(helpRequestId, sessionOccurred) {
  return apiClient
    .post(`/help-requests/${helpRequestId}/confirm`, { session_occurred: sessionOccurred })
    .then((res) => res.data)
}
