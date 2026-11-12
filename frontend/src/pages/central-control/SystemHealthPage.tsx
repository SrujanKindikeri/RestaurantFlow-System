// =============================================================================
// RestaurantFlow — System Health Page
// Phase 15
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { centralControlApi, SystemHealth } from '@/services/centralControl'
import { Activity, RefreshCw, CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react'

type ComponentStatus = 'HEALTHY' | 'DEGRADED' | 'UNAVAILABLE' | 'UNKNOWN'

function StatusIcon({ status }: { status: string }) {
  switch (status) {
    case 'HEALTHY':     return <CheckCircle2 className="w-5 h-5 text-green-500"  aria-hidden="true" />
    case 'DEGRADED':    return <AlertTriangle className="w-5 h-5 text-yellow-500" aria-hidden="true" />
    case 'UNAVAILABLE': return <XCircle       className="w-5 h-5 text-red-500"   aria-hidden="true" />
    default:            return <HelpCircle    className="w-5 h-5 text-gray-400"  aria-hidden="true" />
  }
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    HEALTHY:     'bg-green-100 text-green-800',
    DEGRADED:    'bg-yellow-100 text-yellow-800',
    UNAVAILABLE: 'bg-red-100 text-red-800',
    UNKNOWN:     'bg-gray-100 text-gray-600',
    WARNING:     'bg-yellow-100 text-yellow-800',
    CRITICAL:    'bg-red-100 text-red-800',
  }
  return (
    <span
      className={`inline-block px-2 py-0.5 rounded text-xs font-medium ${map[status] || map.UNKNOWN}`}
      role="status"
      aria-label={`Status: ${status}`}
    >
      {status}
    </span>
  )
}

interface ComponentRowProps {
  name: string
  status: string
  description: string
}

function ComponentRow({ name, status, description }: ComponentRowProps) {
  return (
    <div className="flex items-center justify-between p-4 border-b border-gray-100 last:border-0">
      <div className="flex items-center gap-3">
        <StatusIcon status={status} />
        <div>
          <p className="font-medium text-gray-900 text-sm">{name}</p>
          <p className="text-xs text-gray-500">{description}</p>
        </div>
      </div>
      <StatusBadge status={status} />
    </div>
  )
}

export function SystemHealthPage() {
  const [health, setHealth] = useState<SystemHealth | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await centralControlApi.getSystemHealth()
      setHealth(res)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load health data.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()
    const interval = setInterval(load, 120_000) // refresh every 2 min
    return () => clearInterval(interval)
  }, [load])

  const components: Array<{ key: keyof SystemHealth; name: string; description: string }> = [
    { key: 'api',       name: 'API Server',         description: 'REST API availability' },
    { key: 'database',  name: 'Database',            description: 'PostgreSQL connectivity and response time' },
    { key: 'redis',     name: 'Redis',               description: 'Cache and channel layer availability' },
    { key: 'workers',   name: 'Background Workers',  description: 'Celery task worker status' },
    { key: 'websocket', name: 'WebSocket / Channels', description: 'Django Channels real-time infrastructure' },
  ]

  return (
    <main className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Activity className="w-6 h-6 text-blue-500" aria-hidden="true" />
            System Health
          </h1>
          {health?.checked_at && (
            <p className="text-sm text-gray-500 mt-0.5">
              Last checked: {new Date(health.checked_at).toLocaleTimeString()}
            </p>
          )}
        </div>
        <div className="flex items-center gap-3">
          {health && (
            <div className="text-center">
              <p className="text-xs text-gray-500">Overall</p>
              <StatusBadge status={health.overall} />
            </div>
          )}
          <button
            onClick={load}
            disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 
                       rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 
                       disabled:opacity-50"
            aria-label="Refresh system health"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm mb-4" role="alert">
          {error}
        </div>
      )}

      {loading && !health ? (
        <div className="flex items-center justify-center h-32" role="status" aria-label="Loading">
          <div className="animate-spin h-6 w-6 border-b-2 border-blue-600 rounded-full" aria-hidden="true" />
        </div>
      ) : health ? (
        <div className="bg-white rounded-lg border border-gray-200">
          {components.map(({ key, name, description }) => (
            <ComponentRow
              key={key}
              name={name}
              status={String(health[key] ?? 'UNKNOWN')}
              description={description}
            />
          ))}
        </div>
      ) : null}

      <p className="mt-4 text-xs text-gray-400 text-center">
        These checks are safe lightweight application-level checks.
        Infrastructure details are never exposed.
      </p>
    </main>
  )
}
