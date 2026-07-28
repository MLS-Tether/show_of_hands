import { createContext, useContext } from 'react'

export const SidebarPeekContext = createContext(null)

export function useSidebarPeek() {
  const ctx = useContext(SidebarPeekContext)
  if (!ctx) throw new Error('useSidebarPeek must be used within Layout')
  return ctx
}
