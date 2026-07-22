import { keys } from '../queries'

// Maps a backend data_event ({entity, action, school_id, section_id, ids,
// user_ids}) to the query keys it can affect. Deliberately invalidates
// (refetch-on-next-use) rather than writing cache directly — the payload
// doesn't carry the full row, and invalidation is enough to kill staleness
// within a render.
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
      queryClient.invalidateQueries({ queryKey: ['quests'] })
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
      // Grading/finalizing a submission changes the student's overall
      // grades view (AdminStudentDetail) — without this it went stale for
      // up to the 7-min poll fallback, since none of the keys above cover it.
      if (ids.user_id) queryClient.invalidateQueries({ queryKey: keys.userGrades(ids.user_id) })
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
}
