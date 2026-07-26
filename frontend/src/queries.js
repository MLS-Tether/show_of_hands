import { useMemo } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import api from './api'
import { rememberHelpRequestId } from './utils/roomTracking'

// Single source of truth for query keys, shared between the components that
// read data and realtime/invalidations.js, which maps push events to these
// same keys. Keeping them in one place means a key typo shows up as a stale
// cache instead of a silent invalidation miss.
export const keys = {
  sections: (scope = 'mine') => ['sections', scope],
  section: (sectionId) => ['section', sectionId],
  sectionQuests: (sectionId) => ['section', sectionId, 'quests'],
  quests: (sectionIds) => ['quests', [...sectionIds].sort((a, b) => a - b)],
  sectionResources: (sectionId) => ['section', sectionId, 'resources'],
  sectionHelpRequests: (sectionId) => ['section', sectionId, 'help-requests'],
  sectionAnalytics: (sectionId) => ['section', sectionId, 'analytics'],
  sectionEnrollmentRequests: (sectionId) => ['section', sectionId, 'enrollment-requests'],
  sectionGrades: (sectionId, who = 'me') => ['section', sectionId, 'grades', who],
  assignments: () => ['assignments'],
  assignment: (assignmentId) => ['assignment', assignmentId],
  assignmentSubmissions: (assignmentId) => ['assignment', assignmentId, 'submissions'],
  assignmentMySubmission: (assignmentId) => ['assignment', assignmentId, 'my-submission'],
  helpRequests: () => ['help-requests'],
  notifications: () => ['notifications'],
  points: (userId, page = 1, pageSize = 20) => ['points', userId, page, pageSize],
  school: () => ['school'],
  schoolCode: () => ['school', 'code'],
  schoolPoints: () => ['school', 'points'],
  users: (filters = {}) => ['users', filters],
  user: (userId) => ['user', userId],
  userGrades: (userId) => ['user', userId, 'grades'],
  classRequests: () => ['class-requests'],
  classes: () => ['classes'],
  room: (roomId) => ['room', roomId],
}

function unwrap(promise) {
  return promise.then((res) => res.data)
}

export function useSections(scope = 'mine', options = {}) {
  return useQuery({
    queryKey: keys.sections(scope),
    queryFn: () =>
      unwrap(scope === 'all' ? api.get('/sections', { params: { scope: 'all' } }) : api.get('/sections')),
    ...options,
  })
}

export function useSection(sectionId, options = {}) {
  return useQuery({
    queryKey: keys.section(sectionId),
    queryFn: () => unwrap(api.get(`/sections/${sectionId}`)),
    enabled: !!sectionId,
    ...options,
  })
}

export function useSectionQuests(sectionId, options = {}) {
  return useQuery({
    queryKey: keys.sectionQuests(sectionId),
    queryFn: () => unwrap(api.get(`/sections/${sectionId}/quests`)),
    enabled: !!sectionId,
    ...options,
  })
}

export function useQuestsForSections(sectionIds, options = {}) {
  const ids = sectionIds ?? []
  return useQuery({
    queryKey: keys.quests(ids),
    queryFn: () => unwrap(api.get('/quests', { params: { section_ids: ids } })),
    enabled: ids.length > 0,
    ...options,
  })
}

export function useSectionResources(sectionId, options = {}) {
  return useQuery({
    queryKey: keys.sectionResources(sectionId),
    queryFn: () => unwrap(api.get(`/sections/${sectionId}/resources`)),
    enabled: !!sectionId,
    ...options,
  })
}

export function useSectionHelpRequests(sectionId, options = {}) {
  return useQuery({
    queryKey: keys.sectionHelpRequests(sectionId),
    queryFn: () => unwrap(api.get(`/sections/${sectionId}/help-requests`)),
    enabled: !!sectionId,
    ...options,
  })
}

export function useSectionAnalytics(sectionId, options = {}) {
  return useQuery({
    queryKey: keys.sectionAnalytics(sectionId),
    queryFn: () => unwrap(api.get(`/sections/${sectionId}/analytics`)),
    enabled: !!sectionId,
    ...options,
  })
}

export function useSectionEnrollmentRequests(sectionId, options = {}) {
  return useQuery({
    queryKey: keys.sectionEnrollmentRequests(sectionId),
    queryFn: () => unwrap(api.get(`/sections/${sectionId}/enrollment-requests`)),
    enabled: !!sectionId,
    ...options,
  })
}

export function useSectionGrades(sectionId, who = 'me', options = {}) {
  return useQuery({
    queryKey: keys.sectionGrades(sectionId, who),
    queryFn: () =>
      unwrap(
        who === 'me'
          ? api.get(`/sections/${sectionId}/grades/me`)
          : api.get(`/sections/${sectionId}/grades/${who}`)
      ),
    enabled: !!sectionId,
    ...options,
  })
}

export function useAssignments(options = {}) {
  return useQuery({
    queryKey: keys.assignments(),
    queryFn: () => unwrap(api.get('/assignments')),
    ...options,
  })
}

