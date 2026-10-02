// =============================================================================
// RestaurantFlow — Register Page
// Phase 3
// =============================================================================

import { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { register } from '@/services/auth'
import { Button } from '@/components/ui/Button'
import { Input } from '@/components/ui/Input'
import { useToast } from '@/components/ui/Toast'

interface FormState {
  email: string
  first_name: string
  last_name: string
  phone: string
  password: string
  password_confirm: string
}

interface FormErrors {
  email?: string
  first_name?: string
  last_name?: string
  password?: string
  password_confirm?: string
}

export function RegisterPage() {
  const navigate = useNavigate()
  const { toast: showToast } = useToast()
  const [form, setForm] = useState<FormState>({
    email: '',
    first_name: '',
    last_name: '',
    phone: '',
    password: '',
    password_confirm: '',
  })
  const [errors, setErrors] = useState<FormErrors>({})
  const [loading, setLoading] = useState(false)

  function validate(): boolean {
    const e: FormErrors = {}
    if (!form.email.trim()) e.email = 'Email is required.'
    if (!form.first_name.trim()) e.first_name = 'First name is required.'
    if (!form.last_name.trim()) e.last_name = 'Last name is required.'
    if (form.password.length < 8) e.password = 'Password must be at least 8 characters.'
    if (form.password !== form.password_confirm) e.password_confirm = 'Passwords do not match.'
    setErrors(e)
    return Object.keys(e).length === 0
  }

  function set(field: keyof FormState) {
    return (e: React.ChangeEvent<HTMLInputElement>) =>
      setForm((f) => ({ ...f, [field]: e.target.value }))
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!validate()) return

    setLoading(true)
    try {
      await register(form)
      showToast('Account created! Please sign in.', 'success')
      navigate('/login', { replace: true })
    } catch (err: unknown) {
      const data = (err as { response?: { data?: { message?: string; details?: Record<string, string[]> } } })
        ?.response?.data
      if (data?.details) {
        const fieldErrors: FormErrors = {}
        for (const [key, msgs] of Object.entries(data.details)) {
          ;(fieldErrors as Record<string, string>)[key] = Array.isArray(msgs) ? msgs[0] : String(msgs)
        }
        setErrors(fieldErrors)
      } else {
        showToast(data?.message ?? 'Registration failed.', 'error')
      }
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

        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 shadow-2xl shadow-black/50">
          <h1 className="text-lg font-semibold text-white mb-1">Create account</h1>
          <p className="text-sm text-gray-500 mb-6">Fill in your details to register.</p>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <Input
                label="First name"
                id="first_name"
                value={form.first_name}
                onChange={set('first_name')}
                error={errors.first_name}
                disabled={loading}
              />
              <Input
                label="Last name"
                id="last_name"
                value={form.last_name}
                onChange={set('last_name')}
                error={errors.last_name}
                disabled={loading}
              />
            </div>
            <Input
              label="Email"
              id="email"
              type="email"
              autoComplete="email"
              value={form.email}
              onChange={set('email')}
              error={errors.email}
              placeholder="you@example.com"
              disabled={loading}
            />
            <Input
              label="Phone (optional)"
              id="phone"
              type="tel"
              value={form.phone}
              onChange={set('phone')}
              disabled={loading}
            />
            <Input
              label="Password"
              id="password"
              type="password"
              value={form.password}
              onChange={set('password')}
              error={errors.password}
              placeholder="Min. 8 characters"
              disabled={loading}
            />
            <Input
              label="Confirm password"
              id="password_confirm"
              type="password"
              value={form.password_confirm}
              onChange={set('password_confirm')}
              error={errors.password_confirm}
              disabled={loading}
            />
            <Button
              type="submit"
              variant="primary"
              size="lg"
              loading={loading}
              className="w-full mt-2"
            >
              Create account
            </Button>
          </form>

          <p className="text-center text-sm text-gray-600 mt-5">
            Already have an account?{' '}
            <Link to="/login" className="text-brand-400 hover:text-brand-300 transition-colors">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
