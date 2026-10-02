// =============================================================================
// RestaurantFlow — Main Layout
// Phase 1: Minimal shell. Navigation and sidebar will be added in later phases.
// =============================================================================

import { Outlet } from 'react-router-dom'

export function MainLayout() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex flex-col">
      {/* Top navigation bar — will be expanded in Phase 2+ */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-14 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {/* Logo mark */}
            <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="w-4 h-4 text-white"
                aria-hidden="true"
              >
                <path d="M3 11l19-9-9 19-2-8-8-2z" />
              </svg>
            </div>
            <span className="font-semibold text-white tracking-tight">RestaurantFlow</span>
          </div>

          <nav aria-label="Main navigation">
            <span className="text-xs text-gray-500 font-mono">Phase 1 — Foundation</span>
          </nav>
        </div>
      </header>

      {/* Page content */}
      <main className="flex-1" id="main-content">
        <Outlet />
      </main>

      {/* Footer */}
      <footer className="border-t border-gray-800 py-4 text-center text-xs text-gray-600">
        RestaurantFlow &copy; {new Date().getFullYear()} — Restaurant Management &amp; POS Platform
      </footer>
    </div>
  )
}
