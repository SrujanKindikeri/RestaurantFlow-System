// =============================================================================
// RestaurantFlow — Login Page
// Phase 3
// =============================================================================

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'
import { login } from '@/services/auth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'

interface FormState {
  email: string
  password: string
}

interface FormErrors {
  email?: string
  password?: string
}

export function LoginPage() {
  const navigate = useNavigate()
  const { setTokens } = useAuth()
  const { toast: showToast } = useToast()
  const [form, setForm] = useState<FormState>({ email: '', password: '' })
  const [errors, setErrors] = useState<FormErrors>({})
  const [loading, setLoading] = useState(false)

  function validate(): boolean {
    const e: FormErrors = {}
    if (!form.email.trim()) e.email = 'Email is required.'
    if (!form.password) e.password = 'Password is required.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    try {
      const tokens = await login({ email: form.email, password: form.password })
      await setTokens(tokens.access, tokens.refresh)
      navigate('/', { replace: true })
    } catch (err: unknown) {
      const message =
        (err as { response?: { data?: { message?: string } } })?.response?.data?.message ??
        'Invalid email or password.'
      showToast(message, 'error')
      setErrors({ password: message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="w-9 h-9 rounded-xl bg-brand-500 flex items-center justify-center">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-5 h-5 text-white" aria-hidden="true">
              <path d="M3 11l19-9-9 19-2-8-8-2z" />
            </svg>
          </div>
          <div>
            <p className="font-semibold text-white text-base tracking-tight">RestaurantFlow</p>
            <p className="text-[10px] text-gray-600 font-mono">Phase 3</p>
          </div>
        </div>

        {/* Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-2xl shadow-black/50">
          <h1 className="text-lg font-semibold text-white mb-1">Sign in</h1>
          <p className="text-sm text-gray-500 mb-6">Enter your credentials to continue.</p>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <Input
              label="Email"
              id="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))}
              error={errors.email}
              placeholder="you@example.com"
              disabled={loading}
            />
            <Input
              label="Password"
              id="password"
              type="password"
              autoComplete="current-password"
              value={form.password}
              onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))}
              error={errors.password}
              placeholder="••••••••"
              disabled={loading}
            />
            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              className="w-full mt-2"
            >
              Sign in
            </Button>
          </form>

          <p className="text-center text-sm text-gray-600 mt-5">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="text-brand-400 hover:text-brand-300 transition-colors">
              Register
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
