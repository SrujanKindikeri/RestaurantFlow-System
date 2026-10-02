// =============================================================================
// RestaurantFlow — Main Layout
// Phase 2: Sidebar navigation + top header
// =============================================================================

import { useState } from 'react'
import { Outlet, NavLink } from 'react-router-dom'
import { cn } from '@/utils/cn'

interface NavItem {
  label: string
  to: string
  icon: React.ReactNode
}

const NAV_ITEMS: NavItem[] = [
  {
    label: 'Dashboard',
    to: '/',
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
        <path strokeLinecap="round" strokeLinejoin="round" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
      </svg>
    ),
  },
  {
    label: 'Organizations',
    to: '/organizations',
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
        <path strokeLinecap="round" strokeLinejoin="round" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
      </svg>
    ),
  },
  {
    label: 'Restaurants',
    to: '/restaurants',
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
        <path strokeLinecap="round" strokeLinejoin="round" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
      </svg>
    ),
  },
  {
    label: 'Branches',
    to: '/branches',
    icon: (
      <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="1.75">
        <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
        <path strokeLinecap="round" strokeLinejoin="round" d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
]

export function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(false)

  return (
    <div className="min-h-screen bg-gray-950 text-gray-100 flex">

      {/* ------------------------------------------------------------------ */}
      {/* Mobile overlay                                                       */}
      {/* ------------------------------------------------------------------ */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-gray-950/80 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* ------------------------------------------------------------------ */}
      {/* Sidebar                                                              */}
      {/* ------------------------------------------------------------------ */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-60 flex flex-col bg-gray-900 border-r border-gray-800',
          'transform transition-transform duration-200 ease-in-out',
          'lg:static lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full',
        )}
        aria-label="Sidebar navigation"
      >
        {/* Logo */}
        <div className="flex items-center gap-3 px-5 h-14 border-b border-gray-800 flex-shrink-0">
          <div className="w-7 h-7 rounded-lg bg-brand-500 flex items-center justify-center flex-shrink-0">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4 text-white" aria-hidden="true">
              <path d="M3 11l19-9-9 19-2-8-8-2z" />
            </svg>
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-white text-sm tracking-tight truncate">RestaurantFlow</p>
            <p className="text-[10px] text-gray-600 font-mono">Phase 2</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4 overflow-y-auto" aria-label="Main navigation">
          <p className="px-2 mb-2 text-[10px] font-semibold text-gray-700 uppercase tracking-widest">
            Management
          </p>
          <ul className="space-y-0.5" role="list">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === '/'}
                  onClick={() => setSidebarOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      'flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
                      isActive
                        ? 'bg-brand-500/10 text-brand-400 border border-brand-500/20'
                        : 'text-gray-500 hover:text-gray-200 hover:bg-gray-800/60 border border-transparent',
                    )
                  }
                >
                  {item.icon}
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>

          {/* Future phases placeholder */}
          <div className="mt-6">
            <p className="px-2 mb-2 text-[10px] font-semibold text-gray-800 uppercase tracking-widest">
              Coming in Phase 3+
            </p>
            {['Users & Roles', 'Menu', 'Orders', 'Billing'].map((label) => (
              <div
                key={label}
                className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm text-gray-800 border border-transparent cursor-not-allowed"
              >
                <div className="h-4 w-4 rounded bg-gray-800" />
                {label}
              </div>
            ))}
          </div>
        </nav>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-gray-800 flex-shrink-0">
          <p className="text-[10px] text-gray-700">
            RestaurantFlow &copy; {new Date().getFullYear()}
          </p>
        </div>
      </aside>

      {/* ------------------------------------------------------------------ */}
      {/* Main content                                                         */}
      {/* ------------------------------------------------------------------ */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <header className="sticky top-0 z-30 h-14 flex items-center gap-4 px-4 sm:px-6 bg-gray-900/80 backdrop-blur-sm border-b border-gray-800 flex-shrink-0">
          {/* Mobile menu button */}
          <button
            className="lg:hidden p-1.5 rounded-md text-gray-500 hover:text-gray-200 hover:bg-gray-800 transition-colors"
            onClick={() => setSidebarOpen(true)}
            aria-label="Open navigation menu"
          >
            <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>

          <div className="flex-1" />

          {/* Phase indicator */}
          <span className="text-xs text-gray-600 font-mono hidden sm:block">
            Phase 2 — Organizations
          </span>
        </header>

        {/* Page */}
        <main className="flex-1 overflow-y-auto" id="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
