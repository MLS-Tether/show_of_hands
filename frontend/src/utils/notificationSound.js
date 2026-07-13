let sharedContext = null

function getContext() {
  if (!sharedContext) {
    const AudioContextClass = window.AudioContext || window.webkitAudioContext
    if (!AudioContextClass) return null
    sharedContext = new AudioContextClass()
  }
  return sharedContext
}

// Small two-note chime synthesized with the Web Audio API — no audio asset
// to bundle or fetch. Browsers block audio before any user gesture on the
// page, so a failure here is silently swallowed (the toast still shows).
export function playNotificationChime() {
  try {
    const ctx = getContext()
    if (!ctx) return
    if (ctx.state === 'suspended') ctx.resume()

    const now = ctx.currentTime
    ;[[880, now, 0.12], [1174.66, now + 0.1, 0.15]].forEach(([freq, start, duration]) => {
      const oscillator = ctx.createOscillator()
      const gain = ctx.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.value = freq
      gain.gain.setValueAtTime(0.0001, start)
      gain.gain.exponentialRampToValueAtTime(0.2, start + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, start + duration)
      oscillator.connect(gain)
      gain.connect(ctx.destination)
      oscillator.start(start)
      oscillator.stop(start + duration + 0.02)
    })
  } catch {
    // best-effort; sound is a nice-to-have, never block on it
  }
}
