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

  addAssistantMessage: (content, status, blenderOut, screenshot) =>
    set((s) => {
      const logs = blenderOut != null
        ? [...s.blenderLogs, {
            timestamp: new Date().toLocaleTimeString('zh-TW'),
            output: blenderOut,
            isError: blenderOut.startsWith('❌'),
          }]
        : s.blenderLogs
      return {
        messages: [...s.messages, { role: 'assistant', content, status }],
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
