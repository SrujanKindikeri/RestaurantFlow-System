// =============================================================================
// RestaurantFlow — Notification Preferences Page
// Phase 16
//
// Route: /settings/notifications
//
// Shows a grid:
//   Notification Type | In-App | Email | SMS | WhatsApp | Telegram
// Toggle per channel.
// Falls back to defaults when no explicit preference exists.
// =============================================================================

import { useNotificationPreferences, useUpsertPreference } from '@/hooks/useNotifications'
import type { NotificationChannel } from '@/types'
import { cn } from '@/utils/cn'

// ---------------------------------------------------------------------------
// All notification type labels
// ---------------------------------------------------------------------------
const NOTIFICATION_TYPES: { type: string; label: string; group: string }[] = [
  { type: 'ORDER_CONFIRMED',         label: 'Order Confirmed',            group: 'Orders' },
  { type: 'ORDER_READY',             label: 'Order Ready',                group: 'Orders' },
  { type: 'ORDER_CANCELLED',         label: 'Order Cancelled',            group: 'Orders' },
  { type: 'KITCHEN_ORDER_READY',     label: 'Kitchen Order Ready',        group: 'Kitchen' },
  { type: 'KITCHEN_ORDER_DELAYED',   label: 'Kitchen Order Delayed',      group: 'Kitchen' },
  { type: 'KITCHEN_BACKLOG',         label: 'Kitchen Backlog',            group: 'Kitchen' },
  { type: 'INVENTORY_LOW_STOCK',     label: 'Low Stock',                  group: 'Inventory' },
  { type: 'INVENTORY_OUT_OF_STOCK',  label: 'Out of Stock',               group: 'Inventory' },
  { type: 'INVENTORY_PURCHASE_RECEIVED', label: 'Purchase Received',      group: 'Inventory' },
  { type: 'INVENTORY_CONSUMPTION_FAILED', label: 'Consumption Failed',    group: 'Inventory' },
  { type: 'PAYMENT_COMPLETED',       label: 'Payment Completed',          group: 'Payments' },
  { type: 'PAYMENT_FAILED',          label: 'Payment Failed',             group: 'Payments' },
  { type: 'REFUND_PROCESSED',        label: 'Refund Processed',           group: 'Payments' },
  { type: 'EXPENSE_APPROVAL_REQUIRED', label: 'Expense Approval Required', group: 'Finance' },
  { type: 'EXPENSE_APPROVED',        label: 'Expense Approved',           group: 'Finance' },
  { type: 'EXPENSE_REJECTED',        label: 'Expense Rejected',           group: 'Finance' },
  { type: 'PAYABLE_OVERDUE',         label: 'Payable Overdue',            group: 'Finance' },
  { type: 'ACCOUNTING_POSTING_FAILED', label: 'Accounting Posting Failed', group: 'Accounting' },
  { type: 'CENTRAL_ALERT_CREATED',   label: 'Central Alert Created',      group: 'Central Control' },
  { type: 'CENTRAL_ISSUE_ASSIGNED',  label: 'Central Issue Assigned',     group: 'Central Control' },
  { type: 'USER_ACCESS_REVOKED',     label: 'User Access Revoked',        group: 'Security' },
  { type: 'SYSTEM_HEALTH_DEGRADED',  label: 'System Health Degraded',     group: 'System' },
]

const CHANNELS: { channel: NotificationChannel; label: string }[] = [
  { channel: 'IN_APP',    label: 'In-App' },
  { channel: 'EMAIL',     label: 'Email' },
  { channel: 'SMS',       label: 'SMS' },
  { channel: 'WHATSAPP',  label: 'WhatsApp' },
  { channel: 'TELEGRAM',  label: 'Telegram' },
]

// Default preferences fallback (mirrors backend DEFAULT_CHANNEL_PREFS)
const DEFAULTS: Record<string, Partial<Record<NotificationChannel, boolean>>> = {
  PAYMENT_FAILED:            { IN_APP: true,  EMAIL: true },
  ACCOUNTING_POSTING_FAILED: { IN_APP: true,  EMAIL: true },
  CENTRAL_ALERT_CREATED:     { IN_APP: true,  EMAIL: true },
  CENTRAL_ISSUE_ASSIGNED:    { IN_APP: true,  EMAIL: true },
  EXPENSE_APPROVAL_REQUIRED: { IN_APP: true,  EMAIL: true },
  PAYABLE_OVERDUE:           { IN_APP: true,  EMAIL: true },
  USER_ACCESS_REVOKED:       { IN_APP: true,  EMAIL: true },
  SYSTEM_HEALTH_DEGRADED:    { IN_APP: true,  EMAIL: true },
}

