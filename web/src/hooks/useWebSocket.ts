import { useEffect, useRef, useCallback } from 'react'
import { useChatStore } from '../stores/chatStore'

// 動態推導 WebSocket URL，支援 Tailscale sub-path（/blender）
// BASE_URL 由 Vite base config 注入：開發環境 = '/blender/'
const _base = import.meta.env.BASE_URL.replace(/\/$/, '') // '/blender'
const _proto = location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = `${_proto}//${location.host}${_base}/ws/chat`

export function useWebSocket() {
  const wsRef = useRef<WebSocket | null>(null)
  const {
    setConnected,
    addAssistantMessage,
    appendStreamToken,
    setSessionId,
    setLiveScreenshot,
    sessionId,
  } = useChatStore()

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
        type?: string
        session_id?: string
        content?: string
        status?: 'done' | 'error' | 'streaming'
        blender_output?: string | null
        screenshot?: string | null
      }

      // Autonomous viewport push from background broadcast task
      if (data.type === 'viewport_update') {
        if (data.screenshot) setLiveScreenshot(data.screenshot)
        return
      }

      if (data.session_id) setSessionId(data.session_id)

      if (data.status === 'streaming') {
        appendStreamToken(data.content ?? '', data.session_id)
      } else {
        addAssistantMessage(data.content ?? '', data.status, data.blender_output, data.screenshot)
      }
    }
  }, [setConnected, addAssistantMessage, appendStreamToken, setSessionId, setLiveScreenshot])

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

