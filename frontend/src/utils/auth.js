export function getRole() {
  return localStorage.getItem('role')
}

export function isTeacher() {
  return getRole() === 'teacher'
}