export function useAssignment(assignmentId, options = {}) {
  return useQuery({
    queryKey: keys.assignment(assignmentId),
    queryFn: () => unwrap(api.get(`/assignments/${assignmentId}`)),
    enabled: !!assignmentId,
    ...options,
  })
}

export function useAssignmentSubmissions(assignmentId, options = {}) {
  return useQuery({
    queryKey: keys.assignmentSubmissions(assignmentId),
    queryFn: () => unwrap(api.get(`/assignments/${assignmentId}/submissions`)),
    enabled: !!assignmentId,
    ...options,
  })
}

export function useAssignmentMySubmission(assignmentId, options = {}) {
  return useQuery({
    queryKey: keys.assignmentMySubmission(assignmentId),
    queryFn: () => unwrap(api.get(`/assignments/${assignmentId}/my-submission`)),
    enabled: !!assignmentId,
    ...options,
  })
}

export function useHelpRequestsBoard(options = {}) {
  return useQuery({
    queryKey: keys.helpRequests(),
    queryFn: () => unwrap(api.get('/help-requests')),
    ...options,
  })
}

// Shared by the Bulletin board's own create form and the mobile floating
// Ask button, so the post + cache-prepend sequence only lives in one place.
export function useCreateHelpRequest(sections) {
  const queryClient = useQueryClient()

  return async function createHelpRequest({ sectionId, topic, description, groupSize, durationMinutes }) {
    const { data } = await api.post(`/sections/${sectionId}/help-requests`, {
      topic,
      description: description || null,
      group_size: Number(groupSize),
      duration_minutes: Number(durationMinutes),
    })
    rememberHelpRequestId(data.help_request_id)
    const section = (sections ?? []).find((s) => s.section_id === Number(sectionId))
    const hr = { ...data, section_id: Number(sectionId), section_name: section?.class_name }
    queryClient.setQueryData(keys.helpRequests(), (prev) => [hr, ...(prev || [])])
    return hr
  }
}

export function useNotifications(options = {}) {
  return useQuery({
    queryKey: keys.notifications(),
    queryFn: () => unwrap(api.get('/notifications')),
    ...options,
  })
}

// Single source of truth for "how many unread notifications point at this
// card" — every card badge must read from this instead of computing its own
// count, so the bell's unread count and every card badge always agree.
export function useNotificationCountsByEntity() {
  const { data: notifications = null } = useNotifications()
  return useMemo(() => {
    const counts = {}
    ;(notifications || []).forEach((n) => {
      if (n.is_read || n.entity_type == null || n.entity_id == null) return
      const key = `${n.entity_type}:${n.entity_id}`
      counts[key] = (counts[key] || 0) + 1
    })
    return counts
  }, [notifications])
}

export function usePoints(userId, page = 1, pageSize = 20, options = {}) {
  return useQuery({
    queryKey: keys.points(userId, page, pageSize),
    queryFn: () => unwrap(api.get(`/users/${userId}/points`, { params: { page, page_size: pageSize } })),
    enabled: !!userId,
    ...options,
  })
}

export function useSchool(options = {}) {
  return useQuery({
    queryKey: keys.school(),
    queryFn: () => unwrap(api.get('/schools/me')),
    ...options,
  })
}

export function useSchoolCode(options = {}) {
  return useQuery({
    queryKey: keys.schoolCode(),
    queryFn: () => unwrap(api.get('/schools/code')),
    ...options,
  })
}

export function useSchoolPoints(options = {}) {
  return useQuery({
    queryKey: keys.schoolPoints(),
    queryFn: () => unwrap(api.get('/schools/points')),
    ...options,
  })
}

export function useUsers(filters = {}, options = {}) {
  return useQuery({
    queryKey: keys.users(filters),
    queryFn: () => unwrap(api.get('/users', { params: filters })),
    ...options,
  })
}

export function useUser(userId, options = {}) {
  return useQuery({
    queryKey: keys.user(userId),
    queryFn: () => unwrap(api.get(`/users/${userId}`)),
    enabled: !!userId,
    ...options,
  })
}

export function useUserGrades(userId, options = {}) {
  return useQuery({
    queryKey: keys.userGrades(userId),
    queryFn: () => unwrap(api.get(`/users/${userId}/grades`)),
    enabled: !!userId,
    ...options,
  })
}

export function useClassRequests(options = {}) {
  return useQuery({
    queryKey: keys.classRequests(),
    queryFn: () => unwrap(api.get('/class-requests')),
    ...options,
  })
}

export function useClasses(options = {}) {
  return useQuery({
    queryKey: keys.classes(),
    queryFn: () => unwrap(api.get('/classes')),
    staleTime: 60 * 60 * 1000,
    refetchInterval: false,
    ...options,
  })
}

export function useRoom(roomId, options = {}) {
  return useQuery({
    queryKey: keys.room(roomId),
    queryFn: () => unwrap(api.get(`/rooms/${roomId}`)),
    enabled: !!roomId,
    refetchInterval: 20 * 1000,
    ...options,
  })
}
