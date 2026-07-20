import { QueryClient } from '@tanstack/react-query'

// Push (RealtimeProvider) keeps data fresh event-by-event, so this interval
// is just a rare safety net for missed events — same role autoRefresh's
// interval used to play. Keep it long.
const FALLBACK_POLL_INTERVAL_MS = 7 * 60 * 1000

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 90 * 1000,
      gcTime: 15 * 60 * 1000,
      refetchOnWindowFocus: true,
      refetchInterval: FALLBACK_POLL_INTERVAL_MS,
      refetchIntervalInBackground: false,
      retry: 1,
    },
  },
})
