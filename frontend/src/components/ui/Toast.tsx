// =============================================================================
// RestaurantFlow — Toast notifications (simple, no external dependency)
// =============================================================================

import { useState, useCallback, createContext, useContext } from 'react'
import { cn } from '@/utils/cn'

type ToastType = 'success' | 'error' | 'warning' | 'info'

interface Toast {
  id: string
  type: ToastType
  message: string
}

interface ToastContextValue {
  toast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextValue | undefined>(undefined)

const typeClasses: Record<ToastType, string> = {
  success: 'bg-gray-900 border-green-500/40 text-green-400',
  error: 'bg-gray-900 border-red-500/40 text-red-400',
  warning: 'bg-gray-900 border-yellow-500/40 text-yellow-400',
  info: 'bg-gray-900 border-blue-500/40 text-blue-400',
}

const typeIcons: Record<ToastType, string> = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ',
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setToasts((prev) => [...prev, { id, type, message }])
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4000)
  }, [])

  const dismiss = (id: string) =>
    setToasts((prev) => prev.filter((t) => t.id !== id))

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      {/* Toast container */}
      <div
        className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none"
        aria-live="polite"
        aria-label="Notifications"
      >
        {toasts.map((t) => (
          <div
            key={t.id}
            role="alert"
            className={cn(
              'pointer-events-auto flex items-center gap-3 rounded-xl border px-4 py-3',
              'shadow-xl shadow-black/50 backdrop-blur-sm min-w-[260px] max-w-xs',
              'animate-[slide-in_0.2s_ease-out]',
              typeClasses[t.type],
            )}
          >
            <span className="font-bold text-sm">{typeIcons[t.type]}</span>
            <p className="flex-1 text-sm">{t.message}</p>
            <button
              onClick={() => dismiss(t.id)}
              className="text-gray-600 hover:text-gray-300 transition-colors"
              aria-label="Dismiss notification"
            >
              ×
            </button>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside <ToastProvider>')
  return ctx
}
