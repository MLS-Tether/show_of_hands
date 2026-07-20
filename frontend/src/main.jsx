import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.jsx'
import { DialogProvider } from './components/DialogProvider.jsx'
import { ToastProvider } from './components/ToastProvider.jsx'
import { queryClient } from './queryClient.js'
import { applyStoredTheme } from './utils/theme.js'

applyStoredTheme()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <DialogProvider>
          <ToastProvider>
            <App />
          </ToastProvider>
        </DialogProvider>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
)
