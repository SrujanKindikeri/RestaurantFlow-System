// =============================================================================
// RestaurantFlow — Frontend Error Reporting (Phase 24)
//
// A minimal, dependency-free global error reporter. Captures JavaScript
// runtime errors and unhandled promise rejections and posts a SAFE, truncated
// payload to /api/observability/frontend-errors. It deliberately does NOT
// collect request bodies, customer data, or stack-trace file contents.
//
// Use navigator.sendBeacon where available so reports survive page unload;
// fall back to fetch(keepalive). Identical errors are deduped for a few
// seconds to avoid spamming the endpoint.
// =============================================================================

const API_BASE =
  (import.meta as unknown as { env?: Record<string, string | undefined> }).env?.VITE_API_URL ??
  'http://localhost:8000/api'

const ENDPOINT = `${API_BASE}/observability/frontend-errors`
const MAX_MESSAGE_LEN = 1000
const DEDUPE_MS = 5000

let lastReportKey = ''
let lastReportAt = 0

interface ErrorPayload {
  type: string
  message: string
  url?: string
  line?: number
  column?: number
  severity: string
}

function truncate(s: unknown, max: number): string {
  if (s === null || s === undefined) return ''
  return String(s).slice(0, max)
}

export function reportFrontendError(input: Partial<ErrorPayload>): void {
  try {
    const payload: ErrorPayload = {
      type: truncate(input.type || 'javascript_error', 80),
      message: truncate(input.message || '', MAX_MESSAGE_LEN),
      url: truncate(input.url || (typeof location !== 'undefined' ? location.href : ''), 500),
      line: typeof input.line === 'number' ? input.line : undefined,
      column: typeof input.column === 'number' ? input.column : undefined,
      severity: truncate(input.severity || 'MEDIUM', 10).toUpperCase() || 'MEDIUM',
    }

    // Dedupe identical errors within a short window.
    const key = `${payload.type}:${payload.message}`
    const now = Date.now()
    if (key === lastReportKey && now - lastReportAt < DEDUPE_MS) return
    lastReportKey = key
    lastReportAt = now

    const body = JSON.stringify(payload)
    // Prefer sendBeacon (survives unload) with a JSON Blob.
    if (typeof navigator !== 'undefined' && typeof navigator.sendBeacon === 'function') {
      const ok = navigator.sendBeacon(ENDPOINT, new Blob([body], { type: 'application/json' }))
      if (ok) return
    }
    // Fallback: fetch with keepalive.
    if (typeof fetch === 'function') {
      void fetch(ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
        credentials: 'omit',
      }).catch(() => {
        /* swallow — error reporting must never throw */
      })
    }
  } catch {
    /* swallow — never let reporting break the app */
  }
}

export function installGlobalErrorReporter(): void {
  if (typeof window === 'undefined') return
  window.addEventListener('error', (event: ErrorEvent) => {
    reportFrontendError({
      type: event.error?.name || 'javascript_error',
      message: event.message,
      url: event.filename,
      line: event.lineno,
      column: event.colno,
      severity: 'HIGH',
    })
  })
  window.addEventListener('unhandledrejection', (event: PromiseRejectionEvent) => {
    const reason = event.reason
    reportFrontendError({
      type: 'unhandledrejection',
      message:
        reason && typeof reason === 'object' && 'message' in reason
          ? String((reason as Error).message)
          : String(reason),
      severity: 'MEDIUM',
    })
  })
}
