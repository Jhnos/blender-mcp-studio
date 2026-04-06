import { useEffect, useRef, useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'

// 動態推導 WebSocket URL，支援 Tailscale sub-path（/blender）
// BASE_URL 由 Vite base config 注入：開發環境 = '/blender/'
const _base = import.meta.env.BASE_URL.replace(/\/$/, '') // '/blender'
const _proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = `${_proto}//${location.host}${_base}/ws/chat`

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const { setConnected, addAssistantMessage, setSessionId, sessionId } = useChatStore()

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const ws = new WebSocket(WS_URL)
    wsRef.current = ws

    ws.onopen = () => setConnected(true)
    ws.onclose = () => {
      setConnected(false)
      setTimeout(connect, 3000) // auto-reconnect
    }
    ws.onerror = () => ws.close()

    ws.onmessage = (event: MessageEvent) => {
      const data = JSON.parse(event.data as string) as {
        session_id?: string
        content: string
        status: 'done' | 'error' | 'streaming'
        blender_output?: string | null
        screenshot?: string | null  // base64 PNG — live viewport update
      }
      if (data.session_id) setSessionId(data.session_id)
      addAssistantMessage(data.content, data.status, data.blender_output, data.screenshot)
    }
  }, [setConnected, addAssistantMessage, setSessionId])

  useEffect(() => {
    connect()
    return () => wsRef.current?.close()
  }, [connect])

  const sendMessage = useCallback(
    (content: string) => {
      if (wsRef.current?.readyState !== WebSocket.OPEN) return
      wsRef.current.send(JSON.stringify({ type: 'chat', content, session_id: sessionId }))
    },
    [sessionId],
  )

  return { sendMessage }
}
