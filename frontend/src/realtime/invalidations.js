import { keys } from '../queries'
import { broadcastRefresh } from '../utils/autoRefresh'

// Maps a backend data_event ({entity, action, school_id, section_id, ids,
// user_ids}) to the query keys it can affect. Deliberately invalidates
// (refetch-on-next-use) rather than writing cache directly — the payload
// doesn't carry the full row, and invalidation is enough to kill staleness
// within a render.
//
// Also calls the legacy broadcastRefresh() bridge so pages not yet migrated
// to react-query (see migration commits 3-9) still refresh instantly. Once
// every page is converted, this bridge call and autoRefresh.js are deleted.
export function invalidateForEvent(queryClient, event) {
  const { entity, section_id: sectionId, ids = {} } = event

  switch (entity) {
    case 'sections':
      queryClient.invalidateQueries({ queryKey: ['sections'] })
      if (sectionId) queryClient.invalidateQueries({ queryKey: keys.section(sectionId) })
      break
    case 'quests':
      if (sectionId) {
        queryClient.invalidateQueries({ queryKey: keys.sectionQuests(sectionId) })
        queryClient.invalidateQueries({ queryKey: keys.section(sectionId) })
      }
      break
    case 'assignments':
      queryClient.invalidateQueries({ queryKey: keys.assignments() })
      if (ids.assignment_id) queryClient.invalidateQueries({ queryKey: keys.assignment(ids.assignment_id) })
      if (sectionId) {
        queryClient.invalidateQueries({ queryKey: keys.section(sectionId) })
        queryClient.invalidateQueries({ queryKey: keys.sectionAnalytics(sectionId) })
      }
      break
    case 'submissions':
      if (ids.assignment_id) {
        queryClient.invalidateQueries({ queryKey: keys.assignment(ids.assignment_id) })
        queryClient.invalidateQueries({ queryKey: keys.assignmentSubmissions(ids.assignment_id) })
        queryClient.invalidateQueries({ queryKey: keys.assignmentMySubmission(ids.assignment_id) })
      }
      if (sectionId) {
        queryClient.invalidateQueries({ queryKey: keys.sectionAnalytics(sectionId) })
        queryClient.invalidateQueries({ queryKey: ['section', sectionId, 'grades'] })
      }
      break
    case 'resources':
      if (sectionId) queryClient.invalidateQueries({ queryKey: keys.sectionResources(sectionId) })
      break
    case 'help_requests':
      queryClient.invalidateQueries({ queryKey: keys.helpRequests() })
      if (sectionId) queryClient.invalidateQueries({ queryKey: keys.sectionHelpRequests(sectionId) })
      break
    case 'enrollment_requests':
      if (sectionId) {
        queryClient.invalidateQueries({ queryKey: keys.sectionEnrollmentRequests(sectionId) })
      }
      queryClient.invalidateQueries({ queryKey: ['sections'] })
      break
    case 'points':
      queryClient.invalidateQueries({ queryKey: ['points'] })
      queryClient.invalidateQueries({ queryKey: keys.schoolPoints() })
      break
    case 'users':
      queryClient.invalidateQueries({ queryKey: ['users'] })
      if (ids.user_id) queryClient.invalidateQueries({ queryKey: ['user', ids.user_id] })
      break
    case 'class_requests':
      queryClient.invalidateQueries({ queryKey: keys.classRequests() })
      break
    case 'school':
      queryClient.invalidateQueries({ queryKey: ['school'] })
      break
    case 'rooms':
      if (ids.room_id) queryClient.invalidateQueries({ queryKey: keys.room(ids.room_id) })
      queryClient.invalidateQueries({ queryKey: keys.helpRequests() })
      break
    default:
      break
  }

  broadcastRefresh()
}
