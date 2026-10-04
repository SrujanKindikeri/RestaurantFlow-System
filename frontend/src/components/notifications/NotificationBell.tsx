// =============================================================================
// RestaurantFlow — Notification Bell
// Phase 16
//
// Displays in the header top bar:
//   - Bell icon with unread badge count
//   - Dropdown showing the 5 most recent notifications
//   - "Mark all read" and "View all" actions
// =============================================================================

import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useUnreadCount, useNotifications, useMarkRead, useMarkAllRead } from '@/hooks/useNotifications'
import { cn } from '@/utils/cn'
import type { NotificationRecipient, NotificationSeverity } from '@/types'

// ---------------------------------------------------------------------------
// Severity color map
// ---------------------------------------------------------------------------
const SEVERITY_COLORS: Record<NotificationSeverity, string> = {
  INFO:     'bg-blue-500',
  LOW:      'bg-gray-400',
  MEDIUM:   'bg-yellow-400',
  HIGH:     'bg-orange-500',
  CRITICAL: 'bg-red-500',
}

const SEVERITY_TEXT: Record<NotificationSeverity, string> = {
  INFO:     'text-blue-400',
  LOW:      'text-gray-400',
  MEDIUM:   'text-yellow-400',
  HIGH:     'text-orange-400',
  CRITICAL: 'text-red-400',
}

// ---------------------------------------------------------------------------
// Single notification row inside the dropdown
// ---------------------------------------------------------------------------
function NotificationRow({
  recipient,
  onRead,
}: {
  recipient: NotificationRecipient
  onRead: (id: string) => void
}) {
  const { notification: n } = recipient
  const severity = (n.severity ?? 'INFO') as NotificationSeverity

  return (
    <button
      onClick={() => onRead(n.id)}
      className={cn(
        'w-full text-left flex items-start gap-3 px-4 py-3 hover:bg-gray-800/60 transition-colors',
        !recipient.is_read && 'bg-gray-800/30',
      )}
    >
      {/* Severity dot */}
      <span
        className={cn('mt-1.5 w-2 h-2 rounded-full flex-shrink-0', SEVERITY_COLORS[severity])}
        aria-hidden="true"
      />
      <div className="flex-1 min-w-0">
        <p className={cn('text-xs font-medium truncate', SEVERITY_TEXT[severity])}>
          {n.title}
        </p>
        <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-2">{n.message}</p>
        <p className="text-[10px] text-gray-700 mt-1">
          {new Date(n.created_at).toLocaleString()}
        </p>
      </div>
      {!recipient.is_read && (
        <span
          className="mt-1 w-1.5 h-1.5 rounded-full bg-brand-500 flex-shrink-0"
          aria-label="Unread"
        />
      )}
    </button>
  )
}

// ---------------------------------------------------------------------------
// Bell button + dropdown
// ---------------------------------------------------------------------------
export function NotificationBell() {
  const [open, setOpen]       = useState(false)
  const dropdownRef           = useRef<HTMLDivElement>(null)
  const navigate              = useNavigate()

  const { data: countData }   = useUnreadCount()
  const { data: listData }    = useNotifications({ page_size: 5 })
  const markRead              = useMarkRead()
  const markAll               = useMarkAllRead()

  const unreadCount           = countData?.count ?? 0
  const recent                = listData?.results?.slice(0, 5) ?? []

  // Close on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  function handleMarkRead(id: string) {
    markRead.mutate(id)
  }

  function handleMarkAll() {
    markAll.mutate()
  }

  function handleViewAll() {
    setOpen(false)
    navigate('/notifications')
  }

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell button */}
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={unreadCount > 0 ? `${unreadCount} unread notifications` : 'Notifications'}
        aria-haspopup="true"
        aria-expanded={open}
        className="relative p-1.5 rounded-md text-gray-500 hover:text-gray-200 hover:bg-gray-800 transition-colors"
      >
        <svg
          className="h-5 w-5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth="1.75"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
          />
        </svg>

        {/* Unread badge */}
        {unreadCount > 0 && (
          <span
            className="absolute top-0.5 right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center leading-none"
            aria-hidden="true"
          >
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {/* Dropdown */}
      {open && (
        <div
          className="absolute right-0 top-full mt-2 w-80 bg-gray-900 border border-gray-800 rounded-xl shadow-2xl z-50 overflow-hidden"
          role="dialog"
          aria-label="Recent notifications"
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800">
            <h2 className="text-sm font-semibold text-gray-200">Notifications</h2>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAll}
                className="text-[11px] text-brand-400 hover:text-brand-300 transition-colors"
              >
                Mark all read
              </button>
            )}
          </div>

          {/* Notification list */}
          {recent.length === 0 ? (
            <div className="px-4 py-6 text-center">
              <svg
                className="h-8 w-8 mx-auto mb-2 text-gray-700"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
                strokeWidth="1.5"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                />
              </svg>
              <p className="text-xs text-gray-600">No notifications</p>
            </div>
          ) : (
            <ul role="list" className="divide-y divide-gray-800/50 max-h-80 overflow-y-auto">
              {recent.map((r) => (
                <li key={r.id}>
                  <NotificationRow recipient={r} onRead={handleMarkRead} />
                </li>
              ))}
            </ul>
          )}

          {/* Footer */}
          <div className="border-t border-gray-800 px-4 py-2.5">
            <button
              onClick={handleViewAll}
              className="w-full text-xs text-center text-brand-400 hover:text-brand-300 transition-colors py-1"
            >
              View all notifications →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
