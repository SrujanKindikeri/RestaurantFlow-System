// =============================================================================
// RestaurantFlow — 404 Not Found Page
// =============================================================================

import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center text-center px-4">
      <h1 className="text-6xl font-bold text-gray-700 mb-4">404</h1>
      <p className="text-gray-400 mb-6">This page doesn't exist.</p>
      <Link
        to="/"
        className="text-sm text-brand-400 hover:text-brand-300 underline underline-offset-2 transition-colors"
      >
        ← Back to dashboard
      </Link>
    </div>
  )
}
