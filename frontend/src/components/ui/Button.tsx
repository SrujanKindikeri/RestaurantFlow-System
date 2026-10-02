// =============================================================================
// RestaurantFlow — Button
// =============================================================================

import { cn } from '@/utils/cn'

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success'
type ButtonSize = 'sm' | 'md' | 'lg'

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: ButtonSize
  loading?: boolean
  children: React.ReactNode
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'bg-brand-600 hover:bg-brand-500 text-white border border-brand-500/50 focus-visible:ring-brand-500/40',
  secondary:
    'bg-gray-800 hover:bg-gray-700 text-gray-200 border border-gray-700 focus-visible:ring-gray-500/40',
  ghost:
    'bg-transparent hover:bg-gray-800 text-gray-400 hover:text-gray-200 border border-transparent focus-visible:ring-gray-500/40',
  danger:
    'bg-red-600/10 hover:bg-red-600/20 text-red-400 border border-red-600/30 focus-visible:ring-red-500/40',
  success:
    'bg-green-600/10 hover:bg-green-600/20 text-green-400 border border-green-600/30 focus-visible:ring-green-500/40',
}

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'px-3 py-1.5 text-xs',
  md: 'px-4 py-2 text-sm',
  lg: 'px-5 py-2.5 text-sm',
}

export function Button({
  variant = 'secondary',
  size = 'md',
  loading = false,
  disabled,
  className,
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      disabled={disabled || loading}
      className={cn(
        'inline-flex items-center justify-center gap-2 rounded-lg font-medium',
        'transition-colors duration-150',
        'focus-visible:outline-none focus-visible:ring-2',
        'disabled:pointer-events-none disabled:opacity-50',
        variantClasses[variant],
        sizeClasses[size],
        className,
      )}
      {...props}
    >
      {loading && (
        <svg
          className="h-3.5 w-3.5 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
          aria-hidden="true"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
          />
        </svg>
      )}
      {children}
    </button>
  )
}
