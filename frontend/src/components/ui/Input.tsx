// =============================================================================
// RestaurantFlow — Input + Textarea + Select
// =============================================================================

import { cn } from '@/utils/cn'

// ---------------------------------------------------------------------------
// Input
// ---------------------------------------------------------------------------

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  hint?: string
}

export function Input({ label, error, hint, className, id, ...props }: InputProps) {
  const fieldId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={fieldId}
          className="text-xs font-medium text-gray-400 uppercase tracking-wide"
        >
          {label}
        </label>
      )}
      <input
        id={fieldId}
        className={cn(
          'w-full rounded-lg bg-gray-800/70 border px-3 py-2 text-sm text-gray-100',
          'placeholder:text-gray-600',
          'focus:outline-none focus:ring-2',
          error
            ? 'border-red-600/50 focus:ring-red-500/30'
            : 'border-gray-700 focus:border-brand-500/50 focus:ring-brand-500/20',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          className,
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
      {hint && !error && <p className="text-xs text-gray-600">{hint}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Textarea
// ---------------------------------------------------------------------------

interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string
  error?: string
}

export function Textarea({ label, error, className, id, ...props }: TextareaProps) {
  const fieldId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={fieldId}
          className="text-xs font-medium text-gray-400 uppercase tracking-wide"
        >
          {label}
        </label>
      )}
      <textarea
        id={fieldId}
        rows={3}
        className={cn(
          'w-full rounded-lg bg-gray-800/70 border px-3 py-2 text-sm text-gray-100',
          'placeholder:text-gray-600 resize-none',
          'focus:outline-none focus:ring-2',
          error
            ? 'border-red-600/50 focus:ring-red-500/30'
            : 'border-gray-700 focus:border-brand-500/50 focus:ring-brand-500/20',
          className,
        )}
        {...props}
      />
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Select
// ---------------------------------------------------------------------------

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string
  error?: string
  options: { value: string; label: string }[]
}

export function Select({ label, error, options, className, id, ...props }: SelectProps) {
  const fieldId = id ?? label?.toLowerCase().replace(/\s+/g, '-')
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label
          htmlFor={fieldId}
          className="text-xs font-medium text-gray-400 uppercase tracking-wide"
        >
          {label}
        </label>
      )}
      <select
        id={fieldId}
        className={cn(
          'w-full rounded-lg bg-gray-800/70 border px-3 py-2 text-sm text-gray-100',
          'focus:outline-none focus:ring-2',
          error
            ? 'border-red-600/50 focus:ring-red-500/30'
            : 'border-gray-700 focus:border-brand-500/50 focus:ring-brand-500/20',
          className,
        )}
        {...props}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value} className="bg-gray-900">
            {opt.label}
          </option>
        ))}
      </select>
      {error && <p className="text-xs text-red-400">{error}</p>}
    </div>
  )
}
