// =============================================================================
// RestaurantFlow — Modal
// =============================================================================

import { useEffect } from 'react'
import { cn } from '@/utils/cn'

interface ModalProps {
  open: boolean
  onClose: () => void
  title: string
  description?: string
  children: React.ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
}

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  size = 'md',
}: ModalProps) {
  // Close on Escape
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-gray-950/80 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Panel */}
      <div
        className={cn(
          'relative w-full rounded-xl bg-gray-900 border border-gray-800',
          'shadow-2xl shadow-black/60',
          sizeClasses[size],
        )}
      >
        {/* Header */}
        <div className="flex items-start justify-between gap-4 px-6 pt-6 pb-4 border-b border-gray-800">
          <div>
            <h2
              id="modal-title"
              className="text-base font-semibold text-white"
            >
              {title}
            </h2>
            {description && (
              <p className="mt-1 text-sm text-gray-500">{description}</p>
            )}
          </div>
          <button
            onClick={onClose}
            className="text-gray-600 hover:text-gray-300 transition-colors mt-0.5"
            aria-label="Close modal"
          >
            <svg
              className="h-5 w-5"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M18 6L6 18M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Body */}
        <div className="px-6 py-5">{children}</div>
      </div>
    </div>
  )
}

// ---------------------------------------------------------------------------
// Confirm Dialog
// ---------------------------------------------------------------------------

interface ConfirmDialogProps {
  open: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmLabel?: string
  confirmVariant?: 'danger' | 'warning' | 'success'
  loading?: boolean
}

export function ConfirmDialog({
  open,
  onClose,
  onConfirm,
  title,
  message,
  confirmLabel = 'Confirm',
  confirmVariant = 'danger',
  loading = false,
}: ConfirmDialogProps) {
  const confirmClasses = {
    danger: 'bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-600/30',
    warning: 'bg-yellow-600/10 hover:bg-yellow-600/20 text-yellow-400 border border-yellow-600/30',
    success: 'bg-green-600/10 hover:bg-green-600/20 text-green-400 border border-green-600/30',
  }

  if (!open) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4" role="alertdialog">
      <div className="absolute inset-0 bg-gray-950/80 backdrop-blur-sm" onClick={onClose} />
      <div className="relative w-full max-w-sm rounded-xl bg-gray-900 border border-gray-800 shadow-2xl shadow-black/60 p-6">
        <h2 className="text-base font-semibold text-white mb-2">{title}</h2>
        <p className="text-sm text-gray-400 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onClose}
            disabled={loading}
            className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-gray-200 border border-gray-700 hover:border-gray-600 transition-colors disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              'px-4 py-2 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 inline-flex items-center gap-2',
              confirmClasses[confirmVariant],
            )}
          >
            {loading && (
              <svg className="h-3.5 w-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
              </svg>
            )}
            {confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}
