import { useState, useRef, useEffect, type FormEvent } from 'react'
import { useChatStore } from '../stores/chatStore'
import { useWebSocket } from '../hooks/useWebSocket'
import { ImageUploadButton } from './ImageUploadButton'
import { RefineOverlay } from './RefineOverlay'
import { Button, Icon } from './ui'

// Example prompts reduce the "blank canvas" freeze and show what the tool can
// do (research: users prefer suggestions on how to begin).
const EXAMPLE_PROMPTS = [
  '做一個木頭桌子',
  '加一盞暖色的燈',
  '建立一個藍色的球體',
  '在場景中央放一個立方體',
]

// ---------------------------------------------------------------------------
// ChatRail — the conversation (primary input). Chat stays present but the
// preview is the focal point (research: chat present-but-secondary).
// ---------------------------------------------------------------------------

export function ChatRail() {
  const { messages, isConnected, isLoading, addUserMessage, setLoading } = useChatStore()
  const { sendMessage } = useWebSocket()
  const [input, setInput] = useState('')
  const [refineOpen, setRefineOpen] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages])

  const send = (text: string) => {
    const t = text.trim()
    if (!t || !isConnected || isLoading) return
    addUserMessage(t)
    setLoading(true)
    sendMessage(t)
    setInput('')
  }
  const onSubmit = (e: FormEvent) => { e.preventDefault(); send(input) }

  return (
    <div className="flex w-[360px] shrink-0 flex-col border-r border-border bg-surface-raised">
      {/* Messages */}
      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.length === 0 ? (
          <div className="mt-10 flex flex-col items-center gap-4 text-center">
            <Icon name="ai" size={30} className="text-accent" />
            <p className="text-sm text-fg-muted">用文字描述，讓 AI 幫你在 Blender 中建模</p>
            <div className="flex flex-wrap justify-center gap-1.5">
              {EXAMPLE_PROMPTS.map((p) => (
                <button
                  key={p}
                  onClick={() => send(p)}
                  disabled={!isConnected}
                  className="rounded-full border border-border bg-surface-overlay px-3 py-1 text-xs
                             text-fg-muted hover:border-accent hover:text-fg transition-colors
                             disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, i) => (
            <div key={i} className={`flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
              {/* AI content is labelled, not indistinguishable from user input (trust). */}
              {msg.role === 'assistant' && msg.status !== 'error' && (
                <span className="mb-0.5 ml-1 inline-flex items-center gap-1 text-[10px] text-fg-subtle">
                  <Icon name="ai" size={10} className="text-accent" /> AI
                </span>
              )}
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-3.5 py-2 text-sm ${
                  msg.role === 'user'
                    ? 'bg-accent text-accent-fg'
                    : msg.status === 'error'
                      ? 'border border-danger/40 bg-danger-bg text-danger'
                      : 'bg-surface-overlay text-fg'
                }`}
              >
                {msg.content}
                {msg.status === 'streaming' && (
                  <span className="ml-0.5 inline-block h-3.5 w-0.5 align-middle bg-accent animate-[blink_0.8s_step-start_infinite]" />
                )}
              </div>
              {/* Shows the AI changed the scene, and that it's reversible (⌘Z). */}
              {msg.executed && (
                <span className="ml-1 mt-0.5 inline-flex items-center gap-1 text-[10px] text-success">
                  <Icon name="apply" size={10} /> 已套用到場景 · 可復原 (⌘Z)
                </span>
              )}
            </div>
          ))
        )}
        {isLoading && messages[messages.length - 1]?.status !== 'streaming' && (
          <div className="flex justify-start">
            <div className="animate-pulse rounded-2xl bg-surface-overlay px-3.5 py-2 text-sm text-fg-muted">
              思考中...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input + toolbar */}
      <div className="border-t border-border p-3">
        <div className="mb-2 flex items-center gap-1.5">
          <ImageUploadButton
            disabled={!isConnected}
            onDescription={(desc) => setInput((prev) => (prev ? `${desc}\n\n${prev}` : desc))}
          />
          <Button
            variant="subtle" icon="ai" onClick={() => setRefineOpen(true)} disabled={!isConnected}
            title="讓 Vision AI 反覆比對並自動修正場景"
          >
            自動精煉
          </Button>
          <div className="flex-1" />
        </div>
        <form onSubmit={onSubmit} className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={!isConnected}
            placeholder={isConnected ? '描述你想建立的 3D 物件...' : '連線中...'}
            className="flex-1 rounded-xl bg-surface-sunken px-4 py-2 text-sm text-fg
                       placeholder:text-fg-subtle focus:outline-none focus:ring-2 focus:ring-accent"
          />
          <Button variant="primary" size="md" type="submit" disabled={!isConnected || isLoading || !input.trim()}>
            <Icon name="send" size={16} />
          </Button>
        </form>
      </div>

      <RefineOverlay open={refineOpen} onClose={() => setRefineOpen(false)} />
    </div>
  )
}
