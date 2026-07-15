import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// T3 dummy run: `?mock` starts the MSW dummy backend (real frontend + engine,
// dummy inputs). DEV-only; never bundled into production behaviour.
async function bootstrap() {
  if (import.meta.env.DEV && new URLSearchParams(location.search).has('mock')) {
    const { enableMocks } = await import('./mocks/browser')
    await enableMocks()
  }
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )
}

void bootstrap()
