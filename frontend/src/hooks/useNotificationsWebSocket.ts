// =============================================================================
// RestaurantFlow — Notifications WebSocket Hook
// Phase 16
//
// Manages the WebSocket connection to ws/notifications/.
// Mirrors the established pattern from useKitchenWebSocket.ts.
//
// Features:
//   - JWT authentication via query string (?token=<jwt>)
//   - Automatic reconnection with exponential backoff (max 30s)
//   - Reconnect counter triggers REST resync (fallback)
//   - Connection status: CONNECTING | CONNECTED | DISCONNECTED | ERROR
//   - Deduplication by event_id / notification_id (last 500)
//
// WebSocket is NOT the source of truth.
// After reconnect the caller is expected to call GET /api/notifications/?unread=true
// =============================================================================

import { useEffect, useRef, useCallback, useState } from 'react'
import type { NotificationWsEvent, NotificationUnreadCountWsEvent } from '@/types'
import { useQueryClient } from '@tanstack/react-query'
import { notificationKeys } from '@/hooks/useNotifications'

export type WsStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'ERROR'

interface UseNotificationsWebSocketOptions {
  token: string | null
  enabled?: boolean
  onNotificationCreated?: (event: NotificationWsEvent) => void
}

const WS_BASE             = import.meta.env.VITE_WS_URL ?? 'ws://localhost:8000'
const INITIAL_BACKOFF_MS  = 1_000
const MAX_BACKOFF_MS      = 30_000
const BACKOFF_MULTIPLIER  = 2

export function useNotificationsWebSocket({
  token,
  enabled = true,
  onNotificationCreated,
}: UseNotificationsWebSocketOptions) {
  const [status, setStatus] = useState<WsStatus>('DISCONNECTED')
  const wsRef              = useRef<WebSocket | null>(null)
  const backoffRef         = useRef(INITIAL_BACKOFF_MS)
  const reconnectTimer     = useRef<ReturnType<typeof setTimeout> | null>(null)
  const shouldReconnect    = useRef(true)
  const seenIds            = useRef<Set<string>>(new Set())
  const onCreatedRef       = useRef(onNotificationCreated)
  const qc                 = useQueryClient()

  useEffect(() => { onCreatedRef.current = onNotificationCreated }, [onNotificationCreated])

  const connect = useCallback(() => {
    if (!token || !enabled) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    const url = `${WS_BASE}/ws/notifications/?token=${token}`
    setStatus('CONNECTING')

    const ws = new WebSocket(url)
    wsRef.current = ws

    ws.onopen = () => {
      setStatus('CONNECTED')
      backoffRef.current = INITIAL_BACKOFF_MS
    }

    ws.onmessage = (evt) => {
      let data: unknown
      try {
        data = JSON.parse(evt.data as string)
      } catch {
        return
      }

      const msg = data as { type: string; [key: string]: unknown }

      if (msg.type === 'notification.event') {
        const payload = msg.payload as NotificationWsEvent | NotificationUnreadCountWsEvent
        handlePayload(payload)
        return
      }

      // Direct type from server
      handlePayload(msg as NotificationWsEvent | NotificationUnreadCountWsEvent)
    }

    ws.onerror = () => setStatus('ERROR')

    ws.onclose = (evt) => {
      wsRef.current = null
      // Auth rejection codes — do not reconnect
      if (evt.code >= 4001 && evt.code <= 4099) {
        setStatus('ERROR')
        return
      }
      if (shouldReconnect.current && enabled) {
        setStatus('DISCONNECTED')
        const delay = Math.min(backoffRef.current, MAX_BACKOFF_MS)
        backoffRef.current = Math.min(backoffRef.current * BACKOFF_MULTIPLIER, MAX_BACKOFF_MS)
        reconnectTimer.current = setTimeout(() => {
          connect()
          // Resync on reconnect — invalidate queries so they refetch
          qc.invalidateQueries({ queryKey: notificationKeys.unreadCount() })
          qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
        }, delay)
      } else {
        setStatus('DISCONNECTED')
      }
    }
  }, [token, enabled, qc]) // eslint-disable-line react-hooks/exhaustive-deps

  function handlePayload(payload: NotificationWsEvent | NotificationUnreadCountWsEvent) {
    if (!payload) return

    if (payload.type === 'notification.unread_count') {
      // Server pushed fresh unread count — update query cache
      const ev = payload as NotificationUnreadCountWsEvent
      qc.setQueryData(notificationKeys.unreadCount(), { count: ev.count })
      return
    }

    const ev = payload as NotificationWsEvent

    if (ev.type === 'notification.created') {
      const id = ev.notification_id
      if (id) {
        if (seenIds.current.has(id)) return
        seenIds.current.add(id)
        if (seenIds.current.size > 500) {
          const first = seenIds.current.values().next().value
          if (first !== undefined) seenIds.current.delete(first)
        }
      }
      // Invalidate list + unread count so they refetch
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount() })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
      onCreatedRef.current?.(ev)
    }

    if (ev.type === 'notification.read') {
      qc.invalidateQueries({ queryKey: notificationKeys.unreadCount() })
      qc.invalidateQueries({ queryKey: ['notifications', 'list'] })
    }
  }

  useEffect(() => {
    shouldReconnect.current = true
    connect()
    return () => {
      shouldReconnect.current = false
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current)
      if (wsRef.current) {
        wsRef.current.onclose = null
        wsRef.current.close()
        wsRef.current = null
      }
      setStatus('DISCONNECTED')
    }
  }, [connect])

  const sendPing = useCallback(() => {
    wsRef.current?.readyState === WebSocket.OPEN &&
      wsRef.current.send(JSON.stringify({ type: 'ping' }))
  }, [])

  const requestSync = useCallback(() => {
    wsRef.current?.readyState === WebSocket.OPEN &&
      wsRef.current.send(JSON.stringify({ type: 'sync' }))
  }, [])

  return { status, sendPing, requestSync }
}
