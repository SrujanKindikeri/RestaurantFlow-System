// =============================================================================
// RestaurantFlow — Notification Center Page
// Phase 16
//
// Route: /notifications
//
// Features:
//   - All / Unread filter
//   - Filter by severity, notification_type
//   - Paginated list
//   - Mark individual or all as read
//   - Acknowledge action
//   - Click-through to action_url
// =============================================================================

import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  useNotifications,
  useUnreadCount,
  useMarkRead,
  useAcknowledge,
  useMarkAllRead,
} from '@/hooks/useNotifications'
import { cn } from '@/utils/cn'
import type { NotificationRecipient, NotificationSeverity } from '@/types'

const SEVERITY_COLORS: Record<NotificationSeverity, string> = {
  INFO:     'border-l-blue-500 bg-blue-500/5',
  LOW:      'border-l-gray-500 bg-gray-500/5',
  MEDIUM:   'border-l-yellow-500 bg-yellow-500/5',
  HIGH:     'border-l-orange-500 bg-orange-500/5',
  CRITICAL: 'border-l-red-500 bg-red-500/5',
}
const SEVERITY_BADGE: Record<NotificationSeverity, string> = {
  INFO:     'bg-blue-500/10 text-blue-400',
  LOW:      'bg-gray-500/10 text-gray-400',
  MEDIUM:   'bg-yellow-500/10 text-yellow-400',
  HIGH:     'bg-orange-500/10 text-orange-400',
  CRITICAL: 'bg-red-500/10 text-red-400',
}

function NotificationCard({
  recipient,
  onRead,
  onAcknowledge,
}: {
  recipient: NotificationRecipient
  onRead: (id: string) => void
  onAcknowledge: (id: string) => void
}) {
  const { notification: n } = recipient
  const severity = (n.severity ?? 'INFO') as NotificationSeverity
  const navigate = useNavigate()

  function handleAction() {
    onRead(n.id)
    if (n.action_url) {
      // action_url is a server-generated path, safe to use for internal navigation
      navigate(n.action_url)
    }
  }

  return (
    <article
      className={cn(
        'border-l-4 rounded-r-lg p-4 transition-opacity',
        SEVERITY_COLORS[severity],
        recipient.is_read && 'opacity-60',
      )}
      aria-label={n.title}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span
              className={cn(
                'inline-block text-[10px] font-semibold px-2 py-0.5 rounded uppercase tracking-wide',
                SEVERITY_BADGE[severity],
              )}
            >
              {n.severity}
            </span>
            <span className="text-[10px] text-gray-600">
              {n.notification_type.replace(/_/g, ' ')}
            </span>
          </div>
          <h3 className="text-sm font-semibold text-gray-200 mb-1">{n.title}</h3>
          <p className="text-xs text-gray-400 leading-relaxed">{n.message}</p>
          <p className="text-[10px] text-gray-700 mt-2">
            {new Date(n.created_at).toLocaleString()}
          </p>
        </div>

        <div className="flex flex-col gap-1.5 flex-shrink-0">
          {!recipient.is_read && (
            <button
              onClick={() => onRead(n.id)}
              className="text-[11px] text-brand-400 hover:text-brand-300 transition-colors whitespace-nowrap"
            >
              Mark read
            </button>
          )}
          {!recipient.acknowledged_at && (
            <button
              onClick={() => onAcknowledge(n.id)}
              className="text-[11px] text-gray-500 hover:text-gray-300 transition-colors whitespace-nowrap"
            >
              Acknowledge
            </button>
          )}
          {n.action_url && (
            <button
              onClick={handleAction}
              className="text-[11px] text-brand-400 hover:text-brand-300 transition-colors whitespace-nowrap"
            >
              View →
            </button>
          )}
        </div>
      </div>
    </article>
  )
}

export function NotificationCenter() {
  const [unreadOnly, setUnreadOnly]       = useState(false)
  const [severity, setSeverity]           = useState('')
  const [notifType, setNotifType]         = useState('')
  const [page, setPage]                   = useState(1)

  const { data: countData }  = useUnreadCount()
  const { data, isLoading }  = useNotifications({
    unread: unreadOnly || undefined,
    severity: severity || undefined,
    notification_type: notifType || undefined,
    page,
    page_size: 20,
  })

  const markRead    = useMarkRead()
  const acknowledge = useAcknowledge()
  const markAll     = useMarkAllRead()

  const results    = data?.results ?? []
  const total      = data?.count ?? 0
  const totalPages = Math.ceil(total / 20)
  const unreadCount = countData?.count ?? 0

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-gray-100">Notifications</h1>
          {unreadCount > 0 && (
            <p className="text-xs text-gray-500 mt-0.5">{unreadCount} unread</p>
          )}
        </div>
        {unreadCount > 0 && (
          <button
            onClick={() => markAll.mutate()}
            className="text-sm text-brand-400 hover:text-brand-300 transition-colors"
          >
            Mark all read
          </button>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-6">
        <button
          onClick={() => { setUnreadOnly(false); setPage(1) }}
          className={cn(
            'text-xs px-3 py-1.5 rounded-lg border transition-colors',
            !unreadOnly
              ? 'border-brand-500/50 text-brand-400 bg-brand-500/10'
              : 'border-gray-700 text-gray-500 hover:text-gray-300',
          )}
        >
          All
        </button>
        <button
          onClick={() => { setUnreadOnly(true); setPage(1) }}
          className={cn(
            'text-xs px-3 py-1.5 rounded-lg border transition-colors',
            unreadOnly
              ? 'border-brand-500/50 text-brand-400 bg-brand-500/10'
              : 'border-gray-700 text-gray-500 hover:text-gray-300',
          )}
        >
          Unread
        </button>

        <select
          value={severity}
          onChange={(e) => { setSeverity(e.target.value); setPage(1) }}
          className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 bg-gray-800 text-gray-400 focus:outline-none focus:border-brand-500"
          aria-label="Filter by severity"
        >
          <option value="">All severities</option>
          <option value="CRITICAL">Critical</option>
          <option value="HIGH">High</option>
          <option value="MEDIUM">Medium</option>
          <option value="LOW">Low</option>
          <option value="INFO">Info</option>
        </select>
      </div>

      {/* List */}
      {isLoading ? (
        <div className="space-y-3">
          {[...Array(4)].map((_, i) => (
            <div key={i} className="h-20 rounded-lg bg-gray-800/50 animate-pulse" />
          ))}
        </div>
      ) : results.length === 0 ? (
        <div className="text-center py-16">
          <svg
            className="h-12 w-12 mx-auto mb-3 text-gray-700"
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
          <p className="text-sm text-gray-600">No notifications</p>
        </div>
      ) : (
        <div className="space-y-2">
          {results.map((r) => (
            <NotificationCard
              key={r.id}
              recipient={r}
              onRead={(id) => markRead.mutate(id)}
              onAcknowledge={(id) => acknowledge.mutate(id)}
            />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-6">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page <= 1}
            className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 text-gray-500 hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Previous
          </button>
          <span className="text-xs text-gray-600">
            Page {page} of {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page >= totalPages}
            className="text-xs px-3 py-1.5 rounded-lg border border-gray-700 text-gray-500 hover:text-gray-300 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Next
          </button>
        </div>
      )}
    </div>
  )
}
