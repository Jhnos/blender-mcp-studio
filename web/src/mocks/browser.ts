import { setupWorker } from 'msw/browser'
import { handlers, wsHandlers } from './handlers'

export const worker = setupWorker(...handlers, ...wsHandlers)

// Start the dummy backend. Base is "/blender", so the worker script (in public/)
// is served under that sub-path. DEV-only; enabled via ?mock in the URL.
export async function enableMocks(): Promise<void> {
  await worker.start({
    serviceWorker: { url: '/blender/mockServiceWorker.js' },
    onUnhandledRequest: 'bypass',
  })
}
