// =============================================================================
// RestaurantFlow — Dashboard Page
// Phase 1: Foundation landing page with backend health status display.
// =============================================================================

import { useHealth } from '@/hooks/useHealth'
import { StatusIndicator } from '@/components/StatusIndicator'
import { Card } from '@/components/Card'

export function DashboardPage() {
  const { data, isLoading, isError, dataUpdatedAt } = useHealth()

  const backendStatus = isLoading ? 'loading' : isError ? 'disconnected' : 'connected'
  const apiStatus = isLoading ? 'loading' : data?.status === 'ok' ? 'connected' : 'disconnected'

  const lastChecked = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleTimeString()
    : null

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-16">

      {/* Hero */}
      <div className="text-center mb-14">
        {/* Logo mark */}
        <div className="mx-auto mb-5 w-16 h-16 rounded-2xl bg-brand-500/10 border border-brand-500/30 flex items-center justify-center">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="w-8 h-8 text-brand-400"
            aria-hidden="true"
          >
            <path d="M3 11l19-9-9 19-2-8-8-2z" />
          </svg>
        </div>

        <h1 className="text-4xl sm:text-5xl font-bold text-white tracking-tight mb-3">
          RestaurantFlow
        </h1>
        <p className="text-lg text-gray-400 font-light">
          Restaurant Management &amp; POS Platform
        </p>

        <div className="mt-4 inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-800 border border-gray-700 text-xs text-gray-400">
          <span className="w-1.5 h-1.5 rounded-full bg-brand-500"></span>
          Phase 1 — Foundation
        </div>
      </div>

      {/* Divider */}
      <div className="border-t border-gray-800 mb-10" />

      {/* System Status */}
      <Card
        title="System Status"
        description="Live connectivity check between frontend and backend."
        className="mb-6"
      >
        <div className="flex flex-col gap-2">
          <StatusIndicator
            status={backendStatus}
            label="Backend"
            sublabel="Django REST API"
          />
          <StatusIndicator
            status={apiStatus}
            label="API"
            sublabel={data ? `${data.service}` : 'GET /api/health/'}
          />
        </div>

        {lastChecked && (
          <p className="text-xs text-gray-600 mt-3 text-right">
            Last checked: {lastChecked}
          </p>
        )}

        {isError && (
          <div
            className="mt-4 rounded-lg bg-red-950/40 border border-red-800/50 px-4 py-3 text-xs text-red-400"
            role="alert"
          >
            <strong className="font-semibold">Cannot reach backend.</strong>{' '}
            Make sure the Django server is running on{' '}
            <code className="font-mono">{import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api'}</code>.
          </div>
        )}
      </Card>

      {/* Architecture preview */}
      <Card
        title="Architecture"
        description="Current phase foundation."
      >
        <div className="font-mono text-xs text-gray-400 space-y-1 leading-relaxed">
          <div className="flex items-center gap-2">
            <span className="text-brand-400 font-semibold">React</span>
            <span className="text-gray-600">+ TypeScript + Vite + Tailwind</span>
          </div>
          <div className="pl-6 text-gray-600">↓ REST API</div>
          <div className="flex items-center gap-2">
            <span className="text-blue-400 font-semibold">Django</span>
            <span className="text-gray-600">+ DRF + Simple JWT</span>
          </div>
          <div className="pl-6 text-gray-600">↓</div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2">
              <span className="text-purple-400 font-semibold">PostgreSQL</span>
            </div>
            <span className="text-gray-700">·</span>
            <div className="flex items-center gap-2">
              <span className="text-red-400 font-semibold">Redis</span>
              <span className="text-gray-600">(WebSocket-ready)</span>
            </div>
          </div>
        </div>
      </Card>

      {/* Phase roadmap teaser */}
      <div className="mt-8 grid grid-cols-2 sm:grid-cols-3 gap-2">
        {[
          { phase: '1', label: 'Foundation', active: true },
          { phase: '2', label: 'Companies & Restaurants', active: false },
          { phase: '3', label: 'Users & Roles', active: false },
          { phase: '4', label: 'Counters & Sessions', active: false },
          { phase: '5', label: 'Menu', active: false },
          { phase: '6', label: 'Tables & Orders', active: false },
        ].map((item) => (
          <div
            key={item.phase}
            className={`rounded-lg px-3 py-2 text-xs border ${
              item.active
                ? 'bg-brand-500/10 border-brand-500/30 text-brand-400'
                : 'bg-gray-900/40 border-gray-800 text-gray-600'
            }`}
          >
            <span className="font-semibold">Phase {item.phase}</span>
            <div className="mt-0.5 text-[11px] opacity-80">{item.label}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
