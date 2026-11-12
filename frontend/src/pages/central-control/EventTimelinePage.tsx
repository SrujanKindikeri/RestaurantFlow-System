// =============================================================================
// RestaurantFlow — Central Control Event Timeline
// Phase 15
// =============================================================================

import { useEffect, useState, useCallback } from 'react'
import { centralControlApi, CentralSystemEvent } from '@/services/centralControl'
import { Clock, RefreshCw, Search } from 'lucide-react'

const SEVERITY_DOT: Record<string, string> = {
  CRITICAL: 'bg-red-500',
  HIGH:     'bg-orange-500',
  MEDIUM:   'bg-yellow-500',
  LOW:      'bg-blue-400',
  INFO:     'bg-gray-400',
}

function EventItem({ event }: { event: CentralSystemEvent }) {
  const dotColor = SEVERITY_DOT[event.severity] || SEVERITY_DOT.INFO
  return (
    <li className="flex gap-3 py-3 border-b border-gray-50 last:border-0">
      <div className="flex-shrink-0 flex flex-col items-center">
        <span
          className={`w-2.5 h-2.5 rounded-full mt-1 ${dotColor}`}
          aria-hidden="true"
        />
        <div className="w-px flex-1 bg-gray-100 mt-1" aria-hidden="true" />
      </div>
      <div className="flex-1 min-w-0 pb-1">
        <p className="text-sm font-medium text-gray-900">{event.title}</p>
        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
          <span className="text-xs text-gray-500">
            {new Date(event.occurred_at).toLocaleString()}
          </span>
          {event.restaurant && (
            <span className="text-xs text-gray-400">· {event.restaurant.name}</span>
          )}
          {event.branch && (
            <span className="text-xs text-gray-400">· {event.branch.name}</span>
          )}
          <span className="text-xs text-gray-400">
            · {event.event_type.replace(/_/g, ' ')}
          </span>
        </div>
        {event.description && (
          <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{event.description}</p>
        )}
      </div>
      <div className="flex-shrink-0">
        <span
          className={`inline-block px-1.5 py-0.5 rounded text-xs font-medium ${
            event.severity === 'CRITICAL' ? 'bg-red-100 text-red-700' :
            event.severity === 'HIGH'     ? 'bg-orange-100 text-orange-700' :
            'bg-gray-100 text-gray-600'
          }`}
          aria-label={`Severity: ${event.severity}`}
        >
          {event.severity}
        </span>
      </div>
    </li>
  )
}

export function EventTimelinePage() {
  const [events, setEvents] = useState<CentralSystemEvent[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await centralControlApi.getEvents({
        page,
        page_size: 30,
        ...(search ? { search } : {}),
      })
      setEvents(res.results)
      setTotal(res.count)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load events.')
    } finally {
      setLoading(false)
    }
  }, [page, search])

  useEffect(() => { load() }, [load])

  return (
    <main className="p-4 max-w-3xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Clock className="w-6 h-6 text-blue-500" aria-hidden="true" />
            Event Timeline
          </h1>
          <p className="text-sm text-gray-500 mt-0.5">{total} organization-level events</p>
        </div>
        <button
          onClick={load}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg 
                     hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          aria-label="Refresh events"
        >
          <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} aria-hidden="true" />
          Refresh
        </button>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-400" aria-hidden="true" />
        <input
          type="search"
          placeholder="Search events…"
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1) }}
          className="w-full pl-9 pr-3 py-2 text-sm border border-gray-300 rounded-lg 
                     focus:outline-none focus:ring-2 focus:ring-blue-500"
          aria-label="Search events"
        />
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm mb-4" role="alert">
          {error}
        </div>
      )}

      <div className="bg-white rounded-lg border border-gray-200 px-4">
        {loading && events.length === 0 ? (
          <div className="flex items-center justify-center h-32" role="status" aria-label="Loading">
            <div className="animate-spin h-6 w-6 border-b-2 border-blue-600 rounded-full" aria-hidden="true" />
          </div>
        ) : events.length === 0 ? (
          <p className="py-8 text-center text-gray-400 text-sm">No events found.</p>
        ) : (
          <ul aria-label="Event timeline">
            {events.map(event => <EventItem key={event.id} event={event} />)}
          </ul>
        )}
      </div>

      {total > 30 && (
        <div className="flex items-center justify-between mt-4 text-sm text-gray-500">
          <p>Showing {(page-1)*30+1}–{Math.min(page*30,total)} of {total}</p>
          <div className="flex gap-2">
            <button onClick={() => setPage(p => Math.max(1, p-1))} disabled={page===1}
              className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              aria-label="Previous page">Previous</button>
            <button onClick={() => setPage(p => p+1)} disabled={page*30>=total}
              className="px-3 py-1 border border-gray-300 rounded hover:bg-gray-50 
                         focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
              aria-label="Next page">Next</button>
          </div>
        </div>
      )}
    </main>
  )
}
