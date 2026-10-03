// =============================================================================
// RestaurantFlow — Kitchen WebSocket Hook
// Phase 7
//
// Manages the WebSocket connection to the KDS channel.
// Features:
//   - JWT authentication via query string
//   - Automatic reconnection with exponential backoff (max 30s)
//   - Reconnect counter: after reconnect, triggers a REST sync
//   - Connection status: CONNECTING | CONNECTED | DISCONNECTED | ERROR
//   - Deduplication by event_id (prevents duplicate processing on reconnect)
//   - Does NOT store kitchen state — that lives in useKitchen hook
// =============================================================================

import { useEffect, useRef, useCallback, useState } from 'react'
import type { KitchenEventMessage, KitchenSyncMessage } from '@/types'

export type WsStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR'

interface UseKitchenWebSocketOptions {
  branchId: string | null
  token: string | null
  onEvent: (msg: KitchenEventMessage) => void
  onSync: (msg: KitchenSyncMessage) => void
  enabled?: boolean
}

const WS_BASE = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
const INITIAL_BACKOFF_MS = 1_000
const MAX_BACKOFF_MS = 30_000
const BACKOFF_MULTIPLIER = 2

export function useKitchenWebSocket({
  branchId,
  token,
  onEvent,
  onSync,
  enabled = true,
}: UseKitchenWebSocketOptions) {
  const [status, setStatus] = useState<WsStatus>('DISCONNECTED')
  const wsRef = useRef<WebSocket | null>(null)
  const backoffRef = useRef(INITIAL_BACKOFF_MS)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const seenEventIds = useRef<Set<string>>(new Set())
  const shouldReconnect = useRef(true)
  const onEventRef = useRef(onEvent)
  const onSyncRef = useRef(onSync)

  // Keep callbacks fresh without re-triggering the effect
  useEffect(() => { onEventRef.current = onEvent }, [onEvent])
  useEffect(() => { onSyncRef.current = onSync }, [onSync])

  const connect = useCallback(() => {
    if (!branchId || !token || !enabled) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const url = `${WS_BASE}/ws/kitchen/${branchId}/?token=${token}`
    setStatus('CONNECTING')

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('CONNECTED')
      backoffRef.current = INITIAL_BACKOFF_MS // reset backoff on success
    }

    ws.onmessage = (evt) => {
      let data: unknown
      try {
        data = JSON.parse(evt.data as string)
      } catch {
        return
      }

      const msg = data as { type: string; [key: string]: unknown }

      if (msg.type === 'kitchen.sync') {
        onSyncRef.current(msg as unknown as KitchenSyncMessage)
        return
      }

      if (msg.type === 'kitchen.event') {
        const eventMsg = msg as unknown as KitchenEventMessage
        const eventId = eventMsg.payload?.event_id
        // Deduplicate by event_id
        if (eventId && seenEventIds.current.has(eventId)) return
        if (eventId) seenEventIds.current.add(eventId)
        // Keep seen set bounded (last 500 events)
        if (seenEventIds.current.size > 500) {
          const first = seenEventIds.current.values().next().value
          if (first !== undefined) seenEventIds.current.delete(first)
        }
        onEventRef.current(eventMsg)
      }
    }

    ws.onerror = () => {
      setStatus('ERROR')
    }

    ws.onclose = (evt) => {
      wsRef.current = null
      if (shouldReconnect.current && enabled && (evt.code !== 4001 && evt.code !== 4003 && evt.code !== 4004)) {
        // Rejected by server due to auth/permissions — don't reconnect
        if (evt.code >= 4001 && evt.code <= 4099) {
          setStatus('ERROR')
          return
        }
        setStatus('DISCONNECTED')
        const delay = Math.min(backoffRef.current, MAX_BACKOFF_MS)
        backoffRef.current = Math.min(backoffRef.current * BACKOFF_MULTIPLIER, MAX_BACKOFF_MS)
        reconnectTimerRef.current = setTimeout(connect, delay)
      } else {
        setStatus('DISCONNECTED')
      }
    }
  }, [branchId, token, enabled])

  // Connect on mount / when branchId/token change
  useEffect(() => {
    shouldReconnect.current = true
    connect()

    return () => {
      shouldReconnect.current = false
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
      if (wsRef.current) {
        wsRef.current.onclose = null // prevent reconnect on intentional close
        wsRef.current.close()
        wsRef.current = null
      }
      setStatus('DISCONNECTED')
    }
  }, [connect])

  const sendPing = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'ping' }))
    }
  }, [])

  const requestSync = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: 'sync' }))
    }
  }, [])

  return { status, sendPing, requestSync }
}
