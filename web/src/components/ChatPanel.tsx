import { useState, useRef, useEffect, useCallback, type FormEvent } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useWebSocket } from '../hooks/useWebSocket'

const _base = import.meta.env.BASE_URL.replace(/\/$/, '')
const API_BASE = `${location.origin}${_base}`

function useUndoRedo() {
  const [lastAction, setLastAction] = useState<string | null>(null)

  const runAction = useCallback(async (action: 'undo' | 'redo') => {
    try {
      const res = await fetch(`${API_BASE}/api/${action}`, { method: 'POST' })
      const data = await res.json() as { success: boolean; message: string }
      setLastAction(`${action === 'undo' ? '↩ 復原' : '↪ 重做'}: ${data.success ? '✅' : '❌'} ${data.message}`)
      setTimeout(() => setLastAction(null), 2000)
    } catch {
      setLastAction(`${action} 失敗`)
    }
  }, [])

  // Keyboard: Cmd+Z = undo, Cmd+Shift+Z = redo
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'z') {
        e.preventDefault()
        if (e.shiftKey) void runAction('redo')
        else void runAction('undo')
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [runAction])

  return { lastAction, runAction }
}

function ExportMenu() {
  const [open, setOpen] = useState(false)
  const [exporting, setExporting] = useState(false)

  const exportScene = async (format: 'stl' | 'obj' | 'fbx' | 'glb') => {
    setOpen(false)
    setExporting(true)
    try {
      const res = await fetch(`${API_BASE}/api/export`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format, selection_only: false }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText })) as { detail: string }
        alert(`匯出失敗: ${err.detail}`)
        return
      }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `blender_scene.${format}`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) {
      alert(`匯出失敗: ${String(e)}`)
    } finally {
      setExporting(false)
    }
  }

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={exporting}
        className="text-xs px-3 py-1.5 rounded-lg bg-slate-700 hover:bg-slate-600
                   text-slate-300 transition-colors disabled:opacity-50"
        title="匯出場景"
      >
        {exporting ? '匯出中...' : '⬇ 匯出'}
      </button>
      {open && (
        <div className="absolute bottom-full left-0 mb-1 bg-slate-800 border border-slate-600
                        rounded-lg shadow-xl z-50 py-1 min-w-[100px]">
          {(['stl', 'obj', 'fbx', 'glb'] as const).map((fmt) => (
            <button
              key={fmt}
              onClick={() => void exportScene(fmt)}
              className="w-full text-left px-3 py-1.5 text-xs text-slate-300
                         hover:bg-slate-700 transition-colors uppercase font-mono"
            >
              {fmt === 'stl' ? '🖨 STL (3D列印)' : fmt === 'obj' ? '◼ OBJ' : fmt === 'fbx' ? '🎮 FBX' : '🌐 GLB'}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

export function ChatPanel() {
  const { messages, isConnected, isLoading, addUserMessage, setLoading } = useChatStore()
  const { sendMessage } = useWebSocket()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const { lastAction, runAction } = useUndoRedo()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const text = input.trim()
    if (!text || !isConnected || isLoading) return
    addUserMessage(text)
    setLoading(true)
    sendMessage(text)
    setInput('')
  }

  return (
    <div className="flex flex-col flex-1 overflow-hidden">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.length === 0 && (
          <p className="text-center text-slate-500 mt-16">
            👋 輸入文字描述，讓 AI 幫你在 Blender 中建模
          </p>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap ${
                msg.role === 'user'
                  ? 'bg-violet-600 text-white'
                  : msg.status === 'error'
                    ? 'bg-red-900/50 text-red-300 border border-red-700'
                    : 'bg-slate-800 text-slate-200'
              }`}
            >
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-slate-800 rounded-2xl px-4 py-2 text-slate-400 text-sm animate-pulse">
              思考中...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Undo/Redo toast */}
      {lastAction && (
        <div className="mx-4 mb-1 text-xs text-center text-slate-400 bg-slate-800/80 rounded px-2 py-1">
          {lastAction}
        </div>
      )}

      {/* Input + toolbar */}
      <div className="p-3 border-t border-slate-700">
        {/* Toolbar: undo/redo + export */}
        <div className="flex gap-1.5 mb-2">
          <button
            onClick={() => void runAction('undo')}
            className="text-xs px-2.5 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-400 transition-colors"
            title="復原 (⌘Z)"
          >
            ↩
          </button>
          <button
            onClick={() => void runAction('redo')}
            className="text-xs px-2.5 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-400 transition-colors"
            title="重做 (⌘⇧Z)"
          >
            ↪
          </button>
          <div className="flex-1" />
          <ExportMenu />
        </div>

        <form onSubmit={handleSubmit} className="flex gap-2">
          <input
            className="flex-1 bg-slate-800 text-slate-200 rounded-xl px-4 py-2 text-sm outline-none focus:ring-2 focus:ring-violet-500 placeholder:text-slate-500"
            placeholder={isConnected ? '描述你想建立的 3D 物件...' : '連線中...'}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!isConnected}
          />
          <button
            type="submit"
            disabled={!isConnected || isLoading || !input.trim()}
            className="bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-white rounded-xl px-4 py-2 text-sm font-medium transition-colors"
          >
            送出
          </button>
        </form>
      </div>
    </div>
  )
}
