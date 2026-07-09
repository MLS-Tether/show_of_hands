import { apiClient } from '../lib/apiClient'

export function listSections() {
  return apiClient.get('/sections').then((res) => res.data)
}

export function getSection(sectionId) {
  return apiClient.get(`/sections/${sectionId}`).then((res) => res.data)
}
