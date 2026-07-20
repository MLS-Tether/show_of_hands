import { createContext, useContext } from 'react'

export const RealtimeContext = createContext({ toasts: [], dismissToast: () => {} })

export function useRealtimeToasts() {
  return useContext(RealtimeContext)
}
