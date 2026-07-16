export function getRole() {
  return localStorage.getItem('role')
}

export function isTeacher() {
  return getRole() === 'teacher'
}

export function isAdmin() {
  return getRole() === 'admin'
}

export function getUserId() {
  return Number(localStorage.getItem('user_id'))
}
