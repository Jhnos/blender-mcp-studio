import { useChatStore } from './stores/chatStore'
import { ChatPanel } from './components/ChatPanel'
import { SceneView } from './components/SceneView'
import './index.css'

function App() {
  const isConnected = useChatStore((s) => s.isConnected)

  return (
    <div className="flex flex-col h-full bg-slate-950 text-slate-200">
      {/* Header */}
      <header className="flex items-center justify-between px-5 py-3 border-b border-slate-800 bg-slate-900">
        <div className="flex items-center gap-2">
          <span className="text-lg font-semibold tracking-tight">🎨 Blender MCP Studio</span>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span
            className={`w-2 h-2 rounded-full ${isConnected ? 'bg-green-500' : 'bg-red-500'}`}
          />
          <span className="text-slate-400">{isConnected ? 'Backend 連線中' : '等待連線...'}</span>
        </div>
      </header>

      {/* Main: Chat (left, flex-1) + Output (right, fixed w-80) */}
      <div className="flex flex-1 overflow-hidden min-h-0">
        <ChatPanel />
        <SceneView />
      </div>
    </div>
  )
}

export default App

