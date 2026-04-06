import { create } from 'zustand'

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  status?: 'done' | 'error' | 'streaming'
}

export interface BlenderLog {
  timestamp: string
  output: string
  isError: boolean
}

interface ChatStore {
  messages: ChatMessage[]
  sessionId: string | null
  isConnected: boolean
  isLoading: boolean
  blenderLogs: BlenderLog[]
  sceneRefreshTick: number
  liveScreenshot: string | null  // base64 PNG from last Blender command
  addUserMessage: (content: string) => void
  addAssistantMessage: (
    content: string,
    status: ChatMessage['status'],
    blenderOut?: string | null,
    screenshot?: string | null,
  ) => void
  appendStreamToken: (token: string, sessionId?: string) => void
  setConnected: (v: boolean) => void
  setLoading: (v: boolean) => void
  setSessionId: (id: string) => void
  triggerSceneRefresh: () => void
  setLiveScreenshot: (b64: string | null) => void
}

export const useChatStore = create<ChatStore>((set) => ({
  messages: [],
  sessionId: null,
  isConnected: false,
  isLoading: false,
  blenderLogs: [],
  sceneRefreshTick: 0,
  liveScreenshot: null,

  addUserMessage: (content) =>
    set((s) => ({ messages: [...s.messages, { role: 'user', content }] })),

  // Called when status === 'streaming': append token to last assistant message,
  // or create a new streaming message if last message is from user.
  appendStreamToken: (token) =>
    set((s) => {
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      if (last?.role === 'assistant' && last.status === 'streaming') {
        msgs[msgs.length - 1] = { ...last, content: last.content + token }
      } else {
        msgs.push({ role: 'assistant', content: token, status: 'streaming' })
      }
      return { messages: msgs, isLoading: false }
    }),

  addAssistantMessage: (content, status, blenderOut, screenshot) =>
    set((s) => {
      // Replace the last streaming message (if any) with the final content
      const msgs = [...s.messages]
      const last = msgs[msgs.length - 1]
      const isReplacingStream = last?.role === 'assistant' && last.status === 'streaming'
      const newMessage: ChatMessage = { role: 'assistant', content, status }
      const nextMsgs = isReplacingStream
        ? [...msgs.slice(0, -1), newMessage]
        : [...msgs, newMessage]

      const logs = blenderOut != null
        ? [...s.blenderLogs, {
            timestamp: new Date().toLocaleTimeString('zh-TW'),
            output: blenderOut,
            isError: blenderOut.startsWith('❌'),
          }]
        : s.blenderLogs
      return {
        messages: nextMsgs,
        isLoading: false,
        blenderLogs: logs,
        sceneRefreshTick: blenderOut != null ? s.sceneRefreshTick + 1 : s.sceneRefreshTick,
        liveScreenshot: screenshot !== undefined ? screenshot : s.liveScreenshot,
      }
    }),

  setConnected: (isConnected) => set({ isConnected }),
  setLoading: (isLoading) => set({ isLoading }),
  setSessionId: (sessionId) => set({ sessionId }),
  triggerSceneRefresh: () => set((s) => ({ sceneRefreshTick: s.sceneRefreshTick + 1 })),
  setLiveScreenshot: (liveScreenshot) => set({ liveScreenshot }),
}))

