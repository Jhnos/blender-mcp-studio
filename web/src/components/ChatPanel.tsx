import { useState, useRef, useEffect, type FormEvent } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useWebSocket } from '../hooks/useWebSocket'

export function ChatPanel() {
  const { messages, isConnected, isLoading, addUserMessage, setLoading } = useChatStore()
  const { sendMessage } = useWebSocket()
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)

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

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-slate-700 flex gap-2">
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
  )
}