function getDefaultEnabled(type: string, channel: NotificationChannel): boolean {
  return DEFAULTS[type]?.[channel] ?? (channel === 'IN_APP')
}

// ---------------------------------------------------------------------------
// Toggle switch
// ---------------------------------------------------------------------------
function Toggle({
  checked,
  onChange,
  label,
}: {
  checked: boolean
  onChange: (v: boolean) => void
  label: string
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      aria-label={label}
      onClick={() => onChange(!checked)}
      className={cn(
        'relative inline-flex h-4 w-7 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-brand-500',
        checked ? 'bg-brand-500' : 'bg-gray-700',
      )}
    >
      <span
        aria-hidden="true"
        className={cn(
          'pointer-events-none inline-block h-3 w-3 rounded-full bg-white shadow-sm ring-0 transition-transform',
          checked ? 'translate-x-3' : 'translate-x-0',
        )}
      />
    </button>
  )
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------
export function NotificationPreferences() {
  const { data: prefs = [], isLoading } = useNotificationPreferences()
  const upsert = useUpsertPreference()

  function getEnabled(notifType: string, channel: NotificationChannel): boolean {
    const existing = prefs.find(
      (p) => p.notification_type === notifType && p.channel === channel,
    )
    return existing != null ? existing.enabled : getDefaultEnabled(notifType, channel)
  }

  function handleToggle(notifType: string, channel: NotificationChannel, enabled: boolean) {
    upsert.mutate({ notification_type: notifType, channel, enabled })
  }

  // Group notifications by group label
  const groups = Array.from(new Set(NOTIFICATION_TYPES.map((n) => n.group)))

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-gray-100">Notification Preferences</h1>
        <p className="text-sm text-gray-500 mt-1">
          Choose which notifications you receive per channel.
        </p>
      </div>

      {isLoading ? (
        <div className="space-y-4">
          {[...Array(5)].map((_, i) => (
            <div key={i} className="h-10 rounded-lg bg-gray-800/50 animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="space-y-8">
          {groups.map((group) => {
            const types = NOTIFICATION_TYPES.filter((n) => n.group === group)
            return (
              <section key={group} aria-labelledby={`group-${group}`}>
                <h2
                  id={`group-${group}`}
                  className="text-xs font-semibold text-gray-600 uppercase tracking-widest mb-3"
                >
                  {group}
                </h2>
                <div className="rounded-xl border border-gray-800 overflow-hidden">
                  {/* Column headers */}
                  <div className="grid grid-cols-[1fr_repeat(5,_52px)] gap-0 border-b border-gray-800 bg-gray-800/30">
                    <div className="px-4 py-2 text-[10px] text-gray-600 uppercase tracking-widest">
                      Notification
                    </div>
                    {CHANNELS.map((c) => (
                      <div
                        key={c.channel}
                        className="text-[10px] text-gray-600 uppercase tracking-widest text-center py-2"
                      >
                        {c.label}
                      </div>
                    ))}
                  </div>

                  {/* Rows */}
                  {types.map((item, idx) => (
                    <div
                      key={item.type}
                      className={cn(
                        'grid grid-cols-[1fr_repeat(5,_52px)] items-center',
                        idx < types.length - 1 && 'border-b border-gray-800/50',
                      )}
                    >
                      <div className="px-4 py-3 text-sm text-gray-300">{item.label}</div>
                      {CHANNELS.map((c) => (
                        <div key={c.channel} className="flex justify-center py-3">
                          <Toggle
                            checked={getEnabled(item.type, c.channel)}
                            onChange={(v) => handleToggle(item.type, c.channel, v)}
                            label={`${item.label} via ${c.label}`}
                          />
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </section>
            )
          })}
        </div>
      )}
    </div>
  )
}
