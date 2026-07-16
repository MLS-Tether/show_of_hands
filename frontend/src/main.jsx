import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import './index.css'
import App from './App.jsx'
import { DialogProvider } from './components/DialogProvider.jsx'
import { ToastProvider } from './components/ToastProvider.jsx'
import { applyStoredTheme } from './utils/theme.js'

applyStoredTheme()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <DialogProvider>
        <ToastProvider>
          <App />
        </ToastProvider>
      </DialogProvider>
    </BrowserRouter>
  </StrictMode>,
)
