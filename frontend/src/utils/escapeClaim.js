let claimed = false

export function claimEscape() {
  claimed = true
}

export function releaseEscape() {
  claimed = false
}

export function isEscapeClaimed() {
  return claimed
}
